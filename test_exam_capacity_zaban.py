from __future__ import annotations

import unittest

from admission_chance_api import AdmissionChanceRequest, admission_chance
from admission_exam_capacity import build_exam_capacity_results


class ZabanExamCapacityLoaderTests(unittest.TestCase):
    def test_english_teaching_tehran_daily_returns_capacity(self):
        items = build_exam_capacity_results(
            group="zaban",
            major_ids=[147],  # آموزش زبان انگلیسی
            province="تهران",
            periods=["روزانه"],
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))

    def test_english_literature_tehran_daily_returns_capacity(self):
        items = build_exam_capacity_results(
            group="zaban",
            major_ids=[148],  # زبان و ادبیات انگلیسی
            province="تهران",
            periods=["روزانه"],
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))

    def test_unrelated_province_returns_empty(self):
        items = build_exam_capacity_results(
            group="zaban",
            major_ids=[147],
            province="سیستان و بلوچستان",
            periods=["روزانه"],
        )
        self.assertEqual(items, [])

    def test_api_exposes_zaban_group(self):
        response = admission_chance(
            AdmissionChanceRequest(
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
        )
        self.assertEqual(response["group"], "zaban")
        self.assertGreater(response["count"], 0)
        self.assertTrue(all(item["sanjesh_code"] for item in response["items"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
