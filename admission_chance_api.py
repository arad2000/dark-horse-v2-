"""Admission-chance service aligned to Senjesh-style quota/cutoff dimensions.

This module is intentionally separate from Dark Horse scoring/ranking.
It reads the admission-only `program2s.json` dataset and never mutates
scientific scoring data, the individuality engine, Hybrid, or cutover state.
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
ACADEMIC_GPA_OK_LABEL = "معدل حداقل را پوشش می‌دهد"
ACADEMIC_GPA_LOW_LABEL = "معدل کمتر از حداقل"
ACADEMIC_GPA_REQUIRED_LABEL = "معدل کتبی لازم است"
ACADEMIC_GPA_DATA_MISSING_LABEL = "حداقل معدل در داده برنامه ثبت نشده"

GHOTBI_NOTE = "بومی قطبی: اعمال دقیق قطب نیازمند داده رسمی است"
OSTANI_MISMATCH_NOTE = "بومی استانی فقط در صورت تطابق استان داوطلب و محل تحصیل اعمال شد."
BOMI_DATA_MISSING_NOTE = "داده cutoff بومی این برنامه/بعد در منبع موجود نیست؛ cutoff بعد دیگری جایگزین نشد."
CUTOFF_DIMENSION_MISSING_NOTE = "برای این سهمیه، cutoff همان بُعد در داده برنامه موجود نیست؛ بعد دیگری جایگزین نشد."

QUOTA_DIMENSIONS = {
    "region_1": "zone_1",
    "region_2": "zone_2",
    "region_3": "zone_3",
    "isargaran_25": "isargaran_25",
    "isargaran_5": "isargaran_5",
    "shahid": "shahid",
}
QUOTA_OPTIONS = tuple(QUOTA_DIMENSIONS.keys())

PROVINCE_OPTIONS = (
    "آذربایجان شرقی",
    "آذربایجان غربی",
    "اردبیل",
    "اصفهان",
    "البرز",
    "ایلام",
    "بوشهر",
    "تهران",
    "چهارمحال و بختیاری",
    "خراسان جنوبی",
    "خراسان رضوی",
    "خراسان شمالی",
    "خوزستان",
    "زنجان",
    "سمنان",
    "سیستان و بلوچستان",
    "فارس",
    "قزوین",
    "قم",
    "کردستان",
    "کرمان",
    "کرمانشاه",
    "کهگیلویه و بویراحمد",
    "گلستان",
    "گیلان",
    "لرستان",
    "مازندران",
    "مرکزی",
    "هرمزگان",
    "همدان",
    "یزد",
)
PROVINCE_SET = set(PROVINCE_OPTIONS)


class AdmissionInputError(ValueError):
    """Client-provided admission input is invalid."""


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    text = text.replace("\u200c", " ").replace("\u200f", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _canonical_province(value: Any) -> str | None:
    key = _normalize_text(value)
    key = re.sub(r"^استان\s+", "", key)
    for province in PROVINCE_OPTIONS:
        if _normalize_text(province) == key:
            return province
    return None


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
    if any(any(marker in value for marker in ("همه", "تمام", "کلیه")) for value in values):
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
        course_type = _normalize_text(
            admission.get("course_type") or program.get("course_type")
        )
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
    university_province = _canonical_province(university.get("province"))
    candidate_province = _canonical_province(province)
    return (
        bomi_type == "ostani"
        and bool(candidate_province)
        and bool(university_province)
        and candidate_province == university_province
        and bool(program.get("cutoffs_bomi"))
    )


def _resolve_context(
    *,
    major_ids: list[int] | None,
    rank_in_quota: int | None,
    rank_legacy: int | None,
    quota_type: str | None,
    quota_legacy: str | None,
    region_zone_legacy: int | None,
    province: str | None,
    gpa_written: float | None,
    gpa_legacy: float | None,
) -> dict[str, Any]:
    if not major_ids:
        raise AdmissionInputError("major_ids حداقل یک رشته را شامل شود.")

    if rank_in_quota is not None and rank_legacy is not None and rank_in_quota != rank_legacy:
        raise AdmissionInputError("rank_in_quota و rank قدیمی نمی‌توانند متفاوت باشند.")
    resolved_rank = rank_in_quota if rank_in_quota is not None else rank_legacy
    if resolved_rank is None or int(resolved_rank) < 1:
        raise AdmissionInputError("رتبه در سهمیه (کارنامه ملاک عمل) الزامی است و باید مثبت باشد.")

    canonical_province = _canonical_province(province)
    if canonical_province is None:
        raise AdmissionInputError(
            "استان نامعتبر است؛ یکی از ۳۱ استان استاندارد را انتخاب کنید."
        )

    new_quota = _normalize_text(quota_type) if quota_type else ""
    legacy_quota = _normalize_text(quota_legacy) if quota_legacy else ""

    if new_quota:
        if new_quota not in QUOTA_DIMENSIONS:
            raise AdmissionInputError(
                "quota_type باید یکی از region_1، region_2، region_3، "
                "isargaran_25، isargaran_5 یا shahid باشد."
            )
        resolved_quota_type = new_quota
        if legacy_quota and legacy_quota not in {"azad", new_quota}:
            raise AdmissionInputError("quota_type با quota قدیمی ناسازگار است.")
    elif legacy_quota:
        if legacy_quota == "azad":
            if region_zone_legacy not in {1, 2, 3}:
                raise AdmissionInputError(
                    "برای payload قدیمی با quota=azad، region_zone باید ۱، ۲ یا ۳ باشد."
                )
            resolved_quota_type = f"region_{int(region_zone_legacy)}"
        elif legacy_quota in QUOTA_DIMENSIONS:
            resolved_quota_type = legacy_quota
        else:
            raise AdmissionInputError(
                "quota قدیمی فاقد cutoff dimension معتبر است؛ به منطقه دیگر fallback نشد."
            )
    elif region_zone_legacy in {1, 2, 3}:
        resolved_quota_type = f"region_{int(region_zone_legacy)}"
    else:
        raise AdmissionInputError(
            "quota_type الزامی است و باید یک dimension پشتیبانی‌شده را مشخص کند."
        )

    if (
        region_zone_legacy in {1, 2, 3}
        and resolved_quota_type.startswith("region_")
        and int(resolved_quota_type[-1]) != int(region_zone_legacy)
    ):
        raise AdmissionInputError("region_zone قدیمی با quota_type جدید ناسازگار است.")

    if gpa_written is not None and gpa_legacy is not None and abs(gpa_written - gpa_legacy) > 1e-9:
        raise AdmissionInputError("gpa_written و gpa قدیمی نمی‌توانند متفاوت باشند.")
    resolved_gpa = gpa_written if gpa_written is not None else gpa_legacy

    return {
        "rank_in_quota": int(resolved_rank),
        "quota_type": resolved_quota_type,
        "cutoff_dimension": QUOTA_DIMENSIONS[resolved_quota_type],
        "province": canonical_province,
        "gpa_written": resolved_gpa,
    }


def _select_exam_cutoff(
    program: dict[str, Any],
    *,
    cutoff_dimension: str,
    province: str,
) -> tuple[int | float | None, int | None, str, str | None]:
    admission = program.get("admission_info", {}) or {}
    bomi_type = _normalize_text(admission.get("bomi_type"))
    use_bomi = _is_ostani_bomi(program, province)

    if bomi_type == "ghotbi":
        # The dataset deliberately has no province -> ghotb mapping. Do not invent one.
        ghotbi_note = GHOTBI_NOTE
    else:
        ghotbi_note = None

    note: str | None = ghotbi_note
    if bomi_type == "ostani" and not use_bomi:
        note = note or OSTANI_MISMATCH_NOTE

    if use_bomi:
        cutoff, year = _latest_historical_cutoff(
            program.get("cutoffs_bomi"),
            cutoff_dimension,
        )
        if cutoff is not None:
            return cutoff, year, cutoff_dimension, note
        # Do not substitute another dimension when a bomi cutoff is missing.
        note = note or BOMI_DATA_MISSING_NOTE
        return None, None, cutoff_dimension, note

    predicted = program.get("cutoffs_predicted_1405")
    cutoff = _cutoff_from_dimension(predicted, cutoff_dimension)
    if cutoff is not None:
        return cutoff, 1405, cutoff_dimension, note

    # Historical fallback keeps the SAME dimension. It never swaps region/quota.
    cutoff, year = _latest_historical_cutoff(
        program.get("cutoffs_historical"),
        cutoff_dimension,
    )
    if cutoff is not None:
        return cutoff, year, cutoff_dimension, note

    return None, None, cutoff_dimension, note or CUTOFF_DIMENSION_MISSING_NOTE


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


def _academic_label(gpa_written: float | None, minimum_gpa: int | float | None) -> str:
    if minimum_gpa is None:
        return ACADEMIC_GPA_DATA_MISSING_LABEL
    if gpa_written is None:
        return ACADEMIC_GPA_REQUIRED_LABEL
    return (
        ACADEMIC_GPA_OK_LABEL
        if float(gpa_written) >= float(minimum_gpa)
        else ACADEMIC_GPA_LOW_LABEL
    )


def build_results(
    *,
    major_ids: list[int] | None,
    programs: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    rank_in_quota: int | None = None,
    quota_type: str | None = None,
    province: str | None = None,
    diploma_type: str | None = None,
    gpa_written: float | None = None,
    gpa_total: float | None = None,
    national_rank: int | None = None,
    course_types: list[str] | None = None,
    limit: int = 30,
    # Backward-compatible aliases used by the Phase-1 contract.
    rank: int | None = None,
    region_zone: int | None = None,
    quota: str | None = None,
    gpa: float | None = None,
) -> list[dict[str, Any]]:
    context = _resolve_context(
        major_ids=major_ids,
        rank_in_quota=rank_in_quota,
        rank_legacy=rank,
        quota_type=quota_type,
        quota_legacy=quota,
        region_zone_legacy=region_zone,
        province=province,
        gpa_written=gpa_written,
        gpa_legacy=gpa,
    )

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
            "cutoff_dimension": context["cutoff_dimension"],
            "label": ACADEMIC_LABEL if method == ACADEMIC_LABEL else None,
            "prestige_level": university.get("prestige_level"),
        }

        if method == "با آزمون":
            cutoff, cutoff_year, dimension, note = _select_exam_cutoff(
                program,
                cutoff_dimension=context["cutoff_dimension"],
                province=context["province"],
            )
            base["cutoff_used"] = cutoff
            base["cutoff_year"] = cutoff_year
            base["cutoff_dimension"] = dimension

            if cutoff is None:
                base["label"] = "اطلاعات cutoff کافی نیست"
            else:
                base["label"] = qualitative_label(context["rank_in_quota"], cutoff)
            if note:
                base["note"] = note

        elif method == ACADEMIC_LABEL:
            # Academic-record admission NEVER uses rank. Only written GPA is
            # compared with the source program's minimum_gpa.
            academic_cutoff = _academic_cutoff(program)
            minimum_gpa = academic_cutoff["minimum_gpa"]
            base["cutoff_used"] = academic_cutoff
            base["label"] = _academic_label(context["gpa_written"], minimum_gpa)
            if context["gpa_written"] is not None:
                base["gpa_input"] = float(context["gpa_written"])
            base["gpa_compared_to"] = minimum_gpa
            if gpa_total is not None:
                base["gpa_total_input"] = float(gpa_total)
        else:
            continue

        results.append(base)
        if len(results) >= limit:
            break

    return results


class AdmissionChanceRequest(BaseModel):
    major_ids: list[int] = Field(
        default_factory=list,
        description="شناسه رشته‌های کشف‌شده؛ حداقل یک شناسه.",
    )

    rank_in_quota: int | None = Field(
        default=None,
        ge=1,
        description="رتبه در سهمیه (کارنامه ملاک عمل انتخاب رشته سنجش).",
    )
    rank: int | None = Field(
        default=None,
        ge=1,
        description="Deprecated legacy alias for rank_in_quota.",
        deprecated=True,
    )

    quota_type: str | None = Field(
        default=None,
        description="سهمیه/بعد cutoff: region_1 | region_2 | region_3 | isargaran_25 | isargaran_5 | shahid",
        json_schema_extra={"enum": list(QUOTA_OPTIONS)},
    )
    quota: str | None = Field(
        default=None,
        max_length=64,
        description="Deprecated legacy alias. quota=azad uses region_zone only for backward compatibility.",
        deprecated=True,
    )
    region_zone: int | None = Field(
        default=None,
        description="Deprecated legacy field; used only when quota_type/quota is omitted or quota=azad.",
        deprecated=True,
    )

    province: str | None = Field(
        default=None,
        max_length=64,
        description="استان بومی داوطلب؛ یکی از ۳۱ استان استاندارد.",
        json_schema_extra={"enum": list(PROVINCE_OPTIONS)},
    )

    gpa_written: float | None = Field(
        default=None,
        ge=0,
        le=20,
        description="معدل کتبی نهایی دیپلم؛ برای مسیر سوابق تحصیلی با minimum_gpa مقایسه می‌شود.",
    )
    gpa: float | None = Field(
        default=None,
        ge=0,
        le=20,
        description="Deprecated legacy alias for gpa_written.",
        deprecated=True,
    )
    gpa_total: float | None = Field(
        default=None,
        ge=0,
        le=20,
        description="معدل کل/اختیاری؛ در فاز فعلی cutoff سوابق با gpa_written انجام می‌شود.",
    )
    national_rank: int | None = Field(
        default=None,
        ge=1,
        description="رتبه کشوری اختیاری؛ برای label سوابق تحصیلی استفاده نمی‌شود.",
    )
    course_types: list[str] = Field(default_factory=list)
    diploma_type: str | None = Field(default=None, max_length=64)
    limit: int = Field(default=30, ge=1, le=100)


router = APIRouter()


@router.post("/admission/chance")
def admission_chance(request: AdmissionChanceRequest) -> dict[str, Any]:
    try:
        context = _resolve_context(
            major_ids=request.major_ids,
            rank_in_quota=request.rank_in_quota,
            rank_legacy=request.rank,
            quota_type=request.quota_type,
            quota_legacy=request.quota,
            region_zone_legacy=request.region_zone,
            province=request.province,
            gpa_written=request.gpa_written,
            gpa_legacy=request.gpa,
        )
    except AdmissionInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        items = build_results(
            major_ids=request.major_ids,
            programs=load_programs(),
            rank_in_quota=context["rank_in_quota"],
            quota_type=context["quota_type"],
            province=context["province"],
            diploma_type=request.diploma_type,
            gpa_written=context["gpa_written"],
            gpa_total=request.gpa_total,
            national_rank=request.national_rank,
            course_types=request.course_types,
            limit=request.limit,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="داده پذیرش دانشگاه در دسترس نیست") from exc
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="داده پذیرش دانشگاه قابل استفاده نیست") from exc

    return {
        "items": items,
        "count": len(items),
        "limit": request.limit,
        "context": {
            "rank_in_quota": context["rank_in_quota"],
            "quota_type": context["quota_type"],
            "cutoff_dimension": context["cutoff_dimension"],
            "province": context["province"],
            "gpa_written": context["gpa_written"],
        },
        "disclaimer": "نتایج تخمینی و بر اساس مدل‌سازی آماری؛ جایگزین دفترچه و نتایج رسمی سنجش نیست.",
    }


def attach_router(target_router: APIRouter) -> None:
    target_router.include_router(router)
