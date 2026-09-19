"""Dark Horse V2 — PostgreSQL infrastructure for the Hybrid architecture.

Reference/psychometric data remains JSON-backed and versioned in Git.
Operational data is prepared for PostgreSQL via SQLAlchemy.
This module does not alter scoring, ranking, Strategy, Value, or Engine logic.
"""

import os
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import BigInteger
from sqlalchemy.orm import Session, sessionmaker

from models import Base


# SQLite does not autoincrement a BIGINT primary key unless the declared type is
# exactly INTEGER. Keep PostgreSQL BIGINT semantics in production, while making
# the CI/dev SQLite compatibility path behave like the production identity
# columns. This is a DDL compilation detail only; it does not change the ORM
# model or PostgreSQL schema.
@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(type_, compiler, **kw):
    return "INTEGER"


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}")
    return value


DATABASE_URL = os.getenv("DATABASE_URL", "")
engine = None
SessionLocal = None

if DATABASE_URL:
    engine_kwargs = {
        "pool_pre_ping": True,
        "future": True,
    }
    # Preserve the existing SQLite compatibility path. PostgreSQL and other
    # server databases can tune pool capacity through deployment environment
    # variables without changing application code.
    if not DATABASE_URL.lower().startswith("sqlite"):
        engine_kwargs.update(
            pool_size=_env_int("DB_POOL_SIZE", 5, minimum=1),
            max_overflow=_env_int("DB_MAX_OVERFLOW", 10, minimum=0),
            pool_timeout=_env_int("DB_POOL_TIMEOUT", 30, minimum=1),
            pool_recycle=_env_int("DB_POOL_RECYCLE", -1, minimum=-1),
        )
    engine = create_engine(DATABASE_URL, **engine_kwargs)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


def is_configured() -> bool:
    return engine is not None and SessionLocal is not None


def get_db() -> Generator[Session, None, None]:
    """Yield a PostgreSQL session when DATABASE_URL is configured."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create ORM tables for local/dev bootstrap only.

    Production schema evolution should use Alembic in the next phase.
    """
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    Base.metadata.create_all(bind=engine)


def healthcheck() -> bool:
    """Return True when a configured PostgreSQL connection can execute SELECT 1."""
    if engine is None:
        return False
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
