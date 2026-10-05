# SANJESH Ensani 1405 — Data Contract / Phase 0

## Scope

Phase 0 only: source-data audit and a reproducible audit script for the 1405 **ensani** program dataset.

Source:
- `docs/data/sanjesh_ensani_1405_programs.json`
- year: **1405**
- group: **ensani**
- source blob SHA audited: `54b343685cfd1e07365e7a8b03e6974ee2383198`

This artifact does **not** switch any Loader or `CAPACITY_PATHS`, and does not change scoring, engine, Hybrid, majors data, API, or UI.

## Required fields

The audited 1405 source rows contain these required fields:

`sanjesh_code`, `major_name`, `campus`, `province`, `period`, `capacity`, `admission_type`, `note`, `page`, `year`, `group`

Observed extra field preserved in the source:
- `gender`

## Baseline — Ensani 1405

| Metric | Value |
|---|---:|
| Total rows | 10,502 |
| Unique Sanjesh codes | 10,502 |
| Blank Sanjesh codes | 0 |
| Duplicate code values | 0 |
| Duplicate code rows | 0 |
| با آزمون | 1,502 |
| صرفاً سوابق | 9,000 |
| `period=نامشخص` | 7,564 |
| Blank province | 158 |
| Page range | 46–572 |
| Distinct pages | 273 |
| Year values | 1405 only |
| Group values | ensani only |

## Reported overlap

Comparison source:
`docs/data/sanjesh_ensani_1404_programs.json`

- Shared `sanjesh_code`: **9,480**
- Shared normalized row signatures using
  `major_name + campus + province + period + admission_type`: **63**
- 1405-only normalized signatures: **7,597**

Record-capacity source:
`docs/data/sanjesh_record_capacity_full.json`

- Record-capacity rows: **8,350**
- Record-capacity unique codes: **8,350**
- Shared `sanjesh_code`: **7,957**
- Shared normalized signatures using
  `major_name + campus + province + period`: **19**

The code-overlap figures and signature-overlap figures are intentionally reported separately; they are not equivalent measures.

## Phase-0 constraints

- No Loader switch to 1405.
- No `CAPACITY_PATHS` switch.
- No scoring/ranking/engine/Hybrid changes.
- No changes to `majors_database_v2.json` or other protected scientific data.
- Source JSON is audit input only; this PR does not rebuild or modify it.
