# Sanjesh Record Capacity — Matching Audit v1

**Audit date:** 2026-09-29  
**Audit scope:** Step 0 only — data audit; no engine/program enrichment changes.  
**Audit base:** `deploy/liara-commercial-sandbox` at `49d3b6640bbfba2c7870ed67bc6520865198adc7`.

## 1. Source files

| File | Observed revision |
|---|---|
| `docs/data/sanjesh_record_capacity_full.json` | `8a5efdb3c19576ed3557107f13ebb74d2681eebd` |
| `docs/data/sanjesh_capacity_quota_rules_v1.json` | `526e23952fabd135d77240bf5be0682d6c950cf4` |
| `docs/data/sanjesh_record_capacity_sample.json` | `349ca37f138be1e69bf18e04c0aa7d9b3a803c65` |
| `program2s.json` | `0c2747057a35f3fdf4aa70c178ed68580e7c4537` |

The audit uses `sanjesh_record_capacity_full.json` as the capacity-row source and inspects `program2s.json` only for an existing official matching key. No synthetic code or fuzzy match is introduced.

## 2. Capacity dataset statistics

### 2.1 Row and code counts

- **total_rows:** 8,350
- **unique sanjesh_code:** 8,350
- **duplicate sanjesh_code values:** 0
- **rows missing sanjesh_code:** 0

### 2.2 Period distribution

| period | rows |
|---|---:|
| روزانه | 1,082 |
| نوبت دوم | 522 |
| پیام نور | 4,462 |
| غیرانتفاعی | 2,224 |
| مجازی | 6 |
| روزانه – غیردولتی | 19 |
| پردیس خودگردان | 22 |
| نامشخص | 13 |
| **جمع** | **8,350** |

### 2.3 Capacity validity

For this audit, a capacity value is treated as invalid when it is missing/null, non-numeric, or <= 0.

- **empty/missing capacity:** 0
- **non-numeric capacity:** 0
- **non-positive capacity:** 0
- **valid numeric capacity rows:** 8,350

Therefore, the full capacity file contains no row with an empty or invalid capacity under the above audit rule.

## 3. program2s matching-key audit

### 3.1 program2s structure

- **total programs:** 4,150
- **سوابق تحصیلی programs:** 2,196
- **با آزمون programs:** 1,954

Each program was inspected for an existing field named `sanjesh_code` and for obvious official-key variants containing both `sanjesh` and `code`.

### 3.2 sanjesh_code presence

- **program2s has sanjesh_code:** **No**
- **field name found:** **none**
- **sanjesh/code variant found:** **none**
- `program_id` exists, but it is **not** treated as a sanjesh code or official equivalent for this audit.

This means the required preferred key (`sanjesh_code`) is absent from program2s, and no documented formal equivalent key is present in the inspected program objects.

## 4. Exact matching result

Matching policy for Step 0:

> Exact match only on the official `sanjesh_code` (or a documented official equivalent already present in program2s). No name-only university/major matching is used.

Result:

- **capacity rows with exact official match:** 0 / 8,350
- **unique sanjesh codes matched:** 0 / 8,350
- **programs with an official capacity key:** 0 / 4,150
- **record programs currently matchable by official capacity key:** 0 / 2,196

### Conclusion

**Current program2s ↔ capacity linkage has a hard key gap.** The capacity catalog is internally complete at the audit level (8,350 rows, 8,350 unique codes, no invalid capacities), but program2s currently does not carry the `sanjesh_code` needed for deterministic 1:1 matching.

Accordingly:

1. **No capacity was written to any program.**
2. **No program was matched by university/major name.**
3. **No sanjesh code was invented or inferred.**
4. **No engine, G1–G4, Section 2, Hybrid, cutover, frontend, calibration, or scientific JSON was changed.**

## 5. Step 0 decision

**Status: AUDIT COMPLETE — MATCHING BLOCKED BY MISSING OFFICIAL KEY**

The next step is **not** program enrichment. Step 1 requires a documented source/contract that establishes the official `sanjesh_code` ↔ program2s mapping (or an explicitly approved formal equivalent key) before any capacity field may be attached to a program.

This PR contains documentation only.
