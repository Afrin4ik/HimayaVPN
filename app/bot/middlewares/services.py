from collections.abc import Awaitable, Callable
from typing import Any
from dataclasses import dataclass

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.integrations.yookassa import AsyncYooKassa
from app.services.payment_service import PaymentService
from app.services.tariff_service import TariffService


@dataclass(slots=True)
class RequestServices:
    payments: PaymentService
    tariffs: TariffService


class RequestServicesMiddleware(BaseMiddleware):
    def __init__(
            self,
            *,
            yookassa: AsyncYooKassa,
            settings: Settings,
    ) -> None:
        self.yookassa = yookassa
        self.settings = settings

    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
    ) -> Any:
        session = data.get("session")

        if not isinstance(session, AsyncSession):
            raise RuntimeError(
                "RequestServicesMiddleware requires DatabaseSessionMiddleware to run first"
            )

        data["services"] = RequestServices(
            payments=PaymentService(
                session=session,
                yookassa=self.yookassa,
                settings=self.settings,
            ),
            tariffs=TariffService(
                session=session,
            ),
        )

        return await handler(event, data)
