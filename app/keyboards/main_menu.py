import os
from dotenv import load_dotenv

from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


load_dotenv()
SUPPORT_URL: str | None = os.getenv(key="SUPPORT_TG_URL")


def get_main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="👤 Профиль",
        callback_data="profile"
    )

    builder.button(
        text="📲 Подключить VPN",
        callback_data="connect_vpn"
    )

    builder.button(
        text="🛠️ Тех. поддержка",
        url=SUPPORT_URL
    )

    builder.adjust(1, 1, 1)

    return builder.as_markup()
