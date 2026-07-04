import asyncio
from aiogram import Bot, Dispatcher

from app.config import Settings, get_settings
from app.handlers import router


async def main() -> None:
    settings: Settings = get_settings()

    bot = Bot(token=settings.bot_token)

    dp = Dispatcher()
    dp.include_router(router=router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main=main())
