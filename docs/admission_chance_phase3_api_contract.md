# Admission Chance — Phase 3 API contract

## Two explicit admission paths

POST /api/v1/admission/chance

Canonical requests use:
- admission_path: "exam" for با آزمون
- admission_path: "record" for صرفاً سوابق تحصیلی

The previous exam-oriented payload remains accepted as a compatibility envelope.

## Exam path

Required:
- major_ids
- rank_in_quota
- region_zone: 1, 2, or 3
- province: one of the 31 canonical provinces

Optional:
- special_quota: none | isargaran_25 | isargaran_5 | shahid
- national_rank
- course_types
- diploma_type
- gpa_written

The exam path filters to method = با آزمون.

region_zone is always a separate input from special_quota.

Cutoff rules:
- region_1/2/3 map to zone_1/2/3.
- When a selected special quota has its own dimension in program2s, that dimension is used.
- The response exposes cutoff_dimension and cutoff_used.
- When a special-quota dimension is absent, the service may use the region dimension only with an explicit note. There is no silent fallback.
- Matching provincial bomi data is preferred when bomi_type=ostani, the applicant province equals the university province, and cutoffs_bomi exists.
- ghotbi keeps the conservative official-mapping warning.
- gpa_written is informational on the exam path; the rank label is based on rank_in_quota and cutoff, not GPA.

The service remains qualitative and does not return a deterministic admission percentage.

## Record path

Required:
- major_ids
- province
- diploma_type
- the GPA field appropriate to diploma type:
  - theoretical diplomas (riazi, tajrobi, ensani, maaref) require gpa_written
  - technical/knowledge-skill diplomas (other_fani) require gpa_total

Optional:
- course_types
- target_field_group: riazi | tajrobi | ensani | honar | zaban

When target_field_group is omitted, it is inferred from majors_database_v2.exam_group for each returned major. If a major cannot be mapped, the request fails with an explicit 400 asking for target_field_group.

The record path filters to method = سوابق تحصیلی only.

### Base GPA coefficient matrix

| diploma | ریاضی | تجربی | انسانی | هنر | زبان |
|---|---:|---:|---:|---:|---:|
| ریاضی‌فیزیک | 100 | 100 | 57.1 | 100 | 100 |
| تجربی | 100 | 100 | 57.1 | 100 | 100 |
| انسانی | 57.1 | 57.1 | 100 | 100 | 100 |
| معارف | 57.1 | 57.1 | 100 | 100 | 100 |
| سایر/فنی | 51.4 | 51.4 | 51.4 | 100 | 100 |

For a record result:
gpa_effective = input_gpa × (gpa_coefficient / 100)

The response includes:
- gpa_input
- gpa_coefficient
- gpa_effective
- cutoff_used
- target_field_group

No rank is used in record labeling.

The code explicitly notes that special case rules from official guidance are not fabricated when a machine-readable official mapping is absent; only the base matrix is applied.

## Source note

The coefficient matrix is consistent with published reproductions of the historic admission-with-records guidance, including the 57.1 / 51.4 structure. The current official Sanjesh page/PDF for the exact year was not retrievable through the available index during this implementation pass, so the implementation does not claim that the table is a freshly verified current-year official table.

## Scope lock

This phase changes only the admission-chance API module, its regression test, and this contract document.

It does not modify:
- dark_horse_engine_v2.py
- scientific JSONs
- scoring weights / M-V-S
- Hybrid
- PostgreSQL runtime cutover
