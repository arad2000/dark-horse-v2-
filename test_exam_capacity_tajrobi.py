from __future__ import annotations

import unittest

from admission_chance_api import AdmissionChanceRequest, admission_chance
from admission_exam_capacity import build_exam_capacity_results


class TajrobiExamCapacityLoaderTests(unittest.TestCase):
    def test_medical_major_tehran_daily_returns_capacity_rows(self):
        items = build_exam_capacity_results(
            group="tajrobi",
            major_ids=[1],  # پزشکی
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
            group="tajrobi",
            major_ids=[1],
            province="هرمزگان",
            periods=["روزانه"],
        )
        self.assertEqual(items, [])

    def test_unrelated_major_stays_empty(self):
        items = build_exam_capacity_results(
            group="tajrobi",
            major_ids=[41],  # مهندسی برق؛ بی‌ربط به دفترچه تجربی
            province="تهران",
            periods=["روزانه"],
        )
        self.assertEqual(items, [])

    def test_unknown_period_is_excluded_by_default(self):
        items = build_exam_capacity_results(
            group="tajrobi",
            major_ids=[1],
            province="تهران",
            periods=["نامشخص"],
        )
        self.assertEqual(items, [])

    def test_api_exposes_explicit_tajrobi_group_without_rank_cutoff(self):
        request = AdmissionChanceRequest(
            admission_path="exam",
            source="capacity",
            group="tajrobi",
            major_ids=[1],
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
        self.assertEqual(response["group"], "tajrobi")
        self.assertGreater(response["count"], 0)
        self.assertTrue(all(item["sanjesh_code"] for item in response["items"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
