import asyncio
import logging

from datetime import datetime, timedelta, timezone

from  aiogram import Bot

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings

from app.database.models import Order, VpnKey
from app.database.repositories import OrderRepository, VpnKeyRepository

from app.integrations.xui import AsyncXUI, XUIConfig
from app.integrations.yookassa import AsyncYooKassa

from app.services.dto import TelegramUserData, VpnKeyAccess

from app.services.payment_service import PaymentService
from app.services.vpn_key_service import VpnKeyService


logger = logging.getLogger(__name__)


FULFILLMENT_STALE_TIMEOUT = timedelta(minutes=3)
NOTIFICATION_RETRY_TIMEOUT = timedelta(minutes=5)

PAYMENT_STATUS_INTERVAL_SECONDS = 30
PAID_ORDER_INTERVAL_SECONDS = 5


async def reconcile_pending_payments_once(
        *,
        session_factory: async_sessionmaker[AsyncSession],
        yookassa: AsyncYooKassa,
        settings: Settings,
) -> None:
    async with session_factory() as session:
        order_repository = OrderRepository(session=session)

        payment_ids: list[str] = await order_repository.get_pending_provider_payment_ids(limit=50)

    for payment_id in payment_ids:
        async with session_factory() as session:
            payment_service = PaymentService(
                session=session,
                yookassa=yookassa,
                settings=settings,
            )

            try:
                await payment_service.synchronize_payment(payment_id=payment_id)

            except asyncio.CancelledError:
                await session.rollback()
                raise

            except Exception:
                await session.rollback()

                logger.exception(
                    "Cannot reconcile YooKassa payment (payment_id=%s)",
                    payment_id,
                )


async def fulfill_paid_orders_once(
        *,
        session_factory: async_sessionmaker[AsyncSession],
        xui: AsyncXUI,
        xui_config: XUIConfig,
) -> None:
    retry_before: datetime = datetime.now(timezone.utc) - FULFILLMENT_STALE_TIMEOUT

    async with session_factory() as session:
        order_repository = OrderRepository(session=session)

        order_ids: list[int] = await order_repository.get_fulfillable_order_ids(
            retry_before=retry_before,
            limit=50,
        )

    for order_id in order_ids:
        async with session_factory() as session:
            order_repository = OrderRepository(session=session)

            order: Order | None = await order_repository.claim_order_for_fulfillment(
                order_id=order_id,
                retry_before=retry_before,
            )

            if order is None:
                await session.rollback()
                continue

            await session.commit()

            order: Order | None = await order_repository.get_order_by_id(order_id=order_id)

            if order is None:
                logger.error(
                    "Claimed order disappeared (order_id=%s)",
                    order_id,
                )
                continue

            telegram_user = TelegramUserData(
                id=order.user.telegram_id,
                username=order.user.username,
                first_name=order.user.first_name,
                last_name=order.user.last_name,
                language_code=order.user.language_code,
                is_bot=order.user.is_bot,
            )

            vpn_service = VpnKeyService(
                session=session,
                xui=xui,
                xui_config=xui_config,
            )

            try:
                await vpn_service.fulfill_paid_order(
                    telegram_user=telegram_user,
                    tariff_id=order.tariff_id,
                    order_id=order.id,
                )

                logger.info(
                    "Paid order fulfilled successfully (order_id=%s)",
                    order.id,
                )

            except asyncio.CancelledError:
                await session.rollback()
                raise

            except Exception as exc:
                await session.rollback()

                await order_repository.mark_fulfillment_failed(
                    order_id=order.id,
                    error=f"{type(exc).__name__}: {exc}",
                )
                await session.commit()

                logger.exception(
                    "Cannot fulfill paid order (order_id=%s)",
                    order.id,
                )


async def notify_fulfilled_orders_once(
        *,
        session_factory: async_sessionmaker[AsyncSession],
        bot: Bot,
) -> None:
    retry_before: datetime = datetime.now(timezone.utc) - NOTIFICATION_RETRY_TIMEOUT

    async with session_factory() as session:
        order_repository = OrderRepository(session=session)

        order_ids: list[int] = await order_repository.get_unnotified_fulfilled_order_ids(
            notification_retry_before=retry_before,
            limit=50,
        )

    for order_id in order_ids:
        async with session_factory() as session:
            order_repository = OrderRepository(session=session)
            vpn_key_repository = VpnKeyRepository(session=session)

            order: Order | None = await order_repository.get_order_by_id(order_id=order_id)

            if order is None or order.notified_at is not None:
                continue

            vpn_key: VpnKey | None = await vpn_key_repository.get_vpn_key_by_last_fulfilled_order_id(order_id=order.id)

            try:
                if vpn_key is None:
                    raise RuntimeError("Fulfilled order does not have VPN key")

                if not vpn_key.subscription_url:
                    raise RuntimeError("VPN key does not have subscription_url")

                if vpn_key.expires_at is None:
                    raise RuntimeError("VPN key does not have expiration date")

                await bot.send_message(
                    chat_id=order.user.telegram_id,
                    text=(
                        f"✅ Оплата получена!\n\n"
                        f"VPN-ключ успешно продлён\n\n"
                        f"Действует до:\n"
                        f"{vpn_key.expires_at:%d.%m.%Y %H:%M} UTC\n\n"
                        f"Ваш ключ:\n"
                        f"{vpn_key.subscription_url}\n\n"
                        f"Скопируйте ссылку и добавьте её в VPN-клиент"
                    )
                )

                await order_repository.mark_notified(order_id=order.id)
                await session.commit()

                logger.info(
                    "Paid order notification sent (order_id=%s, telegram_id=%s)",
                    order.id,
                    order.user.telegram_id,
                )

            except asyncio.CancelledError:
                await session.rollback()
                raise

            except Exception as exc:
                await session.rollback()

                await order_repository.mark_notification_failed(
                    order_id=order.id,
                    error=f"{type(exc).__name__}: {exc}",
                )
                await session.commit()

                logger.exception(
                    "Cannot notify user about paid order (order_id=%s, telegram_id=%s)",
                    order.id,
                    order.user.telegram_id,
                )


async def run_payment_status_reconciler(
        *,
        session_factory:async_sessionmaker[AsyncSession],
        yookassa: AsyncYooKassa,
        settings: Settings,
) -> None:
    logger.info("Payment status reconciler started")

    try:
        while True:
            try:
                await reconcile_pending_payments_once(
                    session_factory=session_factory,
                    yookassa=yookassa,
                    settings=settings,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception("Payment status reconciliation failed")

            await asyncio.sleep(PAYMENT_STATUS_INTERVAL_SECONDS)

    finally:
        logger.info("Payment status reconciler stopped")


async def run_paid_order_reconciler(
        *,
        session_factory: async_sessionmaker[AsyncSession],
        xui: AsyncXUI,
        xui_config: XUIConfig,
        bot: Bot,
) -> None:
    logger.info("Paid order reconciler started")

    try:
        while True:
            try:
                await fulfill_paid_orders_once(
                    session_factory=session_factory,
                    xui=xui,
                    xui_config=xui_config,
                )

                await notify_fulfilled_orders_once(
                    session_factory=session_factory,
                    bot=bot,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception("Paid order reconciliation failed")

            await asyncio.sleep(PAID_ORDER_INTERVAL_SECONDS)

    finally:
        logger.info("Paid order reconciler stopped")
