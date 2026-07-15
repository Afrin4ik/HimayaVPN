import asyncio

from sqlalchemy.dialects.postgresql import insert

from app.database.connection import async_session_factory
from app.database.models import Tariff

TARIFFS = [
    {
        "code": "trial_3_days",
        "title": "Пробный период — 3 дня",
        "price_rub": 0,
        "duration_days": 3,
        "limit_ip": 1,
        "total_gb": 30,
        "is_active": True,
    },
    {
        "code": "tariff_1",
        "title": "1 месяц",
        "price_rub": 100,
        "duration_days": 30,
        "limit_ip": 1,
        "total_gb": 300,
        "is_active": True,
    },
    {
        "code": "tariff_3",
        "title": "3 месяца",
        "price_rub": 250,
        "duration_days": 90,
        "limit_ip": 1,
        "total_gb": 900,
        "is_active": True,
    },
    {
        "code": "tariff_6",
        "title": "6 месяцев",
        "price_rub": 500,
        "duration_days": 180,
        "limit_ip": 1,
        "total_gb": 1800,
        "is_active": True,
    },
    {
        "code": "tariff_12",
        "title": "12 месяцев",
        "price_rub": 1000,
        "duration_days": 360,
        "limit_ip": 1,
        "total_gb": 3600,
        "is_active": True,
    },
]


async def main():
    async with async_session_factory() as session:
        for tariff in TARIFFS:
            stmt = insert(table=Tariff).values(**tariff)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Tariff.code],
                set_=tariff,
            )
            await session.execute(statement=stmt)

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main=main())
