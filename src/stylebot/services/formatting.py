from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from html import escape

from stylebot.services.clients import ClientState


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


def human_date(value: datetime) -> str:
    """1 March 2026. Avoids %-d, which is not portable to Windows."""
    return f"{value.day} {value:%B %Y}"


def _format_row(row: ClientRow) -> str:
    return (
        f"- {escape_html(row.display_name)} <code>{row.telegram_user_id}</code>\n"
        f"  first seen {human_date(row.first_seen_at)}"
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
