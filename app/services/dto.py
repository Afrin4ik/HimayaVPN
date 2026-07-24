from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TelegramUserData:
    id: int
    username: str | None
    first_name: str
    last_name: str | None
    language_code: str | None
    is_bot: bool


@dataclass(frozen=True, slots=True)
class TariffOption:
    code: str
    title: str
    price_rub: int


@dataclass(frozen=True, slots=True)
class VpnKeyAccess:
    id: int
    subscription_url: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class VpnKeyProfile:
    subscription_url: str | None
    status: str
    tariff_title: str
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class PaymentCheckout:
    order_id: int
    confirmation_url: str
    amount_rub: int
