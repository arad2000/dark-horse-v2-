# Sanjesh Record Capacity — University Alias + Pilot Join v1

**Date:** 2026-09-29  
**Scope:** Step 1 (university alias table) + Step 2 (read-only pilot join).  
**Status:** REPORT ONLY — no `program2s` enrichment and no capacity write.

## 1. Guardrails

This PR does **not** modify `program2s.json`, engine/scoring, Section 2, G1–G4, Hybrid, cutover, frontend, chance, calibration, or any capacity field on a program.

No fuzzy matching with an unstated threshold was used. No Sanjesh code was invented.

## 2. Source revisions

| Source | Revision |
|---|---|
| `program2s.json` | `0c2747057a35f3fdf4aa70c178ed68580e7c4537` |
| `docs/data/sanjesh_record_capacity_full.json` | `8a5efdb3c19576ed3557107f13ebb74d2681eebd` |
| `majors_database_v2.json` | `c573c494e7c40bc9920b03734bd62698de455779` |

Record programs: **2196**  
Record programs with resolvable `major_id → major name`: **2196/2196**  
Capacity rows: **8350**

## 3. Step 1 — university alias table

There are **66** distinct `university_id` values in `program2s`.

Using only observed strings and the deterministic rule documented in `docs/data/sanjesh_university_alias_v1.json`:

| Metric | Result |
|---|---:|
| university_id with ≥1 observed campus pattern | **19** |
| coverage of program2s university_ids | **28.79%** |
| observed campus patterns | **34** |
| campus patterns assigned to multiple university_id values | **0** |

The alias table is intentionally conservative. A university with no deterministic observed pattern is left out rather than assigned by name guesswork.

## 4. Step 2 — period mapping from observed values

Only values present in the two datasets were used:

| program2s course_type | capacity.period candidates |
|---|---|
| `payam_noor` | `پیام نور` |
| `nonprofit` | `غیرانتفاعی` |
| `savabegh_dolati` | `روزانه` **and** `نوبت دوم` |
| `azad` | **no corresponding capacity.period observed** |

Capacity period counts: `پیام نور` 4462, `غیرانتفاعی` 2224, `روزانه` 1082, `نوبت دوم` 522.

For `savabegh_dolati`, both periods were tested independently. If both produced candidates, the program was classified **ambiguous**; no preference for روزانه or نوبت دوم was made.

## 5. Pilot join definition

Join dimensions:

```text
program.university_id
    → university alias → capacity.campus
program.major_id
    → majors_database_v2.name → capacity.major_name (normalized text)
program.admission_info.course_type
    → observed capacity.period mapping above
```

A program is:

- **matched_1to1:** exactly one capacity row is returned.
- **ambiguous:** more than one capacity row is returned.
- **unmatched:** no capacity row is returned.

## 6. Pilot result — all record programs

| Course type | Programs | matched 1:1 | ambiguous | unmatched | matched rate |
|---|---:|---:|---:|---:|---:|
| azad | 846 | 0 | 0 | 846 | 0% |
| nonprofit | 550 | 0 | 0 | 550 | 0% |
| payam_noor | 220 | 0 | 0 | 220 | 0% |
| savabegh_dolati | 580 | 17 | 11 | 552 | 2.93% |
| **TOTAL** | **2196** | **17** | **11** | **2168** | **0.77%** |

### Interpretation

The overall record-program 1:1 rate is **0.77%**, far below the requested 50% threshold.

**بدون غنی‌سازی دستی/رسمی بیشتر ادامه موجه نیست.**

In particular:
- `savabegh_dolati`: 17/580 1:1 (**2.93%**).
- `payam_noor`: 0/220 1:1.
- `nonprofit`: 0/550 1:1.
- `azad`: 0/846; no matching capacity period exists.

## 7. Capacity-side coverage and blank province effect

