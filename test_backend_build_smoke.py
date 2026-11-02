"""Build-check contracts only: no database, listener or remote services."""
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import backend_build_smoke as smoke


class BackendBuildSmokeTests(unittest.TestCase):
    def test_child_environment_drops_inherited_service_settings(self):
        with patch.dict("os.environ", {
            "PATH": "/audit/bin",
            "DATABASE_URL": "audit-do-not-use",
            "CF_API_TOKEN": "audit-do-not-forward",
            "PYTHONPATH": "/audit/unsafe",
            "APP_ENV": "production",
            "ALLOW_RUNTIME_SCHEMA_BOOTSTRAP": "true",
            "POSTGRES_RUNTIME_CUTOVER_APPROVED": "true",
        }, clear=True):
            env = smoke.child_environment()
        self.assertEqual(env["PATH"], "/audit/bin")
        self.assertEqual(env["DATABASE_URL"], "")
        self.assertEqual(env["APP_ENV"], "local")
        self.assertEqual(env["ALLOW_RUNTIME_SCHEMA_BOOTSTRAP"], "false")
        self.assertEqual(env["POSTGRES_RUNTIME_CUTOVER_APPROVED"], "false")
        self.assertNotIn("CF_API_TOKEN", env)
        self.assertNotIn("PYTHONPATH", env)

    def test_missing_artifact_fails_without_starting_child(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(smoke.subprocess, "run") as run:
            with redirect_stderr(StringIO()) as output:
                self.assertEqual(smoke.main(Path(directory)), 1)
            self.assertIn("admin_router.py", output.getvalue())
            run.assert_not_called()

    def run_with_complete_fixture(self, run):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in smoke.REQUIRED_FILES:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
            with redirect_stderr(StringIO()):
                result = smoke.main(root)
            self.assertEqual(run.call_args.kwargs["cwd"], root)
        return result

    def test_child_is_isolated_and_success_is_propagated(self):
        with patch.object(smoke.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(self.run_with_complete_fixture(run), 0)
            self.assertIn("-I", run.call_args.args[0])
            self.assertEqual(run.call_args.kwargs["timeout"], 60)
            self.assertEqual(run.call_args.kwargs["env"]["DATABASE_URL"], "")

    def test_child_failure_is_not_hidden(self):
        with patch.object(smoke.subprocess, "run", return_value=SimpleNamespace(returncode=7)) as run:
            self.assertEqual(self.run_with_complete_fixture(run), 7)

    def test_timeout_fails_closed(self):
        with patch.object(smoke.subprocess, "run", side_effect=subprocess.TimeoutExpired("audit", 60)) as run:
            self.assertEqual(self.run_with_complete_fixture(run), 1)

    def test_common_socket_connection_paths_are_blocked(self):
        # Check the guard before the actual imports, without importing app code.
        guard = smoke.CHILD_CODE.split("import database", 1)[0]
        import socket
        with patch.object(socket, "create_connection"), patch.object(socket.socket, "connect"), patch.object(socket.socket, "connect_ex"):
            exec(guard, {})
            for call in (socket.create_connection, socket.socket.connect, socket.socket.connect_ex):
                with self.assertRaisesRegex(RuntimeError, "Network access is forbidden"):
                    call(("audit.invalid", 443))


if __name__ == "__main__":
    unittest.main()
