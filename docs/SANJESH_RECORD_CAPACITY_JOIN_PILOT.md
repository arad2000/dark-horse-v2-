# Sanjesh Record Capacity — University Alias + Pilot Join v1

**Date:** 2026-09-29  
**Base:** `deploy/liara-commercial-sandbox@49d3b6640bbfba2c7870ed67bc6520865198adc7`  
**Scope:** Step 1 + Step 2 only. Read-only pilot; no `program2s` write.

## 1. Guardrails

This PR does **not**:
- add `sanjesh_code` or capacity to `program2s.json`;
- alter engine/scoring/Section 2/G1–G4/Hybrid/cutover/frontend;
- invent any code;
- force `savabegh_dolati` into either daily or second-shift;
- match by fuzzy name similarity without the explicit deterministic rule below.

## 2. Input revisions

| Dataset | SHA |
|---|---|
| `program2s.json` | `0c2747057a35f3fdf4aa70c178ed68580e7c4537` |
| `docs/data/sanjesh_record_capacity_full.json` | `8a5efdb3c19576ed3557107f13ebb74d2681eebd` |
| `majors_database_v2.json` | `c573c494e7c40bc9920b03734bd62698de455779` |

Record population: **2,196 programs**. All record `major_id` values map to a major name in `majors_database_v2.json`.

## 3. Observed course_type ↔ capacity.period mapping

Only values actually present in the datasets were used.

| program2s `course_type` | record count | capacity `period` tested | Treatment |
|---|---:|---|---|
| `payam_noor` | 220 | `پیام نور` | exact observed mapping |
| `nonprofit` | 550 | `غیرانتفاعی` | exact observed mapping |
| `savabegh_dolati` | 580 | `روزانه`, `نوبت دوم` | both tested separately; both = ambiguous |
| `azad` | 846 | **no observed matching capacity period** | no candidate period invented |
| `roozaneh` | exists in program2s overall, not in record population | `روزانه` | observed overall only; not used for record pilot |
| `nobat_dovom` | exists in program2s overall, not in record population | `نوبت دوم` | observed overall only; not used for record pilot |

## 4. Step 1 — University alias proposal

There are **66 distinct `university_id` values** in `program2s`.

A proposed alias is retained only when:
1. the raw `capacity.campus` value is actually present;
2. normalized `capacity.campus` contains normalized `university.name`;
3. the prefix before the university name is only empty, `دانشگاه`, or an observed `استان ... -` / `ادامه استان ... -` prefix;
4. nonblank capacity province equals the program university province after the same normalization.

Result:

| Metric | Count |
|---|---:|
| university_id total | **66** |
| university_id with ≥1 observed safe pattern | **19** |
| observed campus patterns retained | **34** |

The 47 remaining university IDs receive no alias in this proposal; no spelling or campus name is invented for them.

Alias file: `docs/data/sanjesh_university_alias_v1.json`.

## 5. Step 2 — Read-only pilot join

Join key for the pilot:

`program.university_id → alias.campus_patterns`  
+ exact normalized `major_id → major_name` from `majors_database_v2.json`  
+ mapped `period` from Section 3  
+ for `savabegh_dolati`, daily and second-shift are evaluated independently.

For a non-ambiguous result, exactly one capacity row must remain.

### Overall record result

| Result | Programs | Share |
|---|---:|---:|
| **matched 1:1** | **17** | **0.77%** |
| **ambiguous** | **11** | **0.50%** |
| **unmatched** | **2,168** | **98.73%** |
| **record total** | **2,196** | **100%** |

### By course_type

| course_type | Programs | matched 1:1 | ambiguous | unmatched |
|---|---:|---:|---:|---:|
| `savabegh_dolati` | 580 | 17 | 11 | 552 |
| `payam_noor` | 220 | 0 | 0 | 220 |
| `nonprofit` | 550 | 0 | 0 | 550 |
| `azad` | 846 | 0 | 0 | 846 |

### savabegh_dolati period sensitivity

This course_type is intentionally **not** forced to either period.

| Test | Programs |
|---|---:|
| daily candidate exists | 23 |
| daily candidate exactly 1 row | 22 |
| daily candidate ambiguous | 1 |
| second-shift candidate exists | 15 |
| second-shift candidate exactly 1 row | 15 |
| second-shift candidate ambiguous | 0 |
| both daily and second-shift exist | 10 |
| both-period cases remain ambiguous | 10 |
| neither period has a candidate | 552 |

Thus the ambiguous cases are preserved rather than choosing daily or second-shift by assumption.

## 6. Blank-province effect

The capacity file contains **330 / 8,350** rows with blank province (**3.95%**).

For this conservative alias pilot, province equality is part of the alias construction. Therefore:
- blank-province rows are **excluded from accepted university aliases**;
- they contribute **0 accepted pilot matches**;
- no attempt was made to recover province by campus-name guessing.

