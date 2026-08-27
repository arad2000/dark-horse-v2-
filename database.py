"""Dark Horse V2 — database infrastructure (Hybrid migration phase 1).

Reference/psychometric data remains JSON-backed and versioned in Git.
Operational data is prepared for PostgreSQL via SQLAlchemy.
No application scoring or recommendation logic is changed here.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = None
SessionLocal = None

if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        future=True,
    )
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


def get_db() -> Generator[Session, None, None]:
    """Yield a DB session when DATABASE_URL is configured."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create ORM tables for local/dev bootstrapping.

    Production schema changes must be managed through migrations once
    Alembic is introduced. This helper does not alter application logic.
    """
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    Base.metadata.create_all(bind=engine)
