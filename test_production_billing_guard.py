from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from production_billing_guard import assert_production_billing_configuration


class ProductionBillingGuardTests(unittest.TestCase):
    def _assert_rejected(self, env: dict[str, str], expected: str) -> None:
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(HTTPException) as ctx:
                assert_production_billing_configuration()
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn(expected, str(ctx.exception.detail))

    def test_non_production_keeps_current_dev_behavior(self):
        with patch.dict(os.environ, {"APP_ENV": "staging", "BILLING_PROVIDER": "mock", "BILLING_FREE_MODE": "true"}, clear=True):
            assert_production_billing_configuration()

    def test_production_rejects_free_mode(self):
        self._assert_rejected(
            {
                "APP_ENV": "production",
                "BILLING_FREE_MODE": "true",
                "BILLING_PROVIDER": "zarinpal",
                "ZARINPAL_MERCHANT_ID": "configured",
                "ZARINPAL_PRODUCTION_APPROVED": "true",
            },
            "BILLING_FREE_MODE",
        )

    def test_production_rejects_mock_provider(self):
        self._assert_rejected(
            {
                "APP_ENV": "production",
                "BILLING_PROVIDER": "mock",
                "ZARINPAL_MERCHANT_ID": "configured",
                "ZARINPAL_PRODUCTION_APPROVED": "true",
            },
            "BILLING_PROVIDER=zarinpal",
        )

    def test_production_requires_merchant_id(self):
        self._assert_rejected(
            {
                "APP_ENV": "production",
                "BILLING_PROVIDER": "zarinpal",
                "ZARINPAL_PRODUCTION_APPROVED": "true",
            },
            "ZARINPAL_MERCHANT_ID",
        )

    def test_production_rejects_zarinpal_sandbox(self):
        self._assert_rejected(
            {
                "APP_ENV": "production",
                "BILLING_PROVIDER": "zarinpal",
                "ZARINPAL_MERCHANT_ID": "configured",
                "ZARINPAL_SANDBOX": "true",
                "ZARINPAL_PRODUCTION_APPROVED": "true",
            },
            "sandbox",
        )

    def test_production_requires_explicit_approval(self):
        self._assert_rejected(
            {
                "APP_ENV": "production",
                "BILLING_PROVIDER": "zarinpal",
                "ZARINPAL_MERCHANT_ID": "configured",
                "ZARINPAL_SANDBOX": "false",
            },
            "production approval",
        )

    def test_production_accepts_explicit_live_zarinpal_configuration(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "BILLING_FREE_MODE": "false",
                "BILLING_PROVIDER": "zarinpal",
                "ZARINPAL_MERCHANT_ID": "configured",
                "ZARINPAL_SANDBOX": "false",
                "ZARINPAL_PRODUCTION_APPROVED": "true",
            },
            clear=True,
        ):
            assert_production_billing_configuration()


if __name__ == "__main__":
    unittest.main(verbosity=2)
