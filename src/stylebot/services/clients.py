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
