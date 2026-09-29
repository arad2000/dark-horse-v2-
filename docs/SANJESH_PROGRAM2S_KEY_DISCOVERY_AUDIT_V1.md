# Sanjesh Program2s Key Discovery Audit v1

**Audit date:** 2026-09-29  
**Scope:** Step A only — discovery/statistics; no program2s enrichment and no matching policy implementation.

## 1. Scope and guardrails

This audit inspects the existing `program2s.json` and `docs/data/sanjesh_record_capacity_full.json` data on the Step A audit revision.

Rules:
- Read-only inspection of `program2s.json`.
- No field is added or changed in `program2s.json`.
- No name/fuzzy matching.
- No synthetic or inferred `sanjesh_code`.
- No capacity is attached to programs.
- No engine, scoring, Hybrid, cutover, frontend, calibration, Section 2, or G1–G4 changes.

## 2. Source revisions

| Source | Revision |
|---|---|
| `program2s.json` | `0c2747057a35f3fdf4aa70c178ed68580e7c4537` |
| `docs/data/sanjesh_record_capacity_full.json` | `8a5efdb3c19576ed3557107f13ebb74d2681eebd` |

Dataset sizes:
- `program2s`: **4,150 programs**
- capacity: **8,350 rows**
- capacity `sanjesh_code`: **8,350 non-empty / 8,350 unique**

## 3. Complete structure of one program2s sample

The first program object was inspected recursively. Its top-level structure is:

```text
program_id
university_id
major_id
major_group
university
  name
  province
  gender_policy
  prestige_level
admission_info
  method
  course_type
  bomi_type
  diploma_requirements
    accepts_diploma_types[]
    is_floating
  special_conditions
    has_interview
    has_practical_exam
gpa_impact
  year
  konkur_weight
  gpa_weight
financial
  tuition_per_term
  living_cost_level
special_requirements
  min_gpa_required
  has_service_commitment
  service_years
cutoffs_historical
  1401 / 1402 / 1403 / 1404
    zone_1
    zone_2
    zone_3
    isargaran_25
    isargaran_5
    shahid
cutoffs_bomi
  1401 / 1402 / 1403 / 1404
    zone_1
    zone_2
    zone_3
    isargaran_25
    isargaran_5
    shahid
cutoffs_predicted_1405
  zone_1
  zone_2
  zone_3
  isargaran_25
  isargaran_5
  shahid
```

Observed first-sample identity values:
- `program_id`: `PROG_00001`
- `university_id`: `TUMS`
- `major_id`: `1`
- `university.name`: دانشگاه علوم پزشکی تهران
- `university.province`: تهران
- `admission_info.method`: با آزمون
- `admission_info.course_type`: `roozaneh`

## 4. Existing code-like fields in program2s

Recursive inspection of the sample's complete key paths found:

| Check | Result |
|---|---:|
| `sanjesh_code` | **not present** |
| `selection_code` | **not present** |
| `field_code` | **not present** |
| `kod` / obvious code variant | **not present** |
| Any field containing the `sanjesh` + `code` concept | **not present** |

`program_id` exists, but it is not treated as an official Sanjesh code.

## 5. Candidate composite — program2s

For the requested candidate combination, the actual existing paths are:

```text
university.name
major_id
admission_info.course_type
university.province
admission_info.method
```

All five fields are populated for all 4,150 programs.

| Metric | Result |
|---|---:|
| Programs | **4,150** |
| Programs with complete 5-field key | **4,150** |
| Distinct complete composite keys | **4,150** |
| Unique composite-key groups | **4,150** |
| Programs inside unique groups | **4,150** |
| Ambiguous composite-key groups | **0** |
| Programs inside ambiguous groups | **0** |

**Step A observation:** the five-field combination is internally unique across all current `program2s` records.

This is only an internal uniqueness statistic. It does **not** establish that the combination is an official Sanjesh key or that it can safely be used to match capacity rows.

## 6. Capacity-side requested composite

The requested capacity-side normalized combination is:

```text
normalized major_name
+ period
+ province
+ campus
```

Normalization used for this audit:
- trim surrounding whitespace
- collapse repeated whitespace
- normalize Arabic/Persian `ي/ى → ی` and `ك → ک`
- lowercase for comparison

Results:

| Metric | Result |
|---|---:|
| Capacity rows | **8,350** |
| Rows with all 4 fields populated | **8,020** |
| Rows missing/partial | **330** |
| Missing `major_name` | **0** |
| Missing `period` | **0** |
| Missing `province` | **330** |
| Missing `campus` | **0** |
| Distinct complete composite keys | **8,015** |
| Unique composite-key groups | **8,012** |
| Rows inside unique groups | **8,012** |
| Ambiguous composite-key groups | **3** |
| Rows inside ambiguous groups | **8** |

Therefore, among capacity rows with a complete four-field key, **8,012 rows are individually unique and 8 rows belong to 3 ambiguous groups**. The remaining **330 rows cannot be evaluated on the requested four-field key because province is missing.

## 7. Step A conclusion

1. `program2s` contains **no existing Sanjesh-code field or obvious documented code variant**.
2. The requested five-field `program2s` composite is internally unique for **4,150 / 4,150** programs.
3. The requested capacity composite is complete for **8,020 / 8,350** rows.
4. Within those complete capacity rows, **8,012 / 8,020** are unique and **8 rows** are ambiguous across **3 composite-key groups**.
5. **No cross-dataset match is asserted by this audit.** The two composite definitions are structurally different (`major_id`/university name/method/course type versus `major_name`/period/province/campus), so internal uniqueness alone is insufficient to establish an official mapping.

**Step A status: COMPLETE — REPORT ONLY.**

Step B (match-policy proposal) is intentionally not implemented or approved by this PR.
