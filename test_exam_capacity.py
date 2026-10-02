from __future__ import annotations

import unittest

from admission_chance_api import AdmissionChanceRequest, admission_chance
from admission_exam_capacity import build_exam_capacity_results


class ExamCapacityLoaderTests(unittest.TestCase):
    def test_valid_major_province_period_returns_sanjesh_codes(self):
        items = build_exam_capacity_results(
            major_ids=[41],  # مهندسی برق
            province="تهران",
            periods=["روزانه"],
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["major_name"] == "مهندسی برق" for item in items))
        self.assertTrue(all(item["province"] == "تهران" for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))
        self.assertTrue(all(item["capacity"] is not None for item in items))

    def test_unrelated_province_reduces_to_empty(self):
        items = build_exam_capacity_results(
            major_ids=[41],
            province="هرمزگان",
            periods=["روزانه"],
        )
        self.assertEqual(items, [])

    def test_invalid_period_returns_empty(self):
        items = build_exam_capacity_results(
            major_ids=[41],
            province="تهران",
            periods=["این دوره وجود ندارد"],
        )
        self.assertEqual(items, [])

    def test_unknown_period_is_excluded_by_default(self):
        items = build_exam_capacity_results(
            major_ids=[41],
            province="تهران",
            periods=["نامشخص"],
        )
        self.assertEqual(items, [])

    def test_api_exam_capacity_uses_loader_without_rank_cutoff(self):
        request = AdmissionChanceRequest(
            admission_path="exam",
            source="capacity",
            major_ids=[41],
            province="تهران",
            periods=["روزانه"],
            rank_in_quota=None,
            region_zone=None,
            special_quota="isargaran_25",
            limit=5,
        )
        response = admission_chance(request)
        self.assertEqual(response["admission_path"], "exam")
        self.assertEqual(response["source"], "capacity")
        self.assertGreater(response["count"], 0)
        self.assertTrue(all(item["sanjesh_code"] for item in response["items"]))
        self.assertTrue(any("special_quota" in note for note in response["notes"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
