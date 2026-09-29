# Sanjesh Record Capacity — Official Key Discovery Audit v1

**Date:** 2026-09-29  
**Scope:** Step A only — discovery/statistics. No `program2s` data was modified.  
**Base:** `deploy/liara-commercial-sandbox@49d3b6640bbfba2c7870ed67bc6520865198adc7`

## 1. Complete nested-key structure of one `program2s` program

A complete recursive key/path inspection of `program2s.json.programs[0]` produced:

### Top level
- `program_id`
- `university_id`
- `major_id`
- `major_group`
- `university`
- `admission_info`
- `gpa_impact`
- `financial`
- `special_requirements`
- `cutoffs_historical`
- `cutoffs_bomi`
- `cutoffs_predicted_1405`

### `university`
- `university.name`
- `university.province`
- `university.gender_policy`
- `university.prestige_level`

### `admission_info`
- `admission_info.method`
- `admission_info.course_type`
- `admission_info.bomi_type`
- `admission_info.diploma_requirements`
  - `admission_info.diploma_requirements.accepts_diploma_types`
  - `admission_info.diploma_requirements.is_floating`
- `admission_info.special_conditions`
  - `admission_info.special_conditions.has_interview`
  - `admission_info.special_conditions.has_practical_exam`

### `gpa_impact`
- `gpa_impact.year`
- `gpa_impact.konkur_weight`
- `gpa_impact.gpa_weight`

### `financial`
- `financial.tuition_per_term`
- `financial.living_cost_level`

### `special_requirements`
- `special_requirements.min_gpa_required`
- `special_requirements.has_service_commitment`
- `special_requirements.service_years`

### `cutoffs_historical`
For each of `1401`, `1402`, `1403`, `1404`:
- `zone_1`
- `zone_2`
- `zone_3`
- `isargaran_25`
- `isargaran_5`
- `shahid`

### `cutoffs_bomi`
For each of `1401`, `1402`, `1403`, `1404`:
- `zone_1`
- `zone_2`
- `zone_3`
- `isargaran_25`
- `isargaran_5`
- `shahid`

### `cutoffs_predicted_1405`
- `cutoffs_predicted_1405.zone_1`
- `cutoffs_predicted_1405.zone_2`
- `cutoffs_predicted_1405.zone_3`
- `cutoffs_predicted_1405.isargaran_25`
- `cutoffs_predicted_1405.isargaran_5`
- `cutoffs_predicted_1405.shahid`

## 2. Search for an existing official-looking code field

The complete `program2s` object was recursively scanned for field names resembling:

- `code`
- `selection_code`
- `field_code`
- `kod`
- `sanjesh`
- `sanjesh_code`

**Result: none found.**

In particular:
- `sanjesh_code`: absent
- `selection_code`: absent
- `field_code`: absent
- `kod`: absent
- any nested key containing `sanjesh`: absent

`program_id` and `university_id` exist, but neither is treated as a Sanjesh code.

## 3. Candidate composite uniqueness in `program2s`

The requested candidate was evaluated as:

`university + major_id + course_type + province + method`

For the stable university component, both of these were measured:
1. `university_id + major_id + admission_info.course_type + university.province + admission_info.method`
2. `university.name + major_id + admission_info.course_type + university.province + admission_info.method`

Normalization for the statistics:
- Unicode NFKC
- remove ZWJ/ZWNJ/BOM
- `ي/ى → ی`
- `ك → ک`
- remove Arabic diacritics
- collapse whitespace
- trim

| Program composite | Programs | Unique combinations | Rows in duplicate groups | Ambiguous row rate |
|---|---:|---:|---:|---:|
| university_id + major_id + course_type + province + method | 4,150 | 4,150 | 0 | 0% |
| university.name + major_id + course_type + province + method | 4,150 | 4,150 | 0 | 0% |

Therefore, the candidate composite is unique within `program2s` under both university representations.

**Important:** this is only a uniqueness statistic. It does not establish that the fields have the same semantics/grain as the official Sanjesh capacity rows.

## 4. Capacity-side composite uniqueness

The requested capacity candidate was evaluated as:

`normalized major_name + period + province + campus`

Using the same normalization rules:

| Capacity composite | Rows | Unique combinations | Rows in singleton groups | Rows in duplicate groups | Ambiguous row rate |
|---|---:|---:|---:|---:|---:|
| major_name + period + province + campus | 8,350 | 8,343 | 8,338 | 12 | 0.144% |

Additional observation:
- **330 / 8,350 capacity rows (3.95%) have a blank province.**
- major_name, period, and campus were present in all 8,350 rows.

### Duplicate composite groups

| Composite | sanjesh_codes | Count |
|---|---|---:|
| مهندسی شیمی + روزانه + خراسان رضوی + مجتمع آموزش عالی گناباد | 12756, 12757, 12758 | 3 |
| مهندسی مکانیک + روزانه + خراسان رضوی + مجتمع آموزش عالی گناباد | 12765, 12766, 12767 | 3 |
| مهندسی و علم مواد + روزانه + خراسان رضوی + مجتمع آموزش عالی گناباد | 12768, 12769 | 2 |
| علوم کامپیوتر + روزانه + province blank + دانشگاه صنعتی سیرجان... | 18995, 19020 | 2 |
| گردشگری + روزانه + province blank + دانشگاه ولیعصر(عج) رفسنجان... | 19007, 19010 | 2 |

Thus this composite is **not globally unique** on the capacity side.

## 5. Step A conclusion

The requested discovery is complete:

- `program2s` has **no existing Sanjesh/code-like key**.
- The proposed program-side composite is **100% unique internally** (4,150/4,150).
- The proposed capacity-side composite has **5 ambiguous groups / 12 ambiguous rows**, plus **330 rows with missing province**.
- No match was written to `program2s`.
- No capacity was attached to any program.
- No fuzzy/name-only matching was performed.
- No engine, scoring, Section 2, G1–G4, frontend, Hybrid, cutover, chance, or calibration logic was changed.

**Step B is intentionally not proposed here.** This document only records the requested discovery statistics for supervisor review.
