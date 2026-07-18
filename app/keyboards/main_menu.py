from app.config import get_settings

from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


SUPPORT_URL: str = get_settings().tg_support_url


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
