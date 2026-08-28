# Dark Horse V2 — Operational API Persistence Contract

This document prepares API persistence while PostgreSQL remains staging-only.

## Safety
- JSON remains the live scoring/reference source.
- PostgreSQL runtime cutover remains OFF.
- No API endpoint may use PostgreSQL reference tables for scoring or ranking before explicit approval.
- Operational writes may target PostgreSQL only when explicitly invoked by a future adapter; current main runtime is unchanged.

## Persistable entities
- `UserSession`
- `DiscoveryResult`
- `BranchRecommendation`
- `UserFeedback`
- `AuditLog`

## Contract invariants
1. Session UUID is unique.
2. A result references an existing session and major.
3. A branch recommendation references an existing session and school branch.
4. Scores must be finite and within 0..100.
5. Ranking is deterministic and contiguous when supplied.
6. Feedback references an existing session and, when supplied, an existing major.
7. Persistence failures must rollback the complete transaction.
8. Reference JSON is never mutated by operational persistence.

## Future cutover sequence
`JSON live scoring -> operational persistence validated -> dual-run -> approval -> runtime feature flag -> production DB reference reads`
