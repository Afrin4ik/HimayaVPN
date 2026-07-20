import asyncio
from sqlalchemy import text
from app.config import Settings, get_settings
from app.database.connection import Database, create_database

async def main():
    settings: Settings = get_settings()

    database: Database = create_database(database_url=settings.database_url)

    try:
        async with database.session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar_one()
            print(f"Сессия работает. Результат: {value}")

    except Exception as error:
        print(f"Ошибка подключения: {error}")
        raise

    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
