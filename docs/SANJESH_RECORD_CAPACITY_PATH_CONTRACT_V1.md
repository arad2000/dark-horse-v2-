# Sanjesh Record Capacity Direct-Source Contract v1

**Date:** 2026-09-29  
**Status:** contract proposal only — docs-only PR; not merged.  
**Scope:** `admission_path=record` direct read-only consumption of `docs/data/sanjesh_record_capacity_full.json`.

## 1. Purpose

The `record` admission path may serve capacity results directly from the Sanjesh record-capacity catalog instead of attempting to enrich `program2s` with `sanjesh_code` or capacity values.

This contract deliberately separates:

1. **capacity-row selection**, driven only by fields that actually exist in the capacity source; and
2. **existing program/scientific logic**, which remains outside this source path.

### Explicit scope locks

This contract does **not**:
- write `sanjesh_code` to `program2s`;
- write `capacity_total` to `program2s`;
- modify `dark_horse_engine_v2.py`;
- modify scoring, M-V-S weights, Hybrid, cutover, or frontend;
- change Section 2 geography rules for `program2s`;
- invent an `azad` period;
- introduce admission percentages or calibration.

## 2. Source of record

Record-capacity items are read from:

```text
docs/data/sanjesh_record_capacity_full.json
```

Observed source fields:

```text
sanjesh_code
major_name
capacity
period
gender
campus
province
group
page
quota_shares_mvp
```

The observed `period` values are exactly:

| period |
|---|
| روزانه |
| روزانه – غیردولتی |
| غیرانتفاعی |
| مجازی |
| نامشخص |
| نوبت دوم |
| پردیس خودگردان |
| پیام نور |

**Important:** `azad` is not an observed capacity `period` value and must not be invented or mapped into one.

## 3. Canonical major resolution

The request carries numeric `major_ids`.

Resolution source:

```text
majors_database_v2.json
```

For each requested `major_id`:

```text
major_id -> majors_database_v2[].name -> normalized major_name
```

Only an existing major record may produce a major-name filter. Unknown `major_id` values are not converted to guessed names.

A capacity row qualifies only when its normalized `major_name` equals one of the resolved normalized major names.

No fuzzy major-name matching is permitted in this path.

## 4. API request contract for admission_path=record

The request envelope is:

```json
{
  "admission_path": "record",
  "major_ids": [1, 23],
  "province": "تهران",
  "diploma_type": "tajrobi",
  "gpa": 18.25,
  "periods": ["روزانه", "نوبت دوم"],
  "special_quota": "isargaran_5"
}
```

### Required inputs

| Field | Meaning | Capacity-row effect |
|---|---|---|
| `admission_path` | must be `record` | selects this path |
| `major_ids` | requested majors | **filter** through `majors_database_v2.json` |
| `province` | user/application province | **filter** populated capacity province |
| `diploma_type` | diploma context | validation/context; not a capacity field |
| `gpa` | applicant GPA | validation/context; not a capacity field |
| `periods` | user-selected periods | **exact filter** on source `period` |

`special_quota` is accepted as **note-only** for this source path.

### GPA and diploma rule

Capacity rows contain no diploma or GPA field. Therefore this direct source path must **not** manufacture an eligibility calculation from `capacity`.

`diploma_type` and `gpa` may remain in the record request because they are part of the surrounding record-admission contract, but this capacity selector does not use them to alter, synthesize, or rank capacity rows.

Any future GPA/eligibility computation must be separately specified and sourced.

## 5. Period filtering

`periods` is a list of exact values from the observed capacity source.

The selector applies:

```text
row.period ∈ requested periods
```

No synonym-to-new-value conversion is performed inside the source loader.

Known exact source values include:

- `روزانه`
- `نوبت دوم`
- `پیام نور`
- `غیرانتفاعی`
- `مجازی`
- `پردیس خودگردان`
- `روزانه – غیردولتی`
- `نامشخص`

An omitted or empty `periods` list should not silently invent a default period. The API layer must either require an explicit selection or document an explicit all-period behavior before implementation.

## 6. Province filtering

Province matching is applied only against populated capacity `province` values.

Normalization may use the existing Persian-safe normalization convention (for example whitespace normalization and Arabic/Persian letter normalization) before equality comparison.

Rules:

1. populated `row.province` equal to the canonical request province -> eligible;
2. populated `row.province` different from the request province -> excluded;
3. blank `row.province` -> **not treated as a match** to any named province;
4. blank province is never filled or inferred from `campus`.

This prevents an empty source field from becoming an invented geographical match.

## 7. Capacity row selection pipeline

The read-only selection order is:

