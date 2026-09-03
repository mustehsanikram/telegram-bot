# Project Plan

## 1. Problem - What problem are we solving?

Running a paid styling service over Telegram means tracking, by hand, who has
paid, who is overdue, and who should still be able to see the private styling
channel. That bookkeeping is done in a spreadsheet or from memory today, which
causes three concrete failures:

- Lapsed clients keep channel access because nobody remembered to remove them.
- Paying clients get removed by mistake, or wait for a manual re-add.
- Renewals are missed because nobody chased them before the date passed.

The bot makes subscription state the single source of truth, and makes channel
access a consequence of that state rather than a manual chore.

## 2. Users - Who is this for?

**The stylist (admin).** One person, the business owner. Records payments,
sees who is active and who is lapsing, and never touches the channel member
list by hand.

**Styling clients (subscribers).** Paying customers who want access to the
private channel, want to know when their subscription runs out, and want a
reminder before it does. They interact only through direct chat with the bot.

There is no third user type. No staff accounts, no multi-tenant support: this
serves one styling business.

## 3. Features - What does the MVP need?

- Client intake: a prospective client starts a chat with the bot, which captures their
  Telegram account, and the admin approves them into the registry
- Subscription periods with a paid-through date and a derived active/expiring/expired status
- Manual payment recording that extends a client's paid-through date and keeps a payment history
- Automatic private-channel access: granted when a subscription becomes active, revoked when it lapses
- A daily sweep that finds lapsed subscriptions and revokes their access
- Automated renewal reminders sent before a subscription expires

Explicitly out of scope for the MVP:

- Any web UI or dashboard. Telegram is the whole interface.
- Multiple stylists, teams, or role hierarchies beyond one admin list.
- Refunds, proration, and partial-period accounting.
- Styling content itself. The bot manages access, it does not deliver the service.

Clients are never added by typing a raw Telegram user id. A Telegram bot cannot send
the first message to someone who has not contacted it, so a client who was never
captured through their own `/start` could not be sent a renewal reminder. Intake is
therefore always client-initiated and admin-approved.

## 4. Data - What are we storing?

- **Clients** - Telegram user id, display name, when they first messaged the bot, whether
  the admin has approved them, whether they are still active
- **Subscriptions** - which client, paid-through date, plan length in days
- **Payments** - which client, amount, currency, when it was recorded, who recorded it, what period it bought
- **Channel access events** - which client, granted or revoked, when, and why (paid, lapsed, manual override)
- **Reminder log** - which client, which reminder, when it was sent, so the same reminder is never sent twice

No payment card data is ever stored. No styling content or client photos are stored.

### Subscription rules

- **One period is 30 days.** Stored per subscription rather than as a global constant, so an individual client can be put on a different length later without a migration.
- **A subscription counts as expiring soon in its final 3 days.** That same window is when the renewal reminder goes out, so the client is warned and the status agrees.
- **Day boundaries are UTC.** A subscription flips to expired at midnight UTC on the day after `paid_through`. Storing and comparing in one zone avoids a client and the stylist disagreeing about which day it is.

## 5. Tech - What stack are we using?

- Python 3.12, managed by uv
- aiogram 3 for the Telegram bot, long polling
- SQLAlchemy 2 with Alembic migrations
- PostgreSQL in deployment, SQLite for local development and tests
- APScheduler for the daily expiry sweep and reminder jobs
- pytest, ruff, and mypy as the local quality gates

## 6. Monetize - How will this make money?

The bot is not itself a product and is not sold. It is internal tooling for one
styling business, and it protects revenue rather than generating it: subscription
fees are the business's income, and the bot's job is to stop paid access leaking
to lapsed clients and to reduce churn by chasing renewals before they are missed.

## 7. UI/UX - How should this look and feel?

Telegram chat conventions, nothing invented:

- Short messages. A client asking `/status` gets a date and a state, not a paragraph.
- Clear, human dates ("your access runs to 14 March"), never raw timestamps or ISO strings.
- Admin commands are separate from client commands and refuse politely for non-admins.
- Reminders read like a person wrote them, not like a billing system. One nudge, not a dunning sequence.
- Every access change tells the client what happened and what to do next.

## 8. Deployment - Where and how will this ship?

Source lives at `https://github.com/mustehsanikram/telegram-bot`.

Hosted on **Railway** as a worker service. A long-polling bot needs an always-on
process with no inbound HTTP, which rules out anything that sleeps and means no
port binding or health check path is involved.

Railway's filesystem is ephemeral, so storage is a managed **Railway Postgres**
rather than a SQLite file: a SQLite database on the container disk would be
erased on every redeploy, taking the client registry with it.

Known requirements whatever the host:

- Always-on single process. Running two instances would double-send reminders and conflict on polling.
- Managed Postgres. The container filesystem does not survive a redeploy.
- Env vars by name: `BOT_TOKEN`, `PRIVATE_CHANNEL_ID`, `ADMIN_USER_IDS`, `DATABASE_URL`.
- No inbound HTTP needed while on long polling. Switching to webhooks would add a public HTTPS endpoint and a health check path.
