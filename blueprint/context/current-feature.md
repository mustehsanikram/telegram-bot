# Feature: Persistence foundation

**From build-plan:** feature 1a (under 1, Client registry)
**Status:** not started

## Goal

Stand up the database layer the whole project sits on: an async SQLAlchemy engine
and session, the `Client` model, Alembic wired up with the first migration, and
the derived registry-state rule that 1b and 1c will both read.

Nothing user-facing ships here. This exists so 1b (intake) and 1c (listing) are
small, and so every later feature has a real migration path instead of a schema
someone created by hand.

## In scope

- Declarative `Base` and an async engine plus session factory
- The `Client` model exactly as locked in `project-overview.md`
- Alembic initialised for async SQLAlchemy, with `env.py` pointed at `Base.metadata`
- The first migration, creating the `clients` table
- `ClientState` and the pure function deriving it from `approved_at` and `is_active`

## Out of scope

- Any handler, command, or bot-visible behavior. No `/start` change, no `/clients`. Those are 1b and 1c.
- `Subscription`, `Payment`, `AccessEvent`, `ReminderLog` models. Each lands with the feature that uses it, so migrations stay reviewable.
- Postgres. SQLite only for now; the engine URL stays configurable so the move is a config change.
- Seed data and fixtures.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan mode lays out the step before any code.
2. The AI implements just that step.
3. It shows the diff (not full files); you read it and understand it.
4. You approve, then choose whether to commit a checkpoint or roll straight on.
   Checkpoints are optional; `/complete` makes the real feature-level commit at the end.

Never accept a step you haven't read. If a diff is too big to review, the step was too big, so split it.

## Build steps

- [ ] **Step 1 - Base and session** - add `db/base.py` with the declarative `Base`, and `db/session.py` with the async engine, `async_sessionmaker`, and a session dependency. Engine URL comes from `Settings.database_url`. *Done when:* a throwaway script opens a session against a temp SQLite file and closes it cleanly, and `uv run mypy` is green.

- [ ] **Step 2 - Client model** - add `db/models.py` with `Client`, using SQLAlchemy 2 `Mapped[...]` annotations and the exact fields locked in the overview. `telegram_user_id` unique and indexed; `first_seen_at` and `approved_at` as `DateTime(timezone=True)`. *Done when:* `Client.__table__.columns` shows the six expected columns with the right nullability, and mypy is green.

- [ ] **Step 3 - Registry state rule** - add `services/clients.py` with a `ClientState` StrEnum (`PENDING`, `APPROVED`, `REMOVED`) and a pure function deriving it from `approved_at` and `is_active`. No DB access in this function. *Done when:* `uv run pytest` covers all three states plus the declined case (`approved_at` set and `is_active` false), and passes.

- [ ] **Step 4 - Alembic and first migration** - initialise Alembic with the async template, point `env.py` at `Base.metadata`, autogenerate the initial migration, and review the generated DDL by hand before keeping it. *Done when:* against a fresh temp database, `uv run alembic upgrade head` creates the `clients` table, `uv run alembic current` reports the revision, and `uv run alembic downgrade base` drops it cleanly.

## Files / areas

| Path | Why |
|---|---|
| `src/stylebot/db/base.py` | new - declarative `Base` |
| `src/stylebot/db/session.py` | new - async engine, session factory |
| `src/stylebot/db/models.py` | new - `Client` |
| `src/stylebot/services/clients.py` | new - `ClientState` and the derivation rule |
| `alembic.ini`, `alembic/env.py`, `alembic/versions/*` | new - migration tooling and first revision |
| `tests/test_clients.py` | new - covers the derivation rule |
| `.gitignore` | check `*.db` already covers the temp databases used in verification |

## Data / contracts

`Client` is load-bearing. Features 2 through 6 all hang off it, so this shape is
locked here:

| Field | Type | Notes |
|---|---|---|
| `id` | int, PK | |
| `telegram_user_id` | int | unique, indexed |
| `display_name` | str | |
| `first_seen_at` | datetime, UTC | when they first messaged the bot |
| `approved_at` | datetime, UTC, nullable | null means pending |
| `is_active` | bool | false means declined or former client |

Derived, never stored:

- `approved_at is None` and `is_active` -> `PENDING`
- `approved_at` set and `is_active` -> `APPROVED`
- `is_active` false -> `REMOVED`

No `state` column. Same rule the subscription status already follows.

## Testing

`uv run pytest` is configured, so the test gate is on.

- **Step 3 is the logic-bearing step** and must ship `tests/test_clients.py` in the same diff. Table-driven with `parametrize`, covering pending, approved, removed, and the declined edge case.
- Steps 1, 2, and 4 are infrastructure. They ride on observable command evidence: a session that opens, a table whose columns match, and a migration that applies and rolls back against a temp database.
- Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy` before any step is approved.

## Notes for the AI

- **Alembic must use the async template** (`alembic init -t async`). The default sync template will not work against `sqlite+aiosqlite`.

- **Do not import `Settings` in `alembic/env.py`.** `Settings` requires `bot_token` and `private_channel_id`, which have no defaults, so a migration run without a populated `.env` would crash on config validation rather than anything database-related. Read `DATABASE_URL` from the environment in `env.py`, falling back to the same default string as `Settings.database_url`.

- **SQLite does not store timezones.** `DateTime(timezone=True)` is still correct for the eventual Postgres move, but SQLite will hand back naive datetimes. Always write timezone-aware UTC, and do not assume what comes back is aware. This will matter for real when feature 6 compares reminder timestamps.

- Review the autogenerated migration before keeping it. Autogenerate is a starting point, not an authority, and this is the one migration every later migration builds on.

- Layering: `services/clients.py` holds the derivation rule and must not import SQLAlchemy or any Telegram type. That is what keeps it unit-testable and is why the rule lives in `services`, not on the model.

- Follow the existing `SubscriptionWindow` pattern in `services/subscriptions.py`: a `StrEnum` plus a pure function, no hidden clock reads.
