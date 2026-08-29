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


def main() -> None:
    assert is_postgres_runtime_enabled() is False, "PostgreSQL runtime cutover must remain OFF"

    report = {"status": "PASS", "runtime_cutover": "OFF", "checks": {}}

    required = {
        "micro_motives": ("micro_motives", "motives", "data"),
        "majors": ("majors", "data"),
        "school_branches": ("school_branches", "branches", "data"),
        "value_poles": ("value_poles", "poles", "data"),
    }

    for name, keys in required.items():
        path = SOURCES[name]
        assert path.exists(), f"Missing reference source: {path}"
        rows = records(load(path), keys)
        assert rows, f"No records detected in {path}"
        report["checks"][name] = {"records": len(rows), "path": str(path.relative_to(ROOT))}

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
