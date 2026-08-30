from datetime import datetime

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from stylebot.db.base import Base
from stylebot.db.types import UtcDateTime


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Live Telegram account ids already exceed 32 bits, so Integer overflows on Postgres.
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    first_seen_at: Mapped[datetime] = mapped_column(UtcDateTime)
    approved_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
