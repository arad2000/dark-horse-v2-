#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only audit for the 1404 Tajrobi/Sanjesh program dataset.

No writes to input data. No admission filtering, scoring, ranking, or business logic.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_PROGRAMS = Path("docs/data/sanjesh_tajrobi_1404_programs.json")
DEFAULT_RIAZI = Path("docs/data/sanjesh_riazi_1404_programs.json")
DEFAULT_RECORD = Path("docs/data/sanjesh_record_capacity_full.json")

BASELINE = {
    "total_rows": 13_143,
    "unique_sanjesh_codes": 13_143,
    "admission_type": {
        "با آزمون": 4_238,
        "صرفا بر اساس سوابق تحصیلی": 8_905,
    },
    "page_min": 41,
    "page_max": 402,
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def unwrap_rows(payload: Any, label: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        candidates = ("programs", "items", "rows", "data", "records")
        rows = next(
            (payload[key] for key in candidates if isinstance(payload.get(key), list)),
            None,
        )
        if rows is None:
            raise ValueError(
                f"{label}: expected a top-level list or one of {candidates}"
            )
    else:
        raise ValueError(f"{label}: unsupported JSON root type {type(payload).__name__}")

    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{label}: every row must be a JSON object")
    return rows


def norm_code(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def unique_codes(rows: list[dict[str, Any]]) -> set[str]:
    return {
        code
        for row in rows
        if (code := norm_code(row.get("sanjesh_code")))
    }


def sample_exam_rows(
    rows: list[dict[str, Any]],
    pattern: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    matcher = re.compile(pattern, re.IGNORECASE)
    result: list[dict[str, Any]] = []

    for row in rows:
        if norm_text(row.get("admission_type")) != "با آزمون":
            continue
        if not matcher.search(norm_text(row.get("major_name"))):
            continue
        result.append(
            {
                "sanjesh_code": norm_code(row.get("sanjesh_code")),
                "major_name": norm_text(row.get("major_name")),
                "capacity": row.get("capacity"),
                "period": norm_text(row.get("period")),
                "gender": norm_text(row.get("gender")),
                "campus": norm_text(row.get("campus")),
                "province": norm_text(row.get("province")),
                "note": norm_text(row.get("note")),
                "page": row.get("page"),
            }
        )
        if len(result) >= limit:
            break

    return result


def compare_baseline(summary: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "total_rows": {
            "expected": BASELINE["total_rows"],
            "actual": summary["total_rows"],
        },
        "unique_sanjesh_codes": {
            "expected": BASELINE["unique_sanjesh_codes"],
            "actual": summary["unique_sanjesh_codes"],
        },
        "admission_type.با آزمون": {
            "expected": BASELINE["admission_type"]["با آزمون"],
            "actual": summary["admission_type"].get("با آزمون", 0),
        },
        "admission_type.صرفا بر اساس سوابق تحصیلی": {
            "expected": BASELINE["admission_type"]["صرفا بر اساس سوابق تحصیلی"],
            "actual": summary["admission_type"].get(
                "صرفا بر اساس سوابق تحصیلی", 0
            ),
        },
        "page_min": {
            "expected": BASELINE["page_min"],
            "actual": summary["page_min"],
        },
        "page_max": {
            "expected": BASELINE["page_max"],
            "actual": summary["page_max"],
        },
    }
    for check in checks.values():
        check["match"] = check["expected"] == check["actual"]

    return {
        "all_match": all(check["match"] for check in checks.values()),
        "checks": checks,
    }


def build_summary(
    programs_path: Path,
    riazi_path: Path | None,
    record_path: Path | None,
) -> dict[str, Any]:
    if not programs_path.exists():
        return {
            "status": "INPUT_MISSING",
            "programs_path": str(programs_path),
        }

    rows = unwrap_rows(load_json(programs_path), "tajrobi programs")
    codes = [norm_code(row.get("sanjesh_code")) for row in rows]
    nonempty_codes = [code for code in codes if code]
    code_counts = Counter(nonempty_codes)
    duplicate_codes = {
        code: count
        for code, count in sorted(code_counts.items())
        if count > 1
    }

    admission = Counter(
        norm_text(row.get("admission_type")) or "(خالی)" for row in rows
    )
    periods = Counter(
        norm_text(row.get("period")) or "(خالی)" for row in rows
    )

    pages = [
        int(row["page"])
        for row in rows
        if isinstance(row.get("page"), int)
        or (isinstance(row.get("page"), str) and row["page"].strip().isdigit())
    ]

    province_empty = sum(not norm_text(row.get("province")) for row in rows)
    period_unknown = sum(
        norm_text(row.get("period")) == "نامشخص" for row in rows
    )

    required = (
        "sanjesh_code",
        "major_name",
        "capacity",
        "period",
        "admission_type",
        "campus",
        "province",
        "page",
    )
    missing_required = {
        key: sum(key not in row for row in rows)
        for key in required
    }

    overlap: dict[str, Any] = {}

    if riazi_path and riazi_path.exists():
        riazi_rows = unwrap_rows(load_json(riazi_path), "riazi")
        common = sorted(set(nonempty_codes) & unique_codes(riazi_rows))
        overlap["riazi"] = {
            "status": "PASS",
            "riazi_unique_codes": len(unique_codes(riazi_rows)),
            "overlap_unique_codes": len(common),
            "sample_overlap_codes": common[:20],
        }
    else:
        overlap["riazi"] = {
            "status": "SKIPPED",
            "path": str(riazi_path) if riazi_path else None,
        }

    if record_path and record_path.exists():
        record_rows = unwrap_rows(load_json(record_path), "record capacity")
        common = sorted(set(nonempty_codes) & unique_codes(record_rows))
        overlap["record_capacity"] = {
            "status": "PASS",
            "record_capacity_unique_codes": len(unique_codes(record_rows)),
            "overlap_unique_codes": len(common),
            "sample_overlap_codes": common[:20],
        }
    else:
        overlap["record_capacity"] = {
            "status": "SKIPPED",
            "path": str(record_path) if record_path else None,
        }

    summary = {
        "status": "PASS",
        "programs_path": str(programs_path),
        "total_rows": len(rows),
        "unique_sanjesh_codes": len(set(nonempty_codes)),
        "blank_sanjesh_code_rows": sum(not code for code in codes),
        "duplicate_sanjesh_codes": len(duplicate_codes),
        "duplicate_code_details_sample": dict(list(duplicate_codes.items())[:20]),
        "admission_type": dict(admission),
        "period": dict(periods),
        "province_empty_rows": province_empty,
        "period_unknown_rows": period_unknown,
        "page_min": min(pages) if pages else None,
        "page_max": max(pages) if pages else None,
        "missing_required_field_rows": missing_required,
        "samples_exam": {
            "پزشکی": sample_exam_rows(rows, r"پزشک", 3),
            "پرستاری": sample_exam_rows(rows, r"پرستار", 3),
            "داروسازی": sample_exam_rows(rows, r"داروساز", 3),
        },
        "overlap": overlap,
    }
    summary["baseline_comparison"] = compare_baseline(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--programs", type=Path, default=DEFAULT_PROGRAMS)
    parser.add_argument("--riazi", type=Path, default=DEFAULT_RIAZI)
    parser.add_argument("--record-capacity", type=Path, default=DEFAULT_RECORD)
    args = parser.parse_args()

    report = build_summary(args.programs, args.riazi, args.record_capacity)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["status"] == "INPUT_MISSING":
        return 2

    if not report["baseline_comparison"]["all_match"]:
        return 1

    if report["blank_sanjesh_code_rows"] > 0:
        return 1

    if report["duplicate_sanjesh_codes"] > 0:
        return 1

    if any(report["missing_required_field_rows"].values()):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
