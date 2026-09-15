"""Staging-only PostgreSQL backup/restore rehearsal.

Creates a custom-format pg_dump, restores it into a separate staging database,
then checks the restored target directly. Production-like environments are
rejected.
"""
from __future__ import annotations

import argparse
import os
import subprocess

PROD_MARKERS = {"prod", "production", "live"}


def run(*args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, check=True, env=env)


def libpq_url(url: str) -> str:
    """Convert SQLAlchemy PostgreSQL URLs to libpq-compatible URLs."""
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url[len("postgresql+psycopg://") :]
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql://" + url[len("postgresql+psycopg2://") :]
    return url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--backup", default="/tmp/dark-horse-staging.dump")
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL", "").strip()
    restore_url = os.getenv("RESTORE_DATABASE_URL", "").strip()
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if not args.confirm_staging:
        raise SystemExit("refusing to run: pass --confirm-staging")
    if not url:
        raise SystemExit("DATABASE_URL is required")
    if not restore_url:
        raise SystemExit("RESTORE_DATABASE_URL is required for restore rehearsal")
    if app_env in PROD_MARKERS:
        raise SystemExit(f"refusing to run in APP_ENV={app_env!r}")
    if os.getenv("POSTGRES_RUNTIME_CUTOVER_APPROVED", "false").lower() == "true":
        raise SystemExit("refusing to rehearse while production cutover is approved")
    if restore_url == url:
        raise SystemExit("restore target must be separate from source database")

    run(
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--file",
        args.backup,
        libpq_url(url),
    )
    run(
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--dbname",
        libpq_url(restore_url),
        args.backup,
    )

    health_env = dict(os.environ)
    health_env["DATABASE_URL"] = restore_url
    run("python", "-c", "from database import healthcheck; assert healthcheck() is True", env=health_env)
    print(f"BACKUP_RESTORE_REHEARSAL=PASS backup={args.backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
