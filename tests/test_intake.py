from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stylebot.db import repository
from stylebot.db.models import Client
from stylebot.services.clients import DecisionOutcome, IntakeOutcome
from stylebot.services.intake import approve_client, decline_client, register_client

FIRST_SEEN = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
LATER = datetime(2026, 3, 5, 18, 0, tzinfo=UTC)
EVEN_LATER = datetime(2026, 3, 9, 12, 0, tzinfo=UTC)


async def count_clients(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(Client))).scalar_one()


async def test_first_start_registers_a_pending_client(session: AsyncSession) -> None:
    outcome, client = await register_client(session, 4242, "Ada Lovelace", FIRST_SEEN)

    assert outcome is IntakeOutcome.REGISTERED
    assert client.approved_at is None
    assert client.is_active is True
    assert await count_clients(session) == 1


async def test_second_start_is_idempotent(session: AsyncSession) -> None:
    await register_client(session, 4242, "Ada Lovelace", FIRST_SEEN)
    outcome, client = await register_client(session, 4242, "Ada Renamed", LATER)

    assert outcome is IntakeOutcome.ALREADY_PENDING
    assert await count_clients(session) == 1
    # The name the admin first saw is kept, and first_seen_at is not moved.
    assert client.display_name == "Ada Lovelace"
    assert client.first_seen_at == FIRST_SEEN


async def test_start_from_an_approved_client_changes_nothing(session: AsyncSession) -> None:
    _, client = await register_client(session, 7, "Grace Hopper", FIRST_SEEN)
    await repository.mark_approved(session, client, LATER)

    outcome, _ = await register_client(session, 7, "Grace Hopper", LATER)

    assert outcome is IntakeOutcome.ALREADY_APPROVED
    assert await count_clients(session) == 1


async def test_removed_client_stays_removed(session: AsyncSession) -> None:
    _, client = await register_client(session, 9, "Someone Else", FIRST_SEEN)
    await repository.mark_removed(session, client)

    outcome, returned = await register_client(session, 9, "Someone Else", LATER)

    assert outcome is IntakeOutcome.PREVIOUSLY_REMOVED
    assert returned.is_active is False
    assert await count_clients(session) == 1


async def test_losing_a_race_still_answers_the_client(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two near-simultaneous /start updates: the loser must recover, not crash."""
    async with session_factory() as writer:
        await repository.create_pending(writer, 4242, "First writer", FIRST_SEEN)
        await writer.commit()

    real_lookup = repository.get_by_telegram_id
    lookups = 0

    async def missing_on_first_lookup(
        session: AsyncSession, telegram_user_id: int
    ) -> Client | None:
        nonlocal lookups
        lookups += 1
        # Simulates reading before the competing insert committed.
        if lookups == 1:
            return None
        return await real_lookup(session, telegram_user_id)

    monkeypatch.setattr(repository, "get_by_telegram_id", missing_on_first_lookup)

    async with session_factory() as loser:
        outcome, client = await register_client(loser, 4242, "Second writer", LATER)

    assert outcome is IntakeOutcome.ALREADY_PENDING
    assert client.display_name == "First writer"
    assert lookups == 2, "the recovery re-read did not happen"


async def test_approve_moves_a_pending_client_to_approved(session: AsyncSession) -> None:
    await register_client(session, 4242, "Ada", FIRST_SEEN)

    outcome, client = await approve_client(session, 4242, LATER)

    assert outcome is DecisionOutcome.APPROVED
    assert client is not None
    assert client.approved_at == LATER


async def test_approving_twice_changes_nothing(session: AsyncSession) -> None:
    await register_client(session, 4242, "Ada", FIRST_SEEN)
    await approve_client(session, 4242, LATER)

    outcome, client = await approve_client(session, 4242, EVEN_LATER)

    assert outcome is DecisionOutcome.ALREADY_APPROVED
    assert client is not None
    assert client.approved_at == LATER, "the original approval time must be preserved"


async def test_approving_an_unknown_id_is_reported_not_raised(session: AsyncSession) -> None:
    outcome, client = await approve_client(session, 12345, LATER)

    assert outcome is DecisionOutcome.NOT_FOUND
    assert client is None


async def test_decline_removes_a_pending_client(session: AsyncSession) -> None:
    await register_client(session, 4242, "Ada", FIRST_SEEN)

    outcome, client = await decline_client(session, 4242)

    assert outcome is DecisionOutcome.DECLINED
    assert client is not None
    assert client.is_active is False


async def test_decline_also_removes_an_approved_client(session: AsyncSession) -> None:
    await register_client(session, 4242, "Ada", FIRST_SEEN)
    await approve_client(session, 4242, LATER)

    outcome, _ = await decline_client(session, 4242)

    assert outcome is DecisionOutcome.DECLINED


async def test_a_removed_client_cannot_be_approved_back(session: AsyncSession) -> None:
    """Readmission is deliberately out of scope; it must refuse, not silently work."""
    await register_client(session, 4242, "Ada", FIRST_SEEN)
    await decline_client(session, 4242)

    outcome, client = await approve_client(session, 4242, EVEN_LATER)

    assert outcome is DecisionOutcome.ALREADY_REMOVED
    assert client is not None
    assert client.is_active is False
