"""Offline login guard tests: no provider, network, or database connections."""
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from ai_rate_limit import SlidingWindowRateLimiter
import commercial_api
from database import get_db
import login_rate_limit as guard


class LoginRateLimitTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        clock = lambda: self.now
        self.ip = SlidingWindowRateLimiter(limit=3, window_seconds=60, clock=clock)
        self.account = SlidingWindowRateLimiter(limit=2, window_seconds=60, clock=clock)
        self.patches = [patch.object(guard, 'LOGIN_IP_LIMITER', self.ip),
                        patch.object(guard, 'LOGIN_ACCOUNT_LIMITER', self.account)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def request(self, host='192.0.2.1', forwarded='203.0.113.1'):
        return SimpleNamespace(client=SimpleNamespace(host=host), headers={'x-forwarded-for': forwarded})

    def test_account_limit_applies_across_addresses_and_whitespace(self):
        guard.enforce_login_rate_limit(self.request('a'), '09120000001')
        guard.enforce_login_rate_limit(self.request('b'), ' 0912 0000001 ')
        with self.assertRaises(HTTPException) as caught:
            guard.enforce_login_rate_limit(self.request('c'), '09120000001')
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.headers['Retry-After'], '60')
        self.assertNotIn('0912', str(self.account._events))

    def test_ip_limit_applies_across_accounts_and_ignores_forwarded_header(self):
        for i in range(3):
            guard.enforce_login_rate_limit(self.request(forwarded=str(i)), f'0912000000{i}')
        with self.assertRaises(HTTPException):
            guard.enforce_login_rate_limit(self.request(forwarded='another'), '09120000009')

    def test_window_recovers_without_permanent_lockout(self):
        for _ in range(2):
            guard.enforce_login_rate_limit(self.request(), '09120000001')
        self.now += 60.001
        guard.enforce_login_rate_limit(self.request(), '09120000001')

    def test_missing_peer_and_blank_phone_do_not_raise_internal_error(self):
        guard.enforce_login_rate_limit(SimpleNamespace(client=None), '   ')

    def test_http_429_prevents_password_verification_and_session_creation(self):
        # Mount only the router: never run the production app lifespan.
        app = FastAPI()
        app.include_router(commercial_api.router)
        app.dependency_overrides[get_db] = lambda: SimpleNamespace(rollback=lambda: None)
        with TestClient(app) as client, patch.object(commercial_api, 'assert_production_billing_configuration'), patch.object(
            commercial_api, 'authenticate_user', side_effect=ValueError('invalid credentials')
        ) as authenticate:
            body = {'phone': '09120000001', 'password': 'invalid-password'}
            self.assertEqual(client.post('/api/v1/auth/login', json=body).status_code, 401)
            self.assertEqual(client.post('/api/v1/auth/login', json=body).status_code, 401)
            response = client.post('/api/v1/auth/login', json=body)
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers['retry-after'], '60')
            self.assertEqual(authenticate.call_count, 2)
            self.assertNotIn(body['phone'], response.text)

    def test_successful_requests_are_also_throttled(self):
        user = SimpleNamespace(id=8, public_id='user-8', name='User', phone='09120000001', role='user', status='active')
        db = SimpleNamespace(commit=lambda: None)
        app = FastAPI()
        app.include_router(commercial_api.router)
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client, patch.object(commercial_api, 'assert_production_billing_configuration'), patch.object(
            commercial_api, 'authenticate_user', return_value=(user, 'test-token')
        ) as authenticate, patch.object(commercial_api, 'ensure_free_entitlement'), patch.object(
            commercial_api, '_quota_details', return_value={'credits_remaining': 1, 'credits_consumed': 0, 'credits_granted': 1}
        ):
            body = {'phone': user.phone, 'password': 'valid-password'}
            self.assertEqual(client.post('/api/v1/auth/login', json=body).status_code, 200)
            self.assertEqual(client.post('/api/v1/auth/login', json=body).status_code, 200)
            self.assertEqual(client.post('/api/v1/auth/login', json=body).status_code, 429)
            self.assertEqual(authenticate.call_count, 2)
