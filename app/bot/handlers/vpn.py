import logging

from aiogram import Router, F

from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings

from app.bot.keyboards.common import get_back_to_main_menu_inline_keyboard
from app.bot.keyboards.payment import PaymentStatusCallback, get_payment_inline_keyboard
from app.bot.keyboards.tariffs import TariffCallback, get_tariffs_inline_keyboard
from app.bot.mappers import map_telegram_user

from app.integrations.yookassa import AsyncYooKassa, YooKassaError

from app.services.payment_service import PaymentService
from app.services.tariff_service import TariffService
from app.services.exceptions import (
    TariffServiceError,
    PaymentServiceError,
    PaymentOrderNotFoundError,
)
from app.services.dto import (
    TariffOption,
    PaymentCheckout,
    PaymentOrderView,
)

from app.database.models.statuses import (
    ORDER_CREATED,
    ORDER_CANCELLED,
    ORDER_PAID,
    ORDER_FAILED,
    ORDER_FULFILLING,
    ORDER_FULFILLED,
)


logger = logging.getLogger(__name__)


router = Router()


@router.callback_query(F.data == "connect_vpn")
async def callback_connect_vpn(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings
) -> None:
    await callback.answer()

    tariff_service = TariffService(session=session)

    try:
        tariffs: list[TariffOption] = await tariff_service.get_public_active_tariffs()

    except TariffServiceError:
        await session.rollback()

        logger.exception(
            "Cannot load public active tariffs (telegram_user_id=%s)",
            callback.from_user.id,
        )

        await callback.message.edit_text(
            text=(
                f"⛓️‍💥 Не удалось загрузить тарифы\n\n"
                f"Попробуйте ещё раз позже или обратитесь в тех. поддержку: {settings.tg_support_username}"
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
                f"Попробуйте ещё раз позже или обратитесь в тех. поддержку: {settings.tg_support_username}"
            ),
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )

        return

    if not tariffs:
        await callback.message.edit_text(
            text=(
                f"🚨 На данный момент нет доступных тарифов\n\n"
                f"Попробуйте ещё раз позже или обратитесь в тех. поддержку: {settings.tg_support_username}"
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
    yookassa: AsyncYooKassa,
    settings: Settings,
) -> None:
    tariff_code: str = callback_data.tariff_code

    await callback.answer()

    payment_service = PaymentService(
        session=session,
        yookassa=yookassa,
        settings=settings,
    )

    try:
        checkout: PaymentCheckout = await payment_service.create_checkout(
            telegram_user=map_telegram_user(user=callback.from_user),
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
                "❌ Выбранный тариф на данный момент недоступен\n\n"
                "Пожалуйста, выберите другой тариф"
            ),
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )

        return

    except (PaymentServiceError, YooKassaError):
        await session.rollback()

        logger.exception(
            "Cannot create YooKassa payment (telegram_user_id=%s, tariff_code=%s)",
            callback.from_user.id,
            tariff_code,
        )

        await callback.message.edit_text(
            text=(
                f"⛓️‍💥 Не удалось сформировать оплату\n\n"
                f"Попробуйте ещё раз позже или обратитесь в тех. поддержку: {settings.tg_support_username}"
            ),
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )

        return

    except Exception:
        await session.rollback()

        logger.exception(
            "Unexpected payment creation error (telegram_user_id=%s, tariff_code=%s)",
            callback.from_user.id,
            tariff_code,
        )

        await callback.message.edit_text(
            text=(
                f"⛓️‍💥 Не удалось сформировать оплату\n\n"
                f"Попробуйте ещё раз позже или обратитесь в тех. поддержку: {settings.tg_support_username}"
            ),
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )

        return

    await callback.message.edit_text(
        text=(
            f"🗃️ Заказ №{checkout.order_id} сформирован\n\n"
            f"💳 К оплате: {checkout.amount_rub} ₽\n\n"
            "Нажмите на кнопку «Перейти к оплате», чтобы оплатить заказ\n\n"
            "После успешной оплаты бот автоматически продлит ваш VPN-ключ"
        ),
        reply_markup=get_payment_inline_keyboard(
            confirmation_url=checkout.confirmation_url,
            order_id=checkout.order_id,
        ),
    )


