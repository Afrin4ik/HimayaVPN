import logging
import asyncio

from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from app.config import Settings, get_settings
from app.bot.router import build_router
from app.bot.middlewares.database import DatabaseSessionMiddleware
from app.database.connection import Database, create_database
from app.integrations.xui import AsyncXUI, XUIConfig
from app.integrations.xui.factory import build_xui_config
from app.integrations.yookassa import AsyncYooKassa

from app.http.yookassa_webhook import build_yookassa_http_app


logger = logging.getLogger(__name__)


async def main() -> None:
    settings: Settings = get_settings()

    database: Database = create_database(database_url=settings.database_url)

    xui_config: XUIConfig = build_xui_config(settings=settings)
    xui = AsyncXUI(config=xui_config)

    yookassa = AsyncYooKassa(
        shop_id=settings.yookassa_shop_id,
        secret_key=settings.yookassa_secret_key,
    )

    http_runner: web.AppRunner | None = None

    bot = Bot(token=settings.bot_token)

    try:
        await xui.start()
        await yookassa.start()

        http_app: web.Application = build_yookassa_http_app(
            session_factory=database.session_factory,
            yookassa=yookassa,
            settings=settings,
        )

        http_runner = web.AppRunner(
            app=http_app,
            access_log=None,
        )
        await http_runner.setup()

        http_site = web.TCPSite(
            runner=http_runner,
            host=settings.yookassa_webhook_host,
            port=settings.yookassa_webhook_port,
        )
        await http_site.start()

        logger.info(
            "YooKassa HTTP server started on %s:%s",
            settings.yookassa_webhook_host,
            settings.yookassa_webhook_port,
        )

        await bot.set_my_commands(
            commands=[
                BotCommand(
                    command="start",
                    description="Запустить бота",
                ),
            ]
        )

        await bot.delete_webhook(drop_pending_updates=True)

        dispatcher = Dispatcher()

        dispatcher["settings"] = settings
        dispatcher["xui_config"] = xui_config
        dispatcher["xui"] = xui
        dispatcher["yookassa"] = yookassa

        dispatcher.update.middleware(
            middleware=DatabaseSessionMiddleware(
                session_factory=database.session_factory,
            )
        )

        dispatcher.include_router(router=build_router())

        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
            close_bot_session=False,
        )

    finally:
        if http_runner is not None:
            await http_runner.cleanup()

        await bot.session.close()
        await yookassa.close()
        await xui.close()
        await database.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s,%(msecs)03d | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    asyncio.run(main=main())
