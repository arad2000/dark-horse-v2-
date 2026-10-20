# API request-body security review — 2026-10-20

## Scope

This review applies byte ceilings before FastAPI parses JSON on API routes that previously had no transport-level body cap. It does not change scoring, catalog or motive data, authentication rules, quota semantics, Hybrid/cutover, payment behavior, callback configuration, Liara environment values, or CORS policy.

## Request-body ceilings proposed in Draft PR

The new ASGI middleware checks both a declared `Content-Length` and the bytes actually streamed; it rejects invalid lengths with HTTP 400 and oversized bodies with HTTP 413 before calling the endpoint.

| Method and path | Ceiling | Access / reason |
|---|---:|---|
| `POST /api/v1/auth/register` | 8 KiB | Public registration |
| `POST /api/v1/auth/register/verify` | 4 KiB | Public OTP verification |
| `POST /api/v1/auth/login` | 8 KiB | Public login |
| `POST /api/v1/admission/chance` | 32 KiB | Public admission comparison; input includes lists |
| `POST /api/v1/me/consume-test` | 4 KiB | Authenticated, small session identifier |
| `POST /api/v1/me/save-result` | 128 KiB | Authenticated result summary is a nested dictionary |
| `POST /api/v2/darkhorse/discover` | 16 KiB | Public discover; enforce existing ceiling before parsing too |
| `POST /api/v2/darkhorse/branch-discovery` | 16 KiB | Public branch discover; enforce existing ceiling before parsing too |
| `POST /api/v2/darkhorse/counsel` | 32 KiB | Public counsel; enforce existing ceiling before parsing too |

The public feedback routes `POST /api/v1/feedback` and `POST /api/feedback/submit` already stream and enforce a 32 KiB cap in `feedback_api.py`, so their body readers are not replaced. GET-only health/root routes do not consume JSON request bodies. Admin credit grant/revoke routes are privileged and have bounded model fields; they are not included in the public-route cap list.

## CSP decision: deferred

No Content-Security-Policy header is added in this pass. We do not have a successful live browser verification covering the currently deployed PWA/service-worker behavior and the current Android-to-Chrome same-origin payment handoff. A restrictive CSP could block scripts, worker registration, API calls, or the current handoff. Revisit CSP only after a dedicated non-customer end-to-end browser test covers home → journey → discover result, PWA startup/update, and the existing Chrome handoff. This is a deferral for test evidence, not an approval to change payment behavior.

## Explicit exclusions

- `POST /api/v1/billing/create-payment` and `GET /api/v1/billing/callback` are excluded from this PR because payment is locked for this round.
- CORS remains restricted to the current `https://asbe-siah.ir` origin; no origins are added.
- The Hybrid Migration Audit / PostgreSQL cutover path is out of scope and remains unchanged.
- This PR is Draft until supervisor review; no merge is implied.
