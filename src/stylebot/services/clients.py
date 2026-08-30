from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum


class ClientState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REMOVED = "removed"


def client_state(approved_at: datetime | None, is_active: bool) -> ClientState:
    """Registry state, derived from the two stored fields. Never stored itself."""
    # Checked first: a client who was approved and later removed is removed, not approved.
    if not is_active:
        return ClientState.REMOVED
    if approved_at is None:
        return ClientState.PENDING
    return ClientState.APPROVED


class IntakeOutcome(StrEnum):
    REGISTERED = "registered"
    ALREADY_PENDING = "already_pending"
    ALREADY_APPROVED = "already_approved"
    PREVIOUSLY_REMOVED = "previously_removed"


def intake_outcome(existing: ClientState | None) -> IntakeOutcome:
    """What a /start means, given whatever the registry already holds for the sender."""
    if existing is None:
        return IntakeOutcome.REGISTERED
    if existing is ClientState.PENDING:
        return IntakeOutcome.ALREADY_PENDING
    if existing is ClientState.APPROVED:
        return IntakeOutcome.ALREADY_APPROVED
    return IntakeOutcome.PREVIOUSLY_REMOVED


# Matches the display_name column width; Postgres rejects an overlong value
# where SQLite would silently accept it.
DISPLAY_NAME_MAX = 255


def display_name_for(full_name: str, username: str | None, telegram_user_id: int) -> str:
    """A name the admin can recognise, however sparse the Telegram profile is."""
    if cleaned := full_name.strip():
        return cleaned[:DISPLAY_NAME_MAX]
    if username:
        return f"@{username}"[:DISPLAY_NAME_MAX]
    return f"id {telegram_user_id}"


def is_admin(user_id: int, admin_ids: Sequence[int]) -> bool:
    """Authority comes only from the configured list; an empty list means nobody."""
    return user_id in admin_ids


class DecisionOutcome(StrEnum):
    APPROVED = "approved"
    DECLINED = "declined"
    NOT_FOUND = "not_found"
    ALREADY_APPROVED = "already_approved"
    ALREADY_REMOVED = "already_removed"


def parse_telegram_id(raw: str | None) -> int | None:
    """The id an admin typed, or None if it is not a usable Telegram id."""
    if raw is None:
        return None
    tokens = raw.split()
    if len(tokens) != 1:
        return None
    try:
        value = int(tokens[0])
    except ValueError:
        return None
    # Telegram user ids are positive, so a negative value is a chat id or a typo.
    return value if value > 0 else None
