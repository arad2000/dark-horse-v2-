#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase-0 read-only audit for Sanjesh Honar 1405 program data."""

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

EXPECTED_ADMISSION_TYPES = {"با آزمون", "صرفاً سوابق", "صرفا سوابق"}
EXPECTED_YEAR = 1405
EXPECTED_GROUP = "honar"


def load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = (
            payload.get("rows")
            or payload.get("programs")
            or payload.get("items")
            or payload.get("data")
        )
    else:
        raise ValueError(f"Unsupported JSON root in {path}")

    if not isinstance(rows, list):
        raise ValueError(f"No row list found in {path}")

    bad_rows = [index for index, row in enumerate(rows) if not isinstance(row, dict)]
    if bad_rows:
        raise ValueError(f"{path}: non-object rows at indexes {bad_rows[:10]}")
    return rows


def norm(value: Any) -> str:
    text = str(value or "")
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    text = text.replace("\u200c", " ").replace("\u200f", " ")
    return " ".join(text.split()).strip()


def normalized_admission(value: Any) -> str:
    text = norm(value)
    if text == "صرفا سوابق":
        return "صرفاً سوابق"
    return text


def code_of(row: dict[str, Any]) -> str:
    return norm(row.get("sanjesh_code"))


def row_signature(
    row: dict[str, Any],
    *,
    include_admission_type: bool = True,
) -> str:
    fields = ["major_name", "campus", "province", "period"]
    if include_admission_type:
        fields.append("admission_type")
    return "|".join(norm(row.get(field)) for field in fields)


def code_set(rows: list[dict[str, Any]]) -> set[str]:
    return {code_of(row) for row in rows if code_of(row)}


def audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing_fields = Counter()
    type_issues = Counter()
    codes = [code_of(row) for row in rows]
    non_empty_codes = [code for code in codes if code]
    code_counts = Counter(non_empty_codes)
    duplicate_codes = {
        code: count for code, count in code_counts.items() if count > 1
    }

    admission_counts = Counter(normalized_admission(row.get("admission_type")) for row in rows)
    period_counts = Counter(norm(row.get("period")) for row in rows)
    year_counts = Counter(row.get("year") for row in rows)
    group_counts = Counter(norm(row.get("group")) for row in rows)

    pages = [row["page"] for row in rows if isinstance(row.get("page"), int)]

    for row in rows:
        for field in REQUIRED_FIELDS:
            if field not in row:
                missing_fields[field] += 1
        if "capacity" in row and not isinstance(row["capacity"], (int, float)):
            type_issues["capacity_not_numeric"] += 1
        if "page" in row and not isinstance(row["page"], int):
            type_issues["page_not_int"] += 1
        if "year" in row and not isinstance(row["year"], int):
            type_issues["year_not_int"] += 1

    return {
        "rows_total": len(rows),
        "unique_sanjesh_codes": len(set(non_empty_codes)),
        "blank_sanjesh_code": sum(1 for code in codes if not code),
        "duplicate_sanjesh_code_values": duplicate_codes,
        "duplicate_sanjesh_code_rows": sum(count - 1 for count in duplicate_codes.values()),
        "admission_type_counts": dict(admission_counts),
        "exam_rows": admission_counts.get("با آزمون", 0),
        "record_rows": admission_counts.get("صرفاً سوابق", 0),
        "unknown_admission_type_counts": {
            key: value
            for key, value in admission_counts.items()
            if key not in {"با آزمون", "صرفاً سوابق"}
        },
        "period_counts": dict(period_counts),
        "period_unknown_rows": period_counts.get("نامشخص", 0),
        "blank_province_rows": sum(
            1 for row in rows if not norm(row.get("province"))
        ),
        "page_min": min(pages) if pages else None,
        "page_max": max(pages) if pages else None,
        "distinct_page_count": len(set(pages)),
        "year_counts": {str(key): value for key, value in year_counts.items()},
        "group_counts": dict(group_counts),
        "required_field_missing": dict(missing_fields),
        "field_type_issues": dict(type_issues),
    }


def audit_overlap(
    rows_1405: list[dict[str, Any]],
    rows_1404: list[dict[str, Any]],
    record_rows: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    codes_1405 = code_set(rows_1405)
    codes_1404 = code_set(rows_1404)

    sig_1405 = {row_signature(row) for row in rows_1405}
    sig_1404 = {row_signature(row) for row in rows_1404}

    result: dict[str, Any] = {
        "honar_1404": {
            "rows_total": len(rows_1404),
            "unique_codes": len(codes_1404),
            "shared_code_count": len(codes_1405 & codes_1404),
            "shared_signature_count": len(sig_1405 & sig_1404),
            "new_only_signature_count": len(sig_1405 - sig_1404),
        }
    }

    if record_rows is not None:
        codes_record = code_set(record_rows)
        sig_1405_record = {
            row_signature(row, include_admission_type=False)
            for row in rows_1405
        }
        sig_record = {
            row_signature(row, include_admission_type=False)
            for row in record_rows
        }
        result["record_capacity_full"] = {
            "rows_total": len(record_rows),
            "unique_codes": len(codes_record),
            "shared_code_count": len(codes_1405 & codes_record),
            "shared_signature_count": len(sig_1405_record & sig_record),
        }

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("docs/data/sanjesh_honar_1405_programs.json"),
    )
    parser.add_argument(
        "--compare-1404",
        type=Path,
        default=Path("docs/data/sanjesh_honar_1404_programs.json"),
    )
    parser.add_argument(
        "--record-capacity",
        type=Path,
        default=Path("docs/data/sanjesh_record_capacity_full.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("honar_1405_audit_report.json"),
    )
    args = parser.parse_args()

    rows = load_rows(args.input)
    report = {
        "input": str(args.input),
        "audit": audit_rows(rows),
        "overlap": audit_overlap(
            rows,
            load_rows(args.compare_1404) if args.compare_1404.exists() else [],
            load_rows(args.record_capacity) if args.record_capacity.exists() else None,
        ),
    }

    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    audit = report["audit"]
    print("DARK HORSE V2 — HONAR 1405 PHASE-0 AUDIT")
    print(f"rows={audit['rows_total']}")
    print(f"unique_codes={audit['unique_sanjesh_codes']}")
    print(f"exam={audit['exam_rows']}")
    print(f"record={audit['record_rows']}")
    print(f"blank_code={audit['blank_sanjesh_code']}")
    print(f"duplicate_code_values={len(audit['duplicate_sanjesh_code_values'])}")
    print(f"period_unknown={audit['period_unknown_rows']}")
    print(f"blank_province={audit['blank_province_rows']}")
    print(f"pages={audit['page_min']}..{audit['page_max']}")
    print(f"report={args.output}")

    failures: list[str] = []
    if audit["blank_sanjesh_code"]:
        failures.append("blank sanjesh_code rows detected")
    if audit["duplicate_sanjesh_code_values"]:
        failures.append("duplicate sanjesh_code values detected")
    if audit["required_field_missing"]:
        failures.append("missing required fields detected")
    if audit["field_type_issues"]:
        failures.append("field type issues detected")
    if set(audit["year_counts"]) != {str(EXPECTED_YEAR)}:
        failures.append("year is not uniformly 1405")
    if set(audit["group_counts"]) != {EXPECTED_GROUP}:
        failures.append("group is not uniformly honar")
    if any(
        key not in {"با آزمون", "صرفاً سوابق"} for key in audit["admission_type_counts"]
    ):
        failures.append("unexpected admission_type detected")

    if failures:
        print("AUDIT_STATUS=FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("AUDIT_STATUS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
