from __future__ import annotations

import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api_persistence_adapter import OperationalPersistenceAdapter, assert_safe_mode
from models import Base, Major, SchoolBranch, UserSession, DiscoveryResult, BranchRecommendation, UserFeedback
from operational_store import OperationalStore


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(cls.engine, "connect")
        def enable_fk(dbapi_connection, _record):
            cur = dbapi_connection.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with self.SessionLocal() as db:
            db.add(Major(id=1, name="Test Major", group="Test", strategy_weights=[[0.0] * 5 for _ in range(25)], value_weights={}))
            db.add(SchoolBranch(id=1, name="Test Branch", group="Test", strategy_weights=[[0.0] * 5 for _ in range(25)], value_weights={}))
            db.commit()
        self.adapter = OperationalPersistenceAdapter(OperationalStore(self.SessionLocal))

    def test_create_session_and_persist_discovery(self):
        session = self.adapter.create_session(
            {"micro_motives": [], "sjt_answers": {}, "conjoint_choices": {}, "session_uuid": "api-1"},
            request_meta={"user_agent": "test"},
        )
        self.adapter.persist_discovery(
            session.id,
            {
                "recommendations": [
                    {"major_id": 1, "fit_score": 81.5, "fit_level": "high"}
                ]
            },
        )
        with self.SessionLocal() as db:
            self.assertIsNotNone(db.get(UserSession, session.id))
            self.assertEqual(db.query(DiscoveryResult).count(), 1)
            self.assertEqual(db.query(DiscoveryResult).one().rank, 1)

    def test_persist_branch(self):
        session = self.adapter.create_session({"micro_motives": [], "sjt_answers": {}, "conjoint_choices": {}}, request_meta={})
        self.adapter.persist_branch_discovery(
            session.id,
            {"branches": [{"branch_name": "Test Branch", "fit_score": 72.25}]},
        )
        with self.SessionLocal() as db:
            self.assertEqual(db.query(BranchRecommendation).count(), 1)
            self.assertEqual(db.query(BranchRecommendation).one().rank, 1)

    def test_feedback_and_complete(self):
        session = self.adapter.create_session({"micro_motives": [], "sjt_answers": {}, "conjoint_choices": {}}, request_meta={})
        self.adapter.feedback(session.id, {"satisfaction_score": 4, "accuracy_rating": 5, "recommended_major_id": 1})
        self.adapter.complete(session.id)
        with self.SessionLocal() as db:
            self.assertTrue(db.get(UserSession, session.id).is_completed)
            self.assertEqual(db.query(UserFeedback).count(), 1)

    def test_invalid_discovery_is_rejected_before_persistence(self):
        session = self.adapter.create_session({"micro_motives": [], "sjt_answers": {}, "conjoint_choices": {}}, request_meta={})
        with self.assertRaises(ValueError):
            self.adapter.persist_discovery(
                session.id,
                {"recommendations": [{"major_id": 1, "fit_score": 150.0}]},
            )
        with self.SessionLocal() as db:
            self.assertEqual(db.query(DiscoveryResult).count(), 0)

    def test_invalid_branch_is_rejected(self):
        session = self.adapter.create_session({"micro_motives": [], "sjt_answers": {}, "conjoint_choices": {}}, request_meta={})
        with self.assertRaises(ValueError):
            self.adapter.persist_branch_discovery(
                session.id,
                {"branches": [{"branch_name": "Unknown", "fit_score": 50.0}]},
            )
        with self.SessionLocal() as db:
            self.assertEqual(db.query(BranchRecommendation).count(), 0)

    def test_safe_mode_gate_is_off(self):
        assert_safe_mode()


if __name__ == "__main__":
    unittest.main(verbosity=2)