This exclusion does not alter any `program2s` data.

## 7. Ten matched 1:1 samples

| program_id | university_id | major_id / major_name | course_type | period | sanjesh_code |
|---|---|---|---|---|---|
| PROG_01112 | UMZ | 81 / ریاضیات و کاربردها | savabegh_dolati | نوبت دوم | 17269 |
| PROG_01224 | UK | 81 / ریاضیات و کاربردها | savabegh_dolati | روزانه | 15808 |
| PROG_01230 | UK | 84 / فیزیک | savabegh_dolati | روزانه | 15809 |
| PROG_01594 | YAZD | 81 / ریاضیات و کاربردها | savabegh_dolati | روزانه | 18520 |
| PROG_01600 | YAZD | 84 / فیزیک | savabegh_dolati | روزانه | 18521 |
| PROG_01647 | YAZD | 148 / زبان و ادبیات انگلیسی | savabegh_dolati | نوبت دوم | 18527 |
| PROG_01657 | BIRJAND | 52 / مهندسی عمران | savabegh_dolati | روزانه | 12539 |
| PROG_01667 | BIRJAND | 81 / ریاضیات و کاربردها | savabegh_dolati | روزانه | 12493 |
| PROG_01673 | BIRJAND | 84 / فیزیک | savabegh_dolati | روزانه | 12495 |
| PROG_01704 | BIRJAND | 113 / اقتصاد | savabegh_dolati | نوبت دوم | 12526 |

## 8. Ten ambiguous samples

| program_id | university_id | major_id / major_name | course_type | candidate sanjesh_code(s) | periods |
|---|---|---|---|---|---|
| PROG_01118 | UMZ | 84 / فیزیک | savabegh_dolati | 17267, 17270 | روزانه, نوبت دوم |
| PROG_01521 | KASHAN | 81 / ریاضیات و کاربردها | savabegh_dolati | 10917, 10920 | روزانه, نوبت دوم |
| PROG_01527 | KASHAN | 84 / فیزیک | savabegh_dolati | 10918, 10921 | روزانه, نوبت دوم |
| PROG_01727 | ZABOL | 45 / علوم کامپیوتر | savabegh_dolati | 14286, 14297 | روزانه, نوبت دوم |
| PROG_01730 | ZABOL | 52 / مهندسی عمران | savabegh_dolati | 14291, 14302 | روزانه, نوبت دوم |
| PROG_01740 | ZABOL | 81 / ریاضیات و کاربردها | savabegh_dolati | 14285, 14296 | روزانه, نوبت دوم |
| PROG_01746 | ZABOL | 84 / فیزیک | savabegh_dolati | 14288, 14299 | روزانه, نوبت دوم |
| PROG_01783 | ZABOL | 132 / تاریخ | savabegh_dolati | 14347, 14350 | روزانه, نوبت دوم |
| PROG_01785 | ZABOL | 134 / جغرافیا | savabegh_dolati | 14348, 14351 | روزانه, نوبت دوم |
| PROG_01965 | ZANJAN | 84 / فیزیک | savabegh_dolati | 13884, 13886 | روزانه, نوبت دوم |

## 9. Ten unmatched samples

| program_id | university_id | major_id / major_name | course_type | sanjesh_code(s) |
|---|---|---|---|---|
| PROG_02261 | IAUCTB | 4 / دامپزشکی | azad | — |
| PROG_02411 | SRBIAU | 4 / دامپزشکی | azad | — |
| PROG_02561 | IAUN | 4 / دامپزشکی | azad | — |
| PROG_03158 | PNU_T | 41 / مهندسی برق | payam_noor | — |
| PROG_03268 | PNU_I | 41 / مهندسی برق | payam_noor | — |
| PROG_03601 | ALBORZ_NONPROFIT | 41 / مهندسی برق | nonprofit | — |
| PROG_03711 | KHATAM_NONPROFIT | 41 / مهندسی برق | nonprofit | — |
| PROG_00985 | GUILAN | 44 / مهندسی نرم‌افزار | savabegh_dolati | — |
| PROG_01097 | UMZ | 44 / مهندسی نرم‌افزار | savabegh_dolati | — |
| PROG_01100 | UMZ | 45 / علوم کامپیوتر | savabegh_dolati | — |

## 10. Decision

The pilot does **not** establish a sufficiently complete official join.

**1:1 matched record programs = 17 / 2,196 = 0.77%.**

This is far below the requested 50% threshold.

> **بدون غنی‌سازی دستی/رسمی بیشتر ادامه موجه نیست.**

Therefore this wave stops at the alias/pilot layer. No `sanjesh_code` is written into `program2s`, and no capacity field is attached to any program.

