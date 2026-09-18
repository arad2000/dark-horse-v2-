"""Seed disposable auth/quota data for CI scale regression only."""
from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import billing_models  # noqa: F401,E402
import feedback_models  # noqa: F401,E402
from auth_service import hash_token  # noqa: E402
from billing_models import AuthSession, Entitlement, PremiumPlan, User  # noqa: E402
from database import engine  # noqa: E402
from models import Base  # noqa: E402


def main() -> None:
    if engine is None:
        raise RuntimeError("DATABASE_URL must be configured")
    user_count = int(os.getenv("SCALE_USER_COUNT", "100"))
    credits = int(os.getenv("SCALE_USER_CREDITS", "10"))
    if user_count < 1 or credits < 1:
        raise RuntimeError("SCALE_USER_COUNT and SCALE_USER_CREDITS must be >= 1")

    Base.metadata.create_all(bind=engine)
    now = datetime.now(timezone.utc)
    tokens: list[dict[str, object]] = []

    with engine.begin() as conn:
        conn.execute(
            PremiumPlan.__table__.insert().values(
                code="ci_scale_pack",
                name_fa="CI Scale Pack",
                plan_type="credits",
                duration_days=None,
                credits_granted=credits,
                price_minor=0,
                currency="IRR",
                is_active=True,
                features={"ci_only": True},
            )
        )

        plan_id = conn.execute(
            PremiumPlan.__table__.select()
            .with_only_columns(PremiumPlan.id)
            .where(PremiumPlan.code == "ci_scale_pack")
        ).scalar_one()

        user_rows = []
        session_rows = []
        entitlement_rows = []
        for i in range(user_count):
            raw_token = secrets.token_urlsafe(32)
            user_id = i + 1
            user_rows.append(
                {
                    "id": user_id,
                    "public_id": str(uuid4()),
                    "name": f"CI Scale User {i + 1}",
                    "phone": f"0911{1000000 + i:07d}",
                    "password_hash": None,
                    "role": "user",
                    "status": "active",
                }
            )
            session_rows.append(
                {
                    "user_id": user_id,
                    "token_hash": hash_token(raw_token),
                    "expires_at": now + timedelta(days=1),
                    "revoked_at": None,
                }
            )
            entitlement_rows.append(
                {
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "source": "ci",
                    "credits_granted": credits,
                    "credits_remaining": credits,
                    "starts_at": now,
                    "expires_at": None,
                    "status": "active",
                    "order_id": None,
                }
            )
            tokens.append({"user_id": user_id, "token": raw_token})

        conn.execute(User.__table__.insert(), user_rows)
        conn.execute(AuthSession.__table__.insert(), session_rows)
        conn.execute(Entitlement.__table__.insert(), entitlement_rows)

    path = Path(os.getenv("SCALE_AUTH_FILE", "/tmp/darkhorse-scale-users.json"))
    path.write_text(json.dumps(tokens, ensure_ascii=False), encoding="utf-8")
    path.chmod(0o600)
    print(f"Seeded {user_count} users with {credits} credits each")


if __name__ == "__main__":
    main()
