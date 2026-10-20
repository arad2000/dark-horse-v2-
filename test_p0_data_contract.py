"""P0.2 contracts between narrow-path prefixes, motives, and majors."""
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_JS = ROOT / "docs" / "data.js"
MOTIVES_JSON = ROOT / "docs" / "data" / "micro_motives.json"
MAJORS_JSON = ROOT / "majors_database_v2.json"


def load_contract_data():
    data_source = DATA_JS.read_text(encoding="utf-8")
    marker = "const NARROW_PATHS = {"
    marker_at = data_source.find(marker)
    if marker_at < 0:
        raise AssertionError(f"{DATA_JS.relative_to(ROOT)} has no NARROW_PATHS declaration")
    narrow_source = data_source[marker_at:]

    prefix_arrays = re.findall(
        r"\bmajorCodes\s*:\s*\[([^\]]*)\]", narrow_source, flags=re.DOTALL
    )
    prefixes = [
        code
        for raw_array in prefix_arrays
        for code in re.findall(r"""['"]([^'"]+)['"]""", raw_array)
    ]
    motives = json.loads(MOTIVES_JSON.read_text(encoding="utf-8"))
    majors = json.loads(MAJORS_JSON.read_text(encoding="utf-8"))
    motive_codes = {item.get("code") for item in motives if item.get("code")}
    return prefixes, motive_codes, majors


class MotiveCodeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prefixes, cls.motive_codes, cls.majors = load_contract_data()

    def test_every_narrow_path_major_code_prefix_exists_in_micro_motives(self):
        self.assertTrue(self.prefixes, "No majorCodes prefixes were parsed from NARROW_PATHS")
        unmatched = sorted({
            prefix for prefix in self.prefixes
            if not any(code.startswith(prefix) for code in self.motive_codes)
        })
        self.assertEqual(
            unmatched,
            [],
            "NARROW_PATHS majorCodes prefixes without any micro_motives code",
        )

    def test_each_motive_driven_major_has_existing_motive_codes(self):
        motive_driven = [major for major in self.majors if major.get("motive_driven") is True]
        self.assertTrue(motive_driven, "No motive_driven majors were found in the database")

        missing_lists = [
            f"{major.get('id')}:{major.get('name')}"
            for major in motive_driven
            if not isinstance(major.get("micro_motive_codes"), list)
            or not major.get("micro_motive_codes")
        ]
        self.assertEqual(
            missing_lists,
            [],
            "motive_driven majors must have at least one micro_motive_codes entry",
        )

        missing_codes = [
            f"{major.get('id')}:{major.get('name')} -> {code}"
            for major in motive_driven
            for code in major.get("micro_motive_codes", [])
            if code not in self.motive_codes
        ]
        self.assertEqual(
            missing_codes,
            [],
            "motive_driven majors reference codes absent from micro_motives JSON",
        )

    def test_every_motive_driven_major_is_reachable_from_narrow_paths_and_sub_realms(self):
        data_source = DATA_JS.read_text(encoding="utf-8")
        sub_at = data_source.find("const SUB_REALMS = {")
        narrow_at = data_source.find("const NARROW_PATHS = {")
        self.assertGreaterEqual(sub_at, 0)
        self.assertGreater(narrow_at, sub_at)

        sub_section = data_source[sub_at:narrow_at]
        sub_prefixes = {
            code
            for raw_array in re.findall(r"\bmajorCodes\s*:\s*\[([^\]]*)\]", sub_section, flags=re.DOTALL)
            for code in re.findall(r"""['"]([^'"]+)['"]""", raw_array)
        }
        narrow_prefixes = set(self.prefixes)

        motive_driven = [major for major in self.majors if major.get("motive_driven") is True]
        self.assertEqual(len(motive_driven), 202)

        unreachable_sub = [
            f"{major.get('id')}:{major.get('name')}"
            for major in motive_driven
            if not any(
                any(code.startswith(prefix) for prefix in sub_prefixes)
                for code in major.get("micro_motive_codes", [])
            )
        ]
        unreachable_narrow = [
            f"{major.get('id')}:{major.get('name')}"
            for major in motive_driven
            if not any(
                any(code.startswith(prefix) for prefix in narrow_prefixes)
                for code in major.get("micro_motive_codes", [])
            )
        ]
        self.assertEqual(unreachable_sub, [], "Active majors missing from SUB_REALMS")
        self.assertEqual(unreachable_narrow, [], "Active majors missing from NARROW_PATHS")


if __name__ == "__main__":
    unittest.main()
