from __future__ import annotations

import json
import random
import unittest
from pathlib import Path

from record_major_map import load_major_id_name_map, major_name_for_id


ROOT = Path(__file__).resolve().parent


class RecordMajorMapTests(unittest.TestCase):
    def test_map_covers_current_major_reference_data(self):
        source = json.loads((ROOT / "majors_database_v2.json").read_text(encoding="utf-8"))
        mapping = load_major_id_name_map()
        source_ids = {str(item["id"]) for item in source if isinstance(item, dict) and item.get("id") is not None}
        self.assertEqual(set(mapping), source_ids)
        self.assertEqual(len(mapping), 160)

    def test_deterministic_sample_ids_return_canonical_names(self):
        mapping = load_major_id_name_map()
        rng = random.Random(1404)
        sample_ids = rng.sample(sorted(mapping, key=int), 5)
        for major_id in sample_ids:
            self.assertEqual(major_name_for_id(major_id), mapping[major_id])
            self.assertTrue(major_name_for_id(major_id))

    def test_known_reference_names(self):
        self.assertEqual(major_name_for_id(1), "پزشکی")
        self.assertEqual(major_name_for_id(41), "مهندسی برق")
        self.assertEqual(major_name_for_id(81), "ریاضیات و کاربردها")
        self.assertEqual(major_name_for_id(150), "زبان‌شناسی همگانی")

    def test_unknown_major_is_unresolved(self):
        self.assertIsNone(major_name_for_id(999999))


if __name__ == "__main__":
    unittest.main(verbosity=2)
