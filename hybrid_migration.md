# Dark Horse V2 — Hybrid PostgreSQL Migration

This branch prepares a safe, incremental migration.

## Non-negotiable safety gate

- **Production PostgreSQL cutover is OFF.**
- JSON reference/psychometric datasets remain versioned in Git and continue to feed the scoring engine.
- PostgreSQL is introduced for operational data: sessions, results, branch recommendations, feedback, and audit logs.
- No change to M/V/S formulas, Strategy question order, spark ordering, ranking, or recommendation semantics is allowed during migration work.
- PostgreSQL runtime may not be enabled by environment configuration alone; the explicit code gate in `migration_control.py` remains `False` until approved.
- Engine/API cutover happens only after a dual-run comparison proves equivalence.

## Phases

1. **PostgreSQL/SQLAlchemy infrastructure — COMPLETE**
   - `models.py`
   - `database.py`
   - SQLAlchemy/PostgreSQL/Alembic dependencies
   - explicit hard cutover gate
2. **Alembic migrations — COMPLETE (files authored; DB execution pending)**
   - `alembic.ini`
   - `alembic/env.py`
   - `alembic/versions/0001_initial_hybrid_schema.py`
3. Deterministic JSON-to-PostgreSQL seed/import with row-count and checksum verification.
4. Operational persistence for sessions/results/feedback/audit logs.
5. Dual-run comparison against the current JSON-backed engine.
6. API integration for operational writes/reads.
7. Production cutover only after the complete integrity audit passes.

## Validation rule

A migration is not considered complete merely because the schema exists. Before any cutover, reference data must be imported deterministically and compared against the JSON source by counts, unique codes, key structure, and stable content hashes. Engine outputs must then match the JSON-backed baseline for fixed fixtures, including M/V/S components, fit scores, ranking order, and alternative-path ordering.
