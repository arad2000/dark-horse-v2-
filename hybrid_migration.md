# Dark Horse V2 — Hybrid PostgreSQL Migration

This branch prepares a safe, incremental migration.

## Invariants

- JSON reference/psychometric datasets remain versioned in Git and continue to feed the scoring engine.
- PostgreSQL is introduced for operational data: sessions, results, branch recommendations, feedback, and audit logs.
- No change to M/V/S formulas, Strategy question order, spark ordering, ranking, or recommendation semantics is allowed during Phase 1.
- Engine/API cutover happens only after a dual-run comparison proves equivalence.

## Phases

1. PostgreSQL/SQLAlchemy infrastructure.
2. Alembic migrations.
3. Deterministic JSON-to-PostgreSQL seed/import with row-count and checksum verification.
4. Operational persistence for sessions/results/feedback/audit logs.
5. Dual-run comparison against the current JSON-backed engine.
6. API integration for operational writes/reads.
7. Production cutover only after integrity audit passes.
