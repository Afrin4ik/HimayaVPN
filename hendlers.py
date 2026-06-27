from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import CommandStart
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.types.user import User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from typing import LiteralString

router = Router()


def get_main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="👤 Профиль",
        callback_data="profile"
    )

    builder.button(
        text="📲 Подключить VPN",
        callback_data="connect_vpn"
    )

    builder.button(
        text="👨‍💻 Тех. поддержка",
        url="https://t.me/miolerr"
    )

    builder.adjust(1, 1, 1)

    return builder.as_markup()


def get_back_to_main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🔙 Назад",
        callback_data="back_to_main_menu"
    )

    builder.adjust(1)

    return builder.as_markup()


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
        f"Полное имя: {user.full_name}\n"
        f"Имя пользователя: {usrname}\n\n"
        f"Баланс: ...\n\n"
        f"Тариф: ...\n"
        f"Действует до: ...\n"
    )

    await callback.message.edit_text(text=profile_message, reply_markup=get_back_to_main_menu_inline_keyboard())


@router.callback_query(F.data == "connect_vpn")
async def callback_connect_vpn(callback: CallbackQuery) -> None:
    connect_vpn_message: LiteralString = (
        f"Выбирите тариф\n"
        f"... (инлайн кнопки с тарифами)"
    )

    await callback.message.edit_text(text=connect_vpn_message, reply_markup=get_back_to_main_menu_inline_keyboard())


@router.callback_query(F.data == "back_to_main_menu")
async def callback_back_to_main_menu(callback: CallbackQuery) -> None:
    main_message: LiteralString = (
        f"Для продолжения работы выбирете действие ниже"
    )
    await callback.message.edit_text(text=main_message, reply_markup=get_main_menu_inline_keyboard())


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user: User | None = message.from_user

    if user.username:
        greeting: str = f"👋 Привет, @{user.username}!"
    else:
        greeting: str = f"👋 Привет, {user.first_name}!"

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


@router.message()
async def cmd_help(message: Message) -> None:
    wrong_message: LiteralString = (
        f"⚠️ Если у вас возникли какие-либо сложности или вопросы, пишите в тех. поддержку: @miolerr"
    )

    await message.answer(text=wrong_message, reply_markup=get_back_to_main_menu_inline_keyboard())
