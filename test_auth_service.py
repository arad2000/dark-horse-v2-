from __future__ import annotations

import unittest
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth_service import (
    authenticate_user,
    hash_password,
    hash_token,
    register_user,
    resolve_session,
    revoke_session,
    verify_password,
)
from billing_models import AuthSession, User
from models import Base


class AuthServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False)
        _ = (User, AuthSession)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def test_password_hash_is_not_plaintext_and_verifies(self):
        encoded = hash_password("strong-pass-123")
        self.assertNotEqual(encoded, "strong-pass-123")
        self.assertTrue(verify_password("strong-pass-123", encoded))
        self.assertFalse(verify_password("wrong-pass", encoded))

    def test_register_login_resolve_and_revoke(self):
        with self.SessionLocal() as db:
            user, token = register_user(db, name="Test User", phone="09000000000", password="strong-pass-123")
            db.commit()
            self.assertEqual(user.phone, "09000000000")
            self.assertNotEqual(token, hash_token(token))

            resolved = resolve_session(db, token)
            self.assertEqual(resolved.id, user.id)

            logged_in, token2 = authenticate_user(db, phone="09000000000", password="strong-pass-123")
            self.assertEqual(logged_in.id, user.id)
            self.assertNotEqual(token, token2)

            revoke_session(db, token2)
            db.commit()
            with self.assertRaises(ValueError):
                resolve_session(db, token2)

    def test_duplicate_phone_rejected(self):
        with self.SessionLocal() as db:
            register_user(db, name="One", phone="09120000000", password="strong-pass-123")
            db.commit()
            with self.assertRaises(ValueError):
                register_user(db, name="Two", phone="09120000000", password="strong-pass-456")

    def test_expired_session_rejected(self):
        with self.SessionLocal() as db:
            user = User(id=1, public_id="u1", name="Test", phone="09200000000", password_hash=hash_password("strong-pass-123"))
            db.add(user)
            db.flush()
            session = AuthSession(user_id=user.id, token_hash=hash_token("expired-token"), expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc) - timedelta(minutes=1))
            db.add(session)
            db.commit()
            with self.assertRaises(ValueError):
                resolve_session(db, "expired-token")


if __name__ == "__main__":
    unittest.main(verbosity=2)
