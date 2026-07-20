from aiogram.types import User

from app.services.dto import TelegramUserData


def map_telegram_user(user: User) -> TelegramUserData:
    return TelegramUserData(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
        is_bot=user.is_bot,
    )
