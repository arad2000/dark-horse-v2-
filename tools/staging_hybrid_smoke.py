"""Shared-DB staging smoke for the hybrid commercial path.

The staging deployment is expected to expose multiple HTTPS replica origins
backed by one PostgreSQL database. The test deliberately moves a single
registration/verification/quota/consume flow across replicas, then creates a
payment through another replica.
"""
from __future__ import annotations

import os
import secrets
import string
from urllib.parse import urlparse

import httpx

PRODUCTION_HOSTS = {"api.asbe-siah.ir", "www.asbe-siah.ir", "asbe-siah.ir"}


def fail(message: str) -> None:
    raise SystemExit(message)


def load_replicas() -> list[str]:
    raw = os.getenv("STAGING_REPLICA_URLS", "").strip()
    replicas = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    if len(replicas) < 2:
        fail("STAGING_REPLICA_URLS must contain at least two HTTPS replica origins")
    for value in replicas:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            fail("all staging replica URLs must be explicit HTTPS origins")
        if parsed.hostname and parsed.hostname.lower() in PRODUCTION_HOSTS:
            fail("production hosts are forbidden for the staging hybrid gate")
    return replicas


def request_json(
    client: httpx.Client,
    replica: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    json: dict | None = None,
) -> tuple[httpx.Response, dict]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = client.request(method, replica + path, headers=headers, json=json)
    try:
        body = response.json()
    except ValueError:
        body = {}
    return response, body if isinstance(body, dict) else {}


def main() -> None:
    replicas = load_replicas()
    timeout = float(os.getenv("STAGING_SMOKE_TIMEOUT", "20"))
    password = "Staging-" + secrets.token_urlsafe(12)[:20] + "!"
    phone = "09" + "".join(secrets.choice(string.digits) for _ in range(9))
    name = "Hybrid Staging QA"

    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        first, first_body = request_json(
            client,
            replicas[0],
            "POST",
            "/api/v1/auth/register",
            json={"name": name, "phone": phone, "password": password},
        )
        if first.status_code != 200:
            fail(f"register failed on replica 1: HTTP {first.status_code}")

        challenge_id = first_body.get("challenge_id")
        debug_code = str(first_body.get("debug_code") or "")
        if not challenge_id:
            fail("register did not return challenge_id")
        if len(debug_code) != 6 or not debug_code.isdigit():
            fail(
                "staging OTP smoke requires OTP_EXPOSE_DEBUG_CODE=true on the "
                "staging deployment so the test can verify without a live SMS inbox"
            )

        second, second_body = request_json(
            client,
            replicas[1],
            "POST",
            "/api/v1/auth/register/verify",
            json={"challenge_id": challenge_id, "code": debug_code},
        )
        if second.status_code != 200:
            fail(f"OTP verify failed on replica 2: HTTP {second.status_code}")

        token = str(second_body.get("token") or "")
        if not token:
            fail("OTP verification returned no session token")
        with open("/tmp/darkhorse-staging-token", "w", encoding="utf-8") as handle:
            handle.write(token)

        health_results = []
        for index, replica in enumerate(replicas, start=1):
            response, body = request_json(client, replica, "GET", "/api/v1/runtime/quota-health")
            if response.status_code != 200 or body.get("migration_ok") is not True:
                fail(f"quota-health failed on replica {index}: HTTP {response.status_code}")
            if body.get("postgres_runtime_cutover_approved") is not False:
                fail(f"cutover is not disabled on replica {index}")
            health_results.append(
                {
                    "replica": index,
                    "migration": body.get("alembic_revisions"),
                    "migration_ok": body.get("migration_ok"),
                    "cutover": body.get("postgres_runtime_cutover_approved"),
                }
            )

        quota_replica = replicas[2 % len(replicas)]
        quota, quota_body = request_json(
            client, quota_replica, "GET", "/api/v1/me/quota", token=token
        )
        if quota.status_code != 200 or quota_body.get("credits_remaining") != 1:
            fail(f"initial quota failed: HTTP {quota.status_code} body={quota_body}")

        session_uuid = secrets.token_urlsafe(18)
        consume_one, consume_one_body = request_json(
            client,
            replicas[0],
            "POST",
            "/api/v1/me/consume-test",
            token=token,
            json={"session_uuid": session_uuid},
        )
        if consume_one.status_code != 200 or consume_one_body.get("consumed") != 1:
            fail(f"first consume failed: HTTP {consume_one.status_code} body={consume_one_body}")

        consume_two, consume_two_body = request_json(
            client,
            replicas[1],
            "POST",
            "/api/v1/me/consume-test",
            token=token,
            json={"session_uuid": session_uuid},
        )
        if (
            consume_two.status_code != 200
            or consume_two_body.get("consumed") != 0
            or consume_two_body.get("already_consumed") is not True
            or consume_two_body.get("credits_remaining") != 0
        ):
            fail(f"idempotent consume failed: HTTP {consume_two.status_code} body={consume_two_body}")

        payment_replica = replicas[2 % len(replicas)]
        payment, payment_body = request_json(
            client, payment_replica, "POST", "/api/v1/billing/create-payment", token=token
        )
        if payment.status_code != 200:
            fail(f"create-payment failed on staging: HTTP {payment.status_code} body={payment_body}")
        for field in ("order_id", "payment_id", "provider", "payment_url"):
            if not payment_body.get(field):
                fail(f"create-payment response missing {field}")

    print(
        {
            "ok": True,
            "replica_count": len(replicas),
            "register_replica": 1,
            "verify_replica": 2,
            "quota_replica": (2 % len(replicas)) + 1,
            "consume_replicas": [1, 2],
            "payment_replica": (2 % len(replicas)) + 1,
            "health": health_results,
            "idempotency": "pass",
            "create_payment": "pass",
        }
    )


if __name__ == "__main__":
    main()
