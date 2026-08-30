from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class SubscriptionWindow:
    """A paid-through window, evaluated against a reference day."""

    expires_on: date
    reminder_lead_days: int = 3

    def status_on(self, today: date) -> SubscriptionStatus:
        if today > self.expires_on:
            return SubscriptionStatus.EXPIRED
        if today >= self.expires_on - timedelta(days=self.reminder_lead_days):
            return SubscriptionStatus.EXPIRING_SOON
        return SubscriptionStatus.ACTIVE

    def grants_channel_access_on(self, today: date) -> bool:
        return self.status_on(today) is not SubscriptionStatus.EXPIRED
