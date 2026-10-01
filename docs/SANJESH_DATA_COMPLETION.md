# Sanjesh Data Completion — Phase 0 Gap Audit

**Audit date:** 1405-07-03 / 2026-09-25  
**Target year assumed for this audit:** 1405  
**Scope:** Phase 0 only — data/provenance gap audit.  
**Hard scope locks:** no `dark_horse_engine_v2.py`, no individuality scoring/weights, no Hybrid/PostgreSQL cutover, no payment, no fabricated locality mapping, no fabricated capacity, no numeric probability, no 90% accuracy claim.

## 1. Source-of-truth gate

The mandatory source for Phase 1 locality mapping is the official **دفترچه راهنمای انتخاب رشته (شماره ۲)** for the target year on the National Education Assessment Organization (Sanjesh) domain, together with the quota/locality explanations in that same year's booklet and the official selection-result report guidance.

As of **2026-09-25**, I could not independently verify a target-year **1405 undergraduate selection booklet No. 2** directly from `sanjesh.org` / its official download host using the available web index. Secondary pages and reposts were deliberately **not** used as a data source. Therefore:

> **Phase 1 province→region→pole extraction is BLOCKED until the official 1405 booklet is directly verifiable.**

No 1404 table, blog table, inferred table, or hand-built mapping is substituted for the 1405 source.

Official portal: https://sanjesh.org/

## 2. Dataset audited

Primary dataset:
- `program2s.json`
- Blob SHA: `f0dba97099a93d9daa8698271730c9a386dc61ec`
- metadata.version: `5.2 Final`
- metadata.last_updated: `1405-03-10`
- total programs: **4,150**
- total universities: **66**
- total majors represented in programs: **150**
- majors reference rows: **160**

Existing Phase-1 contract audit is retained in:
- `docs/SANJESH_ADMISSION_ENGINE_CONTRACT.md`
- `scripts/validate_program2s_admission_contract.py`

This Phase-0 document adds the explicit cross-tab and the 90%-path gap inventory; it does not modify admission behavior.

## 3. Core field coverage

All 4,150 programs have non-empty values for:
- `program_id`
- `major_id`
- `university.name`
- `university.province`
- `admission_info.method`
- `admission_info.course_type`
- `admission_info.bomi_type`

### University province coverage

The current program dataset contains universities in **20 distinct provinces**. This is not evidence that the national 31-province map is complete; it only describes the provinces represented by the current university rows.

The 20 observed university provinces are:
آذربایجان شرقی، اصفهان، البرز، ایلام، تهران، خراسان جنوبی، خراسان رضوی، خوزستان، زنجان، سیستان و بلوچستان، فارس، قم، مازندران، مرکزی، همدان، کردستان، کرمان، کرمانشاه، گیلان، یزد.

The Phase-1 validator must nevertheless validate the official locality source against **all 31 provinces**, not merely provinces appearing in `program2s.json`.

## 4. Explicit bomi_type × admission method matrix

| bomi_type | با آزمون | سوابق تحصیلی | جمع |
|---|---:|---:|---:|
| ostani | 958 | 2,196 | 3,154 |
| ghotbi | 561 | 0 | 561 |
| nahieyi | 0 | 0 | 0 |
| keshvari | 435 | 0 | 435 |
| **جمع** | **1,954** | **2,196** | **4,150** |

Observations:
1. Every record-method program is currently marked `ostani` in `program2s`.
2. No record-method program is marked `ghotbi`, `nahieyi`, or `keshvari`.
3. No `nahieyi` program exists in the current dataset.
4. The **561 ghotbi** programs are all exam-based, so the missing official province→region→pole mapping is a direct blocker for exact locality handling on these rows.

## 5. Cutoff / academic-record coverage

### Exam path — 1,954 programs

All 1,954 exam programs contain structurally complete:
- `cutoffs_predicted_1405`
- `cutoffs_historical`
- `cutoffs_bomi`

For all three structures, the following dimensions were present and numeric in the audited dataset:
- `zone_1`
- `zone_2`
- `zone_3`
- `isargaran_25`
- `isargaran_5`
- `shahid`

**Important provenance gap:** dataset metadata explicitly describes `cutoffs_bomi` as calculated from non-bomi. It must not be presented as an official Sanjesh cutoff unless independently supported by the target-year official source.

### Record path — 2,196 programs

All 2,196 record-method programs contain:
- `cutoffs_savabegh.minimum_gpa`
- `cutoffs_savabegh.minimum_traz`

