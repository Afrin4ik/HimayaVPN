from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.database.models import Tariff
from app.bot.keyboards.common import get_back_to_main_menu_inline_keyboard


class TariffCallback(CallbackData, prefix="tariff"):
    tariff_code: str


def get_tariffs_inline_keyboard(
        *,
        tariffs: list[Tariff],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for tariff in tariffs:
        builder.button(
            text=f"{tariff.title} - {tariff.price_rub}₽",
            callback_data=TariffCallback(
                tariff_code=tariff.code
            ),
        )

    builder.adjust(1)

    back_keyboard: InlineKeyboardMarkup = get_back_to_main_menu_inline_keyboard()
    back_builder: InlineKeyboardBuilder = InlineKeyboardBuilder.from_markup(markup=back_keyboard)

    builder.attach(builder=back_builder)

    return builder.as_markup()
