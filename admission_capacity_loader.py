"""Read-only loader for the direct Sanjesh record-capacity source."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CAPACITY_PATH = ROOT / "docs" / "data" / "sanjesh_record_capacity_full.json"
MAJORS_PATH = ROOT / "majors_database_v2.json"


class CapacitySourceError(RuntimeError):
    """The direct capacity source is missing or malformed."""


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    text = text.replace("‌", " ").replace("‏", " ")
    return re.sub(r"s+", " ", text).strip().lower()


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("rows", "items", "records", "data", "capacity"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise CapacitySourceError("sanjesh_record_capacity_full.json structure is unsupported")


@lru_cache(maxsize=1)
def load_record_capacity() -> tuple[dict[str, Any], ...]:
    payload = json.loads(CAPACITY_PATH.read_text(encoding="utf-8"))
    rows = _extract_rows(payload)
    if not rows:
        raise CapacitySourceError("sanjesh_record_capacity_full.json contains no capacity rows")
    return tuple(rows)


@lru_cache(maxsize=1)
def load_record_capacity_majors() -> dict[str, dict[str, Any]]:
    payload = json.loads(MAJORS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise CapacitySourceError("majors_database_v2.json structure is unsupported")
    return {str(item.get("id")): item for item in payload if isinstance(item, dict)}


def available_record_periods() -> tuple[str, ...]:
    periods = {
        str(row.get("period")).strip()
        for row in load_record_capacity()
        if str(row.get("period") or "").strip()
    }
    return tuple(sorted(periods))


def _province_key(value: Any) -> str:
    key = _normalize_text(value)
    key = re.sub(r"^استان\s+", "", key)
    return key


def _major_name_for_id(major_id: int, majors: dict[str, dict[str, Any]]) -> str | None:
    major = majors.get(str(int(major_id)))
    if not isinstance(major, dict):
        return None
    name = str(major.get("name") or "").strip()
    return name or None


def build_record_capacity_results(
    *,
    major_ids: list[int],
    province: str,
    periods: list[str],
    special_quota: str,
    limit: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Select capacity rows by exact normalized major/period/province fields."""
    if not periods:
        raise ValueError("periods در مسیر source=capacity الزامی است.")

    requested_periods = {_normalize_text(value) for value in periods if str(value or "").strip()}
    if not requested_periods:
        raise ValueError("periods در مسیر source=capacity الزامی است.")

    rows = load_record_capacity()
    majors = load_record_capacity_majors()
    resolved_major_names = {
        _normalize_text(name)
        for major_id in major_ids
        if (name := _major_name_for_id(major_id, majors))
    }
    missing_major_ids = [
        int(major_id)
        for major_id in major_ids
        if _major_name_for_id(major_id, majors) is None
    ]
    province_key = _province_key(province)

    notes: list[str] = []
    if missing_major_ids:
        notes.append(
            "برای major_idهای ناموجود در majors_database_v2.json ردیف ظرفیتی انتخاب نشد: "
            + ", ".join(str(value) for value in missing_major_ids)
        )
    if special_quota != "none":
        notes.append(
            "special_quota در منبع مستقیم ظرفیت فقط به‌صورت note/context نگه داشته شد و ظرفیت یا سهمیه محاسبه نشد."
        )

    results: list[dict[str, Any]] = []
    for row in rows:
        major_name = str(row.get("major_name") or "").strip()
        row_period = str(row.get("period") or "").strip()
        row_province = str(row.get("province") or "").strip()

        # No fuzzy matching: exact equality after only Persian-safe normalization.
        if _normalize_text(major_name) not in resolved_major_names:
            continue
        if _normalize_text(row_period) not in requested_periods:
            continue
        # Blank capacity province never matches a named province.
        if not row_province or _province_key(row_province) != province_key:
            continue

        capacity_value = row.get("capacity")
        sanjesh_code = str(row.get("sanjesh_code") or "").strip()
        if not sanjesh_code or capacity_value is None:
            continue

        item_notes = [
            "منبع مستقیم ظرفیت سنجش؛ هیچ linkage یا enrichment روی program2s انجام نشده است."
        ]
        if special_quota != "none":
            item_notes.append(
                "special_quota فقط note است؛ ظرفیت سهمیه‌ای جدید از این ردیف محاسبه نشده است."
            )

        item = {
            "sanjesh_code": sanjesh_code,
            "major_name": major_name,
            "campus": str(row.get("campus") or ""),
            "province": row.get("province"),
            "period": row_period,
            "capacity_total": capacity_value,
            "notes": item_notes + (row.get("notes") if isinstance(row.get("notes"), list) else [])
        }
        if isinstance(row.get("quota_shares_mvp"), dict):
            item["quota_shares_mvp"] = row["quota_shares_mvp"]
        results.append(item)
        if len(results) >= limit:
            break

    if not results:
        notes.append(
            "برای ترکیب رشته/استان/دوره انتخاب‌شده ردیف ظرفیت منطبق در منبع سنجش یافت نشد."
        )
    return results, notes
