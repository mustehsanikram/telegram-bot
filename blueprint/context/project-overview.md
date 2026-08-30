# StyleBot - Project Overview

<!-- blueprint:source-hash 9e05e237f7387adaa20d3f0322a2d53bf5271df469c019c2843aa65efda2e757 -->

> **Generated file. Don't hand-edit.** Re-run `/overview` when `project-plan.md`
> or `build-plan.md` changes materially.

> A Telegram bot that makes private-channel access a consequence of subscription
> state for a one-person styling business.

## Problem

Subscription bookkeeping for a paid styling service is done by hand today, in a
spreadsheet or from memory. Lapsed clients keep channel access because nobody
removed them, paying clients get removed by mistake, and renewals slip past
unchased. The bot makes subscription state authoritative and derives channel
access from it, so nobody edits the channel member list manually.

## Users

| User | Needs |
|---|---|
| **The stylist (admin)** | One person, the business owner. Records payments, sees who is active and who is lapsing, never touches the channel member list by hand. |
| **Styling clients (subscribers)** | Paying customers. Want channel access while paid up, want to know when their subscription runs out, and want a reminder before it does. Direct chat with the bot only. |

Access tiers are just these two. Admin identity comes from `ADMIN_USER_IDS`;
everyone else is a client. No staff accounts, no multi-tenancy.

## Features

In build-plan order. The headline feature is **4, channel access control**:
everything before it exists to make that decision correctly, and everything after
it keeps that decision current over time.

1. **Client registry** - prospective clients reach the bot, the admin approves them, the registry lists everyone. Split into
   **1a** persistence foundation, **1b** client intake, **1c** client listing.
2. **Subscription periods** - a paid-through date per client and a derived active/expiring/expired status; `/status` lets a client check their own.
3. **Manual payment recording** - admin records a payment that extends the paid-through date and appends to that client's payment history.
4. **Channel access control** - grant access when a subscription becomes active, revoke when it lapses, log every change.
5. **Daily expiry sweep** - scheduled job that finds subscriptions that lapsed overnight and revokes their access.
6. **Renewal reminders** - scheduled reminder before expiry, sent once per period.
7. **Automatic payment collection** (post-MVP) - accept payment inside Telegram so subscriptions extend without manual recording.
8. **Deployment readiness** (post-MVP) - pick the host, add provider config, verify an always-on single process, smoke-test against the real channel.

## Data model

Derived from project-plan section 4 and the features that use it. Money is stored
as integer minor units and timestamps as timezone-aware UTC, per
`coding-standards.md`.

### Client

- `id` (int, PK) - internal id
- `telegram_user_id` (int, unique, indexed) - the Telegram account; how every lookup starts
- `display_name` (str) - what the admin sees in `/clients`
- `first_seen_at` (datetime, UTC) - when they first messaged the bot
- `approved_at` (datetime, UTC, nullable) - null means pending; set when the admin approves
- `is_active` (bool) - false means a former or declined client, kept for payment history
- has one `Subscription`, has many `Payment`, `AccessEvent`, `ReminderLog`

> **Locked shape.** Registry state is *derived*, not stored: pending when
> `approved_at` is null, approved when it is set, removed when `is_active` is
> false. Same rule as subscription status - no `state` column.

> **Why intake is client-initiated.** A Telegram bot cannot send the first
> message to a user who has never contacted it. A client added by raw id could
> never be sent a renewal reminder, so feature 6 would silently fail for them.
> `first_seen_at` being non-null is the proof the bot can reach them.

### Subscription

- `id` (int, PK)
- `client_id` (int, FK -> Client, unique) - one current subscription per client
- `paid_through` (date) - the authoritative field; every status decision reads this
- `plan_length_days` (int) - what one payment buys, so item 3 knows how far to extend
- `updated_at` (datetime, UTC)

> **Locked shape.** Status is *derived* from `paid_through`, never stored as a
> column. `SubscriptionWindow.status_on(today)` in
> `src/stylebot/services/subscriptions.py` already implements this and returns
> `active` / `expiring_soon` / `expired`. Features 4, 5, and 6 all depend on
> status being computed the same way from the same field. Do not add a
> `status` column.

