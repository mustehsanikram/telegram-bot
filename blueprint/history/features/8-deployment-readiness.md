# Feature: Deployment readiness

**From build-plan:** feature 8
**Status:** verified

## Goal

Make the bot deployable to Railway as an always-on worker backed by Postgres,
with migrations applied on every deploy and every required setting documented.

Railpack currently fails with "No start command detected", but that error is the
smallest of four problems. Fixing only it produces a container that starts,
crashes on missing config, and if it survived would write to a database erased on
the next redeploy.

## In scope

- Postgres support: the `asyncpg` driver, and proof the existing migration applies to a real Postgres
- `railpack.json` declaring a start command that migrates before it starts the bot
- Deployment documentation: every Railway variable, the Postgres step, and the single-replica requirement
- A smoke-test checklist the user runs against the deployed bot

## Out of scope

- **Running the deploy.** Creating the Railway service, adding Postgres, setting variables, and clicking deploy are the user's actions. This feature makes the repo deployable; it cannot deploy it.
- **Pushing to GitHub.** Railway builds from `origin/main`, which is still one commit behind. Pushing needs a credential this project does not yet have working.
- **A Postgres test in the permanent suite.** The verification uses a throwaway Docker container. Requiring Docker for `uv run pytest` would break the test gate for anyone without it. See Follow-ups.
- **Channel access smoke-testing.** The build-plan line says "smoke-test against the real channel", but channel grant and revoke are feature 4 and do not exist. The smoke test covers the intake flow that does. See Scope note.
- Webhooks, autoscaling, health check endpoints, staging environments, log drains.

## Scope note

The build-plan line for item 8 anticipated a channel to test against. Features 2
through 6 are unbuilt, so nothing touches the private channel yet. This feature
proves the deployed bot can be reached, register a client, notify the admin, and
survive a redeploy with its data intact. Channel verification joins the smoke
test when feature 4 lands.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan mode lays out the step before any code.
2. The AI implements just that step.
3. It shows the diff (not full files); you read it and understand it.
4. You approve, then choose whether to commit a checkpoint or roll straight on.
   Checkpoints are optional; `/complete` makes the real feature-level commit at the end.

Never accept a step you haven't read. If a diff is too big to review, the step was too big, so split it.

## Build steps

- [x] **Step 1 - Postgres support, proven against a real Postgres** - add `asyncpg` as a runtime dependency, then verify the existing migration and repository work against a Postgres container. *Done when:* against a throwaway Docker Postgres, `alembic upgrade head` succeeds, `clients` shows `BIGINT` for `telegram_user_id` and `TIMESTAMP WITH TIME ZONE` for both datetime columns, a client round-trips with an aware datetime, `alembic downgrade base` drops cleanly, and the SQLite suite still passes.

- [x] **Step 2 - Railpack start command** - add `railpack.json` declaring `uv run alembic upgrade head && uv run stylebot`. *Done when:* the file is valid JSON with the documented `deploy.startCommand` shape, and running that exact command locally against a temp database applies the migration and then reaches Telegram authentication, failing only on the placeholder token.

- [x] **Step 3 - Deployment documentation** - add a Deployment section to `README.md` covering the four Railway variables, adding Railway Postgres and wiring `DATABASE_URL`, and why the service must stay at one replica. *Done when:* every field on `Settings` appears in both `.env.example` and the README table, verified by a check that reads the model rather than by eye.

- [x] **Step 4 - Smoke-test checklist** - document the ordered checks to run against the deployed bot, including a redeploy to prove data survives. *Done when:* the checklist is in the README, each item states what to do and what counts as wrong, and the persistence check explicitly involves a redeploy.

## Files / areas

| Path | Why |
|---|---|
| `pyproject.toml`, `uv.lock` | new `asyncpg` runtime dependency |
| `railpack.json` | new - the start command Railpack is asking for |
| `README.md` | new Deployment and Smoke test sections |
| `.env.example` | confirm it covers every `Settings` field |

## Data / contracts

**No schema change and no new migration.** This feature proves the *existing*
migration applies to a second backend. If `alembic check` reports pending
operations against Postgres, that is a real portability defect to investigate,
not a migration to generate.

Backend mapping to confirm in step 1:

| Model | SQLite (today) | Postgres (expected) |
|---|---|---|
| `BigInteger` | `BIGINT` | `BIGINT` |
| `UtcDateTime` | `DATETIME` | `TIMESTAMP WITH TIME ZONE` |
| `String(255)` | `VARCHAR(255)` | `VARCHAR(255)` |

## Testing

`uv run pytest` stays SQLite-only and must stay green throughout.

- **Step 1** is verified by a throwaway Docker container, not by a new permanent test. The evidence is command output, not a test file.
- **Steps 2, 3, 4** are configuration and documentation. Step 3's done-when is machine-checked against `Settings.model_fields` so the docs cannot silently drift from the code.
- No step here adds application logic, so no step adds a unit test. If one does, it ships a test with it.

**What cannot be verified from here:** the actual Railway deployment. No step
claims the bot runs on Railway. Step 4 produces the checklist; running it is the
user's job, and its results are not evidence this feature can cite.

## Notes for the AI

- **The existing migration has never touched Postgres.** It was autogenerated under SQLite with `render_as_batch`, so it contains a `batch_alter_table` block for the unique index. Batch mode passes through to ordinary DDL on Postgres, but that is the assumption step 1 exists to test. Do not assume it applies cleanly; run it.

- **`asyncpg` builds native extensions.** If no Windows wheel is available for Python 3.12 it will try to compile and may fail. If that happens, stop and report it rather than switching drivers quietly: `psycopg` v3 is the fallback, but it changes the URL scheme and belongs in a reviewed decision.

- **Migrations run in the start command, not a release phase.** Railway has no separate release step, and the service is single-replica, so `alembic upgrade head &&` in the start command is safe. It would not be safe with multiple replicas starting at once.

- **Never put a real token, database URL, or channel id in `railpack.json`, the README, or `.env.example`.** Those files are committed. Placeholders only.

- Keep `.env.example` and the README table generated from what `Settings` actually declares, so a new setting cannot be added without appearing in the docs.

## Follow-ups

1. **No automated Postgres coverage.** The suite runs on SQLite, so a future Postgres-only regression would not be caught locally. A CI job with a Postgres service container is the fix; that belongs with `/ci`.
2. **Channel smoke-testing** joins step 4's checklist when feature 4 lands.
3. **Token rejection was not observable locally.** Step 2 proved the start command migrates then starts the bot, and the bot reaches the Telegram authentication call, but aiohttp could not complete a TLS connection from the build environment. Whether a bad token produces a clean failure is therefore unproven and belongs in step 4's smoke test.
