# Dark Horse V2 — Billing, Premium & Admin Architecture Plan

## Scope

This document defines the next implementation phase. It does **not** enable PostgreSQL runtime cutover, does not modify scoring/ranking, and does not activate real payments.

## Current baseline

- JSON reference data remains the live source for scoring and recommendations.
- PostgreSQL is staging-only for the Hybrid migration.
- Production cutover gate remains `POSTGRES_RUNTIME_CUTOVER_APPROVED = False`.
- Existing frontend auth client already references `/api/v1/auth/*`, `/api/v1/me`, `/api/v1/me/quota`, `/api/v1/me/consume-test`, `/api/v1/me/save-result`, `/api/v1/billing/create-payment`, and a development-only premium activation endpoint.
- The current `main_v2.py` exposes only the V2 discovery and school-branch discovery endpoints; therefore Billing/Admin are not yet a complete backend feature.

## Target data model

### users
- `id` bigint primary key
- `public_id` uuid unique, non-secret identifier exposed to clients
- `name` varchar(200)
- `phone` varchar(32) unique, normalized
- `password_hash` text nullable when external auth is used later
- `role` enum/string: `user`, `admin`, `support`
- `status` enum/string: `active`, `suspended`, `deleted`
- `created_at`, `updated_at`, `last_login_at`

### auth_sessions
- `id` bigint primary key
- `user_id` FK users
- `token_hash` unique
- `expires_at`
- `revoked_at`
- `created_at`
- Never store a raw bearer token.

### premium_plans
- `id` bigint primary key
- `code` varchar(64) unique
- `name_fa` varchar(200)
- `duration_days` integer
- `price_minor` bigint
- `currency` varchar(8)
- `is_active` boolean
- `features` JSON
- `created_at`, `updated_at`

Store monetary values as integer minor units; do not use floating point for money.

### entitlements
- `id` bigint primary key
- `user_id` FK users
- `plan_id` FK premium_plans
- `source` string: `payment`, `grant`, `admin`, `promo`
- `starts_at`, `expires_at`
- `status` string: `active`, `expired`, `revoked`
- `order_id` FK orders nullable
- `created_at`, `updated_at`

Premium access is derived from active entitlements, never from a client-side flag.

### orders
- `id` bigint primary key
- `public_id` uuid unique
- `user_id` FK users
- `plan_id` FK premium_plans
- `amount_minor` bigint
- `currency` varchar(8)
- `status` string: `pending`, `paid`, `failed`, `cancelled`, `refunded`
- `created_at`, `paid_at`, `updated_at`

### payments
- `id` bigint primary key
- `order_id` FK orders
- `provider` string (`zarinpal`, future provider, etc.)
- `provider_request_id` nullable
- `provider_authority` nullable
- `provider_transaction_id` nullable
- `amount_minor` bigint
- `currency` varchar(8)
- `status` string: `initiated`, `redirected`, `verified`, `failed`, `refunded`
- `raw_callback` JSON nullable but sanitized; never store secrets
- `verification_response` JSON nullable and sanitized
- `created_at`, `verified_at`, `updated_at`
- Unique constraint on provider transaction identity where applicable.

### payment_events
- `id` bigint primary key
- `payment_id` FK payments
- `event_type` string
- `event_key` varchar(200) unique for idempotency
- `payload` JSON
- `created_at`

Callbacks/webhooks must be idempotent. A repeated provider callback must not create a second entitlement.

### admin_audit_logs
- `id` bigint primary key
- `admin_user_id` FK users
- `action` string
- `target_type` string
- `target_id` string
- `metadata` JSON
- `ip_address` nullable
- `created_at`

## Payment flow

1. Authenticated user selects a premium plan.
2. Server creates a `pending` order.
3. Server creates a payment with a unique provider request identity.
4. Server requests gateway payment/authority.
5. Client is redirected to the gateway.
6. Gateway returns to a server callback URL.
7. Server validates the callback and verifies the payment with the provider.
8. In one DB transaction: mark payment `verified`, mark order `paid`, create/update the user's entitlement, and append a payment event + audit record.
9. Duplicate callbacks are accepted safely but do not duplicate entitlements.

## Security requirements

- Never trust client-supplied price, plan duration, premium status, payment status, or transaction identity.
- Server resolves plan and price from `premium_plans`.
- Payment verification is server-to-server with the gateway.
- Raw access tokens/passwords/secrets are never written to DB logs.
- All admin mutations create an audit record.
- Refund/revoke operations must be explicit and auditable.
- Rate-limit auth and payment endpoints.

## Admin panel target

A separate protected admin surface should expose:

- Overview: users, active premium, paid orders, recent failures
- Users: search by phone/public ID, status, premium expiry
- Sessions/results: operational visibility only; no scoring edits
- Plans: create/activate/deactivate pricing plans
- Orders/payments: status, provider authority, verification result, refund state
- Entitlements: grant/revoke with mandatory reason
- Feedback: review satisfaction/accuracy feedback
- Audit: immutable admin action history
- System health: API, DB connectivity, migration state, cutover gate

Admin UI must not expose or allow direct editing of reference psychometric datasets from this panel.

## Implementation order

1. Add user/auth operational models and migration.
2. Add plan/order/payment/entitlement models and migrations.
3. Add service-layer transaction tests and idempotency tests.
4. Implement Billing API in disabled/sandbox mode first.
5. Add admin API with role enforcement.
6. Add admin UI against the admin API.
7. Integrate one real payment provider only after sandbox tests pass.
8. Keep PostgreSQL runtime cutover OFF until the existing Hybrid reference-data and dual-run gates are green.

## Explicit non-goals for this phase

- No change to M/V/S formulas.
- No PostgreSQL reference-data reads by the scoring engine.
- No production payment activation.
- No production DB cutover.
