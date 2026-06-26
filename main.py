import os
from dotenv import load_dotenv

import asyncio
from aiogram import Bot, Dispatcher
from hendlers import router

load_dotenv()
TOKEN: str | None = os.getenv(key="BOT_TOKEN")


async def main() -> None:
    bot = Bot(token=TOKEN)

    dp = Dispatcher()
    dp.include_router(router=router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main=main())
