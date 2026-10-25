from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

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
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"return": {"status": 200, "message": "موفق"}}
        client = MagicMock()
        client.post.return_value = response
        with patch.dict(os.environ, {"KAVENEGAR_API_KEY": "test-key", "KAVENEGAR_OTP_TEMPLATE": "registerverify"}, clear=False), patch("phone_verification_service.httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value = client
            _send_kavenegar_otp("09120000001", "123456")
        client.post.assert_called_once_with(
            "https://api.kavenegar.com/v1/test-key/verify/lookup.json",
            data={"receptor": "09120000001", "token": "123456", "template": "registerverify", "type": "sms"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
