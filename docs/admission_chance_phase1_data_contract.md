# Admission Chance — Phase 1 Data Contract Audit

## Source-of-truth refs

- `program2s.json` on `main`
  - blob SHA: `f0dba97099a93d9daa8698271730c9a386dc61ec`
  - metadata version: `5.2 Final`
  - last_updated: `1405-03-10`
- `majors_database_v2.json` on `main`
  - blob SHA: `c573c494e7c40bc9920b03734bd62698de455779`

## Parsed structure

The file parses as a JSON object with `metadata` and `programs`.

| Metric | Verified |
|---|---:|
| Programs | 4,150 |
| Unique program_id | 4,150 |
| Universities | 66 |
| Major IDs used by programs | 150 |
| Majors in majors_database_v2 | 160 |

All 150 unique `program2s.major_id` values are present in `majors_database_v2.id`; no unmapped IDs were found.

### admission_info

Every program (4,150/4,150) contains `admission_info` with:

- `method`: `با آزمون` or `سوابق تحصیلی`
- `course_type`
- `bomi_type`
- `diploma_requirements`
- `special_conditions`

Method distribution:

- `با آزمون`: 1,954
- `سوابق تحصیلی`: 2,196

Course types:

- `roozaneh`: 1,562
- `nobat_dovom`: 392
- `savabegh_dolati`: 580
- `azad`: 846
- `payam_noor`: 220
- `nonprofit`: 550

Bomi types:

- `ostani`: 3,154
- `ghotbi`: 561
- `keshvari`: 435

## Cutoff contract

For the 1,954 `با آزمون` programs:

- `cutoffs_historical`: available, years 1401–1404
- `cutoffs_bomi`: available, years 1401–1404
- `cutoffs_predicted_1405`: available

All three cutoff structures use the same six dimensions:

`zone_1`, `zone_2`, `zone_3`, `isargaran_25`, `isargaran_5`, `shahid`.

For the 2,196 `سوابق تحصیلی` programs:

- `cutoffs_historical`, `cutoffs_bomi`, and `cutoffs_predicted_1405` are absent.
- `cutoffs_savabegh` is present for all 2,196 records, with `minimum_gpa` and `minimum_traz`.

This confirms that the Phase-1 API must keep the two admission methods separate. For `با آزمون`, rank-vs-cutoff comparison is valid. For `سوابق تحصیلی`, no rank-vs-cutoff comparison should be fabricated.

## Bomi / province note for implementation

`admission_info.bomi_type` explicitly identifies `ostani`, `ghotbi`, or `keshvari`, and each program also carries `university.province`.

The dataset does **not** expose a separate province-to-`ghotbi` grouping table in the inspected program record structure. Therefore Phase 1 must not invent a province-group mapping. Any bomi selection logic must be explicit in code and limited to mappings supported by available data; otherwise the implementation should fall back conservatively rather than claim an unsupported official equivalence.

## Fixed dataset disclaimer

Source metadata states:

`⚠️ نتایج تخمینی و بر اساس مدل‌سازی آماری - برای استفاده در MVP`

The feature must not present a deterministic admission percentage or claim replacement of official Senjesh guidance.

## Scope lock

This audit is data-only. It does not modify:

- scoring/ranking or M-V-S weights
- `dark_horse_engine_v2.py`
- scientific reference JSONs
- Hybrid / migration cutover
- frontend behavior
