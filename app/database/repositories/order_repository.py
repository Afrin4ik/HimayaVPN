from datetime import datetime
from typing import Tuple

from sqlalchemy import Result, and_, or_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Order
from app.database.models.statuses import (
    ORDER_CREATED,
    ORDER_PAID,
    ORDER_FAILED,
    ORDER_FULFILLING,
    ORDER_FULFILLED,
)


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session

    async def create_order(
            self,
            *,
            user_id: int,
            tariff_id: int,
            amount_rub: int,
            idempotency_key: str,
            payload: dict,
    ) -> Order:
        order = Order(
            user_id=user_id,
            tariff_id=tariff_id,
            amount_rub=amount_rub,
            status=ORDER_CREATED,
            provider="yookassa",
            idempotency_key=idempotency_key,
            payload=payload,
        )

        self.session.add(order)
        await self.session.flush()

        return order

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

    async def mark_fulfilled(
            self,
            *,
            order_id: int,
    ) -> None:
        await self.session.execute(
            statement=update(table=Order)
            .where(
                Order.id == order_id,
                Order.status == ORDER_FULFILLING,
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
