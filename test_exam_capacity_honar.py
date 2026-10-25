from __future__ import annotations

import unittest

from admission_chance_api import AdmissionChanceRequest, admission_chance
from admission_exam_capacity import build_exam_capacity_results


class HonarExamCapacityLoaderTests(unittest.TestCase):
    def test_graphic_alias_karaj_daily_returns_capacity_rows(self):
        items = build_exam_capacity_results(
            group="honar",
            major_ids=[140],  # majors_database_v2: طراحی گرافیک
            province="البرز",
            periods=["روزانه"],
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["capacity"] is not None for item in items))
        self.assertTrue(all(item["province"] == "البرز" for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))
        self.assertTrue(any(item["major_name"] == "گرافيک" for item in items))

    def test_unrelated_province_returns_empty(self):
        items = build_exam_capacity_results(
            group="honar",
            major_ids=[140],
            province="تهران",
            periods=["روزانه"],
        )
        self.assertEqual(items, [])

    def test_unknown_period_is_excluded_by_default(self):
        items = build_exam_capacity_results(
            group="honar",
            major_ids=[140],
            province="البرز",
            periods=["نامشخص"],
        )
        self.assertEqual(items, [])

    def test_api_exposes_honar_group_without_rank_cutoff(self):
        request = AdmissionChanceRequest(
            admission_path="exam",
            source="capacity",
            group="honar",
            major_ids=[140],
            province="البرز",
            periods=["روزانه"],
            rank_in_quota=None,
            region_zone=None,
            special_quota="none",
            limit=5,
        )
        response = admission_chance(request)
        self.assertEqual(response["admission_path"], "exam")
        self.assertEqual(response["source"], "capacity")
        self.assertEqual(response["group"], "honar")
        self.assertGreater(response["count"], 0)
        self.assertTrue(all(item["sanjesh_code"] for item in response["items"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
