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


async def test_list_clients_orders_pending_first_then_by_arrival(
    session: AsyncSession,
) -> None:
    # Seeded out of display order on purpose.
    approved_early = await repository.create_pending(
        session, 1, "Approved Early", datetime(2026, 1, 1, tzinfo=UTC)
    )
    await repository.mark_approved(session, approved_early, APPROVED_ON)

    pending_late = await repository.create_pending(
        session, 2, "Pending Late", datetime(2026, 5, 1, tzinfo=UTC)
    )
    pending_early = await repository.create_pending(
        session, 3, "Pending Early", datetime(2026, 2, 1, tzinfo=UTC)
    )
    removed = await repository.create_pending(
        session, 4, "Removed", datetime(2026, 1, 15, tzinfo=UTC)
    )
    await repository.mark_removed(session, removed)

    listed = await repository.list_clients(session)

    assert [c.display_name for c in listed] == [
        "Pending Early",
        "Pending Late",
        "Approved Early",
    ]
    assert pending_early.id is not None and pending_late.id is not None


async def test_list_clients_excludes_removed(session: AsyncSession) -> None:
    client = await repository.create_pending(session, 7, "Gone", FIRST_SEEN)
    assert len(await repository.list_clients(session)) == 1

    await repository.mark_removed(session, client)

    assert await repository.list_clients(session) == []


async def test_list_clients_on_an_empty_registry(session: AsyncSession) -> None:
    assert await repository.list_clients(session) == []
