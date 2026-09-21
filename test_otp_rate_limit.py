from __future__ import annotations

import unittest
from datetime import timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import password_reset_service as prs
import phone_verification_service as pvs


class OtpRateLimitTests(unittest.TestCase):
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
        self.db.execute(text("DELETE FROM phone_verifications"))
        self.db.execute(text("DELETE FROM users"))
        self.db.commit()
        self.addCleanup(self.db.close)

    def _add_verification(self, *, ident: int, phone: str, purpose: str, request_ip: str, created_at):
        self.db.execute(
            text("""
                INSERT INTO phone_verifications
                (id, challenge_id, phone, purpose, name, password_hash, code_hash, attempts, expires_at, request_ip, created_at)
                VALUES (:id, :challenge_id, :phone, :purpose, :name, :password_hash, :code_hash, 0, :expires_at, :request_ip, :created_at)
            """),
            {
                "id": ident,
                "challenge_id": f"challenge-{ident}",
                "phone": phone,
                "purpose": purpose,
                "name": "Rate Test",
                "password_hash": "x",
                "code_hash": "y",
                "expires_at": created_at + timedelta(minutes=5),
                "request_ip": request_ip,
                "created_at": created_at,
            },
        )

    def test_registration_blocks_after_three_sms_for_same_phone_in_ten_minutes(self):
        now = pvs.utcnow()
        for idx in range(1, 4):
            self._add_verification(
                ident=idx,
                phone="09120000001",
                purpose="register",
                request_ip="10.0.0.1",
                created_at=now - timedelta(minutes=idx + 1),
            )
        with self.assertRaises(TimeoutError):
            pvs.request_registration_otp(
                self.db,
                name="Rate User",
                phone="09120000001",
                password="StrongPass123",
                request_ip="10.0.0.1",
            )

    def test_registration_blocks_after_ten_sms_from_same_ip_in_one_hour(self):
        now = pvs.utcnow()
        for idx in range(1, 11):
            self._add_verification(
                ident=idx,
                phone=f"091200000{idx:02d}",
                purpose="register",
                request_ip="10.0.0.2",
                created_at=now - timedelta(minutes=idx),
            )
        with self.assertRaises(TimeoutError):
            pvs.request_registration_otp(
                self.db,
                name="Rate User",
                phone="09910000001",
                password="StrongPass123",
                request_ip="10.0.0.2",
            )

    def test_password_reset_uses_the_same_phone_limit(self):
        now = prs.utcnow()
        self.db.execute(
            text("""
                INSERT INTO users
                (public_id, name, phone, password_hash, role, status, created_at)
                VALUES ('reset-rate-user', 'Reset Rate', '09121112222', 'hash', 'user', 'active', :created_at)
            """),
            {"created_at": now},
        )
        for idx in range(1, 4):
            self._add_verification(
                ident=idx,
                phone="09121112222",
                purpose="password_reset",
                request_ip="10.0.0.3",
                created_at=now - timedelta(minutes=idx + 1),
            )
        self.db.commit()
        with self.assertRaises(TimeoutError):
            prs.request_password_reset_otp(
                self.db,
                phone="09121112222",
                request_ip="10.0.0.3",
            )

    def test_phone_window_is_shared_across_register_and_password_reset(self):
        now = pvs.utcnow()
        for idx, purpose in enumerate(("register", "register", "password_reset"), start=1):
            self._add_verification(
                ident=idx,
                phone="09123334455",
                purpose=purpose,
                request_ip="10.0.0.5",
                created_at=now - timedelta(minutes=idx + 1),
            )
        with self.assertRaises(TimeoutError):
            pvs.enforce_sms_rate_limit(
                self.db,
                phone="09123334455",
                request_ip="10.0.0.5",
            )

    def test_ip_window_is_shared_across_register_and_password_reset(self):
        now = pvs.utcnow()
        for idx in range(1, 11):
            self._add_verification(
                ident=idx,
                phone=f"0912333{idx:04d}",
                purpose="register" if idx < 10 else "password_reset",
                request_ip="10.0.0.6",
                created_at=now - timedelta(minutes=idx),
            )
        with self.assertRaises(TimeoutError):
            pvs.enforce_sms_rate_limit(
                self.db,
                phone="09127770001",
                request_ip="10.0.0.6",
            )

    def test_password_reset_unknown_and_known_phone_response_shapes_match(self):
        self.db.execute(
            text("""
                INSERT INTO users
                (public_id, name, phone, password_hash, role, status, created_at)
                VALUES ('known-reset-user', 'Known Reset', '09124445566', 'hash', 'user', 'active', :created_at)
            """),
            {"created_at": prs.utcnow()},
        )
        self.db.commit()

        with patch.object(prs, "_send_reset_otp"):
            known = prs.request_password_reset_otp(
                self.db,
                phone="09124445566",
                request_ip="10.0.0.7",
            )
            unknown = prs.request_password_reset_otp(
                self.db,
                phone="09129999999",
                request_ip="10.0.0.7",
            )

        self.assertEqual(set(known), set(unknown))
        self.assertTrue(known["otp_required"])
        self.assertTrue(unknown["otp_required"])
        self.assertTrue(known["challenge_id"])
        self.assertTrue(unknown["challenge_id"])
        self.assertEqual(known["expires_in"], prs.OTP_TTL_SECONDS)
        self.assertEqual(unknown["expires_in"], prs.OTP_TTL_SECONDS)
        self.assertEqual(known["resend_after"], prs.RESEND_COOLDOWN_SECONDS)
        self.assertEqual(unknown["resend_after"], prs.RESEND_COOLDOWN_SECONDS)
        self.assertEqual(known["message"], unknown["message"])
        stored = self.db.execute(
            text("SELECT COUNT(*) FROM phone_verifications WHERE phone = '09124445566'")
        ).scalar_one()
        self.assertEqual(stored, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
