from typing import TYPE_CHECKING

from app.database.base import Base
from app.database.models.mixins import TimestampMixin

from sqlalchemy import (
    Integer,
    Boolean,
    String,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


if TYPE_CHECKING:
    from app.database.models.vpn_key import VpnKey
    from app.database.models.order import Order


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
    limit_ip: Mapped[int] = mapped_column(Integer, nullable=False)
    total_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    vpn_keys: Mapped[list["VpnKey"]] = relationship(back_populates="tariff", foreign_keys="VpnKey.tariff_id")
    orders: Mapped[list["Order"]] = relationship(back_populates="tariff")
