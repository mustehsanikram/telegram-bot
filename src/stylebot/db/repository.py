from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stylebot.db.models import Client, Subscription


async def get_by_telegram_id(session: AsyncSession, telegram_user_id: int) -> Client | None:
    result = await session.execute(
        select(Client).where(Client.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


async def create_pending(
    session: AsyncSession,
    telegram_user_id: int,
    display_name: str,
    first_seen_at: datetime,
) -> Client:
    client = Client(
        telegram_user_id=telegram_user_id,
        display_name=display_name,
        first_seen_at=first_seen_at,
    )
    session.add(client)
    # Flush, never commit: session_scope owns the transaction boundary.
    await session.flush()
    return client


async def mark_approved(session: AsyncSession, client: Client, approved_at: datetime) -> None:
    client.approved_at = approved_at
    await session.flush()


async def mark_removed(session: AsyncSession, client: Client) -> None:
    client.is_active = False
    await session.flush()


async def list_clients(session: AsyncSession) -> Sequence[tuple[Client, Subscription | None]]:
    """Registry rows for display, each with its subscription if it has one.

    Pending first, then oldest arrival first; removed clients are excluded.
    Ordering on `approved_at IS NOT NULL` puts pending (false) ahead of approved
    (true) on both SQLite and Postgres. The outer join keeps this one query
    rather than a lookup per client.
    """
    result = await session.execute(
        select(Client, Subscription)
        .outerjoin(Subscription, Subscription.client_id == Client.id)
        .where(Client.is_active.is_(True))
        .order_by(Client.approved_at.is_not(None), Client.first_seen_at)
    )
    return [(client, subscription) for client, subscription in result.all()]


async def get_subscription_for_client(
    session: AsyncSession, client_id: int
) -> Subscription | None:
    result = await session.execute(
        select(Subscription).where(Subscription.client_id == client_id)
    )
    return result.scalar_one_or_none()
