from datetime import UTC, datetime

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from stylebot.handlers.filters import IsAdmin
from stylebot.handlers.notifications import (
    APPROVED_NOTICE,
    DECLINED_NOTICE,
    notify_client_of_decision,
)
from stylebot.services.clients import DecisionOutcome, parse_telegram_id
from stylebot.services.intake import approve_client, decline_client

router = Router(name="admin")

ADMIN_COMMANDS = ("approve", "decline")

REFUSAL = "That command is for your stylist only."

BAD_ID = (
    "I need one numeric Telegram id, for example:\n"
    "<code>/approve 778899</code>\n\n"
    "The id is in the notification you got when the client first messaged the bot."
)

CONFIRMATIONS = {
    DecisionOutcome.APPROVED: "Approved {name}. They have been told.",
    DecisionOutcome.DECLINED: "Declined {name}. They have been told.",
    DecisionOutcome.NOT_FOUND: "No client with id {target} has messaged the bot yet.",
    DecisionOutcome.ALREADY_APPROVED: "{name} was already approved. Nothing changed.",
    DecisionOutcome.ALREADY_REMOVED: (
        "{name} was removed earlier. Bringing someone back is not supported yet."
    ),
}

CLIENT_NOTICES = {
    DecisionOutcome.APPROVED: APPROVED_NOTICE,
    DecisionOutcome.DECLINED: DECLINED_NOTICE,
}


@router.message(Command(*ADMIN_COMMANDS), ~IsAdmin())
async def refuse_non_admin(message: Message) -> None:
    await message.answer(REFUSAL)


@router.message(Command("approve"), IsAdmin())
async def handle_approve(message: Message, command: CommandObject, session: AsyncSession) -> None:
    await _decide(message, command, session, approving=True)


@router.message(Command("decline"), IsAdmin())
async def handle_decline(message: Message, command: CommandObject, session: AsyncSession) -> None:
    await _decide(message, command, session, approving=False)


async def _decide(
    message: Message, command: CommandObject, session: AsyncSession, approving: bool
) -> None:
    target = parse_telegram_id(command.args)
    if target is None:
        await message.answer(BAD_ID)
        return

    if approving:
        outcome, client = await approve_client(session, target, datetime.now(UTC))
    else:
        outcome, client = await decline_client(session, target)

    name = client.display_name if client is not None else str(target)
    await message.answer(CONFIRMATIONS[outcome].format(name=name, target=target))

    notice = CLIENT_NOTICES.get(outcome)
    if notice is not None and message.bot is not None:
        await notify_client_of_decision(message.bot, target, notice)
