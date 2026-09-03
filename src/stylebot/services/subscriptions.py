from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from stylebot.services.clients import ClientState

# One paid period. Stored per subscription, so this is only the default.
DEFAULT_PLAN_LENGTH_DAYS = 30

# How long before expiry a subscription reads as expiring soon. Feature 6 sends
# its renewal reminder in the same window, so the two cannot disagree.
REMINDER_LEAD_DAYS = 3


def utc_today() -> date:
    """Today in UTC.

    Day boundaries are UTC by decision, and date.today() would return the
    machine's local date instead: correct by accident on a UTC host, wrong
    everywhere else.
    """
    return datetime.now(UTC).date()


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class SubscriptionWindow:
    """A paid-through window, evaluated against a reference day."""

    expires_on: date
    reminder_lead_days: int = field(default=REMINDER_LEAD_DAYS)

    def status_on(self, today: date) -> SubscriptionStatus:
        # expires_on is inclusive: access runs to the end of that day.
        if today > self.expires_on:
            return SubscriptionStatus.EXPIRED
        if today >= self.expires_on - timedelta(days=self.reminder_lead_days):
            return SubscriptionStatus.EXPIRING_SOON
        return SubscriptionStatus.ACTIVE

    def grants_channel_access_on(self, today: date) -> bool:
        return self.status_on(today) is not SubscriptionStatus.EXPIRED


def window_from_paid_through(paid_through: date) -> SubscriptionWindow:
    """The status window for a stored paid-through date."""
    return SubscriptionWindow(expires_on=paid_through)


class StatusView(StrEnum):
    """What /status should tell a sender. One value per reachable case."""

    UNKNOWN = "unknown"
    PENDING = "pending"
    REMOVED = "removed"
    NO_SUBSCRIPTION = "no_subscription"
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


_SUBSCRIPTION_VIEWS = {
    SubscriptionStatus.ACTIVE: StatusView.ACTIVE,
    SubscriptionStatus.EXPIRING_SOON: StatusView.EXPIRING_SOON,
    SubscriptionStatus.EXPIRED: StatusView.EXPIRED,
}


def status_view(
    client: ClientState | None, subscription: SubscriptionStatus | None
) -> StatusView:
    """Registry state first: an unapproved client has nothing to report about."""
    if client is None:
        return StatusView.UNKNOWN
    if client is ClientState.REMOVED:
        return StatusView.REMOVED
    if client is ClientState.PENDING:
        return StatusView.PENDING
    if subscription is None:
        return StatusView.NO_SUBSCRIPTION
    return _SUBSCRIPTION_VIEWS[subscription]
