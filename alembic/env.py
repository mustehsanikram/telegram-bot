import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from stylebot.db import models  # noqa: F401  registers Client on Base.metadata
from stylebot.db.base import Base
from stylebot.db.types import UtcDateTime

# Settings is deliberately not imported here: it requires BOT_TOKEN and
# PRIVATE_CHANNEL_ID, so a migration run without a populated .env would fail
# config validation instead of doing anything database-related.
DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./stylebot.db"

config = context.config
config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_: str, obj: object, autogen_context: object) -> str | bool:
    """Keep migrations dependent on SQLAlchemy alone.

    Autogenerate would otherwise emit stylebot.db.types.UtcDateTime into the
    revision, which does not import it and would break anyway if the class were
    ever renamed. The stored SQL type is what matters, so render that.
    """
    if type_ == "type" and isinstance(obj, UtcDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        render_item=render_item,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # SQLite cannot ALTER most columns in place; batch mode rebuilds the table
    # instead. Harmless on Postgres, which never needs the rewrite.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_item=render_item,
        render_as_batch=connection.dialect.name == "sqlite",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
