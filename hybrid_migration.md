# Dark Horse V2 — Hybrid PostgreSQL Migration

This branch prepares and validates a safe, incremental migration.

## Non-negotiable safety gate

- **Production PostgreSQL cutover is OFF.**
- JSON reference/psychometric datasets remain versioned in Git and continue to feed the scoring engine.
- PostgreSQL is used for operational data: sessions, results, branch recommendations, feedback, and audit logs.
- No change to M/V/S formulas, Strategy question order, spark ordering, ranking, or recommendation semantics is allowed during migration work.
- PostgreSQL runtime may not be enabled by environment configuration alone; the explicit code gate in `migration_control.py` remains `False` until approval.
- Engine/API cutover happens only after the complete integrity audit and controlled dual-run pass.

## Current validation status

1. **PostgreSQL/SQLAlchemy infrastructure — COMPLETE**
   - `models.py`
   - `database.py`
   - SQLAlchemy/PostgreSQL/Alembic dependencies
   - explicit hard cutover gate
2. **Alembic migrations — COMPLETE**
   - `alembic.ini`
   - `alembic/env.py`
   - migrations `0001_initial_hybrid_schema` through `0004_txn_unique`
3. **Deterministic JSON-to-PostgreSQL seed — COMPLETE in staging CI**
   - Reference JSON remains source of truth.
   - Counts and source SHA-256 values are reported.
   - **BIOTM correction complete:** `BIOTM-001..007` exist as first-class medical-biotechnology motives (distinct from `BIOT-001..007`). Every unresolved motive reference now fails closed.
4. **Staged reference verification — COMPLETE in staging CI**
   - Exact content/key comparisons pass for micro-motives (1106), 160 majors, 4 school branches, 30 value poles, and 125 strategy options.
   - All many-to-many routes, including BIOTM, are verified exactly.
5. **Operational persistence and API contracts — COMPLETE in staging CI**
   - Sessions, results, feedback, audit logs, RBAC, admin API/HTTP, and shadow safety contracts are covered.
6. **Payment layer — COMPLETE for staging contract**
   - Credit-based product model: `free_1_test` and `pack_3_tests`.
   - `pack_3_tests` grants exactly 3 credits after verified payment.
   - Price is server-side: 249,000 Toman = 2,490,000 IRR.
   - Mock and real ZarinPal adapters share one provider contract; Mock remains deterministic for CI.
7. **Controlled JSON ↔ PostgreSQL dual-run — COMPLETE for staging fixtures**
   - JSON engine remains the live baseline.
   - PostgreSQL engine is staging-only.
   - Semantic output comparison covers recommendations, ordering, scores/components, evidence, warnings, best branch, and alternative paths.
   - Dual-run fixtures include a dedicated `medical_biotech` case (`BIOTM-001/004/007`).
8. **Production cutover — BLOCKED / NOT APPROVED**
   - `POSTGRES_RUNTIME_CUTOVER_APPROVED=false`
   - `DARK_HORSE_SHADOW_PERSISTENCE=false`
   - This BIOTM branch must not be merged to `main`.
   - Liara production deployment is intentionally postponed until post-cutover approval.

## Validation rule

A migration is not considered complete merely because the schema exists. Reference data must be imported deterministically and compared against the JSON source by counts, unique codes, key structure, and stable content hashes. Engine outputs must then match the JSON-backed baseline for fixed fixtures, including M/V/S components, fit scores, ranking order, and alternative-path ordering.

## Final gate

The remaining product gate is an explicit reviewed commit that sets `POSTGRES_RUNTIME_CUTOVER_APPROVED = True` **after** this branch's CI is green **and** after a rebase onto current `main`. **No runtime switch, merge to `main`, or production deployment is permitted from this BIOTM correction alone.**
