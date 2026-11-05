from __future__ import annotations

import unittest
from unittest.mock import patch

from admission_chance_api import AdmissionChanceRequest, admission_chance
from admission_exam_capacity import build_exam_capacity_results, load_exam_capacity_rows


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

    def test_graphic_tehran_daily_preserves_province_filter(self):
        # The current JSON has this province: /360, code 35320.
        # Keep a real-data positive check; do not freeze the total row count.
        source = next(
            row for row in load_exam_capacity_rows("honar")
            if str(row["sanjesh_code"]) == "35320"
        )
        items = build_exam_capacity_results(
            group="honar",
            major_ids=[140],
            province="تهران",
            periods=["روزانه"],
        )
        self.assertIn("35320", [item["sanjesh_code"] for item in items])
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["major_name"] == "گرافيک" for item in items))
        self.assertTrue(all(item["province"] == "تهران" for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))
        self.assertTrue(all(item["capacity"] is not None for item in items))
        anchor = next(item for item in items if item["sanjesh_code"] == "35320")
        self.assertEqual(anchor["capacity"], source["capacity"])
        self.assertEqual(anchor["major_name"], source["major_name"])

        # Controlled contrast: same major/period, different province. Neither
        # an always-empty selector nor a selector ignoring province can pass.
        contrast = dict(source, province="هرمزگان", sanjesh_code="__other_province__")
        with patch("admission_exam_capacity.load_exam_capacity_rows", return_value=(source, contrast)):
            for requested, expected_code in (
                ("تهران", "35320"),
                ("هرمزگان", "__other_province__"),
            ):
                with self.subTest(province=requested):
                    selected = build_exam_capacity_results(
                        group="honar",
                        major_ids=[140],
                        province=requested,
                        periods=["روزانه"],
                    )
                    self.assertEqual([item["sanjesh_code"] for item in selected], [expected_code])
                    self.assertEqual(selected[0]["province"], requested)
                    self.assertEqual(selected[0]["major_name"], source["major_name"])
                    self.assertEqual(selected[0]["capacity"], source["capacity"])

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
