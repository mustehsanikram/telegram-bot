# StyleBot

A Telegram bot that manages private-channel subscriptions for a personal styling
business. It tracks client payments, grants and revokes channel access based on
subscription status, and sends renewal reminders before a subscription lapses.

## Requirements

- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 and the virtualenv)

## Setup

```bash
uv sync
cp .env.example .env
```

Fill in `.env`:

| Variable | What it is |
|---|---|
| `BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather) |
| `PRIVATE_CHANNEL_ID` | Numeric id of the private channel, usually negative |
| `ADMIN_USER_IDS` | JSON list of Telegram user ids allowed to run admin commands |
| `DATABASE_URL` | Defaults to a local SQLite file |

The bot must be an administrator of the private channel with the permission to
invite and remove users, otherwise access changes will fail.

## Commands

| Task | Command |
|---|---|
| Run the bot | `uv run stylebot` |
| Test | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Typecheck | `uv run mypy` |

## Layout

```
src/stylebot/
  config.py            Settings loaded from .env
  bot.py               Bot and dispatcher wiring
  handlers/            Telegram command and message handlers
  services/            Subscription, access, and reminder logic
  db/                  Persistence
tests/                 Pytest suite
```

## Deployment

Hosted on [Railway](https://railway.com) as a **worker** service. The bot uses
long polling, so there is no HTTP server, no port to bind, and no health check
path.

### 1. Add Postgres

Railway's container filesystem is ephemeral: it is wiped on every redeploy. A
SQLite file would take the whole client registry with it, so add a **Railway
Postgres** database to the project and point the bot at it.

### 2. Set the service variables

| Variable | Required | What it is |
|---|---|---|
| `BOT_TOKEN` | yes | Token from [@BotFather](https://t.me/BotFather) |
| `PRIVATE_CHANNEL_ID` | yes | Numeric id of the private channel, usually negative |
| `ADMIN_USER_IDS` | yes | JSON list of Telegram user ids allowed to run admin commands, e.g. `[123456789]`. An empty list locks everyone out. |
| `DATABASE_URL` | yes | `postgresql+asyncpg://...`. Take Railway's Postgres connection string and change the scheme to `postgresql+asyncpg`. |

Railway's own `DATABASE_URL` uses the `postgresql://` scheme, which SQLAlchemy
reads as the sync driver. It must be `postgresql+asyncpg://` or the bot fails to
start.

### 3. Keep it at one replica

Telegram allows a single `getUpdates` poller per bot. A second replica causes
409 conflicts and, once reminders exist, double-sends them. Leave the service at
one instance and do not enable autoscaling.

### 4. Deploy

`railpack.json` declares the start command:

```
uv run alembic upgrade head && uv run stylebot
```

Migrations run on every deploy, before the bot starts. A failed migration aborts
the start rather than running the bot against a schema that is not there. This is
safe because the service is single-replica.

## Smoke test

Run these in order against the deployed bot, after the first successful deploy.
You need a second Telegram account to act as the client; your own account must be
in `ADMIN_USER_IDS`.

**1. The deploy starts cleanly**

Watch the Railway deploy logs.
*Expect:* an Alembic line running the migration, then `starting polling`.
*Wrong if:* the log stops at the migration, or repeats `starting polling` in a
crash loop. A loop usually means `BOT_TOKEN` is wrong or `DATABASE_URL` still has
the `postgresql://` scheme instead of `postgresql+asyncpg://`.

**2. A bad token fails loudly, not silently**

Temporarily set `BOT_TOKEN` to `123456:invalid` and redeploy.
*Expect:* the service crashes with a Telegram unauthorized error naming the token.
*Wrong if:* it sits there looking healthy while doing nothing. Restore the real
token afterwards. This check exists because it could not be verified locally.

**3. A new client can reach the bot**

From the second account, send `/start`.
*Expect:* a welcome reply saying they have been added and their stylist will review it.
*Wrong if:* silence, or an error message. Silence means the update never arrived;
check the bot is running and not blocked by another poller.

**4. You are notified with a usable id**

Check your own Telegram.
*Expect:* a message naming the new client and showing their numeric id, with
`/approve <id>` and `/decline <id>` spelled out.
*Wrong if:* nothing arrives. Either your id is not in `ADMIN_USER_IDS`, or you have
never opened a chat with the bot, which stops it messaging you first.

**5. Repeat `/start` does not duplicate anything**

Send `/start` again from the second account.
*Expect:* a different reply saying they are already on the list, and no second
notification to you.
*Wrong if:* you get a second notification, or the reply is identical to the first.

**6. Approval works end to end**

Send `/approve <id>` from your account.
*Expect:* a confirmation naming the client, and the client receives an approval
message on the second account.
*Wrong if:* either side is missing.

**7. A stranger cannot use admin commands**

From the second account, send `/approve 123`.
*Expect:* "That command is for your stylist only."
*Wrong if:* silence, or anything that looks like it worked.

**8. Data survives a redeploy**

Trigger a redeploy in Railway, wait for it to finish, then send `/start` from the
second account again.
*Expect:* the "already approved" reply, proving the client row outlived the
container.
*Wrong if:* you get the first-time welcome again. That means the database is
ephemeral, so `DATABASE_URL` is not pointing at Railway Postgres, and every deploy
is wiping your client registry.
