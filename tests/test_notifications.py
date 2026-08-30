import logging
from typing import Any, cast

import pytest
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.methods import SendMessage

from stylebot.handlers.notifications import new_client_message, notify_admins_of_new_client


class StubBot:
    """Records sends, and can fail for chosen admin ids."""

    def __init__(self, forbidden: set[int] | None = None, rate_limited: set[int] | None = None):
        self.sent: list[tuple[int, str]] = []
        self._forbidden = forbidden or set()
        self._rate_limited = rate_limited or set()

    async def send_message(self, chat_id: int, text: str) -> None:
        if chat_id in self._forbidden:
            raise TelegramForbiddenError(method=SendMessage(chat_id=chat_id, text=text),
                                         message="bot was blocked by the user")
        if chat_id in self._rate_limited:
            raise TelegramRetryAfter(method=SendMessage(chat_id=chat_id, text=text),
                                     message="flood control", retry_after=30)
        self.sent.append((chat_id, text))


def as_bot(stub: StubBot) -> Bot:
    return cast(Bot, cast(Any, stub))


def test_message_carries_the_id_the_admin_must_type() -> None:
    text = new_client_message("Ada Lovelace", 778899)

    assert "Ada Lovelace" in text
    assert "778899" in text
    assert "/approve 778899" in text


async def test_every_admin_is_notified() -> None:
    bot = StubBot()

    delivered = await notify_admins_of_new_client(as_bot(bot), [1, 2, 3], "Ada", 778899)

    assert delivered == 3
    assert [chat_id for chat_id, _ in bot.sent] == [1, 2, 3]


async def test_an_admin_who_never_opened_the_bot_is_skipped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The client's /start must not fail because one admin is unreachable."""
    caplog.set_level(logging.WARNING)
    bot = StubBot(forbidden={2})

    delivered = await notify_admins_of_new_client(as_bot(bot), [1, 2, 3], "Ada", 778899)

    assert delivered == 2
    assert [chat_id for chat_id, _ in bot.sent] == [1, 3]
    assert "never opened the bot" in caplog.text


async def test_a_rate_limited_admin_does_not_stop_the_rest(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)
    bot = StubBot(rate_limited={1})

    delivered = await notify_admins_of_new_client(as_bot(bot), [1, 2], "Ada", 778899)

    assert delivered == 1
    assert "could not notify admin 1" in caplog.text


async def test_empty_admin_list_warns_instead_of_silently_doing_nothing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    bot = StubBot()

    delivered = await notify_admins_of_new_client(as_bot(bot), [], "Ada", 778899)

    assert delivered == 0
    assert bot.sent == []
    assert "no admin ids configured" in caplog.text
