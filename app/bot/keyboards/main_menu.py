from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_inline_keyboard(
    *,
    support_url: str,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="👤 Профиль",
        callback_data="profile",
    )

    builder.button(
        text="📲 Подключить VPN",
        callback_data="connect_vpn",
    )

    builder.button(
        text="🛠️ Тех. поддержка",
        url=support_url,
    )

    builder.adjust(1, 1, 1)

    return builder.as_markup()
