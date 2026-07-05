from aiogram import Router, F

from aiogram.types import CallbackQuery
from typing import LiteralString
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup

from app.keyboards.common import get_back_to_main_menu_inline_keyboard
from app.keyboards.tariffs import get_tariffs_inline_keyboard


router = Router()


@router.callback_query(F.data == "connect_vpn")
async def callback_connect_vpn(callback: CallbackQuery) -> None:
    connect_vpn_message: LiteralString = (
        f"📆 Выбирите тариф\n"
    )

    tariffs_kd: InlineKeyboardMarkup = get_tariffs_inline_keyboard()
    back_to_main_kd: InlineKeyboardMarkup = get_back_to_main_menu_inline_keyboard()

    inline_kd = InlineKeyboardMarkup(
        inline_keyboard=tariffs_kd.inline_keyboard + back_to_main_kd.inline_keyboard
    )

    await callback.message.edit_text(text=connect_vpn_message, reply_markup=inline_kd)
