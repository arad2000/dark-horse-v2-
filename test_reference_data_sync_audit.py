"""Unit tests for the main/deploy reference-data governance guard."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reference_data_sync_audit import (
    RUNTIME_OWNED_REFERENCE_FILES,
    SHARED_REFERENCE_FILES,
    load_strict_json,
    validate_runtime_owned_file,
)


class ReferenceDataSyncAuditTests(unittest.TestCase):
    def test_only_contractually_shared_files_require_byte_equality(self):
        self.assertEqual(
            SHARED_REFERENCE_FILES,
            (
                "docs/data/questions_v2.json",
                "docs/data/trait_map_v3.json",
                "value_poles_v2.json",
            ),
        )
        self.assertEqual(
            RUNTIME_OWNED_REFERENCE_FILES,
            (
                "docs/data/micro_motives.json",
                "majors_database_v2.json",
                "school_branches_v2.json",
            ),
        )
        self.assertFalse(set(SHARED_REFERENCE_FILES) & set(RUNTIME_OWNED_REFERENCE_FILES))

    def test_strict_json_rejects_nan_infinity_and_overflow(self):
        for literal in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999"):
            with self.subTest(literal=literal), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "data.json"
                path.write_text(f'[{{"value": {literal}}}]', encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_strict_json(path)

    def test_nonfinite_words_inside_strings_are_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text('[{"text": "NaN Infinity -Infinity 1e999"}]', encoding="utf-8")
            self.assertEqual(
                load_strict_json(path),
                [{"text": "NaN Infinity -Infinity 1e999"}],
            )

    def test_runtime_reference_requires_nonempty_object_rows(self):
        for payload in ("[]", "{}", '[null]', '[1, "bad"]'):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = root / "majors_database_v2.json"
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(ValueError):
                    validate_runtime_owned_file("majors_database_v2.json", root=root)

    def test_runtime_reference_reports_hash_and_row_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "majors_database_v2.json"
            path.write_text('[{"id": 1}, {"id": 2}]', encoding="utf-8")
            result = validate_runtime_owned_file("majors_database_v2.json", root=root)
            self.assertEqual(result["rows"], 2)
            self.assertEqual(result["path"], "majors_database_v2.json")
            self.assertEqual(len(result["sha256"]), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
