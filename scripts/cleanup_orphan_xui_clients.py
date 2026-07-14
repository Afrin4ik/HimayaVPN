import argparse
import asyncio
import logging
import time

from typing import Any

from app.config import Settings, get_settings
from app.database.connection import async_session_factory, close_database
from app.integrations.xui import AsyncXUI, XUIConfig
from app.repositories.vpn_keys import VpnKeyRepository


logger = logging.getLogger(__name__)

HIMAYA_VPN_CLIENT_PREFIX = "tg_"
DEFAULT_GRACE_PERIOD_SECONDS = 10 * 60


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find 3x-ui clients that are absent from PostgreSQL database"
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete orphan clients",
    )

    parser.add_argument(
        "--grace-seconds",
        type=int,
        default=DEFAULT_GRACE_PERIOD_SECONDS,
        help="Do not delete clients younger than this value",
    )

    return parser.parse_args()


def build_xui_config(settings: Settings) -> XUIConfig:
    return XUIConfig(
        base_url=settings.xui_base_url,
        web_base_path=settings.xui_web_base_path,
        api_token=settings.xui_api_token,
        subscription_base_url=settings.xui_subscription_base_url,
        subscription_path=settings.xui_subscription_path,
        default_inbound_ids=settings.xui_default_inbound_ids,
        default_limit_ip=settings.xui_default_limit_ip,
        default_total_gb=settings.xui_default_total_gb,
    )


def get_client_created_at_ms(client: dict[str, Any]) -> int | None:
    raw_value = client.get("createdAt")

    if raw_value is None:
        raw_value = client.get("created_at")

    if isinstance(raw_value, bool):
        return None

    if isinstance(raw_value, int):
        return raw_value

    if isinstance(raw_value, float):
        return int(raw_value)

    if isinstance(raw_value, str):
        try:
            return int(raw_value)
        except ValueError:
            return None

    return None


async def get_database_xui_emails() -> set[str]:
    async with async_session_factory() as session:
        vpn_key_repository = VpnKeyRepository(session=session)
        return await vpn_key_repository.get_all_xui_emails()


async def cleanup_orphans(
        *,
        apply_changes: bool,
        grace_period_seconds: int,
) -> None:
    if grace_period_seconds < 0:
        raise ValueError("grace_period_seconds cannot be negative")

    settings: Settings = get_settings()
    xui_config: XUIConfig = build_xui_config(settings=settings)

    database_emails: set[str] = await get_database_xui_emails()

    now_ms = int(time.time() * 1000)
    grace_period_ms = grace_period_seconds * 1000

    orphan_count = 0
    deleted_count = 0
    skipped_count = 0

    async with AsyncXUI(config=xui_config) as xui:
        xui_clients_list: list[dict[str, Any]] = await xui.get_clients_list()

        for xui_client in xui_clients_list:
            xui_client_email = xui_client.get("email")

            if not isinstance(xui_client_email, str):
                continue
            if not xui_client_email.startswith(HIMAYA_VPN_CLIENT_PREFIX):
                continue
            if xui_client_email in database_emails:
                continue

            created_at_ms = get_client_created_at_ms(client=xui_client)
            if created_at_ms is None:
                skipped_count += 1

                logger.warning(
                    "Skipping unknown client age (email: %s)",
                    xui_client_email,
                )
                continue

            age_ms = now_ms - created_at_ms
            if age_ms < grace_period_ms:
                skipped_count += 1

                logger.info(
                    "Skipping recent unmatched client (email: %s, age: %ss)",
                    xui_client_email,
                    max(age_ms // 1000, 0),
                )
                continue

            orphan_count += 1

            if not apply_changes:
                logger.warning(
                    "DRY RUN: orphan client found (email: %s, age: %ss)",
                    xui_client_email,
                    max(age_ms // 1000, 0),
                )
                continue

            try:
                await xui.delete_client(
                    email=xui_client_email,
                    keep_traffic=False,
                )

                deleted_count += 1

                logger.warning(
                    "Deleted orphan XUI client (email: %s)",
                    xui_client_email,
                )

            except Exception:
                logger.exception(
                    "Cannot delete orphan XUI client (email: %s)",
                    xui_client_email,
                )

    logger.info(
        "Reconciliation finished: "
        "database_emails_count=%s, "
        "xui_clients_count=%s, "
        "orphan_count=%s, "
        "deleted_count=%s, "
        "skipped_count=%s, "
        "apply_changes=%s",
        len(database_emails),
        len(xui_clients_list),
        orphan_count,
        deleted_count,
        skipped_count,
        apply_changes,
    )


async def main() -> None:
    arguments: argparse.Namespace = parse_arguments()

    try:
        await cleanup_orphans(
            apply_changes=arguments.apply,
            grace_period_seconds=arguments.grace_seconds,
        )
    finally:
        await close_database()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s,%(msecs)03d | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    asyncio.run(main=main())
