"""Direct read-only selector for group-specific exam-capacity rows.

This module is isolated from the existing exam cutoff/ranking path.
It reads only the owner-provided group-specific Sanjesh extraction and never
writes program2s, scores, ranks, or performs quota-based capacity allocation.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from admission_sanjesh_engine import (
    AdmissionInputError,
    _canonical_province,
    _normalize_text,
    load_majors,
)

ROOT = Path(__file__).resolve().parent
CAPACITY_PATHS = {
    "riazi": ROOT / "docs" / "data" / "sanjesh_riazi_1405_programs.json",
    "tajrobi": ROOT / "docs" / "data" / "sanjesh_tajrobi_1405_programs.json",
    "ensani": ROOT / "docs" / "data" / "sanjesh_ensani_1405_programs.json",
    "honar": ROOT / "docs" / "data" / "sanjesh_honar_1405_programs.json",
    "zaban": ROOT / "docs" / "data" / "sanjesh_zaban_1405_programs.json",
}

GROUP_MAJOR_ALIASES = {
    # Booklet labels are explicit aliases for one catalog major_id only.
    # Matching remains normalized full equality; no generic substring match.
    # Do not add an alias when the catalog contains a distinct/conflicting id.
    "riazi": {
        40: {
            "مهندسی پزشکی",
        },
        53: {
            "مهندسی صنایع و سیستم‌ها",
        },
        69: {
            "علوم و مهندسی باغبانی",
        },
        82: {
            "آمار",
        },
    },
    "tajrobi": {
        1: {
            "دکتری عمومی پزشکی",
            "دکتری حرفه‌ای پزشکی",
            "پزشکی عمومی",
        },
        2: {
            "دکتری عمومی دندانپزشکی",
            "دندانپزشکی عمومی",
        },
        3: {
            "دکتری عمومی داروسازی",
            "داروسازی عمومی",
        },
        5: {
            "کارشناسی پرستاری",
        },
        6: {
            "کارشناسی مامایی",
        },
        7: {
            "فوریت‌های پزشکی پیش‌بیمارستانی",
        },
        8: {
            "تکنولوژی اتاق عمل",
        },
        22: {
            "مهندسی بهداشت حرفه‌ای و ایمنی کار",
        },
        95: {
            "زمین‌شناسی",
        },
        169: {
            "زيستفناوري",
        },
    },
    "ensani": {
        101: {
            "کارشناسی حقوق",
        },
        104: {
            "فقه و مبانی حقوق اسلامی",
        },
        106: {
            "کارشناسی روانشناسی",
        },
        107: {
            "مشاوره",
        },
        120: {
            "کارشناسی حسابداری",
        },
        133: {
            "فلسفه و کلام اسلامی",
        },
        166: {
            "باستانشناسي",
        },
    },
    "honar": {
        140: {
            "گرافيک",
            "گرافیک",
        },
        166: {
            "باستانشناسي",
        },
    },
}
EXAM_METHOD = "با آزمون"
UNKNOWN_PERIOD = "نامشخص"


def _extract_rows(payload: Any, source_name: str) -> list[dict[str, Any]]:
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
            raise RuntimeError(f"{source_name} structure is unsupported")
    else:
        raise RuntimeError(f"{source_name} structure is unsupported")

    return [row for row in rows if isinstance(row, dict)]


@lru_cache(maxsize=4)
def load_exam_capacity_rows(group: Literal["riazi", "tajrobi", "ensani", "honar", "zaban"] = "riazi") -> tuple[dict[str, Any], ...]:
    """Load one group-specific extraction read-only."""
    try:
        path = CAPACITY_PATHS[str(group)]
    except KeyError as exc:
        raise AdmissionInputError(
            "group باید یکی از riazi، tajrobi، ensani، honar یا zaban باشد."
        ) from exc

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = _extract_rows(payload, path.name)
    if not rows:
        raise RuntimeError(f"{path.name} contains no rows")
    return tuple(rows)


def _resolved_major_names(
    major_ids: list[int],
    group: str,
) -> set[str]:
    majors = load_majors()
    names: set[str] = set()
    aliases = GROUP_MAJOR_ALIASES.get(str(group), {})
    for major_id in major_ids:
        major = majors.get(str(int(major_id)))
        if not isinstance(major, dict) or not str(major.get("name") or "").strip():
            raise AdmissionInputError(
                f"major_id={major_id} در majors_database_v2.json پیدا نشد."
            )
        names.add(_normalize_text(major.get("name")))
        for alias in aliases.get(int(major_id), set()):
            names.add(_normalize_text(alias))
    return names


def build_exam_capacity_results(
    *,
    major_ids: list[int],
    province: str,
    periods: list[str],
    include_unknown: bool = False,
    limit: int = 100,
    group: Literal["riazi", "tajrobi", "ensani", "honar", "zaban"] = "riazi",
) -> list[dict[str, Any]]:
    """Select exact exam-capacity rows by major, province, and period.

    Unknown/blank province rows are never fabricated into a requested province.
    include_unknown only permits an explicitly requested نامشخص period.
    """
    if not major_ids:
        raise AdmissionInputError("major_ids حداقل یک رشته را شامل شود.")
    if not periods:
        raise AdmissionInputError(
            "برای مسیر exam با source=capacity انتخاب period اجباری است."
        )

    canonical_province = _canonical_province(province)
    if canonical_province is None:
        raise AdmissionInputError(
            "استان نامعتبر است؛ یکی از ۳۱ استان استاندارد را انتخاب کنید."
        )

    major_names = _resolved_major_names(major_ids, group)
    requested_periods: list[str] = []
    for raw in periods:
        value = str(raw or "").strip()
        if value and value not in requested_periods:
            requested_periods.append(value)

    results: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for row in load_exam_capacity_rows(group):
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
