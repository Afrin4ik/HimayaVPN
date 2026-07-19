from aiogram import Router, F

from aiogram.types import CallbackQuery
from aiogram.types.user import User

from app.bot.keyboards.main_menu import get_main_menu_inline_keyboard

from app.config import Settings


router = Router()


@router.callback_query(F.data == "back_to_main_menu")
async def callback_back_to_main_menu(
    callback: CallbackQuery,
    settings: Settings
) -> None:
    await callback.answer()

    user: User = callback.from_user

    if user.username:
        greeting: str = f"👋 Привет, @{user.username}!"
    else:
        greeting: str = f"👋 Привет, {user.full_name}!"

    main_message: str = (
        f"{greeting}\n\n"
        f"👨‍💻 Для продолжения работы выберите действие ниже"
    )
    await callback.message.edit_text(
        text=main_message,
        reply_markup=get_main_menu_inline_keyboard(support_url=settings.tg_support_url)
    )
