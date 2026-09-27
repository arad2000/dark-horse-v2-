# Sanjesh Table 5 — Step 2 Audit

Base: `deploy/liara-commercial-sandbox` after PR #101 and #102.

## Scope

Only `method=سوابق تحصیلی` + `course_type=savabegh_dolati`.

No cutoff, capacity, scoring, Hybrid, or Azad policy changes.

## Result

The current `program2s.json` is already in the required Table 5 state. Re-applying the deterministic mapping produced **0 bomi_type changes**.

- savabegh_dolati programs: **580**
- unresolved_table5: **322**
- bomi_type changed: **0**

### bomi_type counts

| type | before | after |
|---|---:|---:|
| ostani | 2040 | 2040 |
| nahiyei | 848 | 848 |
| ghotbi | 444 | 444 |
| keshvari | 496 | 496 |
| null | 322 | 322 |

The unchanged global counts are expected because the requested mapping is already present in the base data. The step therefore locks the state with regression tests rather than rewriting identical JSON.

## Resolved examples

- `PROG_00990` — major 52 — مهندسی عمران — nahiyei
- `PROG_01000` — major 81 — ریاضیات و کاربردها — nahiyei
- `PROG_01029` — major 102 — علوم سیاسی — ghotbi

## Unresolved examples

- `PROG_00985` — major 44 — مهندسی نرم‌افزار
- `PROG_00992` — major 53 — مهندسی صنایع
- `PROG_00998` — major 62 — مهندسی مواد و متالورژی

All unresolved records remain `bomi_type=null` with `bomi_type_rule=unresolved_table5`; no geographic type is invented.

## Regression

- `PROG_03158`: existing Payam Noor → nahiyei behavior remains covered.
- `PROG_01000`: Table 5 nahiyei, Gilan included / Tehran excluded.
- `PROG_01029`: Table 5 ghotbi, Gilan included / Tehran excluded.
