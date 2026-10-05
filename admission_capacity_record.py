"""Read-only direct selector for Sanjesh record-capacity rows.

This module is intentionally separate from the program2s admission engine.
It never writes program2s and never performs scoring, locality inference,
fuzzy matching, or period fallback.
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
CAPACITY_PATH = ROOT / "docs" / "data" / "sanjesh_record_capacity_full.json"
GROUP_RECORD_CAPACITY_PATHS = {
    "riazi": ROOT / "docs" / "data" / "sanjesh_riazi_1405_programs.json",
    "tajrobi": ROOT / "docs" / "data" / "sanjesh_tajrobi_1405_programs.json",
    "ensani": ROOT / "docs" / "data" / "sanjesh_ensani_1405_programs.json",
}
RECORD_CAPACITY_GROUPS = frozenset(GROUP_RECORD_CAPACITY_PATHS)


def _extract_capacity_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        for key in ("rows", "items", "records", "data", "capacity"):
            value = payload.get(key)
            if isinstance(value, list):
                rows = value
                break
        else:
            raise RuntimeError("sanjesh_record_capacity_full.json structure is unsupported")
    else:
        raise RuntimeError("sanjesh_record_capacity_full.json structure is unsupported")
    return [row for row in rows if isinstance(row, dict)]


@lru_cache(maxsize=3)
def load_group_record_capacity_rows(group: str) -> tuple[dict[str, Any], ...]:
    """Load 1405 group rows and keep only صرفاً سوابق records."""
    try:
        path = GROUP_RECORD_CAPACITY_PATHS[str(group)]
    except KeyError as exc:
        raise AdmissionInputError(
            "group برای ظرفیت سوابق باید یکی از riazi، tajrobi یا ensani باشد."
        ) from exc

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = _extract_capacity_rows(payload)
    record_rows = [
        row
        for row in rows
        if _normalize_text(row.get("admission_type")) in {"صرفاً سوابق", "صرفا سوابق"}
    ]
    if not record_rows:
        raise RuntimeError(f"{path.name} contains no record-capacity rows")
    return tuple(record_rows)


@lru_cache(maxsize=1)
def load_record_capacity_rows() -> tuple[dict[str, Any], ...]:
    """Load capacity rows read-only from the Sanjesh source file."""
    payload = json.loads(CAPACITY_PATH.read_text(encoding="utf-8"))
    rows = _extract_capacity_rows(payload)
    if not rows:
        raise RuntimeError("sanjesh_record_capacity_full.json contains no rows")
    return tuple(rows)


@lru_cache(maxsize=1)
def record_capacity_periods() -> tuple[str, ...]:
    """Return only period values actually present in the source."""
    seen: list[str] = []
    for row in load_record_capacity_rows():
        value = str(row.get("period") or "").strip()
        if value and value not in seen:
            seen.append(value)
    return tuple(seen)


def _resolved_major_names(major_ids: list[int]) -> set[str]:
    majors = load_majors()
    names: set[str] = set()
    for major_id in major_ids:
        major = majors.get(str(int(major_id)))
        if not isinstance(major, dict) or not str(major.get("name") or "").strip():
            raise AdmissionInputError(f"major_id={major_id} در majors_database_v2.json پیدا نشد.")
        names.add(_normalize_text(major.get("name")))
    return names


def _canonical_periods(periods: list[str]) -> list[str]:
    requested: list[str] = []
    known = record_capacity_periods()
    known_normalized = {_normalize_text(value): value for value in known}
    for raw in periods:
        key = _normalize_text(raw)
        if not key:
            continue
        # Persian-safe normalization only; no synonym or fallback mapping.
        canonical = known_normalized.get(key)
        requested.append(canonical if canonical is not None else str(raw).strip())
    return list(dict.fromkeys(requested))


def build_record_capacity_results(
    *,
    major_ids: list[int],
    province: str,
    periods: list[str],
    special_quota: str = "none",
    group: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Select capacity rows by exact source fields; never writes program2s."""
    if not major_ids:
        raise AdmissionInputError("major_ids حداقل یک رشته را شامل شود.")
    if not periods:
        raise AdmissionInputError("periods در مسیر capacity اجباری است.")

    canonical_province = _canonical_province(province)
    if canonical_province is None:
        raise AdmissionInputError("استان نامعتبر است؛ یکی از ۳۱ استان استاندارد را انتخاب کنید.")

    special = _normalize_text(special_quota or "none")
    if special not in {"none", "isargaran_25", "isargaran_5", "shahid"}:
        raise AdmissionInputError("special_quota نامعتبر است.")

    major_names = _resolved_major_names(major_ids)
    requested_periods = _canonical_periods(periods)

    results: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    if group is not None and group not in RECORD_CAPACITY_GROUPS:
        raise AdmissionInputError(
            "group برای ظرفیت سوابق باید یکی از riazi، tajrobi یا ensani باشد."
        )

    source_rows: list[dict[str, Any]] = []
    if group is not None:
        source_rows.extend(load_group_record_capacity_rows(group))
    source_rows.extend(load_record_capacity_rows())

    for row in source_rows:
        major_name = str(row.get("major_name") or "")
        if _normalize_text(major_name) not in major_names:
            continue

        row_period = str(row.get("period") or "").strip()
        if row_period not in requested_periods:
            continue

        raw_row_province = str(row.get("province") or "").strip()
        if not raw_row_province:
            continue
        row_province = _canonical_province(raw_row_province)
        if row_province != canonical_province:
            continue

        code = str(row.get("sanjesh_code") or "").strip()
        if not code:
            continue
        if code in seen_codes:
            continue
        seen_codes.add(code)

        notes = [
            "منبع مستقیم ظرفیت سنجش؛ بدون اتصال به program2s.",
            "major_name با نام موجود در majors_database_v2 تطبیق دقیق شد.",
            "period به‌صورت دقیق از مقادیر موجود در منبع ظرفیت فیلتر شد.",
            "استان فقط با province پرشده ردیف و بدون استنباط از campus تطبیق شد.",
        ]
        if special != "none":
            notes.append(
                "special_quota در مسیر مستقیم ظرفیت فقط به‌عنوان یادداشت نگه‌داری شد؛ "
                "محاسبه ظرفیت سهمیه‌ای انجام نشد."
            )

        item = {
            "sanjesh_code": code,
            "major_name": major_name,
            "campus": row.get("campus") or "",
            "province": row.get("province") or "",
            "period": row_period,
            "capacity_total": row.get("capacity"),
            "notes": notes,
        }
        if "quota_shares_mvp" in row:
            item["quota_shares_mvp"] = row.get("quota_shares_mvp")

        results.append(item)
        if len(results) >= limit:
            break

    return results
