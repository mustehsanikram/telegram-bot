from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stylebot.db.models import Client


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
