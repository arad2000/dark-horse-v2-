from __future__ import annotations

import unittest

from admission_chance_api import AdmissionChanceRequest, admission_chance
from admission_exam_capacity import CAPACITY_PATHS, build_exam_capacity_results


class RiaziExamCapacityLoaderTests(unittest.TestCase):
    def test_riazi_uses_1405_source(self):
        self.assertIn("sanjesh_riazi_1405_programs.json", str(CAPACITY_PATHS["riazi"]))

    def test_electrical_engineering_tehran_daily_returns_capacity(self):
        items = build_exam_capacity_results(
            group="riazi",
            major_ids=[41],  # مهندسی برق
            province="تهران",
            periods=["روزانه"],
            limit=5,
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["province"] == "تهران" for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))

    def test_empty_major_ids_returns_all_matching_majors(self):
        items = build_exam_capacity_results(
            group="riazi",
            major_ids=[],
            province="تهران",
            periods=["روزانه"],
            limit=100,
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["province"] == "تهران" for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))
        self.assertGreater(len({item["major_name"] for item in items}), 1)

    def test_unrelated_province_returns_empty(self):
        items = build_exam_capacity_results(
            group="riazi",
            major_ids=[41],
            province="سیستان و بلوچستان",
            periods=["روزانه"],
            limit=5,
        )
        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
