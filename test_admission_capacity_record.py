import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from admission_capacity_record import (
    build_record_capacity_results,
    load_record_capacity_rows,
    record_capacity_periods,
)
from main_v2 import app


class RecordCapacityDirectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_record_capacity_rows()
        cls.periods = record_capacity_periods()
        cls.client = TestClient(app)

    def _real_case(self):
        from admission_sanjesh_engine import load_majors

        majors = load_majors()
        for row in self.rows:
            province = str(row.get("province") or "").strip()
            period = str(row.get("period") or "").strip()
            major_name = str(row.get("major_name") or "").strip()
            if not province or not period or not major_name:
                continue
            ids = [
                int(key)
                for key, value in majors.items()
                if str(value.get("name") or "").strip() == major_name
            ]
            if ids:
                return ids[0], province, period
        self.fail("No usable real capacity/major sample found")

    def _approved_real_case(self):
        from admission_sanjesh_engine import load_majors

        major_id = 81
        province = "آذربایجان غربی"
        period = "روزانه"
        majors = load_majors()
        major = majors.get(str(major_id))
        self.assertIsInstance(major, dict)
        major_name = str(major.get("name") or "").strip()
        self.assertTrue(major_name)
        source_rows = [
            row
            for row in self.rows
            if str(row.get("major_name") or "").strip() == major_name
            and str(row.get("province") or "").strip() == province
            and str(row.get("period") or "").strip() == period
            and str(row.get("sanjesh_code") or "").strip()
        ]
        self.assertGreater(
            len(source_rows),
            0,
            "Approved capacity smoke sample major_id=81 / آذربایجان غربی / روزانه is missing from source",
        )
        return major_id, province, period, major_name

    def test_approved_major_81_west_azerbaijan_daily_returns_capacity(self):
        major_id, province, period, _ = self._approved_real_case()
        items = build_record_capacity_results(
            major_ids=[major_id], province=province, periods=[period]
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(items[0]["sanjesh_code"])

    def test_real_major_period_province_returns_capacity_and_sanjesh_code(self):
        major_id, province, period = self._real_case()
        items = build_record_capacity_results(
            major_ids=[major_id], province=province, periods=[period]
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(items[0]["sanjesh_code"])
        self.assertEqual(items[0]["period"], period)
        self.assertEqual(items[0]["province"], province)
        self.assertIn("capacity_total", items[0])
        self.assertIsInstance(items[0]["notes"], list)

    def test_other_province_reduces_or_removes_rows_for_approved_case(self):
        major_id, province, period, _ = self._approved_real_case()
        baseline = build_record_capacity_results(
            major_ids=[major_id], province=province, periods=[period]
        )
        changed = build_record_capacity_results(
            major_ids=[major_id], province="تهران", periods=[period]
        )
        self.assertLessEqual(len(changed), len(baseline))
        self.assertTrue(all(item["province"] == "تهران" for item in changed))

    def test_unknown_period_returns_no_items(self):
        major_id, province, _ = self._real_case()
        items = build_record_capacity_results(
            major_ids=[major_id],
            province=province,
            periods=["__period_not_in_sanjesh_source__"],
        )
        self.assertEqual(items, [])

    def test_blank_source_province_never_matches_named_province(self):
        major_id, province, period, major_name = self._approved_real_case()
        blank_row = {
            "sanjesh_code": "__blank-province-test__",
            "major_name": major_name,
            "period": period,
            "province": "",
            "campus": "blank-province-test",
            "capacity": 99,
        }
        with patch(
            "admission_capacity_record.load_record_capacity_rows",
            return_value=tuple(self.rows) + (blank_row,),
        ):
            items = build_record_capacity_results(
                major_ids=[major_id], province=province, periods=[period]
            )
        self.assertTrue(all(item["sanjesh_code"] != blank_row["sanjesh_code"] for item in items))
        self.assertTrue(all(str(item["province"]).strip() == province for item in items))

    def test_named_province_never_returns_blank_province(self):
        major_id, province, period = self._real_case()
        items = build_record_capacity_results(
            major_ids=[major_id], province=province, periods=[period]
        )
        self.assertTrue(all(str(item["province"]).strip() == province for item in items))

    def test_special_quota_is_note_only(self):
        major_id, province, period = self._real_case()
        items = build_record_capacity_results(
            major_ids=[major_id],
            province=province,
            periods=[period],
            special_quota="isargaran_25",
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(any("special_quota" in note for note in items[0]["notes"]))


class RecordCapacityApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _real_case(self):
        from admission_sanjesh_engine import load_majors

        rows = load_record_capacity_rows()
        majors = load_majors()
        for row in rows:
            province = str(row.get("province") or "").strip()
            period = str(row.get("period") or "").strip()
            major_name = str(row.get("major_name") or "").strip()
            ids = [
                int(key)
                for key, value in majors.items()
                if str(value.get("name") or "").strip() == major_name
            ]
            if province and period and ids:
                return ids[0], province, period
        raise AssertionError("No real API sample found")

    def test_capacity_api_returns_real_item(self):
        major_id, province, period = self._real_case()
        response = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "record",
                "source": "capacity",
                "major_ids": [major_id],
                "province": province,
                "periods": [period],
                "diploma_type": "tajrobi",
                "gpa_written": 18.0,
                "special_quota": "none",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["admission_path"], "record")
        self.assertEqual(payload["source"], "capacity")
        self.assertGreater(payload["count"], 0)
        self.assertTrue(payload["items"][0]["sanjesh_code"])

    def test_capacity_api_wrong_province_reduces_or_zeros(self):
        major_id, province, period = self._real_case()
        from admission_sanjesh_engine import PROVINCE_OPTIONS

        wrong = next(candidate for candidate in PROVINCE_OPTIONS if candidate != province)
        good = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "record",
                "source": "capacity",
                "major_ids": [major_id],
                "province": province,
                "periods": [period],
                "diploma_type": "tajrobi",
                "gpa_written": 18.0,
            },
        )
        changed = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "record",
                "source": "capacity",
                "major_ids": [major_id],
                "province": wrong,
                "periods": [period],
                "diploma_type": "tajrobi",
                "gpa_written": 18.0,
            },
        )
        self.assertEqual(good.status_code, 200, good.text)
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertLessEqual(changed.json()["count"], good.json()["count"])

    def test_capacity_api_unknown_period_returns_empty_with_note(self):
        major_id, province, _ = self._real_case()
        response = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "record",
                "source": "capacity",
                "major_ids": [major_id],
                "province": province,
                "periods": ["__period_not_in_sanjesh_source__"],
                "diploma_type": "tajrobi",
                "gpa_written": 18.0,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["count"], 0)
        self.assertTrue(payload["notes"])

    def test_existing_record_program_route_remains_unchanged(self):
        program = {
            "program_id": "REG-RECORD-1",
            "major_id": 1,
            "university": {"name": "دانشگاه آزمون", "province": "تهران", "prestige_level": 3},
            "admission_info": {
                "method": "سوابق تحصیلی",
                "course_type": "savabegh_dolati",
                "bomi_type": "keshvari",
                "diploma_requirements": {"accepts_diploma_types": ["تجربی"], "is_floating": False},
            },
            "cutoffs_savabegh": {"minimum_gpa": 14},
            "cutoffs_predicted_1405": {},
            "cutoffs_historical": {},
        }
        majors = {"1": {"id": 1, "name": "اقتصاد", "exam_group": "تجربی"}}
        with patch("admission_chance_api.load_programs", return_value=(program,)), \
             patch("admission_chance_api.load_majors", return_value=majors):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "record",
                    "source": "program",
                    "major_ids": [1],
                    "province": "تهران",
                    "region_zone": 2,
                    "special_quota": "none",
                    "diploma_type": "tajrobi",
                    "gpa_written": 18.0,
                    "target_field_group": "tajrobi",
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["admission_path"], "record")
        self.assertEqual(response.json()["source"], "program")


if __name__ == "__main__":
    unittest.main()
