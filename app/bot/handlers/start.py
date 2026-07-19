import logging

from aiogram import Router, F
from aiogram.filters.command import CommandStart

from aiogram.types import Message
from aiogram.types.user import User

from app.bot.keyboards.main_menu import get_main_menu_inline_keyboard

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import VpnKey
from app.integrations.xui import AsyncXUI, XUIConfig
from app.services.vpn_key_service import VpnKeyService
from app.services.exceptions import (
    VpnKeyCreationInProgressError,
    VpnKeyCreationFailedError,
    VpnKeyRenewalInProgressError,
    VpnKeyDisabledError,
    TariffServiceError,
)


logger = logging.getLogger(__name__)


router = Router()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    xui: AsyncXUI,
    xui_config: XUIConfig,
) -> None:
    user: User | None = message.from_user

    if user is None:
        await message.answer(text="⚠️ Не удалось определить пользователя Telegram ⚠️")
        return

    vpn_key_service = VpnKeyService(
        session=session,
        xui=xui,
        xui_config=xui_config,
    )

    trial_vpn_key: VpnKey | None = None
    trial_message: str | None = None

    try:
        trial_vpn_key = await vpn_key_service.create_trial_vpn_key_for_new_user(telegram_user=user)

    except VpnKeyCreationInProgressError:
        await session.rollback()

        trial_message = (
            f"⏳ Немного подождите, VPN-ключ с бесплатным пробным периодом уже создаётся..."
        )

    except VpnKeyCreationFailedError:
        await session.rollback()

        trial_message = (
            f"⛓️‍💥 Не удалось завершить создание VPN-ключа c бесплатным пробным периодом\n\n"
            f"Попробуйте ещё раз через пару минут"
        )

    except VpnKeyRenewalInProgressError:
        await session.rollback()

        trial_message = (
            f"⏳ Немного подождите, VPN-ключ уже продлевается..."
        )

    except VpnKeyDisabledError:
        await session.rollback()

        trial_message = (
            f"Ваш VPN-ключ отключён. Срок действия вашего бесплатного пробного периода истёк ⏱️\n\n"
            f"Чтобы продолжить использовать VPN-ключ, выберите один из доступных тарифов"
        )

    except TariffServiceError:
        await session.rollback()

        trial_message = (
            f"😢 Бесплатный пробный период временно недоступен\n\n"
            f"Попробуйте отправить \"/start\" позже"
        )

        logger.exception(
            "Trial tariff is unavailable (telegram_user_id=%s)",
            user.id,
        )

    except Exception:
        await session.rollback()

        trial_message = (
            f"Не удалось создать VPN-ключ с бесплатным пробным периодом ☹️\n\n"
            f"Попробуйте отправить \"/start\" ещё раз позже"
        )

        logger.exception(
            "Failed to provision trial VPN key (telegram_user_id=%s)",
            user.id,
        )

    if trial_vpn_key is not None:
        trial_message = (
            f"🎁 VPN-ключ с бесплатным пробным периодом готов!\n\n"
            f"Действует до:\n"
            f"{trial_vpn_key.expires_at:%d.%m.%Y %H:%M} UTC\n\n"
            f"Ваш ключ:\n"
            f"{trial_vpn_key.subscription_url}\n\n"
            f"Скопируйте ссылку и добавьте её в VPN-клиент"
        )

    if trial_message is not None:
        await message.answer(text=trial_message)

    if user.username:
        greeting: str = f"👋 Привет, @{user.username}!"
    else:
        greeting: str = f"👋 Привет, {user.full_name}!"

    main_message: str = (
        f"{greeting}\n\n"
        f"👨‍💻 Для продолжения работы выберите действие ниже"
    )
    await message.answer(text=main_message, reply_markup=get_main_menu_inline_keyboard())
