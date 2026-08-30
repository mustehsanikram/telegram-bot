from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stylebot.db.session import session_scope


class DatabaseSessionMiddleware(BaseMiddleware):
    """Gives each update one session, committed or rolled back when it finishes."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_scope(self._factory) as session:
            data["session"] = session
            return await handler(event, data)
