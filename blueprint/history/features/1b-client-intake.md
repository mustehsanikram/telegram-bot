# Feature: Client intake

**From build-plan:** feature 1b (under 1, Client registry)
**Status:** verified

## Goal

Turn the empty `clients` table into a working intake queue. A prospective client
sends `/start`, the bot records them as pending and tells the admin. The admin
approves or declines them, and the client hears back either way.

This is the first sub-feature with behavior a person can see. After it the
registry holds real rows, which is what 1c lists and what feature 2 hangs
subscriptions off.

## In scope

- A repository for `Client` reads and writes, so handlers never touch a session directly
- An aiogram middleware giving each update a database session
- `/start` capturing an unknown sender as a pending client, idempotently
- Notifying the admins when someone new arrives, including the id they need to act on
- An admin guard, with a polite refusal for everyone else
- `/approve <id>` and `/decline <id>`, each telling the client the outcome

## Out of scope

- `/clients` listing. That is 1c. The admin notification carries the id, so 1b is usable without it.
- Anything about subscriptions, dates, payments, or channel access. Approval here means "in the registry", not "has access". Feature 4 connects access.
- Inline keyboard buttons for approve and decline. Commands first; buttons are a later refinement, not a blocker.
- **Readmission of a removed client.** Someone whose `is_active` is false stays removed if they `/start` again. Reversing a removal needs a decision about what happens to their old approval and payment history, and that belongs with the feature that has the history in front of it. See Open questions.
- Any schema change. 1a locked `Client`, and this feature only reads and writes it.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan mode lays out the step before any code.
2. The AI implements just that step.
3. It shows the diff (not full files); you read it and understand it.
4. You approve, then choose whether to commit a checkpoint or roll straight on.
   Checkpoints are optional; `/complete` makes the real feature-level commit at the end.

Never accept a step you haven't read. If a diff is too big to review, the step was too big, so split it.

## Build steps

- [x] **Step 1 - Client repository** - add `db/repository.py` with async functions to fetch a client by Telegram id, create a pending client, mark one approved, and mark one removed. No Telegram types in this module. *Done when:* `uv run pytest` includes a new async test that, against an in-memory SQLite database, creates a client, reads it back, approves it, and sees `client_state` return `APPROVED`.

- [x] **Step 2 - Session middleware** - add `handlers/middleware.py` with an aiogram `BaseMiddleware` that opens one `session_scope` per update and puts the session in the handler data dict. Register it on the root router. *Done when:* a temporary debug handler receives a live `AsyncSession` and executes `select 1` through it, proven by log output, and `uv run mypy` is green.

- [x] **Step 3 - Intake decision and /start capture** - add a pure `intake_outcome` function in `services/clients.py` mapping the sender's existing state (or absence) to one of: registered, already pending, already approved, previously removed. Wire `/start` to call the repository and reply per outcome. *Done when:* `uv run pytest` covers all four outcomes, and a first `/start` and a second `/start` from the same account produce different replies with only one row in `clients`.

- [x] **Step 4 - Admin notification** - on a `registered` outcome only, message every id in `settings.admin_user_ids` with the new client's display name and numeric Telegram id. Swallow and log a per-admin send failure rather than letting it break the client's `/start`. *Done when:* a first `/start` from a non-admin account produces a message to the admin account containing the client's id, and an unreachable admin id logs a warning without raising.

- [x] **Step 5 - Admin guard** - add a pure `is_admin(user_id, admin_ids)` predicate in `services/clients.py` plus an aiogram filter using it. Non-admins attempting an admin command get one polite refusal. *Done when:* `uv run pytest` covers the predicate including the empty-admin-list case, and a non-admin account running an admin command gets the refusal rather than silence.

- [x] **Step 6 - Approve and decline** - add `/approve <id>` and `/decline <id>` behind the guard. Each validates the argument, applies the repository change, confirms to the admin, and notifies the client. *Done when:* approving a pending client sets `approved_at` in the database and the client receives a message; a malformed id, an unknown id, and an already-approved id each produce a distinct, non-crashing reply.

- [x] **Repair A - UTC-aware datetimes** - add a `UtcDateTime` column type that stores aware UTC and re-attaches UTC on read, and use it on `Client`. Removes the naive-datetime hazard before feature 6 depends on comparisons. *Done when:* a round trip through SQLite returns an aware datetime equal to what went in, `alembic check` still reports no schema change, and the workaround in `test_intake.py` is gone.

