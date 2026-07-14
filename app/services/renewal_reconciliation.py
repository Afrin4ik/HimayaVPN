import asyncio
import logging

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.models import VpnKey
from app.integrations.xui import AsyncXUI, XUIConfig
from app.repositories.vpn_keys import VpnKeyRepository
from app.services.vpn_key_service import VpnKeyService, VPN_KEY_RENEWING_TIMEOUT


logger = logging.getLogger(__name__)


RECONCILIATION_INTERVAL_SECONDS = 30
RECONCILIATION_BATCH_SIZE = 50


async def reconcile_stale_renewals_once(
        *,
        session_factory: async_sessionmaker[AsyncSession],
        xui: AsyncXUI,
        xui_config: XUIConfig,
) -> None:
    stale_before: datetime = datetime.now(timezone.utc) - VPN_KEY_RENEWING_TIMEOUT

    async with session_factory() as session:
        vpn_key_repository = VpnKeyRepository(session=session)

        vpn_key_ids: list[int] = await vpn_key_repository.get_stale_renewing_ids(
            stale_before=stale_before,
            limit=RECONCILIATION_BATCH_SIZE,
        )

    for vpn_key_id in vpn_key_ids:
        async with session_factory() as session:
            vpn_key_service = VpnKeyService(
                session=session,
                xui=xui,
                xui_config=xui_config,
            )

            try:
                renewed_vpn_key: VpnKey | None = await vpn_key_service.resume_stale_renewal(
                    vpn_key_id=vpn_key_id,
                    stale_before=stale_before,
                )

                if renewed_vpn_key is None:
                    continue

                logger.info(
                    "Background renewal reconciliation completed (vpn_key_id=%s, expires_at=%s)",
                    renewed_vpn_key.id,
                    renewed_vpn_key.expires_at,
                )

            except asyncio.CancelledError:
                await session.rollback()
                raise

            except Exception:
                await session.rollback()

                logger.exception(
                    "Background renewal reconciliation failed (vpn_key_id=%s)",
                    vpn_key_id,
                )


async def run_renewal_reconciler(
        *,
        session_factory: async_sessionmaker[AsyncSession],
        xui: AsyncXUI,
        xui_config: XUIConfig,
) -> None:
    logger.info("VPN renewal reconciler started")

    try:
        while True:
            try:
                await reconcile_stale_renewals_once(
                    session_factory=session_factory,
                    xui=xui,
                    xui_config=xui_config,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception("VPN renewal reconciliation iteration failed")

            await asyncio.sleep(RECONCILIATION_INTERVAL_SECONDS)

    finally:
        logger.info("VPN renewal reconciler stopped")
