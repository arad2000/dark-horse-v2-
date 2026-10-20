"""Contract tests for pre-parse request body limits."""
from __future__ import annotations

import asyncio
import unittest

from request_body_limit_middleware import RequestBodyLimitMiddleware


class RequestBodyLimitMiddlewareTests(unittest.TestCase):
    def _run_request(
        self,
        *,
        body_chunks: list[bytes],
        limit: int = 4,
        path: str = "/api/v1/auth/login",
        limit_path: str = "/api/v1/auth/login",
        headers: list[tuple[bytes, bytes]] | None = None,
    ):
        messages = [
            {
                "type": "http.request",
                "body": chunk,
                "more_body": index < len(body_chunks) - 1,
            }
            for index, chunk in enumerate(body_chunks)
        ]
        if not messages:
            messages = [{"type": "http.request", "body": b"", "more_body": False}]

        receive_calls = 0
        app_calls = 0
        captured_body = bytearray()
        response_messages = []

        async def receive():
            nonlocal receive_calls
            receive_calls += 1
            if messages:
                return messages.pop(0)
            return {"type": "http.disconnect"}

        async def send(message):
            response_messages.append(message)

        async def app(scope, app_receive, app_send):
            nonlocal app_calls
            app_calls += 1
            while True:
                message = await app_receive()
                if message["type"] == "http.disconnect":
                    break
                if message["type"] != "http.request":
                    continue
                captured_body.extend(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            await app_send({"type": "http.response.start", "status": 200, "headers": []})
            await app_send(
                {
                    "type": "http.response.body",
                    "body": bytes(captured_body),
                    "more_body": False,
                }
            )

        middleware = RequestBodyLimitMiddleware(
            app,
            limits={("POST", limit_path): limit},
        )
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": "POST",
            "path": path,
            "headers": headers or [],
        }
        asyncio.run(middleware(scope, receive, send))
        status = next(
            message["status"]
            for message in response_messages
            if message["type"] == "http.response.start"
        )
        response_body = b"".join(
            message.get("body", b"")
            for message in response_messages
            if message["type"] == "http.response.body"
        )
        return status, response_body, bytes(captured_body), app_calls, receive_calls

    def test_body_at_limit_reaches_application_intact(self):
        status, _, captured, app_calls, _ = self._run_request(
            body_chunks=[b"ab", b"cd"],
            headers=[(b"content-length", b"4")],
        )
        self.assertEqual(status, 200)
        self.assertEqual(captured, b"abcd")
        self.assertEqual(app_calls, 1)

    def test_streamed_body_without_content_length_is_limited(self):
        status, body, _, app_calls, _ = self._run_request(body_chunks=[b"abc", b"de"])
        self.assertEqual(status, 413)
        self.assertIn(b"request body exceeds", body)
        self.assertEqual(app_calls, 0)

    def test_oversized_content_length_rejected_before_reading_body(self):
        status, body, _, app_calls, receive_calls = self._run_request(
            body_chunks=[b"abcde"],
            headers=[(b"content-length", b"5")],
        )
        self.assertEqual(status, 413)
        self.assertIn(b"request body exceeds", body)
        self.assertEqual(app_calls, 0)
        self.assertEqual(receive_calls, 0)

    def test_invalid_content_length_is_rejected(self):
        status, body, _, app_calls, _ = self._run_request(
            body_chunks=[b"x"],
            headers=[(b"content-length", b"not-a-number")],
        )
        self.assertEqual(status, 400)
        self.assertIn(b"invalid content-length", body)
        self.assertEqual(app_calls, 0)

    def test_unconfigured_route_is_not_intercepted(self):
        status, _, captured, app_calls, _ = self._run_request(
            body_chunks=[b"abcde"],
            path="/unconfigured",
        )
        self.assertEqual(status, 200)
        self.assertEqual(captured, b"abcde")
        self.assertEqual(app_calls, 1)


if __name__ == "__main__":
    unittest.main()
