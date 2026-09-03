import ast
import inspect
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from stylebot.db.models import Subscription
from stylebot.services.subscriptions import (
    DEFAULT_PLAN_LENGTH_DAYS,
    REMINDER_LEAD_DAYS,
    SubscriptionStatus,
    SubscriptionWindow,
    utc_today,
)


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


# expires_on 30 Jan, 3-day lead: 26 Jan is the last fully active day.
BOUNDARY_WINDOW = SubscriptionWindow(expires_on=date(2026, 1, 30))


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 1, 26), SubscriptionStatus.ACTIVE),
        (date(2026, 1, 27), SubscriptionStatus.EXPIRING_SOON),
        (date(2026, 1, 30), SubscriptionStatus.EXPIRING_SOON),
        (date(2026, 1, 31), SubscriptionStatus.EXPIRED),
    ],
    ids=[
        "day before the warning starts",
        "first warning day",
        "paid_through itself is still covered",
        "day after paid_through",
    ],
)
def test_transition_boundaries(today: date, expected: SubscriptionStatus) -> None:
    assert BOUNDARY_WINDOW.status_on(today) is expected


def test_access_survives_the_whole_paid_through_day() -> None:
    """An off-by-one here would revoke a paying client's channel a day early."""
    assert BOUNDARY_WINDOW.grants_channel_access_on(date(2026, 1, 30)) is True
    assert BOUNDARY_WINDOW.grants_channel_access_on(date(2026, 1, 31)) is False


def test_default_lead_comes_from_the_named_constant() -> None:
    assert SubscriptionWindow(expires_on=date(2026, 1, 30)).reminder_lead_days == (
        REMINDER_LEAD_DAYS
    )


def test_utc_today_matches_the_utc_date() -> None:
    assert utc_today() == datetime.now(UTC).date()


def test_no_local_date_call_in_the_subscription_rules() -> None:
    """A UTC host hides a local-date bug, so ban the call rather than trust review.

    Parsed, not grepped: the docstrings here mention the call deliberately.
    """
    source = Path(inspect.getfile(utc_today)).read_text(encoding="utf-8")
    today_calls = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "today"
    ]

    assert today_calls == [], "date.today() leaks the host timezone into the rule"


def test_the_plan_length_default_is_recorded() -> None:
    assert DEFAULT_PLAN_LENGTH_DAYS == 30


def test_model_default_matches_the_domain_constant() -> None:
    """models.py cannot import services, so a literal 30 lives there. Pin the two together."""
    column_default = Subscription.__table__.columns["plan_length_days"].default

    assert column_default is not None
    assert column_default.arg == DEFAULT_PLAN_LENGTH_DAYS


def test_one_subscription_per_client_is_enforced_by_the_schema() -> None:
    client_id = Subscription.__table__.columns["client_id"]

    assert client_id.unique is True, "two subscriptions for one client would break status"
    assert [fk.target_fullname for fk in client_id.foreign_keys] == ["clients.id"]
