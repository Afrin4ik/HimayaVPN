from datetime import datetime
from typing import Tuple

from sqlalchemy import Result, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import VpnKey, VPN_KEY_ACTIVE, VPN_KEY_DISABLED, VPN_KEY_DELETED


class VpnKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session

    async def get_vpn_key_by_user_id(self, user_id: int) -> VpnKey | None:
        result: Result[Tuple[VpnKey]] = await self.session.execute(
            statement=select(VpnKey)
            .options(selectinload(VpnKey.user))
            .where(VpnKey.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_vpn_key_entry(
            self,
            *,
            user_id: int,
            xui_email: str,
            xui_uuid: str,
            xui_sub_id: str,
            inbound_ids: list[int],
            subscription_url: str,
            expires_at: datetime,
    ) -> VpnKey:
        key = VpnKey(
            user_id=user_id,
            status=VPN_KEY_ACTIVE,
            xui_email=xui_email,
            xui_uuid=xui_uuid,
            xui_sub_id=xui_sub_id,
            inbound_ids=inbound_ids,
            subscription_url=subscription_url,
            expires_at=expires_at,
            error_message=None,
        )
        self.session.add(instance=key)
        await self.session.flush()
        return key

    async def set_active_vpn_key_by_user_id(
            self,
            *,
            user_id: int,
            error_message: str | None = None,
    ) -> VpnKey:
        stmt = (
            update(table=VpnKey)
            .where(VpnKey.user_id == user_id)
            .values(
                status=VPN_KEY_ACTIVE,
                error_message=error_message,
                updated_at=func.now(),
            )
            .returning(VpnKey)
        )
        result: Result[Tuple[VpnKey]] = await self.session.execute(statement=stmt)
        return result.scalar_one()

    async def set_disable_vpn_key_by_user_id(
            self,
            *,
            user_id: int,
            error_message: str | None = None,
        ) -> VpnKey:
        stmt = (
            update(table=VpnKey)
            .where(VpnKey.user_id == user_id)
            .values(
                status=VPN_KEY_DISABLED,
                error_message=error_message,
                updated_at=func.now(),
            )
            .returning(VpnKey)
        )
        result: Result[Tuple[VpnKey]] = await self.session.execute(statement=stmt)
        return result.scalar_one()

    async def set_deleted_vpn_key_by_user_id(
            self,
            *,
            user_id: int,
            error_message: str | None = None,
    ) -> VpnKey:
        stmt = (
            update(table=VpnKey)
            .where(VpnKey.user_id == user_id)
            .values(
                status=VPN_KEY_DELETED,
                error_message=error_message,
                updated_at=func.now(),
            )
            .returning(VpnKey)
        )
        result: Result[Tuple[VpnKey]] = await self.session.execute(statement=stmt)
        return result.scalar_one()
