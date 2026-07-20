from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.database.repositories.user_repository import UserRepository

from app.services.dto import TelegramUserData


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session
        self.user_repository = UserRepository(session=session)

    async def sync_telegram_user(
            self,
            *,
            telegram_user: TelegramUserData,
        ) -> User:
        user: User = await self.user_repository.upsert_user(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            language_code=telegram_user.language_code,
            is_bot=telegram_user.is_bot,
        )

        await self.session.flush()

        return user

    async def consume_trial_if_available(
            self,
            *,
            user_id: int,
    ) -> bool:
        return await self.user_repository.consume_trial_if_available(user_id=user_id)
