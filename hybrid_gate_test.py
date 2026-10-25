"""Offline safety tests for Dark Horse Hybrid PostgreSQL migration.

These tests intentionally require no PostgreSQL server. They validate the
migration guard and the reference-data contract before any DB cutover.
"""

from __future__ import annotations

import json
from pathlib import Path

from audit_hybrid_integrity import SOURCES, load, records
from migration_control import is_postgres_runtime_enabled

ROOT = Path(__file__).resolve().parent


def _expected_value_pole_codes() -> list[str]:
    codes: list[str] = []
    for question in range(1, 16):
        codes.append(f"Q{question}A")
        codes.append(f"Q{question}B")
    return codes


def main() -> None:
    assert is_postgres_runtime_enabled() is False, "PostgreSQL runtime cutover must remain OFF"

    report = {"status": "PASS", "runtime_cutover": "OFF", "checks": {}}

    # List-shaped reference collections (not value_poles, which is a flat object).
    required_lists = {
        "micro_motives": ("micro_motives", "motives", "data"),
        "majors": ("majors", "data"),
        "school_branches": ("school_branches", "branches", "data"),
    }

    for name, keys in required_lists.items():
        path = SOURCES[name]
        assert path.exists(), f"Missing reference source: {path}"
        rows = records(load(path), keys)
        assert rows, f"No records detected in {path}"
        report["checks"][name] = {"records": len(rows), "path": str(path.relative_to(ROOT))}

    # Canonical value_poles_v2.json is an object keyed by Q1A..Q15B descriptions.
    # Do not lexicographically sort codes: Q10 would sort before Q2.
    value_path = SOURCES["value_poles"]
    assert value_path.exists(), f"Missing reference source: {value_path}"
    value_payload = load(value_path)
    assert isinstance(value_payload, dict), "value_poles must be a JSON object keyed by Q1A..Q15B"
    expected_poles = _expected_value_pole_codes()
    actual_poles = {str(k).strip().upper() for k in value_payload.keys()}
    assert actual_poles == set(expected_poles), (
        "value pole codes mismatch: expected exact set Q1A..Q15B, "
        f"missing={sorted(set(expected_poles) - actual_poles)}, "
        f"extra={sorted(actual_poles - set(expected_poles))}"
    )
    assert all(str(value_payload[k]).strip() for k in value_payload), (
        "value pole descriptions must be non-empty"
    )
    report["checks"]["value_poles"] = {
        "records": len(actual_poles),
        "exact_Q1A_Q15B": True,
        "path": str(value_path.relative_to(ROOT)),
    }

    trait_path = SOURCES["trait_map"]
    payload = load(trait_path)
    assert isinstance(payload, dict), "Trait map must be a JSON object"
    expected = [f"S{i:02d}" for i in range(1, 26)]
    actual = sorted(str(k) for k in payload.keys())
    assert actual == expected, f"Strategy question IDs mismatch: {actual}"
    report["checks"]["strategy_questions"] = {"count": len(actual), "exact_S01_S25": True}

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
