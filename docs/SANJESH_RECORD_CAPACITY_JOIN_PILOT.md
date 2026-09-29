# Sanjesh University Alias + Record Capacity Join Pilot

**Date:** 2026-09-29  
**Scope:** Steps 1–2 only. Read-only pilot; no write to `program2s.json`.

## 1. Hard constraints
- No `capacity_total` or Sanjesh key was written to `program2s`.
- No engine/scoring/Hybrid/cutover/frontend/Section 2/G1–G4 changes.
- No fuzzy/free-form name matching.
- No guessed choice between `روزانه` and `نوبت دوم`.
- No invented `sanjesh_code`.

## 2. Sources
| Source | SHA |
|---|---|
| `program2s.json` | `0c2747057a35f3fdf4aa70c178ed68580e7c4537` |
| `docs/data/sanjesh_record_capacity_full.json` | `8a5efdb3c19576ed3557107f13ebb74d2681eebd` |
| `majors_database_v2.json` | `c573c494e7c40bc9920b03734bd62698de455779` |

`program2s`: **4,150** programs; record path: **2,196** programs.

## 3. Step 1 — University alias table
Alias candidates use only values actually present in the two datasets.

Comparison normalization:
- Unicode NFKC
- `ي/ى → ی`
- `ك → ک`
- remove ZWJ/ZWNJ/BOM and Arabic diacritics
- collapse whitespace
- normalize punctuation around `-`
- strip leading `استان ... -` / `ادامه استان ... -` only for comparison
- when the capacity province equals the program province under normalization, normalize that province token inside the campus text to the program-side spelling for comparison

The JSON stores the **raw observed capacity campus strings** in `campus_patterns`.

No fuzzy or Levenshtein threshold is used.

| Metric | Result |
|---|---:|
| Distinct `university_id` | **66** |
| IDs with ≥1 alias pattern | **23** |
| Total observed campus patterns | **86** |
| IDs without alias pattern | **43** |

This is proposed alias infrastructure, not an official Sanjesh mapping.

## 4. Step 2 — course_type ↔ period
| program2s course_type | capacity period(s) used |
|---|---|
| `payam_noor` | **پیام نور** |
| `nonprofit` | **غیرانتفاعی** |
| `savabegh_dolati` | **روزانه** and **نوبت دوم**, tested separately |
| `azad` | **no corresponding capacity period**; no join |

For `savabegh_dolati`, neither period is preferred.

Major mapping is direct: `major_id → name` from `majors_database_v2.json`; then normalized exact comparison to capacity `major_name`.

## 5. Pilot join rule
A candidate edge requires:
1. program `university_id` has an alias entry;
2. capacity `campus` exactly equals an observed raw `campus_pattern`;
3. mapped major name equals normalized capacity `major_name`;
4. course-type period mapping matches.

Classification:
- **matched 1:1:** one capacity candidate and that capacity code has one program candidate;
- **ambiguous:** multiple candidates on either side;
- **unmatched:** no candidate.

Nothing is written back to `program2s`.

## 6. Record results
### Overall
| Category | Programs | Rate |
|---|---:|---:|
| **matched 1:1** | **40** | **1.82%** |
| **ambiguous** | **64** | **2.91%** |
| **unmatched** | **2,092** | **95.27%** |

No capacity code was linked to multiple record programs; ambiguity came from multiple capacity candidates for one program.

### By course_type
| course_type | Total | matched 1:1 | ambiguous | unmatched |
|---|---:|---:|---:|---:|
| `savabegh_dolati` | 580 | **22** | **11** | **547** |
| `payam_noor` | 220 | **18** | **53** | **149** |
| `nonprofit` | 550 | **0** | **0** | **550** |
| `azad` | 846 | **0** | **0** | **846** |

### savabegh_dolati, separate period tests
| Period tested | Total | matched 1:1 | ambiguous | unmatched |
|---|---:|---:|---:|---:|
| **روزانه only** | 580 | **27** | **1** | **552** |
| **نوبت دوم only** | 580 | **15** | **0** | **565** |

The combined classification deliberately marks a program ambiguous when both periods produce candidates.

## 7. Capacity coverage / blank province
For relevant periods `پیام نور`, `غیرانتفاعی`, `روزانه`, `نوبت دوم`:
- capacity rows: **8,290**
- rows with at least one record-program candidate: **462**
- unmatched relevant capacity rows: **7,828**

