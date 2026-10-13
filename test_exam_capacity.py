from __future__ import annotations

import unittest
from unittest.mock import patch

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

    def test_phase1_explicit_aliases_match_by_major_id(self):
        cases = [
            ("tajrobi", 1, "دکتری عمومی پزشکی"),
            ("tajrobi", 25, "فناوري اطالعات سالمت"),
            ("riazi", 44, "مهندسي رايانه (نرم افزار)"),
            ("riazi", 53, "مهندسي صنايع و سيستمها"),
            ("riazi", 62, "مهندسي و علم مواد"),
            ("riazi", 195, "مهندسي حرفهاي کامپيوتر"),
            ("honar", 140, "گرافیک"),
            ("riazi", 82, "آمار"),
        ]
        with patch("admission_exam_capacity.load_exam_capacity_rows") as load_rows:
            for group, major_id, booklet_name in cases:
                load_rows.return_value = (
                    {
                        "sanjesh_code": f"__alias-{major_id}__",
                        "major_name": booklet_name,
                        "province": "تهران",
                        "period": "روزانه",
                        "admission_type": "با آزمون",
                        "capacity": 1,
                    },
                )
                items = build_exam_capacity_results(
                    major_ids=[major_id],
                    province="تهران",
                    periods=["روزانه"],
                    group=group,
                )
                self.assertEqual([item["sanjesh_code"] for item in items], [f"__alias-{major_id}__"])

    def test_phase1_graphic_alias_does_not_capture_visual_communication_major(self):
        with patch("admission_exam_capacity.load_exam_capacity_rows") as load_rows:
            load_rows.return_value = (
                {
                    "sanjesh_code": "__visual-communication__",
                    "major_name": "ارتباط تصویری",
                    "province": "تهران",
                    "period": "روزانه",
                    "admission_type": "با آزمون",
                    "capacity": 1,
                },
            )
            self.assertEqual(
                build_exam_capacity_results(
                    major_ids=[140],
                    province="تهران",
                    periods=["روزانه"],
                    group="honar",
                ),
                [],
            )
            items = build_exam_capacity_results(
                major_ids=[141],
                province="تهران",
                periods=["روزانه"],
                group="honar",
            )
            self.assertEqual([item["sanjesh_code"] for item in items], ["__visual-communication__"])

    def test_phase2_wave1_new_major_ids_match_1405_capacity_rows(self):
        cases = [
            (161, "فارس", "روزانه", "ensani"),   # علوم ورزشی
            (162, "آذربایجان شرقی", "روزانه", "riazi"),  # مهندسی معماری
            (163, "اردبیل", "روزانه", "ensani"),  # گردشگری
            (166, "تهران", "روزانه", "ensani"),  # باستان‌شناسی
            (169, "قم", "روزانه", "tajrobi"),    # زیست‌فناوری / alias
        ]
        for major_id, province, period, group in cases:
            items = build_exam_capacity_results(
                major_ids=[major_id],
                province=province,
                periods=[period],
                group=group,
            )
            self.assertGreater(
                len(items),
                0,
                f"phase2 major_id={major_id} should match 1405 {group} capacity data",
            )
            self.assertTrue(all(item["sanjesh_code"] for item in items))
            self.assertTrue(all(item["province"] == province for item in items))
            self.assertTrue(all(item["period"] == period for item in items))

    def test_wave_c_new_majors_match_real_1405_capacity_rows(self):
        # These are source-backed 1405 riazi rows, not mocked aliases:
        # 195 has booklet spelling "مهندسي حرفهاي کامپيوتر";
        # 198 has booklet spelling "مهندسي ساخت و توليد".
        cases = [
            (195, "آذربایجان شرقی", "روزانه"),
            (198, "آذربایجان شرقی", "روزانه"),
        ]
        for major_id, province, period in cases:
            items = build_exam_capacity_results(
                major_ids=[major_id],
                province=province,
                periods=[period],
                group="riazi",
                limit=5,
            )
            self.assertGreater(
                len(items),
                0,
                f"wave C major_id={major_id} must match real 1405 riazi capacity rows",
            )
            self.assertTrue(all(item["sanjesh_code"] for item in items))
            self.assertTrue(all(item["province"] == province for item in items))
            self.assertTrue(all(item["period"] == period for item in items))
            self.assertTrue(all(item["capacity"] is not None for item in items))

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
