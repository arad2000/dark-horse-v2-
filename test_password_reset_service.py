import unittest
from datetime import timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import password_reset_service as prs
from auth_service import hash_password, hash_token, resolve_session
from billing_models import AuthSession, User


class PasswordResetServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        with cls.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    public_id VARCHAR(36) NOT NULL UNIQUE,
                    name VARCHAR(200) NOT NULL,
                    phone VARCHAR(32) NOT NULL UNIQUE,
                    password_hash TEXT,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    created_at DATETIME,
                    updated_at DATETIME,
                    last_login_at DATETIME
                )
            """))
            conn.execute(text("""
                CREATE TABLE auth_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash VARCHAR(128) NOT NULL UNIQUE,
                    expires_at DATETIME NOT NULL,
                    revoked_at DATETIME,
                    created_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """))
            conn.execute(text("""
                CREATE TABLE phone_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenge_id VARCHAR(128) NOT NULL UNIQUE,
                    phone VARCHAR(32) NOT NULL,
                    purpose VARCHAR(32) NOT NULL DEFAULT 'register',
                    name VARCHAR(200) NOT NULL,
                    password_hash TEXT NOT NULL,
                    code_hash VARCHAR(128) NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    expires_at DATETIME NOT NULL,
                    verified_at DATETIME,
                    request_ip VARCHAR(45),
                    created_at DATETIME
                )
            """))
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.db = self.Session()
        self.addCleanup(self.db.close)

    def test_reset_otp_changes_password_revokes_old_sessions_and_is_single_use(self):
        user = User(
            public_id="user-reset-test",
            name="Reset User",
            phone="09121234567",
            password_hash=hash_password("OldPassword123"),
        )
        self.db.add(user)
        self.db.flush()

        old_token = "old-session-token"
        old_session = AuthSession(
            user_id=user.id,
            token_hash=hash_token(old_token),
            expires_at=prs.utcnow() + timedelta(hours=1),
        )
        self.db.add(old_session)
        self.db.commit()

        sent = {}
        original_sender = prs._send_reset_otp
        original_issue = prs.issue_session
        prs._send_reset_otp = lambda phone, code: sent.update(phone=phone, code=code)

        def issue_test_session(db, reset_user):
            token = "new-session-token"
            session = AuthSession(
                user_id=reset_user.id,
                token_hash=hash_token(token),
                expires_at=prs.utcnow() + timedelta(hours=1),
            )
            db.add(session)
            db.flush()
            return token, session

        prs.issue_session = issue_test_session
        self.addCleanup(lambda: setattr(prs, "_send_reset_otp", original_sender))
        self.addCleanup(lambda: setattr(prs, "issue_session", original_issue))

        result = prs.request_password_reset_otp(self.db, phone=user.phone)
        self.db.commit()
        self.assertTrue(result["otp_required"])
        self.assertIn("challenge_id", result)
        self.assertEqual(sent["phone"], user.phone)

        with self.assertRaises(ValueError):
            prs.reset_password_with_otp(
                self.db,
                challenge_id=result["challenge_id"],
                code="000000" if sent["code"] != "000000" else "111111",
                new_password="NewPassword123",
            )
        self.db.rollback()

        user_db, new_token = prs.reset_password_with_otp(
            self.db,
            challenge_id=result["challenge_id"],
            code=sent["code"],
            new_password="NewPassword123",
        )
        self.db.commit()

        self.assertEqual(user_db.id, user.id)
        self.assertTrue(resolve_session(self.db, new_token))
        with self.assertRaises(ValueError):
            resolve_session(self.db, old_token)
        self.assertIsNotNone(self.db.get(AuthSession, old_session.id).revoked_at)

        with self.assertRaises(ValueError):
            prs.reset_password_with_otp(
                self.db,
                challenge_id=result["challenge_id"],
                code=sent["code"],
                new_password="AnotherPassword123",
            )

    def test_unknown_phone_does_not_issue_a_challenge(self):
        result = prs.request_password_reset_otp(self.db, phone="09120000000")
        self.assertFalse(result["otp_required"])
        self.assertIn("اگر حسابی", result["message"])

    def test_resend_is_rate_limited(self):
        user = User(
            public_id="user-reset-rate",
            name="Rate User",
            phone="09121112222",
            password_hash=hash_password("OldPassword123"),
        )
        self.db.add(user)
        self.db.flush()

        original_sender = prs._send_reset_otp
        prs._send_reset_otp = lambda phone, code: None
        self.addCleanup(lambda: setattr(prs, "_send_reset_otp", original_sender))
        prs.request_password_reset_otp(self.db, phone=user.phone)
        self.db.flush()
        with self.assertRaises(TimeoutError):
            prs.request_password_reset_otp(self.db, phone=user.phone)


if __name__ == "__main__":
    unittest.main()
