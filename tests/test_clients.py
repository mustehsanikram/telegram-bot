from datetime import UTC, datetime

import pytest

from stylebot.services.clients import ClientState, client_state

APPROVED_ON = datetime(2026, 3, 14, 9, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("approved_at", "is_active", "expected"),
    [
        (None, True, ClientState.PENDING),
        (APPROVED_ON, True, ClientState.APPROVED),
        (None, False, ClientState.REMOVED),
        (APPROVED_ON, False, ClientState.REMOVED),
    ],
    ids=["awaiting approval", "approved", "declined before approval", "removed after approval"],
)
def test_client_state(approved_at: datetime | None, is_active: bool, expected: ClientState) -> None:
    assert client_state(approved_at, is_active) is expected


def test_removal_outranks_approval() -> None:
    """An approved client who is deactivated reads as removed, not approved."""
    assert client_state(APPROVED_ON, is_active=False) is ClientState.REMOVED
