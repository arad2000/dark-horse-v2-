"""Dark Horse V2 — PostgreSQL infrastructure for the Hybrid architecture.

Reference/psychometric data remains JSON-backed and versioned in Git.
Operational data is prepared for PostgreSQL via SQLAlchemy.
This module does not alter scoring, ranking, Strategy, Value, or Engine logic.
"""

import os
from typing import Generator

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from models import Base


def _normalize_database_url(url: str) -> str:
    """Map plain postgresql:// to the installed psycopg v3 SQLAlchemy dialect.

    requirements.txt installs psycopg[binary] (v3). SQLAlchemy treats
    postgresql:// as psycopg2, which is not installed and crashes Liara startup.
    """
    u = (url or "").strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    if u.startswith("postgresql://") and not u.startswith("postgresql+"):
        u = "postgresql+psycopg://" + u[len("postgresql://"):]
    return u


DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", ""))
engine = None
SessionLocal = None

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
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
    seed_default_plans()


def seed_default_plans() -> None:
    """Ensure the two canonical credit plans exist (idempotent)."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")

    # Import here so Base.metadata is fully populated by billing_models first.
    from billing_models import PremiumPlan

    defaults = [
        {
            "code": "free_1_test",
            "name_fa": "اعتبار رایگان یک تست",
            "plan_type": "credits",
            "duration_days": None,
            "credits_granted": 1,
            "price_minor": 0,
            "currency": "IRR",
            "is_active": True,
            "features": {"source": "free", "tests": 1},
        },
        {
            "code": "pack_3_tests",
            "name_fa": "بسته ۳ تست",
            "plan_type": "credits",
            "duration_days": None,
            "credits_granted": 3,
            "price_minor": 2_490_000,  # 249,000 تومان
            "currency": "IRR",
            "is_active": True,
            "features": {"source": "payment", "tests": 3},
        },
    ]

    db = SessionLocal()
    try:
        for row in defaults:
            existing = db.scalar(select(PremiumPlan).where(PremiumPlan.code == row["code"]))
            if existing is None:
                db.add(PremiumPlan(**row))
            else:
                existing.name_fa = row["name_fa"]
                existing.plan_type = row["plan_type"]
                existing.duration_days = row["duration_days"]
                existing.credits_granted = row["credits_granted"]
                existing.price_minor = row["price_minor"]
                existing.currency = row["currency"]
                existing.is_active = row["is_active"]
                existing.features = row["features"]
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def healthcheck() -> bool:
    """Return True when a configured PostgreSQL connection can execute SELECT 1."""
    if engine is None:
        return False
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
