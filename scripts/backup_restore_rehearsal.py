"""Staging-only PostgreSQL backup/restore rehearsal.

Creates a custom-format pg_dump, restores it into a fresh temporary database,
then checks connectivity. Production-like environments are rejected.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

PROD_MARKERS = {"prod", "production", "live"}


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--backup", default="/tmp/dark-horse-staging.dump")
    parser.add_argument("--restore-db", required=True)
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL", "").strip()
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if not args.confirm_staging:
        raise SystemExit("refusing to run: pass --confirm-staging")
    if not url:
        raise SystemExit("DATABASE_URL is required")
    if app_env in PROD_MARKERS:
        raise SystemExit(f"refusing to run in APP_ENV={app_env!r}")
    if os.getenv("POSTGRES_RUNTIME_CUTOVER_APPROVED", "false").lower() == "true":
        raise SystemExit("refusing to rehearse while production cutover is approved")

    run("pg_dump", "--format=custom", "--no-owner", "--file", args.backup, url)
    restore_url = os.getenv("RESTORE_DATABASE_URL", "").strip()
    if not restore_url:
        raise SystemExit("RESTORE_DATABASE_URL is required for restore rehearsal")
    run("pg_restore", "--clean", "--if-exists", "--no-owner", "--dbname", restore_url, args.backup)
    run(sys.executable, "-c", "from database import healthcheck; assert healthcheck() is True")
    print(f"BACKUP_RESTORE_REHEARSAL=PASS backup={args.backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
