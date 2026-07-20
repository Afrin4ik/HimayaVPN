import html

from datetime import datetime, timezone

from aiogram.types import User

from app.services.dto import VpnKeyProfile


VPN_KEY_STATUS_TEXTS: dict[str, str] = {
    "active": "Активный",
    "creating": "Создаётся",
    "renewing": "Продлевается",
    "failed": "Попытка создать VPN-ключ не удалась",
    "disabled": "Отключён",
}


def format_remaining_time(
        expires_at: datetime | None,
        *,
        now: datetime | None = None,
) -> str:
    if expires_at is None:
        return "Рассчитывается..."

    current_time: datetime = now or datetime.now(timezone.utc)
    remaining_seconds = int((expires_at - current_time).total_seconds())

    if remaining_seconds <= 0:
        return "Срок действия истёк"

    days, remainder = divmod(remaining_seconds, 24 * 60 * 60)
    hours, remainder = divmod(remainder, 60 * 60)
    minutes, _seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days} дн. {hours} ч. {minutes} мин."

    if hours > 0:
        return f"{hours} ч. {minutes} мин."

    if minutes > 0:
        return f"{minutes} мин."

    return "Меньше минуты"


def render_profile(
        *,
        telegram_user: User,
        vpn_key: VpnKeyProfile | None,
) -> str:
    user_name: str = ""
    subscription_url_text: str = ""
    status_text: str = ""
    tariff_text: str = ""
    expires_at_text: str = ""
    remaining_time_text: str = ""

    if telegram_user.username:
        user_name = f"@{telegram_user.username}"
    else:
        user_name = "-"

    if vpn_key is None:
        subscription_url_text = "-"
        status_text = "У вас нет VPN-ключа"
        tariff_text = "-"
        expires_at_text = "-"
        remaining_time_text = "-"

    else:
        if vpn_key.subscription_url is not None:
            subscription_url_text = vpn_key.subscription_url
        else:
            subscription_url_text = "Формируется..."

        status_text = VPN_KEY_STATUS_TEXTS.get(vpn_key.status, "Неизвестный статус")

        tariff_text = vpn_key.tariff_title

        if vpn_key.expires_at is not None:
            expires_at_text = vpn_key.expires_at.strftime(
                format="%d.%m.%Y %H:%M UTC"
            )
        else:
            expires_at_text = "Рассчитывается..."

        remaining_time_text = format_remaining_time(expires_at=vpn_key.expires_at)

        if vpn_key.status == "failed":
            subscription_url_text = "-"
            expires_at_text = "-"
            remaining_time_text = "-"

    safe_user_name: str = html.escape(user_name)
    safe_full_name: str = html.escape(telegram_user.full_name)
    safe_subscription_url: str = html.escape(subscription_url_text)
    safe_status: str = html.escape(status_text)
    safe_tariff: str = html.escape(tariff_text)
    safe_expires_at: str = html.escape(expires_at_text)
    safe_remaining_time: str = html.escape(remaining_time_text)

    return (
        f"👤 <b>Профиль</b>\n\n"
        f"<b>ID:</b> {telegram_user.id}\n"
        f"<b>Имя пользователя:</b> {safe_user_name}\n"
        f"<b>Полное имя:</b> {safe_full_name}\n\n"
        f"🔑 <b>Ваш VPN-ключ:</b>\n"
        f'<span class="tg-spoiler">{safe_subscription_url}</span>\n\n'
        f"💡 <b>Статус VPN-ключа:</b>\n"
        f"{safe_status}\n\n"
        f"📆 <b>Выбранный тариф:</b>\n"
        f'"{safe_tariff}"\n\n'
        f"⏱️ <b>Дата окончания действия тарифа:</b>\n"
        f"{safe_expires_at}\n\n"
        f"⌛ <b>VPN-ключ перестанет работать через:</b>\n"
        f"{safe_remaining_time}\n"
    )
