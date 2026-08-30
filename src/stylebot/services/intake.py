from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from stylebot.db import repository
from stylebot.db.models import Client
from stylebot.services.clients import (
    ClientState,
    DecisionOutcome,
    IntakeOutcome,
    client_state,
    intake_outcome,
)


async def register_client(
    session: AsyncSession,
    telegram_user_id: int,
    display_name: str,
    now: datetime,
) -> tuple[IntakeOutcome, Client]:
    """Record a /start. Creates a pending client only the first time."""
    existing = await repository.get_by_telegram_id(session, telegram_user_id)

    if existing is None:
        try:
            # A savepoint so a losing race rolls back the insert alone, leaving
            # the surrounding transaction usable.
            async with session.begin_nested():
                created = await repository.create_pending(
                    session, telegram_user_id, display_name, now
                )
        except IntegrityError:
            # Another update for the same sender landed between our read and our
            # insert. Re-read rather than failing the client's /start.
            existing = await repository.get_by_telegram_id(session, telegram_user_id)
            if existing is None:
                raise
        else:
            return IntakeOutcome.REGISTERED, created

    return intake_outcome(client_state(existing.approved_at, existing.is_active)), existing


async def approve_client(
    session: AsyncSession, telegram_user_id: int, now: datetime
) -> tuple[DecisionOutcome, Client | None]:
    client = await repository.get_by_telegram_id(session, telegram_user_id)
    if client is None:
        return DecisionOutcome.NOT_FOUND, None

    state = client_state(client.approved_at, client.is_active)
    if state is ClientState.APPROVED:
        return DecisionOutcome.ALREADY_APPROVED, client
    if state is ClientState.REMOVED:
        # Readmission needs a decision about the client's history, so refuse here.
        return DecisionOutcome.ALREADY_REMOVED, client

    await repository.mark_approved(session, client, now)
    return DecisionOutcome.APPROVED, client


async def decline_client(
    session: AsyncSession, telegram_user_id: int
) -> tuple[DecisionOutcome, Client | None]:
    client = await repository.get_by_telegram_id(session, telegram_user_id)
    if client is None:
        return DecisionOutcome.NOT_FOUND, None

    if client_state(client.approved_at, client.is_active) is ClientState.REMOVED:
        return DecisionOutcome.ALREADY_REMOVED, client

    await repository.mark_removed(session, client)
    return DecisionOutcome.DECLINED, client
