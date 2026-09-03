from datetime import date

import pytest

from stylebot.services.clients import ClientState
from stylebot.services.formatting import format_status
from stylebot.services.subscriptions import StatusView, SubscriptionStatus, status_view

PAID_THROUGH = date(2026, 3, 14)


@pytest.mark.parametrize(
    ("client", "subscription", "expected"),
    [
        (None, None, StatusView.UNKNOWN),
        (ClientState.PENDING, None, StatusView.PENDING),
        (ClientState.REMOVED, None, StatusView.REMOVED),
        (ClientState.APPROVED, None, StatusView.NO_SUBSCRIPTION),
        (ClientState.APPROVED, SubscriptionStatus.ACTIVE, StatusView.ACTIVE),
        (ClientState.APPROVED, SubscriptionStatus.EXPIRING_SOON, StatusView.EXPIRING_SOON),
        (ClientState.APPROVED, SubscriptionStatus.EXPIRED, StatusView.EXPIRED),
    ],
    ids=["never messaged", "pending", "removed", "approved but unpaid",
         "active", "expiring soon", "expired"],
)
def test_status_view(
    client: ClientState | None, subscription: SubscriptionStatus | None, expected: StatusView
) -> None:
    assert status_view(client, subscription) is expected


def test_registry_state_outranks_a_stale_subscription() -> None:
    """A removed client must not be told their subscription is still active."""
    assert status_view(ClientState.REMOVED, SubscriptionStatus.ACTIVE) is StatusView.REMOVED
    assert status_view(ClientState.PENDING, SubscriptionStatus.ACTIVE) is StatusView.PENDING


def test_every_view_produces_a_distinct_message() -> None:
    messages = {
        view: format_status(view, PAID_THROUGH if _needs_date(view) else None)
        for view in StatusView
    }

    assert len(set(messages.values())) == len(StatusView), "two views share wording"


def _needs_date(view: StatusView) -> bool:
    return view in {StatusView.ACTIVE, StatusView.EXPIRING_SOON, StatusView.EXPIRED}


@pytest.mark.parametrize(
    "view", [StatusView.ACTIVE, StatusView.EXPIRING_SOON, StatusView.EXPIRED]
)
def test_dated_views_name_the_date_in_human_form(view: StatusView) -> None:
    message = format_status(view, PAID_THROUGH)

    assert "14 March 2026" in message
    assert "2026-03-14" not in message


@pytest.mark.parametrize(
    "view", [StatusView.ACTIVE, StatusView.EXPIRING_SOON, StatusView.EXPIRED]
)
def test_a_dated_view_without_a_date_is_a_caller_bug(view: StatusView) -> None:
    with pytest.raises(ValueError, match="paid-through date"):
        format_status(view, None)


@pytest.mark.parametrize(
    "view", [StatusView.UNKNOWN, StatusView.PENDING, StatusView.REMOVED,
             StatusView.NO_SUBSCRIPTION]
)
def test_undated_views_never_mention_a_date(view: StatusView) -> None:
    assert "2026" not in format_status(view, None)
