from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from admission_sanjesh_engine import (
    BORDERLINE_LABEL,
    EXAM_METHOD,
    GHOTBI_NOTE,
    HIGHER_LABEL,
    LOWER_LABEL,
    RECORD_ABOVE_LABEL,
    RECORD_BELOW_LABEL,
    build_exam_results,
    build_record_results,
    filter_programs,
    load_programs,
)
from main_v2 import app


def _program(
    *,
    program_id: str,
    major_id: int,
    method: str,
    course_type: str,
    diploma: str = "تجربی",
    province: str = "تهران",
    bomi_type: str = "keshvari",
    predicted=None,
    historical=None,
    bomi=None,
    academic=None,
):
    admission = {
        "method": method,
        "course_type": course_type,
        "bomi_type": bomi_type,
        "diploma_requirements": [diploma],
    }
    return {
        "program_id": program_id,
        "major_id": major_id,
        "university": {
            "name": "دانشگاه آزمون",
            "province": province,
            "prestige_level": 3,
        },
        "admission_info": admission,
        "cutoffs_predicted_1405": predicted or {},
        "cutoffs_historical": historical or {},
        "cutoffs_bomi": bomi or {},
        "cutoffs_savabegh": academic or {},
    }


EXAM_PROGRAM = _program(
    program_id="EXAM-1",
    major_id=1,
    method="با آزمون",
    course_type="roozaneh",
    predicted={"zone_1": 500, "zone_2": 1000, "zone_3": 1500, "isargaran_25": 300},
    historical={"1404": {"zone_2": 1100, "zone_3": 1600}},
)

SPECIAL_PROGRAM = _program(
    program_id="EXAM-2",
    major_id=1,
    method="با آزمون",
    course_type="nobat_dovom",
    predicted={"zone_2": 1000, "isargaran_25": 300},
)

SPECIAL_FALLBACK_PROGRAM = _program(
    program_id="EXAM-3",
    major_id=1,
    method="با آزمون",
    course_type="nobat_dovom",
    predicted={"zone_2": 1000},
)

ACADEMIC_PROGRAM = _program(
    program_id="ACA-1",
    major_id=1,
    method="سوابق تحصیلی",
    course_type="savabegh_dolati",
    academic={"minimum_gpa": 14, "minimum_traz": 6000},
)

GHOTBI_PROGRAM = _program(
    program_id="GHOTBI-1",
    major_id=1,
    method="با آزمون",
    course_type="roozaneh",
    province="اصفهان",
    bomi_type="ghotbi",
    predicted={"zone_2": 1000},
)

OSTANI_BOMI_PROGRAM = _program(
    program_id="OSTANI-1",
    major_id=1,
    method="با آزمون",
    course_type="roozaneh",
    province="تهران",
    bomi_type="ostani",
    predicted={"zone_2": 900},
    historical={"1404": {"zone_2": 950}},
    bomi={"1404": {"zone_2": 700}},
)

MAJORS = {"1": {"id": 1, "name": "نمونه", "exam_group": "تجربی"}}


