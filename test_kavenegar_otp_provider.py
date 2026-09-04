import pytest
from unittest.mock import Mock, patch

import httpx

from otp_service import _kavenegar_receptor, send_code


def _response(status_code=200, return_status=200):
    response = Mock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = {"return": {"status": return_status, "message": "OK"}}
    return response


def test_kavenegar_receptor_normalizes_iranian_mobile():
    assert _kavenegar_receptor("09121234567") == "+989121234567"


def test_kavenegar_lookup_provider_sends_without_exposing_code(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "kavenegar")
    monkeypatch.setenv("OTP_SECRET", "staging-test-secret")
    monkeypatch.setenv("KAVENEGAR_API_KEY", "test-api-key")
    monkeypatch.setenv("KAVENEGAR_OTP_TEMPLATE", "darkhorse_otp")

    response = _response()
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.post.return_value = response

    with patch("otp_service.httpx.Client", return_value=client):
        send_code("09121234567", "123456")

    client.post.assert_called_once()
    _, kwargs = client.post.call_args
    assert kwargs["params"] == {
        "receptor": "+989121234567",
        "token": "123456",
        "template": "darkhorse_otp",
    }


def test_kavenegar_sms_provider_requires_sender_without_template(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "kavenegar")
    monkeypatch.setenv("OTP_SECRET", "staging-test-secret")
    monkeypatch.setenv("KAVENEGAR_API_KEY", "test-api-key")
    monkeypatch.delenv("KAVENEGAR_OTP_TEMPLATE", raising=False)
    monkeypatch.delenv("KAVENEGAR_SENDER", raising=False)

    with pytest.raises(RuntimeError, match="KAVENEGAR_SENDER"):
        send_code("09121234567", "123456")


def test_kavenegar_rejects_provider_error(monkeypatch):
    monkeypatch.setenv("OTP_PROVIDER", "kavenegar")
    monkeypatch.setenv("OTP_SECRET", "staging-test-secret")
    monkeypatch.setenv("KAVENEGAR_API_KEY", "test-api-key")
    monkeypatch.setenv("KAVENEGAR_OTP_TEMPLATE", "darkhorse_otp")

    response = _response(status_code=200, return_status=400)
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.post.return_value = response

    with patch("otp_service.httpx.Client", return_value=client):
        with pytest.raises(RuntimeError, match="Kavenegar rejected the SMS"):
            send_code("09121234567", "123456")
