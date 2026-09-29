# Sanjesh Record Capacity — Join Pilot v1

**Date:** 2026-09-29  
**Scope:** Step B — read-only candidate join experiment.  
**Base:** `deploy/liara-commercial-sandbox@49d3b6640bbfba2c7870ed67bc6520865198adc7`

## 1. Hard guardrails

This pilot only computes candidate joins in memory and records the result.

- **No write to `program2s.json`.**
- No capacity enrichment.
- No engine/scoring/Section 2/G1–G4 changes.
- No Hybrid/cutover/frontend changes.
- No fuzzy matching.
- No synthetic or inferred `sanjesh_code`.
- Ambiguous and unmatched rows are never filled.

## 2. Source revisions

| Source | Revision |
|---|---|
| `program2s.json` | `0c2747057a35f3fdf4aa70c178ed68580e7c4537` |
| `majors_database_v2.json` | `c573c494e7c40bc9920b03734bd62698de455779` |
| `docs/data/sanjesh_record_capacity_full.json` | `8a5efdb3c19576ed3557107f13ebb74d2681eebd` |

## 3. Record population and major_id resolution

- Total `program2s` programs: **4,150**
- Record (`method = سوابق تحصیلی`) programs: **2,196**
- Unique record `major_id` values: **147**
- Record programs whose `major_id` is absent from `majors_database_v2.json`: **0 / 2,196**

Thus the `major_id → major name` step is fully resolvable from the existing majors database. No name was invented.

## 4. Course-type / method → capacity-period mapping

Actual record-side `course_type` values:

| Record `course_type` | Record programs | Pilot mapping |
|---|---:|---|
| `payam_noor` | 220 | **→ پیام نور** |
| `nonprofit` | 550 | **→ غیرانتفاعی** |
| `savabegh_dolati` | 580 | **No deterministic period mapping** |
| `azad` | 846 | **No corresponding period value in capacity** |

Capacity-side observed `period` values are:
- روزانه
- نوبت دوم
- پیام نور
- غیرانتفاعی
- مجازی
- روزانه – غیردولتی
- پردیس خودگردان
- نامشخص

### Why `savabegh_dolati` is not mapped

For record programs with `course_type = savabegh_dolati`, using the other exact join dimensions (major name + province + exact university-name containment in campus) produced observed capacity periods:

| Observed period | Candidate rows |
|---|---:|
| روزانه | 24 |
| نوبت دوم | 15 |

Therefore the available data does **not** establish a one-to-one mapping from `savabegh_dolati` to one capacity `period`. Mapping it to either period would be an inference and is excluded.

### Why `azad` is not mapped

`azad` occurs in 846 record programs, but **آزاد** is not one of the actual capacity `period` values listed above. No new value is invented.

So the deterministic Step-B join domain is:

- **770 record programs** = `payam_noor` + `nonprofit`
- **1,426 record programs** are outside the deterministic period-join domain:
  - 580 `savabegh_dolati`
  - 846 `azad`

## 5. Deterministic university and province test

The pilot uses:

1. `major_id` → exact name from `majors_database_v2.json`.
2. Exact normalized `major_name` equality.
3. Exact normalized mapped `period` equality.
4. Exact normalized province equality.
5. University gate: normalized `program2s.university.name` must occur as an **exact substring** inside normalized `capacity.campus`.

Normalization is limited to:
- Unicode NFKC
- remove ZWJ/ZWNJ/BOM
- `ي/ى → ی`
- `ك → ک`
- remove Arabic diacritics
- collapse whitespace
- trim

There is **no similarity score, edit distance, token similarity, fuzzy threshold, alias invention, or manual university-name substitution**.

## 6. Join-pilot result for record path

### 6.1 Program-side result

| Metric | Result |
|---|---:|
| Total record programs | **2,196** |
| Period-mappable record programs | **770** |
| Period-unmapped / outside deterministic pilot | **1,426** |
| Candidate join pairs produced | **0** |
| Programs with ≥1 candidate | **0** |
| Matched unique 1:1 programs | **0** |
| Ambiguous programs | **0** |
| Unmatched programs inside deterministic pilot | **770 / 770** |

The zero candidate-pair result occurs **after** the major, period, province and deterministic university checks.

