import os

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON as SAJSON

from models import Base
import billing_models  # noqa: F401  # register auth/billing/commercial models
import feedback_models  # noqa: F401  # register public feedback model


pytestmark = pytest.mark.integration


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value.startswith("postgresql"):
        pytest.skip("PostgreSQL DATABASE_URL is not configured")
    return value


def _compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    # Billing payload columns intentionally use PostgreSQL JSONB while the ORM
    # uses SQLAlchemy's portable JSON type for SQLite compatibility. Both are
    # JSON document contracts at the application boundary.
    if isinstance(inspected_type, JSONB) and isinstance(metadata_type, SAJSON):
        return False
    if isinstance(metadata_type, JSONB) and isinstance(inspected_type, SAJSON):
        return False
    return None


def _include_object(obj, name, object_type, reflected, compare_to):
    # Models.py historically used index=True on PK/score fields. Those implicit
    # ix_* metadata indexes are redundant with PostgreSQL PK/explicit indexes
    # created by Alembic and are not part of the migration contract.
    if object_type == "index" and name and name.startswith("ix_") and not reflected:
        return False
    return True


def test_postgresql_orm_schema_matches_migrated_database():
    engine = create_engine(_database_url(), future=True)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(
                connection=conn,
                opts={
                    "compare_type": _compare_type,
                    "compare_server_default": False,
                    "include_object": _include_object,
                },
            )
            differences = compare_metadata(context, Base.metadata)
        assert differences == [], "ORM/Alembic structural schema drift detected:\n" + "\n".join(map(repr, differences))
    finally:
        engine.dispose()
