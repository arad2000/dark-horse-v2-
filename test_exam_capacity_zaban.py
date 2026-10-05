from __future__ import annotations

import unittest

from admission_chance_api import AdmissionChanceRequest, admission_chance
from admission_exam_capacity import CAPACITY_PATHS, build_exam_capacity_results


class ZabanExamCapacityLoaderTests(unittest.TestCase):
    def test_zaban_uses_1405_source(self):
        self.assertIn("sanjesh_zaban_1405_programs.json", str(CAPACITY_PATHS["zaban"]))

    def test_english_teaching_tehran_daily_returns_capacity_rows(self):
        items = build_exam_capacity_results(
            group="zaban",
            major_ids=[147],  # آموزش زبان انگلیسی
            province="تهران",
            periods=["روزانه"],
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["capacity"] is not None for item in items))
        self.assertTrue(all(item["province"] == "تهران" for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))

    def test_unrelated_province_returns_empty(self):
        items = build_exam_capacity_results(
            group="zaban",
            major_ids=[147],
            province="قم",
            periods=["روزانه"],
        )
        self.assertEqual(items, [])

    def test_unknown_period_is_excluded_by_default(self):
        items = build_exam_capacity_results(
            group="zaban",
            major_ids=[147],
            province="تهران",
            periods=["نامشخص"],
        )
        self.assertEqual(items, [])

    def test_api_exposes_zaban_group_without_rank_cutoff(self):
        request = AdmissionChanceRequest(
            admission_path="exam",
            source="capacity",
            group="zaban",
            major_ids=[147],
            province="تهران",
            periods=["روزانه"],
            rank_in_quota=None,
            region_zone=None,
            special_quota="none",
            limit=5,
        )
        response = admission_chance(request)
        self.assertEqual(response["admission_path"], "exam")
        self.assertEqual(response["source"], "capacity")
        self.assertEqual(response["group"], "zaban")
        self.assertGreater(response["count"], 0)
        self.assertTrue(all(item["sanjesh_code"] for item in response["items"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
