"""Small in-process rate limiter for expensive AI counsel requests.

This is intentionally dependency-free and bounded. It is defense-in-depth for a
single application process; production-wide enforcement should also be provided
by the edge/gateway layer before multi-replica scale-out.
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict, deque


class SlidingWindowRateLimiter:
    def __init__(
        self,
        *,
        limit: int = 10,
        window_seconds: float = 60.0,
        max_clients: int = 10_000,
        clock=time.monotonic,
    ) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_clients <= 0:
            raise ValueError("max_clients must be positive")
        self.limit = int(limit)
        self.window_seconds = float(window_seconds)
        self.max_clients = int(max_clients)
        self._clock = clock
        self._lock = threading.Lock()
        self._events: OrderedDict[str, deque[float]] = OrderedDict()

    def allow(self, client_key: str) -> tuple[bool, int]:
        """Consume one request and return (allowed, retry_after_seconds)."""
        key = client_key.strip() or "unknown"
        now = self._clock()
        cutoff = now - self.window_seconds

        with self._lock:
            events = self._events.get(key)
            if events is None:
                if len(self._events) >= self.max_clients:
                    self._events.popitem(last=False)
                events = deque()
                self._events[key] = events
            else:
                self._events.move_to_end(key)

            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= self.limit:
                retry_after = max(1, int(events[0] + self.window_seconds - now + 0.999))
                return False, retry_after

            events.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


COUNSEL_RATE_LIMITER = SlidingWindowRateLimiter(
    limit=_positive_int("AI_COUNSEL_RATE_LIMIT", 10),
    window_seconds=_positive_float("AI_COUNSEL_RATE_WINDOW_SECONDS", 60.0),
    max_clients=_positive_int("AI_COUNSEL_MAX_TRACKED_CLIENTS", 10_000),
)
