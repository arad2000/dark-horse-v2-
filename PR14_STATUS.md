# Runtime Integration Gate — PR #14

Staging-only draft. PostgreSQL runtime cutover remains hard-disabled and production ZarinPal activation remains off.

## Verified gates
- Runtime Integration Contract: GREEN
- PostgreSQL Migration Audit: GREEN
- PostgreSQL ORM Schema Parity: GREEN

## Current state
Alembic 0001→0007 migration/rollback audit is green, and ORM metadata now matches the migrated PostgreSQL structural contract after excluding intentional SQLite/ORM portability differences and implicit `ix_*` indexes.

No scoring, reference-data, M/V/S formula, Strategy/Spark ordering, or ranking semantics were changed.

## Next reviewed gate
Staging-only Kavenegar OTP configuration and end-to-end verification, using secrets supplied through the deployment environment only. No production OTP, production payment provider activation, or PostgreSQL runtime cutover is authorized by this branch.
