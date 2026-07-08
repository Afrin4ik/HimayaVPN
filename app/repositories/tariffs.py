from typing import Tuple

from sqlalchemy import Result, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tariff


class TariffRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session

    async def get_active_tariff_by_code(self, code: str) -> Tariff | None:
        result: Result[Tuple[Tariff]] = await self.session.execute(
            statement=select(Tariff).where(
                Tariff.code == code,
                Tariff.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
