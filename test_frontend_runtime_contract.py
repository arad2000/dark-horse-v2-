from pathlib import Path


UI = Path("docs/commercial_ui.js").read_text(encoding="utf-8")
AUTH = Path("docs/auth_api_client.js").read_text(encoding="utf-8")


def test_escape_html_is_real_escaping():
    assert ".replace(/&/g,'&amp;')" in UI
    assert ".replace(/</g,'&lt;')" in UI
    assert ".replace(/>/g,'&gt;')" in UI
    assert ".replace(/\\\"/g,'&quot;')" in UI
    assert ".replace(/'/g,'&#39;')" in UI


def test_admin_feedback_uses_new_five_dimension_contract():
    assert "Array.isArray(rowsResp.feedback)" in UI
    for field in ("major_fit", "motive_accuracy", "strategy_fit", "value_fit", "nps"):
        assert field in UI


def test_auth_client_matches_runtime_endpoints():
    assert "/api/v1/auth/register/verify" in AUTH
    assert "/api/v1/me/save-result" in AUTH
