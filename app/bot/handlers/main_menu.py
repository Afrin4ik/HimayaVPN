from aiogram import Router, F

from aiogram.types import CallbackQuery

from app.config import Settings

from app.bot.keyboards.main_menu import get_main_menu_inline_keyboard
from app.bot.presenters.main_menu import render_main_menu


router = Router()


@router.callback_query(F.data == "back_to_main_menu")
async def callback_back_to_main_menu(
    callback: CallbackQuery,
    settings: Settings
) -> None:
    await callback.answer()

    main_message: str = render_main_menu(user=callback.from_user)

    await callback.message.edit_text(
        text=main_message,
        reply_markup=get_main_menu_inline_keyboard(support_url=settings.tg_support_url)
    )
