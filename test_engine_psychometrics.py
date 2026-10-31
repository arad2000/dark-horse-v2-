"""Unit test suite for DarkHorseEngineV2 P0 + P1 psychometric and isolation fixes (PR-C)."""
from __future__ import annotations

import json
import logging
import random
import unittest
from pathlib import Path

from dark_horse_engine_v2 import DarkHorseEngineV2

ROOT = Path(__file__).resolve().parent


class DarkHorseEnginePsychometricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log_records: list[logging.LogRecord] = []

        class _ListHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                cls.log_records.append(record)

        logger = logging.getLogger("darkhorse_engine_final")
        handler = _ListHandler()
        logger.addHandler(handler)
        try:
            cls.engine = DarkHorseEngineV2(
                motives_path="docs/data/micro_motives.json",
                majors_path="majors_database_v2.json",
                trait_map_path="trait_map_v3.json",
                value_poles_path="value_poles_v2.json",
                school_branches_path="school_branches_v2.json",
            )
        finally:
            logger.removeHandler(handler)

        cls.majors = json.loads((ROOT / "majors_database_v2.json").read_text(encoding="utf-8"))
        cls.motives = json.loads((ROOT / "docs/data/micro_motives.json").read_text(encoding="utf-8"))

    def test_p0_stub_isolation_at_startup_discovery_and_alternative_paths(self) -> None:
        warnings = [r.getMessage() for r in self.log_records if r.levelno >= logging.WARNING]
        self.assertEqual(warnings, [], f"Unexpected engine startup warnings: {warnings}")

        stub_majors = [m for m in self.majors if m.get("motive_driven") is False]
        stub_ids = {m["id"] for m in stub_majors}
        self.assertEqual(len(stub_ids), 28)

        for major_id, major_data in self.engine.majors_db.items():
            alts = self.engine._find_alternative_paths(major_id, top_n=3)
            if major_data.get("motive_driven") is False:
                self.assertEqual(alts, [])
            else:
                self.assertEqual(len(alts), 3)
                for alt in alts:
                    self.assertNotIn(alt["major_id"], stub_ids)

        injected_stub_codes = [
            code
            for m in stub_majors
            for code in (m.get("micro_motive_codes") or [])
        ]
        res = self.engine.discover_individuality(
            user_motives=injected_stub_codes + ["WOOD-001", "WOOD-002", "WOOD-003", "WOOD-004", "WOOD-005"],
            sjt_answers={f"sjt_{i}": "A" for i in range(1, 26)},
            conjoint_choices={f"conj_{i}": f"Q{i}A" for i in range(1, 16)},
        )
        discovered_ids = {m["major_id"] for m in res["discovered_majors"]}
        self.assertTrue(discovered_ids.isdisjoint(stub_ids))
        self.assertIn(76, discovered_ids)
        self.assertEqual(res["summary"]["total_majors_analyzed"], 230)
        self.assertEqual(res["summary"]["active_majors_analyzed"], 202)

    def test_p0_dominant_and_misaligned_traits_disjoint_across_40400_profiles(self) -> None:
        rng = random.Random(20261020)
        active_majors = [
            m for m in self.engine.majors_db.values() if m.get("motive_driven") is not False
        ]
        self.assertEqual(len(active_majors), 202)

        contradictions = 0
        for _ in range(200):
            answers = [rng.randint(0, 4) for _ in range(25)]
            for major in active_majors:
                sw = major.get("strategy_weights", [])
                dom = set(self.engine._extract_dominant_traits(answers, sw))
                mis = set(self.engine._extract_s_misaligned_traits(answers, sw))
                if dom & mis:
                    contradictions += 1
        self.assertEqual(contradictions, 0)

    def test_p0_water_and_wood_engine_discoverability_and_partial_spark_copy(self) -> None:
        res_water = self.engine.discover_individuality(
            user_motives=["WW-001", "WW-002", "WW-003", "WW-004", "WW-005"],
            sjt_answers={f"sjt_{i}": "A" for i in range(1, 26)},
            conjoint_choices={f"conj_{i}": f"Q{i}A" for i in range(1, 16)},
        )
        self.assertIn(56, {m["major_id"] for m in res_water["discovered_majors"]})

        desc = self.engine._generate_scenario_description(
            major_name="علوم و مهندسی صنایع چوب و فرآورده‌های سلولزی",
            m_evidence=[{"code": "WOOD-001", "description": "ساخت سازه‌های چوبی مهندسی"}],
            m_score=0.28,
            s_score=0.72,
            v_score=0.80,
            strategy_answers=[0] * 25,
            strategy_weights=[[1.0, 0.2, 0.2, 0.2, 0.2]] * 25,
            value_choices=[f"Q{i}A" for i in range(1, 16)],
            value_weights={f"Q{i}{l}": (0.9 if l == "A" else 0.2) for i in range(1, 16) for l in ("A", "B")},
        )
        self.assertIn("همپوشانی خرده‌انگیزه‌های شما با این رشته نسبی است", desc)
        self.assertNotIn("همخوانی مستقیمی با این رشته ندارد", desc)

    def test_p1_pairwise_v_score_eliminates_group_ceiling_bias(self) -> None:
        active_majors = [
            m for m in self.engine.majors_db.values() if m.get("motive_driven") is not False
        ]
        for major in active_majors:
            vw = major.get("value_weights", {})
            optimal_choices = [
                (f"Q{i}A" if vw.get(f"Q{i}A", 0.0) >= vw.get(f"Q{i}B", 0.0) else f"Q{i}B")
                for i in range(1, 16)
            ]
            v_score, _ = self.engine._compute_v_score(optimal_choices, vw)
            self.assertAlmostEqual(
                v_score,
                1.0,
                places=6,
                msg=f"Major {major['id']} ({major['name']}) failed to reach 1.0 V-Score ceiling",
            )

    def test_p1_branch_m_fixed_30_contract_with_real_reference_codes(self) -> None:
        # Use the actual branch reference data and active micro-motive catalog.
        branches = self.engine.school_branches
        self.assertEqual(len(branches), 4)
        self.assertEqual(
            [branch.get("m_score_denom_limit") for branch in branches.values()],
            [30, 30, 30, 30],
        )

        fani = self.engine._active_branch_code_set(
            branches["فنی و حرفه‌ای"]["micro_motive_codes"]
        )
        riazi = self.engine._active_branch_code_set(
            branches["ریاضی فیزیک"]["micro_motive_codes"]
        )
        other_branch_codes = set().union(*[
            self.engine._active_branch_code_set(branch["micro_motive_codes"])
            for name, branch in branches.items()
            if name not in {"فنی و حرفه‌ای", "ریاضی فیزیک"}
        ])

        five_fani = sorted(fani)[:5]
        five_riazi = sorted(riazi)[:5]
        padding = sorted(other_branch_codes)
        self.assertEqual(len(five_fani), 5)
        self.assertEqual(len(five_riazi), 5)
        self.assertGreaterEqual(len(padding), 70)

        # Five shared sparks in each branch must score equally at profile sizes 20, 30 and 80.
        for profile_length in (20, 30, 80):
            profile = five_fani + five_riazi + padding[:profile_length - 10]
            fani_score, _ = self.engine._compute_branch_m_score(
                profile, branches["فنی و حرفه‌ای"]
            )
            riazi_score, _ = self.engine._compute_branch_m_score(
                profile, branches["ریاضی فیزیک"]
            )
            self.assertAlmostEqual(fani_score, 5 / 30, places=12)
            self.assertAlmostEqual(riazi_score, 5 / 30, places=12)
            self.assertAlmostEqual(fani_score, riazi_score, places=12)

        # Twenty and thirty sparks with the same five Fani matches remain 5/30.
        profile_20 = five_fani + five_riazi + padding[:10]
        profile_30 = five_fani + five_riazi + padding[:20]
        score_20, _ = self.engine._compute_branch_m_score(
            profile_20, branches["فنی و حرفه‌ای"]
        )
        score_30, _ = self.engine._compute_branch_m_score(
            profile_30, branches["فنی و حرفه‌ای"]
        )
        self.assertAlmostEqual(score_20, 5 / 30, places=12)
        self.assertAlmostEqual(score_30, 5 / 30, places=12)
        self.assertAlmostEqual(score_20, score_30, places=12)

        # Three shared sparks in a 20-spark profile stay below the 15% eligibility threshold.
        profile_three_matches = five_fani[:3] + five_riazi + padding[:12]
        score_three, _ = self.engine._compute_branch_m_score(
            profile_three_matches, branches["فنی و حرفه‌ای"]
        )
        self.assertAlmostEqual(score_three, 3 / 30, places=12)
        self.assertLess(score_three, 0.15)

        # Adding one more spark from another branch cannot reduce Fani M.
        score_before, _ = self.engine._compute_branch_m_score(
            profile_20, branches["فنی و حرفه‌ای"]
        )
        score_after, _ = self.engine._compute_branch_m_score(
            profile_20 + [padding[10]], branches["فنی و حرفه‌ای"]
        )
        self.assertAlmostEqual(score_before, 5 / 30, places=12)
        self.assertAlmostEqual(score_after, score_before, places=12)

    def test_engine_startup_rejects_non_30_branch_denominator(self) -> None:
        # Derive a negative startup case from the real reference file; no mocks are used.
        from tempfile import TemporaryDirectory

        raw_branches = json.loads(
            (ROOT / "school_branches_v2.json").read_text(encoding="utf-8")
        )
        raw_branches[0]["m_score_denom_limit"] = 29

        with TemporaryDirectory() as temp_dir:
            invalid_branches_path = Path(temp_dir) / "school_branches_v2.json"
            invalid_branches_path.write_text(
                json.dumps(raw_branches, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "m_score_denom_limit=30"):
                DarkHorseEngineV2(
                    motives_path="docs/data/micro_motives.json",
                    majors_path="majors_database_v2.json",
                    trait_map_path="trait_map_v3.json",
                    value_poles_path="value_poles_v2.json",
                    school_branches_path=str(invalid_branches_path),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
