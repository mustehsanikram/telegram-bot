from typing import Any

import pytest
from aiogram.types import TelegramObject
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stylebot.bot import build_dispatcher
from stylebot.config import Settings
from stylebot.handlers.middleware import DatabaseSessionMiddleware

SETTINGS = Settings(bot_token="unused", private_channel_id=-1001, admin_user_ids=[])


async def test_handler_receives_a_usable_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    middleware = DatabaseSessionMiddleware(session_factory)
    observed: dict[str, Any] = {}

    async def handler(event: TelegramObject, data: dict[str, Any]) -> str:
        session = data["session"]
        assert isinstance(session, AsyncSession)
        observed["select_1"] = (await session.execute(text("select 1"))).scalar_one()
        return "handled"

    result = await middleware(handler, TelegramObject(), {})

    assert result == "handled"
    assert observed["select_1"] == 1


async def test_handler_failure_propagates(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A failing handler must not be swallowed by the session wrapper."""
    middleware = DatabaseSessionMiddleware(session_factory)

    async def failing_handler(event: TelegramObject, data: dict[str, Any]) -> None:
        raise RuntimeError("handler blew up")

    with pytest.raises(RuntimeError, match="handler blew up"):
        await middleware(failing_handler, TelegramObject(), {})


async def test_each_update_gets_its_own_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    middleware = DatabaseSessionMiddleware(session_factory)
    sessions: list[AsyncSession] = []

    async def handler(event: TelegramObject, data: dict[str, Any]) -> None:
        sessions.append(data["session"])

    await middleware(handler, TelegramObject(), {})
    await middleware(handler, TelegramObject(), {})

    assert sessions[0] is not sessions[1]


def test_middleware_is_registered_on_the_dispatcher() -> None:
    """Without this, the unit tests above would still pass on an unwired middleware."""
    dispatcher = build_dispatcher(async_sessionmaker(), SETTINGS)

    assert any(
        isinstance(middleware, DatabaseSessionMiddleware)
        for middleware in dispatcher.update.middleware
    )
