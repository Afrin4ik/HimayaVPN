import logging

import asyncio

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.vpn_key_repository import VpnKeyRepository


logger = logging.getLogger(__name__)


EXPIRATION_RECONCILIATION_INTERVAL_SECONDS = 30


async def disable_expired_vpn_keys_once(
        *,
        session_factory: async_sessionmaker[AsyncSession],
) -> None:
    expired_before: datetime = datetime.now(timezone.utc)

    async with session_factory() as session:
        vpn_key_repository = VpnKeyRepository(session=session)

        try:
            disabled_vpn_key_ids: list[int] = await vpn_key_repository.disable_expired_active_keys(expired_before=expired_before)
            await session.commit()

        except asyncio.CancelledError:
            await session.rollback()
            raise

        except Exception:
            await session.rollback()
            raise

    if disabled_vpn_key_ids:
        logger.info(
            "Expired VPN keys disabled (count=%s, vpn_key_ids=%s, expired_before=%s)",
            len(disabled_vpn_key_ids),
            disabled_vpn_key_ids,
            expired_before,
        )


async def run_expiration_reconciler(
        *,
        session_factory: async_sessionmaker[AsyncSession],
) -> None:
    logger.info("VPN expiration reconciler started")

    try:
        while True:
            try:
                await disable_expired_vpn_keys_once(session_factory=session_factory)

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception("VPN expiration reconciliation iteration failed")

            await asyncio.sleep(EXPIRATION_RECONCILIATION_INTERVAL_SECONDS)

    finally:
        logger.info("VPN expiration reconciler stopped")
