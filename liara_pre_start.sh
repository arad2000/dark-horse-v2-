#!/bin/sh
# Liara pre-start hook — schema migration gate.
#
# Runs before the application process starts, with the app's environment
# variables available, which is why DATABASE_URL is present here.
#
# Contract:
#   * fail closed by default: any problem exits non-zero so the release does
#     not serve traffic on an unknown schema
#   * never echo DATABASE_URL or any part of it
#   * normal path is exactly one database action: `alembic upgrade head`
#
# Legacy baseline (opt-in, one release only):
#   A deployment that previously booted with runtime `create_all` has tables
#   but no `alembic_version` row. Replaying 0001 against it fails with
#   DuplicateTable. Setting ALEMBIC_BASELINE_REVISION to the revision that
#   matches the existing schema stamps it once, then upgrades to head.
#   Unset (the default) keeps the gate fail-closed. The hook never guesses a
#   stamp on its own; when the schema is unstamped it reports which revision
#   the live tables already match so the operator can choose.

set -eu

fail() {
  printf 'liara_pre_start: FATAL: %s\n' "$*" >&2
  exit 1
}

cd "$(dirname "$0")" || fail "cannot change directory to the release root"
[ -f alembic.ini ] || fail "alembic.ini not found in $(pwd)"
[ -n "${DATABASE_URL:-}" ] || fail "DATABASE_URL is not set; refusing to start without a migration target"

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

# Probe the exact invocation used below: the repo's own alembic/ directory is
# importable as a namespace package, so `import alembic` can falsely pass.
"$PYTHON_BIN" -m alembic --version >/dev/null 2>&1 \
  || fail "alembic is not runnable via '$PYTHON_BIN -m alembic'"

STATE_FILE="${TMPDIR:-/tmp}/liara_pre_start_state.$$.json"
trap 'rm -f "$STATE_FILE"' EXIT

# Read-only schema probe. Prints exactly one of:
#   stamped | unstamped_empty | unstamped_tables
# For unstamped_tables it also writes a landmark snapshot to $STATE_FILE.
# Uses the same URL normalization as alembic/env.py and database.py.
db_state() {
  "$PYTHON_BIN" - "$STATE_FILE" <<'PY'
import json
import os
import sys

state_path = sys.argv[1]
url = os.environ.get("DATABASE_URL", "").strip()
if url.startswith("postgres://"):
    url = "postgresql://" + url[len("postgres://"):]
if url.startswith("postgresql://") and not url.startswith("postgresql+"):
    url = "postgresql+psycopg://" + url[len("postgresql://"):]

try:
    from sqlalchemy import create_engine, inspect
    engine = create_engine(url)
    with engine.connect() as conn:
        insp = inspect(conn)
        names = set(insp.get_table_names())
        if "alembic_version" in names:
            print("stamped")
            raise SystemExit(0)
        if not names:
            print("unstamped_empty")
            raise SystemExit(0)
        data = {"tables": sorted(names), "columns": {}, "indexes": [], "constraints": []}
        for table in sorted(names):
            data["columns"][table] = sorted(c["name"] for c in insp.get_columns(table))
            data["indexes"] += [i["name"] for i in insp.get_indexes(table) if i.get("name")]
            try:
                data["constraints"] += [
                    c["name"] for c in insp.get_unique_constraints(table) if c.get("name")
                ]
            except Exception:
                pass
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        print("unstamped_tables")
except SystemExit:
    raise
except Exception as exc:
    print("probe_failed", file=sys.stderr)
    print(type(exc).__name__, file=sys.stderr)
    raise SystemExit(3)
PY
}

# Newest revision whose schema landmarks are already present in the live DB.
suggested_baseline() {
  "$PYTHON_BIN" - "$STATE_FILE" <<'PY'
import json
import sys

state = json.load(open(sys.argv[1], encoding="utf-8"))
tables = set(state["tables"])
columns = state["columns"]
indexes = set(state["indexes"])
constraints = set(state["constraints"])


def has_col(table, column):
    return column in columns.get(table, [])


# Ordered newest -> oldest; the first satisfied landmark is the safe stamp.
LANDMARKS = (
    ("0012_referral_attribution", "uq_admin_audit_referral_code" in indexes),
    ("0011_otp_request_ip", has_col("phone_verifications", "request_ip")),
    ("0010_journey_credit_consumptions", "journey_credit_consumptions" in tables),
    ("0007_result_summary", has_col("user_sessions", "result_summary")),
    ("0006_user_session_owner", has_col("user_sessions", "user_id")),
    ("0005_phone_verification", "phone_verifications" in tables),
    ("0004_txn_unique", "uq_payment_provider_transaction" in constraints),
    ("0003_credit_based_entitlements", has_col("entitlements", "credits_remaining")),
    ("0002_auth_billing", "users" in tables),
    ("0001_initial_hybrid_schema", "micro_motives" in tables),
)
for revision, present in LANDMARKS:
    if present:
        print(revision)
        break
PY
}

STATE="$(db_state)" || fail "cannot inspect the target schema; refusing to start"
BASELINE="${ALEMBIC_BASELINE_REVISION:-}"

case "$STATE" in
  stamped)
    ;;
  unstamped_empty)
    printf 'liara_pre_start: empty database; applying the full migration chain.\n'
    ;;
  unstamped_tables)
    if [ -n "$BASELINE" ]; then
      printf 'liara_pre_start: legacy schema without alembic_version; stamping baseline %s once.\n' "$BASELINE"
      "$PYTHON_BIN" -m alembic -c alembic.ini stamp "$BASELINE" \
        || fail "alembic stamp $BASELINE failed; aborting startup"
    else
      SUGGESTED="$(suggested_baseline 2>/dev/null || true)"
      if [ -n "$SUGGESTED" ]; then
        printf 'liara_pre_start: live tables already match revision %s (derived read-only).\n' "$SUGGESTED" >&2
        fail "database has tables but no alembic_version (pre-Alembic schema); replaying 0001 would fail with DuplicateTable. Set ALEMBIC_BASELINE_REVISION=$SUGGESTED for this one release, then remove it."
      fi
      fail "database has tables but no alembic_version (pre-Alembic schema); replaying 0001 would fail with DuplicateTable. Set ALEMBIC_BASELINE_REVISION to the revision matching the live schema for one release, then remove it."
    fi
    ;;
  *)
    fail "unexpected schema probe result: $STATE"
    ;;
esac

printf 'liara_pre_start: applying alembic migrations to head...\n'
if ! "$PYTHON_BIN" -m alembic -c alembic.ini upgrade head; then
  printf 'liara_pre_start: hint: a UniqueViolation on uq_admin_audit_referral_code means\n' >&2
  printf 'liara_pre_start: duplicate referral_code ledger rows exist; resolve them, then\n' >&2
  printf 'liara_pre_start: redeploy (or deploy the parent revision first).\n' >&2
  fail "alembic upgrade head failed; aborting startup so this release does not serve traffic"
fi

printf 'liara_pre_start: migrations applied; starting application.\n'
