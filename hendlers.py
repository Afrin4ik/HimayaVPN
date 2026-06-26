from aiogram import Router
from aiogram.types import Message
from aiogram.filters.command import CommandStart
from aiogram.types.user import User

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user: User | None = message.from_user

    if user.username:
        await message.answer(text=f"Привет, @{user.username}!")
    else:
        await message.answer(text=f"Привет, {user.first_name}!")
