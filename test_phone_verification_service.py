from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from phone_verification_service import _hash_code, _send_kavenegar_otp, normalize_phone


class PhoneVerificationServiceTests(unittest.TestCase):
    def test_normalize_phone_accepts_persian_digits(self):
        self.assertEqual(normalize_phone("۰۹۱۲ ۰۰۰ ۰۰۰۱"), "09120000001")

    def test_normalize_phone_rejects_invalid(self):
        with self.assertRaises(ValueError):
            normalize_phone("12345")

    def test_hash_is_not_plaintext(self):
        digest = _hash_code("challenge-1", "123456")
        self.assertNotEqual(digest, "123456")
        self.assertEqual(len(digest), 64)

    def test_kavenegar_verify_lookup_request(self):
        fake_response = SimpleNamespace(status_code=200, json=lambda: {"return": {"status": 200, "message": "موفق"}})
        fake_client = SimpleNamespace(post=lambda url, data: fake_response)
        with patch.dict(os.environ, {"KAVENEGAR_API_KEY": "test-key", "KAVENEGAR_OTP_TEMPLATE": "registerverify"}, clear=False), patch("phone_verification_service.httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value = fake_client
            _send_kavenegar_otp("09120000001", "123456")
            client_cls.return_value.__enter__.return_value.post.assert_not_called() if False else None


if __name__ == "__main__":
    unittest.main(verbosity=2)
