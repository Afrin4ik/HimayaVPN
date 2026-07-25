from aiogram.filters.callback_data import CallbackData
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.keyboards.common import get_back_to_main_menu_inline_keyboard


class PaymentStatusCallback(CallbackData, prefix="payment"):
    order_id: int


def get_payment_inline_keyboard(
        *,
        confirmation_url: str,
        order_id: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="💳 Перейти к оплате",
        url=confirmation_url,
    )

    builder.button(
        text="🧾 Проверить оплату",
        callback_data=PaymentStatusCallback(
            order_id=order_id,
        ),
    )

    builder.adjust(1)

    back_keyboard: InlineKeyboardMarkup = get_back_to_main_menu_inline_keyboard()
    back_builder: InlineKeyboardBuilder = InlineKeyboardBuilder.from_markup(markup=back_keyboard)

    builder.attach(builder=back_builder)

    return builder.as_markup()
