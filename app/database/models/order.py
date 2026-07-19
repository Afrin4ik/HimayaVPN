from typing import TYPE_CHECKING

from app.database.base import Base
from app.database.models.mixins import TimestampMixin

from app.database.models.statuses import (
    ORDER_CREATED,
)

from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    CheckConstraint,
    text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB


if TYPE_CHECKING:
    from app.database.models.user import User
    from app.database.models.tariff import Tariff


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            sqltext="status in ('created', 'paid', 'cancelled', 'failed')",
            name="ck_orders_status",
        ),
        CheckConstraint(
            sqltext="amount_rub >= 0",
            name="ck_orders_amount_rub_non_negative",
        ),
        CheckConstraint(
            sqltext="jsonb_typeof(payload) = 'object'",
            name="ck_orders_payload_is_object",
        ),
        Index(
            "ix_orders_user_id_created_at",
            "user_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey(column="users.id", ondelete="CASCADE"), nullable=False)
    tariff_id: Mapped[int] = mapped_column(ForeignKey(column="tariffs.id", ondelete="RESTRICT"), nullable=False)

    amount_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), server_default=ORDER_CREATED, nullable=False)

    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="orders")
    tariff: Mapped["Tariff"] = relationship(back_populates="orders")
