from typing import Tuple
from datetime import datetime

from sqlalchemy import Result, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    VpnKey,
    VPN_KEY_CREATING,
    VPN_KEY_ACTIVE,
    VPN_KEY_FAILED,
    VPN_KEY_DISABLED,
    VPN_KEY_RENEWING,
)

class VpnKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session

    async def get_vpn_key_by_user_id(self, user_id: int) -> VpnKey | None:
        result: Result[Tuple[VpnKey]] = await self.session.execute(
            statement=select(VpnKey)
            .options(selectinload(VpnKey.tariff))
            .where(VpnKey.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all_xui_emails(self) -> set[str]:
        result: Result[Tuple[str | None]] = await self.session.execute(
            statement=select(VpnKey.xui_email).where(
                VpnKey.xui_email.is_not(None)
            )
        )
        return set(email for email in result.scalars().all() if email is not None)

    async def create_placeholder(
            self,
            *,
            user_id: int,
            tariff_id: int,
    ) -> VpnKey:
        key = VpnKey(
            user_id=user_id,
            tariff_id=tariff_id,
            status=VPN_KEY_CREATING,
            inbound_ids=[],
        )
        self.session.add(key)
        await self.session.flush()
        return key

    async def activate(
            self,
            *,
            vpn_key_id: int,
            xui_email: str,
            xui_uuid: str,
            xui_sub_id: str,
            inbound_ids: list[int],
            subscription_url: str,
            expires_at: datetime,
    ) -> VpnKey:
        stmt = (
            update(table=VpnKey)
            .where(VpnKey.id == vpn_key_id)
            .values(
                status=VPN_KEY_ACTIVE,
                xui_email=xui_email,
                xui_uuid=xui_uuid,
                xui_sub_id=xui_sub_id,
                inbound_ids=inbound_ids,
                subscription_url=subscription_url,
                expires_at=expires_at,
                error_message=None,
                updated_at=func.now(),
            )
            .returning(VpnKey)
        )
        result: Result[Tuple[VpnKey]] = await self.session.execute(statement=stmt)
        return result.scalar_one()

    async def set_creating(
            self,
            *,
            vpn_key_id: int,
            tariff_id: int,
    ) -> VpnKey:
        stmt = (
            update(table=VpnKey)
            .where(VpnKey.id == vpn_key_id)
            .values(
                tariff_id=tariff_id,
                status=VPN_KEY_CREATING,
                error_message=None,
                updated_at=func.now(),
            )
            .returning(VpnKey)
        )
        result: Result[Tuple[VpnKey]] = await self.session.execute(statement=stmt)
        return result.scalar_one()

    async def claim_stale_creating(
            self,
            *,
            vpn_key_id: int,
            tariff_id: int,
            stale_before: datetime,
    ) -> VpnKey | None:
        stmt = (
            update(table=VpnKey)
            .where(
                VpnKey.id == vpn_key_id,
                VpnKey.status == VPN_KEY_CREATING,
                VpnKey.updated_at <= stale_before,
            )
            .values(
                tariff_id=tariff_id,
                status=VPN_KEY_CREATING,
                xui_email=None,
                xui_uuid=None,
                xui_sub_id=None,
                inbound_ids=[],
                subscription_url=None,
                expires_at=None,
                error_message=None,
                updated_at=func.now(),
            )
            .returning(VpnKey)
        )

        result: Result[Tuple[VpnKey]] = await self.session.execute(statement=stmt)

        return result.scalar_one_or_none()

    async def begin_renewal(
            self,
            *,
            vpn_key_id: int,
            pending_tariff_id: int,
            pending_expires_at: datetime,
    ) -> VpnKey | None:
        stmt = (
            update(table=VpnKey)
            .where(
                VpnKey.id == vpn_key_id,
                VpnKey.status.in_([VPN_KEY_ACTIVE, VPN_KEY_DISABLED]),
            )
            .values(
                status=VPN_KEY_RENEWING,
                pending_tariff_id=pending_tariff_id,
                pending_expires_at=pending_expires_at,
                error_message=None,
                updated_at=func.now(),
            )
            .returning(VpnKey)
        )

        result: Result[Tuple[VpnKey]] = await self.session.execute(statement=stmt)

        return result.scalar_one_or_none()

    async def get_stale_renewing_ids(
            self,
            *,
            stale_before: datetime,
            limit: int = 50,
    ) -> list[int]:
        if limit <= 0:
            raise ValueError("limit must be positive")

        result: Result[Tuple[int]] = await self.session.execute(
            statement=select(VpnKey.id)
            .where(
                VpnKey.status == VPN_KEY_RENEWING,
                VpnKey.updated_at <= stale_before,
            )
            .order_by(VpnKey.updated_at.asc())
            .limit(limit=limit)
        )

        return list(result.scalars().all())

    async def claim_stale_renewing(
            self,
            *,
            vpn_key_id: int,
            stale_before: datetime,
    ) -> VpnKey | None:
        stmt = (
            update(table=VpnKey)
            .where(
                VpnKey.id == vpn_key_id,
                VpnKey.status == VPN_KEY_RENEWING,
                VpnKey.updated_at <= stale_before,
            )
            .values(
                updated_at=func.now(),
            )
            .returning(VpnKey)
        )

        result: Result[Tuple[VpnKey]] = await self.session.execute(statement=stmt)

        return result.scalar_one_or_none()

    async def complete_renewal(
            self,
            *,
            vpn_key_id: int,
            tariff_id: int,
            expires_at: datetime,
    ) -> VpnKey:
        stmt = (
            update(table=VpnKey)
            .where(
                VpnKey.id == vpn_key_id,
                VpnKey.status == VPN_KEY_RENEWING,
            )
            .values(
                status=VPN_KEY_ACTIVE,
                tariff_id=tariff_id,
                expires_at=expires_at,
                pending_tariff_id=None,
                pending_expires_at=None,
                error_message=None,
                updated_at=func.now(),
            )
            .returning(VpnKey)
        )

        result: Result[Tuple[VpnKey]] = await self.session.execute(statement=stmt)

        return result.scalar_one()

    async def record_renewal_error(
            self,
            *,
            vpn_key_id: int,
            error_message: str,
    ) -> None:
        await self.session.execute(
            statement=update(table=VpnKey)
            .where(
                VpnKey.id == vpn_key_id,
                VpnKey.status == VPN_KEY_RENEWING,
            )
            .values(
                error_message=error_message[:2000],
                updated_at=func.now(),
            )
        )

    async def disable_expired_active_keys(
            self,
            *,
            expired_before: datetime,
    ) -> list[int]:
        stmt = (
            update(table=VpnKey)
            .where(
                VpnKey.status == VPN_KEY_ACTIVE,
                VpnKey.expires_at.is_not(None),
                VpnKey.expires_at <= expired_before,
            )
            .values(
                status=VPN_KEY_DISABLED,
                updated_at=func.now(),
            )
            .returning(VpnKey.id)
        )

        result: Result[Tuple[int]] = await self.session.execute(statement=stmt)

        return list(result.scalars().all())

    async def mark_failed(
            self,
            *,
            vpn_key_id: int,
            error_message: str,
    ) -> None:
        await self.session.execute(
            statement=update(table=VpnKey)
            .where(
                VpnKey.id == vpn_key_id,
                VpnKey.status == VPN_KEY_CREATING,
            )
            .values(
                status=VPN_KEY_FAILED,
                error_message=error_message[:2000],
                updated_at=func.now(),
            )
        )
