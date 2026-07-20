from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.database.models.vpn_key import VpnKey
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.vpn_key_repository import VpnKeyRepository

from app.services.dto import VpnKeyProfile


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.user_repository = UserRepository(session=session)
        self.vpn_key_repository = VpnKeyRepository(session=session)

    async def get_vpn_key_profile(
            self,
            *,
            telegram_id: int,
    ) -> VpnKeyProfile | None:
        user: User | None = await self.user_repository.get_user_by_telegram_id(telegram_id=telegram_id)
        if user is None:
            return None

        vpn_key: VpnKey | None = await self.vpn_key_repository.get_vpn_key_by_user_id(user_id=user.id)
        if vpn_key is None:
            return None

        return VpnKeyProfile(
            subscription_url=vpn_key.subscription_url,
            status=vpn_key.status,
            tariff_title=vpn_key.tariff.title,
            expires_at=vpn_key.expires_at,
        )
