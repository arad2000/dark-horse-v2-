#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only audit for the 1404 Honar/Sanjesh program dataset."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_PROGRAMS = Path("docs/data/sanjesh_honar_1404_programs.json")
DEFAULT_RIAZI = Path("docs/data/sanjesh_riazi_1404_programs.json")
DEFAULT_TAJROBI = Path("docs/data/sanjesh_tajrobi_1404_programs.json")
DEFAULT_ENSANI = Path("docs/data/sanjesh_ensani_1404_programs.json")
DEFAULT_RECORD = Path("docs/data/sanjesh_record_capacity_full.json")

BASELINE = {
    "total_rows": 9_253,
    "unique_sanjesh_codes": 9_253,
    "admission_type": {
        "با آزمون": 358,
        "صرفا بر اساس سوابق تحصیلی": 8_895,
    },
    "page_min": 32,
    "page_max": 254,
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


def norm_text(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return " ".join(
        text.replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ك", "ک")
        .split()
    )


def norm_code(value: Any) -> str:
    return "" if value is None else str(value).strip()


def unique_codes(rows: list[dict[str, Any]]) -> set[str]:
    return {
        code for row in rows if (code := norm_code(row.get("sanjesh_code")))
    }


def sample_exam_rows(
    rows: list[dict[str, Any]],
    pattern: str,
    limit: int = 5,
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


def overlap_info(
    source_codes: set[str],
    path: Path | None,
    label: str,
) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "status": "SKIPPED",
            "path": str(path) if path else None,
        }

    rows = unwrap_rows(load_json(path), label)
    other_codes = unique_codes(rows)
    common = sorted(source_codes & other_codes)

    return {
        "status": "PASS",
        "other_unique_codes": len(other_codes),
        "overlap_unique_codes": len(common),
        "sample_overlap_codes": common[:20],
    }


def compare_baseline(summary: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "total_rows": (BASELINE["total_rows"], summary["total_rows"]),
        "unique_sanjesh_codes": (
            BASELINE["unique_sanjesh_codes"],
            summary["unique_sanjesh_codes"],
        ),
        "admission_type.با آزمون": (
            BASELINE["admission_type"]["با آزمون"],
            summary["admission_type"].get("با آزمون", 0),
        ),
        "admission_type.صرفا بر اساس سوابق تحصیلی": (
            BASELINE["admission_type"]["صرفا بر اساس سوابق تحصیلی"],
            summary["admission_type"].get(
                "صرفا بر اساس سوابق تحصیلی", 0
            ),
        ),
        "page_min": (BASELINE["page_min"], summary["page_min"]),
        "page_max": (BASELINE["page_max"], summary["page_max"]),
    }

    return {
        "all_match": all(expected == actual for expected, actual in checks.values()),
        "checks": {
            name: {
                "expected": expected,
                "actual": actual,
                "match": expected == actual,
            }
            for name, (expected, actual) in checks.items()
        },
    }


def build_summary(
    programs_path: Path,
    riazi_path: Path | None,
    tajrobi_path: Path | None,
    ensani_path: Path | None,
    record_path: Path | None,
) -> dict[str, Any]:
    if not programs_path.exists():
        return {
            "status": "INPUT_MISSING",
            "programs_path": str(programs_path),
        }

    rows = unwrap_rows(load_json(programs_path), "honar programs")

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
        "province_empty_rows": sum(
            not norm_text(row.get("province")) for row in rows
        ),
        "period_unknown_rows": sum(
            norm_text(row.get("period")) == "نامشخص" for row in rows
        ),
        "page_min": min(pages) if pages else None,
        "page_max": max(pages) if pages else None,
        "missing_required_field_rows": {
            key: sum(key not in row for row in rows)
            for key in (
                "sanjesh_code",
                "major_name",
                "capacity",
                "period",
                "admission_type",
                "campus",
                "province",
                "page",
            )
        },
        "samples_exam": {
            "گرافیک": sample_exam_rows(rows, r"گرافیک|گرافی", 5),
            "فرش": sample_exam_rows(rows, r"فرش", 5),
            "ارتباط تصویری": sample_exam_rows(rows, r"ارتباطs*تصویری", 5),
            "هنر اسلامی": sample_exam_rows(rows, r"هنرs*اسلامی", 5),
        },
        "overlap": {
            "riazi": overlap_info(
                set(nonempty_codes), riazi_path, "riazi programs"
            ),
            "tajrobi": overlap_info(
                set(nonempty_codes), tajrobi_path, "tajrobi programs"
            ),
            "ensani": overlap_info(
                set(nonempty_codes), ensani_path, "ensani programs"
            ),
            "record_capacity": overlap_info(
                set(nonempty_codes), record_path, "record capacity"
            ),
        },
    }

    summary["baseline_comparison"] = compare_baseline(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--programs", type=Path, default=DEFAULT_PROGRAMS)
    parser.add_argument("--riazi", type=Path, default=DEFAULT_RIAZI)
    parser.add_argument("--tajrobi", type=Path, default=DEFAULT_TAJROBI)
    parser.add_argument("--ensani", type=Path, default=DEFAULT_ENSANI)
    parser.add_argument("--record-capacity", type=Path, default=DEFAULT_RECORD)
    args = parser.parse_args()

    report = build_summary(
        args.programs,
        args.riazi,
        args.tajrobi,
        args.ensani,
        args.record_capacity,
    )
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
