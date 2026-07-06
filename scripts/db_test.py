import asyncio
from sqlalchemy import text
from app.database.connection import get_session

async def main():
    try:
        async for session in get_session():
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            print(f"Сессия работает. Результат: {value}")
            break
    except Exception as e:
        print(f"Ошибка подключения: {e}")

if __name__ == "__main__":
    asyncio.run(main())
