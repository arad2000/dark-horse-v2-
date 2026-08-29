from __future__ import annotations

import os
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api_persistence_adapter import OperationalPersistenceAdapter
from models import Base, Major, SchoolBranch
from operational_store import OperationalStore
from shadow_persistence import ShadowPersistenceReport, persist_shadow, shadow_enabled


class ShadowPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        os.environ.pop("DARK_HORSE_SHADOW_PERSISTENCE", None)
        with self.SessionLocal() as db:
            db.add(Major(id=1, name="Test Major", group="Test", strategy_weights=[[0.0] * 5 for _ in range(25)], value_weights={}))
            db.add(SchoolBranch(id=1, name="Test Branch", group="Test", strategy_weights=[[0.0] * 5 for _ in range(25)], value_weights={}))
            db.commit()
        self.adapter = OperationalPersistenceAdapter(OperationalStore(self.SessionLocal))

    def tearDown(self):
        os.environ.pop("DARK_HORSE_SHADOW_PERSISTENCE", None)

    def test_disabled_by_default_is_noop(self):
        self.assertFalse(shadow_enabled())
        report = persist_shadow(
            self.adapter,
            {"micro_motives": [], "sjt_answers": {}, "conjoint_choices": {}},
            {"recommendations": []},
        )
        self.assertEqual(report, ShadowPersistenceReport(attempted=False, persisted=False))

    def test_enabled_persists_without_changing_response(self):
        os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = "true"
        request = {"micro_motives": [], "sjt_answers": {}, "conjoint_choices": {}}
        response = {"recommendations": [{"major_id": 1, "fit_score": 82.0}]}
        before = dict(response)
        report = persist_shadow(self.adapter, request, response)
        self.assertTrue(report.attempted)
        self.assertTrue(report.persisted)
        self.assertIsNotNone(report.session_id)
        self.assertEqual(response, before)

    def test_non_strict_failure_is_non_fatal(self):
        os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = "on"
        response = {"recommendations": [{"major_id": 999, "fit_score": 50.0}]}
        report = persist_shadow(
            self.adapter,
            {"micro_motives": [], "sjt_answers": {}, "conjoint_choices": {}},
            response,
            strict=False,
        )
        self.assertTrue(report.attempted)
        self.assertFalse(report.persisted)
        self.assertIsNotNone(report.error)

    def test_strict_failure_raises(self):
        os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = "1"
        response = {"recommendations": [{"major_id": 999, "fit_score": 50.0}]}
        with self.assertRaises(ValueError):
            persist_shadow(
                self.adapter,
                {"micro_motives": [], "sjt_answers": {}, "conjoint_choices": {}},
                response,
                strict=True,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
