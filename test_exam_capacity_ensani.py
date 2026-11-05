from __future__ import annotations

import unittest
from unittest.mock import patch

from admission_chance_api import AdmissionChanceRequest, admission_chance
from admission_exam_capacity import build_exam_capacity_results, load_exam_capacity_rows


class EnsaniExamCapacityLoaderTests(unittest.TestCase):
    def test_law_tehran_daily_returns_capacity_rows(self):
        items = build_exam_capacity_results(
            group="ensani",
            major_ids=[101],  # حقوق
            province="تهران",
            periods=["روزانه"],
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["capacity"] is not None for item in items))
        self.assertTrue(all(item["province"] == "تهران" for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))

    def test_law_hormozgan_daily_preserves_province_filter(self):
        # The current JSON has this province: /2656, code 35015.
        # Keep a real-data positive check; do not freeze the total row count.
        source = next(
            row for row in load_exam_capacity_rows("ensani")
            if str(row["sanjesh_code"]) == "35015"
        )
        items = build_exam_capacity_results(
            group="ensani",
            major_ids=[101],
            province="هرمزگان",
            periods=["روزانه"],
        )
        self.assertIn("35015", [item["sanjesh_code"] for item in items])
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["major_name"] == "حقوق" for item in items))
        self.assertTrue(all(item["province"] == "هرمزگان" for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))
        self.assertTrue(all(item["capacity"] is not None for item in items))
        anchor = next(item for item in items if item["sanjesh_code"] == "35015")
        self.assertEqual(anchor["capacity"], source["capacity"])
        self.assertEqual(anchor["major_name"], source["major_name"])

        # Controlled contrast: same major/period, different province. Neither
        # an always-empty selector nor a selector ignoring province can pass.
        contrast = dict(source, province="تهران", sanjesh_code="__other_province__")
        with patch("admission_exam_capacity.load_exam_capacity_rows", return_value=(source, contrast)):
            for requested, expected_code in (
                ("هرمزگان", "35015"),
                ("تهران", "__other_province__"),
            ):
                with self.subTest(province=requested):
                    selected = build_exam_capacity_results(
                        group="ensani",
                        major_ids=[101],
                        province=requested,
                        periods=["روزانه"],
                    )
                    self.assertEqual([item["sanjesh_code"] for item in selected], [expected_code])
                    self.assertEqual(selected[0]["province"], requested)
                    self.assertEqual(selected[0]["major_name"], source["major_name"])
                    self.assertEqual(selected[0]["capacity"], source["capacity"])

    def test_unrelated_major_stays_empty(self):
        items = build_exam_capacity_results(
            group="ensani",
            major_ids=[1],  # پزشکی؛ بی‌ربط به دفترچه انسانی
            province="تهران",
            periods=["روزانه"],
        )
        self.assertEqual(items, [])

    def test_unknown_period_is_excluded_by_default(self):
        items = build_exam_capacity_results(
            group="ensani",
            major_ids=[101],
            province="تهران",
            periods=["نامشخص"],
        )
        self.assertEqual(items, [])

    def test_api_exposes_ensani_group_without_rank_cutoff(self):
        request = AdmissionChanceRequest(
            admission_path="exam",
            source="capacity",
            group="ensani",
            major_ids=[101],
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
        self.assertEqual(response["group"], "ensani")
        self.assertGreater(response["count"], 0)
        self.assertTrue(all(item["sanjesh_code"] for item in response["items"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
