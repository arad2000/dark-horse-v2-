"""Atomic, process-local rate limiting for the real password-login endpoint.

The limiter reserves capacity before password verification, so concurrent requests
cannot all pass the same remaining slot. Keys are HMACed and never retain raw
phone numbers or client IP addresses. State is intentionally process-local; use a
shared store before scaling the API to multiple independent workers/replicas.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import os
import secrets
import threading
import time
from collections import deque
from typing import Callable


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) and value > 0 else default


class LoginAttemptRateLimiter:
    """Sliding-window limiter with atomic reservations for IP and account keys."""

    def __init__(
        self,
        *,
        account_max_failures: int = 5,
        ip_max_failures: int = 60,
        window_seconds: float = 900.0,
        max_tracked_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if account_max_failures < 1 or ip_max_failures < 1:
            raise ValueError("failure limits must be positive")
        if window_seconds <= 0 or not math.isfinite(window_seconds):
            raise ValueError("window_seconds must be positive")
        if max_tracked_keys < 2:
            raise ValueError("max_tracked_keys must be at least two")

        self.account_max_failures = int(account_max_failures)
        self.ip_max_failures = int(ip_max_failures)
        self.window_seconds = float(window_seconds)
        self.max_tracked_keys = int(max_tracked_keys)
        self._clock = clock
        self._salt = secrets.token_bytes(32)
        self._lock = threading.Lock()
        self._failures: dict[str, deque[float]] = {}
        self._in_flight: dict[str, int] = {}
        self._reservations: dict[int, tuple[str, str]] = {}
        self._next_reservation = 0

    def _key(self, kind: str, value: str | None) -> str:
        normalized = "".join((value or "").split())
        digest = hmac.new(
            self._salt,
            (kind + "\0" + normalized).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{kind}:{digest}"

    def _keys(self, client_ip: str | None, account: str | None) -> tuple[str, str]:
        # Empty/missing IPs share one conservative bucket rather than bypassing
        # the IP control. The account key is based on normalized request input,
        # not on a database lookup, so unknown accounts receive identical limits.
        return self._key("ip", client_ip), self._key("account", account)

    def _limit(self, key: str) -> int:
        return self.ip_max_failures if key.startswith("ip:") else self.account_max_failures

    def _prune_key(self, key: str, now: float) -> None:
        attempts = self._failures.get(key)
        if attempts is not None:
            while attempts and now - attempts[0] >= self.window_seconds:
                attempts.popleft()
            if not attempts and self._in_flight.get(key, 0) == 0:
                self._failures.pop(key, None)

    def _active_keys(self) -> set[str]:
        return set(self._failures) | set(self._in_flight)

    def _make_room(self, requested: tuple[str, str], now: float) -> bool:
        active = self._active_keys()
        if len(active | set(requested)) <= self.max_tracked_keys:
            return True
        # Capacity is only swept when approaching the bound; normal requests
        # prune just their own two keys and do not scan the whole table.
        for key in tuple(active):
            self._prune_key(key, now)
        return len(self._active_keys() | set(requested)) <= self.max_tracked_keys

    def _retry_after(self, keys: list[str], now: float) -> int:
        waits = []
        for key in keys:
            attempts = self._failures.get(key)
            if attempts and len(attempts) + self._in_flight.get(key, 0) >= self._limit(key):
                waits.append(max(1, math.ceil(attempts[0] + self.window_seconds - now)))
            elif self._in_flight.get(key, 0) >= self._limit(key):
                waits.append(1)
        return max(waits, default=max(1, math.ceil(self.window_seconds)))

    def reserve_attempt(self, *, client_ip: str | None, account: str | None) -> tuple[int | None, int]:
        """Reserve one slot or return (None, retry_after_seconds) when limited."""
        now = self._clock()
        with self._lock:
            keys = self._keys(client_ip, account)
            for key in keys:
                self._prune_key(key, now)

            blocked = [
                key
                for key in keys
                if len(self._failures.get(key, ())) + self._in_flight.get(key, 0) >= self._limit(key)
            ]
            if blocked:
                return None, self._retry_after(blocked, now)

            if not self._make_room(keys, now):
                return None, max(1, math.ceil(self.window_seconds))

            self._next_reservation += 1
            reservation = self._next_reservation
            self._reservations[reservation] = keys
            for key in keys:
                self._in_flight[key] = self._in_flight.get(key, 0) + 1
            return reservation, 1

    def finish_attempt(self, reservation: int, *, outcome: str) -> None:
        """Complete a reservation as failure, success, or abandon.

        A successful authentication clears only that account's failure window.
        The aggregate IP window is retained so a success cannot erase unrelated
        failures from the same network. 'abandon' releases capacity without
        recording a failure when the backend fails for a non-credential reason.
        """
        if outcome not in {"failure", "success", "abandon"}:
            raise ValueError("outcome must be failure, success, or abandon")

        with self._lock:
            keys = self._reservations.pop(reservation, None)
            if keys is None:
                return
            now = self._clock()

            for key in keys:
                remaining = self._in_flight.get(key, 0) - 1
                if remaining > 0:
                    self._in_flight[key] = remaining
                else:
                    self._in_flight.pop(key, None)

            if outcome == "success":
                self._failures.pop(keys[1], None)
            elif outcome == "failure":
                for key in keys:
                    self._failures.setdefault(key, deque()).append(now)

            for key in keys:
                self._prune_key(key, now)


LOGIN_ACCOUNT_MAX_FAILURES = _positive_int("AUTH_LOGIN_ACCOUNT_MAX_FAILURES", 5)
LOGIN_IP_MAX_FAILURES = _positive_int("AUTH_LOGIN_IP_MAX_FAILURES", 60)
LOGIN_RATE_WINDOW_SECONDS = _positive_float("AUTH_LOGIN_RATE_WINDOW_SECONDS", 900.0)
LOGIN_MAX_TRACKED_KEYS = _positive_int("AUTH_LOGIN_MAX_TRACKED_KEYS", 10_000)
LOGIN_RATE_LIMITED_DETAIL = "تعداد تلاش‌های ورود بیش از حد مجاز است؛ کمی بعد دوباره تلاش کنید."

AUTH_LOGIN_RATE_LIMITER = LoginAttemptRateLimiter(
    account_max_failures=LOGIN_ACCOUNT_MAX_FAILURES,
    ip_max_failures=LOGIN_IP_MAX_FAILURES,
    window_seconds=LOGIN_RATE_WINDOW_SECONDS,
    max_tracked_keys=max(2, LOGIN_MAX_TRACKED_KEYS),
)
