from typing import TYPE_CHECKING

from app.database.base import Base
from app.database.models.mixins import TimestampMixin

from app.database.models.statuses import (
    VPN_KEY_CREATING,
)

from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB


if TYPE_CHECKING:
    from app.database.models.user import User
    from app.database.models.tariff import Tariff


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
    subscription_url: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    inbound_ids: Mapped[list[int]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"), nullable=False)

    status: Mapped[str] = mapped_column(String(16), server_default=VPN_KEY_CREATING, nullable=False)

    tariff_id: Mapped[int] = mapped_column(ForeignKey(column="tariffs.id", ondelete="RESTRICT"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pending_tariff_id: Mapped[int | None] = mapped_column(ForeignKey(column="tariffs.id", ondelete="RESTRICT"), nullable=True)
    pending_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pending_order_id: Mapped[int | None] = mapped_column(ForeignKey(column="orders.id", ondelete="SET NULL"), unique=True, nullable=True)
    last_fulfilled_order_id: Mapped[int | None] = mapped_column(ForeignKey(column="orders.id", ondelete="SET NULL"), unique=True, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="vpn_key")
    tariff: Mapped["Tariff"] = relationship(back_populates="vpn_keys", foreign_keys=[tariff_id])