### Payment

- `id` (int, PK)
- `client_id` (int, FK -> Client)
- `amount_minor` (int) - minor units, never float
- `currency` (str, ISO 4217) - see Open questions
- `recorded_at` (datetime, UTC)
- `recorded_by` (int) - admin Telegram user id, so manual entries are attributable
- `period_start` (date), `period_end` (date) - which window this payment bought
- `source` (str) - `manual` today; feature 7 adds provider values without a schema change

### AccessEvent

- `id` (int, PK)
- `client_id` (int, FK -> Client)
- `action` (str) - `granted` or `revoked`
- `reason` (str) - `paid`, `lapsed`, or `manual_override`
- `occurred_at` (datetime, UTC)

> Append-only audit trail. It is the answer to "why did this person lose access",
> which is the question the admin will actually ask in production.

### ReminderLog

- `id` (int, PK)
- `client_id` (int, FK -> Client)
- `period_end` (date) - which subscription period the reminder was for
- `sent_at` (datetime, UTC)
- unique on (`client_id`, `period_end`) - the constraint that makes feature 6 idempotent, so a restarted scheduler cannot double-send

## Tech stack

| Tech | Role |
|---|---|
| **Python 3.12 + uv** | Runtime and toolchain; uv owns the venv and lockfile |
| **aiogram 3** | Telegram bot framework, long polling |
| **SQLAlchemy 2 + Alembic** | ORM and schema migrations |
| **PostgreSQL** | Storage in deployment (Railway Postgres); SQLite locally and in tests |
| **APScheduler** | Daily expiry sweep (feature 5) and reminder jobs (feature 6) |
| **pytest, ruff, mypy** | Local quality gates; tests are a gate for logic-bearing steps |

## Monetization

Not a product and not sold. This is internal tooling for one styling business.
It protects revenue rather than generating it: subscription fees are the
business's income, and the bot stops paid access leaking to lapsed clients while
reducing churn by chasing renewals before they are missed.

## UI/UX

Telegram chat conventions. Short messages, human dates ("your access runs to
14 March") rather than timestamps, and reminders that read like a person wrote
them. Every access change tells the client what happened and what to do next.

There is no web UI. The command surface is the interface:

**Client commands**

- `/start` - introduce the bot and what it manages
- `/status` - current subscription state and the date access runs to

**Admin commands** (rejected politely for non-admins)

- `/clients` - everyone in the registry, pending and approved (feature 1c)
- approve or decline a pending client (feature 1b)
- record a payment against a client (feature 3)

> Exact admin command names are a `/feature` decision, not fixed here.

## Deployment

Source lives at `https://github.com/mustehsanikram/telegram-bot`.

Hosted on **Railway** as a worker service: long polling, no inbound HTTP, so no
port binding and no health check path.

Constraints:

- **Always-on single process.** Two pollers conflict on `getUpdates` and would double-send reminders, so the service stays at one replica.
- **Managed Postgres.** Railway's container filesystem is ephemeral; a SQLite file would be erased on every redeploy.
- **Env vars by name** - `BOT_TOKEN`, `PRIVATE_CHANNEL_ID`, `ADMIN_USER_IDS`, `DATABASE_URL`.
- **No inbound HTTP** while on long polling. Moving to webhooks would add a public HTTPS endpoint and a health check path.
- **Channel permission** - the bot must be an admin of the private channel with rights to invite and restrict members, or feature 4 fails at runtime.

## Open questions

Resolve in the plans, then re-run `/overview`.

1. **Currency and price** - no currency or subscription price is specified. `Payment.currency` exists but nothing says what goes in it.
2. **Plan length** - `plan_length_days` has no value. Monthly (30 days) is assumed but never stated.
3. **Reminder lead time** - the scaffolded `SubscriptionWindow` defaults to 3 days. The plans never state the intended lead time.
4. **Scheduler timezone** - "daily" is undefined without one. Reminder timing depends on it.
