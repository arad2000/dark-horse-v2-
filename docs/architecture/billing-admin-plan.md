# Dark Horse V2 — Credit Billing, Premium & Admin Architecture Plan

## Scope

This phase defines and tests the commercial model without enabling PostgreSQL runtime cutover, changing scoring/ranking, or merging to `main`/Liara.

## Product model (authoritative)

Dark Horse is **not a time-based subscription product**.

- Free tier: exactly **1 test credit** per user.
- Paid plan: `pack_3_tests`.
- Price: **249,000 Toman** = **2,490,000 Rial** when stored in IRR.
- Successful verified payment grants **exactly 3 additional test credits**.
- `credits_remaining` is the source for test availability.
- Expiration is optional; the normal product state is **non-expiring** (`expires_at = NULL`).

The server determines plan, amount and credit grant from the DB. Client payloads cannot override them.

## Target data model

### users
- bigint `id` primary key
- UUID `public_id` unique/non-secret
- name, normalized phone, password hash
- role: `user`, `admin`, `support`
- status: `active`, `suspended`, `deleted`

### auth_sessions
- user FK
- unique `token_hash`; never store raw bearer tokens
- expires/revocation timestamps

### premium_plans
- unique `code`
- `plan_type = credits`
- nullable `duration_days` kept only as a legacy/optional field
- integer `credits_granted`
- integer `price_minor` in stored currency units
- active flag and feature JSON

Canonical plans:

| code | credits | price | expiration |
|---|---:|---:|---|
| `free_1_test` | 1 | 0 IRR | none |
| `pack_3_tests` | 3 | 2,490,000 IRR (249,000 Toman) | none |

### entitlements
- user FK + plan FK
- source: `free`, `payment`, `grant`, `admin`, `promo`
- `credits_granted`
- `credits_remaining`
- `starts_at`
- nullable `expires_at`
- status
- optional order FK

A verified payment creates one payment entitlement with exactly `plan.credits_granted` remaining credits. The free entitlement is idempotently provisioned with exactly one credit.

### orders / payments / payment_events
- server-side amount copied from the selected DB plan
- provider authority/request/transaction identifiers
- payment verification response
- unique provider + transaction identity
- unique `payment_events.event_key`
- duplicate callbacks must never grant a second entitlement

## Payment flow

`select plan -> create pending order -> create payment attempt -> provider request -> gateway redirect -> callback -> server-side verify -> atomic paid order + verified payment + exactly 3 credits + event/audit`

The same order is idempotent even if a gateway callback is replayed with a different callback event key.

## Providers: parallel development

### Mock provider
Used for deterministic CI and local integration tests.

### Real ZarinPal provider
Implemented against the current REST v4 request/verify flow. It is developed **in parallel** with the Mock provider and must not be blocked by Mock completion. Network calls occur only when explicitly invoked and credentials are present.

The current ZarinPal Lab examples use:
- request: `POST https://api.zarinpal.com/pg/v4/payment/request.json`
- verify: `POST https://api.zarinpal.com/pg/v4/payment/verify.json`
- payment redirect via `https://www.zarinpal.com/pg/StartPay/{authority}`

See the ZarinPal Lab sample for the request/authority flow. citeturn623801search0turn623801search1

## Security requirements

- Never trust client-supplied price, credits, premium status, payment status, provider transaction id, or entitlement size.
- Verify payment server-to-server using the amount stored on the order.
- Store hashes for access tokens, not raw tokens.
- Do not log passwords, raw access tokens, merchant secrets, or unsanitized sensitive callback data.
- Rate-limit authentication and payment endpoints.
- Make payment verification and entitlement issuance atomic.
- Treat callback/webhook delivery as at-least-once and therefore idempotent.

## Admin panel target

Protected admin API/UI should expose operational controls only:

- overview / health
- users and account status
- test credits / entitlements
- plans/pricing
- orders/payments/verification status
- refunds/revocations with mandatory reason
- feedback
- immutable admin audit history

The admin panel must not edit the psychometric/reference JSON or scoring parameters directly.

## Rollout constraints

- `main` must not be merged from this staging branch yet.
- Do not merge or deploy to Liara.
- PostgreSQL runtime cutover remains OFF.
- Reference-data migration and the `BIOTM-*` blocker remain independent gates.
- Mock and real ZarinPal development proceed in parallel.

## Implementation order

1. Credit-based SQL model + migration ✅
2. Credit service and atomic consumption/entitlement issuance ✅
3. Mock provider ✅
4. Real ZarinPal provider contract ✅
5. Billing API in disabled/sandbox mode
6. Auth/role enforcement
7. Admin API
8. Admin UI
9. Sandbox payment tests with real provider credentials
10. Only later: production payment activation and PostgreSQL runtime cutover
