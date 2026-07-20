from aiogram import Router, F
from aiogram.types import CallbackQuery

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.presenters.profile import render_profile
from app.bot.keyboards.common import get_back_to_main_menu_inline_keyboard

from app.services.profile_service import ProfileService
from app.services.dto import VpnKeyProfile


router = Router()


@router.callback_query(F.data == "profile")
async def callback_profile(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    await callback.answer()

    profile_service = ProfileService(session=session)

    vpn_key_profile: VpnKeyProfile | None = await profile_service.get_vpn_key_profile(telegram_id=callback.from_user.id)

    profile_message: str = render_profile(
        telegram_user=callback.from_user,
        vpn_key=vpn_key_profile,
    )

    await callback.message.edit_text(
        text=profile_message,
        parse_mode="HTML",
        reply_markup=get_back_to_main_menu_inline_keyboard(),
    )
