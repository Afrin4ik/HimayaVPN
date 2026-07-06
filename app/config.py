import os
from dotenv import load_dotenv

from dataclasses import dataclass


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    xui_base_url: str
    xui_web_base_path: str
    xui_api_token: str
    database_url: str


def get_settings() -> Settings:
    bot_token: str | None = os.getenv(key="BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")

    xui_base_url: str | None = os.getenv(key="XUI_BASE_URL")
    if not xui_base_url:
        raise RuntimeError("XUI_BASE_URL is not set")

    xui_web_base_path: str | None = os.getenv(key="XUI_WEB_BASE_PATH")
    if not xui_web_base_path:
        raise RuntimeError("XUI_WEB_BASE_PATH is not set")

    xui_api_token: str | None = os.getenv(key="XUI_API_TOKEN")
    if not xui_api_token:
        raise RuntimeError("XUI_API_TOKEN is not set")

    database_url: str | None = os.getenv(key="DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    return Settings(
        bot_token=bot_token,
        xui_base_url=xui_base_url,
        xui_web_base_path=xui_web_base_path,
        xui_api_token=xui_api_token,
        database_url=database_url
    )