### 6.2 Capacity-side result

The deterministic pilot period domain is:

- پیام نور
- غیرانتفاعی

Capacity rows in this domain: **6,686**

Of these:
- blank province: **27**
- candidate-linked rows: **0**
- unmatched capacity rows: **6,686**

The full capacity file contains **8,350** rows. The other **1,664** rows use periods for which the record-side pilot has no deterministic period mapping, so they are outside this Step-B join domain rather than being treated as program matches.

### 6.3 Overall ambiguity

Within the deterministic join graph:

- program → multiple capacity: **0**
- capacity → multiple program: **0**
- ambiguous joined pairs: **0**

The earlier capacity-side composite audit still reports ambiguity in the raw `major_name + period + province + campus` key, but none of those rows reaches a valid program-side candidate under the stricter record pilot.

## 7. Effect of blank province

Across all 8,350 capacity rows:
- blank province: **330**

Within the deterministic record-period domain:
- blank province: **27 / 6,686**

Those 27 rows fail the province equality gate automatically. They are not guessed or reassigned.

The remaining 303 blank-province capacity rows are outside the current record-period domain.

## 8. Five raw unmatched program examples

No matched sample exists because the pilot produced **0 matches**. Five unmatched raw program keys are shown instead.

### Example 1

| Field | Raw value |
|---|---|
| program_id | `PROG_03158` |
| university_id | `PNU_T` |
| university.name | دانشگاه پیام نور تهران |
| university.province | تهران |
| major_id | `41` |
| major name from majors DB | مهندسی برق |
| course_type | `payam_noor` |
| method | سوابق تحصیلی |
| mapped period | پیام نور |

### Example 2

| Field | Raw value |
|---|---|
| program_id | `PROG_03159` |
| university_id | `PNU_T` |
| university.name | دانشگاه پیام نور تهران |
| university.province | تهران |
| major_id | `42` |
| major name from majors DB | مهندسی کامپیوتر |
| course_type | `payam_noor` |
| method | سوابق تحصیلی |
| mapped period | پیام نور |

### Example 3

| Field | Raw value |
|---|---|
| program_id | `PROG_03160` |
| university_id | `PNU_T` |
| university.name | دانشگاه پیام نور تهران |
| university.province | تهران |
| major_id | `43` |
| major name from majors DB | مهندسی فناوری اطلاعات |
| course_type | `payam_noor` |
| method | سوابق تحصیلی |
| mapped period | پیام نور |

### Example 4

| Field | Raw value |
|---|---|
| program_id | `PROG_03161` |
| university_id | `PNU_T` |
| university.name | دانشگاه پیام نور تهران |
| university.province | تهران |
| major_id | `44` |
| major name from majors DB | مهندسی نرم‌افزار |
| course_type | `payam_noor` |
| method | سوابق تحصیلی |
| mapped period | پیام نور |

### Example 5

| Field | Raw value |
|---|---|
| program_id | `PROG_03162` |
| university_id | `PNU_T` |
| university.name | دانشگاه پیام نور تهران |
| university.province | تهران |
| major_id | `45` |
| major name from majors DB | علوم کامپیوتر |
| course_type | `payam_noor` |
| method | سوابق تحصیلی |
| mapped period | پیام نور |

For examples 1, 2 and 5, capacity rows exist after matching only major + period + province, but none passes the final exact university-name-in-campus test. This demonstrates that the remaining gap is not simply absence of capacity data.

## 9. Step-B conclusion

**Matched unique 1:1 = 0 / 770 deterministic-domain record programs.**

The join is therefore **not viable for production enrichment without an official key or an authoritative university/campus alias mapping**.

Most importantly:
- no `sanjesh_code` exists in `program2s`;
- `savabegh_dolati` cannot be assigned a unique capacity period from current data;
- `azad` has no matching capacity-period value;
- `payam_noor` and `nonprofit` have deterministic period mappings, but the exact university/campus comparison still yields zero candidate joins;
- **no capacity may be written to `program2s` on the basis of this pilot.**

**Step B status: PILOT COMPLETE — 0 deterministic 1:1 matches.**

**Continuation decision:** without an official `sanjesh_code` linkage (or a separately sourced, authoritative university/campus mapping), continuing to populate `program2s` is not justified.
