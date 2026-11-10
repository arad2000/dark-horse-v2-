"""Isolated CORS tests: no production router imports, lifespan, DB or real signup."""
import ast
import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

import httpx
from fastapi.middleware.cors import CORSMiddleware


TREE = ast.parse(Path(__file__).with_name("main_v2.py").read_text())
HELPER = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "_cors_allowed_origins")
SCOPE = {"os": os, "urlsplit": urlsplit}
exec(compile(ast.Module(body=[HELPER], type_ignores=[]), "<isolated CORS config>", "exec"), SCOPE)
CORS_CALL = next(n.value for n in TREE.body if isinstance(n, ast.Expr)
                 and isinstance(n.value, ast.Call) and n.value.args
                 and isinstance(n.value.args[0], ast.Name) and n.value.args[0].id == "CORSMiddleware")


def settings(value=None):
    with patch.dict(os.environ, {}, clear=True):
        if value is not None:
            os.environ["CORS_ALLOWED_ORIGINS"] = value
        return {kw.arg: eval(compile(ast.Expression(kw.value), "<CORS setting>", "eval"), SCOPE)
                for kw in CORS_CALL.keywords}


class CorsOriginTests(unittest.TestCase):
    def test_default_production_origins(self):
        self.assertEqual(settings()["allow_origins"],
                         ["https://asbe-siah.ir", "https://www.asbe-siah.ir"])

    def test_empty_env_keeps_defaults(self):
        self.assertEqual(settings(" , ")["allow_origins"], settings()["allow_origins"])

    def test_exact_staging_env_adds_without_replacing_defaults(self):
        self.assertEqual(settings(" https://cors-test-example.liara.run/ , https://asbe-siah.ir ")["allow_origins"],
                         settings()["allow_origins"] + ["https://cors-test-example.liara.run"])

    def test_credentials_methods_headers_unchanged(self):
        config = settings()
        self.assertIs(config["allow_credentials"], False)
        self.assertEqual(config["allow_methods"], ["*"])
        self.assertEqual(config["allow_headers"], ["*"])

    def test_invalid_origins_rejected(self):
        for value in ["*", "https://*.liara.run", "http://example.liara.run",
                      "https://example.liara.run/login", "https://example.liara.run?x=1",
                      "https://example.liara.run#fragment", "https://user:secret@example.liara.run",
                      "https://example.liara.run:99999", "https://example.liara.run\\evil",
                      "https://exa mple.liara.run"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                settings(value)

    def probe(self, origin, env=None):
        async def run():
            calls = []
            async def stub(scope, receive, send):
                calls.append(scope["path"])
                await send({"type": "http.response.start", "status": 200,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"stub":true}'})
            app = CORSMiddleware(stub, **settings(env))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test.invalid") as client:
                preflight = await client.options("/api/v1/auth/register", headers={
                    "Origin": origin, "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type"})
                post = await client.post("/api/v1/auth/register", headers={"Origin": origin}, json={})
            return preflight, post, calls
        return asyncio.run(run())

    def assert_allowed(self, origin, env=None):
        pre, post, calls = self.probe(origin, env)
        self.assertEqual(pre.status_code, 200)
        for response in [pre, post]:
            self.assertEqual(response.headers["access-control-allow-origin"], origin)
            self.assertNotIn("access-control-allow-credentials", response.headers)
            self.assertIn("Origin", response.headers["vary"])
        self.assertIn("POST", pre.headers["access-control-allow-methods"])
        self.assertEqual(pre.headers["access-control-allow-headers"], "authorization,content-type")
        self.assertEqual(calls, ["/api/v1/auth/register"])

    def test_production_preflight_and_response(self):
        for origin in settings()["allow_origins"]:
            with self.subTest(origin=origin):
                self.assert_allowed(origin)

    def test_configured_exact_staging_preflight_and_response(self):
        origin = "https://cors-test-example.liara.run"
        self.assert_allowed(origin, origin)

    def test_unconfigured_staging_and_other_origins_denied(self):
        for origin in ["https://cors-test-example.liara.run", "https://other.liara.run", "null"]:
            pre, post, _ = self.probe(origin)
            self.assertEqual(pre.status_code, 400)
            self.assertNotIn("access-control-allow-origin", pre.headers)
            self.assertNotIn("access-control-allow-origin", post.headers)

    def test_other_liara_origin_still_denied_after_one_added(self):
        pre, post, _ = self.probe("https://other.liara.run", "https://cors-test-example.liara.run")
        self.assertEqual(pre.status_code, 400)
        self.assertNotIn("access-control-allow-origin", post.headers)


if __name__ == "__main__":
    unittest.main()
