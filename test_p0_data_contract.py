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


if __name__ == "__main__":
    unittest.main()
