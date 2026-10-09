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
    normalize_diploma_requirements,
    load_bomi_geography,
    load_bomi_table5,
    load_programs,
    load_majors,
    _coefficient,
    _resolve_record_bomi,
)
from admission_exam_capacity import build_exam_capacity_results
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
    university_name: str = "دانشگاه آزمون",
):
    admission = {
        "method": method,
        "course_type": course_type,
        "bomi_type": bomi_type,
        "diploma_requirements": {"accepts_diploma_types": [diploma, "انسانی"], "is_floating": False},
    }
    return {
        "program_id": program_id,
        "major_id": major_id,
        "university": {
            "name": university_name,
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

SPECIAL_HISTORICAL_PROGRAM = _program(
    program_id="EXAM-4",
    major_id=1,
    method="با آزمون",
    course_type="nobat_dovom",
    predicted={"zone_2": 1000, "isargaran_25": 300},
    historical={"1403": {"isargaran_25": 190}, "1404": {"isargaran_25": 200}},
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

NAHIYE_RECORD_PROGRAM = _program(
    program_id="NAHIYE-RECORD-1",
    major_id=1,
    method="سوابق تحصیلی",
    course_type="payam_noor",
    province="خراسان شمالی",
    bomi_type="nahiyei",
    academic={"minimum_gpa": 14, "minimum_traz": 6000},
)

OSTANI_RECORD_PROGRAM = _program(
    program_id="OSTANI-RECORD-1",
    major_id=1,
    method="سوابق تحصیلی",
    course_type="savabegh_dolati",
    province="تهران",
    bomi_type="ostani",
    academic={"minimum_gpa": 14, "minimum_traz": 6000},
)

MAJORS = {"1": {"id": 1, "name": "اقتصاد", "exam_group": "تجربی"}}

Nahiye_RECORD_PROGRAM = _program(
    program_id="NAHIYE-RECORD-1",
    major_id=1,
    method="سوابق تحصیلی",
    course_type="payam_noor",
    province="خراسان شمالی",
    bomi_type="nahiyei",
    academic={"minimum_gpa": 14, "minimum_traz": 6000},
)

GHOTBI_RECORD_PROGRAM = _program(
    program_id="GHOTBI-RECORD-1",
    major_id=1,
    method="سوابق تحصیلی",
    course_type="savabegh_dolati",
    province="کرمان",
    bomi_type="ghotbi",
    academic={"minimum_gpa": 14, "minimum_traz": 6000},
)

AZAD_RECORD_PROGRAM = _program(
    program_id="AZAD-RECORD-1",
    major_id=1,
    method="سوابق تحصیلی",
    course_type="savabegh_dolati",
    province="تهران",
    bomi_type="keshvari",
    academic={"minimum_gpa": 14},
    university_name="دانشگاه آزاد اسلامی واحد نمونه",
)

KESHVARI_RECORD_PROGRAM = _program(
    program_id="KESHVARI-RECORD-1",
    major_id=1,
    method="سوابق تحصیلی",
    course_type="pardis",
    province="کرمان",
    bomi_type="keshvari",
    academic={"minimum_gpa": 14, "minimum_traz": 6000},
)

UNRESOLVED_TABLE5_RECORD = _program(
    program_id="UNRESOLVED-TABLE5-RECORD",
    major_id=999,
    method="سوابق تحصیلی",
    course_type="savabegh_dolati",
    province="تهران",
    bomi_type="",
    academic={"minimum_gpa": 14},
)
UNRESOLVED_TABLE5_RECORD["admission_info"]["bomi_type_rule"] = "unresolved_table5"

EMPTY_BOMI_NOBAT_RECORD = _program(
    program_id="EMPTY-BOMI-NOBAT",
    major_id=1,
    method="سوابق تحصیلی",
    course_type="nobat_dovom",
    province="تهران",
    bomi_type="",
    academic={"minimum_gpa": 14},
)

EMPTY_BOMI_ROOZANEH_RECORD = _program(
    program_id="EMPTY-BOMI-ROOZANEH",
    major_id=999,
    method="سوابق تحصیلی",
    course_type="roozaneh",
    province="اصفهان",
    bomi_type="",
    academic={"minimum_gpa": 14},
)

UNRESOLVED_ROOZANEH_MAJORS = {
    "999": {"id": 999, "name": "رشته بدون جدول ۵", "exam_group": "تجربی"}
}



class AdmissionChanceServiceTests(unittest.TestCase):

    def test_diploma_requirements_normalizer_supports_production_and_legacy_shapes(self):
        production = normalize_diploma_requirements({
            "accepts_diploma_types": ["ریاضی", "تجربی"],
            "is_floating": True,
        })
        legacy = normalize_diploma_requirements(["riazi", "تجربی"])
        empty = normalize_diploma_requirements(None)
        self.assertEqual(production["accepts_diploma_types"], ["ریاضی", "تجربی"])
        self.assertIs(production["is_floating"], True)
        self.assertEqual(legacy["accepts_diploma_types"], ["riazi", "تجربی"])
        self.assertIs(legacy["is_floating"], False)
        self.assertEqual(empty, {"accepts_diploma_types": [], "is_floating": False})

    def test_bomi_geography_has_31_provinces_and_valid_ids(self):
        geography = load_bomi_geography()
        self.assertEqual(len(geography), 31)
        self.assertTrue(all(1 <= int(item["nahiye_id"]) <= 9 for item in geography.values()))
        self.assertTrue(all(1 <= int(item["ghotb_id"]) <= 5 for item in geography.values()))
        self.assertEqual(geography["تهران"]["nahiye_id"], 1)
        self.assertEqual(geography["گلستان"]["nahiye_id"], 9)
        self.assertEqual(geography["خراسان رضوی"]["ghotb_id"], 2)
        self.assertEqual(geography["فارس"]["ghotb_id"], 5)

    def test_real_program2s_payam_noor_tehran_vs_kerman(self):
        programs = [item for item in load_programs() if item.get("program_id") == "PROG_03158"]
        self.assertEqual(len(programs), 1)
        program = programs[0]
        self.assertEqual(program["admission_info"]["course_type"], "payam_noor")
        self.assertEqual(program["admission_info"]["bomi_type"], "nahiyei")
        self.assertEqual(program["university"]["province"], "تهران")
        self.assertEqual(_resolve_record_bomi(program, load_majors()), ("nahiyei", "period_defaults"))

        local = build_record_results(
            major_ids=[41],
            diploma_type="riazi",
            gpa_written=18.0,
            gpa_total=None,
            province="تهران",
            target_field_group="riazi",
            course_types=["payam_noor"],
            programs=programs,
            majors=load_majors(),
            limit=30,
            region_zone=1,
            special_quota="none",
        )
        remote = build_record_results(
            major_ids=[41],
            diploma_type="riazi",
            gpa_written=18.0,
            gpa_total=None,
            province="کرمان",
            target_field_group="riazi",
            course_types=["payam_noor"],
            programs=programs,
            majors=load_majors(),
            limit=30,
            region_zone=2,
            special_quota="none",
        )
        self.assertEqual([item["program_id"] for item in local], ["PROG_03158"])
        self.assertEqual(remote, [])
        self.assertIn("بومی ناحیه‌ای", local[0]["note"])

    def test_real_program2s_nahiyei_locks_to_same_region(self):
        programs = [item for item in load_programs() if item.get("program_id") == "PROG_01000"]
        self.assertEqual(len(programs), 1)
        program = programs[0]
        self.assertEqual(program["admission_info"]["bomi_type"], "nahiyei")
        self.assertEqual(program["university"]["province"], "گیلان")
        self.assertEqual(_resolve_record_bomi(program, load_majors()), ("nahiyei", "table5_daily"))

        local = build_record_results(
            major_ids=[81],
            diploma_type="tajrobi",
            gpa_written=18.0,
            gpa_total=None,
            province="گیلان",
            target_field_group="tajrobi",
            course_types=["savabegh_dolati"],
            programs=programs,
            majors=load_majors(),
            limit=30,
            region_zone=2,
            special_quota="none",
        )
        remote = build_record_results(
            major_ids=[81],
            diploma_type="tajrobi",
            gpa_written=18.0,
            gpa_total=None,
            province="تهران",
            target_field_group="tajrobi",
            course_types=["savabegh_dolati"],
            programs=programs,
            majors=load_majors(),
            limit=30,
            region_zone=1,
            special_quota="none",
        )
        self.assertEqual([item["program_id"] for item in local], ["PROG_01000"])
        self.assertEqual(remote, [])
        self.assertIn("بومی ناحیه‌ای", local[0]["note"])

    def test_record_nahiyei_filters_same_region_and_rejects_other_region(self):
        same = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="خراسان رضوی", target_field_group="tajrobi",
            course_types=["payam_noor"], programs=[NAHIYE_RECORD_PROGRAM], majors=MAJORS, limit=30,
            region_zone=2, special_quota="none",
        )
        other = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi",
            course_types=["payam_noor"], programs=[NAHIYE_RECORD_PROGRAM], majors=MAJORS, limit=30,
            region_zone=1, special_quota="none",
        )
        self.assertEqual(len(same), 1)
        self.assertEqual(other, [])
        self.assertIn("بومی ناحیه‌ای", same[0]["note"])

    def test_record_ghotbi_filters_same_pole_and_rejects_other_pole(self):
        same = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="خراسان رضوی", target_field_group="tajrobi",
            course_types=["savabegh_dolati"], programs=[GHOTBI_RECORD_PROGRAM], majors=MAJORS, limit=30,
            region_zone=2, special_quota="none",
        )
        other = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi",
            course_types=["savabegh_dolati"], programs=[GHOTBI_RECORD_PROGRAM], majors=MAJORS, limit=30,
            region_zone=1, special_quota="none",
        )
        self.assertEqual(len(same), 1)
        self.assertEqual(other, [])
        self.assertIn("بومی قطبی", same[0]["note"])

    def test_record_azad_adds_fixed_note_without_filtering(self):
        result = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi",
            course_types=["savabegh_dolati"], programs=[AZAD_RECORD_PROGRAM], majors=MAJORS, limit=30,
            region_zone=1, special_quota="none",
        )
        self.assertEqual([item["program_id"] for item in result], ["AZAD-RECORD-1"])
        self.assertTrue(any(note == "سامانه آزاد؛ بومی‌گزینی سراسری کامل نیست" for note in result[0]["notes"]))

    def test_record_keshvari_does_not_filter_by_province(self):
        results = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi",
            course_types=["pardis"], programs=[KESHVARI_RECORD_PROGRAM], majors=MAJORS, limit=30,
            region_zone=1, special_quota="none",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["bomi_type"], "keshvari")
        self.assertIn("بومی کشوری: فیلتر استان/ناحیه/قطب اعمال نشد", results[0]["note"])

    def test_record_blank_bomi_uses_course_defaults(self):
        result = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi",
            course_types=["nobat_dovom"], programs=[EMPTY_BOMI_NOBAT_RECORD], majors=MAJORS, limit=30,
            region_zone=1, special_quota="none",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["bomi_type"], "ostani")
        self.assertEqual(result[0]["bomi_source"], "period_defaults")

    def test_record_unresolved_table5_is_excluded_from_main_results(self):
        result = build_record_results(
            major_ids=[999], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi",
            course_types=["savabegh_dolati"], programs=[UNRESOLVED_TABLE5_RECORD], majors=UNRESOLVED_ROOZANEH_MAJORS, limit=30,
            region_zone=1, special_quota="none",
        )
        self.assertEqual(result, [])

    def test_record_blank_roozaneh_resolves_unresolved_table5_and_is_excluded(self):
        self.assertEqual(
            _resolve_record_bomi(EMPTY_BOMI_ROOZANEH_RECORD, UNRESOLVED_ROOZANEH_MAJORS),
            (None, "unresolved_table5"),
        )
        result = build_record_results(
            major_ids=[999], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi",
            course_types=["roozaneh"], programs=[EMPTY_BOMI_ROOZANEH_RECORD], majors=UNRESOLVED_ROOZANEH_MAJORS, limit=30,
            region_zone=1, special_quota="none",
        )
        self.assertEqual(result, [])

    def test_record_table5_period_defaults_are_loaded_from_source(self):
        table5 = load_bomi_table5()
        self.assertEqual(len(table5["period_defaults"]), 14)
        cases = {
            "payam_noor": "nahiyei",
            "nobat_dovom": "ostani",
            "nonprofit": "nahiyei",
            "virtual": "keshvari",
            "pardis": "keshvari",
            "shabane": "ostani",
            "majazi": "keshvari",
        }
        for course_type, expected in cases.items():
            program = _program(
                program_id=f"PERIOD-{course_type}",
                major_id=1,
                method="سوابق تحصیلی",
                course_type=course_type,
                bomi_type="",
            )
            self.assertEqual(
                _resolve_record_bomi(program, MAJORS),
                (expected, "period_defaults"),
            )

    def test_record_table5_daily_bomi_uses_aliases_and_direct_names(self):
        majors = {
            "53": {"id": 53, "name": "مهندسی صنایع", "exam_group": "ریاضی"},
            "62": {"id": 62, "name": "مهندسی مواد و متالورژی", "exam_group": "ریاضی"},
            "81": {"id": 81, "name": "ریاضیات و کاربردها", "exam_group": "ریاضی"},
        }
        expected = {53: "ghotbi", 62: "ghotbi", 81: "nahiyei"}
        for major_id, bomi_type in expected.items():
            program = _program(
                program_id=f"TABLE5-{major_id}",
                major_id=major_id,
                method="سوابق تحصیلی",
                course_type="savabegh_dolati",
                bomi_type="ostani",
            )
            self.assertEqual(
                _resolve_record_bomi(program, majors),
                (bomi_type, "table5_daily"),
            )

    def test_record_table5_daily_type_is_not_taken_from_program_bomi_type(self):
        majors = {"81": {"id": 81, "name": "ریاضیات و کاربردها", "exam_group": "ریاضی"}}
        program = _program(
            program_id="TABLE5-PRECEDENCE",
            major_id=81,
            method="سوابق تحصیلی",
            course_type="savabegh_dolati",
            bomi_type="ostani",
        )
        self.assertEqual(_resolve_record_bomi(program, majors), ("nahiyei", "table5_daily"))

    def test_record_azad_without_table5_resolution_keeps_null_bomi(self):
        majors = {"999": {"id": 999, "name": "رشته بدون جدول ۵", "exam_group": "تجربی"}}
        program = _program(
            program_id="AZAD-UNRESOLVED-RECORD",
            major_id=999,
            method="سوابق تحصیلی",
            course_type="savabegh_dolati",
            bomi_type="ghotbi",
            university_name="دانشگاه آزاد اسلامی واحد نمونه",
        )
        self.assertEqual(_resolve_record_bomi(program, majors), (None, "azad_unresolved"))

    def test_record_resolver_source_rules_are_exposed_on_real_programs(self):
        programs = {
            "PROG_03158": next(item for item in load_programs() if item.get("program_id") == "PROG_03158"),
            "PROG_01000": next(item for item in load_programs() if item.get("program_id") == "PROG_01000"),
        }
        self.assertEqual(_resolve_record_bomi(programs["PROG_03158"], load_majors()), ("nahiyei", "period_defaults"))
        self.assertEqual(_resolve_record_bomi(programs["PROG_01000"], load_majors()), ("nahiyei", "table5_daily"))

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

    def test_ghotbi_locality_uses_official_geography_mapping(self):
        matching = build_exam_results(
            major_ids=[1], rank_in_quota=800, region_zone=2, special_quota="none",
            province="یزد", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[GHOTBI_PROGRAM], limit=30,
        )
        mismatching = build_exam_results(
            major_ids=[1], rank_in_quota=800, region_zone=2, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[GHOTBI_PROGRAM], limit=30,
        )
        self.assertEqual([item["program_id"] for item in matching], ["GHOTBI-1"])
        self.assertEqual(mismatching, [])
        self.assertIn("بومی قطبی", matching[0]["note"])
        self.assertIn("استان school_province_3y", matching[0]["note"])

    def test_nahiyei_locality_uses_official_geography_mapping(self):
        program = _program(
            program_id="NAHIYEI-1",
            major_id=1,
            method="با آزمون",
            course_type="roozaneh",
            province="اصفهان",
            bomi_type="nahiyei",
            predicted={"zone_2": 1000},
        )
        matching = build_exam_results(
            major_ids=[1], rank_in_quota=800, region_zone=2, special_quota="none",
            province="یزد", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[program], limit=30,
        )
        mismatching = build_exam_results(
            major_ids=[1], rank_in_quota=800, region_zone=2, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[program], limit=30,
        )
        self.assertEqual([item["program_id"] for item in matching], ["NAHIYEI-1"])
        self.assertEqual(mismatching, [])
        self.assertIn("بومی ناحیه‌ای", matching[0]["note"])

    def test_locality_missing_geography_excludes_program_instead_of_inference(self):
        program = _program(
            program_id="GHOTBI-NO-GEO",
            major_id=1,
            method="با آزمون",
            course_type="roozaneh",
            province="اصفهان",
            bomi_type="ghotbi",
            predicted={"zone_2": 1000},
        )
        with patch("admission_sanjesh_engine.load_bomi_geography", return_value={}):
            result = build_exam_results(
                major_ids=[1], rank_in_quota=800, region_zone=2, special_quota="none",
                province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
                course_types=["roozaneh"], programs=[program], limit=30,
            )
        self.assertEqual(result, [])

    def test_ostani_province_changes_exam_result_for_same_major(self):
        local = build_exam_results(
            major_ids=[1], rank_in_quota=800, region_zone=2, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[OSTANI_BOMI_PROGRAM], limit=30,
        )
        remote = build_exam_results(
            major_ids=[1], rank_in_quota=800, region_zone=2, special_quota="none",
            province="اصفهان", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[OSTANI_BOMI_PROGRAM], limit=30,
        )
        self.assertEqual(len(local), 1)
        self.assertEqual(local[0]["program_id"], "OSTANI-1")
        self.assertEqual(remote, [])

    def test_ostani_province_filter_also_applies_to_record(self):
        local = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[OSTANI_RECORD_PROGRAM], majors=MAJORS, limit=30,
        )
        remote = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="اصفهان", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[OSTANI_RECORD_PROGRAM], majors=MAJORS, limit=30,
        )
        self.assertEqual(len(local), 1)
        self.assertEqual(remote, [])

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

    def test_ghotbi_nonmatching_province_is_excluded_by_official_mapping(self):
        result = build_exam_results(
            major_ids=[1], rank_in_quota=900, region_zone=2, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[GHOTBI_PROGRAM], limit=30,
        )
        self.assertEqual(result, [])

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

    def test_g3_humanities_exception_riazi_and_tajrobi_are_100(self):
        majors = {
            "10": {"id": 10, "name": "روانشناسی", "exam_group": "انسانی"},
            "11": {"id": 11, "name": "مدیریت کسب و کار", "exam_group": "انسانی"},
        }
        self.assertEqual(
            _coefficient("riazi", "ensani", major_id=10, majors=majors),
            100.0,
        )
        self.assertEqual(
            _coefficient("tajrobi", "ensani", major_id=11, majors=majors),
            100.0,
        )

    def test_g3_humanities_exception_does_not_expand_to_unlisted_major(self):
        majors = {
            "12": {"id": 12, "name": "حقوق", "exam_group": "انسانی"},
        }
        self.assertEqual(
            _coefficient("riazi", "ensani", major_id=12, majors=majors),
            57.1,
        )

    def test_g3_base_coefficients_remain_unchanged(self):
        majors = {
            "13": {"id": 13, "name": "مهندسی کامپیوتر", "exam_group": "انسانی"},
        }
        self.assertEqual(
            _coefficient("riazi", "ensani", major_id=13, majors=majors),
            57.1,
        )
        self.assertEqual(
            _coefficient("other_fani", "ensani", major_id=13, majors=majors),
            51.4,
        )

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

    def test_record_minimum_gpa_filters_below_and_keeps_above(self):
        below = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=13.99, gpa_total=None,
            province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )
        above = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=14.01, gpa_total=None,
            province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )
        self.assertEqual(below, [])
        self.assertEqual([item["program_id"] for item in above], ["ACA-1"])

    def test_record_minimum_traz_filters_only_when_traz_is_supplied(self):
        missing = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None, traz=None,
            province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )
        below = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None, traz=5999,
            province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )
        above = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None, traz=6000,
            province="تهران", target_field_group="tajrobi", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )
        self.assertEqual([item["program_id"] for item in missing], ["ACA-1"])
        self.assertTrue(any("تراز اعلام نشده" in note for note in missing[0]["notes"]))
        self.assertEqual(below, [])
        self.assertEqual([item["program_id"] for item in above], ["ACA-1"])
        self.assertEqual(above[0]["traz_input"], 6000)

    def test_record_label_uses_only_three_qualitative_labels(self):
        below = build_record_results(
            major_ids=[1], diploma_type="ensani", gpa_written=10.0, gpa_total=None,
            province="تهران", target_field_group="ensani", course_types=["savabegh_dolati"],
            programs=[ACADEMIC_PROGRAM], majors=MAJORS, limit=30,
        )
        self.assertEqual(below, [])

        labels = set()
        for gpa in (14.0, 20.0):
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

    def test_ghotbi_nonmatching_province_has_no_implicit_pass_through(self):
        result = build_exam_results(
            major_ids=[1], rank_in_quota=900, region_zone=2, special_quota="none",
            province="تهران", diploma_type=None, gpa_written=None, national_rank=None,
            course_types=["roozaneh"], programs=[GHOTBI_PROGRAM], limit=30,
        )
        self.assertEqual(result, [])


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

    def test_api_ostani_province_changes_result_for_same_major(self):
        with patch("admission_chance_api.load_programs", return_value=(OSTANI_BOMI_PROGRAM,)):
            local = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "exam",
                    "major_ids": [1],
                    "rank_in_quota": 800,
                    "region_zone": 2,
                    "special_quota": "none",
                    "province": "تهران",
                },
            )
            remote = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "exam",
                    "major_ids": [1],
                    "rank_in_quota": 800,
                    "region_zone": 2,
                    "special_quota": "none",
                    "province": "اصفهان",
                },
            )
        self.assertEqual(local.status_code, 200, local.text)
        self.assertEqual(remote.status_code, 200, remote.text)
        self.assertEqual(local.json()["count"], 1)
        self.assertEqual(local.json()["items"][0]["program_id"], "OSTANI-1")
        self.assertEqual(remote.json()["items"], [])

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

    def test_record_request_applies_optional_traz_cutoff(self):
        with patch("admission_chance_api.load_programs", return_value=(ACADEMIC_PROGRAM,)),              patch("admission_chance_api.load_majors", return_value=MAJORS):
            below = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "record",
                    "major_ids": [1],
                    "province": "تهران",
                    "region_zone": 2,
                    "special_quota": "none",
                    "diploma_type": "tajrobi",
                    "gpa_written": 18.0,
                    "traz": 5999,
                    "target_field_group": "tajrobi",
                },
            )
            above = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "record",
                    "major_ids": [1],
                    "province": "تهران",
                    "region_zone": 2,
                    "special_quota": "none",
                    "diploma_type": "tajrobi",
                    "gpa_written": 18.0,
                    "traz": 6000,
                    "target_field_group": "tajrobi",
                },
            )
        self.assertEqual(below.status_code, 200, below.text)
        self.assertEqual(below.json()["items"], [])
        self.assertEqual(above.status_code, 200, above.text)
        self.assertEqual(above.json()["items"][0]["traz_input"], 6000)

    def test_record_special_quota_is_note_only(self):
        result = build_record_results(
            major_ids=[1], diploma_type="tajrobi", gpa_written=18.0, gpa_total=None,
            province="تهران", target_field_group="tajrobi",
            course_types=["savabegh_dolati"], programs=[ACADEMIC_PROGRAM],
            majors=MAJORS, limit=30, region_zone=2, special_quota="isargaran_25",
        )
        self.assertEqual([item["program_id"] for item in result], ["ACA-1"])
        self.assertEqual(result[0]["special_quota"], "isargaran_25")
        self.assertTrue(any("سهمیه خاص در داده سوابق" in note for note in result[0]["notes"]))
        self.assertTrue(any("فیلتر/حدنصاب سهمیه‌ای در مسیر record اعمال نشد" in note for note in result[0]["notes"]))

    def test_record_request_uses_gpa_coefficient(self):
        with patch("admission_chance_api.load_programs", return_value=(ACADEMIC_PROGRAM,)),              patch("admission_chance_api.load_majors", return_value=MAJORS):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "record",
                    "major_ids": [1],
                    "province": "تهران",
                    "region_zone": 2,
                    "special_quota": "none",
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
                    "region_zone": 2,
                    "special_quota": "none",
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
                    "region_zone": 2,
                    "special_quota": "none",
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



    def test_exam_capacity_tajrobi_medical_still_returns_rows(self):
        items = build_exam_capacity_results(
            group="tajrobi",
            major_ids=[1],
            province="تهران",
            periods=["روزانه"],
            limit=5,
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))

    def test_exam_capacity_ensani_law_still_returns_rows(self):
        items = build_exam_capacity_results(
            group="ensani",
            major_ids=[101],
            province="تهران",
            periods=["روزانه"],
            limit=5,
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))

    def test_exam_capacity_without_major_ids_returns_group_province_period_rows(self):
        response = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "exam",
                "source": "capacity",
                "group": "riazi",
                "province": "تهران",
                "periods": ["روزانه"],
                "limit": 100,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["source"], "capacity")
        self.assertEqual(payload["context"]["major_ids"], [])
        self.assertGreater(payload["count"], 0)
        self.assertTrue(all(item["sanjesh_code"] for item in payload["items"]))
        self.assertTrue(all(item["major_name"] for item in payload["items"]))
        self.assertTrue(all(item["province"] == "تهران" for item in payload["items"]))
        self.assertTrue(all(item["period"] == "روزانه" for item in payload["items"]))
        self.assertGreater(len({item["major_name"] for item in payload["items"]}), 1)

    def test_exam_capacity_empty_major_ids_do_not_expand_program_or_record_paths(self):
        program = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "exam",
                "source": "program",
                "major_ids": [],
                "rank_in_quota": 900,
                "region_zone": 2,
                "province": "تهران",
            },
        )
        record = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "record",
                "source": "program",
                "major_ids": [],
                "province": "تهران",
                "diploma_type": "tajrobi",
                "gpa_written": 18.0,
                "region_zone": 2,
            },
        )
        self.assertEqual(program.status_code, 400)
        self.assertEqual(record.status_code, 400)
        self.assertIn("major_ids", program.json()["detail"])
        self.assertIn("major_ids", record.json()["detail"])

    def test_exam_program_rank_comparison_returns_status_and_reference(self):
        with patch("admission_chance_api.load_programs", return_value=(EXAM_PROGRAM,)):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "exam",
                    "source": "program",
                    "major_ids": [1],
                    "rank_in_quota": 900,
                    "region_zone": 2,
                    "special_quota": "none",
                    "province": "تهران",
                    "course_types": ["roozaneh"],
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["source"], "program")
        self.assertGreater(payload["count"], 0)
        item = payload["items"][0]
        self.assertEqual(item["status"], "above")
        self.assertEqual(item["status_label"], "بالاتر از محدودهٔ قبولی تاریخی")
        self.assertEqual(item["cutoff_reference"]["value"], 1100)
        self.assertEqual(item["cutoff_reference"]["year"], 1404)
        self.assertEqual(item["cutoff_used"], 1100)
        self.assertEqual(item["cutoff_year"], 1404)
        self.assertEqual(item["cutoff_source"], "program2s historical cutoff data")
        self.assertIn("هیچ احتمال عددی محاسبه نمی‌شود", payload["disclaimer"])

    def test_exam_program_missing_program2s_major_returns_explicit_empty_reason(self):
        response = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "exam",
                "source": "program",
                "major_ids": [166],
                "rank_in_quota": 1000,
                "region_zone": 2,
                "special_quota": "none",
                "province": "تهران",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["empty_reason"], "no_program2s_data")
        self.assertEqual(payload["context"]["missing_program2s_major_ids"], [166])
        self.assertIn(
            "برای این رشته در دادهٔ مقایسه رتبه برنامه‌ای ثبت نشده. ظرفیت را از منبع «ظرفیت دفترچه» ببینید.",
            payload["notes"],
        )

    def test_exam_program_medical_regression_still_returns_rows(self):
        response = self.client.post(
            "/api/v1/admission/chance",
            json={
                "admission_path": "exam",
                "source": "program",
                "major_ids": [1],
                "rank_in_quota": 900,
                "region_zone": 2,
                "special_quota": "none",
                "province": "تهران",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["source"], "program")
        self.assertGreater(payload["count"], 0)
        self.assertEqual(payload["items"][0]["major_id"], 1)
        self.assertNotIn("empty_reason", payload)

    def test_exam_program_special_quota_uses_historical_special_cutoff(self):
        with patch("admission_chance_api.load_programs", return_value=(SPECIAL_HISTORICAL_PROGRAM,)):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "exam",
                    "source": "program",
                    "major_ids": [1],
                    "rank_in_quota": 210,
                    "region_zone": 2,
                    "special_quota": "isargaran_25",
                    "province": "تهران",
                    "course_types": ["nobat_dovom"],
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()["items"][0]
        self.assertEqual(item["status"], "near")
        self.assertEqual(item["cutoff_dimension"], "isargaran_25")
        self.assertEqual(item["cutoff_reference"]["value"], 200)
        self.assertEqual(item["cutoff_reference"]["year"], 1404)
        self.assertEqual(item["cutoff_source"], "program2s historical cutoff data")

    def test_exam_program_special_quota_without_historical_cutoff_returns_unknown(self):
        with patch("admission_chance_api.load_programs", return_value=(SPECIAL_FALLBACK_PROGRAM,)):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "exam",
                    "source": "program",
                    "major_ids": [1],
                    "rank_in_quota": 700,
                    "region_zone": 2,
                    "special_quota": "isargaran_25",
                    "province": "تهران",
                    "course_types": ["nobat_dovom"],
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()["items"][0]
        self.assertEqual(item["status"], "unknown")
        self.assertEqual(item["status_label"], "دادهٔ آخرین رتبه در دسترس نیست")
        self.assertIsNone(item["cutoff_used"])
        self.assertIsNone(item["cutoff_reference"])
        self.assertEqual(item["cutoff_dimension"], "isargaran_25")
        self.assertIn("برای این سهمیه دادهٔ آخرین رتبه در دسترس نیست", item["note"])
        self.assertNotIn("fallback مستند", item["note"])

    def test_exam_program_rank_missing_returns_400(self):
        with patch("admission_chance_api.load_programs", return_value=(EXAM_PROGRAM,)):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "exam",
                    "source": "program",
                    "major_ids": [1],
                    "region_zone": 2,
                    "special_quota": "none",
                    "province": "تهران",
                    "course_types": ["roozaneh"],
                },
            )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("rank_in_quota الزامی", response.json()["detail"])

    def test_exam_program_without_cutoff_returns_unknown(self):
        no_cutoff = _program(
            program_id="EXAM-UNKNOWN",
            major_id=1,
            method="با آزمون",
            course_type="roozaneh",
            predicted={},
            historical={},
        )
        with patch("admission_chance_api.load_programs", return_value=(no_cutoff,)):
            response = self.client.post(
                "/api/v1/admission/chance",
                json={
                    "admission_path": "exam",
                    "source": "program",
                    "major_ids": [1],
                    "rank_in_quota": 1000,
                    "region_zone": 2,
                    "special_quota": "none",
                    "province": "تهران",
                    "course_types": ["roozaneh"],
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()["items"][0]
        self.assertEqual(item["status"], "unknown")
        self.assertIsNone(item["cutoff_reference"])



if __name__ == "__main__":
    unittest.main(verbosity=2)
