"""Static integrity check for the PostgreSQL Hybrid schema."""
from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import Base  # noqa: E402
import billing_models  # noqa: F401,E402

EXPECTED_TABLES = {
    "micro_motives", "value_poles", "trait_options", "majors", "school_branches",
    "major_micro_motives", "branch_micro_motives", "user_sessions", "discovery_results",
    "branch_recommendations", "user_feedback", "audit_logs", "users", "auth_sessions",
    "premium_plans", "orders", "payments", "entitlements", "payment_events", "admin_audit_logs",
}
EXPECTED_COLUMNS = {
    "micro_motives": {"id", "code", "description_fa", "category", "intensity_level"},
    "value_poles": {"id", "pole_code", "question_num", "option_letter", "description_fa", "opposite_pole_id"},
    "trait_options": {"id", "question_code", "option_index", "traits", "description_fa"},
    "majors": {"id", "name", "group", "strategy_weights", "value_weights", "archetype"},
    "school_branches": {"id", "name", "group", "strategy_weights", "value_weights"},
    "user_sessions": {"id", "session_uuid", "micro_motives", "sjt_answers", "conjoint_choices"},
    "discovery_results": {"id", "session_id", "major_id", "m_score", "s_score", "v_score", "total_score"},
    "branch_recommendations": {"id", "session_id", "branch_id", "m_score", "s_score", "v_score", "average_score"},
    "user_feedback": {"id", "session_id", "satisfaction_score", "accuracy_rating"},
    "audit_logs": {"id", "table_name", "record_id", "action", "old_values", "new_values"},
    "users": {"id", "public_id", "name", "phone", "password_hash", "role", "status"},
    "auth_sessions": {"id", "user_id", "token_hash", "expires_at", "revoked_at"},
    "premium_plans": {"id", "code", "name_fa", "duration_days", "price_minor", "currency", "is_active", "features"},
    "orders": {"id", "public_id", "user_id", "plan_id", "amount_minor", "currency", "status"},
    "payments": {"id", "order_id", "provider", "amount_minor", "currency", "status", "provider_authority"},
    "entitlements": {"id", "user_id", "plan_id", "source", "starts_at", "expires_at", "status", "order_id"},
    "payment_events": {"id", "payment_id", "event_type", "event_key", "payload"},
    "admin_audit_logs": {"id", "admin_user_id", "action", "target_type", "target_id", "metadata", "ip_address"},
}

def main() -> int:
    actual_tables = set(Base.metadata.tables)
    missing_tables = EXPECTED_TABLES - actual_tables
    unexpected_tables = actual_tables - EXPECTED_TABLES
    failures: list[str] = []
    if missing_tables: failures.append(f"missing tables: {sorted(missing_tables)}")
    if unexpected_tables: failures.append(f"unexpected tables: {sorted(unexpected_tables)}")
    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        if table_name not in Base.metadata.tables: continue
        actual_columns = set(Base.metadata.tables[table_name].columns.keys())
        missing_columns = expected_columns - actual_columns
        if missing_columns: failures.append(f"{table_name}: missing columns {sorted(missing_columns)}")
    if failures:
        print("HYBRID SCHEMA CHECK: FAIL")
        for failure in failures: print(" -", failure)
        return 1
    print("HYBRID SCHEMA CHECK: PASS")
    print(f"Tables: {len(actual_tables)}")
    print("PostgreSQL runtime cutover: OFF (this script does not enable it)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
