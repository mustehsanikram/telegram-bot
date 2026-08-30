from datetime import UTC, datetime

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from stylebot.config import Settings
from stylebot.handlers.notifications import notify_admins_of_new_client
from stylebot.services.clients import IntakeOutcome, display_name_for
from stylebot.services.intake import register_client

router = Router(name="start")

REPLIES = {
    IntakeOutcome.REGISTERED: (
        "Welcome. You have been added to the list and your stylist will review it shortly.\n\n"
        "You will hear from this bot as soon as you are approved."
    ),
    IntakeOutcome.ALREADY_PENDING: (
        "You are already on the list, waiting for your stylist to review it.\n\n"
        "There is nothing else you need to do."
    ),
    IntakeOutcome.ALREADY_APPROVED: (
        "You are already approved and on your stylist's list.\n\n"
        "Your stylist will be in touch about your subscription."
    ),
    IntakeOutcome.PREVIOUSLY_REMOVED: (
        "Your access has been removed. Please contact your stylist directly if you would "
        "like to come back."
    ),
}


@router.message(CommandStart())
async def handle_start(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = message.from_user
    if user is None:
        return

    name = display_name_for(user.full_name, user.username, user.id)
    outcome, _ = await register_client(session, user.id, name, datetime.now(UTC))
    await message.answer(REPLIES[outcome])

    if outcome is IntakeOutcome.REGISTERED and message.bot is not None:
        await notify_admins_of_new_client(message.bot, settings.admin_user_ids, name, user.id)
