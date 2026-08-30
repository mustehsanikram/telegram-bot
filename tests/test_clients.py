from datetime import UTC, datetime

import pytest

from stylebot.services.clients import (
    DISPLAY_NAME_MAX,
    ClientState,
    IntakeOutcome,
    client_state,
    display_name_for,
    intake_outcome,
    is_admin,
    parse_telegram_id,
)

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


@pytest.mark.parametrize(
    ("existing", "expected"),
    [
        (None, IntakeOutcome.REGISTERED),
        (ClientState.PENDING, IntakeOutcome.ALREADY_PENDING),
        (ClientState.APPROVED, IntakeOutcome.ALREADY_APPROVED),
        (ClientState.REMOVED, IntakeOutcome.PREVIOUSLY_REMOVED),
    ],
    ids=["unknown sender", "waiting", "already in", "removed"],
)
def test_intake_outcome(existing: ClientState | None, expected: IntakeOutcome) -> None:
    assert intake_outcome(existing) is expected


@pytest.mark.parametrize(
    ("full_name", "username", "expected"),
    [
        ("Ada Lovelace", "ada", "Ada Lovelace"),
        ("  Grace Hopper  ", None, "Grace Hopper"),
        ("", "ada", "@ada"),
        ("   ", "ada", "@ada"),
        ("", None, "id 4242"),
    ],
    ids=["full name", "trimmed", "username fallback", "blank name", "id fallback"],
)
def test_display_name_for(full_name: str, username: str | None, expected: str) -> None:
    assert display_name_for(full_name, username, 4242) == expected


def test_display_name_is_capped_at_the_column_width() -> None:
    assert len(display_name_for("A" * 400, None, 4242)) == DISPLAY_NAME_MAX


def test_long_username_is_also_capped() -> None:
    assert len(display_name_for("", "u" * 400, 4242)) == DISPLAY_NAME_MAX


@pytest.mark.parametrize(
    ("user_id", "admin_ids", "expected"),
    [
        (111, [111], True),
        (111, [222, 111, 333], True),
        (999, [111, 222], False),
        (111, [], False),
    ],
    ids=["sole admin", "one of several", "not an admin", "empty list denies"],
)
def test_is_admin(user_id: int, admin_ids: list[int], expected: bool) -> None:
    assert is_admin(user_id, admin_ids) is expected


def test_empty_admin_list_never_defaults_open() -> None:
    """A misconfigured deployment must lock everyone out, not let everyone in."""
    assert is_admin(1, []) is False
    assert is_admin(0, []) is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("778899", 778899),
        ("  778899  ", 778899),
        (None, None),
        ("", None),
        ("   ", None),
        ("abc", None),
        ("778899 extra", None),
        ("-1001234", None),
        ("0", None),
        ("77.88", None),
    ],
    ids=["plain", "padded", "missing", "empty", "whitespace", "words",
         "two tokens", "negative", "zero", "decimal"],
)
def test_parse_telegram_id(raw: str | None, expected: int | None) -> None:
    assert parse_telegram_id(raw) == expected
