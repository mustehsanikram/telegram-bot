from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from stylebot.db import repository

FIRST_SEEN = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


async def test_datetime_round_trips_as_aware_utc(session: AsyncSession) -> None:
    await repository.create_pending(session, 4242, "Ada", FIRST_SEEN)
    session.expunge_all()

    found = await repository.get_by_telegram_id(session, 4242)

    assert found is not None
    assert found.first_seen_at.tzinfo is not None, "read back naive"
    assert found.first_seen_at == FIRST_SEEN


async def test_non_utc_input_is_normalised(session: AsyncSession) -> None:
    kabul = timezone(timedelta(hours=4, minutes=30))
    same_instant = FIRST_SEEN.astimezone(kabul)

    await repository.create_pending(session, 7, "Grace", same_instant)
    session.expunge_all()

    found = await repository.get_by_telegram_id(session, 7)

    assert found is not None
    assert found.first_seen_at == FIRST_SEEN


async def test_naive_input_is_rejected(session: AsyncSession) -> None:
    """A naive write is a bug at the call site, not something to silently assume UTC."""
    # SQLAlchemy wraps a bind-param failure, so the ValueError arrives as the cause.
    with pytest.raises(StatementError) as caught:
        naive = datetime(2026, 3, 1, 10, 0)  # noqa: DTZ001  the naivety is the thing under test
        await repository.create_pending(session, 9, "Nobody", naive)

    assert isinstance(caught.value.orig, ValueError)
    assert "naive datetime" in str(caught.value.orig)
