from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from html import escape

from stylebot.services.clients import ClientState
from stylebot.services.subscriptions import StatusView, SubscriptionStatus


def escape_html(value: str) -> str:
    """Make client-supplied text safe for Telegram's HTML parse mode.

    Telegram requires &, < and > to be entities. Quotes are left alone: escaping
    them would show &#x27; where a name contains an apostrophe.
    """
    return escape(value, quote=False)


# Telegram rejects a sendMessage over this length outright, so an oversized
# listing means the admin gets nothing at all rather than a partial list.
TELEGRAM_MESSAGE_LIMIT = 4096

EMPTY_REGISTRY = "No clients yet. Someone appears here once they message the bot."


@dataclass(frozen=True, slots=True)
class ClientRow:
    """What the listing needs, decoupled from the ORM so formatting stays pure."""

    display_name: str
    telegram_user_id: int
    state: ClientState
    first_seen_at: datetime
    paid_through: date | None = None
    subscription: SubscriptionStatus | None = None


def human_date(value: date) -> str:
    """1 March 2026. Accepts a date or a datetime; avoids %-d, unportable on Windows."""
    return f"{value.day} {value:%B %Y}"


SUBSCRIPTION_LABELS = {
    SubscriptionStatus.ACTIVE: "active to",
    SubscriptionStatus.EXPIRING_SOON: "expiring, paid to",
    SubscriptionStatus.EXPIRED: "expired on",
}

NO_SUBSCRIPTION_LABEL = "no payment recorded"


def _subscription_line(row: ClientRow) -> str:
    """Only approved clients have anything to say here."""
    if row.state is not ClientState.APPROVED:
        return ""
    if row.subscription is None or row.paid_through is None:
        return f"\n  {NO_SUBSCRIPTION_LABEL}"
    return f"\n  {SUBSCRIPTION_LABELS[row.subscription]} {human_date(row.paid_through)}"


def _format_row(row: ClientRow) -> str:
    return (
        f"- {escape_html(row.display_name)} <code>{row.telegram_user_id}</code>\n"
        f"  first seen {human_date(row.first_seen_at)}"
        f"{_subscription_line(row)}"
    )


def _render(rows: Sequence[ClientRow], omitted: int) -> str:
    pending = [r for r in rows if r.state is ClientState.PENDING]
    approved = [r for r in rows if r.state is ClientState.APPROVED]

    blocks = [f"<b>Clients</b> ({len(rows) + omitted})"]
    if pending:
        blocks.append(
            "<b>Waiting for approval</b>\n" + "\n".join(_format_row(r) for r in pending)
        )
    if approved:
        blocks.append("<b>Approved</b>\n" + "\n".join(_format_row(r) for r in approved))
    if omitted:
        blocks.append(f"{omitted} more not shown.")
    return "\n\n".join(blocks)


def format_client_list(
    rows: Sequence[ClientRow], limit: int = TELEGRAM_MESSAGE_LIMIT
) -> str:
    """One message listing the registry, trimmed to fit Telegram's limit."""
    if not rows:
        return EMPTY_REGISTRY

    shown = list(rows)
    while shown:
        text = _render(shown, omitted=len(rows) - len(shown))
        if len(text) <= limit:
            return text
        shown.pop()

    # Not even one row fits, which means a pathological name. Report the count.
    return _render([], omitted=len(rows))


STATUS_MESSAGES = {
    StatusView.UNKNOWN: (
        "I do not have you on the list yet. Send /start and your stylist will review it."
    ),
    StatusView.PENDING: (
        "You are on the list, waiting for your stylist to review it.\n\n"
        "There is nothing else you need to do."
    ),
    StatusView.REMOVED: (
        "Your access has ended. Please contact your stylist directly if you would "
        "like to come back."
    ),
    StatusView.NO_SUBSCRIPTION: (
        "You are approved, but no payment has been recorded yet.\n\n"
        "Your stylist will set your subscription up shortly."
    ),
}


def format_status(view: StatusView, paid_through: date | None) -> str:
    """The client's own subscription state, in one short message."""
    fixed = STATUS_MESSAGES.get(view)
    if fixed is not None:
        return fixed

    # The remaining views all carry a date, so a missing one is a caller bug.
    if paid_through is None:
        raise ValueError(f"{view} needs a paid-through date")

    when = human_date(paid_through)
    if view is StatusView.ACTIVE:
        return f"You are all set. Your access runs to {when}."
    if view is StatusView.EXPIRING_SOON:
        return (
            f"Your access runs to {when}, which is coming up soon.\n\n"
            "Message your stylist to renew and nothing will be interrupted."
        )
    return f"Your access ended on {when}.\n\nMessage your stylist to start again."
