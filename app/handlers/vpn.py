from aiogram import Router, F

from aiogram.types import CallbackQuery
from typing import LiteralString

from app.keyboards.common import get_back_to_main_menu_inline_keyboard


router = Router()


@router.callback_query(F.data == "connect_vpn")
async def callback_connect_vpn(callback: CallbackQuery) -> None:
    connect_vpn_message: LiteralString = (
        f"Выбирите тариф\n"
        f"... (инлайн кнопки с тарифами)"
    )

    await callback.message.edit_text(text=connect_vpn_message, reply_markup=get_back_to_main_menu_inline_keyboard())
