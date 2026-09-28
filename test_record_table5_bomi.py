from __future__ import annotations

import json
import unittest
from pathlib import Path

from admission_sanjesh_engine import build_record_results, load_majors, load_programs


ROOT = Path(__file__).resolve().parent


class RecordTable5BomiTests(unittest.TestCase):
    def test_savabegh_dolati_counts_and_rules(self):
        programs = list(load_programs())
        rows = [
            p for p in programs
            if (p.get("admission_info") or {}).get("method") == "سوابق تحصیلی"
            and (p.get("admission_info") or {}).get("course_type") == "savabegh_dolati"
        ]
        counts = {"ostani": 0, "nahiyei": 0, "ghotbi": 0, "keshvari": 0, "null": 0}
        for row in rows:
            value = (row.get("admission_info") or {}).get("bomi_type")
            counts[value if value in counts else "null"] += 1
        self.assertEqual(len(rows), 580)
        self.assertEqual(
            counts,
            {"ostani": 0, "nahiyei": 78, "ghotbi": 108, "keshvari": 102, "null": 292},
        )

        unresolved = [
            p for p in rows
            if (p.get("admission_info") or {}).get("bomi_type") is None
        ]
        self.assertEqual(len(unresolved), 292)
        self.assertTrue(
            all(
                (p.get("admission_info") or {}).get("bomi_type_rule")
                == "unresolved_table5"
                for p in unresolved
            )
        )

    def test_table5_samples(self):
        programs = {p["program_id"]: p for p in load_programs()}
        self.assertEqual(programs["PROG_01000"]["admission_info"]["bomi_type"], "nahiyei")
        self.assertEqual(programs["PROG_01000"]["admission_info"]["bomi_type_rule"], "table5.daily_major_bomi")
        self.assertEqual(programs["PROG_01029"]["admission_info"]["bomi_type"], "ghotbi")
        self.assertEqual(programs["PROG_00992"]["admission_info"]["bomi_type"], "ghotbi")
        self.assertEqual(programs["PROG_00998"]["admission_info"]["bomi_type"], "ghotbi")
        self.assertEqual(programs["PROG_00985"]["admission_info"]["bomi_type"], None)
        self.assertEqual(programs["PROG_00985"]["admission_info"]["bomi_type_rule"], "unresolved_table5")

    def test_regression_payam_noor_and_table5_province_filter(self):
        programs = {p["program_id"]: p for p in load_programs()}
        majors = load_majors()

        local_payam = build_record_results(
            major_ids=[41],
            diploma_type="riazi",
            gpa_written=18.0,
            gpa_total=None,
            province="تهران",
            target_field_group="riazi",
            course_types=["payam_noor"],
            programs=[programs["PROG_03158"]],
            majors=majors,
            limit=30,
        )
        remote_payam = build_record_results(
            major_ids=[41],
            diploma_type="riazi",
            gpa_written=18.0,
            gpa_total=None,
            province="کرمان",
            target_field_group="riazi",
            course_types=["payam_noor"],
            programs=[programs["PROG_03158"]],
            majors=majors,
            limit=30,
        )
        self.assertEqual([x["program_id"] for x in local_payam], ["PROG_03158"])
        self.assertEqual(remote_payam, [])

        local_table5 = build_record_results(
            major_ids=[81],
            diploma_type="tajrobi",
            gpa_written=18.0,
            gpa_total=None,
            province="گیلان",
            target_field_group="tajrobi",
            course_types=["savabegh_dolati"],
            programs=[programs["PROG_01000"]],
            majors=majors,
            limit=30,
        )
        remote_table5 = build_record_results(
            major_ids=[81],
            diploma_type="tajrobi",
            gpa_written=18.0,
            gpa_total=None,
            province="تهران",
            target_field_group="tajrobi",
            course_types=["savabegh_dolati"],
            programs=[programs["PROG_01000"]],
            majors=majors,
            limit=30,
        )
        self.assertEqual([x["program_id"] for x in local_table5], ["PROG_01000"])
        self.assertEqual(remote_table5, [])

    def test_table5_ghotbi_same_and_other_pole(self):
        programs = {p["program_id"]: p for p in load_programs()}
        majors = load_majors()

        same = build_record_results(
            major_ids=[102],
            diploma_type="ensani",
            gpa_written=18.0,
            gpa_total=None,
            province="گیلان",
            target_field_group="ensani",
            course_types=["savabegh_dolati"],
            programs=[programs["PROG_01029"]],
            majors=majors,
            limit=30,
        )
        other = build_record_results(
            major_ids=[102],
            diploma_type="ensani",
            gpa_written=18.0,
            gpa_total=None,
            province="کرمانشاه",
            target_field_group="ensani",
            course_types=["savabegh_dolati"],
            programs=[programs["PROG_01029"]],
            majors=majors,
            limit=30,
        )
        self.assertEqual([x["program_id"] for x in same], ["PROG_01029"])
        self.assertEqual(other, [])

    def test_null_table5_mapping_has_runtime_note(self):
        programs = {p["program_id"]: p for p in load_programs()}
        majors = load_majors()
        result = build_record_results(
            major_ids=[44],
            diploma_type="riazi",
            gpa_written=18.0,
            gpa_total=None,
            province="گیلان",
            target_field_group="riazi",
            course_types=["savabegh_dolati"],
            programs=[programs["PROG_00985"]],
            majors=majors,
            limit=30,
        )
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["bomi_type"])
        self.assertTrue(
            any("نوع بومی: نامشخص" in note for note in result[0]["notes"])
        )

    def test_null_table5_mapping_is_explicitly_unresolved_in_data(self):
        programs = {p["program_id"]: p for p in load_programs()}
        row = programs["PROG_00985"]
        self.assertIsNone(row["admission_info"]["bomi_type"])
        self.assertEqual(row["admission_info"]["bomi_type_rule"], "unresolved_table5")


if __name__ == "__main__":
    unittest.main(verbosity=2)
