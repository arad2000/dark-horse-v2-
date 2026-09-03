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
2. **Alembic migrations — COMPLETE** (`0001` through `0005_payment_txn_partial_unique`)
3. **Deterministic JSON-to-PostgreSQL seed — COMPLETE in staging CI** (BIOTM-001..007 first-class; catalog 1106)
4. **Staged reference verification — COMPLETE in staging CI**
5. **Operational persistence and API contracts — COMPLETE in staging CI**
6. **Payment layer — COMPLETE for staging contract**
   - Credit-based: `free_1_test` and `pack_3_tests`
   - Price is server-side: 249,000 Toman = 2,490,000 IRR
   - Provider transaction uniqueness is a PostgreSQL **partial** unique index so pending NULL transaction ids can coexist
7. **Commercial HTTP mount — COMPLETE in staging**
   - `commercial_api.py` mounted on `main_v2.py` as `/api/v1`
   - Endpoints: register/login/logout, quota, atomic consume-test, create-payment, callback
   - JSON scoring `/api/v2/darkhorse/*` remains unbilled in this phase
8. **Auth/role hardening — COMPLETE in staging**
   - Iranian mobile validation
   - Suspended/inactive users cannot authenticate or resolve sessions
   - Public JSON never returns internal sequential `user_id`, `payment_id`, or `entitlement_id`
   - Logout revokes the bearer session
   - Admin HTTP remains on `admin_http_api.py` and is **not** mounted on `main_v2.py`
9. **Controlled JSON ↔ PostgreSQL dual-run — COMPLETE for staging fixtures**
10. **Production cutover — BLOCKED / NOT APPROVED**
    - `POSTGRES_RUNTIME_CUTOVER_APPROVED=false`
    - `DARK_HORSE_SHADOW_PERSISTENCE=false`
    - This branch must not be merged to `main`

## Final gate

The remaining product gate is an explicit reviewed commit that sets `POSTGRES_RUNTIME_CUTOVER_APPROVED = True` **after** this branch's CI is green **and** after a rebase onto current `main`. **No runtime switch, merge to `main`, or production deployment is permitted from this commercial/auth hardening work alone.**
