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


def revision_ids(output: str) -> set[str]:
    return set(re.findall(r"\b[0-9a-f]{4,40}\b", output, flags=re.IGNORECASE))


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

    head_output = run_capture("alembic", "heads")
    head_ids = revision_ids(head_output)
    if len(head_ids) != 1:
        raise SystemExit(f"expected exactly one Alembic head, got {sorted(head_ids)}")
    head = next(iter(head_ids))

    run_capture("alembic", "current")
    run_capture("alembic", "upgrade", "head")
    current = run_capture("alembic", "current")
    if head not in revision_ids(current) or "(head)" not in current:
        raise SystemExit(f"after upgrade, current revision is not head={head!r}: {current.strip()}")

    run_capture("alembic", "downgrade", "-1")
    run_capture("alembic", "current")
    run_capture("alembic", "upgrade", "head")
    final = run_capture("alembic", "current")
    if head not in revision_ids(final) or "(head)" not in final:
        raise SystemExit(f"after re-upgrade, current revision is not head={head!r}: {final.strip()}")

    print(f"MIGRATION_REHEARSAL=PASS head={head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
