"""Offline integrity tests for the BIOTM medical-biotechnology correction.

No PostgreSQL. No runtime cutover. JSON remains the source of truth.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIOTM = [f"BIOTM-{i:03d}" for i in range(1, 8)]
BIOT = [f"BIOT-{i:03d}" for i in range(1, 8)]


def load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def rows(payload, keys):
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    raise AssertionError(f"unsupported collection in keys={keys}")


class BiotmReferenceIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.motives_docs = rows(load(ROOT / "docs/data/micro_motives.json"), ("micro_motives", "motives", "data"))
        cls.motives_root = rows(load(ROOT / "micro_motives.json"), ("micro_motives", "motives", "data"))
        cls.majors = rows(load(ROOT / "majors_database_v2.json"), ("majors", "data"))
        cls.branches = rows(load(ROOT / "school_branches_v2.json"), ("school_branches", "branches", "data"))

    def test_root_and_docs_motive_catalogs_match(self):
        self.assertEqual(
            [(m.get("code"), m.get("description_fa")) for m in self.motives_docs],
            [(m.get("code"), m.get("description_fa")) for m in self.motives_root],
        )

    def test_catalog_has_exactly_seven_biotm_codes(self):
        codes = [str(m.get("code") or "") for m in self.motives_docs]
        self.assertEqual([c for c in codes if c.startswith("BIOTM-")], BIOTM)
        self.assertEqual(len(self.motives_docs), 1106)

    def test_medical_biotech_uses_biotm_not_biot(self):
        medical = next(m for m in self.majors if m.get("id") == 34)
        basic = next(m for m in self.majors if m.get("id") == 93)
        self.assertEqual(medical.get("name"), "بیوتکنولوژی (پزشکی)")
        self.assertEqual(basic.get("name"), "بیوتکنولوژی (علوم پایه)")
        self.assertEqual(medical.get("micro_motive_codes"), BIOTM)
        self.assertEqual(basic.get("micro_motive_codes"), BIOT)
        self.assertNotEqual(set(BIOTM), set(BIOT))

    def test_every_major_and_branch_reference_resolves(self):
        known = {str(m.get("code") or "") for m in self.motives_docs}
        missing = []
        for item in self.majors:
            for code in item.get("micro_motive_codes") or []:
                if str(code) not in known:
                    missing.append(f"major:{item.get('id')}:{code}")
        for item in self.branches:
            for code in item.get("micro_motive_codes") or []:
                if str(code) not in known:
                    missing.append(f"branch:{item.get('name')}:{code}")
        self.assertEqual(missing, [])

    def test_experimental_branch_includes_resolved_biotm(self):
        experimental = next(b for b in self.branches if b.get("name") == "علوم تجربی")
        codes = experimental.get("micro_motive_codes") or []
        self.assertTrue(set(BIOTM).issubset(set(codes)))

    def test_biotm_texts_are_medical_not_copies_of_basic_biot(self):
        by_code = {m["code"]: m["description_fa"] for m in self.motives_docs}
        biot_texts = {by_code[c] for c in BIOT}
        for code in BIOTM:
            text = by_code[code].strip()
            self.assertTrue(text)
            self.assertNotIn(text, biot_texts)

    def test_runtime_cutover_remains_off(self):
        from migration_control import POSTGRES_RUNTIME_CUTOVER_APPROVED, is_postgres_runtime_enabled
        self.assertIs(POSTGRES_RUNTIME_CUTOVER_APPROVED, False)
        self.assertIs(is_postgres_runtime_enabled(), False)


if __name__ == "__main__":
    unittest.main()