The current stored threshold is therefore structurally available, but an applicant's Traz is not a current input in the fixed request contract; the engine must not invent a Traz comparison without a documented applicant-side value.

## 6. Required 90%-path gaps

### P0 — Official province → 9 regions mapping

**Missing:** a separately versioned official mapping of all 31 provinces into the 9 bomi regions, with booklet page/section citations.

**Why it matters:** without it, `nahieyi` eligibility cannot be evaluated from official data.

**Rule:** do not infer or copy a blog table.

### P0 — Official region → 5 poles mapping

**Missing:** a separately versioned official mapping of the 9 regions into the 5 poles (or an equivalently explicit province→pole table) with booklet page/section citations.

**Why it matters:** the current dataset has 561 `ghotbi` programs, but no independent pole mapping.

**Rule:** no inferred pole assignment.

### P1 — Capacity fields

No capacity key was found in any of the 4,150 program objects.

Missing/unknown:
- `capacity_total`
- `capacity_bomi`
- `capacity_free`
- any equivalent quota-specific capacity split

**Rule:** use `null` + explicit note when the official source does not expose an extractable value; never synthesize a number.

### P1 — Isargaran threshold in a usable score dimension

The dataset contains rank cutoffs for:
- `isargaran_25`
- `isargaran_5`
- `shahid`

But the 70%-style special-quota threshold rule is a **score/grade relationship**, not something that can be safely derived from a rank-only record.

Current gap:
- no official free-quota last-admitted score/grade paired to each program in a directly comparable dimension;
- no validated rank↔score calibration dataset for the target year.

**Rule before calibration:** if only rank is available, return an explicit note that the score-based threshold cannot be computed from the available inputs. Do not turn 70% into an invented rank formula.

### P1 — Record locality provenance

The current dataset marks all 2,196 record programs as `ostani`. This is a dataset fact, not proof of the official locality rule for every record program.

The official booklet must determine which record admissions are actually subject to provincial locality and which are national/open.

### P1 — Historical cutoff provenance

`cutoffs_historical` is structurally complete, but the dataset does not preserve a page/section citation per cutoff value.

The 90%-ready data layer needs:
- source year,
- source booklet/report,
- page/section,
- extraction date,
- and a clear distinction between official data and modeled/estimated values.

### P2 — Candidate bomi basis

The current API accepts `province` as a proxy input. The implementation documentation must explicitly state that the official bomi basis is determined from the candidate's applicable locality record (including the documented multi-year rule), and that a single province input is only a current product-side proxy until the exact official rule/data is modeled.

## 7. Safe current engine policy

Until the official Phase-1 locality map and missing provenance are locked:

- `keshvari`: do not provincial-filter.
- `ostani`: only use explicit province information already present in program data.
- `ghotbi` / `nahieyi`: do not claim definitive locality; emit an incomplete-locality note.
- Cutoff source order remains: `cutoffs_predicted_1405` → latest historical.
- `cutoffs_bomi` is not treated as an official source.
- Capacity is not applied while capacity data is absent.
- Special-quota threshold is not converted from rank to a fake 70% rank rule.
- Output remains qualitative only.
- No percentage probability and no 90% accuracy statement is permitted.

## 8. Phase gates

### Phase 0 — STATUS: COMPLETE

Deliverable:
- this document.

Scope check:
- docs only
- no engine changes
- no API changes
- no UI changes
- no scientific JSON changes
- no Hybrid/cutover changes
- no payment changes

### Phase 1 — STATUS: BLOCKED ON OFFICIAL SOURCE

Required before implementation:
1. Directly verifiable official 1405 booklet No. 2.
2. Exact page/section citations for the 9 bomi regions.
3. Exact page/section citations for the 5 bomi poles.
4. Reconciliation against the quota/locality explanation in the same booklet.
5. Then create:
   - `data/sanjesh_bomi_regions_1405.json`
   - Phase-1 validator
   - source-backed documentation

No Phase-1 JSON with invented/placeholder geographic assignments should be merged.

## 9. Acceptance criteria for the next PR

The next PR may be proposed only when the official target-year source is available and directly verifiable. It must:
- add only the official mapping JSON + validator + documentation;
- prove one-and-only-one region assignment for all 31 provinces;
- prove complete pole coverage;
- store citation metadata on each mapping row;
- contain no engine/scoring/Hybrid/payment changes;
- remain unmerged until technical-owner approval.

## 10. Audit provenance

This audit was calculated from the current `program2s.json` blob and the already-merged Phase-1 contract audit. The numerical cross-tab in §4 was recomputed from the full JSON payload rather than inferred from file names or aggregate labels.

