import logging

import asyncio

from aiogram import Bot, Dispatcher

from app.config import Settings, get_settings
from app.handlers import router
from app.database.connection import async_session_factory, close_database
from app.integrations.xui import AsyncXUI, XUIConfig
from app.middlewares.database import DatabaseSessionMiddleware


async def main() -> None:
    settings: Settings = get_settings()

    bot = Bot(token=settings.bot_token)

    xui_config = XUIConfig(
        base_url=settings.xui_base_url,
        web_base_path=settings.xui_web_base_path,
        api_token=settings.xui_api_token,
        subscription_base_url=settings.xui_subscription_base_url,
        subscription_path=settings.xui_subscription_path,
        default_inbound_ids=settings.xui_default_inbound_ids,
        default_limit_ip=settings.xui_default_limit_ip,
        default_total_gb=settings.xui_default_total_gb,
    )
    xui = AsyncXUI(config=xui_config)
    await xui.start()

    dp = Dispatcher()
    dp["xui_config"] = xui_config
    dp["xui"] = xui
    dp.update.middleware(middleware=DatabaseSessionMiddleware(session_factory=async_session_factory))
    dp.include_router(router=router)

    try:
        await dp.start_polling(bot)
    finally:
        await xui.close()
        await close_database()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s,%(msecs)03d | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(main=main())
