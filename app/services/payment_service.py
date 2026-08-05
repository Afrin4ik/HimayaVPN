from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models.vpn_key import VpnKey
from app.integrations.yookassa import AsyncYooKassa
from app.database.models import Order, Tariff, User
from app.database.models.statuses import (
    ORDER_CREATED,
    ORDER_PAID,
    ORDER_CANCELLED,
    ORDER_FULFILLED,
    ORDER_FAILED,
)
from app.database.repositories.order_repository import OrderRepository
from app.database.repositories.vpn_key_repository import VpnKeyRepository
from app.services.tariff_service import TariffService, TRIAL_TARIFF_CODE
from app.services.user_service import UserService
from app.services.dto import (
    TelegramUserData,
    PaymentCheckout,
    PaymentOrderView,
)

from app.services.exceptions import (
    PaymentServiceError,
    PaymentVerificationError,
    PaymentOrderNotFoundError,
)


class PaymentService:
    def __init__(
            self,
            *,
            session: AsyncSession,
            yookassa: AsyncYooKassa,
            settings: Settings,
    ) -> None:
        self.session: AsyncSession = session
        self.yookassa: AsyncYooKassa = yookassa
        self.settings: Settings = settings

        self.order_repository = OrderRepository(session=session)
        self.vpn_key_repository = VpnKeyRepository(session=session)
        self.user_service = UserService(session=session)
        self.tariff_service = TariffService(session=session)

    @staticmethod
    def _payment_snapshot(payment: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": payment.get("id"),
            "status": payment.get("status"),
            "paid": payment.get("paid"),
            "amount": payment.get("amount"),
            "created_at": payment.get("created_at"),
            "captured_at": payment.get("captured_at"),
            "cancellation_details": payment.get("cancellation_details"),
            "test": payment.get("test"),
        }

    @staticmethod
    def _tariff_snapshot(tariff: Tariff) -> dict[str, Any]:
        return {
            "id": tariff.id,
            "code": tariff.code,
            "title": tariff.title,
            "price_rub": tariff.price_rub,
            "duration_days": tariff.duration_days,
            "limit_ip": tariff.limit_ip,
            "total_gb": tariff.total_gb,
        }

    async def create_checkout(
            self,
            *,
            telegram_user: TelegramUserData,
            tariff_code: str,
    ) -> PaymentCheckout:
        user: User = await self.user_service.sync_telegram_user(telegram_user=telegram_user)

        tariff: Tariff = await self.tariff_service.get_active_tariff_by_code(code=tariff_code)
        if tariff.code == TRIAL_TARIFF_CODE or tariff.price_rub <= 0:
            raise PaymentServiceError("This tariff cannot be purchased")

        idempotency_key = str(uuid4())

        order: Order = await self.order_repository.create_order(
            user_id=user.id,
            tariff_id=tariff.id,
            amount_rub=tariff.price_rub,
            idempotency_key=idempotency_key,
            payload={
                "tariff_snapshot": self._tariff_snapshot(tariff=tariff),
            },
        )

        await self.session.commit()

        payment_request: dict[str, Any] = {
            "amount": {
                "value": f"{order.amount_rub}.00",
                "currency": "RUB",
            },
            "description": f"HimayaVPN. Оплата заказа №{order.id}",
            "confirmation": {
                "type": "redirect",
                "return_url": self.settings.yookassa_return_url,
            },
            "capture": True,
            "metadata": {
                "order_id": str(order.id),
            },
        }

        payment: dict[str, Any] = await self.yookassa.create_payment(
            request=payment_request,
            idempotency_key=order.idempotency_key,
        )

        payment_id = payment.get("id")
        if not isinstance(payment_id, str) or not payment_id:
            raise PaymentServiceError("YooKassa did not return payment id")

        confirmation = payment.get("confirmation")
        if isinstance(confirmation, dict):
            confirmation_url = confirmation.get("confirmation_url")
        else:
            confirmation_url = None

        if confirmation_url is None or not isinstance(confirmation_url, str) or not confirmation_url:
            raise PaymentServiceError("YooKassa did not return confirmation_url")

        locked_order: Order | None = await self.order_repository.get_order_by_id(
            order_id=order.id,
            for_update=True,
        )

        if locked_order is None:
            raise PaymentServiceError(f"Order {order.id} disappeared")

        locked_order.provider = "yookassa"
        locked_order.provider_payment_id = payment_id
        locked_order.confirmation_url = confirmation_url
        locked_order.payload = {
            **locked_order.payload,
            "yookassa": self._payment_snapshot(payment=payment),
        }

        await self.session.commit()

        return PaymentCheckout(
            order_id=locked_order.id,
            confirmation_url=confirmation_url,
            amount_rub=locked_order.amount_rub,
        )

    async def synchronize_payment(
            self,
            *,
            payment_id: str,
    ) -> None:
        payment: dict[str, Any] = await self.yookassa.get_payment(payment_id=payment_id)

        metadata = payment.get("metadata")

        if not isinstance(metadata, dict):
            raise PaymentVerificationError("Payment does not contain metadata")

        raw_order_id = metadata.get("order_id")

        try:
            order_id = int(raw_order_id)
        except (TypeError, ValueError):
            raise PaymentVerificationError("Payment contains invalid order_id")

        order: Order | None = await self.order_repository.get_order_by_id(
            order_id=order_id,
            for_update=True,
        )

        if order is None:
            raise PaymentVerificationError(f"Unknown local order {order_id}")

        remote_payment_id = payment.get("id")

        if remote_payment_id != payment_id:
            raise PaymentVerificationError("Payment is mismatch")

        if order.provider_payment_id not in {None, payment_id}:
            raise PaymentVerificationError("Order is linked to another payment")

        amount = payment.get("amount")

        if not isinstance(amount, dict):
            raise PaymentVerificationError("Payment does not contain amount")

        if amount.get("currency") != "RUB":
            raise PaymentVerificationError("Unexpected currency")

        try:
            remote_amount = Decimal(str(amount.get("value")))
        except InvalidOperation:
            raise PaymentVerificationError("Invalid payment amount")

        expected_amount: Decimal = Decimal(order.amount_rub).quantize(Decimal("0.01"))

        if remote_amount != expected_amount:
            raise PaymentVerificationError(f"Amount mismatch ({remote_amount} != {expected_amount})")

        recipient = payment.get("recipient")

        if not isinstance(recipient, dict) or str(recipient.get("account_id")) != self.settings.yookassa_shop_id:
            raise PaymentVerificationError("Payment belongs to another shop")

        is_test: bool = payment.get("test")

        if not isinstance(is_test, bool):
            raise PaymentVerificationError("Payment does not contain a valid test flag")

        if is_test and not self.settings.yookassa_allow_test_payments:
            raise PaymentVerificationError("Test payment is forbidden in this environment")

        order.provider = "yookassa"
        order.provider_payment_id = payment_id
        order.payload = {
            **order.payload,
            "yookassa": self._payment_snapshot(payment=payment),
        }

        status = payment.get("status")
        paid = payment.get("paid")

        if status == "succeeded":
            if paid is not True:
                raise PaymentVerificationError("Succeeded payment has paid=false")

            if order.paid_at is None:
                order.paid_at = datetime.now(timezone.utc)

                if order.status in {ORDER_CREATED, ORDER_CANCELLED, ORDER_FAILED}:
                    order.status = ORDER_PAID

        elif status == "canceled":
            if order.paid_at is None:
                order.status = ORDER_CANCELLED

        elif status != "pending":
            raise PaymentVerificationError(f"Unsupported payment status {status!r}")

        await self.session.commit()

    async def get_user_order_status(
            self,
            *,
            order_id: int,
            telegram_id: int,
            synchronize: bool = True,
    ) -> PaymentOrderView:
        order: Order | None = await self.order_repository.get_order_for_telegram_user(
            order_id=order_id,
            telegram_id=telegram_id,
        )

        if order is None:
            raise PaymentOrderNotFoundError(f"Order {order_id} was not found")

        provider_payment_id: str | None = order.provider_payment_id

        await self.session.commit()

        if synchronize and provider_payment_id is not None:
            await self.synchronize_payment(payment_id=provider_payment_id)

            order = await self.order_repository.get_order_for_telegram_user(
                order_id=order_id,
                telegram_id=telegram_id,
            )

            if order is None:
                raise PaymentOrderNotFoundError(f"Order {order_id} disappeared")

        vpn_key: VpnKey | None = None

        if order.status == ORDER_FULFILLED:
            vpn_key = await self.vpn_key_repository.get_vpn_key_by_last_fulfilled_order_id(order_id=order.id)

            if vpn_key is None:
                vpn_key = await self.vpn_key_repository.get_vpn_key_by_user_id(user_id=order.user_id)

        return PaymentOrderView(
            order_id=order.id,
            status=order.status,
            amount_rub=order.amount_rub,
            confirmation_url=order.confirmation_url,
            paid_at=order.paid_at,
            subscription_url=(
                vpn_key.subscription_url
                if vpn_key is not None
                else None
            ),
            vpn_expires_at=(
                vpn_key.expires_at
                if vpn_key is not None
                else None
            ),
        )
