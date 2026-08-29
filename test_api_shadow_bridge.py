from __future__ import annotations

import copy
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api_persistence_adapter import OperationalPersistenceAdapter
from api_shadow_bridge import persist_api_shadow
from models import Base, Major, SchoolBranch, UserSession
from operational_store import OperationalStore


class ApiShadowBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with self.SessionLocal() as db:
            db.add(
                Major(
                    id=1,
                    name="Test Major",
                    group="Test",
                    strategy_weights=[[0.0] * 5 for _ in range(25)],
                    value_weights={},
                )
            )
            db.add(
                SchoolBranch(
                    id=1,
                    name="Test Branch",
                    group="Test",
                    strategy_weights=[[0.0] * 5 for _ in range(25)],
                    value_weights={},
                )
            )
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

    @staticmethod
    def payload():
        return {
            "micro_motives": ["MOT-001"],
            "sjt_answers": {"S01": {"selected": 0}},
            "conjoint_choices": {"Q1": "A"},
            "language_preference": "fa",
        }

    @staticmethod
    def response():
        return {
            "session_id": "e2e-bridge-001",
            "discovery_result": {
                "total_matches": 1,
                "recommendations": [
                    {
                        "major_id": 1,
                        "fit_score": 82.5,
                        "fit_level": "بالا",
                        "raw_components": {"m_score": 90, "v_score": 80, "s_score": 70},
                        "evidence": {"matched": ["MOT-001"]},
                    }
                ],
            },
            "branch_discovery_result": {
                "total_matches": 1,
                "best_branch": "Test Branch",
                "branches": [
                    {
                        "branch_name": "Test Branch",
                        "average_score": 88.0,
                        "avg_components": {"m_score": 90, "v_score": 86, "s_score": 88},
                    }
                ],
            },
        }

    def test_bridge_off_is_noop(self):
        os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = "false"
        response = self.response()
        original = copy.deepcopy(response)
        returned, report = persist_api_shadow(self.payload(), response, self.adapter)
        self.assertEqual(response, original)
        self.assertEqual(returned, original)
        self.assertFalse(report.attempted)
        with self.SessionLocal() as db:
            self.assertEqual(db.query(UserSession).count(), 0)

    def test_bridge_on_persists_and_preserves_response(self):
        os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = "true"
        response = self.response()
        original = copy.deepcopy(response)
        returned, report = persist_api_shadow(self.payload(), response, self.adapter)
        self.assertEqual(response, original)
        self.assertEqual(returned, original)
        self.assertTrue(report.attempted)
        self.assertTrue(report.persisted)
        self.assertIsNotNone(report.session_id)
        with self.SessionLocal() as db:
            self.assertEqual(db.query(UserSession).count(), 1)

    def test_bridge_carries_request_metadata_without_touching_response(self):
        os.environ["DARK_HORSE_SHADOW_PERSISTENCE"] = "true"
        response = self.response()
        returned, report = persist_api_shadow(
            self.payload(),
            response,
            self.adapter,
            request_meta={"user_ip": "127.0.0.1", "user_agent": "test-agent"},
        )
        self.assertTrue(report.persisted)
        self.assertEqual(returned, response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
