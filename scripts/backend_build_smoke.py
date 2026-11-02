"""Offline import/lifespan check for the deploy backend; never a readiness probe.

Use the interpreter from an isolated environment with requirements.txt installed.
No parent application configuration/credentials are passed to the child process.
No listener, request, database, migration, payment or AI call is started.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "requirements.txt",
    "constraints.txt",
    "liara.json",
    "main_v2.py",
    "dark_horse_engine_v2.py",
    "admin_router.py",
    "commercial_api.py",
    "feedback_api.py",
    "trait_map_v3.json",
    "majors_database_v2.json",
    "school_branches_v2.json",
    "value_poles_v2.json",
    "docs/data/micro_motives.json",
    "docs/data/questions_v2.json",
    "docs/data/trait_map_v3.json",
)

CHILD_CODE = r'''
import asyncio
import socket

# Fail rather than contact an external service if imports/startup ever change.
def deny_connection(*args, **kwargs):
    raise RuntimeError("Network access is forbidden in the offline backend smoke check")

socket.create_connection = deny_connection
socket.socket.connect = deny_connection
socket.socket.connect_ex = deny_connection

import database
assert not database.is_configured(), "Offline smoke must not configure a database"
from main_v2 import app
print("APP_IMPORT=PASS", flush=True)

async def check():
    async with app.router.lifespan_context(app):
        engine = app.state.engine
        assert engine is not None
        assert engine is app.state.branch_engine
        print("SCORING_REFERENCES=PASS", flush=True)
        print("SHARED_ENGINE=PASS", flush=True)
    print("LIFESPAN=PASS", flush=True)
    print("EXTERNAL_SERVICES=NOT_TESTED", flush=True)

asyncio.run(check())
'''


def child_environment() -> dict[str, str]:
    """Allowlist only interpreter necessities; do not inherit service secrets."""
    env = {name: os.environ[name] for name in ("PATH", "SYSTEMROOT") if name in os.environ}
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "APP_ENV": "local",
        "DATABASE_URL": "",
        "POSTGRES_RUNTIME_CUTOVER_APPROVED": "false",
        "DARK_HORSE_SHADOW_PERSISTENCE": "false",
        "ALLOW_RUNTIME_SCHEMA_BOOTSTRAP": "false",
    })
    return env


def main(root: Path = ROOT) -> int:
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        print("BACKEND_ARTIFACT=FAIL: missing required files: " + ", ".join(missing), file=sys.stderr)
        return 1
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-c", "import sys; sys.path.insert(0, '.');\n" + CHILD_CODE],
            cwd=root,
            env=child_environment(),
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"BACKEND_SMOKE=FAIL: {type(exc).__name__}", file=sys.stderr)
        return 1
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
