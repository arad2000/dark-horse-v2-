"""Staging-only migration rehearsal for the Hybrid rollout.

The command refuses to run against production-like environments and never
changes the application cutover gate. It performs an upgrade -> consistency
check -> downgrade -> upgrade cycle on an explicit staging DB.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys


PROD_MARKERS = {"prod", "production", "live"}


def env_name() -> str:
    return os.getenv("APP_ENV", "").strip().lower()


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not args.confirm_staging:
        raise SystemExit("refusing to run: pass --confirm-staging")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    if env_name() in PROD_MARKERS:
        raise SystemExit(f"refusing to run in APP_ENV={env_name()!r}")
    if os.getenv("POSTGRES_RUNTIME_CUTOVER_APPROVED", "false").lower() == "true":
        raise SystemExit("refusing to rehearse while production cutover is approved")

    run(sys.executable, "-m", "alembic", "current")
    run(sys.executable, "-m", "alembic", "upgrade", "head")
    run(sys.executable, "-m", "alembic", "check")
    run(sys.executable, "-m", "alembic", "downgrade", "-1")
    run(sys.executable, "-m", "alembic", "upgrade", "head")
    run(sys.executable, "-m", "alembic", "check")
    run(sys.executable, "-m", "alembic", "current")
    print("MIGRATION_REHEARSAL=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
