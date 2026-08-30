import logging

from aiogram import Router
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

FALLBACK_REPLY = "Something went wrong on our side. Please try again in a moment."

router = Router(name="errors")


@router.errors()
async def handle_unexpected_error(event: ErrorEvent) -> bool:
    logger.exception("unhandled error while processing an update", exc_info=event.exception)

    message = getattr(event.update, "message", None)
    if message is not None:
        # A second failure here would mask the original, so never let it escape.
        try:
            await message.answer(FALLBACK_REPLY)
        except Exception:
            logger.exception("could not deliver the fallback reply")

    # Handled: the poller keeps running rather than dying on one bad update.
    return True
