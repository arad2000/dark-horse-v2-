from __future__ import annotations

import json
import random
import unittest
from pathlib import Path

from record_major_map import load_major_id_name_map, major_name_for_id


ROOT = Path(__file__).resolve().parent


def _legacy_name_weight_fingerprint(items):
    payload = "\n".join(
        f"{int(item['id'])}|{item['name']}|{item['weights_version']}"
        for item in sorted(items, key=lambda item: int(item["id"]))
    )
    # Code-point FNV-1a mirrors the deterministic baseline generated before Phase 2.
    value = 0xCBF29CE484222325
    prime = 0x100000001B3
    mask = 0xFFFFFFFFFFFFFFFF
    for char in payload:
        value ^= ord(char)
        value = (value * prime) & mask
    return f"{value:016x}"


class RecordMajorMapTests(unittest.TestCase):
    def test_map_covers_current_major_reference_data(self):
        source = json.loads((ROOT / "majors_database_v2.json").read_text(encoding="utf-8"))
        mapping = load_major_id_name_map()
        source_ids = {str(item["id"]) for item in source if isinstance(item, dict) and item.get("id") is not None}
        self.assertEqual(set(mapping), source_ids)
        self.assertEqual(len(mapping), 176)

    def test_phase2_legacy_1_160_name_weight_fingerprint_unchanged(self):
        source = json.loads((ROOT / "majors_database_v2.json").read_text(encoding="utf-8"))
        self.assertEqual(len(source), 176)
        legacy = [item for item in source if 1 <= int(item["id"]) <= 160]
        self.assertEqual(len(legacy), 160)
        self.assertEqual(
            _legacy_name_weight_fingerprint(legacy),
            "15ce7c0ad63de857",
        )

    def test_phase2_wave1_new_majors_are_capacity_stubs(self):
        source = json.loads((ROOT / "majors_database_v2.json").read_text(encoding="utf-8"))
        expected = {
            161: "علوم ورزشی",
            162: "مهندسی معماری",
            163: "گردشگری",
            164: "علوم قرآن و حدیث",
            165: "علوم و مهندسی آب",
            166: "باستان‌شناسی",
            167: "فرش",
            168: "صنایع دستی",
            169: "زیست‌فناوری",
            170: "هنر اسلامی",
            171: "هتلداری",
            172: "معماری داخلی",
            173: "ادیان و عرفان",
            174: "مطالعات خانواده",
            175: "زبان و ادبیات فرانسه",
            176: "مترجمی زبان عربی",
        }
        rows = {int(item["id"]): item for item in source if int(item["id"]) >= 161}
        self.assertEqual(set(rows), set(expected))
        for major_id, name in expected.items():
            row = rows[major_id]
            self.assertEqual(row["name"], name)
            self.assertFalse(row["handcrafted"])
            self.assertFalse(row["motive_driven"])
            self.assertIn("phase2_capacity_stub_v1", row["weights_version"])
            self.assertTrue(
                all(code.startswith(f"P2-{major_id}-") for code in row["micro_motive_codes"])
            )
            self.assertEqual(row["archetype"], "phase2-capacity-stub")

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
