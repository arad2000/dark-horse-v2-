# Sanjesh University Alias + Record Capacity Join Pilot v1

**Date:** 2026-09-29  
**Scope:** Step 1 + Step 2 only; read-only pilot; no `program2s` enrichment.

## 1. Guardrails

- `program2s.json` was not modified.
- No capacity field was written to any program.
- No synthetic or inferred `sanjesh_code` was created.
- No fuzzy similarity, edit distance, score, or unreported threshold was used.
- No engine, scoring, Hybrid, cutover, frontend, Section 2, or G1-G4 changes were made.

## 2. Locked source revisions

| Source | SHA |
|---|---|
| `program2s.json` | `0c2747057a35f3fdf4aa70c178ed68580e7c4537` |
| `docs/data/sanjesh_record_capacity_full.json` | `8a5efdb3c19576ed3557107f13ebb74d2681eebd` |
| `majors_database_v2.json` | `c573c494e7c40bc9920b03734bd62698de455779` |

Dataset: 4,150 programs; 2,196 `سوابق تحصیلی` programs; 8,350 capacity rows; 8,350 unique `sanjesh_code` values.

## 3. Step 1 — proposed university alias table

File: `docs/data/sanjesh_university_alias_v1.json`

Only raw `capacity.campus` values observed in the source file are stored as patterns.

Deterministic discovery rules:
1. normalized `program2s.university.name` is an exact substring of normalized `capacity.campus` and province is equal; or
2. for Payam Noor, the exact observed phrase `دانشگاه پیام نور استان <province>` is present in the campus string; or
3. for an academic institution, its exact distinctive name is present in an observed `دانشگاه غیرانتفاعی ...` or `موسسه غیرانتفاعی ...` campus string in the same province.

Normalization: Unicode NFKC, `ي/ى→ی`, `ك→ک`, removal of ZWJ/ZWNJ/BOM and Arabic diacritics, whitespace collapse. No fuzzy comparison.

### Alias statistics

| Metric | Result |
|---|---:|
| `program2s` university_id count | 66 |
| university_id with at least one proposed pattern | **22** |
| total raw campus patterns | **86** |
| record-path university_id count | 28 |
| record-path university_id with proposed alias | **12** |

Record university_id values still without a proposed alias:
`GUILAN`, `RAZI`, `BASU`, `QOM`, `ILAM`, `IAUCTB`, `SRBIAU`, `IAUN`, `IAUM`, `IAUS`, `IAUT`, `ALZAHRA`, `ALBORZ_NONPROFIT`, `KHATAM_NONPROFIT`, `SHEIKH_BAHAI_NONPROFIT`, `IMAM_SADEQ_NONPROFIT`.

The alias table is a proposal, not an official Sanjesh identity key.

## 4. Step 2 — course_type / method to period

| record course_type | count | pilot period treatment |
|---|---:|---|
| `payam_noor` | 220 | `پیام نور` |
| `nonprofit` | 550 | `غیرانتفاعی` |
| `savabegh_dolati` | 580 | test separately against `روزانه` and `نوبت دوم` |
| `azad` | 846 | no corresponding capacity period; outside deterministic period domain |

No new period value was invented. For `savabegh_dolati`, if both daily and second-shift produce a candidate, the program is ambiguous and receives no code.

## 5. Strict pilot join key

`major_id` is resolved to the exact name in `majors_database_v2.json`.

Candidate join:
`normalized major_name + exact period + exact normalized province + proposed university alias`.

Capacity rows with blank province are excluded from strict 1:1 matching, not reassigned.

## 6. Results by course_type

| course_type | period test | programs | 1:1 matched | ambiguous | unmatched |
|---|---|---:|---:|---:|---:|
| `payam_noor` | پیام نور | 220 | **18** | **53** | **149** |
| `nonprofit` | غیرانتفاعی | 550 | **12** | **0** | **538** |
| `savabegh_dolati` | روزانه | 580 | **22** | **1** | **557** |
| `savabegh_dolati` | نوبت دوم | 580 | **15** | **0** | **565** |
| `savabegh_dolati` combined | روزانه vs نوبت دوم | 580 | **17** | **10** | **553** |
| `azad` | — | 846 | **0** | **0** | outside deterministic period domain |

Across the deterministic record join domain (`payam_noor` + `nonprofit` + `savabegh_dolati`):
- 1,350 programs are testable.
- **47** programs are 1:1 matched.
- **63** are ambiguous.
- **1,240** are unmatched.
- 1:1 yield = **47 / 1,350 = 3.48%**.
- 1:1 yield over all 2,196 record programs = **2.14%**.

## 7. Capacity-side effect of blank province

| period | capacity rows | blank province | rows used by strict 1:1 |
|---|---:|---:|---:|
| پیام نور | 4,462 | 0 | 18 |
| غیرانتفاعی | 2,224 | 27 | 12 |
| روزانه | 1,082 | 262 | 22 |
| نوبت دوم | 522 | 13 | 15 |