- [x] **Repair B - Global error handler** - register a dispatcher error handler that logs the exception and tells the user something went wrong. *Done when:* a handler that raises produces a logged error and a user-facing reply rather than silence, proven by a test.

- [x] **Repair C - Bound display name** - cap `display_name_for` at the column's 255 characters. *Done when:* a pathological name is truncated and `uv run pytest` covers it.

## Files / areas

| Path | Why |
|---|---|
| `src/stylebot/db/repository.py` | new - all `Client` persistence |
| `src/stylebot/handlers/middleware.py` | new - per-update session |
| `src/stylebot/services/clients.py` | extend - `intake_outcome`, `is_admin`, display-name formatting |
| `src/stylebot/handlers/start.py` | change - capture the sender |
| `src/stylebot/handlers/admin.py` | new - approve and decline |
| `src/stylebot/handlers/__init__.py` | change - include the admin router, register middleware |
| `tests/test_clients.py` | extend - intake outcomes, admin predicate |
| `tests/test_repository.py` | new - repository against in-memory SQLite |

## Data / contracts

**No schema change.** 1a locked the `Client` shape and this feature only uses it.
No migration should be generated. If autogenerate proposes one, something has
drifted: that is a bug to investigate, not a migration to keep.

State transitions this feature performs:

| From | Action | To |
|---|---|---|
| no row | `/start` | pending (`approved_at` null, `is_active` true) |
| pending | `/approve` | approved (`approved_at` set) |
| pending | `/decline` | removed (`is_active` false) |
| approved | `/decline` | removed (`is_active` false) |
| removed | `/start` | unchanged, stays removed |

`display_name` is captured once at intake from the Telegram sender and is not
refreshed later. A client who renames themselves keeps the name the admin first
saw, which is the more useful behavior for the admin.

## Testing

`uv run pytest` is configured, so the test gate is on.

- **Step 1** ships `tests/test_repository.py`, async against in-memory SQLite (`sqlite+aiosqlite:///:memory:`). This is the project's first database-touching test, so it establishes the fixture pattern later features reuse.
- **Step 3** ships table-driven tests for `intake_outcome`, all four outcomes.
- **Step 5** ships tests for `is_admin`, including an empty admin list, which must deny.
- Steps 2, 4, and 6 are Telegram integration and cannot be unit tested honestly. They need manual verification against a real bot.

**Manual verification requires a real bot.** Steps 3, 4, and 6 have done-whens
observable only by talking to a bot on Telegram. That needs a `BOT_TOKEN` from
@BotFather in `.env`, a second Telegram account to act as the prospective client,
and the admin's own numeric id in `ADMIN_USER_IDS`. Without those, only the pure
logic, the repository tests, and the fact the bot process starts can be proven.
Do not describe a Telegram flow as working on the strength of the code alone.

## Notes for the AI

- **An admin who has never opened the bot cannot be messaged.** Telegram refuses a bot's first message to a user. Step 4's notification will raise `TelegramForbiddenError` for such an admin. Catch it per recipient, log a warning naming the id, and carry on. A failed admin notification must never break the client's `/start`.

- **Keep the session out of the services layer.** `services/clients.py` stays pure: enums and predicates, no SQLAlchemy import. The repository owns persistence, handlers orchestrate. This is the layering that made 1a's rule unit-testable and it is easy to erode here.

- **`/start` must be idempotent.** Tapping start twice must not create a second row, must not re-notify the admins, and must not reset anyone's state. `telegram_user_id` is unique, so a careless insert raises `IntegrityError` rather than failing quietly.

- **`message.from_user` is optional in aiogram's types.** It is `None` for channel posts. Handle that rather than reaching for `!` style suppression; mypy runs strict and will catch it.

- Parse `/approve` and `/decline` arguments defensively. The admin pastes ids by hand, so a non-numeric argument, a missing argument, and extra whitespace all need handling.

- Admin ids come from `settings.admin_user_ids` only. Never infer authority from chat type, from being alone in a chat, or from a username.

- An empty `ADMIN_USER_IDS` means nobody is an admin. `is_admin` must deny, not default open. That also makes step 4's notification a silent no-op, which is correct but worth a startup warning.

- Follow the existing `client_state` pattern: `StrEnum` plus a pure function, no hidden clock or database reads.

## Open questions

1. **Readmission.** A removed client who returns has no path back. Fine now; needs deciding once payment history exists, since re-approving someone should probably not silently resume an old subscription.
2. **Notification volume.** Every new `/start` messages every admin. Correct for one admin; a longer admin list would want a digest.
