from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from types import SimpleNamespace

from ai_rate_limit import SlidingWindowRateLimiter
from main_v2 import darkhorse_counsel


class FakeClock:
    def __init__(self, value: float = 0.0):
        self.value = value

    def __call__(self) -> float:
        return self.value


class AiRateLimitTests(unittest.IsolatedAsyncioTestCase):
    def test_sliding_window_blocks_after_limit_and_recovers(self):
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10, max_clients=2, clock=clock)

        self.assertEqual(limiter.allow("client-a"), (True, 0))
        self.assertEqual(limiter.allow("client-a"), (True, 0))
        allowed, retry_after = limiter.allow("client-a")
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry_after, 1)

        clock.value = 10.001
        self.assertEqual(limiter.allow("client-a"), (True, 0))

    def test_rate_limiter_is_bounded(self):
        limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, max_clients=2)
        limiter.allow("a")
        limiter.allow("b")
        limiter.allow("c")
        self.assertLessEqual(len(limiter._events), 2)

    async def test_counsel_endpoint_returns_429_without_calling_ai(self):
        request = SimpleNamespace(client=SimpleNamespace(host="198.51.100.10"))
        payload = {"profile": {}, "top_results": []}

        from main_v2 import COUNSEL_RATE_LIMITER
        COUNSEL_RATE_LIMITER.reset()
        COUNSEL_RATE_LIMITER.limit = 1

        try:
            with patch("main_v2.generate_counseling", new=AsyncMock(return_value="ok")) as generate:
                first = await darkhorse_counsel(payload, request)
                self.assertEqual(first["success"], True)
                generate.assert_awaited_once()

                with self.assertRaises(HTTPException) as ctx:
                    await darkhorse_counsel(payload, request)
                self.assertEqual(ctx.exception.status_code, 429)
                self.assertIn("Retry-After", ctx.exception.headers)
                self.assertEqual(generate.await_count, 1)
        finally:
            COUNSEL_RATE_LIMITER.reset()
            COUNSEL_RATE_LIMITER.limit = 10


if __name__ == "__main__":
    unittest.main(verbosity=2)
