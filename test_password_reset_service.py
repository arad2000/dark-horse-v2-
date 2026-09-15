import unittest
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import password_reset_service as prs
from auth_service import hash_password, issue_session, resolve_session
from billing_models import AuthSession, PhoneVerification, User
from models import Base


class PasswordResetServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            cls.engine,
            tables=[User.__table__, AuthSession.__table__, PhoneVerification.__table__],
        )
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
        old_token, old_session = issue_session(self.db, user)
        self.db.commit()

        sent = {}
        original_sender = prs._send_reset_otp
        prs._send_reset_otp = lambda phone, code: sent.update(phone=phone, code=code)
        self.addCleanup(lambda: setattr(prs, "_send_reset_otp", original_sender))

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
