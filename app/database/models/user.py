from typing import TYPE_CHECKING

from app.database.base import Base
from app.database.models.mixins import TimestampMixin

from sqlalchemy import (
    Integer,
    BigInteger,
    Boolean,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


if TYPE_CHECKING:
    from app.database.models.vpn_key import VpnKey
    from app.database.models.order import Order


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
