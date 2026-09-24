#!/usr/bin/env python3
"""Audit program2s.json against the Phase-1 Sanjesh-like admission data contract.

Read-only validator. It never edits admission data, scoring/ranking, Hybrid,
or runtime cutover configuration.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROGRAMS_PATH = ROOT / "program2s.json"
MAJORS_PATH = ROOT / "majors_database_v2.json"

DIMENSIONS = (
    "zone_1",
    "zone_2",
    "zone_3",
    "isargaran_25",
    "isargaran_5",
    "shahid",
)

CORE_MISSING_PATHS = (
    "program_id",
    "university.name",
    "major_id",
    "admission_info.course_type",
    "admission_info.method",
    "admission_info.bomi_type",
    "university.province",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("programs"), list):
        return [item for item in payload["programs"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise ValueError(f"Unsupported structure: {payload!r}")


def has_nonempty(value: Any) -> bool:
    return value not in (None, "")


def get_path(record: dict[str, Any], path: str) -> Any:
    current: Any = record
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def collect_keys(value: Any, out: Counter[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            out[str(key)] += 1
            collect_keys(child, out)
    elif isinstance(value, list):
        for child in value:
            collect_keys(child, out)


def audit(records: list[dict[str, Any]], majors: list[dict[str, Any]]) -> dict[str, Any]:
    methods = Counter()
    course_types = Counter()
    bomi_types = Counter()
    core_missing = Counter()
    capacity_programs = 0
    exam_records: list[dict[str, Any]] = []
    record_records: list[dict[str, Any]] = []

    key_counts: Counter[str] = Counter()
    collect_keys(records, key_counts)

    for program in records:
        admission = program.get("admission_info") or {}
        methods[admission.get("method") or ""] += 1
        course_types[admission.get("course_type") or program.get("course_type") or ""] += 1
        bomi_types[admission.get("bomi_type") or ""] += 1

        for path in CORE_MISSING_PATHS:
            if not has_nonempty(get_path(program, path)):
                core_missing[path] += 1

        def contains_capacity(value: Any) -> bool:
            if isinstance(value, dict):
                return any(
                    ("capacity" in str(key).lower() or "ظرفیت" in str(key))
                    or contains_capacity(child)
                    for key, child in value.items()
                )
            if isinstance(value, list):
                return any(contains_capacity(child) for child in value)
            return False

        if contains_capacity(program):
            capacity_programs += 1
        if admission.get("method") == "با آزمون":
            exam_records.append(program)
        elif admission.get("method") == "سوابق تحصیلی":
            record_records.append(program)

    major_ids = {str(row.get("id")) for row in majors if row.get("id") is not None}
    program_major_ids = {
        str(program.get("major_id"))
        for program in records
        if program.get("major_id") is not None
    }
    unmatched_major_ids = sorted(program_major_ids - major_ids)

    historical_missing = Counter()
    predicted_missing = Counter()
    bomi_missing = Counter()
    historical_complete = predicted_complete = bomi_complete = 0
    historical_shape_errors: list[dict[str, Any]] = []
    predicted_shape_errors: list[dict[str, Any]] = []
    bomi_shape_errors: list[dict[str, Any]] = []

    for program in exam_records:
        historical = program.get("cutoffs_historical") or {}
        predicted = program.get("cutoffs_predicted_1405") or {}
        bomi = program.get("cutoffs_bomi") or {}
        hist_ok = bool(historical)
        pred_ok = isinstance(predicted, dict)
        bomi_ok = bool(bomi)

        for year, values in historical.items():
            for dimension in DIMENSIONS:
                if not isinstance(values, dict) or not isinstance(values.get(dimension), (int, float)):
                    historical_missing[dimension] += 1
                    hist_ok = False
                    if len(historical_shape_errors) < 20:
                        historical_shape_errors.append({
                            "program_id": program.get("program_id"),
                            "year": year,
                            "dimension": dimension,
                        })

        for dimension in DIMENSIONS:
            if not isinstance(predicted, dict) or not isinstance(predicted.get(dimension), (int, float)):
                predicted_missing[dimension] += 1
                if len(predicted_shape_errors) < 20:
                    predicted_shape_errors.append({
                        "program_id": program.get("program_id"),
                        "dimension": dimension,
                    })

        for year, values in bomi.items():
            for dimension in DIMENSIONS:
                if not isinstance(values, dict) or not isinstance(values.get(dimension), (int, float)):
                    bomi_missing[dimension] += 1
                    bomi_ok = False
                    if len(bomi_shape_errors) < 20:
                        bomi_shape_errors.append({
                            "program_id": program.get("program_id"),
                            "year": year,
                            "dimension": dimension,
                        })

        if hist_ok:
            historical_complete += 1
        if pred_ok:
            predicted_complete += 1
        if bomi_ok:
            bomi_complete += 1

    record_gpa_missing = sum(
        1 for program in record_records
        if not isinstance(program.get("cutoffs_savabegh"), dict)
        or program["cutoffs_savabegh"].get("minimum_gpa") is None
    )
    record_traz_missing = sum(
        1 for program in record_records
        if not isinstance(program.get("cutoffs_savabegh"), dict)
        or program["cutoffs_savabegh"].get("minimum_traz") is None
    )

    return {
        "total_programs": len(records),
        "method_counts": dict(methods),
        "course_type_counts": dict(course_types),
        "bomi_type_counts": dict(bomi_types),
        "unique_program_major_ids": len(program_major_ids),
        "majors_database_rows": len(majors),
        "unmatched_major_ids": unmatched_major_ids,
        "core_missing_counts": dict(core_missing),
        "capacity_key_names": sorted(
            key for key in key_counts
            if "capacity" in key.lower() or "ظرفیت" in key
        ),
        "capacity_present_program_count": capacity_programs,
        "exam_program_count": len(exam_records),
        "record_program_count": len(record_records),
        "exam_cutoff_presence": {
            "historical": historical_complete,
            "predicted_1405": predicted_complete,
            "bomi": bomi_complete,
        },
        "historical_missing_by_dimension": dict(historical_missing),
        "predicted_1405_missing_by_dimension": dict(predicted_missing),
        "bomi_missing_by_dimension": dict(bomi_missing),
        "historical_shape_errors_sample": historical_shape_errors,
        "predicted_shape_errors_sample": predicted_shape_errors,
        "bomi_shape_errors_sample": bomi_shape_errors,
        "record_missing_minimum_gpa": record_gpa_missing,
        "record_missing_minimum_traz": record_traz_missing,
        "locality_mapping_keys": sorted(
            key for key in key_counts
            if any(marker in key.lower() for marker in ("pole", "nahie", "region_mapping"))
            or any(marker in key for marker in ("قطب", "ناحیه"))
        ),
    }


def main() -> int:
    if not PROGRAMS_PATH.exists():
        print(json.dumps({"ok": False, "error": "program2s.json not found"}, ensure_ascii=False))
        return 2
    if not MAJORS_PATH.exists():
        print(json.dumps({"ok": False, "error": "majors_database_v2.json not found"}, ensure_ascii=False))
        return 2

    payload = load_json(PROGRAMS_PATH)
    majors_payload = load_json(MAJORS_PATH)
    records = flatten_records(payload)
    majors = flatten_records(majors_payload)

    report = audit(records, majors)
    core_failed = any(report["core_missing_counts"].values())
    cutoff_failed = any(report["historical_missing_by_dimension"].values()) or any(
        report["predicted_1405_missing_by_dimension"].values()
    ) or any(report["bomi_missing_by_dimension"].values())
    report["ok"] = not (core_failed or cutoff_failed or report["unmatched_major_ids"])
    report["known_nonblocking_gaps"] = {
        "capacity": report["capacity_present_program_count"] == 0,
        "ghotbi_nahieyi_mapping": not report["locality_mapping_keys"],
    }

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
