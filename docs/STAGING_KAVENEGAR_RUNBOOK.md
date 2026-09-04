# Staging Kavenegar OTP Runbook

This runbook is for the staging environment only. Do not place API keys, OTP secrets, or other credentials in Git.

## Required staging configuration

Set these values in the deployment environment/secret store:

```text
OTP_PROVIDER=kavenegar
OTP_SECRET=<strong-random-secret>
KAVENEGAR_API_KEY=<staging-kavenegar-api-key>
KAVENEGAR_OTP_TEMPLATE=<approved-kavenegar-template>
```

`KAVENEGAR_SENDER` is required only when using the ordinary SMS send fallback instead of the verification template.

Keep these disabled in staging unless explicitly needed for a test:

```text
POSTGRES_RUNTIME_CUTOVER_APPROVED=false
DARK_HORSE_SHADOW_PERSISTENCE=false
ZARINPAL_PRODUCTION_APPROVED=false
```

`OTP_EXPOSE_DEBUG_CODE` must remain off for a realistic Kavenegar test.

## End-to-end acceptance path

1. `POST /api/v1/auth/register` with a fresh Iranian mobile number.
   - Expect HTTP 200.
   - Response must contain `challenge_id` and `expires_in`.
   - Response must not contain `debug_code`.
   - Kavenegar must receive the verification request for the normalized `+98...` receptor.

2. Enter the received OTP and call `POST /api/v1/auth/register/verify`.
   - Expect HTTP 200.
   - Expect a session token and public user data.
   - Expect the free entitlement to provide exactly one test credit.

3. Call `GET /api/v1/me` and `GET /api/v1/me/quota` with the bearer token.
   - Expect an active user.
   - Expect `credits_remaining` to be 1 before consumption.

4. Call `POST /api/v1/me/consume-test`.
   - Expect exactly one credit consumed.
   - Expect remaining credits to be 0.

5. Call `POST /api/v1/me/save-result` with a representative result payload.
   - Expect HTTP 200 and a persisted `result_id`.

6. Call `POST /api/v1/auth/login` with the same phone/password.
   - Expect HTTP 200 and a fresh session token.

## Negative acceptance tests

- Invalid OTP increments the attempt counter and returns HTTP 400.
- The sixth invalid attempt is rejected; the configured maximum remains 5.
- An expired challenge is rejected with HTTP 400.
- A consumed challenge cannot be reused.
- A duplicate registered phone is rejected.
- Missing `OTP_SECRET` with `OTP_PROVIDER=kavenegar` fails closed.
- Missing `KAVENEGAR_API_KEY` fails closed.
- Missing `KAVENEGAR_OTP_TEMPLATE` and missing `KAVENEGAR_SENDER` fails closed.
- Provider rejection/network failure returns an operational error without exposing the OTP.

## Security checks

Never log the OTP, API key, OTP secret, authorization bearer token, or raw password. Do not commit any staging credentials. Do not enable production ZarinPal or PostgreSQL runtime cutover as part of this test.
