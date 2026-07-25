import logging

from aiogram import Router, F

from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings

from app.bot.keyboards.common import get_back_to_main_menu_inline_keyboard
from app.bot.keyboards.payment import get_payment_inline_keyboard
from app.bot.keyboards.tariffs import TariffCallback, get_tariffs_inline_keyboard
from app.bot.mappers import map_telegram_user

from app.integrations.yookassa import AsyncYooKassa, YooKassaError

from app.services.dto import PaymentCheckout, TariffOption
from app.services.payment_service import PaymentService, PaymentServiceError
from app.services.tariff_service import TariffService
from app.services.exceptions import TariffServiceError


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
