"""Strict offline contract audit for Dark Horse Hybrid migration.

Read-only. This script never connects to PostgreSQL and never changes runtime state.
It validates the exact reference-data invariants required before a staging seed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

FILES = {
    "micro_motives": ROOT / "docs" / "data" / "micro_motives.json",
    "majors": ROOT / "majors_database_v2.json",
    "school_branches": ROOT / "school_branches_v2.json",
    "value_poles": ROOT / "value_poles_v2.json",
    "trait_map": ROOT / "docs" / "data" / "trait_map_v3.json",
    "questions": ROOT / "docs" / "data" / "questions_v2.json",
}


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def rows(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    raise ValueError("Unsupported JSON collection shape")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dup(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    result: list[Any] = []
    for value in values:
        if value in seen and value not in result:
            result.append(value)
        seen.add(value)
    return result


def main() -> None:
    report: dict[str, Any] = {"status": "PASS", "runtime_cutover": "OFF", "errors": [], "files": {}}

    payloads: dict[str, Any] = {}
    for name, path in FILES.items():
        if not path.exists():
            report["status"] = "FAIL"
            report["errors"].append(f"missing:{path}")
            continue
        try:
            payloads[name] = load(path)
            report["files"][name] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
        except Exception as exc:
            report["status"] = "FAIL"
            report["errors"].append(f"invalid_json:{name}:{exc}")

    if report["status"] != "PASS":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    motives = rows(payloads["micro_motives"], ("micro_motives", "motives", "data"))
    majors = rows(payloads["majors"], ("majors", "data"))
    branches = rows(payloads["school_branches"], ("school_branches", "branches", "data"))
    values = rows(payloads["value_poles"], ("value_poles", "poles", "data"))

    motive_codes = [str(x.get("code") or "").strip() for x in motives]
    major_ids = [x.get("id") if x.get("id") is not None else x.get("major_id") for x in majors]
    branch_names = [str(x.get("name") or x.get("branch_name") or "").strip() for x in branches]
    value_codes = [str(x.get("pole_code") or x.get("code") or "").strip() for x in values]

    report["counts"] = {
        "micro_motives": len(motives),
        "majors": len(majors),
        "school_branches": len(branches),
        "value_poles": len(values),
    }

    # Hard invariants already established for the current Dark Horse reference set.
    expected_counts = {"micro_motives": 1099, "majors": 160, "value_poles": 30}
    for name, expected in expected_counts.items():
        actual = report["counts"][name]
        if actual != expected:
            report["status"] = "FAIL"
            report["errors"].append(f"count_mismatch:{name}:expected={expected}:actual={actual}")

    if dup(motive_codes):
        report["status"] = "FAIL"
        report["errors"].append(f"duplicate_motive_codes:{dup(motive_codes)}")
    if dup(major_ids):
        report["status"] = "FAIL"
        report["errors"].append(f"duplicate_major_ids:{dup(major_ids)}")
    if dup(branch_names):
        report["status"] = "FAIL"
        report["errors"].append(f"duplicate_branch_names:{dup(branch_names)}")
    if dup(value_codes):
        report["status"] = "FAIL"
        report["errors"].append(f"duplicate_value_codes:{dup(value_codes)}")

    if sorted(int(x) for x in major_ids if x is not None) != list(range(1, 161)):
        report["status"] = "FAIL"
        report["errors"].append("major_ids_not_exact_1_to_160")

    expected_questions = [f"S{i:02d}" for i in range(1, 26)]
    trait_payload = payloads["trait_map"]
    if not isinstance(trait_payload, dict):
        report["status"] = "FAIL"
        report["errors"].append("trait_map_not_object")
    else:
        actual_questions = sorted(str(k) for k in trait_payload.keys())
        report["strategy_questions"] = {
            "count": len(actual_questions),
            "exact_S01_S25": actual_questions == expected_questions,
        }
        if actual_questions != expected_questions:
            report["status"] = "FAIL"
            report["errors"].append("strategy_question_ids_not_exact_S01_S25")

    # The JSON references are the authoritative link graph; no missing code is allowed.
    missing_refs: list[dict[str, str]] = []
    motive_set = set(motive_codes)
    for kind, items, id_key in (
        ("major", majors, "id"),
        ("branch", branches, "id"),
    ):
        for item in items:
            owner = str(item.get(id_key) if item.get(id_key) is not None else item.get("major_id") if kind == "major" else item.get("branch_id") or item.get("name"))
            for raw in item.get("micro_motive_codes") or []:
                code = str(raw).strip()
                if code not in motive_set:
                    missing_refs.append({"kind": kind, "owner": owner, "code": code})
    report["motive_reference_integrity"] = {
        "missing": len(missing_refs),
        "pass": not missing_refs,
        "sample": missing_refs[:20],
    }
    if missing_refs:
        report["status"] = "FAIL"
        report["errors"].append(f"unresolved_motive_references:{len(missing_refs)}")

    # Question source is reference-only in Hybrid, but must remain structurally readable.
    question_payload = payloads["questions"]
    question_rows = rows(question_payload, ("questions", "data"))
    report["questions_reference"] = {"count": len(question_rows), "json_type": type(question_payload).__name__}
    if not question_rows:
        report["status"] = "FAIL"
        report["errors"].append("questions_reference_empty")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
