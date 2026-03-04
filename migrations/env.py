from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.settings import get_settings

# Alembic Config object provides access to values within alembic.ini
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _get_database_url() -> str:
    """
    Load the database URL from typed settings.

    Expected:
      DATABASE_URL=postgresql://user:pass@host:5432/dbname

    Note: If your password contains special characters (e.g. '@'),
    it must be URL-encoded (e.g. '@' -> '%40').

    Driver note:
    This project uses psycopg v3 in production containers. If the URL starts with
    'postgresql://', we rewrite it to 'postgresql+psycopg://' so SQLAlchemy uses
    the psycopg v3 dialect (instead of trying psycopg2).
    """
    settings = get_settings()
    url = settings.database_url

    # Force SQLAlchemy to use psycopg v3
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() here emit the given string to the script output.
    """
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=None,  # using explicit migrations (no ORM metadata)
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section) or {}

    # Inject DATABASE_URL into sqlalchemy.url (ensure psycopg v3 dialect)
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,  # using explicit migrations (no ORM metadata)
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
