from typing import Tuple

from sqlalchemy import Result, func, select, update
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

    async def consume_trial_if_available(
            self,
            *,
            user_id: int,
    ) -> bool:
        stmt = (
            update(table=User)
            .where(
                User.id == user_id,
                User.trial_available.is_(True),
            )
            .values(
                trial_available=False,
                updated_at=func.now(),
            )
            .returning(User.id)
        )

        result: Result[Tuple[int]] = await self.session.execute(statement=stmt)
        claimed_user_id: int | None = result.scalar_one_or_none()

        return claimed_user_id is not None
