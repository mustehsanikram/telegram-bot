from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from stylebot.db import repository
from stylebot.services.clients import client_state
from stylebot.services.formatting import format_status
from stylebot.services.subscriptions import status_view, utc_today, window_from_paid_through

router = Router(name="status")


@router.message(Command("status"))
async def handle_status(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if user is None:
        return

    # Scoped to the sender's own id: a client can only ever see their own state.
    client = await repository.get_by_telegram_id(session, user.id)
    if client is None:
        await message.answer(format_status(status_view(None, None), None))
        return

    subscription = await repository.get_subscription_for_client(session, client.id)
    paid_through = subscription.paid_through if subscription is not None else None
    subscription_status = (
        window_from_paid_through(paid_through).status_on(utc_today())
        if paid_through is not None
        else None
    )

    view = status_view(client_state(client.approved_at, client.is_active), subscription_status)
    await message.answer(format_status(view, paid_through))
