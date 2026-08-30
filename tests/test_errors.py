import logging
from typing import Any, cast

import pytest
from aiogram.types import ErrorEvent

from stylebot.handlers.errors import FALLBACK_REPLY, handle_unexpected_error


class RecordingMessage:
    def __init__(self, fail: bool = False) -> None:
        self.replies: list[str] = []
        self._fail = fail

    async def answer(self, text: str) -> None:
        if self._fail:
            raise RuntimeError("telegram refused the reply")
        self.replies.append(text)


def error_event(message: object | None, exception: Exception) -> ErrorEvent:
    update = cast(Any, type("StubUpdate", (), {"message": message})())
    return ErrorEvent.model_construct(update=update, exception=exception)


async def test_user_gets_a_reply_and_the_error_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    message = RecordingMessage()
    caplog.set_level(logging.ERROR)

    handled = await handle_unexpected_error(error_event(message, RuntimeError("boom")))

    assert handled is True, "returning False would let the poller die on one bad update"
    assert message.replies == [FALLBACK_REPLY]
    assert "unhandled error" in caplog.text
    assert "boom" in caplog.text


async def test_a_failing_reply_does_not_escape(caplog: pytest.LogCaptureFixture) -> None:
    """If the fallback itself fails, that must not mask the original error."""
    caplog.set_level(logging.ERROR)

    handled = await handle_unexpected_error(
        error_event(RecordingMessage(fail=True), RuntimeError("boom"))
    )

    assert handled is True
    assert "could not deliver the fallback reply" in caplog.text


async def test_update_without_a_message_is_survivable(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)

    assert await handle_unexpected_error(error_event(None, RuntimeError("boom"))) is True
    assert "unhandled error" in caplog.text
