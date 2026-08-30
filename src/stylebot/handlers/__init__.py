from aiogram import Router

from stylebot.handlers.admin import router as admin_router
from stylebot.handlers.errors import router as errors_router
from stylebot.handlers.start import router as start_router

router = Router(name="root")
router.include_router(start_router)
router.include_router(admin_router)
router.include_router(errors_router)

__all__ = ["router"]
