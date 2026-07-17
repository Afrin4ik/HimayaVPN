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
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database.base import Base


VPN_KEY_CREATING = "creating"
VPN_KEY_ACTIVE = "active"
VPN_KEY_FAILED = "failed"
VPN_KEY_DISABLED = "disabled"
VPN_KEY_RENEWING = "renewing"

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
    is_bot: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    trial_available: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    vpn_key: Mapped["VpnKey | None"] = relationship(back_populates="user", uselist=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Tariff(Base, TimestampMixin):
    __tablename__ = "tariffs"
    __table_args__ = (
        CheckConstraint(
            sqltext="btrim(code) <> ''",
            name="ck_tariffs_code_not_blank",
        ),
        CheckConstraint(
            sqltext="btrim(title) <> ''",
            name="ck_tariffs_title_not_blank",
        ),
        CheckConstraint(
            sqltext="price_rub >= 0",
            name="ck_tariffs_price_rub_non_negative",
        ),
        CheckConstraint(
            sqltext="duration_days > 0",
            name="ck_tariffs_duration_days_positive",
        ),
        CheckConstraint(
            sqltext="limit_ip > 0",
            name="ck_tariffs_limit_ip_positive",
        ),
        CheckConstraint(
            sqltext="total_gb > 0",
            name="ck_tariffs_total_gb_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)

    price_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    limit_ip: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    total_gb: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    vpn_keys: Mapped[list["VpnKey"]] = relationship(back_populates="tariff", foreign_keys="VpnKey.tariff_id")
    orders: Mapped[list["Order"]] = relationship(back_populates="tariff")


class VpnKey(Base, TimestampMixin):
    __tablename__ = "vpn_keys"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_vpn_keys_user_id"),
        CheckConstraint(
            sqltext="status in ('creating', 'active', 'failed', 'disabled', 'renewing')",
            name="ck_vpn_keys_status",
        ),
        CheckConstraint(
            sqltext=(
                "status NOT IN ('active', 'renewing') OR ("
                "xui_email IS NOT NULL AND "
                "btrim(xui_email) <> '' AND "
                "xui_uuid IS NOT NULL AND "
                "btrim(xui_uuid) <> '' AND "
                "xui_sub_id IS NOT NULL AND "
                "btrim(xui_sub_id) <> '' AND "
                "subscription_url IS NOT NULL AND "
                "btrim(subscription_url) <> '' AND "
                "expires_at IS NOT NULL"
                ")"
            ),
            name="ck_vpn_keys_active_has_credentials",
        ),
        CheckConstraint(
            sqltext=(
                "("
                "status = 'renewing' AND "
                "pending_tariff_id IS NOT NULL AND "
                "pending_expires_at IS NOT NULL"
                ") OR ("
                "status <> 'renewing' AND "
                "pending_tariff_id IS NULL AND "
                "pending_expires_at IS NULL"
                ")"
            ),
            name="ck_vpn_keys_renewing_has_pending_data",
        ),
        Index(
            "ix_vpn_keys_status_updated_at",
            "status",
            "updated_at",
        ),
        Index(
            "ix_vpn_keys_status_expires_at",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey(column="users.id", ondelete="CASCADE"), nullable=False)

    xui_email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    xui_uuid: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    xui_sub_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    inbound_ids: Mapped[list[int]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"), nullable=False)

    status: Mapped[str] = mapped_column(String(16), server_default=VPN_KEY_CREATING, nullable=False)

    tariff_id: Mapped[int] = mapped_column(ForeignKey(column="tariffs.id", ondelete="RESTRICT"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pending_tariff_id: Mapped[int | None] = mapped_column(ForeignKey(column="tariffs.id", ondelete="RESTRICT"), nullable=True)
    pending_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subscription_url: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="vpn_key")
    tariff: Mapped["Tariff"] = relationship(back_populates="vpn_keys", foreign_keys=[tariff_id])


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
