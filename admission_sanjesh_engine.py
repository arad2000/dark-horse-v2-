"""Sanjesh-like university admission selection engine.

Pure admission-data logic. This module is isolated from Dark Horse
individuality scoring/ranking, Hybrid and PostgreSQL runtime cutover.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

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
# Backward-compatible aliases; API outputs the three qualitative labels above.
RECORD_ABOVE_LABEL = HIGHER_LABEL
RECORD_AT_MIN_LABEL = BORDERLINE_LABEL
RECORD_BELOW_LABEL = LOWER_LABEL

EXAM_METHOD = "با آزمون"
RECORD_METHOD = "سوابق تحصیلی"

GHOTBI_NOTE = "اعمال بومی قطبی/ناحیه‌ای ناقص است"
OSTANI_MISMATCH_NOTE = "بومی استانی فقط در صورت تطابق استان داوطلب و محل تحصیل اعمال شد."
SPECIAL_QUOTA_NOTE = (
    "این مقایسه فعلاً روی dimension سهمیه خاص انتخاب‌شده انجام شده است؛ "
    "رتبه منطقه نیز دریافت شده اما در این مقایسه cutoff منطقه ملاک label نیست."
)
SPECIAL_QUOTA_FALLBACK_NOTE = (
    "برای سهمیه خاص انتخاب‌شده در این برنامه cutoff مستقل موجود نبود؛ "
    "برای جلوگیری از fallback بی‌صدا، cutoff منطقه با ذکر این note استفاده شد."
)
SPECIAL_QUOTA_THRESHOLD_NOTE = (
    "حدنصاب کامل سهمیه خاص در این نسخه اعمال نشده است؛ قاعده سال هدف در داده/قرارداد مستند موجود نیست."
)
CUTOFF_DIMENSION_MISSING_NOTE = (
    "برای بعد cutoff انتخاب‌شده در داده برنامه cutoff قابل استفاده موجود نیست."
)
RECORD_COEFFICIENT_NOTE = (
    "ضریب پایه جدول نوع دیپلم/گروه تحصیلی اعمال شد؛ استثناهای موردی سنجش "
    "فقط در صورت وجود نگاشت رسمی در داده منبع قابل اعمال هستند."
)

AZAD_RECORD_NOTE = "سامانه آزاد؛ بومی‌گزینی سراسری کامل نیست"

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

# Official 1404 record-admission exception: for the explicitly listed
# humanities programs, a Math/Experimental diploma uses coefficient 100
# instead of the base humanities-group coefficient 57.1.
GPA_HUMANITIES_RIAZI_TAJROBI_100 = {
    "حسابداری",
    "اقتصاد",
    "روانشناسی",
    "علوم ورزشی",
    "مدیریت امور بانکی",
    "مدیریت صنعتی",
    "مدیریت مالی",
    "مدیریت بازرگانی",
    "مدیریت و بازرگانی دریایی",
    "مدیریت بیمه",
    "مدیریت دولتی",
    "مدیریت امور گمرکی",
    "مدیریت فرهنگی هنری",
    "مدیریت کسب و کار",
    "هتلداری",
    "علم اطلاعات و دانش شناسی",
    "گردشگری",
    "کاردانی مدیریت صنعتی کاربردی",
    "کاردانی امور بانکی",
    "کاردانی بیمه",
    "کاردانی امور دولتی",
    "کاردانی امور مالی و مالیاتی",
}


def _major_name_matches_gpa_exception(
    major_id: Any,
    majors: dict[str, dict[str, Any]] | None,
) -> bool:
    if not majors:
        return False
    major = majors.get(str(major_id))
    if not isinstance(major, dict):
        return False
    name = _normalize_text(major.get("name"))
    if not name:
        return False
    name = " ".join(name.replace("\u200c", " ").split())
    return name in GPA_HUMANITIES_RIAZI_TAJROBI_100

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


BOMI_TABLE5_PATH = ROOT / "docs" / "sanjesh_table5_major_bomi_v1.json"
BOMI_GEOGRAPHY_PATH = ROOT / "docs" / "bomi_geography_v1.json"

@lru_cache(maxsize=1)
def load_bomi_table5() -> dict[str, Any]:
    payload = json.loads(BOMI_TABLE5_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("docs/sanjesh_table5_major_bomi_v1.json structure is unsupported")
    period_defaults = payload.get("period_defaults")
    daily_major_bomi = payload.get("daily_major_bomi")
    name_aliases = payload.get("name_aliases")
    if not isinstance(period_defaults, dict) or not isinstance(daily_major_bomi, dict) or not isinstance(name_aliases, dict):
        raise RuntimeError("Table 5 bomi mapping sections are missing or invalid")
    return {
        "period_defaults": period_defaults,
        "daily_major_bomi": daily_major_bomi,
        "name_aliases": name_aliases,
    }


@lru_cache(maxsize=1)
def load_bomi_geography() -> dict[str, dict[str, int | str]]:
    payload = json.loads(BOMI_GEOGRAPHY_PATH.read_text(encoding="utf-8"))
    provinces = payload.get("provinces") if isinstance(payload, dict) else None
    if not isinstance(provinces, dict):
        raise RuntimeError("docs/bomi_geography_v1.json structure is unsupported")

    mapping: dict[str, dict[str, int | str]] = {}
    for raw_name, item in provinces.items():
        if not isinstance(item, dict):
            continue
        name = _canonical_province(raw_name)
        if not name:
            continue
        nahiye = item.get("nahiye_id")
        ghotb = item.get("ghotb_id")
        if not isinstance(nahiye, int) or nahiye not in range(1, 10):
            raise RuntimeError(f"invalid nahiye_id for {name}")
        if not isinstance(ghotb, int) or ghotb not in range(1, 6):
            raise RuntimeError(f"invalid ghotb_id for {name}")
        mapping[name] = {
            "nahiye_id": nahiye,
            "ghotb_id": ghotb,
            "nahiye_name": str(item.get("nahiye_name") or f"ناحیه {nahiye}"),
            "ghotb_name": str(item.get("ghotb_name") or f"قطب {ghotb}"),
        }

    if len(mapping) != 31:
        raise RuntimeError(f"expected 31 provinces, got {len(mapping)}")
    return mapping


def _normalize_bomi_type(value: Any) -> str | None:
    key = _normalize_text(value).replace("ى", "ی")
    aliases = {
        "ostani": "ostani",
        "استانی": "ostani",
        "nahiyei": "nahiyei",
        "nahieyi": "nahiyei",
        "ناحیه ای": "nahiyei",
        "ناحیه‌ای": "nahiyei",
        "ghotbi": "ghotbi",
        "قطبی": "ghotbi",
        "keshvari": "keshvari",
        "کشوری": "keshvari",
    }
    return aliases.get(key)


def _course_type_text(program: dict[str, Any]) -> str:
    admission = program.get("admission_info", {}) or {}
    return _normalize_text(admission.get("course_type") or program.get("course_type"))

def _is_azad_program(program: dict[str, Any]) -> bool:
    """Detect an explicitly named Azad institution/course without changing eligibility."""
    admission = program.get("admission_info", {}) or {}
    university = program.get("university", {}) or {}
    candidates = [
        university.get("name"),
        program.get("university_name"),
        admission.get("institution_name"),
        admission.get("institution"),
        admission.get("provider_name"),
        admission.get("course_type"),
        program.get("course_type"),
    ]
    for value in candidates:
        text = _normalize_text(value)
        if not text:
            continue
        if "دانشگاه آزاد" in text or "آزاد اسلامی" in text:
            return True
        if re.search(r"(?<![a-z0-9])azad(?![a-z0-9])", text):
            return True
    return False


def _bomi_lookup_key(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "", _normalize_text(value))


def _resolve_record_bomi(
    program: dict[str, Any],
    majors: dict[str, dict[str, Any]],
) -> tuple[str | None, str]:
    table5 = load_bomi_table5()
    course_key = _bomi_lookup_key(_course_type_text(program))
    is_azad = _is_azad_program(program)

    period_defaults = {
        _bomi_lookup_key(key): _normalize_bomi_type(value)
        for key, value in table5["period_defaults"].items()
        if _normalize_bomi_type(value)
    }
    if course_key in period_defaults:
        return period_defaults[course_key], "period_defaults"

    if not is_azad and course_key in {
        _bomi_lookup_key("savabegh_dolati"),
        _bomi_lookup_key("roozaneh"),
    }:
        major = majors.get(str(program.get("major_id")))
        major_name = _normalize_text(major.get("name")) if isinstance(major, dict) else ""
        aliases = {
            _normalize_text(alias): _normalize_text(target)
            for alias, target in table5["name_aliases"].items()
        }
        canonical_name = aliases.get(major_name, major_name)
        daily_map = {
            _normalize_text(name): _normalize_bomi_type(value)
            for name, value in table5["daily_major_bomi"].items()
            if _normalize_bomi_type(value)
        }
        bomi_type = daily_map.get(canonical_name)
        if bomi_type:
            return bomi_type, "table5_daily"
        return None, "unresolved_table5"

    if is_azad:
        return None, "azad_unresolved"

    return None, "unresolved_bomi"

def _record_locality_match(
    program: dict[str, Any],
    candidate_province: str,
    region_zone: int,
    bomi_type: str | None,
    geography: dict[str, dict[str, int | str]],
) -> tuple[bool, list[str]]:
    university = program.get("university", {}) or {}
    university_province = _canonical_province(university.get("province"))
    candidate = geography.get(candidate_province)
    target = geography.get(university_province) if university_province else None
    notes: list[str] = []

    if not candidate or not target:
        notes.append("نگاشت بومی رسمی برای استان داوطلب یا محل دانشگاه در داده موجود نیست؛ فیلتر بومی برای این برنامه اعمال نشد.")
        return True, notes

    if bomi_type == "ostani":
        ok = candidate_province == university_province
        notes.append(
            "بومی استانی: استان داوطلب با استان محل دانشگاه تطابق دارد."
            if ok else
            "بومی استانی: استان داوطلب با استان محل دانشگاه تطابق ندارد."
        )
        return ok, notes

    if bomi_type == "nahiyei":
        ok = int(candidate["nahiye_id"]) == int(target["nahiye_id"])
        notes.append(
            f"بومی ناحیه‌ای: ناحیه داوطلب {candidate['nahiye_id']} و ناحیه دانشگاه {target['nahiye_id']}."
        )
        return ok, notes

    if bomi_type == "ghotbi":
        ok = int(candidate["ghotb_id"]) == int(target["ghotb_id"])
        notes.append(
            f"بومی قطبی: قطب داوطلب {candidate['ghotb_id']} و قطب دانشگاه {target['ghotb_id']}."
        )
        return ok, notes

    if bomi_type == "keshvari":
        notes.append("بومی کشوری: فیلتر استان/ناحیه/قطب اعمال نشد.")
        return True, notes

    notes.append("نوع بومی برنامه از منبع/نگاشت قابل استنتاج نشد؛ فیلتر بومی اعمال نشد.")
    return True, notes


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


def normalize_diploma_requirements(raw: Any) -> dict[str, Any]:
    """Normalize production and legacy diploma requirement shapes."""
    if isinstance(raw, dict):
        return {
            "accepts_diploma_types": raw.get("accepts_diploma_types") or raw.get("types") or [],
            "is_floating": bool(raw.get("is_floating", False)),
        }
    if isinstance(raw, list):
        return {"accepts_diploma_types": raw, "is_floating": False}
    return {"accepts_diploma_types": [], "is_floating": False}


def _diploma_matches(program: dict[str, Any], diploma_type: str | None) -> bool:
    if not diploma_type:
        return True
    raw = (program.get("admission_info") or {}).get("diploma_requirements")
    required = normalize_diploma_requirements(raw)
    accepts = required["accepts_diploma_types"]
    if not isinstance(accepts, list):
        return True

    wanted = _canonical_diploma(diploma_type)
    allowed = {
        _canonical_diploma(str(item))
        for item in accepts
        if isinstance(item, str)
    }
    if not allowed:
        return True
    if wanted in allowed:
        return True

    normalized_allowed = {_normalize_text(str(item)) for item in accepts if isinstance(item, str)}
    return bool(
        any(marker in value for marker in ("همه", "تمام", "کلیه") for value in normalized_allowed)
    )


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



def _program_matches_locality(program: dict[str, Any], province: str) -> bool:
    """Apply only locality rules directly represented in program2s."""
    admission = program.get("admission_info", {}) or {}
    bomi_type = _normalize_text(admission.get("bomi_type"))
    if bomi_type != "ostani":
        # ghotbi/nahieyi have no official province mapping here; keep them
        # eligible and disclose the limitation in notes instead.
        return True

    university = program.get("university", {}) or {}
    program_province = _canonical_province(university.get("province"))
    candidate_province = _canonical_province(province)
    # Never infer locality when either side is missing/unknown.
    return bool(program_province and candidate_province and program_province == candidate_province)


def _locality_notes(program: dict[str, Any], province: str) -> list[str]:
    admission = program.get("admission_info", {}) or {}
    bomi_type = _normalize_text(admission.get("bomi_type"))
    university = program.get("university", {}) or {}
    notes: list[str] = []

    if bomi_type == "ostani":
        university_province = _canonical_province(university.get("province"))
        if university_province == province:
            notes.append("بومی استانی مطابق استان محل دانشگاه و استان داوطلب در داده اعمال شد.")
        else:
            notes.append("بومی استانی برای این برنامه با استان داوطلب تطابق ندارد.")
    elif bomi_type in {"ghotbi", "nahieyi"}:
        notes.append(GHOTBI_NOTE)
    elif bomi_type == "keshvari":
        notes.append("بومی کِشوری است؛ تفاوت بومی استانی/قطبی برای این برنامه اعمال نشد.")

    notes.append("ظرفیت تفکیکی در داده نیست")
    return notes


def _exam_cutoff(
    program: dict[str, Any],
    *,
    cutoff_dimension: str,
    region_dimension: str,
    special_quota: str,
    province: str,
) -> tuple[int | float | None, int | None, str, list[str]]:
    notes = _locality_notes(program, province)
    if special_quota != "none":
        notes.append("dimension سهمیه خاص مستقل از منطقه انتخاب شد؛ رتبه منطقه جایگزین آن نیست.")
        notes.append(SPECIAL_QUOTA_THRESHOLD_NOTE)
    requested_dimension = cutoff_dimension

    # Policy: never prefer or use cutoffs_bomi without an independently
    # verified official source. Prefer predicted-1405, then latest historical.
    predicted = program.get("cutoffs_predicted_1405")
    cutoff = _cutoff_from_dimension(predicted, requested_dimension)
    if cutoff is not None:
        return cutoff, 1405, requested_dimension, notes

    historical = program.get("cutoffs_historical")
    cutoff, year = _latest_historical_cutoff(historical, requested_dimension)
    if cutoff is not None:
        return cutoff, year, requested_dimension, notes

    # Special quota remains a separate dimension. If that dimension is absent,
    # disclose an explicit fallback to the region dimension.
    if special_quota != "none" and requested_dimension != region_dimension:
        cutoff = _cutoff_from_dimension(predicted, region_dimension)
        if cutoff is not None:
            notes.append("برای سهمیه خاص انتخاب‌شده cutoff مستقل در داده موجود نبود؛ cutoff منطقه با fallback مستند استفاده شد.")
            return cutoff, 1405, region_dimension, notes

        cutoff, year = _latest_historical_cutoff(historical, region_dimension)
        if cutoff is not None:
            notes.append("برای سهمیه خاص انتخاب‌شده cutoff مستقل در داده موجود نبود؛ cutoff تاریخی منطقه با fallback مستند استفاده شد.")
            return cutoff, year, region_dimension, notes

    notes.append("برای بعد cutoff انتخاب‌شده در داده برنامه cutoff قابل استفاده موجود نیست.")
    return None, None, requested_dimension, notes

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
    if minimum_gpa is None or gpa_effective is None:
        return LOWER_LABEL
    if gpa_effective > minimum_gpa:
        return HIGHER_LABEL
    if gpa_effective == minimum_gpa:
        return BORDERLINE_LABEL
    return LOWER_LABEL


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


def _coefficient(
    diploma_type: str,
    target_group: str,
    *,
    major_id: Any = None,
    majors: dict[str, dict[str, Any]] | None = None,
) -> float:
    base = GPA_COEFFICIENTS[diploma_type][target_group]
    if (
        diploma_type in {"riazi", "tajrobi"}
        and target_group == "ensani"
        and _major_name_matches_gpa_exception(major_id, majors)
    ):
        return 100.0
    return base


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

    filtered = [
        program
        for program in filter_programs(
            programs,
            major_ids=major_ids,
            course_types=course_types,
            admission_method=EXAM_METHOD,
        )
        if _program_matches_locality(program, province)
    ]

    results: list[dict[str, Any]] = []
    for program in filtered:
        cutoff, cutoff_year, used_dimension, notes = _exam_cutoff(
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
        item["notes"] = list(notes)
        item["note"] = " | ".join(notes) if notes else None
        if special_quota != "none":
            item["special_quota"] = special_quota
        if diploma_type:
            item["diploma_type"] = diploma_type
        if gpa_written is not None:
            item["gpa_input"] = float(gpa_written)
            gpa_note = "اثر معدل در مسیر کنکور داخل رتبه/فرآیند سنجش داوطلب است؛ برای مقایسه cutoff این سرویس از رتبه در سهمیه استفاده می‌کند."
            item["note_gpa"] = gpa_note
            item["notes"].append(gpa_note)
            item["note"] = " | ".join(item["notes"])
        if national_rank is not None:
            item["national_rank_input"] = int(national_rank)
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
    region_zone: int = 2,
    special_quota: str = "none",
    traz: float | None = None,
) -> list[dict[str, Any]]:
    gpa_input, gpa_field = _record_input_gpa(diploma_type, gpa_written, gpa_total)
    canonical_province = _canonical_province(province)
    if canonical_province is None:
        raise AdmissionInputError("استان نامعتبر است.")
    if region_zone not in {1, 2, 3}:
        raise AdmissionInputError("region_zone در مسیر سوابق باید ۱، ۲ یا ۳ باشد.")
    special = _normalize_text(special_quota or "none")
    if special not in {"none", "isargaran_25", "isargaran_5", "shahid"}:
        raise AdmissionInputError("special_quota نامعتبر است.")

    geography = load_bomi_geography()
    filtered = filter_programs(
        programs,
        major_ids=major_ids,
        diploma_type=diploma_type,
        course_types=course_types,
        admission_method=RECORD_METHOD,
    )

    results: list[dict[str, Any]] = []
    for program in filtered:
        bomi_type, bomi_source = _resolve_record_bomi(program, majors)
        if bomi_source == "unresolved_table5":
            continue
        matches, locality_notes = _record_locality_match(
            program,
            canonical_province,
            region_zone,
            bomi_type,
            geography,
        )
        if not matches:
            continue

        target_group = _record_target_group(
            explicit_target=target_field_group,
            major_id=program.get("major_id"),
            majors=majors,
        )
        coefficient = _coefficient(diploma_type, target_group, major_id=program.get("major_id"), majors=majors)
        effective = round(gpa_input * coefficient / 100.0, 4)

        academic_cutoff = _academic_cutoff(program)
        minimum_gpa = academic_cutoff["minimum_gpa"]
        minimum_traz = academic_cutoff["minimum_traz"]

        # G2 policy: compare the program minimum GPA against the raw GPA
        # selected by diploma type. GPA coefficients are a separate G3 rule.
        if minimum_gpa is not None and gpa_input < minimum_gpa:
            continue

        # G2 policy: no traz means no minimum_traz filter; when traz is
        # supplied, values below the program threshold are excluded.
        if minimum_traz is not None and traz is not None and traz < minimum_traz:
            continue

        course_type = (program.get("admission_info") or {}).get("course_type") or program.get("course_type")

        notes = [
            RECORD_COEFFICIENT_NOTE,
            *locality_notes,
            f"نوع بومی: {bomi_type or 'نامشخص'}؛ منبع نگاشت: {bomi_source}.",
            "ظرفیت تفکیکی در داده نیست؛ قاعده ظرفیت صفحه ۸ دفترچه در این نسخه فقط به‌عنوان قرارداد/یادداشت حفظ شد.",
            "حداقل تراز در داده برنامه ثبت شده، اما ورودی تراز داوطلب در قرارداد مسیر سوابق وجود ندارد؛ بنابراین مقایسه تراز انجام نشد.",
            f"region_zone={region_zone} در قرارداد مسیر سوابق حفظ شد و برای تقسیم ظرفیت نگه‌داری می‌شود؛ رتبه از این مسیر استفاده نمی‌شود.",
        ]
        if special != "none":
            notes.append(
                "سهمیه خاص در داده سوابق این رشته‌محل ثبت نشده و در این نسخه فقط به‌عنوان context نگه‌داری شد؛ "
                "فیلتر/حدنصاب سهمیه‌ای در مسیر record اعمال نشد."
            )
        if _is_azad_program(program):
            notes.append(AZAD_RECORD_NOTE)
        if bomi_type is None:
            notes.append("برای این برنامه نوع گزینش بومی از منبع قابل استنتاج نشد؛ هیچ نگاشت جغرافیایی حدسی اعمال نشد.")
        if minimum_traz is not None and traz is None:
            notes.append("تراز اعلام نشده؛ فیلتر حداقل تراز برای این برنامه اعمال نشد.")

        item = {
            "program_id": program.get("program_id"),
            "university_name": (program.get("university") or {}).get("name") or program.get("university_name") or "",
            "major_id": int(program.get("major_id")),
            "course_type": course_type,
            "method": RECORD_METHOD,
            "cutoff_dimension": None,
            "cutoff_used": academic_cutoff,
            "label": _record_label(effective, minimum_gpa),
            "gpa_input": gpa_input,
            "gpa_input_field": gpa_field,
            "traz_input": traz,
            "gpa_coefficient": coefficient,
            "gpa_effective": effective,
            "minimum_gpa": minimum_gpa,
            "minimum_traz": minimum_traz,
            "target_field_group": target_group,
            "province": canonical_province,
            "region_zone": region_zone,
            "special_quota": special,
            "bomi_type": bomi_type,
            "bomi_source": bomi_source,
            "notes": notes,
            "note": " | ".join(notes),
        }
        results.append(item)
        if len(results) >= limit:
            break
    return results