Full capacity file: **330 / 8,350** rows have blank province. Within the deterministic period domain above, **302** are province-blank and therefore excluded from strict matching.

## 8. Ten matched 1:1 samples

1. `PROG_03158` | PNU_T | مهندسی برق | payam_noor | `11960`
2. `PROG_03163` | PNU_T | مهندسی مکانیک | payam_noor | `11968`
3. `PROG_03172` | PNU_T | مهندسی شهرسازی | payam_noor | `11943`
4. `PROG_03175` | PNU_T | مهندسی شیمی | payam_noor | `11964`
5. `PROG_03931` | SAJAD_NONPROFIT | مهندسی برق | nonprofit | `13113`
6. `PROG_03932` | SAJAD_NONPROFIT | مهندسی کامپیوتر | nonprofit | `13118`
7. `PROG_03935` | SAJAD_NONPROFIT | علوم کامپیوتر | nonprofit | `13111`
8. `PROG_01112` | UMZ | ریاضیات و کاربردها | savabegh_dolati | `17269`
9. `PROG_01224` | UK | ریاضیات و کاربردها | savabegh_dolati | `15808`
10. `PROG_01230` | UK | فیزیک | savabegh_dolati | `15809`

## 9. Ten ambiguous samples

1. `PROG_03159` | PNU_T | مهندسی کامپیوتر | payam_noor | `11967, 11981, 12000, 12033, 12063, 12118, 12139, 12161, 12190, 12212`
2. `PROG_03162` | PNU_T | علوم کامپیوتر | payam_noor | `11940, 11978, 12016, 12030, 12061, 12085, 12114, 12138, 12158, 12188`
3. `PROG_03169` | PNU_T | مهندسی عمران | payam_noor | `11966, 12117`
4. `PROG_03198` | PNU_T | ریاضیات و کاربردها | payam_noor | `11939, 11998, 12113, 12157, 12187`
5. `PROG_01118` | UMZ | فیزیک | savabegh_dolati | `17267, 17270`
6. `PROG_01521` | KASHAN | ریاضیات و کاربردها | savabegh_dolati | `10917, 10920`
7. `PROG_01527` | KASHAN | فیزیک | savabegh_dolati | `10918, 10921`
8. `PROG_01727` | ZABOL | علوم کامپیوتر | savabegh_dolati | `14286, 14297`
9. `PROG_01730` | ZABOL | مهندسی عمران | savabegh_dolati | `14291, 14302`
10. `PROG_01740` | ZABOL | ریاضیات و کاربردها | savabegh_dolati | `14285, 14296`

در مورد نمونه‌های `savabegh_dolati`، برخورد هم‌زمان با روزانه و نوبت دوم علت ambiguity است؛ انتخاب یکی از آنها مجاز نیست.

## 10. Ten unmatched samples

1. `PROG_03160` | PNU_T | مهندسی فناوری اطلاعات | payam_noor | no `sanjesh_code` candidate
2. `PROG_03161` | PNU_T | مهندسی نرم‌افزار | payam_noor | no `sanjesh_code` candidate
3. `PROG_03164` | PNU_T | مهندسی هوافضا | payam_noor | no `sanjesh_code` candidate
4. `PROG_03601` | ALBORZ_NONPROFIT | مهندسی برق | nonprofit | no `sanjesh_code` candidate
5. `PROG_03602` | ALBORZ_NONPROFIT | مهندسی کامپیوتر | nonprofit | no `sanjesh_code` candidate
6. `PROG_03603` | ALBORZ_NONPROFIT | مهندسی فناوری اطلاعات | nonprofit | no `sanjesh_code` candidate
7. `PROG_00985` | GUILAN | مهندسی نرم‌افزار | savabegh_dolati | no daily/second-shift candidate
8. `PROG_00987` | GUILAN | علوم کامپیوتر | savabegh_dolati | no daily/second-shift candidate
9. `PROG_00990` | GUILAN | مهندسی عمران | savabegh_dolati | no daily/second-shift candidate
10. `PROG_00992` | GUILAN | مهندسی صنایع | savabegh_dolati | no daily/second-shift candidate

## 11. Decision gate

**Matched 1:1 = 47 / 1,350 = 3.48%.**

This is far below the requested 50% continuation gate.

**بدون غنی‌سازی دستی/رسمی بیشتر ادامه موجه نیست.**

Therefore no production enrichment is justified from this alias pilot. In particular, no `sanjesh_code` may be written to `program2s` from any ambiguous or unmatched case.

## 12. Non-actions

No changes to `program2s.json`, engine/scoring, Section 2, G1-G4, Hybrid, cutover, frontend, capacity values, or scientific JSONs.

**Status: Step 1 + Step 2 complete; PR must remain unmerged pending supervisor review.**