from dataclasses import dataclass

from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


@dataclass(slots=True)
class Database:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

    async def close(self) -> None:
        await self.engine.dispose()


def create_database(database_url: str) -> Database:
    engine: AsyncEngine = create_async_engine(
        url=database_url,
        echo=False,
        pool_pre_ping=True,
    )

    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return Database(
        engine=engine,
        session_factory=session_factory,
    )
