"""P0.3 public discover/counsel payload and quota guard tests."""
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
from pydantic import ValidationError

from ai_rate_limit import SlidingWindowRateLimiter
from main_v2 import (
    MAX_COUNSEL_PAYLOAD_BYTES,
    MAX_DISCOVERY_PAYLOAD_BYTES,
    DarkHorseDiscoverRequest,
    _enforce_payload_limit,
    _enforce_public_rate_limit,
)


ROOT = Path(__file__).resolve().parent


class PayloadLimitTests(unittest.TestCase):
    def make_request(self, headers=None):
        return SimpleNamespace(headers=headers or {})

    def test_declared_oversized_payload_is_rejected(self):
        req = self.make_request({"content-length": str(MAX_DISCOVERY_PAYLOAD_BYTES + 1)})
        with self.assertRaises(HTTPException) as caught:
            _enforce_payload_limit(
                req, {"micro_motives": []},
                max_bytes=MAX_DISCOVERY_PAYLOAD_BYTES, endpoint_label="test",
            )
        self.assertEqual(caught.exception.status_code, 413)

    def test_actual_payload_size_is_checked_without_content_length(self):
        req = self.make_request()
        with self.assertRaises(HTTPException) as caught:
            _enforce_payload_limit(
                req, {"profile": {"text": "x" * (MAX_COUNSEL_PAYLOAD_BYTES + 10)}},
                max_bytes=MAX_COUNSEL_PAYLOAD_BYTES, endpoint_label="test",
            )
        self.assertEqual(caught.exception.status_code, 413)

    def test_discovery_collections_have_protocol_sized_caps(self):
        with self.assertRaises(ValidationError):
            DarkHorseDiscoverRequest(micro_motives=["MED-001"] * 101)
        with self.assertRaises(ValidationError):
            DarkHorseDiscoverRequest(sjt_answers={f"sjt_{i}": "A" for i in range(1, 27)})
        with self.assertRaises(ValidationError):
            DarkHorseDiscoverRequest(conjoint_choices={f"conj_{i}": "Q1A" for i in range(1, 17)})


class PublicRateLimitTests(unittest.TestCase):
    def test_rate_limiter_returns_429_and_retry_after(self):
        limiter = SlidingWindowRateLimiter(
            limit=1, window_seconds=60, max_clients=10, clock=lambda: 100.0
        )
        req = SimpleNamespace(client=SimpleNamespace(host="test-client"))
        _enforce_public_rate_limit(req, limiter, "test")
        with self.assertRaises(HTTPException) as caught:
            _enforce_public_rate_limit(req, limiter, "test")
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.headers["Retry-After"], "60")


class EndpointWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_source = (ROOT / "main_v2.py").read_text(encoding="utf-8")

    def test_discovery_and_counsel_endpoints_apply_guards(self):
        self.assertEqual(
            self.api_source.count("_enforce_public_rate_limit(req, DISCOVERY_RATE_LIMITER"),
            2,
        )
        self.assertGreaterEqual(self.api_source.count("_enforce_payload_limit("), 4)
        self.assertIn("MAX_COUNSEL_PAYLOAD_BYTES", self.api_source)

    def test_cors_origin_is_explicit_not_wildcard(self):
        self.assertIn('allow_origins=["https://asbe-siah.ir"]', self.api_source)
        self.assertNotRegex(
            self.api_source,
            re.compile(r"""allow_origins\s*=\s*\[\s*["']\*["']"""),
        )


if __name__ == "__main__":
    unittest.main()
