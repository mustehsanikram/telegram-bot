from datetime import date

import pytest

from stylebot.services.subscriptions import SubscriptionStatus, SubscriptionWindow


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 1, 1), SubscriptionStatus.ACTIVE),
        (date(2026, 1, 27), SubscriptionStatus.EXPIRING_SOON),
        (date(2026, 1, 30), SubscriptionStatus.EXPIRING_SOON),
        (date(2026, 1, 31), SubscriptionStatus.EXPIRED),
    ],
)
def test_status_on(today: date, expected: SubscriptionStatus) -> None:
    window = SubscriptionWindow(expires_on=date(2026, 1, 30))
    assert window.status_on(today) is expected


def test_channel_access_survives_the_final_day() -> None:
    window = SubscriptionWindow(expires_on=date(2026, 1, 30))
    assert window.grants_channel_access_on(date(2026, 1, 30)) is True
    assert window.grants_channel_access_on(date(2026, 1, 31)) is False
