from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_tariffs_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="1 месяц - 100₽",
        callback_data="tariff_1"
    )

    builder.button(
        text="3 месяца - 250₽",
        callback_data="tariff_3"
    )

    builder.button(
        text="6 месяцев - 500₽",
        callback_data="tariff_6"
    )

    builder.button(
        text="12 месяцев - 1000₽",
        callback_data="tariff_12"
    )

    builder.adjust(1, 1, 1, 1)

    return builder.as_markup()
