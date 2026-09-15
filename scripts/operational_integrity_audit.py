"""Read-only staging audit for operational orphan/duplicate/negative-credit invariants."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from database import engine

PROD_MARKERS = {"prod", "production", "live"}

CHECKS = {
    "duplicate_payment_event_keys": "SELECT COUNT(*) FROM (SELECT event_key FROM payment_events GROUP BY event_key HAVING COUNT(*) > 1) q",
    "duplicate_provider_transactions": "SELECT COUNT(*) FROM (SELECT provider, provider_transaction_id FROM payments WHERE provider_transaction_id IS NOT NULL GROUP BY provider, provider_transaction_id HAVING COUNT(*) > 1) q",
    "negative_entitlements": "SELECT COUNT(*) FROM entitlements WHERE credits_remaining < 0 OR credits_granted < 0",
    "orphan_auth_sessions": "SELECT COUNT(*) FROM auth_sessions s LEFT JOIN users u ON u.id=s.user_id WHERE u.id IS NULL",
    "orphan_orders_user": "SELECT COUNT(*) FROM orders o LEFT JOIN users u ON u.id=o.user_id WHERE u.id IS NULL",
    "orphan_orders_plan": "SELECT COUNT(*) FROM orders o LEFT JOIN premium_plans p ON p.id=o.plan_id WHERE p.id IS NULL",
    "orphan_payments_order": "SELECT COUNT(*) FROM payments p LEFT JOIN orders o ON o.id=p.order_id WHERE o.id IS NULL",
    "orphan_payment_events": "SELECT COUNT(*) FROM payment_events e LEFT JOIN payments p ON p.id=e.payment_id WHERE p.id IS NULL",
    "orphan_entitlements_plan": "SELECT COUNT(*) FROM entitlements e LEFT JOIN premium_plans p ON p.id=e.plan_id WHERE p.id IS NULL",
    "verified_payment_without_entitlement": "SELECT COUNT(*) FROM payments p LEFT JOIN entitlements e ON e.order_id=p.order_id WHERE p.status='verified' AND e.id IS NULL",
    "payment_entitlement_multiple_for_order": "SELECT COUNT(*) FROM (SELECT order_id FROM entitlements WHERE order_id IS NOT NULL GROUP BY order_id HAVING COUNT(*) > 1) q",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args()

    env = os.getenv("APP_ENV", "").strip().lower()
    if not args.confirm_staging:
        raise SystemExit("refusing to run: pass --confirm-staging")
    if env in PROD_MARKERS:
        raise SystemExit(f"refusing to run in APP_ENV={env!r}")
    if os.getenv("POSTGRES_RUNTIME_CUTOVER_APPROVED", "false").lower() == "true":
        raise SystemExit("refusing to audit while production cutover is approved")
    if engine is None:
        raise SystemExit("DATABASE_URL is required")

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = SessionLocal()
    try:
        failures: dict[str, int] = {}
        for name, query in CHECKS.items():
            value = int(db.execute(text(query)).scalar_one())
            if value:
                failures[name] = value
        if failures:
            raise SystemExit(f"OPERATIONAL_INTEGRITY=FAIL findings={failures}")
        print(f"OPERATIONAL_INTEGRITY=PASS checks={len(CHECKS)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
