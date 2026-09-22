"""Phase 1 qualitative university-admission chance service.

This module is intentionally separate from Dark Horse scoring/ranking.
It reads the admission-only `program2s.json` dataset and never mutates
scientific scoring data or the individuality engine.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent
PROGRAMS_PATH = ROOT / "program2s.json"

HIGHER_LABEL = "شانس بالاتر (تخمینی)"
BORDERLINE_LABEL = "مرزی / رقابتی"
LOWER_LABEL = "شانس پایین‌تر (تخمینی)"
ACADEMIC_LABEL = "سوابق تحصیلی"
GHOTBI_NOTE = "بومی قطبی: اعمال دقیق قطب نیازمند داده رسمی است"
UNSUPPORTED_QUOTA_NOTE = (
    "quota ورودی بُعد cutoff مستقل ندارد؛ برای فاز ۱ cutoff منطقه استفاده شد."
)
ALL_DIPLOMA_MARKERS = ("همه", "تمام", "کلیه")


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    text = text.replace("\u200c", " ").replace("\u200f", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _number(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip().replace(",", "").replace("٬", "")
    try:
        return float(text)
    except ValueError:
        return None


def _extract_programs(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("programs", "items", "records", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise RuntimeError("program2s.json structure is unsupported")


@lru_cache(maxsize=1)
def load_programs() -> tuple[dict[str, Any], ...]:
    payload = json.loads(PROGRAMS_PATH.read_text(encoding="utf-8"))
    programs = _extract_programs(payload)
    if not programs:
        raise RuntimeError("program2s.json contains no programs")
    return tuple(programs)


def _flatten_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values: list[str] = []
        for child in value.values():
            values.extend(_flatten_text(child))
        return values
    if isinstance(value, list):
        values: list[str] = []
        for child in value:
            values.extend(_flatten_text(child))
        return values
    return []


def _diploma_matches(program: dict[str, Any], diploma_type: str | None) -> bool:
    if not diploma_type:
        return True
    required = program.get("admission_info", {}).get("diploma_requirements")
    if not required:
        return True
    wanted = _normalize_text(diploma_type)
    values = [_normalize_text(item) for item in _flatten_text(required)]
    if any(any(marker in value for marker in ALL_DIPLOMA_MARKERS) for value in values):
        return True
    return any(wanted in value or value in wanted for value in values)


def filter_programs(
    programs: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    major_ids: list[int] | None = None,
    diploma_type: str | None = None,
    course_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    wanted_majors = {str(int(value)) for value in (major_ids or [])}
    wanted_courses = {_normalize_text(value) for value in (course_types or [])}
    filtered: list[dict[str, Any]] = []

    for program in programs:
        if wanted_majors and str(program.get("major_id")) not in wanted_majors:
            continue
        admission = program.get("admission_info", {}) or {}
        course_type = _normalize_text(admission.get("course_type") or program.get("course_type"))
        if wanted_courses and course_type not in wanted_courses:
            continue
        if not _diploma_matches(program, diploma_type):
            continue
        filtered.append(program)
    return filtered


def _year_number(value: Any) -> int:
    match = re.search(r"(\d{4})", str(value))
    return int(match.group(1)) if match else -1


def _cutoff_from_dimension(container: Any, dimension: str) -> int | float | None:
    if not isinstance(container, dict):
        return None
    direct = container.get(dimension)
    value = _number(direct)
    if value is not None:
        return value
    if isinstance(direct, dict):
        for key in ("cutoff", "rank", "value", "maximum_rank"):
            value = _number(direct.get(key))
            if value is not None:
                return value
    return None


def _latest_historical_cutoff(
    historical: Any,
    dimension: str,
) -> tuple[int | float | None, int | None]:
    if not isinstance(historical, dict):
        return None, None
    candidates: list[tuple[int, int | float]] = []
    for year, values in historical.items():
        cutoff = _cutoff_from_dimension(values, dimension)
        year_num = _year_number(year)
        if cutoff is not None and year_num >= 0:
            candidates.append((year_num, cutoff))
    if not candidates:
        return None, None
    year_num, cutoff = max(candidates, key=lambda item: item[0])
    return cutoff, year_num


def _is_ostani_bomi(program: dict[str, Any], province: str | None) -> bool:
    admission = program.get("admission_info", {}) or {}
    bomi_type = _normalize_text(admission.get("bomi_type"))
    university = program.get("university", {}) or {}
    university_province = _normalize_text(university.get("province"))
    candidate_province = _normalize_text(province)
    return (
        bomi_type == "ostani"
        and bool(candidate_province)
        and bool(university_province)
        and candidate_province == university_province
    )


def _select_exam_cutoff(
    program: dict[str, Any],
    *,
    region_zone: int,
    quota: str,
    province: str | None,
) -> tuple[int | float | None, int | None, str, str | None]:
    """Return cutoff, year, dimension/basis and optional conservative note.

    No province -> ghotb mapping is invented here. For ostani programs, an
    exact province match is enough to use the bomi table. For ghotbi/keshvari,
    or when province matching is not supported, phase 1 uses the standard
    zone/quota dimension. Ghotbi gets an explicit warning in the API response.
    """
    quota_key = _normalize_text(quota)
    cutoff_dimension = quota_key if quota_key in {"isargaran_25", "isargaran_5", "shahid"} else f"zone_{int(region_zone)}"
    note: str | None = None

    admission = program.get("admission_info", {}) or {}
    bomi_type = _normalize_text(admission.get("bomi_type"))
    use_bomi = _is_ostani_bomi(program, province)

    if bomi_type == "ghotbi":
        note = GHOTBI_NOTE
    elif bomi_type == "ostani" and province and not use_bomi:
        note = "بومی استانی فقط در صورت تطابق استان داوطلب و محل تحصیل اعمال شد."

    source = program.get("cutoffs_bomi") if use_bomi else program.get("cutoffs_predicted_1405")
    cutoff = _cutoff_from_dimension(source, cutoff_dimension)
    year: int | None = 1405 if cutoff is not None and not use_bomi else None
    if cutoff is not None and use_bomi:
        # cutoffs_bomi is versioned by historical year in phase 1.
        cutoff, year = _latest_historical_cutoff(source, cutoff_dimension)

    if cutoff is None:
        cutoff, year = _latest_historical_cutoff(program.get("cutoffs_historical"), cutoff_dimension)
        if cutoff is not None and note is None and bomi_type == "ghotbi":
            note = GHOTBI_NOTE

    # The phase-1 dataset has no independent "azad" cutoff dimension.
    # Known veteran/quota dimensions use their own cutoff key; every other
    # quota name falls back to the supplied region zone and is disclosed.
    if quota_key not in {"isargaran_25", "isargaran_5", "shahid"}:
        note = note or UNSUPPORTED_QUOTA_NOTE
    return cutoff, year, cutoff_dimension, note


def qualitative_label(rank: int, cutoff: int | float) -> str:
    if cutoff <= 0:
        raise ValueError("cutoff must be positive")
    ratio = float(rank) / float(cutoff)
    if ratio <= 0.90:
        return HIGHER_LABEL
    if ratio <= 1.10:
        return BORDERLINE_LABEL
    return LOWER_LABEL


def _academic_cutoff(program: dict[str, Any]) -> dict[str, Any]:
    cutoff = program.get("cutoffs_savabegh") or {}
    return {
        "minimum_gpa": _number(cutoff.get("minimum_gpa")),
        "minimum_traz": _number(cutoff.get("minimum_traz")),
    }


def build_results(
    *,
    major_ids: list[int] | None,
    rank: int,
    region_zone: int,
    quota: str,
    province: str | None,
    diploma_type: str | None,
    gpa: float | None,
    course_types: list[str] | None,
    limit: int,
    programs: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    filtered = filter_programs(
        programs,
        major_ids=major_ids,
        diploma_type=diploma_type,
        course_types=course_types,
    )
    results: list[dict[str, Any]] = []
    for program in filtered:
        admission = program.get("admission_info", {}) or {}
        method = admission.get("method") or ""
        university = program.get("university", {}) or {}
        base = {
            "program_id": program.get("program_id"),
            "university_name": university.get("name") or program.get("university_name") or "",
            "major_id": int(program.get("major_id")),
            "course_type": admission.get("course_type") or program.get("course_type"),
            "method": method,
            "cutoff_used": None,
            "cutoff_year": None,
            "label": ACADEMIC_LABEL if method == ACADEMIC_LABEL else None,
            "prestige_level": university.get("prestige_level"),
        }

        if method == "با آزمون":
            cutoff, cutoff_year, dimension, note = _select_exam_cutoff(
                program,
                region_zone=region_zone,
                quota=quota,
                province=province,
            )
            if cutoff is None:
                # Do not manufacture a deterministic chance when the dataset
                # does not provide a usable cutoff.
                base["label"] = "اطلاعات cutoff کافی نیست"
                base["cutoff_used"] = None
            else:
                base["cutoff_used"] = cutoff
                base["cutoff_year"] = cutoff_year
                base["label"] = qualitative_label(rank, cutoff)
            base["cutoff_dimension"] = dimension
            if note:
                base["note"] = note
        elif method == ACADEMIC_LABEL:
            # Academic-record admission has no rank cutoff. GPA cutoffs are
            # returned as supplied by cutoffs_savabegh; rank is never compared.
            base["cutoff_used"] = _academic_cutoff(program)
            if gpa is not None:
                base["gpa_input"] = float(gpa)
        else:
            continue

        results.append(base)
        if len(results) >= limit:
            break
    return results


class AdmissionChanceRequest(BaseModel):
    major_ids: list[int] = Field(default_factory=list)
    rank: int | None = Field(default=None, ge=1)
    region_zone: int | None = Field(default=None)
    quota: str | None = Field(default=None, min_length=1, max_length=64)
    province: str | None = Field(default=None, max_length=128)
    diploma_type: str | None = Field(default=None, max_length=64)
    gpa: float | None = Field(default=None, ge=0, le=20)
    course_types: list[str] = Field(default_factory=list)
    limit: int = Field(default=30, ge=1, le=100)


router = APIRouter()


@router.post("/admission/chance")
def admission_chance(request: AdmissionChanceRequest) -> dict[str, Any]:
    missing = []
    if request.rank is None:
        missing.append("rank")
    if request.region_zone is None:
        missing.append("region_zone")
    if not request.quota:
        missing.append("quota")
    if missing:
        raise HTTPException(
            status_code=400,
            detail="فیلدهای ضروری ناقص است: " + "، ".join(missing),
        )
    if request.region_zone not in {1, 2, 3}:
        raise HTTPException(status_code=400, detail="region_zone باید ۱، ۲ یا ۳ باشد")

    try:
        items = build_results(
            major_ids=request.major_ids,
            rank=int(request.rank),
            region_zone=int(request.region_zone),
            quota=str(request.quota),
            province=request.province,
            diploma_type=request.diploma_type,
            gpa=request.gpa,
            course_types=request.course_types,
            limit=request.limit,
            programs=load_programs(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="داده پذیرش دانشگاه در دسترس نیست") from exc
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="داده پذیرش دانشگاه قابل استفاده نیست") from exc

    return {
        "items": items,
        "count": len(items),
        "limit": request.limit,
        "disclaimer": "نتایج تخمینی و بر اساس مدل‌سازی آماری؛ جایگزین دفترچه و نتایج رسمی سنجش نیست.",
    }


def attach_router(target_router: APIRouter) -> None:
    target_router.include_router(router)
