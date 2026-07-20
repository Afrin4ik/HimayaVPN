import logging
import asyncio

from app.config import Settings, get_settings
from app.database.connection import Database, create_database
from app.integrations.xui import AsyncXUI, XUIConfig
from app.integrations.xui.factory import build_xui_config

from app.workers.expiration_reconciler import run_expiration_reconciler
from app.workers.renewal_reconciler import run_renewal_reconciler


async def main() -> None:
    settings: Settings = get_settings()

    database: Database = create_database(database_url=settings.database_url)

    xui_config: XUIConfig = build_xui_config(settings=settings)
    xui = AsyncXUI(config=xui_config)

    try:
        await xui.start()

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

    finally:
        await xui.close()
        await database.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s,%(msecs)03d | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    asyncio.run(main=main())
