"""Staging-only business concurrency rehearsal for credit consumption.

Creates one temporary user entitlement with N credits, concurrently attempts
consumptions with explicit per-journey session_uuid values recorded in the
0010_journey_credit_consumptions ledger (plus duplicate session_uuid replay
checks), and verifies that exactly N credits are deducted, zero duplicate
charges occur, no negative balance is possible, and no DB connection leaks.
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from billing_credit_service import consume_one_test
from billing_models import Entitlement, JourneyCreditConsumption, PremiumPlan, User
from database import SessionLocal, engine, is_configured

PROD_MARKERS = {"prod", "production", "live"}


def consume(user_id: int, session_uuid: str) -> bool:
    db = SessionLocal()
    try:
        existing = db.scalar(
            select(JourneyCreditConsumption).where(
                JourneyCreditConsumption.session_uuid == session_uuid,
            )
        )
        if existing is not None:
            return False
        entitlement = consume_one_test(db, user_id)
        db.add(
            JourneyCreditConsumption(
                user_id=user_id,
                session_uuid=session_uuid,
                entitlement_id=entitlement.id,
            )
        )
        db.commit()
        return True
    except (ValueError, IntegrityError):
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

    marker = secrets.token_hex(8)
    db = SessionLocal()
    try:
        plan = db.scalar(select(PremiumPlan).where(PremiumPlan.code == "free_1_test"))
        if plan is None:
            raise SystemExit("free_1_test plan is missing; run staging schema/seed first")
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

    session_uuids = [f"rehearsal-{marker}-{idx}" for idx in range(args.workers)]
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(consume, user_id, sid) for sid in session_uuids]
            successes = sum(1 for future in as_completed(futures) if future.result())

        # Replay already-charged session_uuids concurrently: must deduct 0 extra credits.
        with ThreadPoolExecutor(max_workers=min(args.workers, args.credits)) as pool:
            replay_futures = [pool.submit(consume, user_id, sid) for sid in session_uuids[: args.credits]]
            replay_deductions = sum(1 for future in as_completed(replay_futures) if future.result())

        check = SessionLocal()
        try:
            remaining = check.scalar(
                select(Entitlement.credits_remaining).where(
                    Entitlement.user_id == user_id,
                    Entitlement.source == "free",
                )
            )
            ledger_rows = int(
                check.scalar(
                    select(func.count()).select_from(JourneyCreditConsumption).where(
                        JourneyCreditConsumption.user_id == user_id
                    )
                )
                or 0
            )
        finally:
            check.close()

        if successes != args.credits:
            raise SystemExit(f"expected {args.credits} successful consumptions, got {successes}")
        if replay_deductions != 0:
            raise SystemExit(f"expected 0 replay deductions, got {replay_deductions}")
        if ledger_rows != args.credits:
            raise SystemExit(f"expected {args.credits} journey_credit_consumptions rows, got {ledger_rows}")
        if int(remaining or 0) != 0:
            raise SystemExit(f"expected zero remaining credits, got {remaining}")
        if engine.pool.checkedout() != 0:
            raise SystemExit(f"connection leak detected: checkedout={engine.pool.checkedout()}")

        print(
            f"BILLING_CONCURRENCY_REHEARSAL=PASS workers={args.workers} "
            f"credits={args.credits} successes={successes} "
            f"ledger_rows={ledger_rows} replay_deductions={replay_deductions} remaining={remaining}"
        )
        return 0
    finally:
        cleanup = SessionLocal()
        try:
            cleanup.execute(delete(JourneyCreditConsumption).where(JourneyCreditConsumption.user_id == user_id))
            cleanup.execute(delete(Entitlement).where(Entitlement.user_id == user_id))
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()
        finally:
            cleanup.close()


if __name__ == "__main__":
    raise SystemExit(main())
