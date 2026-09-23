from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from admission_chance_api import (
    ACADEMIC_GPA_LOW_LABEL,
    ACADEMIC_GPA_OK_LABEL,
    ACADEMIC_LABEL,
    BORDERLINE_LABEL,
    GHOTBI_NOTE,
    HIGHER_LABEL,
    LOWER_LABEL,
    build_results,
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
        "cutoffs_bomi": {},
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

BORDER_PROGRAM = _program(
    program_id="EXAM-2",
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


class AdmissionChanceServiceTests(unittest.TestCase):
    def test_filtering_uses_major_diploma_and_course_type(self):
        other_major = _program(
            program_id="OTHER-1",
            major_id=2,
            method="با آزمون",
            course_type="roozaneh",
            diploma="ریاضی",
            predicted={"zone_2": 900},
        )
        kept = filter_programs(
            [EXAM_PROGRAM, BORDER_PROGRAM, other_major, ACADEMIC_PROGRAM],
            major_ids=[1],
            diploma_type="تجربی",
            course_types=["roozaneh"],
        )
        self.assertEqual([item["program_id"] for item in kept], ["EXAM-1"])

    def test_source_dataset_has_expected_program_count_and_unique_ids(self):
        programs = load_programs()
        self.assertEqual(len(programs), 4150)
        self.assertEqual(
            len({str(item.get("program_id")) for item in programs}),
            4150,
        )

    def test_ostani_bomi_uses_matching_province_and_latest_bomi_cutoff(self):
        program = _program(
            program_id="BOMI-1",
            major_id=1,
            method="با آزمون",
            course_type="roozaneh",
            province="تهران",
            bomi_type="ostani",
            predicted={"zone_2": 1200},
            historical={"1404": {"zone_2": 1100}},
        )
        program["cutoffs_bomi"] = {
            "1403": {"zone_2": 800},
            "1404": {"zone_2": 700},
        }
        result = build_results(
            major_ids=[1],
            programs=[program],
            rank_in_quota=600,
            quota_type="region_2",
            province="تهران",
            diploma_type="تجربی",
            gpa_written=None,
            course_types=["roozaneh"],
            limit=30,
        )[0]
        self.assertEqual(result["cutoff_used"], 700)
        self.assertEqual(result["cutoff_year"], 1404)
        self.assertEqual(result["cutoff_dimension"], "zone_2")
        self.assertEqual(result["label"], HIGHER_LABEL)

    def test_quota_change_changes_cutoff_dimension_and_value(self):
        region_1 = build_results(
            major_ids=[1],
            programs=[EXAM_PROGRAM],
            rank_in_quota=450,
            quota_type="region_1",
            province="تهران",
            diploma_type="تجربی",
            course_types=["roozaneh"],
            limit=30,
        )[0]
        region_3 = build_results(
            major_ids=[1],
            programs=[EXAM_PROGRAM],
            rank_in_quota=450,
            quota_type="region_3",
            province="تهران",
            diploma_type="تجربی",
            course_types=["roozaneh"],
            limit=30,
        )[0]
        self.assertEqual(region_1["cutoff_dimension"], "zone_1")
        self.assertEqual(region_3["cutoff_dimension"], "zone_3")
        self.assertEqual(region_1["cutoff_used"], 500)
        self.assertEqual(region_3["cutoff_used"], 1500)
        self.assertNotEqual(region_1["cutoff_used"], region_3["cutoff_used"])

    def test_special_quota_uses_its_own_dimension(self):
        result = build_results(
            major_ids=[1],
            programs=[EXAM_PROGRAM],
            rank_in_quota=250,
            quota_type="isargaran_25",
            province="تهران",
            diploma_type="تجربی",
            course_types=["roozaneh"],
            limit=30,
        )[0]
        self.assertEqual(result["cutoff_dimension"], "isargaran_25")
        self.assertEqual(result["cutoff_used"], 300)

    def test_rank_better_than_cutoff_gets_higher_label(self):
        result = build_results(
            major_ids=[1],
            programs=[EXAM_PROGRAM],
            rank_in_quota=850,
            quota_type="region_2",
            province="تهران",
            diploma_type="تجربی",
            gpa_written=18.5,
            course_types=["roozaneh"],
            limit=30,
        )[0]
        self.assertEqual(result["label"], HIGHER_LABEL)
        self.assertEqual(result["cutoff_used"], 1000)
        self.assertEqual(result["cutoff_year"], 1405)

    def test_rank_near_cutoff_gets_borderline_label(self):
        result = build_results(
            major_ids=[1],
            programs=[BORDER_PROGRAM],
            rank_in_quota=1050,
            quota_type="region_2",
            province="تهران",
            diploma_type="تجربی",
            gpa_written=18.5,
            course_types=["nobat_dovom"],
            limit=30,
        )[0]
        self.assertEqual(result["label"], BORDERLINE_LABEL)

    def test_rank_worse_than_cutoff_gets_lower_label(self):
        result = build_results(
            major_ids=[1],
            programs=[EXAM_PROGRAM],
            rank_in_quota=1200,
            quota_type="region_2",
            province="تهران",
            diploma_type="تجربی",
            gpa_written=18.5,
            course_types=["roozaneh"],
            limit=30,
        )[0]
        self.assertEqual(result["label"], LOWER_LABEL)

    def test_academic_uses_only_written_gpa_and_ignores_rank(self):
        low_gpa_result = build_results(
            major_ids=[1],
            programs=[ACADEMIC_PROGRAM],
            rank_in_quota=1,
            quota_type="region_1",
            province="تهران",
            diploma_type="تجربی",
            gpa_written=13.5,
            course_types=["savabegh_dolati"],
            limit=30,
        )[0]
        high_gpa_result = build_results(
            major_ids=[1],
            programs=[ACADEMIC_PROGRAM],
            rank_in_quota=999999,
            quota_type="region_3",
            province="تهران",
            diploma_type="تجربی",
            gpa_written=15.0,
            national_rank=1,
            course_types=["savabegh_dolati"],
            limit=30,
        )[0]
        self.assertEqual(low_gpa_result["label"], ACADEMIC_GPA_LOW_LABEL)
        self.assertEqual(high_gpa_result["label"], ACADEMIC_GPA_OK_LABEL)
        self.assertEqual(low_gpa_result["cutoff_used"]["minimum_gpa"], 14)
        self.assertEqual(high_gpa_result["cutoff_used"]["minimum_gpa"], 14)

    def test_gpa_path_never_uses_rank_cutoff(self):
        result_a = build_results(
            major_ids=[1],
            programs=[ACADEMIC_PROGRAM],
            rank_in_quota=1,
            quota_type="region_1",
            province="تهران",
            gpa_written=15.0,
            limit=30,
        )[0]
        result_b = build_results(
            major_ids=[1],
            programs=[ACADEMIC_PROGRAM],
            rank_in_quota=500000,
            quota_type="region_3",
            province="تهران",
            gpa_written=15.0,
            limit=30,
        )[0]
        self.assertEqual(result_a["label"], result_b["label"])
        self.assertEqual(result_a["cutoff_used"], result_b["cutoff_used"])
        self.assertNotIn("cutoff_year", result_a, msg="academic result must not expose rank cutoff year")

    def test_ghotbi_returns_explicit_official_mapping_caution(self):
        result = build_results(
            major_ids=[1],
            programs=[GHOTBI_PROGRAM],
            rank_in_quota=900,
            quota_type="region_2",
            province="تهران",
            diploma_type="تجربی",
            gpa_written=None,
            course_types=["roozaneh"],
            limit=30,
        )[0]
        self.assertEqual(result["label"], HIGHER_LABEL)
        self.assertEqual(result["note"], GHOTBI_NOTE)

    def test_unsupported_quota_does_not_fallback_silently(self):
        with self.assertRaises(ValueError):
            build_results(
                major_ids=[1],
                programs=[EXAM_PROGRAM],
                rank_in_quota=900,
                quota_type="unsupported_quota",
                province="تهران",
                limit=30,
            )


class AdmissionChanceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_missing_required_fields_returns_400(self):
        response = self.client.post("/api/v1/admission/chance", json={"major_ids": [1]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("رتبه", response.json()["detail"])
        self.assertIn("استان", response.json()["detail"])

    def test_missing_province_returns_400(self):\n        body = {\n            "major_ids": [1],\n            "rank_in_quota": 850,\n            "quota_type": "region_2",\n        }\n        response = self.client.post("/api/v1/admission/chance", json=body)\n        self.assertEqual(response.status_code, 400)\n        self.assertIn("استان", response.json()["detail"])\n\n    def test_invalid_province_returns_400(self):
        body = {
            "major_ids": [1],
            "rank_in_quota": 850,
            "quota_type": "region_2",
            "province": "استان نامعتبر",
            "gpa_written": 18.5,
        }
        response = self.client.post("/api/v1/admission/chance", json=body)
        self.assertEqual(response.status_code, 400)
        self.assertIn("استان نامعتبر", response.json()["detail"])

    def test_invalid_quota_type_returns_400_without_zone_fallback(self):
        body = {
            "major_ids": [1],
            "rank_in_quota": 850,
            "quota_type": "unsupported_quota",
            "province": "تهران",
            "gpa_written": 18.5,
        }
        response = self.client.post("/api/v1/admission/chance", json=body)
        self.assertEqual(response.status_code, 400)
        self.assertIn("quota_type", response.json()["detail"])

    def test_runtime_fingerprint_reports_admission_file_and_route(self):
        response = self.client.get("/__runtime_fingerprint")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        file_info = payload["admission_runtime_files"]["admission_chance_api.py"]
        self.assertTrue(file_info["available"])
        self.assertEqual(len(file_info["sha256"]), 64)
        self.assertIn("admission_route_probe", payload)
        self.assertTrue(payload["admission_route_probe"]["registered"])
        self.assertEqual(
            payload["admission_route_probe"]["resolved_path"],
            "/api/v1/admission/chance",
        )

    def test_runtime_module_paths_and_registered_routes(self):
        response = self.client.get("/__runtime_fingerprint")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        diagnostics = payload["runtime_module_diagnostics"]

        self.assertTrue(diagnostics["commercial_api"]["loaded"])
        self.assertTrue(diagnostics["admission_chance_api"]["loaded"])
        self.assertTrue(diagnostics["commercial_api"]["file"].endswith("commercial_api.py"))
        self.assertTrue(diagnostics["admission_chance_api"]["file"].endswith("admission_chance_api.py"))

        admission_module_routes = diagnostics["admission_module_routes"]
        self.assertTrue(
            any(
                route["path"] == "/admission/chance"
                and "POST" in route["methods"]
                and route["endpoint_module"] == "admission_chance_api"
                for route in admission_module_routes
            )
        )

        app_routes = diagnostics["app_registered_routes"]
        self.assertTrue(app_routes)
        self.assertIn("admission_route_probe", payload)
        self.assertTrue(payload["admission_route_probe"]["registered"])
        self.assertEqual(
            payload["admission_route_probe"]["resolved_path"],
            "/api/v1/admission/chance",
        )

    def test_endpoint_returns_new_contract_and_qualitative_items(self):
        with patch(
            "admission_chance_api.load_programs",
            return_value=(EXAM_PROGRAM, ACADEMIC_PROGRAM),
        ):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "major_ids": [1],
                    "rank_in_quota": 850,
                    "quota_type": "region_2",
                    "province": "تهران",
                    "gpa_written": 18.5,
                    "gpa_total": 19.0,
                    "national_rank": 1200,
                    "course_types": ["roozaneh", "savabegh_dolati"],
                    "diploma_type": "تجربی",
                    "limit": 30,
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["context"]["quota_type"], "region_2")
        self.assertEqual(payload["context"]["cutoff_dimension"], "zone_2")
        self.assertEqual(payload["items"][0]["label"], HIGHER_LABEL)
        self.assertEqual(payload["items"][1]["label"], ACADEMIC_GPA_OK_LABEL)
        self.assertIn("جایگزین دفترچه و نتایج رسمی سنجش نیست", payload["disclaimer"])

    def test_legacy_contract_still_works(self):
        with patch(
            "admission_chance_api.load_programs",
            return_value=(EXAM_PROGRAM,),
        ):
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
        payload = response.json()
        self.assertEqual(payload["context"]["quota_type"], "region_2")
        self.assertEqual(payload["context"]["cutoff_dimension"], "zone_2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
