import os
from dotenv import load_dotenv

from aiogram import Router

from aiogram.types import Message

from app.keyboards.common import get_back_to_main_menu_inline_keyboard


load_dotenv()
SUPPORT_USERNAME: str | None = os.getenv(key="SUPPORT_TG_USERNAME")


router = Router()


@router.message()
async def cmd_help(message: Message) -> None:
    wrong_message: str = (
        f"⚠️ Введено некорректное сообщение\n\n"
        f"Если у вас возникли какие-либо сложности или вопросы, напишите в тех. поддержку: {SUPPORT_USERNAME}"
    )

    await message.answer(text=wrong_message, reply_markup=get_back_to_main_menu_inline_keyboard())
