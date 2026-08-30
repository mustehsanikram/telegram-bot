from aiogram import Router

from stylebot.handlers.start import router as start_router

router = Router(name="root")
router.include_router(start_router)

__all__ = ["router"]
