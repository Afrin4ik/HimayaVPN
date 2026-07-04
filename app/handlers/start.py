from aiogram import Router, F
from aiogram.filters.command import CommandStart

from aiogram.types import Message, CallbackQuery
from aiogram.types.user import User
from typing import LiteralString

from app.keyboards.main_menu import get_main_menu_inline_keyboard


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user: User | None = message.from_user

    if user:
        if user.username:
            greeting: str = f"👋 Привет, @{user.username}!"
        else:
            greeting: str = f"👋 Привет, {user.first_name}!"
    else:
        greeting: str = "👋 Привет!"

    welcome_message: LiteralString = (
        f"{greeting}\n\n"
        f"HimayaVPN - это лучший выбор из всех VPN на рынке🥇\n"
        f"Наши приоритеты - безопасность, скорость, стабильность🛡"
    )
    await message.answer(text=welcome_message)

    main_message: LiteralString = (
        f"Для продолжения работы выбирете действие ниже"
    )
    await message.answer(text=main_message, reply_markup=get_main_menu_inline_keyboard())


@router.callback_query(F.data == "back_to_main_menu")
async def callback_back_to_main_menu(callback: CallbackQuery) -> None:
    main_message: LiteralString = (
        f"Для продолжения работы выбирете действие ниже"
    )
    await callback.message.edit_text(text=main_message, reply_markup=get_main_menu_inline_keyboard())
