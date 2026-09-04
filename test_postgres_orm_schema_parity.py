import os

import pytest
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from sqlalchemy import create_engine

from models import Base
import billing_models  # noqa: F401  # register all operational models


pytestmark = pytest.mark.integration


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value.startswith("postgresql"):
        pytest.skip("PostgreSQL DATABASE_URL is not configured")
    return value


def test_postgresql_orm_schema_matches_migrated_database():
    engine = create_engine(_database_url(), future=True)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(
                connection=conn,
                opts={
                    "compare_type": True,
                    "compare_server_default": True,
                },
            )
            differences = compare_metadata(context, Base.metadata)
        assert differences == [], "ORM/Alembic schema drift detected:\n" + "\n".join(map(repr, differences))
    finally:
        engine.dispose()
