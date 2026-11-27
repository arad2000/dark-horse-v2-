"""Alembic environment for the Dark Horse Hybrid database layer.

Reference/psychometric data stays in versioned JSON files. Alembic is only
for PostgreSQL schema evolution. It is never invoked by the application at
startup, so creating this file cannot switch production traffic to PostgreSQL.
"""
from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool
from alembic import context

from models import Base
import billing_models  # noqa: F401  # register billing/auth tables in metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _normalize_database_url(url: str) -> str:
    """Apply the same URL normalization as database.py before any connection.

    requirements.txt installs psycopg v3 (psycopg[binary]) only, so SQLAlchemy
    must see an explicit ``+psycopg`` driver. Left unnormalized, a plain
    ``postgresql://`` URL resolves to psycopg2, which is not installed, and the
    migration fails on a host where the application itself would have started.

    Kept behaviorally identical to database.py::_normalize_database_url. It is
    duplicated rather than imported because importing database.py creates the
    application engine and pool as a side effect inside the migration process.

    This function never logs its input or output: the URL carries credentials.
    """
    u = (url or "").strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    if u.startswith("postgresql://") and not u.startswith("postgresql+"):
        u = "postgresql+psycopg://" + u[len("postgresql://"):]
    return u


def get_url() -> str:
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("DATABASE_URL must be set to run Alembic")
    return _normalize_database_url(url)


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