class AdmissionChanceServiceTests(unittest.TestCase):
    def test_filtering_separates_exam_and_record_methods(self):
        kept_exam = filter_programs(
            [EXAM_PROGRAM, ACADEMIC_PROGRAM],
            major_ids=[1],
            admission_method=EXAM_METHOD,
        )
        kept_record = filter_programs(
            [EXAM_PROGRAM, ACADEMIC_PROGRAM],
            major_ids=[1],
            admission_method="سوابق تحصیلی",
        )
        self.assertEqual([item["program_id"] for item in kept_exam], ["EXAM-1"])
        self.assertEqual([item["program_id"] for item in kept_record], ["ACA-1"])

    def test_source_dataset_has_expected_program_count_and_unique_ids(self):
        programs = load_programs()
        self.assertEqual(len(programs), 4150)
        self.assertEqual(len({str(item.get("program_id")) for item in programs}), 4150)

    def test_exam_region_1_vs_region_3_changes_dimension_and_cutoff(self):
        region_1 = build_exam_results(
            major_ids=[1], rank_in_quota=450, region_zone=1, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[EXAM_PROGRAM], limit=30,
        )[0]
        region_3 = build_exam_results(
            major_ids=[1], rank_in_quota=450, region_zone=3, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[EXAM_PROGRAM], limit=30,
        )[0]
        self.assertEqual(region_1["cutoff_dimension"], "zone_1")
        self.assertEqual(region_3["cutoff_dimension"], "zone_3")
        self.assertEqual(region_1["cutoff_used"], 500)
        self.assertEqual(region_3["cutoff_used"], 1500)

    def test_exam_special_quota_falls_back_to_region_when_dimension_missing(self):
        result = build_exam_results(
            major_ids=[1], rank_in_quota=700, region_zone=2, special_quota="isargaran_25",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["nobat_dovom"], programs=[SPECIAL_FALLBACK_PROGRAM], limit=30,
        )[0]
        self.assertEqual(result["cutoff_dimension"], "zone_2")
        self.assertEqual(result["cutoff_used"], 1000)
        self.assertEqual(result["cutoff_year"], 1405)
        self.assertIn("برای سهمیه خاص انتخاب‌شده cutoff مستقل در داده موجود نبود؛ cutoff منطقه", result["notes"][-1])

    def test_exam_special_quota_records_threshold_gap_explicitly(self):
        result = build_exam_results(
            major_ids=[1], rank_in_quota=250, region_zone=2, special_quota="isargaran_25",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["nobat_dovom"], programs=[SPECIAL_PROGRAM], limit=30,
        )[0]
        self.assertTrue(any(note.startswith("حدنصاب کامل سهمیه خاص در این نسخه اعمال نشده است") for note in result["notes"]))

    def test_exam_special_quota_uses_special_dimension_when_available(self):
        result = build_exam_results(
            major_ids=[1], rank_in_quota=250, region_zone=2, special_quota="isargaran_25",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["nobat_dovom"], programs=[SPECIAL_PROGRAM], limit=30,
        )[0]
        self.assertEqual(result["cutoff_dimension"], "isargaran_25")
        self.assertEqual(result["cutoff_used"], 300)
        self.assertIn("dimension سهمیه خاص", result["note"])

    def test_cutoffs_bomi_is_not_preferred_over_predicted_or_historical(self):
        result = build_exam_results(
            major_ids=[1], rank_in_quota=800, region_zone=2, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[OSTANI_BOMI_PROGRAM], limit=30,
        )[0]
        self.assertEqual(result["cutoff_dimension"], "zone_2")
        self.assertEqual(result["cutoff_used"], 900)
        self.assertEqual(result["cutoff_year"], 1405)
        self.assertIn("ظرفیت تفکیکی در داده نیست", result["notes"])

    def test_ghotbi_has_explicit_incomplete_locality_note(self):
        result = build_exam_results(
            major_ids=[1], rank_in_quota=900, region_zone=2, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[GHOTBI_PROGRAM], limit=30,
        )[0]
        self.assertIn("اعمال بومی قطبی/ناحیه‌ای ناقص است", result["notes"])
        self.assertIn("ظرفیت تفکیکی در داده نیست", result["notes"])

    def test_exam_output_contains_notes_array(self):
        result = build_exam_results(
            major_ids=[1], rank_in_quota=450, region_zone=1, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[EXAM_PROGRAM], limit=30,
        )[0]
        self.assertIsInstance(result["notes"], list)
        self.assertIn("cutoff_dimension", result)
        self.assertIn("cutoff_used", result)
        self.assertIn("cutoff_year", result)

    def test_exam_gpa_does_not_change_rank_label(self):
        with_gpa = build_exam_results(
            major_ids=[1], rank_in_quota=850, region_zone=2, special_quota="none",
            province="تهران", diploma_type="tajrobi", gpa_written=19.0, national_rank=None,
            course_types=["roozaneh"], programs=[EXAM_PROGRAM], limit=30,
        )[0]
        without_gpa = build_exam_results(
            major_ids=[1], rank_in_quota=850, region_zone=2, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[EXAM_PROGRAM], limit=30,
        )[0]
        self.assertEqual(with_gpa["label"], without_gpa["label"])
        self.assertEqual(with_gpa["cutoff_used"], without_gpa["cutoff_used"])

    def test_record_human_diploma_for_tajrobi_group_uses_57_1(self):
        result = build_record_results(
            major_ids=[1], diploma_type="ensani", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )[0]
        self.assertEqual(result["gpa_coefficient"], 57.1)
        self.assertAlmostEqual(result["gpa_effective"], 10.278, places=4)
        self.assertEqual(result["gpa_input"], 18.0)
        self.assertEqual(result["cutoff_used"]["minimum_gpa"], 14)
        self.assertEqual(result["label"], RECORD_BELOW_LABEL)

    def test_record_rank_is_not_used_in_label(self):
        a = build_record_results(
            major_ids=[1], diploma_type="ensani", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )[0]
        b = build_record_results(
            major_ids=[1], diploma_type="ensani", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )[0]
        self.assertEqual(a["label"], b["label"])
        self.assertNotIn("rank", a)


    def test_target_group_can_be_inferred_from_major_metadata(self):
        result = build_record_results(
            major_ids=[1],
            diploma_type="ensani",
            gpa_written=18.0,
            gpa_total=None,
            province="تهران",
            target_field_group=None,
            course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM],
            majors=MAJORS,
            limit=30,
        )[0]
        self.assertEqual(result["target_field_group"], "tajrobi")
        self.assertEqual(result["gpa_coefficient"], 57.1)

    def test_record_other_fani_requires_gpa_total(self):
        with self.assertRaises(ValueError):
            build_record_results(
                major_ids=[1], diploma_type="other_fani", gpa_written=18.0, gpa_total=None,
                province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
                programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
            )

    def test_record_exposes_traz_but_discloses_it_is_not_comparable_without_input(self):
        result = build_record_results(
            major_ids=[1], diploma_type="ensani", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="ensani", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )[0]
        self.assertEqual(result["cutoff_used"]["minimum_traz"], 6000)
        self.assertTrue(any("ورودی تراز داوطلب" in note for note in result["notes"]))

    def test_record_label_uses_only_three_qualitative_labels(self):
        labels = set()
        for gpa in (10.0, 14.0, 20.0):
            result = build_record_results(
                major_ids=[1], diploma_type="ensani", gpa_written=gpa, gpa_total=None,
                province="تهران", target_field_group="ensani", course_types=["savabegh_dolati"],
                programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
            )[0]
            labels.add(result["label"])
        self.assertTrue(labels.issubset({HIGHER_LABEL, BORDERLINE_LABEL, LOWER_LABEL}))

    def test_record_effective_gpa_above_cutoff_is_qualitative(self):
        result = build_record_results(
            major_ids=[1], diploma_type="ensani", gpa_written=20.0, gpa_total=None,
            province="تهران", target_field_group="ensani", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )[0]
        self.assertEqual(result["gpa_coefficient"], 100.0)
        self.assertAlmostEqual(result["gpa_effective"], 20.0, places=4)
        self.assertEqual(result["label"], RECORD_ABOVE_LABEL)

    def test_ghotbi_keeps_caution(self):
        result = build_exam_results(
            major_ids=[1], rank_in_quota=900, region_zone=2, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[GHOTBI_PROGRAM], limit=30,
        )[0]
        self.assertEqual(result["label"], HIGHER_LABEL)
        self.assertIn(GHOTBI_NOTE, result["notes"])
        self.assertIn("ظرفیت تفکیکی در داده نیست", result["notes"])


class AdmissionChanceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_invalid_province_returns_400(self):
        response = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "exam",
                "major_ids": [1],
                "rank_in_quota": 850,
                "region_zone": 2,
                "special_quota": "none",
                "province": "استان نامعتبر",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("استان نامعتبر", response.json()["detail"])

    def test_exam_request_keeps_region_and_special_quota_separate(self):
        with patch("admission_chance_api.load_programs", return_value=(SPECIAL_PROGRAM,)):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "exam",
                    "major_ids": [1],
                    "rank_in_quota": 250,
                    "region_zone": 2,
                    "special_quota": "isargaran_25",
                    "province": "تهران",
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["context"]["region_zone"], 2)
        self.assertEqual(payload["context"]["special_quota"], "isargaran_25")
        self.assertEqual(payload["items"][0]["cutoff_dimension"], "isargaran_25")

    def test_record_request_uses_gpa_coefficient(self):
        with patch("admission_chance_api.load_programs", return_value=(ACADEMIC_PROGRAM,)),              patch("admission_chance_api.load_majors", return_value=MAJORS):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "record",
                    "major_ids": [1],
                    "province": "تهران",
                    "diploma_type": "ensani",
                    "gpa_written": 18.0,
                    "target_field_group": "tajrobi",
                    "rank_in_quota": 1,
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()["items"][0]
        self.assertEqual(item["gpa_coefficient"], 57.1)
        self.assertAlmostEqual(item["gpa_effective"], 10.278, places=4)
        self.assertIn("gpa_effective", item)
        self.assertIn("جایگزین دفترچه و اعلام رسمی سنجش نیست", response.json()["disclaimer"])

    def test_record_request_without_rank_returns_200(self):
        with patch("admission_chance_api.load_programs", return_value=(ACADEMIC_PROGRAM,)),              patch("admission_chance_api.load_majors", return_value=MAJORS):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "record",
                    "major_ids": [1],
                    "province": "تهران",
                    "diploma_type": "ensani",
                    "gpa_written": 18.0,
                    "target_field_group": "tajrobi",
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["admission_path"], "record")
        self.assertNotIn("rank_in_quota", payload["context"])
        self.assertIsInstance(payload["items"][0]["notes"], list)

    def test_record_only_exam_major_returns_empty_items_without_500(self):
        with patch("admission_chance_api.load_programs", return_value=(EXAM_PROGRAM,)),              patch("admission_chance_api.load_majors", return_value=MAJORS):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "record",
                    "major_ids": [1],
                    "province": "تهران",
                    "diploma_type": "ensani",
                    "gpa_written": 18.0,
                    "target_field_group": "tajrobi",
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["count"], 0)

    def test_record_theoretical_requires_gpa_written(self):
        response = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "record",
                "major_ids": [1],
                "province": "تهران",
                "diploma_type": "ensani",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("gpa_written", response.json()["detail"])

    def test_record_fani_requires_gpa_total(self):
        response = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "record",
                "major_ids": [1],
                "province": "تهران",
                "diploma_type": "other_fani",
                "gpa_written": 18.0,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("gpa_total", response.json()["detail"])

    def test_missing_admission_path_rejects_nonlegacy_request(self):
        response = self.client.post(
            "/api/v1/admission/chance",
            json={
                "major_ids": [1],
                "province": "تهران",
                "diploma_type": "ensani",
                "gpa_written": 18.0,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("admission_path", response.json()["detail"])

    def test_legacy_special_quota_maps_without_merging_region(self):
        with patch("admission_chance_api.load_programs", return_value=(SPECIAL_PROGRAM,)):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "major_ids": [1],
                    "rank": 250,
                    "region_zone": 2,
                    "quota": "isargaran_25",
                    "province": "تهران",
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["context"]["region_zone"], 2)
        self.assertEqual(payload["context"]["special_quota"], "isargaran_25")
        self.assertEqual(payload["items"][0]["cutoff_dimension"], "isargaran_25")

    def test_legacy_exam_contract_still_works(self):
        with patch("admission_chance_api.load_programs", return_value=(EXAM_PROGRAM,)):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "major_ids": [1],
                    "rank": 850,
                    "region_zone": 2,
                    "quota": "azad",
                    "province": "تهران",
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["admission_path"], "exam")


if __name__ == "__main__":
    unittest.main(verbosity=2)