| Capacity metric | Rows |
|---|---:|
| Total capacity | **8350** |
| Campus mapped by alias | **336** |
| Campus not mapped by alias | **8014** |
| Capacity codes used by a program candidate (matched or ambiguous) | **39** |
| Unmatched capacity rows | **8311** |
| Blank-province capacity rows | **330** |
| Blank-province rows entering alias map | **0** |

The **330** rows with blank `province` do not enter the alias map under the strict rule because alias evidence requires an observed province match. Therefore they remain unmatched in this pilot; no province was inferred from campus text.

## 8. What remains prohibited at this stage

No `sanjesh_code` was added to `program2s`.  
No `capacity`/capacity_total was attached to any program.  
Ambiguous and unmatched cases remain empty.

## 9. Samples — 10 matched 1:1



```json
[
  {
    "program_id": "PROG_01112",
    "university_id": "UMZ",
    "university_name": "دانشگاه مازندران",
    "major_id": "81",
    "major_name": "ریاضیات و کاربردها",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "17269"
    ],
    "capacity_rows": [
      {
        "major_name": "ریاضیات و كاربردها",
        "period": "نوبت دوم",
        "province": "مازندران",
        "campus": "استان مازندران - دانشگاه مازندران - بابلسر"
      }
    ]
  },
  {
    "program_id": "PROG_01224",
    "university_id": "UK",
    "university_name": "دانشگاه شهید باهنر کرمان",
    "major_id": "81",
    "major_name": "ریاضیات و کاربردها",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "15808"
    ],
    "capacity_rows": [
      {
        "major_name": "ریاضیات و كاربردها",
        "period": "روزانه",
        "province": "کرمان",
        "campus": "استان کرمان - دانشگاه شهيد باهنر کرمان"
      }
    ]
  },
  {
    "program_id": "PROG_01230",
    "university_id": "UK",
    "university_name": "دانشگاه شهید باهنر کرمان",
    "major_id": "84",
    "major_name": "فیزیک",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "15809"
    ],
    "capacity_rows": [
      {
        "major_name": "فیزیک",
        "period": "روزانه",
        "province": "کرمان",
        "campus": "استان کرمان - دانشگاه شهيد باهنر کرمان"
      }
    ]
  },
  {
    "program_id": "PROG_01594",
    "university_id": "YAZD",
    "university_name": "دانشگاه یزد",
    "major_id": "81",
    "major_name": "ریاضیات و کاربردها",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "18520"
    ],
    "capacity_rows": [
      {
        "major_name": "ریاضیات و كاربردها",
        "period": "روزانه",
        "province": "يزد",
        "campus": "استان يزد - دانشگاه يزد"
      }
    ]
  },
  {
    "program_id": "PROG_01600",
    "university_id": "YAZD",
    "university_name": "دانشگاه یزد",
    "major_id": "84",
    "major_name": "فیزیک",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "18521"
    ],
    "capacity_rows": [
      {
        "major_name": "فیزیک",
        "period": "روزانه",
        "province": "يزد",
        "campus": "استان يزد - دانشگاه يزد"
      }
    ]
  },
  {
    "program_id": "PROG_01647",
    "university_id": "YAZD",
    "university_name": "دانشگاه یزد",
    "major_id": "148",
    "major_name": "زبان و ادبیات انگلیسی",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "18527"
    ],
    "capacity_rows": [
      {
        "major_name": "زبان و ادبيات انگلیسی",
        "period": "نوبت دوم",
        "province": "يزد",
        "campus": "استان يزد - دانشگاه يزد (محل تحصيل شهرستان مهريز)"
      }
    ]
  },
  {
    "program_id": "PROG_01657",
    "university_id": "BIRJAND",
    "university_name": "دانشگاه بیرجند",
    "major_id": "52",
    "major_name": "مهندسی عمران",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "12539"
    ],
    "capacity_rows": [
      {
        "major_name": "مهندسی عمران",
        "period": "روزانه",
        "province": "خراسان جنوبي",
        "campus": "استان خراسان جنوبي - دانشگاه بيرجند (محل تحصيل دانشكده فني فردوس واقع در شهرستان فردوس)"
      }
    ]
  },
  {
    "program_id": "PROG_01667",
    "university_id": "BIRJAND",
    "university_name": "دانشگاه بیرجند",
    "major_id": "81",
    "major_name": "ریاضیات و کاربردها",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "12493"
    ],
    "capacity_rows": [
      {
        "major_name": "ریاضیات و كاربردها",
        "period": "روزانه",
        "province": "خراسان جنوبي",
        "campus": "استان خراسان جنوبي - دانشگاه بيرجند"
      }
    ]
  },
  {
    "program_id": "PROG_01673",
    "university_id": "BIRJAND",
    "university_name": "دانشگاه بیرجند",
    "major_id": "84",
    "major_name": "فیزیک",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "12495"
    ],
    "capacity_rows": [
      {
        "major_name": "فیزیک",
        "period": "روزانه",
        "province": "خراسان جنوبي",
        "campus": "استان خراسان جنوبي - دانشگاه بيرجند"
      }
    ]
  },
  {
    "program_id": "PROG_01704",
    "university_id": "BIRJAND",
    "university_name": "دانشگاه بیرجند",
    "major_id": "113",
    "major_name": "اقتصاد",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "12526"
    ],
    "capacity_rows": [
      {
        "major_name": "اقتصاد",
        "period": "نوبت دوم",
        "province": "خراسان جنوبي",
        "campus": "ادامه استان خراسان جنوبي - دانشگاه بيرجند"
      }
    ]
  }
]
```


