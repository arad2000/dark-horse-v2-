import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./ci_dark_horse.db")
os.environ.setdefault("OTP_PROVIDER", "mock")
os.environ.setdefault("OTP_EXPOSE_DEBUG_CODE", "true")
os.environ.setdefault("BILLING_PROVIDER", "mock")

from fastapi.testclient import TestClient
from sqlalchemy import select

from billing_models import PremiumPlan, SavedResult
from database import Base, engine
from main_v2 import app


def setup_module():
    if engine is None:
        raise RuntimeError("test database engine was not configured")
    Base.metadata.create_all(bind=engine)
    from database import SessionLocal
    with SessionLocal() as db:
        plan = db.scalar(select(PremiumPlan).where(PremiumPlan.code == "free_1_test"))
        if plan is None:
            db.add(
                PremiumPlan(
                    code="free_1_test",
                    name_fa="رایگان — ۱ تست",
                    plan_type="credits",
                    duration_days=None,
                    credits_granted=1,
                    price_minor=0,
                    currency="IRR",
                    is_active=True,
                    features={"tests": 1, "non_expiring": True},
                )
            )
            db.commit()


def test_registration_otp_login_and_saved_result_flow():
    client = TestClient(app)
    phone = "09120000001"

    register = client.post(
        "/api/v1/auth/register",
        json={"name": "کاربر آزمون", "phone": phone, "password": "StrongPass123"},
    )
    assert register.status_code == 200, register.text
    challenge = register.json()
    assert challenge["challenge_id"]
    assert challenge["expires_in"] > 0
    assert challenge["debug_code"].isdigit()

    verify = client.post(
        "/api/v1/auth/register/verify",
        json={"challenge_id": challenge["challenge_id"], "code": challenge["debug_code"]},
    )
    assert verify.status_code == 200, verify.text
    verified = verify.json()
    token = verified["token"]
    assert verified["quota"] == 1

    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["name"] == "کاربر آزمون"

    saved = client.post(
        "/api/v1/me/save-result",
        headers=headers,
        json={"session_uuid": "session-test-001", "result_summary": {"best_major": "حقوق", "score": 91}},
    )
    assert saved.status_code == 200, saved.text
    result_id = saved.json()["result_id"]

    from database import SessionLocal
    with SessionLocal() as db:
        row = db.get(SavedResult, result_id)
        assert row is not None
        assert row.user_id > 0
        assert row.result_summary["score"] == 91


def test_duplicate_phone_is_rejected_after_verification():
    client = TestClient(app)
    phone = "09120000001"
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "تکراری", "phone": phone, "password": "StrongPass123"},
    )
    assert response.status_code == 400
