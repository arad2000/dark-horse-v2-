"""Strict JSON parsing contracts for the staging seed loader."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from seed_reference_data import load_json, seed_reference_data


class StrictSeedJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)

    def _load_text(self, raw: str):
        path = self.base / "sample.json"
        path.write_text(raw, encoding="utf-8")
        return load_json(path)

    def test_accepts_finite_numbers_and_nested_metadata(self) -> None:
        payload = self._load_text(
            '{"score":0.75,"metadata":{"measurements":[0,1.25,-2.5]}}'
        )
        self.assertEqual(payload["score"], 0.75)
        self.assertEqual(payload["metadata"]["measurements"], [0, 1.25, -2.5])

    def test_rejects_non_finite_json_constants_at_any_depth(self) -> None:
        documents = (
            "NaN",
            "Infinity",
            "-Infinity",
            '{"metadata":{"value":NaN}}',
            '{"metadata":{"value":Infinity}}',
            '{"metadata":[{"value":-Infinity}]}',
        )
        for raw in documents:
            with self.subTest(document=raw):
                with self.assertRaisesRegex(ValueError, "Non-finite JSON constant"):
                    self._load_text(raw)

    def test_rejects_positive_and_negative_exponent_overflow(self) -> None:
        documents = (
            "1e999",
            "-1e999",
            '{"metadata":{"value":1e999}}',
            '{"metadata":[{"value":-1e999}]}',
        )
        for raw in documents:
            with self.subTest(document=raw):
                with self.assertRaisesRegex(ValueError, "overflows the finite numeric range"):
                    self._load_text(raw)

    def test_invalid_reference_payload_fails_before_database_access(self) -> None:
        data_dir = self.base / "docs" / "data"
        data_dir.mkdir(parents=True)
        (data_dir / "micro_motives.json").write_text("[]", encoding="utf-8")
        (self.base / "majors_database_v2.json").write_text(
            '[{"id":1,"metadata":{"weight":1e999}}]', encoding="utf-8"
        )
        (self.base / "school_branches_v2.json").write_text("[]", encoding="utf-8")
        (self.base / "value_poles_v2.json").write_text("{}", encoding="utf-8")
        (data_dir / "trait_map_v3.json").write_text("{}", encoding="utf-8")

        db = Mock()
        with self.assertRaisesRegex(ValueError, "overflows the finite numeric range"):
            seed_reference_data(db, self.base)
        self.assertEqual(db.mock_calls, [])


if __name__ == "__main__":
    unittest.main()
