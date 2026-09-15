"""Staging-only migration rehearsal for the Hybrid rollout.

The command refuses to run against production-like environments and never
changes the application cutover gate. It performs a full upgrade -> downgrade
-> upgrade cycle and verifies the database ends exactly at the Alembic head.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess


PROD_MARKERS = {"prod", "production", "live"}


def env_name() -> str:
    return os.getenv("APP_ENV", "").strip().lower()


def run_capture(*args: str) -> str:
    completed = subprocess.run(args, check=True, text=True, capture_output=True)
    return (completed.stdout or "") + (completed.stderr or "")


def head_revision(output: str) -> str:
    match = re.search(r"^Rev:\s*([0-9A-Za-z_-]+)", output, flags=re.MULTILINE)
    if not match:
        raise SystemExit(f"could not parse Alembic head from: {output.strip()!r}")
    return match.group(1)


def current_is_head(output: str, head: str) -> bool:
    return bool(re.search(rf"(?:^|\s){re.escape(head)}(?:\s|$)", output) and "(head)" in output)


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

    head = head_revision(run_capture("alembic", "heads", "--verbose"))
    run_capture("alembic", "current")
    run_capture("alembic", "upgrade", "head")
    current = run_capture("alembic", "current")
    if not current_is_head(current, head):
        raise SystemExit(f"after upgrade, current revision is not head={head!r}: {current.strip()}")

    run_capture("alembic", "downgrade", "-1")
    run_capture("alembic", "current")
    run_capture("alembic", "upgrade", "head")
    final = run_capture("alembic", "current")
    if not current_is_head(final, head):
        raise SystemExit(f"after re-upgrade, current revision is not head={head!r}: {final.strip()}")

    print(f"MIGRATION_REHEARSAL=PASS head={head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
