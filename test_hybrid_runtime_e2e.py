from __future__ import annotations

import os
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

os.environ.setdefault("OTP_PROVIDER", "mock")
os.environ.setdefault("BILLING_PROVIDER", "mock")
os.environ.setdefault("OTP_EXPOSE_DEBUG_CODE", "true")

from billing_models import Entitlement, User  # noqa: E402
from database import SessionLocal  # noqa: E402
from main_v2 import app  # noqa: E402
from models import UserSession  # noqa: E402


def test_authenticated_journey_consumption_is_persisted_and_idempotent() -> None:
    assert SessionLocal is not None
    phone = "09" + str(uuid4().int % 1_000_000_000).zfill(9)
    password = "Hybrid-E2E-2026!"
    session_uuid = str(uuid4())

    with TestClient(app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"name": "Hybrid E2E", "phone": phone, "password": password},
        )
        assert registration.status_code == 200, registration.text
        challenge = registration.json()
        code = challenge.get("debug_code")
        assert code and len(code) == 6

        verification = client.post(
            "/api/v1/auth/register/verify",
            json={"challenge_id": challenge["challenge_id"], "code": code},
        )
        assert verification.status_code == 200, verification.text
        verified = verification.json()
        token = verified["token"]
        headers = {"Authorization": f"Bearer {token}"}

        initial = client.get("/api/v1/me/quota", headers=headers)
        assert initial.status_code == 200, initial.text
        initial_quota = initial.json()
        assert initial_quota["credits_granted"] == 1
        assert initial_quota["credits_consumed"] == 0
        assert initial_quota["credits_remaining"] == 1

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.phone == phone))
            assert user is not None
            db.add(
                UserSession(
                    user_id=user.id,
                    session_uuid=session_uuid,
                    micro_motives=[],
                    sjt_answers={},
                    conjoint_choices={},
                    is_completed=False,
                )
            )
            db.commit()

        first = client.post(
            "/api/v1/me/consume-test",
            headers=headers,
            json={"session_uuid": session_uuid},
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["consumed"] == 1
        assert first_body["already_consumed"] is False
        assert first_body["credits_granted"] == 1
        assert first_body["credits_consumed"] == 1
        assert first_body["credits_remaining"] == 0

        second = client.post(
            "/api/v1/me/consume-test",
            headers=headers,
            json={"session_uuid": session_uuid},
        )
        assert second.status_code == 200, second.text
        second_body = second.json()
        assert second_body["consumed"] == 0
        assert second_body["already_consumed"] is True
        assert second_body["credits_consumed"] == 1
        assert second_body["credits_remaining"] == 0

        persisted = client.get("/api/v1/me/quota", headers=headers)
        assert persisted.status_code == 200, persisted.text
        persisted_body = persisted.json()
        assert persisted_body == {
            "credits_granted": 1,
            "credits_consumed": 1,
            "credits_remaining": 0,
        }

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.phone == phone))
        assert user is not None
        session = db.scalar(select(UserSession).where(UserSession.session_uuid == session_uuid))
        assert session is not None and session.user_id == user.id and session.is_completed is True
        entitlement = db.scalar(
            select(Entitlement).where(
                Entitlement.user_id == user.id,
                Entitlement.source == "free",
            )
        )
        assert entitlement is not None
        assert entitlement.credits_granted == 1
        assert entitlement.credits_remaining == 0
