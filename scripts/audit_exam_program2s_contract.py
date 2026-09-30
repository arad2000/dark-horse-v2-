#!/usr/bin/env python3
"""Read-only audit of the current program2s exam contract.

This script never modifies program2s.json or any scientific JSON.
It prints structural coverage and data gaps to stdout.

Usage:
  python scripts/audit_exam_program2s_contract.py \
    --program2s program2s.json \
    --majors majors_database_v2.json \
    [--bomi-geography docs/bomi_geography_v1.json]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

QUOTA_DIMENSIONS = (
    "zone_1",
    "zone_2",
    "zone_3",
    "isargaran_25",
    "isargaran_5",
    "shahid",
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_program_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("programs", "items", "data", "rows"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise ValueError("Unsupported program2s JSON structure")


def method_of(row: dict[str, Any]) -> str:
    return str((row.get("admission_info") or {}).get("method") or "").strip()


def bomi_type_of(row: dict[str, Any]) -> str:
    return str((row.get("admission_info") or {}).get("bomi_type") or "").strip()


def has_dimension(cutoffs: Any, dimension: str) -> bool:
    if not isinstance(cutoffs, dict):
        return False
    for value in cutoffs.values():
        if isinstance(value, dict) and dimension in value:
            return True
    return False


def has_nonempty_object(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def numeric_capacity_paths(value: Any, path: str = "") -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if re.search(r"capacity|ظرفیت", str(key), re.I):
                if isinstance(child, (int, float)) and not isinstance(child, bool):
                    found.add(child_path)
            found.update(numeric_capacity_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.update(numeric_capacity_paths(child, f"{path}[{index}]"))
    return found


def mapping_status(
    exam_rows: list[dict[str, Any]],
    geography: Any | None,
) -> dict[str, int | bool]:
    ghotbi_rows = [row for row in exam_rows if bomi_type_of(row) == "ghotbi"]
    if not geography or not isinstance(geography, dict):
        return {
            "ghotbi_exam_rows": len(ghotbi_rows),
            "repo_province_mapping_available": False,
            "ghotbi_without_repo_mapping": len(ghotbi_rows),
            "exam_mapping_source_verified": False,
        }

    provinces = geography.get("provinces")
    province_map = provinces if isinstance(provinces, dict) else {}
    unmapped = 0
    for row in ghotbi_rows:
        province = str(((row.get("university") or {}).get("province")) or "").strip()
        mapped = province_map.get(province)
        if not isinstance(mapped, dict) or mapped.get("ghotb_id") is None:
            unmapped += 1

    source = str(geography.get("source") or "").strip()
    exam_source_verified = bool(source and "با آزمون" in source)
    return {
        "ghotbi_exam_rows": len(ghotbi_rows),
        "repo_province_mapping_available": bool(province_map),
        "ghotbi_without_repo_mapping": unmapped,
        "exam_mapping_source_verified": exam_source_verified,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program2s", type=Path, required=True)
    parser.add_argument("--majors", type=Path, required=True)
    parser.add_argument("--bomi-geography", type=Path, default=None)
    args = parser.parse_args()

    programs = as_program_list(load_json(args.program2s))
    majors_payload = load_json(args.majors)
    if not isinstance(majors_payload, list):
        raise ValueError("Unsupported majors JSON structure")

    major_ids = {
        str(row.get("id"))
        for row in majors_payload
        if isinstance(row, dict) and row.get("id") is not None
    }

    methods = Counter(method_of(row) for row in programs)
    exam_rows = [row for row in programs if method_of(row) == "با آزمون"]
    record_rows = [row for row in programs if method_of(row) == "سوابق تحصیلی"]

    geography = None
    if args.bomi_geography and args.bomi_geography.exists():
        geography = load_json(args.bomi_geography)

    output: dict[str, Any] = {
        "total_programs": len(programs),
        "method_counts": dict(methods),
        "exam_programs": len(exam_rows),
        "record_programs": len(record_rows),
        "orphan_major_ids": sum(
            1 for row in programs if str(row.get("major_id")) not in major_ids
        ),
        "exam_cutoff_coverage": {
            "cutoffs_historical": sum(
                has_nonempty_object(row.get("cutoffs_historical"))
                for row in exam_rows
            ),
            "cutoffs_predicted_1405": sum(
                has_nonempty_object(row.get("cutoffs_predicted_1405"))
                for row in exam_rows
            ),
            "cutoffs_bomi": sum(
                has_nonempty_object(row.get("cutoffs_bomi"))
                for row in exam_rows
            ),
        },
        "exam_dimension_coverage": {
            dimension: sum(
                has_dimension(row.get("cutoffs_historical"), dimension)
                or has_dimension(row.get("cutoffs_predicted_1405"), dimension)
                or has_dimension(row.get("cutoffs_bomi"), dimension)
                for row in exam_rows
            )
            for dimension in QUOTA_DIMENSIONS
        },
        "exam_bomi_type_distribution": dict(
            Counter(bomi_type_of(row) for row in exam_rows)
        ),
        "program2s_numeric_capacity_fields": sorted(
            {
                path
                for row in programs
                for path in numeric_capacity_paths(row)
            }
        ),
        "mapping_audit": mapping_status(exam_rows, geography),
        "read_only": True,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
