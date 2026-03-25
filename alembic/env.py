"""Alembic environment configuration for Lazy-Bird v2.0

This module configures Alembic for database migrations.
It loads the database URL from environment variables and
imports all SQLAlchemy models for autogenerate support.

Supports both sync and async engines. For local development,
set DATABASE_URL env var (e.g., sqlite:///./test.db for quick testing).
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add project root to path so lazy_bird package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# Import Base and all models
# ---------------------------------------------------------------------------
# We import Base directly from the declarative_base definition.
# We must also import all models so they register with Base.metadata,
# which is required for autogenerate to detect schema changes.
#
# NOTE: lazy_bird.core.database creates engine objects at import time
# using settings.DATABASE_URL.  When running Alembic we override the URL
# below via the environment variable DATABASE_URL (or fall back to the
# settings value).  The engines created at import time are NOT used by
# Alembic -- Alembic creates its own engine from the [alembic] config.
# ---------------------------------------------------------------------------

# Determine the database URL *before* importing heavy modules so we can
# set it in the environment for Settings to pick up.
_db_url = os.environ.get("DATABASE_URL")

if _db_url:
    # Ensure pydantic-settings sees this when it loads
    os.environ["DATABASE_URL"] = _db_url

# Now import -- this may trigger Settings() and engine creation, but
# those side-effects won't affect Alembic's own engine.
from lazy_bird.core.database import Base  # noqa: E402
from lazy_bird.models import *  # noqa: F401, F403, E402

# Also grab settings so we can read DATABASE_URL if env var wasn't set
from lazy_bird.core.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with the resolved database URL.
# Priority: DATABASE_URL env var > settings.DATABASE_URL > alembic.ini value
database_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
config.set_main_option("sqlalchemy.url", database_url)

# Model MetaData for autogenerate support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    so we don't need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we create an Engine and associate a connection
    with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
