from datetime import datetime, timedelta, timezone

from aiogram.types import User as TelegramUser
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.xui import AsyncXUI, CreatedXUIClient, XUIConfig
from app.database.models import User, Tariff, VpnKey, VPN_KEY_CREATING, VPN_KEY_ACTIVE, VPN_KEY_FAILED, VPN_KEY_DISABLED
from app.repositories.tariffs import TariffRepository
from app.repositories.vpn_keys import VpnKeyRepository
from app.services.user_service import UserService


class VpnKeyService:
    def __init__(self, session: AsyncSession, xui: AsyncXUI, xui_config: XUIConfig) -> None:
        self.session: AsyncSession = session
        self.xui: AsyncXUI = xui
        self.xui_config: XUIConfig = xui_config
        self.tariffs_repository = TariffRepository(session=session)
        self.vpn_keys_repository = VpnKeyRepository(session=session)
        self.user_service = UserService(session=session)

    async def get_or_create_vpn_key_for_user(
            self,
            *,
            telegram_user: TelegramUser,
            tariff_code: str,
    ) -> VpnKey:
        user: User = await self.user_service.sync_telegram_user(telegram_user=telegram_user)

        selected_tariff: Tariff | None = await self.tariffs_repository.get_active_tariff_by_code(code=tariff_code)
        if selected_tariff is None:
            raise ValueError("No tariff found or tariff disabled")

        existing_vpn_key: VpnKey | None = await self.vpn_keys_repository.get_vpn_key_by_user_id(user_id=user.id)
        if existing_vpn_key and existing_vpn_key.status == VPN_KEY_ACTIVE:
            return existing_vpn_key
        if existing_vpn_key and existing_vpn_key.status == VPN_KEY_CREATING:
            raise RuntimeError("The VPN key is currently being created. Please try again in a minute")
        if existing_vpn_key and existing_vpn_key.status == VPN_KEY_DISABLED:
            raise RuntimeError("A disabled VPN key already exists for this user")
        if existing_vpn_key and existing_vpn_key.status == VPN_KEY_FAILED:
            placeholder: VpnKey = await self.vpn_keys_repository.set_creating(
                vpn_key_id=existing_vpn_key.id,
                tariff_id=selected_tariff.id,
            )
            await self.session.commit()
        else:
            try:
                placeholder: VpnKey = await self.vpn_keys_repository.create_placeholder(
                    user_id=user.id,
                    tariff_id=selected_tariff.id,
                )
                await self.session.commit()
            except IntegrityError:
                await self.session.rollback()
                existing_vpn_key: VpnKey | None = await self.vpn_keys_repository.get_vpn_key_by_user_id(user_id=user.id)
                if existing_vpn_key is not None:
                    return existing_vpn_key
                raise

        try:
            created_xui_client: CreatedXUIClient = await self.xui.add_client(
                email=f"tg_{user.telegram_id}",
                inbound_ids=self.xui_config.default_inbound_ids,
                limit_ip=self.xui_config.default_limit_ip,
                total_gb=selected_tariff.total_gb,
                expiry_days=selected_tariff.duration_days,
                tg_id=user.telegram_id,
                comment=f"HimayaVPN user, tg_id: {user.telegram_id}",
            )

            subscription_url: str = await self.xui.get_client_subscription_link(email=created_xui_client.email)

            expires_at: datetime = datetime.now(timezone.utc) + timedelta(days=selected_tariff.duration_days)

            vpn_key: VpnKey = await self.vpn_keys_repository.activate(
                vpn_key_id=placeholder.id,
                xui_email=created_xui_client.email,
                xui_uuid=created_xui_client.uuid,
                xui_sub_id=created_xui_client.sub_id,
                inbound_ids=created_xui_client.inbound_ids,
                subscription_url=subscription_url,
                expires_at=expires_at,
            )
            await self.session.commit()
            return vpn_key
        except Exception as exc:
            await self.vpn_keys_repository.mark_failed(
                vpn_key_id=placeholder.id,
                error_message=str(exc),
            )
            await self.session.commit()
            raise
