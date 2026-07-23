import os
from dotenv import load_dotenv

from dataclasses import dataclass
from functools import lru_cache


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    xui_base_url: str
    xui_web_base_path: str
    xui_api_token: str
    xui_subscription_base_url: str
    xui_subscription_path: str
    xui_default_inbound_ids: list[int]
    xui_default_limit_ip: int
    xui_default_total_gb: int
    database_url: str
    tg_support_username: str
    tg_support_url: str
    yookassa_shop_id: str
    yookassa_secret_key: str
    yookassa_return_url: str
    yookassa_webhook_secret: str
    yookassa_webhook_host: str
    yookassa_webhook_port: int
    yookassa_allow_test_payments: bool


def _get_required_env(key: str) -> str:
    value: str | None = os.getenv(key=key)
    if value is None or not value.strip():
        raise RuntimeError(f"{key} is not set")
    return value.strip()

def _parse_list_of_int(value: str) -> list[int]:
    inbound_ids: list[int] = []
    for item in value.split(","):
        clean_item: str = item.strip()
        if clean_item:
            try:
                inbound_ids.append(int(clean_item))
            except ValueError:
                raise ValueError(f"Error converting to int: XUI_INBOUND_ID {clean_item} is not a number")
    if not inbound_ids:
        raise ValueError("XUI_DEFAULT_INBOUND_IDS cannot be empty")
    return inbound_ids

def _parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Error converting to int: {value.strip()} is not a number")

def _parse_bool(value: str) -> bool:
    normalized: str = value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"Cannot convert {value!r} to bool")

@lru_cache
def get_settings() -> Settings:
    return Settings(
        bot_token=_get_required_env(key="BOT_TOKEN"),
        xui_base_url=_get_required_env(key="XUI_BASE_URL"),
        xui_web_base_path=_get_required_env(key="XUI_WEB_BASE_PATH"),
        xui_api_token=_get_required_env(key="XUI_API_TOKEN"),
        xui_subscription_base_url=_get_required_env(key="XUI_SUBSCRIPTION_BASE_URL"),
        xui_subscription_path=_get_required_env(key="XUI_SUBSCRIPTION_PATH"),
        xui_default_inbound_ids=_parse_list_of_int(value=_get_required_env(key="XUI_DEFAULT_INBOUND_IDS")),
        xui_default_limit_ip=_parse_int(value=_get_required_env(key="XUI_DEFAULT_LIMIT_IP")),
        xui_default_total_gb=_parse_int(value=_get_required_env(key="XUI_DEFAULT_TOTAL_GB")),
        database_url=_get_required_env(key="DATABASE_URL"),
        tg_support_username=_get_required_env(key="TG_SUPPORT_USERNAME"),
        tg_support_url=_get_required_env(key="TG_SUPPORT_URL"),
        yookassa_shop_id=_get_required_env(key="YOOKASSA_SHOP_ID"),
        yookassa_secret_key=_get_required_env(key="YOOKASSA_SECRET_KEY"),
        yookassa_return_url=_get_required_env(key="YOOKASSA_RETURN_URL"),
        yookassa_webhook_secret=_get_required_env(key="YOOKASSA_WEBHOOK_SECRET"),
        yookassa_webhook_host=_get_required_env(key="YOOKASSA_WEBHOOK_HOST"),
        yookassa_webhook_port=_parse_int(value=_get_required_env(key="YOOKASSA_WEBHOOK_PORT")),
        yookassa_allow_test_payments=_parse_bool(value=_get_required_env(key="YOOKASSA_ALLOW_TEST_PAYMENTS")),
    )
