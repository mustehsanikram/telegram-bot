# Feature: Client listing

**From build-plan:** feature 1c (under 1, Client registry)
**Status:** verified

## Goal

Give the admin `/clients`: one message showing everyone in the registry, pending
first, each with the name, the numeric id, and when they arrived.

Today the only route to a client's id is the notification sent when they first
messaged the bot. Lose that message and the client is unreachable through the
admin commands. This closes feature 1.

## In scope

- A repository query listing clients for display
- A pure formatter turning that list into one Telegram message
- HTML escaping of every client-supplied value, and the same fix applied to the existing admin notification
- `/clients` behind the admin guard, refused politely for everyone else
- The empty registry and the too-many-clients cases

## Out of scope

- Removed clients. The build-plan line says pending and approved; someone declined stays out of the list. See Open questions.
- Filtering, searching, sorting options, or pagination controls. One message, a fixed order.
- Subscription state in the listing. Feature 2 owns `paid_through`, and there is nothing to show yet.
- Any schema change. `Client` is unchanged.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan mode lays out the step before any code.
2. The AI implements just that step.
3. It shows the diff (not full files); you read it and understand it.
4. You approve, then choose whether to commit a checkpoint or roll straight on.
   Checkpoints are optional; `/complete` makes the real feature-level commit at the end.

Never accept a step you haven't read. If a diff is too big to review, the step was too big, so split it.

## Build steps

- [x] **Step 1 - Escape client-supplied text** - add an escaping helper and use it wherever a display name reaches a message, including the existing `new_client_message`. *Done when:* `uv run pytest` shows a name containing `<b>`, `</code>` and `&` is rendered with entities escaped, and the admin notification no longer emits raw angle brackets from a client's name.

- [x] **Step 2 - Repository listing** - add `list_clients` returning clients ordered pending-first, then by `first_seen_at` within each group, excluding removed clients. *Done when:* an async test against in-memory SQLite seeds pending, approved, and removed clients and asserts the exact returned order with the removed one absent.

- [x] **Step 3 - Format the listing** - add a pure formatter producing the message text: a pending section, an approved section, counts, and a cap so the message cannot exceed Telegram's limit. *Done when:* `uv run pytest` covers the empty registry, a mixed list, a name needing escaping, and a list long enough to truncate, and asserts the produced text never exceeds the cap and says how many were omitted.

- [x] **Step 4 - The /clients command** - register `/clients` behind `IsAdmin`, and add it to the commands a non-admin is refused for. *Done when:* driven through the real dispatcher, an admin gets the listing, a non-admin gets the refusal rather than silence, and an admin with an empty registry gets the empty-state message.

## Files / areas

| Path | Why |
|---|---|
| `src/stylebot/services/formatting.py` | new - escaping helper and the listing formatter |
| `src/stylebot/db/repository.py` | extend - `list_clients` |
| `src/stylebot/handlers/notifications.py` | change - escape the name in the admin notification |
| `src/stylebot/handlers/admin.py` | change - `/clients` handler, added to the refused command list |
| `tests/test_formatting.py` | new |
| `tests/test_repository.py` | extend |

## Data / contracts

**No schema change.** `Client` is unchanged and no migration should be generated.

The formatter takes plain values, not ORM objects, so it stays pure and testable:

| Field | Source |
|---|---|
| `display_name` | `Client.display_name`, escaped before it reaches the message |
| `telegram_user_id` | `Client.telegram_user_id` |
| `state` | derived by `client_state`, never stored |
| `first_seen_at` | `Client.first_seen_at` |

**Telegram's message limit is 4096 characters.** Exceed it and the send fails
outright, so the admin gets nothing rather than a long list. The formatter caps
its output and reports the number omitted; the cap is a constant in
`formatting.py` so a later paging feature has one place to change.

## Testing

`uv run pytest` is configured, so the test gate is on.

- **Step 1** ships escaping tests, including the `</code>` case that would break the existing notification.
- **Step 2** extends `tests/test_repository.py` with an ordering test that includes a removed client.
- **Step 3** ships `tests/test_formatting.py`: empty, mixed, escaped, truncated.
- **Step 4** is dispatcher wiring, verified with the offline harness used for 1b rather than a unit test.

## Notes for the AI

- **The escaping fix is a defect repair, not new scope.** `new_client_message` already interpolates a client-controlled display name into an HTML message. A name containing `</code>` produces unparseable entities, Telegram rejects the send with a 400, and the admin is never told about that client. 1c would repeat this for every row, so it is fixed here rather than logged. Use `aiogram.utils.text_decorations.html_decoration.quote`.

- **Escape at the formatting boundary, never in the database.** Store what Telegram gave us; escape when rendering. Escaping on write would corrupt the stored name and double-escape on any second render.

- **`/clients` must be added to `ADMIN_COMMANDS` in `admin.py`.** That tuple drives the inverted-guard refusal handler. Registering the new command without adding it there leaves non-admins with silence, which is the behaviour step 5 of 1b existed to remove.

- Order pending before approved. The pending ones are the list the admin has to act on; approved ones are reference.

- Show dates the way the project's UI/UX section asks: human dates, not timestamps.

- The formatter takes values and returns a string. No session, no bot, no Telegram types, so it stays unit-testable.

## Open questions

1. **Removed clients are invisible.** Nothing lists someone who was declined or removed, so the admin cannot review or reconsider them. Consistent with the build-plan line and with readmission being deferred, but worth revisiting when readmission is decided.
2. **The cap is a stopgap.** Once the registry outgrows one message the honest answer is paging, which is a feature rather than a constant.
