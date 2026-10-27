from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from auth_login_rate_limit import LoginAttemptRateLimiter
import commercial_api
from password_reset_service import MAX_ATTEMPTS, RESET_PURPOSE, enforce_sms_rate_limit


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds: float):
        self.now += seconds


class FakeDb:
    def __init__(self):
        self.rollbacks = 0

    def rollback(self):
        self.rollbacks += 1


def fail_attempt(limiter: LoginAttemptRateLimiter, *, ip="198.51.100.1", account="09120000001"):
    token, retry_after = limiter.reserve_attempt(client_ip=ip, account=account)
    if token is None:
        raise AssertionError(f"test setup was throttled early; retry_after={retry_after}")
    limiter.finish_attempt(token, outcome="failure")


class LoginAttemptRateLimiterTests(unittest.TestCase):
    def test_under_account_threshold_is_allowed(self):
        clock = FakeClock()
        limiter = LoginAttemptRateLimiter(
            account_max_failures=3, ip_max_failures=20, window_seconds=60, clock=clock
        )
        fail_attempt(limiter)
        fail_attempt(limiter)

        token, _ = limiter.reserve_attempt(client_ip="198.51.100.1", account="09120000001")
        self.assertIsNotNone(token)
        limiter.finish_attempt(token, outcome="abandon")

    def test_account_is_blocked_after_limit_in_sliding_window(self):
        limiter = LoginAttemptRateLimiter(
            account_max_failures=3, ip_max_failures=20, window_seconds=60, clock=FakeClock()
        )
        for _ in range(3):
            fail_attempt(limiter)

        token, retry_after = limiter.reserve_attempt(
            client_ip="198.51.100.1", account="09120000001"
        )
        self.assertIsNone(token)
        self.assertGreaterEqual(retry_after, 1)

    def test_ip_limit_is_shared_across_account_names(self):
        limiter = LoginAttemptRateLimiter(
            account_max_failures=10, ip_max_failures=2, window_seconds=60, clock=FakeClock()
        )
        fail_attempt(limiter, ip="198.51.100.9", account="09120000001")
        fail_attempt(limiter, ip="198.51.100.9", account="09120000002")

        token, _ = limiter.reserve_attempt(
            client_ip="198.51.100.9", account="09120000003"
        )
        self.assertIsNone(token)

    def test_success_clears_account_failures_but_not_ip_failures(self):
        limiter = LoginAttemptRateLimiter(
            account_max_failures=3, ip_max_failures=20, window_seconds=60, clock=FakeClock()
        )
        fail_attempt(limiter, ip="198.51.100.7", account="09120000004")
        fail_attempt(limiter, ip="198.51.100.7", account="09120000004")

        token, _ = limiter.reserve_attempt(client_ip="198.51.100.7", account="09120000004")
        self.assertIsNotNone(token)
        limiter.finish_attempt(token, outcome="success")

        # The account gets a fresh window after successful authentication.
        for _ in range(3):
            fail_attempt(limiter, ip="198.51.100.7", account="09120000004")

        # The IP bucket remains active and is independent of the account reset.
        token, _ = limiter.reserve_attempt(client_ip="198.51.100.7", account="09120000005")
        self.assertIsNotNone(token)
        limiter.finish_attempt(token, outcome="abandon")

    def test_in_flight_reservations_make_limit_atomic_under_concurrency(self):
        limiter = LoginAttemptRateLimiter(
            account_max_failures=2, ip_max_failures=20, window_seconds=60, clock=FakeClock()
        )
        first, _ = limiter.reserve_attempt(client_ip="203.0.113.1", account="09120000006")
        second, _ = limiter.reserve_attempt(client_ip="203.0.113.1", account="09120000006")
        third, _ = limiter.reserve_attempt(client_ip="203.0.113.1", account="09120000006")

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertIsNone(third)
        limiter.finish_attempt(first, outcome="failure")
        limiter.finish_attempt(second, outcome="failure")
        next_attempt, _ = limiter.reserve_attempt(
            client_ip="203.0.113.1", account="09120000006"
        )
        self.assertIsNone(next_attempt)

    def test_window_expires_and_allows_new_attempts(self):
        clock = FakeClock()
        limiter = LoginAttemptRateLimiter(
            account_max_failures=2, ip_max_failures=20, window_seconds=60, clock=clock
        )
        fail_attempt(limiter)
        fail_attempt(limiter)
        clock.advance(61)

        token, _ = limiter.reserve_attempt(client_ip="198.51.100.1", account="09120000001")
        self.assertIsNotNone(token)
        limiter.finish_attempt(token, outcome="abandon")


class LoginRouteContractTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(client=SimpleNamespace(host="192.0.2.10"))
        self.db = FakeDb()
        self.limiter = LoginAttemptRateLimiter(
            account_max_failures=2, ip_max_failures=20, window_seconds=60
        )

    def _login(self, phone="09120000001"):
        return commercial_api.login(
            commercial_api.LoginRequest(phone=phone, password="wrong-pass-123"),
            request=self.request,
            db=self.db,
        )

    def test_actual_login_endpoint_returns_generic_401_then_429(self):
        with (
            patch.object(commercial_api, "AUTH_LOGIN_RATE_LIMITER", self.limiter),
            patch.object(commercial_api, "assert_production_billing_configuration"),
            patch.object(commercial_api, "authenticate_user", side_effect=ValueError("different internal detail")) as authenticate,
        ):
            for _ in range(2):
                with self.assertRaises(HTTPException) as ctx:
                    self._login()
                self.assertEqual(ctx.exception.status_code, 401)
                self.assertEqual(ctx.exception.detail, "invalid credentials")

            with self.assertRaises(HTTPException) as limited:
                self._login()
            self.assertEqual(limited.exception.status_code, 429)
            self.assertEqual(authenticate.call_count, 2)
            self.assertEqual(limited.exception.headers["Retry-After"], "60")

    def test_unknown_and_known_account_errors_do_not_expose_lookup_result(self):
        with (
            patch.object(commercial_api, "AUTH_LOGIN_RATE_LIMITER", self.limiter),
            patch.object(commercial_api, "assert_production_billing_configuration"),
            patch.object(commercial_api, "authenticate_user", side_effect=ValueError("invalid credentials")),
        ):
            responses = []
            for phone in ("09120000001", "09129999999"):
                with self.assertRaises(HTTPException) as ctx:
                    self._login(phone=phone)
                responses.append((ctx.exception.status_code, ctx.exception.detail))
            self.assertEqual(responses, [(401, "invalid credentials"), (401, "invalid credentials")])

    def test_password_reset_contract_and_attempt_limit_remain_intact(self):
        paths = {getattr(route, "path", "") for route in commercial_api.router.routes}
        self.assertIn("/api/v1/auth/password-reset/request", paths)
        self.assertIn("/api/v1/auth/password-reset/confirm", paths)
        self.assertEqual(MAX_ATTEMPTS, 5)
        self.assertEqual(RESET_PURPOSE, "password_reset")
        self.assertTrue(callable(enforce_sms_rate_limit))


if __name__ == "__main__":
    unittest.main(verbosity=2)
