# Security hardening plan — authentication token storage

## Scope
This phase does not rewrite the frontend or authentication service. The current bearer-token flow remains supported while the migration is prepared.

## Target state
Move the browser session token from JavaScript-accessible localStorage to a secure, HttpOnly, Secure cookie with an appropriate SameSite policy. Keep the server authoritative for session state and quota.

## Migration sequence
1. Add cookie-backed session issuance and resolution on the API without removing the bearer-token path.
2. Add CSRF protection for state-changing cookie-authenticated requests.
3. Ship the cookie path behind an explicit feature flag in staging.
4. Instrument authentication failures, refresh/logout behavior, and cross-origin requests.
5. Move the production frontend to cookie auth after staging evidence is green.
6. Remove client-side bearer-token persistence and then remove the legacy bearer-token path after a deprecation window.

## CSP baseline
The frontend now sends a baseline CSP from docs/index.html. It permits same-origin scripts, the existing jsDelivr stylesheet/font dependency, API calls to api.asbe-siah.ir, and normal image/PWA resources. Inline styles remain allowed because the current UI embeds style blocks; inline scripts are not permitted.

## Non-goals
No scoring weights, reference-data semantics, quota rules, or payment semantics are changed by this hardening phase.
