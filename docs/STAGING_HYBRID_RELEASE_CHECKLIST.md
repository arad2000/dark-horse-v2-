# Staging Hybrid / Release Checklist

This checklist is the final operational gate for PR #42. It is intentionally
staging-only. Production PostgreSQL runtime cutover must remain disabled until
the owner gives written approval.

## 1. Staging configuration

- [ ] GitHub Environment: `staging`
- [ ] `STAGING_REPLICA_URLS` contains at least two HTTPS replica origins backed
      by the same PostgreSQL database.
- [ ] `STAGING_SCALE_URL` points to a representative staging endpoint.
- [ ] `POSTGRES_RUNTIME_CUTOVER=false`
- [ ] `POSTGRES_RUNTIME_CUTOVER_APPROVED=false`
- [ ] Staging OTP is testable without exposing a production OTP path
      (the current smoke gate accepts the explicit staging-only
      `OTP_EXPOSE_DEBUG_CODE=true` mechanism).

## 2. Shared-DB commercial smoke

Run:

```text
Staging Hybrid Gate
```

Required flow:

```text
register (replica A)
  -> OTP verify (replica B)
  -> quota (another replica)
  -> consume(session_uuid) (replica A)
  -> consume(session_uuid) again (replica B)
  -> create-payment (another replica)
```

Acceptance:

- [ ] Every request returns the expected HTTP status.
- [ ] The second consume returns `already_consumed=true` and does not charge
      another credit.
- [ ] `/api/v1/runtime/quota-health` reports `migration_ok=true` on every
      configured replica.
- [ ] Every replica reports cutover disabled.
- [ ] Create-payment returns an order, payment id, provider and payment URL.
- [ ] The smoke artifact is retained with the staging deployment evidence.

## 3. Real staging scale

Run the same workflow's real-staging scale round with a bounded request
profile. The CI safety guard rejects known production hosts.

Required evidence:

- [ ] Request count and concurrency recorded.
- [ ] p95 latency recorded.
- [ ] Error-rate recorded.
- [ ] Error-rate is exactly 0 for the acceptance run.
- [ ] Staging target is HTTPS and is not a production hostname.

## 4. Post-deploy release smoke

After every staging/production deployment, repeat:

1. API root / health endpoint responds.
2. One authenticated `consume-test` succeeds for a fresh `session_uuid`.
3. Repeating the same `session_uuid` is idempotent.
4. One `create-payment` request succeeds.
5. `/api/v1/runtime/quota-health` still reports the expected Alembic revision
   and cutover disabled.

## 5. Merge decision

PR #42 remains Draft / Unmerged until all sections above are evidenced.

No scoring/ranking changes are part of this gate.

Production PostgreSQL runtime cutover requires a separate written owner
approval and is not enabled by this checklist.
