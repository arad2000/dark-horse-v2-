"""Staging-only DB pool/concurrency rehearsal.

Exercises concurrent short-lived connections against PostgreSQL and verifies
that the configured pool can serve them without leaking checked-out sessions.
"""
from __future__ import annotations

import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import text

import database

PROD_MARKERS = {"prod", "production", "live"}


def one_query(_: int) -> int:
    if database.engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    with database.engine.connect() as conn:
        return int(conn.execute(text("SELECT 1")).scalar_one())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()

    env = os.getenv("APP_ENV", "").strip().lower()
    if not args.confirm_staging:
        raise SystemExit("refusing to run: pass --confirm-staging")
    if env in PROD_MARKERS:
        raise SystemExit(f"refusing to run in APP_ENV={env!r}")
    if not database.is_configured():
        raise SystemExit("DATABASE_URL is required")
    if args.workers < 1 or args.requests < args.workers:
        raise SystemExit("workers and requests are invalid")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one_query, i) for i in range(args.requests)]
        values = [future.result() for future in as_completed(futures)]

    if values != [1] * args.requests:
        raise SystemExit("unexpected SELECT 1 results")

    pool_obj = database.engine.pool
    checked_out = pool_obj.checkedout() if hasattr(pool_obj, "checkedout") else 0
    if checked_out != 0:
        raise SystemExit(f"connection leak detected: checkedout={checked_out}")

    print(
        f"DB_POOL_CONCURRENCY_REHEARSAL=PASS workers={args.workers} "
        f"requests={args.requests} checkedout={checked_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
