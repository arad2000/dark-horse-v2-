from __future__ import annotations

import unittest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Major, SchoolBranch, UserSession, DiscoveryResult, BranchRecommendation, AuditLog, UserFeedback
from operational_store import OperationalStore


class OperationalStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

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
        self.store = OperationalStore(self.SessionLocal)

    def test_create_and_complete_session(self):
        session = self.store.create_session(["MOT-001"], {"S01": "A"}, {"Q1": "A"}, session_uuid="fixed")
        self.store.complete_session(session.id)
        with self.SessionLocal() as db:
            row = db.get(UserSession, session.id)
            self.assertTrue(row.is_completed)
            self.assertEqual(row.session_uuid, "fixed")

    def test_feedback_upsert(self):
        session = self.store.create_session([], {}, {}, session_uuid="feedback")
        self.store.save_feedback(session.id, satisfaction_score=4, recommended_major_id=1)
        self.store.save_feedback(session.id, satisfaction_score=5, recommended_major_id=1)
        with self.SessionLocal() as db:
            rows = db.query(UserFeedback).filter_by(session_id=session.id).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].satisfaction_score, 5)

    def test_unknown_major_rolls_back_results(self):
        session = self.store.create_session([], {}, {}, session_uuid="rollback")
        with self.assertRaises(ValueError):
            self.store.store_discovery_results(session.id, [{"major_id": 999, "fit_score": 77.0}])
        with self.SessionLocal() as db:
            self.assertEqual(db.query(DiscoveryResult).count(), 0)

    def test_unknown_branch_rolls_back_recommendations(self):
        session = self.store.create_session([], {}, {}, session_uuid="branch")
        with self.assertRaises(ValueError):
            self.store.store_branch_recommendations(session.id, [{"branch_name": "Unknown", "fit_score": 70.0}])
        with self.SessionLocal() as db:
            self.assertEqual(db.query(BranchRecommendation).count(), 0)

    def test_archive_creates_audit_log(self):
        session = self.store.create_session([], {}, {}, session_uuid="archive")
        self.store.archive_session(session.id, changed_by="test")
        with self.SessionLocal() as db:
            row = db.get(UserSession, session.id)
            self.assertTrue(row.is_archived)
            logs = db.query(AuditLog).filter_by(record_id=session.id).all()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].action, "archive")

    def test_duplicate_session_uuid_rejected(self):
        self.store.create_session([], {}, {}, session_uuid="duplicate")
        with self.assertRaises(Exception):
            self.store.create_session([], {}, {}, session_uuid="duplicate")


if __name__ == "__main__":
    unittest.main(verbosity=2)
