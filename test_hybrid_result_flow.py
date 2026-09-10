from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from billing_models import User
from main_v2 import app
from models import Base, BranchRecommendation, Major, SchoolBranch, UserSession, DiscoveryResult


class _FakeEngine:
    def discover_individuality(self, micro_motives, sjt_answers, conjoint_choices):
        return {
            "discovered_majors": [
                {
                    "major_id": 1,
                    "major_name_fa": "رشته آزمون",
                    "realm_fa": "گروه آزمون",
                    "individuality_fit": {
                        "score": 91.5,
                        "level": "عالی",
                        "raw_components": {"m_score": 92.0, "s_score": 90.0, "v_score": 93.0},
                        "evidence": {"source": "fixture"},
                    },
                }
            ]
        }

    def recommend_school_branch(self, micro_motives, sjt_answers, conjoint_choices):
        return {
            "recommended_branches": [
                {
                    "branch_name": "Test Branch",
                    "average_score": 88.0,
                    "count": 3,
                    "avg_components": {"m_score": 89.0, "s_score": 87.0, "v_score": 88.0},
                    "evidence": {"matched": ["MOT-001"]},
                    "warning": "هشدار آزمایشی",
                    "alternative_paths": ["مسیر جایگزین"],
                }
            ],
            "best_branch": "Test Branch",
            "method": {"name": "test"},
            "summary": {"ok": True},
            "next_step": "ادامه",
        }


class HybridResultFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine_db = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(cls.engine_db, "connect")
        def enable_fk(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        cls.SessionLocal = sessionmaker(bind=cls.engine_db, autoflush=False, expire_on_commit=False)
        Base.metadata.create_all(cls.engine_db)

        with cls.SessionLocal() as db:
            db.add(User(id=1, public_id="user-1", name="Flow User", phone="09120000001", password_hash="hash"))
            db.add(
                Major(
                    id=1,
                    name="رشته آزمون",
                    group="آزمون",
                    strategy_weights=[[0.0] * 5 for _ in range(25)],
                    value_weights={},
                )
            )
            db.add(
                SchoolBranch(
                    id=1,
                    name="Test Branch",
                    group="آزمون",
                    strategy_weights=[[0.0] * 5 for _ in range(25)],
                    value_weights={},
                )
            )
            db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.engine_db.dispose()

    def test_anonymous_session_is_claimed_then_saved_after_login(self):
        app.state.engine = _FakeEngine()
        anonymous_client = TestClient(app)

        with patch("main_v2._authenticated_user_id", return_value=None), \
             patch("database.SessionLocal", self.SessionLocal), \
             patch("operational_store.SessionLocal", self.SessionLocal):
            discovery = anonymous_client.post(
                "/api/v2/darkhorse/discover",
                json={
                    "micro_motives": ["MOT-001"],
                    "sjt_answers": {"S01": "A"},
                    "conjoint_choices": {"Q1": "A"},
                },
            )

        self.assertEqual(discovery.status_code, 200, discovery.text)
        session_uuid = discovery.json()["session_id"]
        self.assertTrue(session_uuid)
        operational_session_id = discovery.json()["operational_session_id"]
        self.assertIsNotNone(operational_session_id)

        with self.SessionLocal() as db:
            session = db.query(UserSession).filter_by(session_uuid=session_uuid).one()
            self.assertIsNone(session.user_id)
            self.assertFalse(session.is_completed)
            self.assertEqual(
                db.query(DiscoveryResult).filter_by(session_id=session.id, major_id=1).count(),
                1,
            )

        authenticated_client = TestClient(app)
        with patch("main_v2._authenticated_user_id", return_value=1), \
             patch("database.SessionLocal", self.SessionLocal), \
             patch("operational_store.SessionLocal", self.SessionLocal):
            claimed = authenticated_client.post(
                "/api/v2/darkhorse/discover",
                headers={"Authorization": "Bearer user-token"},
                json={
                    "session_id": session_uuid,
                    "micro_motives": ["MOT-001"],
                    "sjt_answers": {"S01": "A"},
                    "conjoint_choices": {"Q1": "A"},
                },
            )

        self.assertEqual(claimed.status_code, 200, claimed.text)
        self.assertEqual(claimed.json()["session_id"], session_uuid)
        self.assertEqual(claimed.json()["operational_session_id"], operational_session_id)
        self.assertTrue(claimed.json()["operational_result_persisted"])

        with self.SessionLocal() as db:
            session = db.query(UserSession).filter_by(session_uuid=session_uuid).one()
            self.assertEqual(session.user_id, 1)
            self.assertFalse(session.is_completed)
            self.assertEqual(
                db.query(DiscoveryResult).filter_by(session_id=session.id, major_id=1).count(),
                1,
            )

        with patch("database.SessionLocal", self.SessionLocal), \
             patch("operational_store.SessionLocal", self.SessionLocal), \
             patch("commercial_api.resolve_session", return_value=SimpleNamespace(id=1)):
            saved = authenticated_client.post(
                "/api/v1/me/save-result",
                headers={"Authorization": "Bearer user-token"},
                json={
                    "session_id": session_uuid,
                    "result_summary": {
                        "session_id": session_uuid,
                        "kind": "majors",
                        "top_major_id": 1,
                        "top_score": 91.5,
                    },
                },
            )

        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertTrue(saved.json()["saved"])
        self.assertTrue(saved.json()["completed"])

        with self.SessionLocal() as db:
            session = db.query(UserSession).filter_by(session_uuid=session_uuid).one()
            self.assertEqual(session.user_id, 1)
            self.assertTrue(session.is_completed)
            self.assertEqual(
                db.query(DiscoveryResult).filter_by(session_id=session.id, major_id=1).count(),
                1,
            )

    def test_branch_discovery_reuses_same_session_after_claim(self):
        app.state.engine = _FakeEngine()
        app.state.branch_engine = app.state.engine
        anonymous_client = TestClient(app)

        with patch("main_v2._authenticated_user_id", return_value=None), \
             patch("database.SessionLocal", self.SessionLocal), \
             patch("operational_store.SessionLocal", self.SessionLocal):
            discovery = anonymous_client.post(
                "/api/v2/darkhorse/discover",
                json={
                    "micro_motives": ["MOT-001"],
                    "sjt_answers": {"S01": "A"},
                    "conjoint_choices": {"Q1": "A"},
                },
            )
        self.assertEqual(discovery.status_code, 200, discovery.text)
        session_uuid = discovery.json()["session_id"]
        operational_session_id = discovery.json()["operational_session_id"]
        self.assertTrue(session_uuid)
        self.assertIsNotNone(operational_session_id)

        with patch("main_v2._authenticated_user_id", return_value=1), \
             patch("database.SessionLocal", self.SessionLocal), \
             patch("operational_store.SessionLocal", self.SessionLocal):
            branches = anonymous_client.post(
                "/api/v2/darkhorse/branch-discovery",
                headers={"Authorization": "Bearer user-token"},
                json={
                    "session_id": session_uuid,
                    "micro_motives": ["MOT-001"],
                    "sjt_answers": {"S01": "A"},
                    "conjoint_choices": {"Q1": "A"},
                },
            )

        self.assertEqual(branches.status_code, 200, branches.text)
        branch_body = branches.json()
        self.assertEqual(branch_body["session_id"], session_uuid)
        self.assertEqual(branch_body["operational_session_id"], operational_session_id)
        self.assertTrue(branch_body["operational_result_persisted"])
        self.assertEqual(branch_body["branch_discovery_result"]["best_branch"], "Test Branch")

        with self.SessionLocal() as db:
            session = db.query(UserSession).filter_by(session_uuid=session_uuid).one()
            self.assertEqual(session.user_id, 1)
            self.assertEqual(db.query(UserSession).count(), 1)
            self.assertEqual(
                db.query(DiscoveryResult).filter_by(session_id=session.id, major_id=1).count(),
                1,
            )
            self.assertEqual(
                db.query(BranchRecommendation).filter_by(session_id=session.id, branch_id=1).count(),
                1,
            )

    def test_authenticated_discovery_to_save_result_and_retry(self):
        app.state.engine = _FakeEngine()
        headers = {"Authorization": "Bearer flow-token"}

        with patch("main_v2._authenticated_user_id", return_value=1), \
             patch("database.SessionLocal", self.SessionLocal), \
             patch("operational_store.SessionLocal", self.SessionLocal), \
             patch("commercial_api.resolve_session", return_value=SimpleNamespace(id=1)):
            client = TestClient(app)
            discovery = client.post(
                "/api/v2/darkhorse/discover",
                headers=headers,
                json={
                    "micro_motives": ["MOT-001"],
                    "sjt_answers": {"S01": "A"},
                    "conjoint_choices": {"Q1": "A"},
                },
            )
            self.assertEqual(discovery.status_code, 200, discovery.text)
            discovery_body = discovery.json()
            self.assertTrue(discovery_body["session_id"])
            self.assertIsNotNone(discovery_body["operational_session_id"])
            self.assertTrue(discovery_body["operational_result_persisted"])
            session_uuid = discovery_body["session_id"]

            save_payload = {
                "session_id": session_uuid,
                "result_summary": {
                    "session_id": session_uuid,
                    "kind": "majors",
                    "top_major_id": 1,
                    "top_score": 91.5,
                },
            }
            first_save = client.post("/api/v1/me/save-result", headers=headers, json=save_payload)
            self.assertEqual(first_save.status_code, 200, first_save.text)
            self.assertTrue(first_save.json()["saved"])
            self.assertTrue(first_save.json()["completed"])

            save_payload["result_summary"]["retry"] = True
            second_save = client.post("/api/v1/me/save-result", headers=headers, json=save_payload)
            self.assertEqual(second_save.status_code, 200, second_save.text)
            self.assertEqual(first_save.json()["operational_session_id"], second_save.json()["operational_session_id"])

            with self.SessionLocal() as db:
                session = db.query(UserSession).filter_by(session_uuid=session_uuid).one()
                self.assertEqual(session.user_id, 1)
                self.assertTrue(session.is_completed)
                self.assertTrue(session.result_summary["retry"])
                self.assertEqual(
                    db.query(DiscoveryResult).filter_by(session_id=session.id, major_id=1).count(),
                    1,
                )

    def test_second_user_cannot_save_result_to_first_users_session(self):
        with self.SessionLocal() as db:
            session = UserSession(
                user_id=1,
                session_uuid="owned-flow-session",
                micro_motives=[],
                sjt_answers={},
                conjoint_choices={},
            )
            db.add(session)
            db.flush()
            db.add(
                DiscoveryResult(
                    session_id=session.id,
                    major_id=1,
                    m_score=80.0,
                    s_score=80.0,
                    v_score=80.0,
                    total_score=80.0,
                    rank=1,
                )
            )
            db.commit()

        headers = {"Authorization": "Bearer other-token"}
        with patch("database.SessionLocal", self.SessionLocal), \
             patch("operational_store.SessionLocal", self.SessionLocal), \
             patch("commercial_api.resolve_session", return_value=SimpleNamespace(id=2)):
            client = TestClient(app)
            response = client.post(
                "/api/v1/me/save-result",
                headers=headers,
                json={
                    "session_id": "owned-flow-session",
                    "result_summary": {"session_id": "owned-flow-session", "kind": "majors"},
                },
            )
        self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
