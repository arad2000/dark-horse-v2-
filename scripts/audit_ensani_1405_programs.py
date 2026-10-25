#!/usr/bin/env python3
"""Audit Sanjesh Ensani 1405 program data (Phase 0 only).

Reads local JSON files and prints a compact JSON report. It never mutates
source data and does not switch any Loader/CAPACITY_PATHS/API/UI behavior.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = [
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
]


def load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        rows = payload["rows"]
    else:
        raise ValueError(f"Unsupported JSON root in {path}: expected list or dict.rows")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Non-object row found in {path}")
    return rows


def norm(value: Any) -> str:
    return " ".join(str(value if value is not None else "").strip().split())


def code_set(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("sanjesh_code", "")).strip()
        for row in rows
        if str(row.get("sanjesh_code", "")).strip()
    }


def duplicate_stats(rows: list[dict[str, Any]]) -> tuple[int, int]:
    counts = Counter(
        str(row.get("sanjesh_code", "")).strip()
        for row in rows
        if str(row.get("sanjesh_code", "")).strip()
    )
    duplicate_values = sum(1 for count in counts.values() if count > 1)
    duplicate_rows = sum(count - 1 for count in counts.values() if count > 1)
    return duplicate_values, duplicate_rows


def signature(row: dict[str, Any], fields: tuple[str, ...]) -> str:
    return "|".join(norm(row.get(field, "")) for field in fields)


def signature_overlap(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    fields: tuple[str, ...],
) -> tuple[int, int]:
    left_set = {signature(row, fields) for row in left}
    right_set = {signature(row, fields) for row in right}
    return len(left_set & right_set), len(left_set - right_set)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="docs/data/sanjesh_ensani_1405_programs.json",
    )
    parser.add_argument(
        "--compare-1404",
        default="docs/data/sanjesh_ensani_1404_programs.json",
    )
    parser.add_argument(
        "--record-capacity",
        default="docs/data/sanjesh_record_capacity_full.json",
    )
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    source = Path(args.input)
    compare_1404 = Path(args.compare_1404)
    record_capacity = Path(args.record_capacity)

    rows = load_rows(source)
    rows_1404 = load_rows(compare_1404)
    record_rows = load_rows(record_capacity)

    missing_fields = [
        field for field in REQUIRED_FIELDS
        if any(field not in row for row in rows)
    ]

    pages = [
        int(row["page"])
        for row in rows
        if isinstance(row.get("page"), (int, float)) and not isinstance(row.get("page"), bool)
    ]
    duplicate_values, duplicate_rows = duplicate_stats(rows)

    source_codes = code_set(rows)
    compare_codes = code_set(rows_1404)
    record_codes = code_set(record_rows)

    sig_1404, only_1405_sig = signature_overlap(
        rows,
        rows_1404,
        ("major_name", "campus", "province", "period", "admission_type"),
    )
    sig_record, _ = signature_overlap(
        rows,
        record_rows,
        ("major_name", "campus", "province", "period"),
    )

    report = {
        "source": str(source),
        "rows_total": len(rows),
        "unique_sanjesh_codes": len(source_codes),
        "blank_sanjesh_code": sum(
            not norm(row.get("sanjesh_code", "")) for row in rows
        ),
        "duplicate_code_values": duplicate_values,
        "duplicate_code_rows": duplicate_rows,
        "admission_type_counts": dict(
            sorted(Counter(norm(row.get("admission_type", "")) for row in rows).items())
        ),
        "period_unknown": sum(norm(row.get("period", "")) == "نامشخص" for row in rows),
        "blank_province": sum(not norm(row.get("province", "")) for row in rows),
        "page_min": min(pages) if pages else None,
        "page_max": max(pages) if pages else None,
        "distinct_pages": len(set(pages)),
        "years": sorted({row.get("year") for row in rows}, key=str),
        "groups": sorted({norm(row.get("group", "")) for row in rows}),
        "missing_required_fields": missing_fields,
        "extra_fields": sorted(
            set().union(*(row.keys() for row in rows)) - set(REQUIRED_FIELDS)
        ),
        "overlap_1404": {
            "shared_sanjesh_codes": len(source_codes & compare_codes),
            "shared_normalized_signatures": sig_1404,
            "only_1405_normalized_signatures": only_1405_sig,
        },
        "record_capacity": {
            "rows": len(record_rows),
            "unique_sanjesh_codes": len(record_codes),
            "shared_sanjesh_codes": len(source_codes & record_codes),
            "shared_normalized_signatures": sig_record,
        },
    }

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(rendered)

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
