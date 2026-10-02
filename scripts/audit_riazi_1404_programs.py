#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only audit for the 1404 Riazi/Sanjesh program dataset.

No writes to input data. No admission filtering or business logic.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_PROGRAMS = Path("docs/data/sanjesh_riazi_1404_programs.json")
DEFAULT_RECORD = Path("docs/data/sanjesh_record_capacity_full.json")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def unwrap_rows(payload: Any, label: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        candidates = ("programs", "items", "rows", "data", "records")
        rows = next((payload[k] for k in candidates if isinstance(payload.get(k), list)), None)
        if rows is None:
            raise ValueError(f"{label}: expected a top-level list or one of {candidates}")
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
    return {code for row in rows if (code := norm_code(row.get("sanjesh_code")))} 


def build_summary(programs_path: Path, record_path: Path | None) -> dict[str, Any]:
    if not programs_path.exists():
        return {
            "status": "INPUT_MISSING",
            "programs_path": str(programs_path),
            "message": "Upload the owner-provided sanjesh_riazi_1404_programs.json, then rerun this audit.",
        }

    rows = unwrap_rows(load_json(programs_path), "programs")
    codes = [norm_code(row.get("sanjesh_code")) for row in rows]
    nonempty_codes = [code for code in codes if code]
    code_counts = Counter(nonempty_codes)

    admission = Counter(norm_text(row.get("admission_type")) or "(خالی)" for row in rows)
    periods = Counter(norm_text(row.get("period")) or "(خالی)" for row in rows)

    province_empty = sum(not norm_text(row.get("province")) for row in rows)
    period_unknown = sum(norm_text(row.get("period")) == "نامشخص" for row in rows)

    duplicate_codes = {
        code: count for code, count in sorted(code_counts.items()) if count > 1
    }

    overlap: dict[str, Any] = {
        "status": "SKIPPED",
        "record_capacity_path": str(record_path) if record_path else None,
    }

    if record_path and record_path.exists():
        record_rows = unwrap_rows(load_json(record_path), "record capacity")
        record_codes = unique_codes(record_rows)
        riazi_codes = set(nonempty_codes)
        common = sorted(riazi_codes & record_codes)
        overlap = {
            "status": "PASS",
            "riazi_unique_codes": len(riazi_codes),
            "record_capacity_unique_codes": len(record_codes),
            "overlap_unique_codes": len(common),
            "overlap_ratio_vs_riazi_unique": (
                len(common) / len(riazi_codes) if riazi_codes else 0.0
            ),
            "sample_overlap_codes": common[:20],
        }

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

    return {
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
        "missing_required_field_rows": missing_required,
        "overlap_with_record_capacity": overlap,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--programs", type=Path, default=DEFAULT_PROGRAMS)
    parser.add_argument("--record-capacity", type=Path, default=DEFAULT_RECORD)
    args = parser.parse_args()

    report = build_summary(args.programs, args.record_capacity)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["status"] == "INPUT_MISSING":
        return 2

    hard_fail = (
        report["blank_sanjesh_code_rows"] > 0
        or report["period_unknown_rows"] > 0
        or any(report["missing_required_field_rows"].values())
    )
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
