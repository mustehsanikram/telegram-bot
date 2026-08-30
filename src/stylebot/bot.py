import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stylebot.config import Settings
from stylebot.db.session import create_engine, create_session_factory
from stylebot.handlers import router
from stylebot.handlers.middleware import DatabaseSessionMiddleware

logger = logging.getLogger(__name__)


def build_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher(factory: async_sessionmaker[AsyncSession], settings: Settings) -> Dispatcher:
    # Workflow data: aiogram injects these into handlers by parameter name.
    dispatcher = Dispatcher(settings=settings)
    # Registered on update so every event type gets a session, not just messages.
    dispatcher.update.middleware(DatabaseSessionMiddleware(factory))
    dispatcher.include_router(router)
    return dispatcher


async def run_polling(settings: Settings) -> None:
    bot = build_bot(settings)
    engine = create_engine(settings)
    dispatcher = build_dispatcher(create_session_factory(engine), settings)
    logger.info("starting polling")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()
