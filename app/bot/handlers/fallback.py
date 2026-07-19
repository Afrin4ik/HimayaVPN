from aiogram import Router

from aiogram.types import Message

from app.bot.keyboards.common import get_back_to_main_menu_inline_keyboard

from app.config import get_settings


SUPPORT_USERNAME: str = get_settings().tg_support_username


router = Router()


@router.message()
async def fallback_message(message: Message) -> None:
    wrong_message: str = (
        f"⚠️ Введено некорректное сообщение\n\n"
        f"Если у вас возникли какие-либо сложности или вопросы, напишите в тех. поддержку: {SUPPORT_USERNAME}"
    )

    await message.answer(text=wrong_message, reply_markup=get_back_to_main_menu_inline_keyboard())
