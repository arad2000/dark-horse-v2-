"""Offline-safe integrity audit for the Hybrid migration.

The audit is intentionally read-only: it never enables PostgreSQL runtime use and
never modifies reference JSON. It validates that the seed source files are
present, structurally usable, and internally consistent before staging import.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

SOURCES = {
    "micro_motives": ROOT / "docs" / "data" / "micro_motives.json",
    "majors": ROOT / "majors_database_v2.json",
    "school_branches": ROOT / "school_branches_v2.json",
    "value_poles": ROOT / "value_poles_v2.json",
    "trait_map": ROOT / "docs" / "data" / "trait_map_v3.json",
}


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def main() -> None:
    report: dict[str, Any] = {"status": "PASS", "runtime_switch": "OFF", "files": {}, "errors": []}

    for name, path in SOURCES.items():
        if not path.exists():
            report["status"] = "FAIL"
            report["errors"].append(f"missing:{path}")
            continue
        try:
            payload = load(path)
            report["files"][name] = {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "json_type": type(payload).__name__,
            }
        except Exception as exc:
            report["status"] = "FAIL"
            report["errors"].append(f"invalid_json:{path}:{exc}")

    if report["status"] == "PASS":
        motive_rows = records(load(SOURCES["micro_motives"]), ("micro_motives", "motives", "data"))
        major_rows = records(load(SOURCES["majors"]), ("majors", "data"))
        branch_rows = records(load(SOURCES["school_branches"]), ("school_branches", "branches", "data"))
        value_rows = records(load(SOURCES["value_poles"]), ("value_poles", "poles", "data"))
        trait_payload = load(SOURCES["trait_map"])

        motive_codes = [r.get("code") for r in motive_rows]
        major_ids = [r.get("id") or r.get("major_id") for r in major_rows]
        branch_ids = [r.get("id") or r.get("branch_id") for r in branch_rows]
        pole_codes = [r.get("pole_code") or r.get("code") for r in value_rows]

        def duplicate(values: list[Any]) -> list[Any]:
            seen = set()
            dup = []
            for v in values:
                if v in seen and v not in dup:
                    dup.append(v)
                seen.add(v)
            return dup

        report["counts"] = {
            "micro_motives": len(motive_rows),
            "majors": len(major_rows),
            "school_branches": len(branch_rows),
            "value_poles": len(value_rows),
            "trait_map_questions": len(trait_payload) if isinstance(trait_payload, dict) else 0,
        }
        report["duplicates"] = {
            "motive_codes": duplicate(motive_codes),
            "major_ids": duplicate(major_ids),
            "branch_ids": duplicate(branch_ids),
            "pole_codes": duplicate(pole_codes),
        }
        if any(report["duplicates"].values()):
            report["status"] = "FAIL"
            report["errors"].append("duplicate_natural_keys")

        if isinstance(trait_payload, dict):
            qcodes = sorted(str(k) for k in trait_payload.keys())
            expected = [f"S{i:02d}" for i in range(1, 26)]
            report["strategy_questions"] = {
                "exact_S01_S25": qcodes == expected,
                "ids": qcodes,
            }
            if qcodes != expected:
                report["status"] = "FAIL"
                report["errors"].append("strategy_question_ids_not_exact_S01_S25")
        else:
            report["status"] = "FAIL"
            report["errors"].append("trait_map_not_object")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
