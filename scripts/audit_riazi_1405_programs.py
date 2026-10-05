#!/usr/bin/env python3
"""Phase-0 audit for the 1405 Sanjesh mathematics program dataset.

Read-only: this script never edits the source JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "sanjesh_code",
    "major_name",
    "campus",
    "province",
    "period",
    "capacity",
    "admission_type",
    "note",
    "page",
    "year",
    "group",
)

ADMISSION_ALIASES = {
    "با آزمون": "با آزمون",
    "صرفاً سوابق": "صرفاً سوابق",
    "صرفا سوابق": "صرفاً سوابق",
    "صرفا بر اساس سوابق تحصیلی": "صرفاً سوابق",
    "صرفاً بر اساس سوابق تحصیلی": "صرفاً سوابق",
}


def load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        rows = payload["rows"]
    else:
        raise ValueError(f"Unsupported JSON root in {path}: expected list or object.rows")

    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: every row must be a JSON object")
    return rows


def normalized_admission(value: Any) -> str:
    text = str(value or "").strip()
    return ADMISSION_ALIASES.get(text, text)


def code_set(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("sanjesh_code") or "").strip()
        for row in rows
        if str(row.get("sanjesh_code") or "").strip()
    }


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing = Counter()
    extras = Counter()
    code_counts = Counter(
        str(row.get("sanjesh_code") or "").strip() for row in rows
    )
    blank_code_rows = sum(
        not str(row.get("sanjesh_code") or "").strip() for row in rows
    )
    admission = Counter(normalized_admission(row.get("admission_type")) for row in rows)
    periods = Counter(str(row.get("period") or "").strip() for row in rows)
    provinces_blank = sum(
        not str(row.get("province") or "").strip() for row in rows
    )
    pages = [
        int(row["page"])
        for row in rows
        if isinstance(row.get("page"), int) or str(row.get("page", "")).isdigit()
    ]

    for row in rows:
        for field in REQUIRED_FIELDS:
            if field not in row:
                missing[field] += 1
        for key in row:
            if key not in REQUIRED_FIELDS:
                extras[key] += 1

    return {
        "total_rows": len(rows),
        "unique_codes": len(code_set(rows)),
        "blank_code_rows": blank_code_rows,
        "duplicate_code_values": sum(1 for code, count in code_counts.items() if code and count > 1),
        "duplicate_code_rows": sum(count for code, count in code_counts.items() if code and count > 1),
        "admission_type": dict(admission),
        "periods": dict(periods),
        "unknown_period_rows": periods.get("نامشخص", 0),
        "blank_province_rows": provinces_blank,
        "page_min": min(pages) if pages else None,
        "page_max": max(pages) if pages else None,
        "missing_required_fields": dict(missing),
        "observed_extra_fields": dict(extras),
        "year_counts": dict(Counter(str(row.get("year") or "").strip() for row in rows)),
        "group_counts": dict(Counter(str(row.get("group") or "").strip() for row in rows)),
    }


def overlap(rows: list[dict[str, Any]], other_rows: list[dict[str, Any]]) -> dict[str, int]:
    current = code_set(rows)
    other = code_set(other_rows)
    shared = current & other
    return {
        "current_unique": len(current),
        "other_unique": len(other),
        "shared_codes": len(shared),
        "current_only": len(current - other),
        "other_only": len(other - current),
    }


def print_audit(label: str, result: dict[str, Any]) -> None:
    print(f"=== {label} ===")
    print(f"total_rows={result['total_rows']}")
    print(f"unique_codes={result['unique_codes']}")
    print(f"blank_code_rows={result['blank_code_rows']}")
    print(f"duplicate_code_values={result['duplicate_code_values']}")
    print(f"duplicate_code_rows={result['duplicate_code_rows']}")
    print(f"admission_type={json.dumps(result['admission_type'], ensure_ascii=False)}")
    print(f"unknown_period_rows={result['unknown_period_rows']}")
    print(f"blank_province_rows={result['blank_province_rows']}")
    print(f"page_range={result['page_min']}..{result['page_max']}")
    print(f"year_counts={json.dumps(result['year_counts'], ensure_ascii=False)}")
    print(f"group_counts={json.dumps(result['group_counts'], ensure_ascii=False)}")
    print(f"periods={json.dumps(result['periods'], ensure_ascii=False)}")
    print(f"missing_required_fields={json.dumps(result['missing_required_fields'], ensure_ascii=False)}")
    print(f"observed_extra_fields={json.dumps(result['observed_extra_fields'], ensure_ascii=False)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        type=Path,
        default=Path("docs/data/sanjesh_riazi_1405_programs.json"),
        help="1405 riazi JSON",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        default=Path("docs/data/sanjesh_riazi_1404_programs.json"),
        help="optional 1404 riazi JSON",
    )
    parser.add_argument(
        "--record-capacity",
        type=Path,
        default=Path("docs/data/sanjesh_record_capacity_full.json"),
        help="optional record-capacity JSON",
    )
    args = parser.parse_args()

    rows = load_rows(args.json)
    result = audit(rows)
    print_audit("Riazi 1405", result)

    if args.compare.exists():
        compare_rows = load_rows(args.compare)
        print("=== Overlap with Riazi 1404 ===")
        print(json.dumps(overlap(rows, compare_rows), ensure_ascii=False))

    if args.record_capacity.exists():
        record_rows = load_rows(args.record_capacity)
        print("=== Overlap with Record Capacity ===")
        print(json.dumps(overlap(rows, record_rows), ensure_ascii=False))

    # Structural invariants for phase 0.
    failures: list[str] = []
    if result["blank_code_rows"]:
        failures.append("blank sanjesh_code rows detected")
    if result["duplicate_code_values"]:
        failures.append("duplicate sanjesh_code values detected")
    if result["missing_required_fields"]:
        failures.append("missing required fields detected")
    if set(result["year_counts"]) != {"1405"}:
        failures.append("year is not uniformly 1405")
    if set(result["group_counts"]) != {"riazi"}:
        failures.append("group is not uniformly riazi")

    if failures:
        print("AUDIT_STATUS=FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("AUDIT_STATUS=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
