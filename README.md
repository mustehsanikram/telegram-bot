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
