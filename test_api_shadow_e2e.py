"""End-to-end shadow persistence contract tests.

The scoring source remains the JSON-backed DarkHorseEngineV2. The shadow layer is
observability/persistence only and must not alter the returned response.
"""
from __future__ import annotations

import copy
import os
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Major, SchoolBranch, UserSession, DiscoveryResult, BranchRecommendation
from operational_store import OperationalStore
from api_persistence_adapter import OperationalPersistenceAdapter
import shadow_persistence


class ApiShadowE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        @event.listens_for(cls.engine, "connect")
        def enable_fk(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with self.SessionLocal() as db:
            db.add(Major(id=1, name="Test Major", group="Test", strategy_weights=[[0.0]*5 for _ in range(25)], value_weights={}))
            db.add(SchoolBranch(id=1, name="Test Branch", group="Test", strategy_weights=[[0.0]*5 for _ in range(25)], value_weights={}))
            db.commit()
        self.adapter = OperationalPersistenceAdapter(OperationalStore(self.SessionLocal))
        self.old_shadow = os.environ.get("DARK_HORSE_SHADOW_PERSISTENCE")
        self.old_cutover = os.environ.get("POSTGRES_RUNTIME_CUTOVER_APPROVED")
        os.environ["POSTGRES_RUNTIME_CUTOVER_APPROVED"] = "false"

    def tearDown(self):
        if self.old_shadow is None:
            os.environ.pop("DARK_HORSE_SHADOW_PERSISTENCE", None)
        else:
            os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = self.old_shadow
        if self.old_cutover is None:
            os.environ.pop("POSTGRES_RUNTIME_CUTOVER_APPROVED", None)
        else:
            os.environ["POSTGRES_RUNTIME_CUTOVER_APPROVED"] = self.old_cutover

    def _request(self):
        return {
            "session_uuid": "session-e2e-001",
            "micro_motives": ["MOT-001"],
            "sjt_answers": {"S01": 2},
            "conjoint_choices": {"Q1": "A"},
            "language_preference": "fa",
        }

    def _response(self):
        return {
            "discovered_majors": [
                {
                    "major_id": 1,
                    "major_name_fa": "رشته آزمایشی",
                    "individuality_fit": {
                        "score": 82.5,
                        "level": "بالا",
                        "raw_components": {"m_score": 90, "v_score": 80, "s_score": 70},
                        "matched_motives": ["MOT-001"],
                        "strategy_highlights": {"S01": 2},
                        "value_alignment": {"Q1": "A"},
                        "warnings": [],
                        "personalized_description": "شرح آزمایشی",
                    },
                }
            ]
        }

    def _branch_response(self):
        return {
            "recommended_branches": [
                {
                    "branch_name": "Test Branch",
                    "average_score": 88.0,
                    "avg_components": {"m_score": 90, "v_score": 86, "s_score": 88},
                    "matched_motives": ["MOT-001"],
                }
            ]
        }

    def test_shadow_off_is_strict_noop_and_response_identity_is_preserved(self):
        os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = "false"
        before = self._response()
        response = copy.deepcopy(before)
        report = shadow_persistence.persist_shadow(self.adapter, self._request(), response, branch_response=self._branch_response())
        self.assertFalse(report.attempted)
        self.assertFalse(report.persisted)
        self.assertEqual(response, before)
        with self.SessionLocal() as db:
            self.assertEqual(db.query(UserSession).count(), 0)

    def test_shadow_on_persists_without_mutating_response(self):
        os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = "true"
        before = self._response()
        response = copy.deepcopy(before)
        report = shadow_persistence.persist_shadow(self.adapter, self._request(), response, branch_response=self._branch_response(), strict=True)
        self.assertTrue(report.attempted)
        self.assertTrue(report.persisted)
        self.assertEqual(response, before)
        with self.SessionLocal() as db:
            self.assertEqual(db.query(UserSession).count(), 1)
            self.assertEqual(db.query(DiscoveryResult).count(), 1)
            self.assertEqual(db.query(BranchRecommendation).count(), 1)
            session = db.query(UserSession).first()
            self.assertTrue(session.is_completed)
            self.assertEqual(session.session_uuid, "session-e2e-001")

    def test_shadow_on_is_never_allowed_when_cutover_gate_is_true(self):
        os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = "true"
        os.environ["POSTGRES_RUNTIME_CUTOVER_APPROVED"] = "true"
        with self.assertRaises(RuntimeError):
            shadow_persistence.persist_shadow(self.adapter, self._request(), self._response(), strict=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
