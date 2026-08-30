import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from stylebot.config import Settings
from stylebot.handlers import router

logger = logging.getLogger(__name__)


def build_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher


async def run_polling(settings: Settings) -> None:
    bot = build_bot(settings)
    dispatcher = build_dispatcher()
    logger.info("starting polling")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
