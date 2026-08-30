from datetime import UTC, datetime

from sqlalchemy import DateTime, Dialect
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator[datetime]):
    """A timestamp that is always timezone-aware UTC in Python.

    SQLite discards tzinfo, so a plain DateTime(timezone=True) reads back naive
    and comparing it against an aware value raises TypeError. This normalises
    both directions so backend choice stops leaking into business logic.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime written to a UTC column")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