```text
request.major_ids
    ↓
majors_database_v2 major-name resolution
    ↓
exact normalized major_name filter
    ↓
exact period filter
    ↓
province equality filter on populated capacity province
    ↓
optional source-row validity checks
    ↓
response items
```

No program-side university join is required for this path.

In particular, `program2s.university.name`, `program2s.university_id`, `program_id`, and any program-side candidate composite are not used to manufacture a capacity linkage.

## 8. Response item contract

Each surviving capacity row is exposed without rewriting the source row:

```json
{
  "sanjesh_code": "18272",
  "major_name": "آمار",
  "campus": "استان ... - دانشگاه ...",
  "province": "تهران",
  "period": "روزانه",
  "capacity_total": 60,
  "quota_shares_mvp": {
    "capacity_total": 60,
    "isargaran_25": 15,
    "isargaran_5": 3,
    "remainder": 42,
    "free_seats": 8,
    "bomi_pool": 34,
    "free_share_rule": "20% after isargaran",
    "note": "..."
  },
  "notes": []
}
```

### Field provenance

| Output field | Source |
|---|---|
| `sanjesh_code` | capacity row |
| `major_name` | capacity row |
| `campus` | capacity row |
| `province` | capacity row |
| `period` | capacity row |
| `capacity_total` | capacity row `capacity` |
| `quota_shares_mvp` | capacity row, when present |
| `notes[]` | API contract / source-status notes |

`capacity_total` must be copied from the selected capacity row. It must never be inferred from `quota_shares_mvp` when the source `capacity` field exists.

## 9. No-result behavior

If no capacity row remains after the requested exact filters:

```json
{
  "admission_path": "record",
  "items": [],
  "count": 0,
  "context": {
    "major_ids": [1],
    "province": "تهران",
    "periods": ["روزانه"]
  },
  "notes": [
    "برای ترکیب رشته/استان/دوره انتخاب‌شده ردیف ظرفیت منطبق در منبع سنجش یافت نشد."
  ]
}
```

The API must not:
- fall back to fuzzy major matching;
- fall back from one period to another;
- invent an `azad` period;
- attach a program's historical cutoff to a capacity row;
- fill missing province from campus text.

## 10. Special quota semantics

`special_quota` is **note-only** in this direct capacity path.

It may be echoed in response context or produce a note explaining that the source contains quota-share metadata, but the API must not transform `special_quota` into a new capacity number unless a separate, explicit official calculation contract is approved.

The existing `quota_shares_mvp` object may be returned exactly as stored.

No bomi/region capacity split is invented from the `bomi_pool` note.

## 11. G1 / G2 / G3 applicability

This direct capacity source does not contain the full program-side geography/rule dimensions used by the existing `program2s` path.

Therefore, for this source path:

| Rule family | Capacity-path behavior |
|---|---|
| G1 | apply only when the rule is directly expressible from capacity-row fields; otherwise **not applied** and documented in `notes[]` |
| G2 | same rule: no program-side inference; otherwise **not applied** |
| G3 | same rule: no program-side inference; otherwise **not applied** |

The capacity path has no authority to modify or replace Section 2 geography behavior for `program2s`.

If a G-rule depends on a program-side university/program attribute that is absent from the capacity row, the rule is **not simulated** in this path.

## 12. Ordering and deduplication

The implementation must preserve source-row identity by `sanjesh_code`.

Because `sanjesh_code` is the source-row key:

- duplicate `sanjesh_code` rows must not be silently collapsed;
- any source duplicate must be surfaced as a data-integrity issue;
- no alternative synthetic key may replace `sanjesh_code`.

Any UI `limit` may truncate presentation only after the source filter is complete; truncation must not be described as the total number of matching capacity rows.

## 13. Non-goals

This contract does not define:

- probability/percentage of admission;
- calibration;
- score/ranking changes;
- program2s enrichment;
- official Sanjesh-code assignment to program records;
- Hybrid migration;
- PostgreSQL cutover;
- Section 2 rewrite;
- G1–G4 redesign;
- frontend implementation.

## 14. Acceptance criteria for the next implementation step

A future implementation PR must demonstrate, without modifying `program2s`:

1. source loader reads `sanjesh_record_capacity_full.json`;
2. major IDs resolve through `majors_database_v2.json`;
3. period filtering uses exact observed source values;
4. province matching excludes blank-province rows from named-province matches;
5. `special_quota` remains note-only;
6. returned `capacity_total` equals the selected capacity row's `capacity`;
7. zero-result responses contain an explicit note;
8. no `sanjesh_code` or capacity is written into `program2s`;
9. the existing program-based Section 2 path remains unchanged.

**Contract status: PROPOSED — supervisor approval required before Step 2 implementation.**
