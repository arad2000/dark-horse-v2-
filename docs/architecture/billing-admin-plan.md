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

## Security requirements

- Never trust client-supplied price, credits, premium status, payment status, provider transaction id, or entitlement size.
- Never expose internal sequential database ids (`user.id`, `payment.id`, `entitlement.id`) on the public HTTP surface.
- Verify payment server-to-server using the amount stored on the order.
- Store hashes for access tokens, not raw tokens.
- Suspended or deleted users cannot authenticate, resolve a session, or consume credits.
- Treat callback/webhook delivery as at-least-once and therefore idempotent.

## Admin panel target

Admin HTTP currently lives in `admin_http_api.py` as a **standalone staged app**. It must not be mounted on `main_v2.py` until an explicit later phase.

## Rollout constraints

- `main` must not be merged from this staging branch yet.
- Do not merge or deploy to Liara.
- PostgreSQL runtime cutover remains OFF.

## Implementation order

1. Credit-based SQL model + migration ✅
2. Credit service and atomic consumption/entitlement issuance ✅
3. Mock provider ✅
4. Real ZarinPal provider contract ✅
5. Billing API in sandbox mode, mounted on `/api/v1` ✅
6. Auth/role enforcement + public-id contract + logout ✅
7. Admin API (standalone staged app; not mounted on `main_v2`)
8. Admin UI
9. Sandbox payment tests with real provider credentials
10. Only later: production payment activation and PostgreSQL runtime cutover