Complete capacity file:
- rows: **8,350**
- blank province: **330**
- blank-province rows in relevant periods: **302**
- blank-province rows matched in this pilot: **0**
- blank-province relevant rows therefore left unmatched: **302**

Blank-province rows were excluded from alias creation.

## 8. Samples
### matched 1:1
| program_id | university_id | major_id/name | course_type | sanjesh_code(s) |
|---|---|---|---|---|
| PROG_01112 | UMZ | 81 / ریاضیات و کاربردها | savabegh_dolati | 17269 |
| PROG_01224 | UK | 81 / ریاضیات و کاربردها | savabegh_dolati | 15808 |
| PROG_01230 | UK | 84 / فیزیک | savabegh_dolati | 15809 |
| PROG_01332 | RAZI | 61 / مهندسی پلیمر | savabegh_dolati | 16145 |
| PROG_01336 | RAZI | 81 / ریاضیات و کاربردها | savabegh_dolati | 16143 |
| PROG_01342 | RAZI | 84 / فیزیک | savabegh_dolati | 16144 |
| PROG_01448 | BASU | 81 / ریاضیات و کاربردها | savabegh_dolati | 18272 |
| PROG_01454 | BASU | 84 / فیزیک | savabegh_dolati | 18273 |
| PROG_01594 | YAZD | 81 / ریاضیات و کاربردها | savabegh_dolati | 18520 |
| PROG_01600 | YAZD | 84 / فیزیک | savabegh_dolati | 18521 |

### ambiguous
| program_id | university_id | major_id/name | course_type | sanjesh_code(s) |
|---|---|---|---|---|
| PROG_01118 | UMZ | 84 / فیزیک | savabegh_dolati | 17267, 17270 |
| PROG_01521 | KASHAN | 81 / ریاضیات و کاربردها | savabegh_dolati | 10917, 10920 |
| PROG_01527 | KASHAN | 84 / فیزیک | savabegh_dolati | 10918, 10921 |
| PROG_01727 | ZABOL | 45 / علوم کامپیوتر | savabegh_dolati | 14286, 14297 |
| PROG_01730 | ZABOL | 52 / مهندسی عمران | savabegh_dolati | 14291, 14302 |
| PROG_01740 | ZABOL | 81 / ریاضیات و کاربردها | savabegh_dolati | 14285, 14296 |
| PROG_01746 | ZABOL | 84 / فیزیک | savabegh_dolati | 14288, 14299 |
| PROG_01783 | ZABOL | 132 / تاریخ | savabegh_dolati | 14347, 14350 |
| PROG_01785 | ZABOL | 134 / جغرافیا | savabegh_dolati | 14348, 14351 |
| PROG_01965 | ZANJAN | 84 / فیزیک | savabegh_dolati | 13884, 13886 |

### unmatched
| program_id | university_id | major_id/name | course_type | sanjesh_code(s) |
|---|---|---|---|---|
| PROG_00985 | GUILAN | 44 / مهندسی نرم‌افزار | savabegh_dolati | — |
| PROG_00987 | GUILAN | 45 / علوم کامپیوتر | savabegh_dolati | — |
| PROG_00990 | GUILAN | 52 / مهندسی عمران | savabegh_dolati | — |
| PROG_00992 | GUILAN | 53 / مهندسی صنایع | savabegh_dolati | — |
| PROG_00994 | GUILAN | 58 / مهندسی شیمی | savabegh_dolati | — |
| PROG_00996 | GUILAN | 61 / مهندسی پلیمر | savabegh_dolati | — |
| PROG_00998 | GUILAN | 62 / مهندسی مواد و متالورژی | savabegh_dolati | — |
| PROG_01000 | GUILAN | 81 / ریاضیات و کاربردها | savabegh_dolati | — |
| PROG_01002 | GUILAN | 82 / آمار و کاربردها | savabegh_dolati | — |
| PROG_01004 | GUILAN | 83 / علوم داده | savabegh_dolati | — |

## 9. Decision
The pilot yields **40 / 2,196 = 1.82%** 1:1 matches, far below the requested ~50% threshold.

> **بدون غنی‌سازی دستی/رسمی بیشتر ادامه موجه نیست.**

No `admission_info.sanjesh_code` or capacity was written for unmatched/ambiguous rows.

**Status: Steps 1–2 complete; Step 3 not executed.**
