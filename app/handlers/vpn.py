import logging

from aiogram import Router, F

from aiogram.types import CallbackQuery
from typing import LiteralString
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup

from app.keyboards.common import get_back_to_main_menu_inline_keyboard
from app.keyboards.tariffs import get_tariffs_inline_keyboard

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import VpnKey
from app.services.vpn_key_service import VpnKeyService
from app.integrations.xui import AsyncXUI, XUIConfig

from app.services.exceptions import (
    VpnKeyCreationInProgressError,
    VpnKeyCreationFailedError,
    VpnKeyDisabledError,
    VpnKeyRenewalInProgressError,
    VpnKeyRenewalFailedError,
)


logger = logging.getLogger(__name__)


router = Router()


@router.callback_query(F.data == "connect_vpn")
async def callback_connect_vpn(callback: CallbackQuery) -> None:
    connect_vpn_message: LiteralString = (
        f"📆 Выберите тариф\n"
    )

    tariffs_kd: InlineKeyboardMarkup = get_tariffs_inline_keyboard()
    back_to_main_kd: InlineKeyboardMarkup = get_back_to_main_menu_inline_keyboard()

    inline_kd = InlineKeyboardMarkup(
        inline_keyboard=tariffs_kd.inline_keyboard + back_to_main_kd.inline_keyboard
    )

    await callback.message.edit_text(text=connect_vpn_message, reply_markup=inline_kd)

@router.callback_query(F.data.in_({"tariff_1", "tariff_3", "tariff_6", "tariff_12"}))
async def callback_tariff_selected(
    callback: CallbackQuery,
    session: AsyncSession,
    xui: AsyncXUI,
    xui_config: XUIConfig,
) -> None:
    waiting_vpn_key_creating_message: LiteralString = (
        f"Немного подождите, VPN-ключ создаётся..."
    )
    await callback.answer(text=waiting_vpn_key_creating_message)

    try:
        vpn_key_service = VpnKeyService(
            session=session,
            xui=xui,
            xui_config=xui_config,
        )
        vpn_key: VpnKey = await vpn_key_service.get_or_create_vpn_key_for_user(
            telegram_user=callback.from_user,
            tariff_code=callback.data,
        )

    except VpnKeyCreationInProgressError:
        await session.rollback()

        vpn_key_creation_in_progress_message: LiteralString = (
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
            callback.data,
        )

        vpn_key_creation_failed_message: LiteralString = (
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

        vpn_key_disabled_message: LiteralString = (
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

        vpn_key_renewal_in_progress_message: LiteralString = (
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
            callback.data,
        )

        vpn_key_renewal_failed_message: LiteralString = (
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
            callback.data,
        )

        await session.rollback()

        failed_vpn_key_creating_message: LiteralString = (
            f"Не удалось создать VPN-ключ ☹️\n\n"
            f"Обратитесь в тех. поддержку: @miolerr"
        )
        await callback.message.edit_text(
            text=failed_vpn_key_creating_message,
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )
        return

    success_vpn_key_creating_message: LiteralString = (
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
