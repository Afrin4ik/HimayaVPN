from datetime import datetime
from typing import Tuple, Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import Result, and_, or_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Order
from app.database.models.statuses import (
    ORDER_CREATED,
    ORDER_PAID,
    ORDER_CANCELLED,
    ORDER_FULFILLING,
    ORDER_FULFILLED,
    ORDER_FAILED,
)


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session

    async def create_or_get_order(
            self,
            *,
            user_id: int,
            tariff_id: int,
            amount_rub: int,
            provider: str,
            idempotency_key: str,
            payload: dict[str, Any],
    ) -> tuple[Order, bool]:
        stmt = (
            insert(table=Order)
            .values(
                user_id=user_id,
                tariff_id=tariff_id,
                amount_rub=amount_rub,
                status=ORDER_CREATED,
                provider=provider,
                idempotency_key=idempotency_key,
                payload=payload,
            )
            .on_conflict_do_nothing(
                index_elements=[Order.idempotency_key],
            )
            .returning(Order)
        )

        result: Result[Tuple[Order]] = await self.session.execute(statement=stmt)
        created_order: Order | None = result.scalar_one_or_none()

        if created_order is not None:
            return created_order, True

        existing_result: Result[Tuple[Order]] = await self.session.execute(
            statement=select(Order).where(
                Order.idempotency_key == idempotency_key,
            )
        )
        existing_order: Order | None = existing_result.scalar_one_or_none()

        if existing_order is None:
            raise RuntimeError(f"Order was not inserted and cannot be found by idempotency_key={idempotency_key!r}")

        return existing_order, False

    async def get_order_by_id(
            self,
            *,
            order_id: int,
            for_update: bool = False,
    ) -> Order | None:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.tariff),
            )
            .where(Order.id == order_id)
        )

        if for_update:
            stmt = stmt.with_for_update()

        result: Result[Tuple[Order]] = await self.session.execute(statement=stmt)
        return result.scalar_one_or_none()

    async def get_order_for_telegram_user(
            self,
            *,
            order_id: int,
            telegram_id: int,
    ) -> Order | None:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.tariff),
            )
            .where(
                Order.id == order_id,
                Order.user.has(telegram_id=telegram_id),
            )
        )

        result: Result[Tuple[Order]] = await self.session.execute(statement=stmt)

        return result.scalar_one_or_none()

    async def get_fulfillable_order_ids(
            self,
            *,
            retry_before: datetime,
            limit: int = 50,
    ) -> list[int]:
        result: Result[Tuple[int]] = await self.session.execute(
            statement=select(Order.id)
            .where(
                Order.paid_at.is_not(None),
                Order.fulfillment_attempts < 20,
                or_(
                    Order.status == ORDER_PAID,
                    and_(
                        Order.status == ORDER_FAILED,
                        Order.updated_at <= retry_before,
                    ),
                    and_(
                        Order.status == ORDER_FULFILLING,
                        Order.fulfillment_started_at <= retry_before,
                    ),
                ),
            )
            .order_by(Order.created_at.asc())
            .limit(limit)
        )

        return list(result.scalars().all())

    async def get_pending_provider_payment_ids(
            self,
            *,
            limit: int = 50,
    ) -> list[str]:
        result: Result[Tuple[str | None]] = await self.session.execute(
            statement=select(Order.provider_payment_id)
            .where(
                Order.status == ORDER_CREATED,
                Order.provider == "yookassa",
                Order.provider_payment_id.is_not(None),
            )
            .order_by(Order.created_at.asc())
            .limit(limit)
        )

        return [payment_id for payment_id in result.scalars().all() if payment_id is not None]

    async def get_unnotified_fulfilled_order_ids(
            self,
            *,
            notification_retry_before: datetime,
            limit: int = 50,
    ) -> list[int]:
        result: Result[Tuple[int]] = await self.session.execute(
            statement=select(Order.id)
            .where(
                Order.status == ORDER_FULFILLED,
                Order.notified_at.is_(None),
                or_(
                    Order.notification_error.is_(None),
                    Order.updated_at <= notification_retry_before,
                ),
            )
            .order_by(Order.fulfilled_at.asc())
            .limit(limit)
        )

        return list(result.scalars().all())

    async def claim_order_for_fulfillment(
            self,
            *,
            order_id: int,
            retry_before: datetime,
    ) -> Order | None:
        stmt = (
            update(table=Order)
            .where(
                Order.id == order_id,
                Order.paid_at.is_not(None),
                Order.fulfillment_attempts < 20,
                or_(
                    Order.status == ORDER_PAID,
                    and_(
                        Order.status == ORDER_FAILED,
                        Order.updated_at <= retry_before,
                    ),
                    and_(
                        Order.status == ORDER_FULFILLING,
                        Order.fulfillment_started_at <= retry_before,
                    ),
                ),
            )
            .values(
                status=ORDER_FULFILLING,
                fulfillment_started_at=func.now(),
                fulfillment_attempts=Order.fulfillment_attempts + 1,
                fulfillment_error=None,
                updated_at=func.now(),
            )
            .returning(Order)
        )

        result: Result[Tuple[Order]] = await self.session.execute(statement=stmt)
        return result.scalar_one_or_none()

    async def bind_created_payment(
            self,
            *,
            order_id: int,
            provider: str,
            provider_payment_id: str,
            confirmation_url: str,
            payment_snapshot: dict[str, Any],
    ) -> Order | None:
        order: Order | None = await self.get_order_by_id(
            order_id=order_id,
            for_update=True,
        )

        if order is None:
            return None

        if order.provider_payment_id not in {None, provider_payment_id}:
            return None

        order.provider = provider
        order.provider_payment_id = provider_payment_id
        order.confirmation_url = confirmation_url
        order.payload = {
            **order.payload,
            provider: payment_snapshot,
        }

        await self.session.flush()

        return order

    async def record_provider_observation(
            self,
            *,
            order: Order,
            provider: str,
            provider_payment_id: str,
            payment_snapshot: dict[str, Any],
    ) -> bool:
        if order.provider_payment_id not in {None, provider_payment_id}:
            return False

        order.provider = provider
        order.provider_payment_id = provider_payment_id
        order.payload = {
            **order.payload,
            provider: payment_snapshot,
        }

        await self.session.flush()

        return True

    async def mark_fulfilled(
            self,
            *,
            order_id: int,
    ) -> None:
        await self.session.execute(
            statement=update(table=Order)
            .where(
                Order.id == order_id,
                Order.paid_at.is_not(None),
                Order.status.in_([
                    ORDER_PAID,
                    ORDER_FULFILLING,
                    ORDER_FAILED,
                ]),
            )
            .values(
                status=ORDER_FULFILLED,
                fulfilled_at=func.now(),
                fulfillment_error=None,
                updated_at=func.now(),
            )
        )

    async def mark_fulfillment_failed(
            self,
            *,
            order_id: int,
            error: str,
    ) -> None:
        await self.session.execute(
            statement=update(table=Order)
            .where(
                Order.id == order_id,
                Order.status == ORDER_FULFILLING,
            )
            .values(
                status=ORDER_FAILED,
                fulfillment_error=error[:2000],
                updated_at=func.now(),
            )
        )

    async def mark_notified(
            self,
            *,
            order_id: int,
    ) -> None:
        await self.session.execute(
            statement=update(table=Order)
            .where(
                Order.id == order_id,
                Order.status == ORDER_FULFILLED,
                Order.notified_at.is_(None),
            )
            .values(
                notified_at=func.now(),
                notification_error=None,
                updated_at=func.now(),
            )
        )

    async def mark_notification_failed(
            self,
            *,
            order_id: int,
            error: str,
    ) -> None:
        await self.session.execute(
            statement=update(table=Order)
            .where(
                Order.id == order_id,
                Order.status == ORDER_FULFILLED,
                Order.notified_at.is_(None),
            )
            .values(
                notification_error=error[:2000],
                updated_at=func.now(),
            )
        )

    async def mark_paid(
            self,
            *,
            order: Order,
            paid_at: datetime,
    ) -> bool:
        if order.paid_at is not None:
            return True

        if order.status not in {ORDER_CREATED, ORDER_CANCELLED}:
            return False

        order.status = ORDER_PAID
        order.paid_at = paid_at

        await self.session.flush()

        return True

    async def mark_cancelled(
            self,
            *,
            order: Order,
    ) -> bool:
        if order.paid_at is not None:
            return False

        if order.status == ORDER_CANCELLED:
            return True

        if order.status != ORDER_CREATED:
            return False

        order.status = ORDER_CANCELLED

        await self.session.flush()

        return True
