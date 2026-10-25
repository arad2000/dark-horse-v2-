from __future__ import annotations

import os
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

    def test_sandbox_configuration_uses_sandbox_api_and_gateway(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = ZarinPalPaymentProvider(merchant_id="merchant-test", sandbox=True)
        self.assertTrue(provider.sandbox)
        self.assertEqual(provider.base_url, "https://sandbox.zarinpal.com/pg/v4/payment")
        self.assertEqual(provider.gateway_base_url, "https://sandbox.zarinpal.com/pg/StartPay")

    @patch("payment_providers.httpx.Client")
    def test_sandbox_request_contract(self, client_cls):
        fake_response = Mock()
        fake_response.json.return_value = {"data": {"code": 100, "authority": "A-SANDBOX", "request_id": "REQ-SB"}, "errors": []}
        fake_response.raise_for_status.return_value = None
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = fake_response

        with patch.dict(os.environ, {}, clear=True):
            provider = ZarinPalPaymentProvider(merchant_id="merchant-test", sandbox=True)
            result = provider.request_payment(
                amount_rial=2_490_000,
                order_public_id="ord-1",
                callback_url="https://example.test/cb",
            )

        self.assertEqual(result["authority"], "A-SANDBOX")
        self.assertEqual(result["payment_url"], "https://sandbox.zarinpal.com/pg/StartPay/A-SANDBOX")
        client.post.assert_called_once_with(
            "https://sandbox.zarinpal.com/pg/v4/payment/request.json",
            json={
                "merchant_id": "merchant-test",
                "amount": 2_490_000,
                "callback_url": "https://example.test/cb",
                "description": "Dark Horse — ord-1",
                "metadata": {"order_public_id": "ord-1"},
            },
        )

    @patch("payment_providers.httpx.Client")
    def test_sandbox_verify_contract(self, client_cls):
        fake_response = Mock()
        fake_response.json.return_value = {"data": {"code": 100, "ref_id": 654321}, "errors": []}
        fake_response.raise_for_status.return_value = None
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = fake_response

        with patch.dict(os.environ, {}, clear=True):
            provider = ZarinPalPaymentProvider(merchant_id="merchant-test", sandbox=True)
            result = provider.verify_payment(amount_rial=2_490_000, authority="A-SANDBOX")

        self.assertTrue(result["verified"])
        self.assertEqual(result["transaction_id"], "654321")
        client.post.assert_called_once_with(
            "https://sandbox.zarinpal.com/pg/v4/payment/verify.json",
            json={"merchant_id": "merchant-test", "amount": 2_490_000, "authority": "A-SANDBOX"},
        )

    @patch("payment_providers.httpx.Client")
    def test_real_provider_request_contract(self, client_cls):
        fake_response = Mock()
        fake_response.json.return_value = {"data": {"code": 100, "authority": "A00001", "request_id": "REQ1"}, "errors": []}
        fake_response.raise_for_status.return_value = None
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = fake_response

        provider = ZarinPalPaymentProvider(merchant_id="merchant-test", base_url="https://api.zarinpal.com/pg/v4/payment")
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

        provider = ZarinPalPaymentProvider(merchant_id="merchant-test", base_url="https://api.zarinpal.com/pg/v4/payment")
        result = provider.verify_payment(amount_rial=2_490_000, authority="A00001")
        self.assertTrue(result["verified"])
        self.assertEqual(result["transaction_id"], "123456")
        client.post.assert_called_once_with(
            "https://api.zarinpal.com/pg/v4/payment/verify.json",
            json={"merchant_id": "merchant-test", "amount": 2_490_000, "authority": "A00001"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
