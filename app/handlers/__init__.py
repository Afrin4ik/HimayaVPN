from aiogram import Router

from app.handlers import start, profile, vpn, fallback


router = Router()


router.include_router(start.router)
router.include_router(profile.router)
router.include_router(vpn.router)
router.include_router(fallback.router)
