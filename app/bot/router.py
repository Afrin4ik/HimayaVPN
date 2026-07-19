from aiogram import Router

from app.bot.handlers import main_menu, start, vpn, profile, fallback


def build_router() -> Router:
    router = Router(name="root")

    router.include_router(router=main_menu.router)
    router.include_router(router=start.router)
    router.include_router(router=vpn.router)
    router.include_router(router=profile.router)
    router.include_router(router=fallback.router)

    return router