## 10. Samples — 10 ambiguous



```json
[
  {
    "program_id": "PROG_01118",
    "university_id": "UMZ",
    "university_name": "دانشگاه مازندران",
    "major_id": "84",
    "major_name": "فیزیک",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "17267",
      "17270"
    ],
    "capacity_rows": [
      {
        "major_name": "فیزیک",
        "period": "روزانه",
        "province": "مازندران",
        "campus": "استان مازندران - دانشگاه مازندران - بابلسر"
      },
      {
        "major_name": "فیزیک",
        "period": "نوبت دوم",
        "province": "مازندران",
        "campus": "استان مازندران - دانشگاه مازندران - بابلسر"
      }
    ]
  },
  {
    "program_id": "PROG_01521",
    "university_id": "KASHAN",
    "university_name": "دانشگاه کاشان",
    "major_id": "81",
    "major_name": "ریاضیات و کاربردها",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "10917",
      "10920"
    ],
    "capacity_rows": [
      {
        "major_name": "ریاضیات و كاربردها",
        "period": "روزانه",
        "province": "اصفهان",
        "campus": "استان اصفهان - دانشگاه کاشان"
      },
      {
        "major_name": "ریاضیات و كاربردها",
        "period": "نوبت دوم",
        "province": "اصفهان",
        "campus": "استان اصفهان - دانشگاه کاشان"
      }
    ]
  },
  {
    "program_id": "PROG_01527",
    "university_id": "KASHAN",
    "university_name": "دانشگاه کاشان",
    "major_id": "84",
    "major_name": "فیزیک",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "10918",
      "10921"
    ],
    "capacity_rows": [
      {
        "major_name": "فیزیک",
        "period": "روزانه",
        "province": "اصفهان",
        "campus": "استان اصفهان - دانشگاه کاشان"
      },
      {
        "major_name": "فیزیک",
        "period": "نوبت دوم",
        "province": "اصفهان",
        "campus": "استان اصفهان - دانشگاه کاشان"
      }
    ]
  },
  {
    "program_id": "PROG_01727",
    "university_id": "ZABOL",
    "university_name": "دانشگاه زابل",
    "major_id": "45",
    "major_name": "علوم کامپیوتر",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "14286",
      "14297"
    ],
    "capacity_rows": [
      {
        "major_name": "علوم کامپیوتر",
        "period": "روزانه",
        "province": "سيستان و بلوچستان",
        "campus": "استان سيستان و بلوچستان - دانشگاه زابل"
      },
      {
        "major_name": "علوم کامپیوتر",
        "period": "نوبت دوم",
        "province": "سيستان و بلوچستان",
        "campus": "استان سيستان و بلوچستان - دانشگاه زابل"
      }
    ]
  },
  {
    "program_id": "PROG_01730",
    "university_id": "ZABOL",
    "university_name": "دانشگاه زابل",
    "major_id": "52",
    "major_name": "مهندسی عمران",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "14291",
      "14302"
    ],
    "capacity_rows": [
      {
        "major_name": "مهندسی عمران",
        "period": "روزانه",
        "province": "سيستان و بلوچستان",
        "campus": "استان سيستان و بلوچستان - دانشگاه زابل"
      },
      {
        "major_name": "مهندسی عمران",
        "period": "نوبت دوم",
        "province": "سيستان و بلوچستان",
        "campus": "استان سيستان و بلوچستان - دانشگاه زابل"
      }
    ]
  },
  {
    "program_id": "PROG_01740",
    "university_id": "ZABOL",
    "university_name": "دانشگاه زابل",
    "major_id": "81",
    "major_name": "ریاضیات و کاربردها",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "14285",
      "14296"
    ],
    "capacity_rows": [
      {
        "major_name": "ریاضیات و كاربردها",
        "period": "روزانه",
        "province": "سيستان و بلوچستان",
        "campus": "استان سيستان و بلوچستان - دانشگاه زابل"
      },
      {
        "major_name": "ریاضیات و كاربردها",
        "period": "نوبت دوم",
        "province": "سيستان و بلوچستان",
        "campus": "استان سيستان و بلوچستان - دانشگاه زابل"
      }
    ]
  },
  {
    "program_id": "PROG_01746",
    "university_id": "ZABOL",
    "university_name": "دانشگاه زابل",
    "major_id": "84",
    "major_name": "فیزیک",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "14288",
      "14299"
    ],
    "capacity_rows": [
      {
        "major_name": "فیزیک",
        "period": "روزانه",
        "province": "سيستان و بلوچستان",
        "campus": "استان سيستان و بلوچستان - دانشگاه زابل"
      },
      {
        "major_name": "فیزیک",
        "period": "نوبت دوم",
        "province": "سيستان و بلوچستان",
        "campus": "استان سيستان و بلوچستان - دانشگاه زابل"
      }
    ]
  },
  {
    "program_id": "PROG_01783",
    "university_id": "ZABOL",
    "university_name": "دانشگاه زابل",
    "major_id": "132",
    "major_name": "تاریخ",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "14347",
      "14350"
    ],
    "capacity_rows": [
      {
        "major_name": "تاريخ",
        "period": "روزانه",
        "province": "سيستان و بلوچستان",
        "campus": "ادامه استان سيستان و بلوچستان - دانشگاه زابل"
      },
      {
        "major_name": "تاريخ",
        "period": "نوبت دوم",
        "province": "سيستان و بلوچستان",
        "campus": "ادامه استان سيستان و بلوچستان - دانشگاه زابل"
      }
    ]
  },
  {
    "program_id": "PROG_01785",
    "university_id": "ZABOL",
    "university_name": "دانشگاه زابل",
    "major_id": "134",
    "major_name": "جغرافیا",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "14348",
      "14351"
    ],
    "capacity_rows": [
      {
        "major_name": "جغرافیا",
        "period": "روزانه",
        "province": "سيستان و بلوچستان",
        "campus": "ادامه استان سيستان و بلوچستان - دانشگاه زابل"
      },
      {
        "major_name": "جغرافیا",
        "period": "نوبت دوم",
        "province": "سيستان و بلوچستان",
        "campus": "ادامه استان سيستان و بلوچستان - دانشگاه زابل"
      }
    ]
  },
  {
    "program_id": "PROG_01965",
    "university_id": "ZANJAN",
    "university_name": "دانشگاه زنجان",
    "major_id": "84",
    "major_name": "فیزیک",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [
      "13884",
      "13886"
    ],
    "capacity_rows": [
      {
        "major_name": "فیزیک",
        "period": "روزانه",
        "province": "زنجان",
        "campus": "استان زنجان - دانشگاه زنجان"
      },
      {
        "major_name": "فیزیک",
        "period": "نوبت دوم",
        "province": "زنجان",
        "campus": "استان زنجان - دانشگاه زنجان"
      }
    ]
  }
]
```


