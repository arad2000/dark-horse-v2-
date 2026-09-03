from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from payment_providers import MockPaymentProvider, ZarinPalPaymentProvider


class PaymentProviderTests(unittest.TestCase):
    def test_mock_request_and_verify(self):
        provider = MockPaymentProvider()
        requested = provider.request_payment(amount_rial=2_490_000, order_public_id="ord-1", callback_url="https://example.test/cb")
        self.assertEqual(requested["code"], 100)
        self.assertEqual(requested["authority"], "MOCK-AUTH-001")
        verified = provider.verify_payment(amount_rial=2_490_000, authority=requested["authority"])
        self.assertTrue(verified["verified"])
        self.assertEqual(verified["transaction_id"], "MOCK-REF-001")

    def test_real_provider_fails_closed_without_merchant_id(self):
        provider = ZarinPalPaymentProvider(merchant_id="")
        with self.assertRaises(RuntimeError):
            provider.request_payment(amount_rial=2_490_000, order_public_id="ord-1", callback_url="https://example.test/cb")

    def test_sandbox_uses_sandbox_hosts(self):
        provider = ZarinPalPaymentProvider(merchant_id="merchant-test", sandbox=True)
        self.assertTrue(provider.sandbox)
        self.assertEqual(provider.base_url, "https://sandbox.zarinpal.com/pg/v4/payment")
        self.assertEqual(provider._startpay_url("A00001"), "https://sandbox.zarinpal.com/pg/StartPay/A00001")

    def test_live_uses_live_hosts_when_sandbox_false(self):
        provider = ZarinPalPaymentProvider(merchant_id="merchant-test", sandbox=False)
        self.assertFalse(provider.sandbox)
        self.assertEqual(provider.base_url, "https://api.zarinpal.com/pg/v4/payment")
        self.assertEqual(provider._startpay_url("A00001"), "https://www.zarinpal.com/pg/StartPay/A00001")

    @patch("payment_providers.httpx.Client")
    def test_real_provider_request_contract(self, client_cls):
        fake_response = Mock()
        fake_response.json.return_value = {"data": {"code": 100, "authority": "A00001", "request_id": "REQ1"}, "errors": []}
        fake_response.raise_for_status.return_value = None
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = fake_response

        provider = ZarinPalPaymentProvider(merchant_id="merchant-test", base_url="https://api.zarinpal.com/pg/v4/payment", sandbox=False)
        result = provider.request_payment(amount_rial=2_490_000, order_public_id="ord-1", callback_url="https://example.test/cb")
        self.assertEqual(result["authority"], "A00001")
        client.post.assert_called_once_with(
            "https://api.zarinpal.com/pg/v4/payment/request.json",
            json={
                "merchant_id": "merchant-test",
                "amount": 2_490_000,
                "callback_url": "https://example.test/cb",
                "description": "Dark Horse — ord-1",
                "metadata": {"order_public_id": "ord-1"},
            },
        )

    @patch("payment_providers.httpx.Client")
    def test_real_provider_verify_contract(self, client_cls):
        fake_response = Mock()
        fake_response.json.return_value = {"data": {"code": 100, "ref_id": 123456}, "errors": []}
        fake_response.raise_for_status.return_value = None
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = fake_response

        provider = ZarinPalPaymentProvider(merchant_id="merchant-test", base_url="https://api.zarinpal.com/pg/v4/payment", sandbox=False)
        result = provider.verify_payment(amount_rial=2_490_000, authority="A00001")
        self.assertTrue(result["verified"])
        self.assertEqual(result["transaction_id"], "123456")
        client.post.assert_called_once_with(
            "https://api.zarinpal.com/pg/v4/payment/verify.json",
            json={"merchant_id": "merchant-test", "amount": 2_490_000, "authority": "A00001"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
