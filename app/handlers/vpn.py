import logging

from aiogram import Router, F

from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from app.config import get_settings

from app.keyboards.common import get_back_to_main_menu_inline_keyboard
from app.keyboards.tariffs import TariffCallback, get_tariffs_inline_keyboard

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.xui import AsyncXUI, XUIConfig

from app.database.models import VpnKey, Tariff
from app.services.vpn_key_service import VpnKeyService
from app.services.tariff_service import TariffService

from app.services.exceptions import (
    VpnKeyCreationInProgressError,
    VpnKeyCreationFailedError,
    VpnKeyDisabledError,
    VpnKeyRenewalInProgressError,
    VpnKeyRenewalFailedError,
    TariffServiceError,
)


SUPPORT_USERNAME: str = get_settings().tg_support_username


logger = logging.getLogger(__name__)


router = Router()


@router.callback_query(F.data == "connect_vpn")
async def callback_connect_vpn(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    await callback.answer()

    tariff_service = TariffService(session=session)

    try:
        tariffs: list[Tariff] = await tariff_service.get_public_active_tariffs()

    except TariffServiceError:
        await session.rollback()

        logger.exception(
            "Cannot load public active tariffs (telegram_user_id=%s)",
            callback.from_user.id,
        )

        await callback.message.edit_text(
            text=(
                f"⛓️‍💥 Не удалось загрузить тарифы\n\n"
                f"Попробуйте ещё раз позже или обратитесь в тех. поддержку: {SUPPORT_USERNAME}"
            ),
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )

        return

    except Exception:
        await session.rollback()

        logger.exception(
            "Unexpected error while loading tariffs (telegram_user_id=%s)",
            callback.from_user.id,
        )

        await callback.message.edit_text(
            text=(
                f"⛓️‍💥 Не удалось загрузить тарифы\n\n"
                f"Попробуйте ещё раз позже или обратитесь в тех. поддержку: {SUPPORT_USERNAME}"
            ),
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )

        return

    if not tariffs:
        await callback.message.edit_text(
            text=(
                f"🚨 На данный момент нет доступных тарифов\n\n"
                f"Попробуйте ещё раз позже или обратитесь в тех. поддержку: {SUPPORT_USERNAME}"
            ),
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )

        return

    tariffs_keyboard: InlineKeyboardMarkup = get_tariffs_inline_keyboard(tariffs=tariffs)

    await callback.message.edit_text(
        text="📆 Выберите тариф",
        reply_markup=tariffs_keyboard,
    )


@router.callback_query(TariffCallback.filter())
async def callback_tariff_selected(
    callback: CallbackQuery,
    callback_data: TariffCallback,
    session: AsyncSession,
    xui: AsyncXUI,
    xui_config: XUIConfig,
) -> None:
    tariff_code: str = callback_data.tariff_code

    await callback.answer()

    try:
        vpn_key_service = VpnKeyService(
            session=session,
            xui=xui,
            xui_config=xui_config,
        )
        vpn_key: VpnKey = await vpn_key_service.get_or_create_vpn_key_for_user(
            telegram_user=callback.from_user,
            tariff_code=tariff_code,
        )

    except TariffServiceError:
        await session.rollback()

        logger.warning(
            "Selected tariff is unavailable (telegram_user_id=%s, tariff_code=%s)",
            callback.from_user.id,
            tariff_code,
            exc_info=True,
        )

        await callback.message.edit_text(
            text=(
                f"❌ Выбранный тариф на данный момент недоступен\n\n"
                f"Пожалуйста, выберите другой тариф"
            ),
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )

        return

    except VpnKeyCreationInProgressError:
        await session.rollback()

        vpn_key_creation_in_progress_message: str = (
            f"⏳ Немного подождите, VPN-ключ уже создаётся..."
        )
        await callback.message.edit_text(
            text=vpn_key_creation_in_progress_message,
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )
        return

    except VpnKeyCreationFailedError:
        await session.rollback()

        logger.warning(
            "Previous VPN key creation failed (telegram_user_id=%s, tariff_code=%s)",
            callback.from_user.id,
            tariff_code,
        )

        vpn_key_creation_failed_message: str = (
            f"⛓️‍💥 Не удалось завершить создание VPN-ключа\n\n"
            f"Попробуйте ещё раз через пару минут"
        )
        await callback.message.edit_text(
            text=vpn_key_creation_failed_message,
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )
        return

    except VpnKeyDisabledError:
        await session.rollback()

        vpn_key_disabled_message: str = (
            f"Ваш VPN-ключ отключён. Срок действия вашего тарифа истёк ⏱️\n\n"
            f"Чтобы продолжить использовать VPN-ключ, выберите один из доступных тарифов"
        )
        await callback.message.edit_text(
            text=vpn_key_disabled_message,
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )
        return

    except VpnKeyRenewalInProgressError:
        await session.rollback()

        vpn_key_renewal_in_progress_message: str = (
            f"⏳ Немного подождите, VPN-ключ уже продлевается..."
        )
        await callback.message.edit_text(
            text=vpn_key_renewal_in_progress_message,
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )
        return

    except VpnKeyRenewalFailedError:
        await session.rollback()

        logger.warning(
            "VPN key renewal failed (telegram_user_id=%s, tariff_code=%s)",
            callback.from_user.id,
            tariff_code,
        )

        vpn_key_renewal_failed_message: str = (
            f"⛓️‍💥 Не удалось завершить продление VPN-ключа\n\n"
            f"Попробуйте ещё раз через пару минут"
        )
        await callback.message.edit_text(
            text=vpn_key_renewal_failed_message,
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )
        return

    except Exception:
        logger.exception(
            "Failed to create VPN key: telegram_user_id=%s, tariff_code=%s",
            callback.from_user.id,
            tariff_code,
        )

        await session.rollback()

        failed_vpn_key_creating_message: str = (
            f"Не удалось создать VPN-ключ ☹️\n\n"
            f"Обратитесь в тех. поддержку: {SUPPORT_USERNAME}"
        )
        await callback.message.edit_text(
            text=failed_vpn_key_creating_message,
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )
        return

    success_vpn_key_creating_message: str = (
        f"✅ VPN-ключ готов!\n\n"
        f"Действует до:\n"
        f"{vpn_key.expires_at:%d.%m.%Y %H:%M} UTC\n\n"
        f"Ваш ключ:\n"
        f"{vpn_key.subscription_url}\n\n"
        f"Скопируйте ссылку и добавьте её в VPN-клиент"
    )
    await callback.message.edit_text(
        text=success_vpn_key_creating_message,
        reply_markup=get_back_to_main_menu_inline_keyboard(),
    )