## 11. Samples — 10 unmatched programs



```json
[
  {
    "program_id": "PROG_00985",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "44",
    "major_name": "مهندسی نرم‌افزار",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  },
  {
    "program_id": "PROG_00987",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "45",
    "major_name": "علوم کامپیوتر",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  },
  {
    "program_id": "PROG_00990",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "52",
    "major_name": "مهندسی عمران",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  },
  {
    "program_id": "PROG_00992",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "53",
    "major_name": "مهندسی صنایع",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  },
  {
    "program_id": "PROG_00994",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "58",
    "major_name": "مهندسی شیمی",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  },
  {
    "program_id": "PROG_00996",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "61",
    "major_name": "مهندسی پلیمر",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  },
  {
    "program_id": "PROG_00998",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "62",
    "major_name": "مهندسی مواد و متالورژی",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  },
  {
    "program_id": "PROG_01000",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "81",
    "major_name": "ریاضیات و کاربردها",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  },
  {
    "program_id": "PROG_01002",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "82",
    "major_name": "آمار و کاربردها",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  },
  {
    "program_id": "PROG_01004",
    "university_id": "GUILAN",
    "university_name": "دانشگاه گیلان",
    "major_id": "83",
    "major_name": "علوم داده",
    "course_type": "savabegh_dolati",
    "sanjesh_codes": [],
    "capacity_rows": []
  }
]
```


