"""Quota-health migration contract; never mutates application/user data.

Optional real PostgreSQL case uses a pre-migrated isolated database supplied via
QUOTA_HEALTH_TEST_DATABASE_URL. No implicit production DATABASE_URL fallback.
"""
from pathlib import Path
import os
import unittest
from unittest.mock import MagicMock, patch

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from commercial_api import quota_health

ROOT = Path(__file__).resolve().parent
HEAD = "0011_otp_request_ip"


class QuotaHealthMigrationTests(unittest.TestCase):
    def call_with_revisions(self, revisions):
        db = MagicMock()
        db.execute.return_value.scalars.return_value.all.return_value = revisions
        with patch("commercial_api.inspect") as inspect_db:
            inspect_db.return_value.has_table.return_value = True
            return quota_health(db)

    def test_expected_revision_matches_checked_in_alembic_head(self):
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "alembic"))
        self.assertEqual(ScriptDirectory.from_config(config).get_heads(), [HEAD])
        self.assertEqual(self.call_with_revisions([HEAD])["expected_migration_revision"], HEAD)

    def test_current_head_is_healthy(self):
        result = self.call_with_revisions([HEAD])
        self.assertTrue(result["migration_ok"])
        self.assertTrue(result["ledger_table_exists"])
        self.assertEqual(result["alembic_revisions"], [HEAD])

    def test_previous_revision_is_not_current(self):
        self.assertFalse(self.call_with_revisions(["0010_journey_credit_consumptions"])["migration_ok"])

    def test_unavailable_database_fails_closed(self):
        db = MagicMock()
        db.execute.side_effect = RuntimeError("synthetic database unavailable")
        with patch("commercial_api.inspect", side_effect=RuntimeError("synthetic database unavailable")):
            result = quota_health(db)
        self.assertFalse(result["migration_ok"])
        self.assertFalse(result["ledger_table_exists"])
        self.assertEqual(result["alembic_revisions"], [])

    @unittest.skipUnless(os.getenv("QUOTA_HEALTH_TEST_DATABASE_URL"), "requires explicit isolated PostgreSQL URL")
    def test_real_postgresql_migrated_to_head(self):
        engine = create_engine(os.environ["QUOTA_HEALTH_TEST_DATABASE_URL"])
        try:
            self.assertEqual(engine.dialect.name, "postgresql", "SQLite is not an integration substitute")
            with Session(engine) as db:
                result = quota_health(db)
            self.assertEqual(result["alembic_revisions"], [HEAD])
            self.assertEqual(result["expected_migration_revision"], HEAD)
            self.assertTrue(result["ledger_table_exists"])
            self.assertTrue(result["migration_ok"])

            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            from commercial_api import router
            from database import get_db

            api = FastAPI()
            api.include_router(router)

            def isolated_db():
                with Session(engine) as session:
                    yield session

            api.dependency_overrides[get_db] = isolated_db
            with TestClient(api) as client:
                response = client.get("/api/v1/runtime/quota-health")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["migration_ok"])
            self.assertEqual(response.json()["expected_migration_revision"], HEAD)
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
