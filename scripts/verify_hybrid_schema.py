"""Static integrity check for the PostgreSQL Hybrid schema.

The check is intentionally connection-free: it validates the ORM contract so
it can run before PostgreSQL credentials or a database instance exist.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import Base  # noqa: E402

EXPECTED_TABLES = {
    "micro_motives",
    "value_poles",
    "trait_options",
    "majors",
    "school_branches",
    "major_micro_motives",
    "branch_micro_motives",
    "user_sessions",
    "discovery_results",
    "branch_recommendations",
    "user_feedback",
    "audit_logs",
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
}


def main() -> int:
    actual_tables = set(Base.metadata.tables)
    missing_tables = EXPECTED_TABLES - actual_tables
    unexpected_tables = actual_tables - EXPECTED_TABLES

    failures: list[str] = []
    if missing_tables:
        failures.append(f"missing tables: {sorted(missing_tables)}")
    if unexpected_tables:
        failures.append(f"unexpected tables: {sorted(unexpected_tables)}")

    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        if table_name not in Base.metadata.tables:
            continue
        actual_columns = set(Base.metadata.tables[table_name].columns.keys())
        missing_columns = expected_columns - actual_columns
        if missing_columns:
            failures.append(f"{table_name}: missing columns {sorted(missing_columns)}")

    if failures:
        print("HYBRID SCHEMA CHECK: FAIL")
        for failure in failures:
            print(" -", failure)
        return 1

    print("HYBRID SCHEMA CHECK: PASS")
    print(f"Tables: {len(actual_tables)}")
    print("PostgreSQL runtime cutover: OFF (this script does not enable it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
