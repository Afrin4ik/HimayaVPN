from aiogram import Router, F

from aiogram.types import CallbackQuery
from aiogram.types.user import User

from app.keyboards.common import get_back_to_main_menu_inline_keyboard


router = Router()


@router.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery) -> None:
    user: User = callback.from_user

    if user.username:
        usrname: str = f"@{user.username}"
    else:
        usrname = "-"

    profile_message: str = (
        f"👤 Профиль\n\n"
        f"ID: {user.id}\n"
        f"Имя пользователя: {usrname}\n"
        f"Полное имя: {user.full_name}\n\n"
        f"Тариф: ...\n"
        f"Действует до: ...\n"
    )

    await callback.message.edit_text(text=profile_message, reply_markup=get_back_to_main_menu_inline_keyboard())
