# Coding Standards

Stack: Python 3.12 / aiogram 3 / SQLAlchemy 2 / APScheduler / uv.

## Language and runtime

- Target Python 3.12. Use modern syntax: `X | None` over `Optional[X]`, `list[str]` over `List[str]`, `StrEnum`, `match` where it genuinely reads better.
- Type hints on every function signature, including `-> None`. `mypy` runs in strict mode and must stay green.
- No bare `except:`. Catch the narrowest exception that makes sense, and never swallow one silently.
- Prefer `@dataclass(frozen=True, slots=True)` for value objects, Pydantic models for anything parsed from the outside world (env, webhooks, API payloads).
- Async all the way down. Anything doing I/O is `async def`; never block the event loop with sync network or file calls.

## Package management

- `uv` owns the toolchain, the virtualenv, and the lockfile. Run everything through `uv run`.
- Add dependencies with `uv add <pkg>` (or `uv add --dev <pkg>`), never by hand-editing `pyproject.toml` and hoping. Commit `uv.lock`.
- Runtime deps go in `[project.dependencies]`; test and tooling deps go in the `dev` dependency group.

## Project structure

```
src/stylebot/
  config.py            Settings loaded from .env via pydantic-settings
  bot.py               Bot and dispatcher construction
  __main__.py          Entrypoint, wires logging and runs polling
  handlers/            Telegram command and message handlers, one module per area
  services/            Subscription, channel access, payment, and reminder logic
  db/                  SQLAlchemy models and session management
tests/                 Pytest suite, mirroring the source layout
```

Layering rule: `handlers` may call `services`; `services` may call `db`. Never the
reverse. Keep Telegram types out of `services` and `db` so the logic stays testable
without a bot instance.

## Handlers

- One `Router` per handler module, aggregated in `handlers/__init__.py`.
- Handlers stay thin: parse the update, call a service, format a reply. No business rules, no direct DB queries.
- Guard admin-only commands with an explicit check against `settings.admin_user_ids`. Never infer authority from chat type alone.
- Always answer a callback query, even when the work fails, or the client spins.

## Telegram specifics

- Channel access changes go through `ban_chat_member` / `unban_chat_member` (or a revoked invite link). The bot must be a channel admin with invite and restrict rights.
- Treat Telegram API calls as fallible: rate limits (`TelegramRetryAfter`), users who blocked the bot (`TelegramForbiddenError`), and stale ids are all normal. Handle them, don't crash the poller.
- Never log a bot token, an invite link, or a raw payment payload.

## Data and persistence

- SQLAlchemy 2 declarative models with `Mapped[...]` annotations. No legacy `Column` style.
- Store money as integer minor units, never `float`.
- Store timestamps as timezone-aware UTC. Convert at the presentation edge only.
- Schema changes go through Alembic migrations. Never mutate a live schema by hand.

## Configuration and secrets

- All configuration comes from `Settings` in `config.py`. No `os.environ` reads scattered through the codebase.
- `.env` is gitignored; `.env.example` documents every variable and is committed with empty values.
- Never commit a token, key, or channel id. Never paste a live secret into code, a comment, a test fixture, or a commit message.

## Error handling

- Validate at the service boundary, not in handlers.
- Raise domain-specific exceptions from services; translate them to user-facing messages in handlers.
- User-facing errors say what to do next. They never expose a stack trace, an internal id, or library internals.

## Testing

`uv run pytest` is configured and green, so **tests are a gate**: any step that adds
in-scope logic must ship a passing test in the same reviewable diff, and the suite
must be green before the step is approved, before any checkpoint commit, and before
`/complete` merges.

- **What to test:** pure logic where a wrong answer is possible - subscription status and expiry maths, payment parsing, reminder scheduling windows, validators, formatters. These have assertable inputs and real edge cases (boundary dates, missing data, malformed input).
- **What not to test:** live Telegram API calls and real network integration. Cover those with fakes at the service boundary, plus manual verification against a test bot.
- Use `pytest.mark.parametrize` for table-style cases rather than copy-pasted test bodies.
- Inject the reference date into time-dependent logic (as `SubscriptionWindow.status_on(today)` does) instead of calling `date.today()` inside the logic. It keeps tests deterministic without freezing the clock.
- Test files mirror the source path: `src/stylebot/services/subscriptions.py` maps to `tests/test_subscriptions.py`.
- An empty suite must fail, not pass.

When `AGENTS.md` declares a `Verify` command, treat it as the umbrella automated
gate. `/ci` owns Verify and CI setup.

## Verification

This is a backend, Telegram-only project. There is no browser UI, so do not reach
for Playwright or screenshots of a web page.

Verify behavior with:

- `uv run pytest`, `uv run ruff check .`, and `uv run mypy` output
- a real conversation with a test bot against a throwaway private channel
- log output showing the handler fired and the service decided what you expected

Never claim a Telegram flow works without having actually run it against a bot.

## Code quality

- No commented-out code unless there is an explicit reason in a comment.
- No unused imports or variables. `ruff` catches these; keep it green.
- Keep functions under 50 lines when possible; extract private helpers for clarity.
- `ruff format` is the formatter. Do not hand-align code against it.

## Comments

Write code that explains itself; comment only what the code cannot say.
Over-commenting is a common AI tell, so resist it.

- Comment the **why**, not the **what**. Delete any comment that restates the code.
- No banner or header blocks, section dividers, or step-by-step narration of obvious code.
- A comment earns its place only when it captures something the code can't: a non-obvious decision, a gotcha or workaround, a Telegram API quirk, or a link to a spec or issue.
- Prefer self-documenting names and small functions over explanatory comments.
- Keep docstrings minimal: a one-line purpose on a public function or class is plenty. Don't write a docstring that repeats the signature.
- When in doubt, leave the comment out.

## Writing

- No em dashes (U+2014) in generated content: docs, comments, commit messages, READMEs, specs.
- Use a hyphen for `term - description` separators; rephrase prose with commas, parentheses, or a colon. Avoid en dashes and the ellipsis character too.
