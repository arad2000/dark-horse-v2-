"""Phase 3 admission-chance service.

This module is isolated from Dark Horse scoring/ranking. It reads only
admission datasets and never changes the individuality engine, Hybrid, or
PostgreSQL runtime cutover.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
PROGRAMS_PATH = ROOT / "program2s.json"
MAJORS_PATH = ROOT / "majors_database_v2.json"

HIGHER_LABEL = "شانس بالاتر (تخمینی)"
BORDERLINE_LABEL = "مرزی / رقابتی"
LOWER_LABEL = "شانس پایین‌تر (تخمینی)"

RECORD_ABOVE_LABEL = "معدل مؤثر بالاتر از حداقل"
RECORD_AT_MIN_LABEL = "معدل مؤثر در حد حداقل"
RECORD_BELOW_LABEL = "معدل مؤثر پایین‌تر از حداقل"
RECORD_GPA_REQUIRED_LABEL = "معدل لازم برای ارزیابی وارد نشده"
RECORD_GPA_DATA_MISSING_LABEL = "حداقل معدل در داده برنامه ثبت نشده"

EXAM_METHOD = "با آزمون"
RECORD_METHOD = "سوابق تحصیلی"

GHOTBI_NOTE = "بومی قطبی: اعمال دقیق قطب نیازمند داده رسمی است"
OSTANI_MISMATCH_NOTE = "بومی استانی فقط در صورت تطابق استان داوطلب و محل تحصیل اعمال شد."
SPECIAL_QUOTA_NOTE = (
    "این مقایسه فعلاً روی dimension سهمیه خاص انتخاب‌شده انجام شده است؛ "
    "رتبه منطقه نیز دریافت شده اما در این مقایسه cutoff منطقه ملاک label نیست."
)
SPECIAL_QUOTA_FALLBACK_NOTE = (
    "برای سهمیه خاص انتخاب‌شده در این برنامه cutoff مستقل موجود نبود؛ "
    "برای جلوگیری از fallback بی‌صدا، cutoff منطقه با ذکر این note استفاده شد."
)
CUTOFF_DIMENSION_MISSING_NOTE = (
    "برای بعد cutoff انتخاب‌شده در داده برنامه cutoff قابل استفاده موجود نیست."
)
RECORD_COEFFICIENT_NOTE = (
    "ضریب پایه جدول نوع دیپلم/گروه تحصیلی اعمال شد؛ استثناهای موردی سنجش "
    "فقط در صورت وجود نگاشت رسمی در داده منبع قابل اعمال هستند."
)

QUOTA_DIMENSIONS = {
    "region_1": "zone_1",
    "region_2": "zone_2",
    "region_3": "zone_3",
    "isargaran_25": "isargaran_25",
    "isargaran_5": "isargaran_5",
    "shahid": "shahid",
}

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

# The Phase-3 base coefficient table requested by the product contract.
# Rows = diploma type; columns = target admission group.
GPA_COEFFICIENTS = {
    "riazi": {
        "riazi": 100.0,
        "tajrobi": 100.0,
        "ensani": 57.1,
        "honar": 100.0,
        "zaban": 100.0,
    },
    "tajrobi": {
        "riazi": 100.0,
        "tajrobi": 100.0,
        "ensani": 57.1,
        "honar": 100.0,
        "zaban": 100.0,
    },
    "ensani": {
        "riazi": 57.1,
        "tajrobi": 57.1,
        "ensani": 100.0,
        "honar": 100.0,
        "zaban": 100.0,
    },
    "maaref": {
        "riazi": 57.1,
        "tajrobi": 57.1,
        "ensani": 100.0,
        "honar": 100.0,
        "zaban": 100.0,
    },
    "other_fani": {
        "riazi": 51.4,
        "tajrobi": 51.4,
        "ensani": 51.4,
        "honar": 100.0,
        "zaban": 100.0,
    },
}

TARGET_GROUP_VALUES = {"riazi", "tajrobi", "ensani", "honar", "zaban"}
DIPLOMA_VALUES = set(GPA_COEFFICIENTS)

GROUP_MAP = {
    "ریاضی": "riazi",
    "ریاضی فیزیک": "riazi",
    "علوم ریاضی و فنی": "riazi",
    "تجربی": "tajrobi",
    "علوم تجربی": "tajrobi",
    "انسانی": "ensani",
    "علوم انسانی": "ensani",
    "معارف": "maaref",
    "علوم و معارف": "maaref",
    "هنر": "honar",
    "زبان": "zaban",
    "زبانهای خارجه": "zaban",
    "زبان های خارجه": "zaban",
}


class AdmissionInputError(ValueError):
    """Invalid client-side admission input."""


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    text = text.replace("\u200c", " ").replace("\u200f", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


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
    try:
        return float(str(value).strip().replace(",", "").replace("٬", ""))
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


@lru_cache(maxsize=1)
def load_majors() -> dict[str, dict[str, Any]]:
    payload = json.loads(MAJORS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("majors_database_v2.json structure is unsupported")
    return {str(item.get("id")): item for item in payload if isinstance(item, dict)}


def _major_target_group(major_id: Any, majors: dict[str, dict[str, Any]]) -> str | None:
    major = majors.get(str(major_id))
    if not major:
        return None
    raw = _normalize_text(major.get("exam_group"))
    for source, target in GROUP_MAP.items():
        if _normalize_text(source) == raw:
            return target
    return None


def _flatten_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        items: list[str] = []
        for child in value.values():
            items.extend(_flatten_text(child))
        return items
    if isinstance(value, list):
        items: list[str] = []
        for child in value:
            items.extend(_flatten_text(child))
        return items
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
    admission_method: str | None = None,
) -> list[dict[str, Any]]:
    wanted_majors = {str(int(value)) for value in (major_ids or [])}
    wanted_courses = {_normalize_text(value) for value in (course_types or [])}
    filtered: list[dict[str, Any]] = []

    for program in programs:
        if wanted_majors and str(program.get("major_id")) not in wanted_majors:
            continue
        admission = program.get("admission_info", {}) or {}
        method = str(admission.get("method") or "")
        if admission_method and method != admission_method:
            continue
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


def _is_ostani_bomi(program: dict[str, Any], province: str) -> bool:
    admission = program.get("admission_info", {}) or {}
    if _normalize_text(admission.get("bomi_type")) != "ostani":
        return False
    university = program.get("university", {}) or {}
    return (
        _canonical_province(university.get("province")) == province
        and bool(program.get("cutoffs_bomi"))
    )


def _exam_cutoff(
    program: dict[str, Any],
    *,
    cutoff_dimension: str,
    region_dimension: str,
    special_quota: str,
    province: str,
) -> tuple[int | float | None, int | None, str, str | None]:
    admission = program.get("admission_info", {}) or {}
    bomi_type = _normalize_text(admission.get("bomi_type"))
    notes: list[str] = []

    if bomi_type == "ghotbi":
        notes.append(GHOTBI_NOTE)

    if bomi_type == "ostani" and not _is_ostani_bomi(program, province):
        notes.append(OSTANI_MISMATCH_NOTE)

    requested_dimension = cutoff_dimension
    if special_quota != "none":
        notes.append(SPECIAL_QUOTA_NOTE)

    # Bomi is preferred when the province matches and the program has bomi data.
    if _is_ostani_bomi(program, province):
        cutoff, year = _latest_historical_cutoff(
            program.get("cutoffs_bomi"),
            requested_dimension,
        )
        if cutoff is not None:
            return cutoff, year, requested_dimension, " | ".join(notes) or None

        # Explicitly disclosed fallback to the region dimension.
        if requested_dimension != region_dimension:
            cutoff, year = _latest_historical_cutoff(
                program.get("cutoffs_bomi"),
                region_dimension,
            )
            if cutoff is not None:
                notes.append(SPECIAL_QUOTA_FALLBACK_NOTE)
                return cutoff, year, region_dimension, " | ".join(notes)

    predicted = program.get("cutoffs_predicted_1405")
    cutoff = _cutoff_from_dimension(predicted, requested_dimension)
    if cutoff is not None:
        return cutoff, 1405, requested_dimension, " | ".join(notes) or None

    cutoff, year = _latest_historical_cutoff(
        program.get("cutoffs_historical"),
        requested_dimension,
    )
    if cutoff is not None:
        return cutoff, year, requested_dimension, " | ".join(notes) or None

    # Special quota may be unavailable for a program; disclose the region fallback.
    if special_quota != "none" and requested_dimension != region_dimension:
        cutoff = _cutoff_from_dimension(predicted, region_dimension)
        if cutoff is not None:
            notes.append(SPECIAL_QUOTA_FALLBACK_NOTE)
            return cutoff, 1405, region_dimension, " | ".join(notes)
        cutoff, year = _latest_historical_cutoff(
            program.get("cutoffs_historical"),
            region_dimension,
        )
        if cutoff is not None:
            notes.append(SPECIAL_QUOTA_FALLBACK_NOTE)
            return cutoff, year, region_dimension, " | ".join(notes)

    return None, None, requested_dimension, " | ".join(notes + [CUTOFF_DIMENSION_MISSING_NOTE])


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


def _record_label(gpa_effective: float | None, minimum_gpa: float | None) -> str:
    if minimum_gpa is None:
        return RECORD_GPA_DATA_MISSING_LABEL
    if gpa_effective is None:
        return RECORD_GPA_REQUIRED_LABEL
    if gpa_effective > minimum_gpa:
        return RECORD_ABOVE_LABEL
    if gpa_effective == minimum_gpa:
        return RECORD_AT_MIN_LABEL
    return RECORD_BELOW_LABEL


def _canonical_diploma(value: str) -> str:
    key = _normalize_text(value)
    aliases = {
        "ریاضی": "riazi",
        "ریاضی فیزیک": "riazi",
        "تجربی": "tajrobi",
        "انسانی": "ensani",
        "معارف": "maaref",
        "علوم و معارف": "maaref",
        "فنی": "other_fani",
        "فنی حرفه ای": "other_fani",
        "کاردانش": "other_fani",
        "سایر": "other_fani",
        "other": "other_fani",
    }
    return aliases.get(key, key)


def _canonical_target_group(value: str) -> str:
    key = _normalize_text(value)
    aliases = {
        "ریاضی": "riazi",
        "ریاضی فیزیک": "riazi",
        "تجربی": "tajrobi",
        "انسانی": "ensani",
        "هنر": "honar",
        "زبان": "zaban",
    }
    return aliases.get(key, key)


def _record_input_gpa(diploma_type: str, gpa_written: float | None, gpa_total: float | None) -> tuple[float, str]:
    if diploma_type == "other_fani":
        if gpa_total is None:
            raise AdmissionInputError("برای دیپلم فنی/کاردانش فقط gpa_total الزامی است.")
        if gpa_written is not None:
            raise AdmissionInputError("برای دیپلم فنی/کاردانش gpa_written ارسال نشود؛ gpa_total استفاده می‌شود.")
        return float(gpa_total), "gpa_total"
    if diploma_type in {"riazi", "tajrobi", "ensani", "maaref"}:
        if gpa_written is None:
            raise AdmissionInputError("برای دیپلم نظری gpa_written الزامی است.")
        if gpa_total is not None:
            raise AdmissionInputError("برای دیپلم نظری gpa_total ارسال نشود؛ gpa_written استفاده می‌شود.")
        return float(gpa_written), "gpa_written"
    raise AdmissionInputError(
        "diploma_type باید یکی از riazi، tajrobi، ensani، maaref یا other_fani باشد."
    )


def _record_target_group(
    *,
    explicit_target: str | None,
    major_id: Any,
    majors: dict[str, dict[str, Any]],
) -> str:
    if explicit_target:
        target = _canonical_target_group(explicit_target)
        if target not in TARGET_GROUP_VALUES:
            raise AdmissionInputError("target_field_group نامعتبر است.")
        return target

    inferred = _major_target_group(major_id, majors)
    if inferred is None:
        raise AdmissionInputError(
            "گروه تحصیلی هدف از major قابل استنتاج نیست؛ target_field_group را ارسال کنید."
        )
    return inferred


def _coefficient(diploma_type: str, target_group: str) -> float:
    return GPA_COEFFICIENTS[diploma_type][target_group]


def build_exam_results(
    *,
    major_ids: list[int],
    rank_in_quota: int,
    region_zone: int,
    special_quota: str,
    province: str,
    diploma_type: str | None,
    gpa_written: float | None,
    national_rank: int | None,
    course_types: list[str],
    programs: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    limit: int,
) -> list[dict[str, Any]]:
    region_dimension = f"zone_{region_zone}"
    special_dimension = QUOTA_DIMENSIONS.get(special_quota, region_dimension)
    cutoff_dimension = special_dimension if special_quota != "none" else region_dimension

    filtered = filter_programs(
        programs,
        major_ids=major_ids,
        course_types=course_types,
        admission_method=EXAM_METHOD,
    )

    results: list[dict[str, Any]] = []
    for program in filtered:
        cutoff, cutoff_year, used_dimension, note = _exam_cutoff(
            program,
            cutoff_dimension=cutoff_dimension,
            region_dimension=region_dimension,
            special_quota=special_quota,
            province=province,
        )
        item = {
            "program_id": program.get("program_id"),
            "university_name": (program.get("university") or {}).get("name") or program.get("university_name") or "",
            "major_id": int(program.get("major_id")),
            "course_type": (program.get("admission_info") or {}).get("course_type") or program.get("course_type"),
            "method": EXAM_METHOD,
            "cutoff_dimension": used_dimension,
            "cutoff_used": cutoff,
            "cutoff_year": cutoff_year,
            "label": "اطلاعات cutoff کافی نیست" if cutoff is None else qualitative_label(rank_in_quota, cutoff),
        }
        if special_quota != "none":
            item["special_quota"] = special_quota
        if diploma_type:
            item["diploma_type"] = diploma_type
        if gpa_written is not None:
            item["gpa_input"] = float(gpa_written)
            item["note_gpa"] = "اثر معدل در مسیر کنکور داخل رتبه/فرآیند سنجش داوطلب است؛ برای مقایسه cutoff این سرویس از رتبه در سهمیه استفاده می‌کند."
        if national_rank is not None:
            item["national_rank_input"] = int(national_rank)
        if note:
            item["note"] = note
        results.append(item)
        if len(results) >= limit:
            break
    return results


def build_record_results(
    *,
    major_ids: list[int],
    diploma_type: str,
    gpa_written: float | None,
    gpa_total: float | None,
    province: str,
    target_field_group: str | None,
    course_types: list[str],
    programs: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    majors: dict[str, dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    gpa_input, gpa_field = _record_input_gpa(diploma_type, gpa_written, gpa_total)

    filtered = filter_programs(
        programs,
        major_ids=major_ids,
        course_types=course_types,
        admission_method=RECORD_METHOD,
    )

    results: list[dict[str, Any]] = []
    for program in filtered:
        target_group = _record_target_group(
            explicit_target=target_field_group,
            major_id=program.get("major_id"),
            majors=majors,
        )
        coefficient = _coefficient(diploma_type, target_group)
        effective = round(gpa_input * coefficient / 100.0, 4)

        academic_cutoff = _academic_cutoff(program)
        minimum_gpa = academic_cutoff["minimum_gpa"]

        item = {
            "program_id": program.get("program_id"),
            "university_name": (program.get("university") or {}).get("name") or program.get("university_name") or "",
            "major_id": int(program.get("major_id")),
            "course_type": (program.get("admission_info") or {}).get("course_type") or program.get("course_type"),
            "method": RECORD_METHOD,
            "cutoff_dimension": None,
            "cutoff_used": academic_cutoff,
            "label": _record_label(effective, minimum_gpa),
            "gpa_input": gpa_input,
            "gpa_input_field": gpa_field,
            "gpa_coefficient": coefficient,
            "gpa_effective": effective,
            "target_field_group": target_group,
            "province": province,
            "note": RECORD_COEFFICIENT_NOTE,
        }
        results.append(item)
        if len(results) >= limit:
            break
    return results


class AdmissionChanceRequest(BaseModel):
    admission_path: Literal["exam", "record"] | None = Field(
        default=None,
        description="مسیر پذیرش: exam=با آزمون، record=صرفاً سوابق تحصیلی.",
    )
    major_ids: list[int] = Field(default_factory=list)

    # Exam path
    rank_in_quota: int | None = Field(
        default=None,
        ge=1,
        description="رتبه در سهمیه — کارنامه ملاک عمل انتخاب رشته.",
    )
    region_zone: int | None = Field(default=None, ge=1, le=3)
    special_quota: str = Field(default="none")
    province: str | None = Field(default=None, max_length=64)
    national_rank: int | None = Field(default=None, ge=1)
    gpa_written: float | None = Field(default=None, ge=0, le=20)

    # Record path
    diploma_type: str | None = Field(default=None, max_length=64)
    gpa_total: float | None = Field(default=None, ge=0, le=20)
    target_field_group: str | None = Field(default=None, max_length=32)

    course_types: list[str] = Field(default_factory=list)
    limit: int = Field(default=30, ge=1, le=100)

    # Legacy fields accepted only as a compatibility envelope.
    rank: int | None = Field(default=None, ge=1, deprecated=True)
    quota: str | None = Field(default=None, max_length=64, deprecated=True)
    gpa: float | None = Field(default=None, ge=0, le=20, deprecated=True)


def _resolve_legacy_path(request: AdmissionChanceRequest) -> str:
    if request.admission_path:
        return request.admission_path
    # Legacy payloads were exam-oriented. Preserve that contract only when
    # legacy rank/region/quota fields identify an exam request.
    if request.rank_in_quota is not None or request.rank is not None or request.region_zone is not None or request.quota:
        return "exam"
    raise AdmissionInputError("admission_path باید یکی از exam یا record باشد.")


def _resolve_exam_request(request: AdmissionChanceRequest) -> dict[str, Any]:
    rank = request.rank_in_quota if request.rank_in_quota is not None else request.rank
    if rank is None:
        raise AdmissionInputError("برای مسیر با آزمون rank_in_quota الزامی است.")
    region = request.region_zone
    special = _normalize_text(request.special_quota or "none")
    if special == "":
        special = "none"
    special_aliases = {
        "none": "none",
        "هیچکدام": "none",
        "ندارد": "none",
        "ایثارگران ۲۵": "isargaran_25",
        "ایثارگران ۲۵٪": "isargaran_25",
        "isargaran25": "isargaran_25",
        "ایثارگران ۵": "isargaran_5",
        "ایثارگران ۵٪": "isargaran_5",
        "isargaran5": "isargaran_5",
        "خانواده شهدا": "shahid",
    }
    special = special_aliases.get(special, special)
    if special not in {"none", *QUOTA_DIMENSIONS.keys()}:
        raise AdmissionInputError("special_quota نامعتبر است.")
    if region not in {1, 2, 3}:
        if request.quota in {"region_1", "region_2", "region_3"}:
            region = int(request.quota[-1])
        elif request.quota == "azad" and request.region_zone in {1, 2, 3}:
            region = int(request.region_zone)
    if region not in {1, 2, 3}:
        raise AdmissionInputError("region_zone در مسیر با آزمون باید ۱، ۲ یا ۳ باشد.")
    province = _canonical_province(request.province)
    if province is None:
        raise AdmissionInputError("استان نامعتبر است؛ یکی از ۳۱ استان استاندارد را انتخاب کنید.")
    return {
        "rank_in_quota": int(rank),
        "region_zone": int(region),
        "special_quota": special,
        "province": province,
        "diploma_type": request.diploma_type,
        "gpa_written": request.gpa_written if request.gpa_written is not None else request.gpa,
        "national_rank": request.national_rank,
    }


def _resolve_record_request(request: AdmissionChanceRequest) -> dict[str, Any]:
    province = _canonical_province(request.province)
    if province is None:
        raise AdmissionInputError("استان نامعتبر است؛ یکی از ۳۱ استان استاندارد را انتخاب کنید.")

    diploma = _canonical_diploma(request.diploma_type or "")
    if diploma not in DIPLOMA_VALUES:
        raise AdmissionInputError(
            "diploma_type باید یکی از riazi، tajrobi، ensani، maaref یا other_fani باشد."
        )
    _record_input_gpa(diploma, request.gpa_written, request.gpa_total)
    return {
        "diploma_type": diploma,
        "gpa_written": request.gpa_written,
        "gpa_total": request.gpa_total,
        "province": province,
        "target_field_group": request.target_field_group,
    }


router = APIRouter()


@router.post("/admission/chance")
def admission_chance(request: AdmissionChanceRequest) -> dict[str, Any]:
    try:
        path = _resolve_legacy_path(request)
        if not request.major_ids:
            raise AdmissionInputError("major_ids حداقل یک رشته را شامل شود.")

        if path == "exam":
            exam = _resolve_exam_request(request)
            items = build_exam_results(
                major_ids=request.major_ids,
                rank_in_quota=exam["rank_in_quota"],
                region_zone=exam["region_zone"],
                special_quota=exam["special_quota"],
                province=exam["province"],
                diploma_type=exam["diploma_type"],
                gpa_written=exam["gpa_written"],
                national_rank=exam["national_rank"],
                course_types=request.course_types,
                programs=load_programs(),
                limit=request.limit,
            )
            return {
                "admission_path": "exam",
                "items": items,
                "count": len(items),
                "context": {
                    "rank_in_quota": exam["rank_in_quota"],
                    "region_zone": exam["region_zone"],
                    "special_quota": exam["special_quota"],
                    "province": exam["province"],
                },
                "disclaimer": "نتایج تخمینی و جایگزین دفترچه و اعلام رسمی سنجش نیست.",
            }

        if path == "record":
            record = _resolve_record_request(request)
            items = build_record_results(
                major_ids=request.major_ids,
                diploma_type=record["diploma_type"],
                gpa_written=record["gpa_written"],
                gpa_total=record["gpa_total"],
                province=record["province"],
                target_field_group=record["target_field_group"],
                course_types=request.course_types,
                programs=load_programs(),
                majors=load_majors(),
                limit=request.limit,
            )
            return {
                "admission_path": "record",
                "items": items,
                "count": len(items),
                "context": {
                    "diploma_type": record["diploma_type"],
                    "province": record["province"],
                    "target_field_group": record["target_field_group"],
                },
                "disclaimer": "نتایج تخمینی و جایگزین دفترچه و اعلام رسمی سنجش نیست.",
            }

        raise AdmissionInputError("admission_path نامعتبر است.")

    except AdmissionInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="داده پذیرش دانشگاه در دسترس نیست") from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="داده پذیرش دانشگاه قابل استفاده نیست") from exc


def attach_router(target_router: APIRouter) -> None:
    target_router.include_router(router)
