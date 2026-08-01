import logging
import asyncio

from aiogram import Bot

from app.config import Settings, get_settings
from app.database.connection import Database, create_database
from app.integrations.xui import AsyncXUI, XUIConfig
from app.integrations.xui.factory import build_xui_config
from app.integrations.yookassa import AsyncYooKassa

from app.workers.expiration_reconciler import run_expiration_reconciler
from app.workers.renewal_reconciler import run_renewal_reconciler
from app.workers.payment_reconciler import run_payment_status_reconciler, run_paid_order_reconciler


async def main() -> None:
    settings: Settings = get_settings()

    database: Database = create_database(database_url=settings.database_url)

    xui_config: XUIConfig = build_xui_config(settings=settings)
    xui = AsyncXUI(config=xui_config)

    yookassa = AsyncYooKassa(
        shop_id=settings.yookassa_shop_id,
        secret_key=settings.yookassa_secret_key,
    )

    bot = Bot(token=settings.bot_token)

    try:
        await xui.start()
        await yookassa.start()

        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(
                coro=run_renewal_reconciler(
                    session_factory=database.session_factory,
                    xui=xui,
                    xui_config=xui_config,
                ),
                name="vpn-renewal-reconciler",
            )

            task_group.create_task(
                coro=run_expiration_reconciler(
                    session_factory=database.session_factory,
                ),
                name="vpn-expiration-reconciler",
            )

            task_group.create_task(
                coro=run_payment_status_reconciler(
                    session_factory=database.session_factory,
                    yookassa=yookassa,
                    settings=settings,
                ),
                name="payment-status-reconciler",
            )

            task_group.create_task(
                coro=run_paid_order_reconciler(
                    session_factory=database.session_factory,
                    xui=xui,
                    xui_config=xui_config,
                    bot=bot,
                ),
                name="paid-order-reconciler",
            )

    finally:
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