@router.callback_query(PaymentStatusCallback.filter())
async def callback_payment_status(
    callback: CallbackQuery,
    callback_data: PaymentStatusCallback,
    session: AsyncSession,
    yookassa: AsyncYooKassa,
    settings: Settings,
) -> None:
    payment_service = PaymentService(
        session=session,
        yookassa=yookassa,
        settings=settings,
    )

    try:
        order: PaymentOrderView = await payment_service.get_user_order_status(
            order_id=callback_data.order_id,
            telegram_id=callback.from_user.id,
            synchronize=True,
        )

    except PaymentOrderNotFoundError:
        await session.rollback()

        await callback.answer(
            text="🚨 Заказ не найден 🚨",
            show_alert=True,
        )

        return

    except PaymentServiceError:
        await session.rollback()

        logger.exception(
            "Cannot check payment status (order_id=%s, telegram_user_id=%s)",
            callback_data.order_id,
            callback.from_user.id,
        )

        await callback.answer()

        await callback.message.edit_text(
            text=(
                "❌ Не удалось проверить оплату\n\n"
                "Попробуйте ещё раз через несколько минут"
            ),
            reply_markup=get_back_to_main_menu_inline_keyboard(),
        )

        return

    await callback.answer()

    reply_markup: InlineKeyboardMarkup = get_back_to_main_menu_inline_keyboard()
    message: str = ""

    if order.status == ORDER_CREATED:
        message = (
            f"💳 Заказ №{order.order_id} создан\n\n"
            "💸 Оплата пока не завершена\n\n"
            "Если вы уже оплатили заказ, подождите несколько минут и нажмите «Проверить оплату» ещё раз"
        )

        if order.confirmation_url:
            reply_markup = get_payment_inline_keyboard(
                confirmation_url=order.confirmation_url,
                order_id=order.order_id,
            )

    elif order.status == ORDER_PAID:
        message = (
            f"✅ Оплата заказа №{order.order_id} получена!\n\n"
            "⏳ VPN-ключ ожидает обработки, немного подождите..."
        )

    elif order.status == ORDER_FULFILLING:
        message = (
            f"✅ Оплата заказа №{order.order_id} получена!\n\n"
            "⏳ VPN-ключ сейчас продлевается, немного подождите..."
        )

    elif order.status == ORDER_FULFILLED:
        if order.subscription_url is not None and order.vpn_key_expires_at is not None:
            message = (
                f"✅ Заказ №{order.order_id} оплачен!\n\n"
                f"📆 Тариф VPN-ключа успешно продлён!\n\n"
                f"⏱️ Дата окончания действия тарифа:\n"
                f"{order.vpn_key_expires_at:%d.%m.%Y %H:%M} UTC\n\n"
                f"🔑 Ваш VPN-ключ:\n"
                f"{order.subscription_url}"
            )

        else:
            message = (
                f"✅ Заказ №{order.order_id} оплачен!\n\n"
                "🪪 Дату окончания действия тарифа и VPN-ключ можно посмотреть в профиле"
            )

    elif order.status == ORDER_CANCELLED:
        message = (
            f"⛔ Платёж по заказу №{order.order_id} отменён\n\n"
            "Вы можете вернуться к списку тарифов и создать новый заказ"
        )

    elif order.status == ORDER_FAILED:
        if order.paid_at is not None:
            message = (
                f"✅ Оплата заказа №{order.order_id} получена\n\n"
                "⚙️ Возникла техническая задержка при продлении тарифа VPN-ключа\n\n"
                "Повторная обработка выполняется автоматически, немного подождите..."
            )

        else:
            message = (
                f"❌ Не удалось обработать заказ №{order.order_id}\n\n"
                f"Создайте новый заказ или обратитесь в тех. поддержку: {settings.tg_support_username}"
            )

    else:
        message = (
            f"🚨 Неизвестный статус заказа №{order.order_id}\n\n"
            f"Обратитесь в тех. поддержку: {settings.tg_support_username}"
        )

    await callback.message.edit_text(
        text=message,
        reply_markup=reply_markup,
    )
