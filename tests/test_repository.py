from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from stylebot.db import repository
from stylebot.services.clients import ClientState, client_state

FIRST_SEEN = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
APPROVED_ON = datetime(2026, 3, 2, 11, 0, tzinfo=UTC)


async def test_create_read_and_approve(session: AsyncSession) -> None:
    created = await repository.create_pending(session, 4242, "Ada L", FIRST_SEEN)
    assert created.id is not None

    found = await repository.get_by_telegram_id(session, 4242)
    assert found is not None
    assert found.display_name == "Ada L"
    assert client_state(found.approved_at, found.is_active) is ClientState.PENDING

    await repository.mark_approved(session, found, APPROVED_ON)
    assert client_state(found.approved_at, found.is_active) is ClientState.APPROVED


async def test_unknown_telegram_id_returns_none(session: AsyncSession) -> None:
    assert await repository.get_by_telegram_id(session, 999) is None


async def test_mark_removed_outranks_approval(session: AsyncSession) -> None:
    client = await repository.create_pending(session, 7, "Grace H", FIRST_SEEN)
    await repository.mark_approved(session, client, APPROVED_ON)
    await repository.mark_removed(session, client)

    assert client_state(client.approved_at, client.is_active) is ClientState.REMOVED
