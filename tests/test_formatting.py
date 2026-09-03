from datetime import UTC, date, datetime

import pytest

from stylebot.handlers.admin import CONFIRMATIONS
from stylebot.handlers.notifications import new_client_message
from stylebot.services.clients import ClientState, DecisionOutcome
from stylebot.services.formatting import (
    EMPTY_REGISTRY,
    SUBSCRIPTION_LABELS,
    TELEGRAM_MESSAGE_LIMIT,
    ClientRow,
    escape_html,
    format_client_list,
)
from stylebot.services.subscriptions import SubscriptionStatus

# A Telegram display name is whatever the client typed into their profile.
HOSTILE_NAME = "<b>Ada</b> </code> & co"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Ada Lovelace", "Ada Lovelace"),
        ("<b>bold</b>", "&lt;b&gt;bold&lt;/b&gt;"),
        ("Tom & Jerry", "Tom &amp; Jerry"),
        ("</code>", "&lt;/code&gt;"),
        ("", ""),
    ],
    ids=["plain", "tags", "ampersand", "closing tag", "empty"],
)
def test_escape_html(raw: str, expected: str) -> None:
    assert escape_html(raw) == expected


def test_apostrophes_are_left_readable() -> None:
    """Escaping quotes would render O&#x27;Brien in the admin's list."""
    assert escape_html("O'Brien") == "O'Brien"


def test_escaping_is_not_applied_twice() -> None:
    once = escape_html("Tom & Jerry")
    assert escape_html(once) != once, "double escaping is visible, so escape at render only"


def test_admin_notification_neutralises_a_hostile_name() -> None:
    message = new_client_message(HOSTILE_NAME, 778899)

    assert "<b>Ada</b>" not in message
    assert "</code> &" not in message
    assert "&lt;b&gt;Ada&lt;/b&gt;" in message
    # The bot's own markup must survive.
    assert "<code>778899</code>" in message


@pytest.mark.parametrize(
    "outcome",
    [
        DecisionOutcome.APPROVED,
        DecisionOutcome.DECLINED,
        DecisionOutcome.ALREADY_APPROVED,
        DecisionOutcome.ALREADY_REMOVED,
    ],
)
def test_confirmation_templates_accept_an_escaped_name(outcome: DecisionOutcome) -> None:
    rendered = CONFIRMATIONS[outcome].format(name=escape_html(HOSTILE_NAME), target=778899)

    assert "<b>Ada</b>" not in rendered
    assert "&lt;b&gt;Ada&lt;/b&gt;" in rendered


def row(name: str, uid: int, state: ClientState, day: int = 1) -> ClientRow:
    return ClientRow(
        display_name=name,
        telegram_user_id=uid,
        state=state,
        first_seen_at=datetime(2026, 3, day, 12, 0, tzinfo=UTC),
    )


def test_empty_registry_says_so_rather_than_showing_a_bare_header() -> None:
    assert format_client_list([]) == EMPTY_REGISTRY


def test_mixed_list_separates_pending_from_approved() -> None:
    text = format_client_list(
        [
            row("Ada", 1, ClientState.PENDING),
            row("Bob", 2, ClientState.APPROVED),
        ]
    )

    assert "<b>Clients</b> (2)" in text
    assert "Waiting for approval" in text
    assert "Approved" in text
    assert text.index("Waiting for approval") < text.index("<b>Approved</b>")
    assert "<code>1</code>" in text and "<code>2</code>" in text


def test_a_section_is_omitted_when_it_has_no_rows() -> None:
    text = format_client_list([row("Ada", 1, ClientState.PENDING)])

    assert "Waiting for approval" in text
    assert "<b>Approved</b>" not in text


def test_dates_are_human_readable() -> None:
    text = format_client_list([row("Ada", 1, ClientState.PENDING, day=14)])

    assert "first seen 14 March 2026" in text
    assert "2026-03-14" not in text
    assert "00:00" not in text


def test_a_hostile_name_cannot_break_the_listing() -> None:
    text = format_client_list([row("</code><b>evil", 1, ClientState.PENDING)])

    assert "<b>evil" not in text
    assert "&lt;/code&gt;&lt;b&gt;evil" in text
    # The bot's own markup still works.
    assert "<code>1</code>" in text


def test_a_long_list_is_trimmed_to_fit_and_reports_the_remainder() -> None:
    rows = [row(f"Client Number {n:03d}", 1000 + n, ClientState.PENDING) for n in range(400)]

    text = format_client_list(rows)

    assert len(text) <= TELEGRAM_MESSAGE_LIMIT
    assert "more not shown." in text
    assert "<b>Clients</b> (400)" in text, "the header must report the true total, not the shown count"


def test_trimming_reports_an_accurate_omitted_count() -> None:
    rows = [row(f"Client {n:03d}", 1000 + n, ClientState.PENDING) for n in range(400)]

    text = format_client_list(rows)
    shown = text.count("<code>")
    omitted = int(text.split("more not shown.")[0].strip().split("\n")[-1].strip())

    assert shown + omitted == 400


def test_a_short_list_is_not_trimmed() -> None:
    rows = [row(f"Client {n}", n, ClientState.PENDING) for n in range(5)]

    text = format_client_list(rows)

    assert "more not shown." not in text
    assert text.count("<code>") == 5


def approved_row(name: str, uid: int, paid_through: date | None,
                 status: SubscriptionStatus | None) -> ClientRow:
    return ClientRow(
        display_name=name,
        telegram_user_id=uid,
        state=ClientState.APPROVED,
        first_seen_at=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
        paid_through=paid_through,
        subscription=status,
    )


def test_listing_tells_the_four_subscription_cases_apart() -> None:
    text = format_client_list(
        [
            approved_row("Active One", 1, date(2026, 4, 20), SubscriptionStatus.ACTIVE),
            approved_row("Expiring One", 2, date(2026, 3, 4), SubscriptionStatus.EXPIRING_SOON),
            approved_row("Expired One", 3, date(2026, 2, 1), SubscriptionStatus.EXPIRED),
            approved_row("Unpaid One", 4, None, None),
        ]
    )

    assert "active to 20 April 2026" in text
    assert "expiring, paid to 4 March 2026" in text
    assert "expired on 1 February 2026" in text
    assert "no payment recorded" in text


def test_a_pending_client_shows_no_subscription_line() -> None:
    """Nothing has been paid for someone not yet approved, so the line is noise."""
    text = format_client_list([row("Ada", 1, ClientState.PENDING)])

    assert "no payment recorded" not in text
    assert "active to" not in text


def test_an_approved_client_without_a_subscription_says_so() -> None:
    text = format_client_list([approved_row("Grace", 9, None, None)])

    assert "no payment recorded" in text


def test_every_subscription_status_has_a_label() -> None:
    """A missing label would raise KeyError while rendering the admin's list."""
    assert set(SUBSCRIPTION_LABELS) == set(SubscriptionStatus)
