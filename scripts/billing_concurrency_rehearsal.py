"""Staging-only business concurrency rehearsal for credit consumption.

Creates one temporary user entitlement with N credits, concurrently attempts
more consumptions than available, and verifies that exactly N succeed, no
negative balance is possible, and no connection/session remains checked out.
"""
from __future__ import annotations

import argparse
import os
import secrets
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import delete, select

from billing_credit_service import consume_one_test
from billing_models import Entitlement, PremiumPlan, User
from database import SessionLocal, engine, is_configured

PROD_MARKERS = {"prod", "production", "live"}


def consume(user_id: int) -> bool:
    db = SessionLocal()
    try:
        consume_one_test(db, user_id)
        db.commit()
        return True
    except ValueError:
        db.rollback()
        return False
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--credits", type=int, default=20)
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()

    env = os.getenv("APP_ENV", "").strip().lower()
    if not args.confirm_staging:
        raise SystemExit("refusing to run: pass --confirm-staging")
    if env in PROD_MARKERS:
        raise SystemExit(f"refusing to run in APP_ENV={env!r}")
    if not is_configured() or engine is None or SessionLocal is None:
        raise SystemExit("DATABASE_URL is required")
    if args.credits < 1 or args.workers < args.credits:
        raise SystemExit("credits/workers are invalid")

    db = SessionLocal()
    user = None
    try:
        plan = db.scalar(select(PremiumPlan).where(PremiumPlan.code == "free_1_test"))
        if plan is None:
            raise SystemExit("free_1_test plan is missing; run staging schema/seed first")
        marker = secrets.token_hex(8)
        user = User(
            public_id=f"concurrency-{marker}",
            name="Concurrency Rehearsal",
            phone="09" + str(int(marker[:8], 16) % 10_000_000_00).zfill(9),
            password_hash=None,
            role="user",
            status="active",
        )
        db.add(user)
        db.flush()
        entitlement = Entitlement(
            user_id=user.id,
            plan_id=plan.id,
            source="free",
            credits_granted=args.credits,
            credits_remaining=args.credits,
            starts_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            expires_at=None,
            status="active",
        )
        db.add(entitlement)
        db.commit()
        user_id = int(user.id)
    finally:
        db.close()

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(consume, user_id) for _ in range(args.workers)]
            successes = sum(1 for future in as_completed(futures) if future.result())

        check = SessionLocal()
        try:
            remaining = check.scalar(
                select(Entitlement.credits_remaining).where(
                    Entitlement.user_id == user_id,
                    Entitlement.source == "free",
                )
            )
        finally:
            check.close()

        if successes != args.credits:
            raise SystemExit(f"expected {args.credits} successful consumptions, got {successes}")
        if int(remaining or 0) != 0:
            raise SystemExit(f"expected zero remaining credits, got {remaining}")
        if engine.pool.checkedout() != 0:
            raise SystemExit(f"connection leak detected: checkedout={engine.pool.checkedout()}")

        print(
            f"BILLING_CONCURRENCY_REHEARSAL=PASS workers={args.workers} "
            f"credits={args.credits} successes={successes} remaining={remaining}"
        )
        return 0
    finally:
        cleanup = SessionLocal()
        try:
            cleanup.execute(delete(Entitlement).where(Entitlement.user_id == user_id))
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()
        finally:
            cleanup.close()


if __name__ == "__main__":
    raise SystemExit(main())
