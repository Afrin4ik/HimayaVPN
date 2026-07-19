from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tariff
from app.database.repositories.tariff_repository import TariffRepository
from app.services.exceptions import (
    TariffUnavailableError,
    TariffConfigurationError,
)


TRIAL_TARIFF_CODE = "trial_3_days"


class TariffService:
    def __init__(self, session: AsyncSession) -> None:
        self.tariff_repository = TariffRepository(session=session)

    @staticmethod
    def _require_valid_tariff(
        *,
        tariff: Tariff,
    ) -> Tariff:
        if not tariff.code.strip():
            raise TariffConfigurationError(f"Tariff id={tariff.id} has an empty code")

        if not tariff.title.strip():
            raise TariffConfigurationError(f"Tariff {tariff.code!r} has an empty title")

        if tariff.price_rub < 0:
            raise TariffConfigurationError(f"Tariff {tariff.code!r} has a negative price")

        if tariff.duration_days <= 0:
            raise TariffConfigurationError(f"Tariff {tariff.code!r} has a non-positive duration")

        if tariff.limit_ip <= 0:
            raise TariffConfigurationError(f"Tariff {tariff.code!r} has a non-positive limit_ip")

        if tariff.total_gb <= 0:
            raise TariffConfigurationError(f"Tariff {tariff.code!r} has a non-positive total_gb")

        return tariff

    async def get_active_tariff_by_code(
            self,
            *,
            code: str,
    ) -> Tariff:
        normalized_code = code.strip()

        if not normalized_code:
            raise TariffUnavailableError("Tariff code cannot be empty")

        tariff: Tariff | None = await self.tariff_repository.get_active_tariff_by_code(code=normalized_code)

        if tariff is None:
            raise TariffUnavailableError(f"Tariff {normalized_code!r} does not exist or is disabled")

        return self._require_valid_tariff(tariff=tariff)

    async def get_tariff_by_id(
            self,
            *,
            tariff_id: int,
    ) -> Tariff:
        tariff: Tariff | None = await self.tariff_repository.get_tariff_by_id(tariff_id=tariff_id)

        if tariff is None:
            raise TariffUnavailableError(f"Tariff id={tariff_id} does not exist")

        return self._require_valid_tariff(tariff=tariff)

    async def get_public_active_tariffs(self) -> list[Tariff]:
        tariffs: list[Tariff] = await self.tariff_repository.get_active_tariffs()

        public_tariffs: list[Tariff] = []

        for tariff in tariffs:
            if tariff.code == TRIAL_TARIFF_CODE:
                continue

            public_tariffs.append(self._require_valid_tariff(tariff=tariff))

        return public_tariffs
