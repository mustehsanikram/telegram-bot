import logging
from collections.abc import Sequence

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from stylebot.services.formatting import escape_html

logger = logging.getLogger(__name__)


def new_client_message(display_name: str, telegram_user_id: int) -> str:
    return (
        f"New client waiting for approval.\n\n"
        f"Name: {escape_html(display_name)}\n"
        f"Telegram id: <code>{telegram_user_id}</code>\n\n"
        f"Approve with /approve {telegram_user_id}\n"
        f"Decline with /decline {telegram_user_id}"
    )


async def notify_admins_of_new_client(
    bot: Bot,
    admin_ids: Sequence[int],
    display_name: str,
    telegram_user_id: int,
) -> int:
    """Tell every admin about a new client. Returns how many were reached."""
    if not admin_ids:
        logger.warning(
            "no admin ids configured, so nobody was told about client %s", telegram_user_id
        )
        return 0

    delivered = 0
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, new_client_message(display_name, telegram_user_id))
        except TelegramForbiddenError:
            # Telegram refuses a bot's first message, so an admin who has never
            # opened the bot cannot be reached. Not fatal to the client's /start.
            logger.warning("admin %s has never opened the bot, cannot notify them", admin_id)
        except TelegramAPIError:
            logger.exception("could not notify admin %s", admin_id)
        else:
            delivered += 1
    return delivered


APPROVED_NOTICE = (
    "Good news. Your stylist has approved you.\n\n"
    "You will be told as soon as your subscription and channel access are set up."
)

DECLINED_NOTICE = (
    "Your stylist is not able to take you on right now.\n\n"
    "Please contact them directly if you think this is a mistake."
)


async def notify_client_of_decision(bot: Bot, telegram_user_id: int, text: str) -> bool:
    """Tell a client what was decided. Never lets a delivery failure break the admin's command."""
    try:
        await bot.send_message(telegram_user_id, text)
    except TelegramForbiddenError:
        logger.warning("client %s has blocked the bot, could not notify them", telegram_user_id)
        return False
    except TelegramAPIError:
        logger.exception("could not notify client %s", telegram_user_id)
        return False
    return True
