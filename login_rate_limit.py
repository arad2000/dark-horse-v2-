"""Bounded, process-local login throttling (defense in depth, not a cluster quota).

No password, bearer token, or raw phone number is retained by these limiters.
The gateway must enforce a shared limit before running multiple workers/replicas.
Only the ASGI peer address is used; untrusted forwarding headers are ignored.
"""
from __future__ import annotations

import hashlib

from fastapi import HTTPException, Request

from ai_rate_limit import SlidingWindowRateLimiter

# Short windows avoid permanent account lockout. Successful logins count too:
# attackers must not bypass the budget by interleaving successful requests.
LOGIN_ACCOUNT_LIMITER = SlidingWindowRateLimiter(limit=5, window_seconds=60)
LOGIN_IP_LIMITER = SlidingWindowRateLimiter(limit=30, window_seconds=60)


def enforce_login_rate_limit(request: Request, phone: str) -> None:
    client = getattr(request, "client", None)
    peer = client.host if client else "unknown"
    allowed, retry_after = LOGIN_IP_LIMITER.allow(peer)
    if allowed:
        account_key = hashlib.sha256("".join(phone.split()).encode("utf-8")).hexdigest()
        allowed, retry_after = LOGIN_ACCOUNT_LIMITER.allow(account_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="تعداد تلاش‌های ورود بیش از حد مجاز است؛ کمی بعد دوباره تلاش کنید.",
            headers={"Retry-After": str(retry_after)},
        )
