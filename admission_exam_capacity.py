"""Direct read-only selector for 1404 Riazi exam-capacity rows.

This module is isolated from the existing exam cutoff/ranking path.
It reads only the owner-provided Sanjesh Riazi 1404 extraction and never
writes program2s, scores, ranks, or performs quota-based capacity allocation.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from admission_sanjesh_engine import (
    AdmissionInputError,
    _canonical_province,
    _normalize_text,
    load_majors,
)

ROOT = Path(__file__).resolve().parent
RIAZI_CAPACITY_PATH = ROOT / "docs" / "data" / "sanjesh_riazi_1404_programs.json"
EXAM_METHOD = "با آزمون"
UNKNOWN_PERIOD = "نامشخص"


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = None
        for key in ("rows", "items", "programs", "records", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                rows = value
                break
        if rows is None:
            raise RuntimeError(
                "sanjesh_riazi_1404_programs.json structure is unsupported"
            )
    else:
        raise RuntimeError(
            "sanjesh_riazi_1404_programs.json structure is unsupported"
        )

    return [row for row in rows if isinstance(row, dict)]


@lru_cache(maxsize=1)
def load_exam_capacity_rows() -> tuple[dict[str, Any], ...]:
    """Load the Riazi 1404 extraction read-only."""
    payload = json.loads(RIAZI_CAPACITY_PATH.read_text(encoding="utf-8"))
    rows = _extract_rows(payload)
    if not rows:
        raise RuntimeError(
            "sanjesh_riazi_1404_programs.json contains no rows"
        )
    return tuple(rows)


def _resolved_major_names(major_ids: list[int]) -> set[str]:
    majors = load_majors()
    names: set[str] = set()
    for major_id in major_ids:
        major = majors.get(str(int(major_id)))
        if not isinstance(major, dict) or not str(major.get("name") or "").strip():
            raise AdmissionInputError(
                f"major_id={major_id} در majors_database_v2.json پیدا نشد."
            )
        names.add(_normalize_text(major.get("name")))
    return names


def build_exam_capacity_results(
    *,
    major_ids: list[int],
    province: str,
    periods: list[str],
    include_unknown: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Select exact exam-capacity rows by major, province, and period.

    Unknown/blank province rows are never fabricated into a requested province.
    include_unknown only permits an explicitly requested نامشخص period.
    """
    if not major_ids:
        raise AdmissionInputError("major_ids حداقل یک رشته را شامل شود.")
    if not periods:
        raise AdmissionInputError("برای مسیر exam با source=capacity انتخاب period اجباری است.")

    canonical_province = _canonical_province(province)
    if canonical_province is None:
        raise AdmissionInputError(
            "استان نامعتبر است؛ یکی از ۳۱ استان استاندارد را انتخاب کنید."
        )

    major_names = _resolved_major_names(major_ids)
    requested_periods: list[str] = []
    for raw in periods:
        value = str(raw or "").strip()
        if value and value not in requested_periods:
            requested_periods.append(value)

    results: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for row in load_exam_capacity_rows():
        if str(row.get("admission_type") or "").strip() != EXAM_METHOD:
            continue

        major_name = str(row.get("major_name") or "").strip()
        if _normalize_text(major_name) not in major_names:
            continue

        raw_province = str(row.get("province") or "").strip()
        if not raw_province:
            continue
        row_province = _canonical_province(raw_province)
        if row_province != canonical_province:
            continue

        row_period = str(row.get("period") or "").strip()
        if row_period == UNKNOWN_PERIOD and not include_unknown:
            continue
        if row_period not in requested_periods:
            continue

        code = str(row.get("sanjesh_code") or "").strip()
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)

        results.append(
            {
                "sanjesh_code": code,
                "major_name": major_name,
                "campus": row.get("campus") or "",
                "province": row.get("province") or "",
                "period": row_period,
                "capacity": row.get("capacity"),
                "gender": row.get("gender"),
                "note": row.get("note") or "",
                "page": row.get("page"),
            }
        )

        if len(results) >= limit:
            break

    return results
