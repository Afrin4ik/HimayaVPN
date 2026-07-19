import html
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types.user import User

from app.bot.keyboards.common import get_back_to_main_menu_inline_keyboard

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repository import UserRepository
from app.database.repositories.vpn_key_repository import VpnKeyRepository
from app.database.models import (
    User as DatabaseUser,
    VpnKey,
    VPN_KEY_ACTIVE,
    VPN_KEY_CREATING,
    VPN_KEY_FAILED,
    VPN_KEY_DISABLED,
    VPN_KEY_RENEWING,
)


router = Router()


def format_remaining_time(expires_at: datetime | None) -> str:
    if expires_at is None:
        return "Рассчитывается..."

    now: datetime = datetime.now(timezone.utc)
    remaining_seconds = int((expires_at - now).total_seconds())

    if remaining_seconds <= 0:
        return "Срок действия истёк"

    days, remainder = divmod(remaining_seconds, 24 * 60 * 60)
    hours, remainder = divmod(remainder, 60 * 60)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days} дн. {hours} ч. {minutes} мин."

    if hours > 0:
        return f"{hours} ч. {minutes} мин."

    if minutes > 0:
        return f"{minutes} мин."

    return "Меньше минуты"


@router.callback_query(F.data == "profile")
async def callback_profile(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    user: User = callback.from_user

    await callback.answer()

    user_repository = UserRepository(session=session)
    vpn_key_repository = VpnKeyRepository(session=session)

    vpn_key: VpnKey | None = None

    database_user: DatabaseUser | None = await user_repository.get_user_by_telegram_id(telegram_id=user.id)
    if database_user is not None:
        vpn_key = await vpn_key_repository.get_vpn_key_by_user_id(user_id=database_user.id)

    user_name: str = ""
    vpn_key_status_text: str = ""
    vpn_key_subscription_url_text: str = ""
    tariff_text: str = ""
    expires_at_text: str = ""
    remaining_time_text: str = ""

    if user.username:
        user_name = f"@{user.username}"
    else:
        user_name = "-"

    if vpn_key is None:
        vpn_key_subscription_url_text = "-"
        tariff_text = "-"
        expires_at_text = "-"
        remaining_time_text = "-"
    else:
        if vpn_key.subscription_url is not None:
            vpn_key_subscription_url_text = vpn_key.subscription_url
        else:
            vpn_key_subscription_url_text = "Формируется..."

        tariff_text = vpn_key.tariff.title

        if vpn_key.expires_at is not None:
            expires_at_text = vpn_key.expires_at.strftime(
                format="%d.%m.%Y %H:%M UTC"
            )
        else:
            expires_at_text = "Рассчитывается..."

        remaining_time_text = format_remaining_time(expires_at=vpn_key.expires_at)

    if vpn_key is None:
        vpn_key_status_text = "У вас нет VPN-ключа"
    elif vpn_key.status == VPN_KEY_ACTIVE:
        vpn_key_status_text = "Активный"
    elif vpn_key.status == VPN_KEY_CREATING:
        vpn_key_status_text = "Создаётся"
    elif vpn_key.status == VPN_KEY_RENEWING:
        vpn_key_status_text = "Продлевается"
    elif vpn_key.status == VPN_KEY_FAILED:
        vpn_key_status_text = "Попытка создать VPN-ключ не удалась"
        vpn_key_subscription_url_text = "-"
        expires_at_text = "-"
        remaining_time_text = "-"
    elif vpn_key.status == VPN_KEY_DISABLED:
        vpn_key_status_text = "Отключён"
    else:
        vpn_key_status_text = "Неизвестный статус"

    safe_user_name: str = html.escape(user_name)
    safe_full_name: str = html.escape(user.full_name)
    safe_vpn_key_subscription_url_text: str = html.escape(vpn_key_subscription_url_text)
    safe_vpn_key_status_text: str = html.escape(vpn_key_status_text)
    safe_tariff_text: str = html.escape(tariff_text)
    safe_expires_at_text: str = html.escape(expires_at_text)
    safe_remaining_time_text: str = html.escape(remaining_time_text)

    profile_message: str = (
        f'👤 <b>Профиль</b>\n\n'
        f'<b>ID:</b> {user.id}\n'
        f'<b>Имя пользователя:</b> {safe_user_name}\n'
        f'<b>Полное имя:</b> {safe_full_name}\n\n'
        f'🔑 <b>Ваш VPN-ключ:</b>\n'
        f'<span class="tg-spoiler">{safe_vpn_key_subscription_url_text}</span>\n\n'
        f'💡 <b>Статус VPN-ключа:</b>\n'
        f'{safe_vpn_key_status_text}\n\n'
        f'📆 <b>Выбранный тариф:</b>\n'
        f'"{safe_tariff_text}"\n\n'
        f'⏱️ <b>Дата окончания действия тарифа:</b>\n'
        f'{safe_expires_at_text}\n\n'
        f'⌛ <b>VPN-ключ перестанет работать через:</b>\n'
        f'{safe_remaining_time_text}\n'
    )

    await callback.message.edit_text(
        text=profile_message,
        parse_mode="HTML",
        reply_markup=get_back_to_main_menu_inline_keyboard()
    )
