from typing import Tuple

from sqlalchemy import Result, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        result: Result[Tuple[User]] = await self.session.execute(
            statement=select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def upsert_user(
            self,
            *,
            telegram_id: int,
            username: str | None,
            first_name: str | None,
            last_name: str | None,
            language_code: str | None,
            is_bot: bool,
    ) -> User:
        values = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language_code": language_code,
            "is_bot": is_bot,
        }

        stmt = insert(table=User).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[User.telegram_id],
            set_={**values, "updated_at": func.now()},
        ).returning(User)

        result: Result[Tuple[User]] = await self.session.execute(statement=stmt)
        return result.scalar_one()
