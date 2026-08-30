# Build Plan

Features in rough build order, one line each. `/feature` with no number specs the
next unchecked item. Completed items get checked off here, so this doubles as the
progress tracker.

## MVP

- [ ] 1. **Client registry** - prospective clients reach the bot, the admin approves them, and the registry lists everyone
  - [ ] 1a. **Persistence foundation** - database engine, session, Alembic setup, the `Client` model, and the first migration
  - [ ] 1b. **Client intake** - `/start` records a prospective client as pending, and an approved admin approves or declines them
  - [ ] 1c. **Client listing** - `/clients` lists pending and approved clients with their registry details
- [ ] 2. **Subscription periods** - a paid-through date per client, a derived active/expiring/expired status, and `/status` for the client to check their own
- [ ] 3. **Manual payment recording** - admin records a payment that extends the paid-through date and appends to that client's payment history
- [ ] 4. **Channel access control** - grant private-channel access when a subscription becomes active, revoke it when it lapses, and log every change
- [ ] 5. **Daily expiry sweep** - a scheduled job that finds subscriptions that lapsed overnight and revokes their access
- [ ] 6. **Renewal reminders** - a scheduled reminder to each client before their subscription expires, sent once per period

## Post-MVP

- [ ] 7. **Automatic payment collection** - accept payment inside Telegram so subscriptions extend without the admin recording anything by hand
- [ ] 8. **Deployment readiness** - pick the host, add the provider config, verify an always-on single process, and smoke-test against the real channel
