"""API contract regression for the canonical session_uuid field."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from commercial_api import SaveResultRequest


def test_save_result_accepts_session_uuid():
    req = SaveResultRequest(
        session_uuid="12345678-1234-1234-1234-123456789012",
        result_summary={"session_uuid": "12345678-1234-1234-1234-123456789012"},
    )
    assert req.session_uuid


def test_save_result_rejects_legacy_session_id():
    with pytest.raises(ValidationError):
        SaveResultRequest(
            session_id="12345678-1234-1234-1234-123456789012",
            result_summary={"session_id": "12345678-1234-1234-1234-123456789012"},
        )


def test_frontend_uses_canonical_field():
    source = (Path(__file__).resolve().parent / "docs" / "auth_api_client.js").read_text(
        encoding="utf-8"
    )
    assert "body: JSON.stringify({ session_uuid: sessionId" in source
