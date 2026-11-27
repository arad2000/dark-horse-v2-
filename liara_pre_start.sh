#!/bin/sh
# Liara pre-start hook — schema migration gate.
#
# Runs before the application process starts. Liara executes this file before
# the `args` command in liara.json (uvicorn), with the app's environment
# variables available, which is why DATABASE_URL is present here.
#
# Contract:
#   * exactly one database action: `alembic upgrade head`
#   * fail closed: any problem exits non-zero so the release does not start
#   * never echo DATABASE_URL or any part of it
#   * no dependency on the ORM, the FastAPI app, or any project module
#
# Out of scope by design: frontend, database credentials, public database
# exposure, data backfills, and seed scripts. Those are not touched here.

set -eu

fail() {
  printf 'liara_pre_start: FATAL: %s\n' "$*" >&2
  exit 1
}

# Liara may invoke this hook from the app root or via an absolute path.
# Migrations must run against the release tree that is about to serve traffic.
cd "$(dirname "$0")" || fail "cannot change directory to the release root"
[ -f alembic.ini ] || fail "alembic.ini not found in $(pwd)"

# Without a target there is nothing to migrate against; refuse to start rather
# than boot an application whose schema state is unknown.
[ -n "${DATABASE_URL:-}" ] || fail "DATABASE_URL is not set; refusing to start without a migration target"

# Resolve the interpreter the same way the platform does (python, then python3).
PYTHON_BIN="${PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
  else
    fail "no python interpreter found on PATH"
  fi
fi

# Probe the exact invocation used below, not just `import alembic`: the local
# `alembic/` migrations directory is importable as a namespace package when the
# real library is missing, so an import check can give a false pass.
if ! "$PYTHON_BIN" -m alembic --version >/dev/null 2>&1; then
  fail "alembic is not runnable via '$PYTHON_BIN -m alembic'"
fi

printf 'liara_pre_start: applying alembic migrations to head...\n'

# `-m alembic` keeps the interpreter and the alembic package in the same
# environment. `-c alembic.ini` pins the config file explicitly.
if ! "$PYTHON_BIN" -m alembic -c alembic.ini upgrade head; then
  fail "alembic upgrade head failed; aborting startup so this release does not serve traffic"
fi

printf 'liara_pre_start: migrations applied; starting application.\n'
