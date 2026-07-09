from datetime import datetime

from sqlalchemy import (
    Integer,
    BigInteger,
    Boolean,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database.base import Base


VPN_KEY_CREATING = "creating"
VPN_KEY_ACTIVE = "active"
VPN_KEY_FAILED = "failed"
VPN_KEY_DISABLED = "disabled"

ORDER_CREATED = "created"
ORDER_PAID = "paid"
ORDER_CANCELLED = "cancelled"
ORDER_FAILED = "failed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)

    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_bot: Mapped[str] = mapped_column(Boolean, server_default="false", nullable=False)

    vpn_key: Mapped["VpnKey | None"] = relationship(back_populates="user", uselist=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Tariff(Base, TimestampMixin):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)

    price_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    limit_ip: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    total_gb: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    vpn_keys: Mapped[list["VpnKey"]] = relationship(back_populates="tariff")
    orders: Mapped[list["Order"]] = relationship(back_populates="tariff")


class VpnKey(Base, TimestampMixin):
    __tablename__ = "vpn_keys"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_vpn_keys_user_id"),
        CheckConstraint(
            sqltext="status in ('creating', 'active', 'failed', 'disabled')",
            name="ck_vpn_keys_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey(column="users.id", ondelete="CASCADE"), unique=True, nullable=False)

    xui_email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    xui_uuid: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    xui_sub_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    inbound_ids: Mapped[list[int]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"), nullable=False)

    status: Mapped[str] = mapped_column(String(16), server_default=VPN_KEY_CREATING, nullable=False)

    tariff_id: Mapped[int | None] = mapped_column(ForeignKey(column="tariffs.id", ondelete="SET NULL"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subscription_url: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="vpn_key")
    tariff: Mapped["Tariff | None"] = relationship(back_populates="vpn_key")


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            sqltext="status in ('created', 'paid', 'cancelled', 'failed')",
            name="ck_orders_status",
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
