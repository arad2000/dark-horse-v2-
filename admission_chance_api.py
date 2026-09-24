"""Phase 2 admission chance API facade.

The Sanjesh-like selection logic lives in admission_sanjesh_engine.py.
This API layer only validates/normalizes the HTTP contract and mounts the route.
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from admission_sanjesh_engine import (
    AdmissionInputError,
    DIPLOMA_VALUES,
    PROVINCE_OPTIONS,
    QUOTA_DIMENSIONS,
    _canonical_diploma,
    _canonical_province,
    _normalize_text,
    _record_input_gpa,
    build_exam_results,
    build_record_results,
    load_majors,
    load_programs,
)

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
    special_quota: str = Field(
        default="none",
        description="سهمیه خاص؛ از سهمیه منطقه جداست.",
        json_schema_extra={"enum": ["none", "isargaran_25", "isargaran_5", "shahid"]},
    )
    province: str | None = Field(
        default=None,
        max_length=64,
        description="استان بومی؛ یکی از ۳۱ استان استاندارد.",
        json_schema_extra={"enum": list(PROVINCE_OPTIONS)},
    )
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
    if special == "none" and request.quota in {"isargaran_25", "isargaran_5", "shahid"}:
        special = str(request.quota)

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
