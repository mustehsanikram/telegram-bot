# Feature: Subscription periods

**From build-plan:** feature 2
**Status:** verified

## Goal

Give each client a paid-through date and derive active, expiring soon, or expired
from it, then let the client check their own with `/status`.

This is the field features 3 through 6 all read. Payments extend it, channel
access is granted or revoked on it, the daily sweep scans it, and reminders fire
off it. Getting the shape and the day-boundary rule right here is the point.

## In scope

- The `Subscription` model, its migration, and the one-per-client constraint
- Settled parameters as named constants: 30-day period, 3-day expiring window, UTC day boundary
- A repository read for a client's subscription
- `/status`, covering every state a sender can be in, including having no subscription
- Subscription state added to `/clients`, the piece 1c deferred here

## Out of scope

- **Creating or extending a subscription.** Feature 3 records payments and sets `paid_through`. Nothing in this feature writes one, so verification seeds rows directly.
- Channel access. Feature 4 reads the status this feature derives; it does not belong here.
- The daily sweep and reminders. Features 5 and 6.
- Currency and price. Still open, and only feature 3 needs them.
- Changing a client's plan length through a command. The column supports it; no command exposes it yet.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan mode lays out the step before any code.
2. The AI implements just that step.
3. It shows the diff (not full files); you read it and understand it.
4. You approve, then choose whether to commit a checkpoint or roll straight on.
   Checkpoints are optional; `/complete` makes the real feature-level commit at the end.

Never accept a step you haven't read. If a diff is too big to review, the step was too big, so split it.

## Build steps

- [x] **Step 1 - Settled parameters and a UTC today** - put the 30-day period, the 3-day expiring window, and a `utc_today()` helper in `services/subscriptions.py`, and have `SubscriptionWindow` take its lead time from the named constant rather than an inline default. *Done when:* `uv run pytest` covers the boundary days either side of both the expiring and expired transitions, and `utc_today()` is shown to return the UTC date rather than the machine's local date.

- [x] **Step 2 - Subscription model and migration** - add the model with a unique `client_id`, `paid_through`, `plan_length_days` defaulting to 30, and `updated_at`; autogenerate the migration and review the DDL. *Done when:* against a fresh database `alembic upgrade head` applies both revisions in order, the `subscriptions` table shows the expected column types and a unique constraint on `client_id`, `alembic downgrade base` is clean, and the same migration is confirmed against a Postgres container.

- [x] **Step 3 - Read a client's subscription** - add a repository function fetching the subscription for a client, plus a helper turning a `Subscription` into a `SubscriptionWindow`. *Done when:* an async test seeds a subscription, reads it back, and gets the expected status for a date inside the window, a date in the final 3 days, and a date after `paid_through`.

- [x] **Step 4 - The /status command** - a client-facing handler answering for every sender state. *Done when:* driven through the real dispatcher, each of the six cases in the table below produces its own distinct, non-crashing reply, and the active case names the paid-through date in human form.

- [x] **Step 5 - Subscription state in /clients** - extend the admin listing so each approved client shows their status and paid-through date, or that they have none yet. *Done when:* `uv run pytest` covers a listing containing an active, an expiring, an expired, and a no-subscription client, and the offline harness shows the admin the four apart.

## Files / areas

| Path | Why |
|---|---|
| `src/stylebot/services/subscriptions.py` | extend - constants, `utc_today`, window from a model |
| `src/stylebot/db/models.py` | new `Subscription` |
| `alembic/versions/*` | second migration |
| `src/stylebot/db/repository.py` | subscription read, listing joins the subscription |
| `src/stylebot/handlers/status.py` | new - `/status` |
| `src/stylebot/handlers/__init__.py` | register the status router |
| `src/stylebot/services/formatting.py` | status wording, human date for a `date` |
| `tests/` | `test_subscriptions.py`, `test_repository.py`, `test_formatting.py` |

## Data / contracts

**`Subscription` is load-bearing.** Features 3, 4, 5, and 6 all read it, so the
shape is locked here:

| Field | Type | Notes |
|---|---|---|
| `id` | int, PK | |
| `client_id` | int, FK to Client | **unique** - one current subscription per client |
| `paid_through` | date | the authoritative field; every status decision reads it |
| `plan_length_days` | int, default 30 | per-subscription so one client can differ |
| `updated_at` | datetime, UTC | |

Status stays **derived**, never stored. No `status` column, matching the rule
already applied to `Client`.

### The six `/status` cases

| Sender | Reply |
|---|---|
| Never messaged the bot | Ask them to `/start` |
| Pending approval | Waiting for the stylist |
| Removed | Access ended, contact the stylist |
| Approved, no subscription | Approved, nothing paid yet |
| Active | Runs to `<date>` |
| Expiring soon | Runs to `<date>`, renew shortly |
| Expired | Ended on `<date>`, contact the stylist |

That is seven rows for six sender states because active and expiring soon are the
same sender state with different dates. Every row must be reachable.

## Testing

`uv run pytest` is configured, so the test gate is on.

- **Step 1** is pure date logic and the most likely place for an off-by-one. Test the exact boundaries: the day before expiring starts, the first expiring day, `paid_through` itself, and the day after.
- **Step 2** is schema, verified by migration output on SQLite and Postgres rather than a unit test.
- **Steps 3 and 5** ship async tests against in-memory SQLite.
- **Step 4** is dispatcher wiring, verified with the offline harness.

## Notes for the AI

- **`paid_through` is inclusive.** Access runs to the end of that day, so `today == paid_through` is still active, and expiry starts the day after. Feature 4 grants access on exactly this rule, so an off-by-one here silently removes a paying client a day early.

- **Never call `date.today()` inside the logic.** It reads the machine's local date, which on a UTC-configured deployment is right by accident and wrong the moment anyone runs it locally. Use `utc_today()` at the handler edge and pass the date into the logic, the way `status_on(today)` already expects.

- **Do not create `Subscription` rows in this feature.** Feature 3 owns that. Tests and harness runs seed rows directly.

- **The second migration must chain from `ca3a1676edb8`.** Check `down_revision` is set to it rather than `None`; an autogenerated revision with a null parent silently forks the history.

- Keep the derived-status rule intact: no `status` column, and `SubscriptionWindow` stays the single place the transition is computed, since features 4, 5, and 6 will all call it.

- `/status` is a client command, so it carries no admin guard, but it must only ever reveal the sender's own subscription.

## Open questions

1. **Currency and price** remain unresolved. Feature 3 needs them; this feature does not.
2. **Changing a plan length** has no command. The column allows it, so a later admin command or a direct database edit is the only route today.
