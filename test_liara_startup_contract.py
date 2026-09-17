from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class LiaraStartupContractTests(unittest.TestCase):
    def test_liara_uses_direct_uvicorn_argv(self) -> None:
        config = json.loads((ROOT / "liara.json").read_text(encoding="utf-8"))
        self.assertEqual(config["platform"], "python")
        self.assertEqual(config["port"], 80)
        self.assertEqual(
            config["args"],
            [
                "uvicorn",
                "main_v2:app",
                "--host",
                "0.0.0.0",
                "--port",
                "80",
            ],
        )
        self.assertNotIn("sh", config["args"])
        self.assertNotIn("alembic", config["args"])


if __name__ == "__main__":
    unittest.main()
