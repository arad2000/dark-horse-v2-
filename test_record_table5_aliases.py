from __future__ import annotations

import json
import re
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALIASES = {
    "مهندسی صنایع": "مهندسی صنایع و سیستم ها",
    "مهندسی مواد و متالورژی": "مهندسی و علم مواد",
    "مهندسی مواد": "مهندسی و علم مواد",
}


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک").replace("‌", " ")
    return re.sub(r"\s+", " ", text).strip()


def _load():
    programs = json.loads((ROOT / "program2s.json").read_text(encoding="utf-8"))["programs"]
    majors = json.loads((ROOT / "majors_database_v2.json").read_text(encoding="utf-8"))
    table = json.loads((ROOT / "docs" / "sanjesh_table5_major_bomi_v1.json").read_text(encoding="utf-8"))
    return programs, majors, table


class RecordTable5AliasTests(unittest.TestCase):
    def test_alias_remap_audit_and_regressions(self):
        programs, majors, table = _load()
        id_name = {str(item["id"]): str(item["name"]) for item in majors if item.get("id") is not None}

        daily = table["daily_major_bomi"]
        lookup = {_norm(k): v for k, v in daily.items()}
        for alias, target in table["name_aliases"].items():
            if target in daily:
                lookup[_norm(alias)] = daily[target]

        before = 0
        after = 0
        changed = 0
        for program in programs:
            admission = program.get("admission_info") or {}
            if admission.get("method") != "سوابق تحصیلی":
                continue
            if admission.get("course_type") != "savabegh_dolati":
                continue

            if admission.get("bomi_type") is None:
                before += 1

            major_name = id_name.get(str(program.get("major_id")))
            mapped = lookup.get(_norm(major_name)) if major_name else None
            predicted = admission.get("bomi_type") or mapped

            if admission.get("bomi_type") is None and mapped:
                changed += 1
            if predicted is None:
                after += 1

        self.assertEqual(before, 322)
        self.assertEqual(changed, 30)
        self.assertEqual(after, 292)

        expected = {
            "PROG_03158": "nahiyei",
            "PROG_01000": "nahiyei",
            "PROG_01029": "ghotbi",
        }
        actual = {}
        for program in programs:
            if program.get("program_id") in expected:
                actual[program["program_id"]] = (program.get("admission_info") or {}).get("bomi_type")
        self.assertEqual(actual, expected)

        self.assertEqual(table["name_aliases"]["مهندسی صنایع"], "مهندسی صنایع و سیستم ها")
        self.assertEqual(table["name_aliases"]["مهندسی مواد و متالورژی"], "مهندسی و علم مواد")
        self.assertEqual(table["name_aliases"]["مهندسی مواد"], "مهندسی و علم مواد")


if __name__ == "__main__":
    unittest.main(verbosity=2)
