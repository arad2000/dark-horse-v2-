import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

import production_billing_guard as guard


class ProductionFreeOnlyLaunchTests(unittest.TestCase):
    def test_production_free_only_mode_is_allowed_without_merchant(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "BILLING_FREE_ONLY_MODE": "true",
                "BILLING_FREE_MODE": "false",
                "BILLING_PROVIDER": "",
                "ZARINPAL_MERCHANT_ID": "",
                "ZARINPAL_PRODUCTION_APPROVED": "false",
                "BILLING_SANDBOX_MODE": "false",
            },
            clear=False,
        ):
            self.assertTrue(guard.is_production_free_only_mode())
            guard.assert_production_billing_configuration()

    def test_free_only_mode_cannot_be_combined_with_unlimited_free_mode(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "BILLING_FREE_ONLY_MODE": "true",
                "BILLING_FREE_MODE": "true",
            },
            clear=False,
        ):
            with self.assertRaises(HTTPException) as ctx:
                guard.assert_production_billing_configuration()
            self.assertEqual(ctx.exception.status_code, 503)

    def test_production_without_free_only_requires_real_billing_configuration(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "BILLING_FREE_ONLY_MODE": "false",
                "BILLING_FREE_MODE": "false",
                "BILLING_PROVIDER": "mock",
                "ZARINPAL_MERCHANT_ID": "",
                "ZARINPAL_PRODUCTION_APPROVED": "false",
                "BILLING_SANDBOX_MODE": "false",
            },
            clear=False,
        ):
            with self.assertRaises(HTTPException) as ctx:
                guard.assert_production_billing_configuration()
            self.assertEqual(ctx.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main(verbosity=2)