## 12. Samples — 10 unmatched capacity rows

These have no associated `program_id` under the pilot:



```json
[
  {
    "program_id": null,
    "sanjesh_code": "10001",
    "major_name": "آمار",
    "period": "روزانه",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  },
  {
    "program_id": null,
    "sanjesh_code": "10002",
    "major_name": "ریاضیات و كاربردها",
    "period": "روزانه",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  },
  {
    "program_id": null,
    "sanjesh_code": "10003",
    "major_name": "فیزیک",
    "period": "روزانه",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  },
  {
    "program_id": null,
    "sanjesh_code": "10004",
    "major_name": "مهندسی مکانيك بيوسیستم (اين رشته",
    "period": "روزانه",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  },
  {
    "program_id": null,
    "sanjesh_code": "10005",
    "major_name": "آمار",
    "period": "نوبت دوم",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  },
  {
    "program_id": null,
    "sanjesh_code": "10006",
    "major_name": "ریاضیات و كاربردها",
    "period": "نوبت دوم",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  },
  {
    "program_id": null,
    "sanjesh_code": "10007",
    "major_name": "علوم و مهندسی آب",
    "period": "نوبت دوم",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  },
  {
    "program_id": null,
    "sanjesh_code": "10008",
    "major_name": "زمین شناسي",
    "period": "روزانه",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  },
  {
    "program_id": null,
    "sanjesh_code": "10009",
    "major_name": "زیست شناسي جانوری",
    "period": "روزانه",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  },
  {
    "program_id": null,
    "sanjesh_code": "10010",
    "major_name": "زیست شناسي گياهي",
    "period": "روزانه",
    "province": "آذربايجان غربي",
    "campus": "استان آذربايجان غربي - دانشگاه اروميه"
  }
]
```


## 13. Step 1+2 decision

**Step 1 complete:** conservative university alias table created from observed data only.

**Step 2 complete:** read-only pilot join executed.

**Decision:** the pilot does **not** justify bulk enrichment. The next required step is an additional official/manual mapping source for university/program identity and Sanjesh selection-code linkage. Until that source exists, `program2s` must remain without mass `sanjesh_code` enrichment.
