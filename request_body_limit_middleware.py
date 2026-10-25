"""Bound selected API request bodies before FastAPI parses JSON.

This is transport-level protection. It does not change API business rules, scoring,
authentication, payment configuration, or result semantics.
"""
from __future__ import annotations

import json
from collections import deque
from typing import Any


class RequestBodyLimitMiddleware:
    """Enforce per-method/path byte limits before downstream request parsing."""

    def __init__(self, app, *, limits: dict[tuple[str, str], int]) -> None:
        self.app = app
        self.limits = {
            (str(method).upper(), str(path)): int(limit)
            for (method, path), limit in limits.items()
        }
        if any(limit <= 0 for limit in self.limits.values()):
            raise ValueError("request body limits must be positive")

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        key = (str(scope.get("method", "")).upper(), str(scope.get("path", "")))
        limit = self.limits.get(key)
        if limit is None:
            await self.app(scope, receive, send)
            return

        content_lengths = [
            value for name, value in scope.get("headers", []) if name.lower() == b"content-length"
        ]
        if len(set(content_lengths)) > 1:
            await self._reject(send, 400, "invalid content-length")
            return

        if content_lengths:
            try:
                declared_length = int(content_lengths[0].decode("ascii").strip())
            except (UnicodeDecodeError, ValueError):
                await self._reject(send, 400, "invalid content-length")
                return
            if declared_length < 0:
                await self._reject(send, 400, "invalid content-length")
                return
            if declared_length > limit:
                await self._reject(send, 413, "request body exceeds configured limit")
                return

        # Buffer at most limit bytes, so requests without Content-Length are bounded too.
        messages: deque[dict[str, Any]] = deque()
        total_bytes = 0
        while True:
            message = await receive()
            messages.append(message)

            message_type = message.get("type")
            if message_type == "http.disconnect":
                break
            if message_type != "http.request":
                continue

            total_bytes += len(message.get("body", b""))
            if total_bytes > limit:
                await self._reject(send, 413, "request body exceeds configured limit")
                return
            if not message.get("more_body", False):
                break

        async def replay_receive():
            if messages:
                return messages.popleft()
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(send, status_code: int, detail: str) -> None:
        body = json.dumps({"detail": detail}, separators=(",", ":")).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})
