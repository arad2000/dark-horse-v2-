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

    def test_p1_school_branch_m_score_option_2a_neutralizes_pool_scale_bias(self) -> None:
        sjt = {f"sjt_{i}": "C" for i in range(1, 26)}
        conj = {f"conj_{i}": f"Q{i}{'A' if i % 2 == 1 else 'B'}" for i in range(1, 16)}

        # 1) Profile A (10 pure Riazi) vs Profile B (10 pure Fani): |m_fani - m_riazi| < 1% (~0%)
        prof_a = [
            "AERO-001", "AERO-002", "AERO-003", "AERO-005", "AERO-006",
            "AERO-007", "AERO-008", "AGM-001", "AGM-002", "AGM-003",
        ]
        prof_b = [
            "ARCHA-001", "ARCHA-002", "ARCHA-003", "ARCHA-004", "ARCHA-005",
            "ARCHA-006", "ARCHA-007", "FAS-001", "FAS-002", "FAS-003",
        ]
        res_a = {b["branch_name"]: b for b in self.engine.recommend_school_branch(prof_a, sjt, conj)["recommended_branches"]}
        res_b = {b["branch_name"]: b for b in self.engine.recommend_school_branch(prof_b, sjt, conj)["recommended_branches"]}
        m_riazi = res_a["ریاضی فیزیک"]["avg_components"]["m_score"]
        m_fani = res_b["فنی و حرفه‌ای"]["avg_components"]["m_score"]
        self.assertLess(abs(m_fani - m_riazi), 1.0)
        self.assertEqual(m_riazi, m_fani)

        # 2) Profile C1 (5 Riazi + 5 Fani): both branches M >= 15% and Total >= 30%
        prof_c1 = prof_a[:5] + prof_b[:5]
        res_c1 = {b["branch_name"]: b for b in self.engine.recommend_school_branch(prof_c1, sjt, conj)["recommended_branches"]}
        self.assertGreaterEqual(res_c1["ریاضی فیزیک"]["avg_components"]["m_score"], 15.0)
        self.assertGreaterEqual(res_c1["فنی و حرفه‌ای"]["avg_components"]["m_score"], 15.0)
        self.assertEqual(
            res_c1["ریاضی فیزیک"]["avg_components"]["m_score"],
            res_c1["فنی و حرفه‌ای"]["avg_components"]["m_score"],
        )

        # 3) Profile C2 (3+3+3+3 across all 4 branches): non-empty UI and all 4 branches M >= 15%
        prof_c2 = [
            "ANB-001", "ANB-002", "ANB-003",
            "AERO-001", "AERO-002", "AERO-003",
            "ACC-001", "ACC-002", "ACC-003",
            "ARCHA-001", "ARCHA-002", "ARCHA-003",
        ]
        out_c2 = self.engine.recommend_school_branch(prof_c2, sjt, conj)
        visible_c2 = [
            b for b in out_c2["recommended_branches"]
            if b["average_score"] >= 30.0 and b["avg_components"]["m_score"] >= 15.0
        ]
        self.assertEqual(len(visible_c2), 4)
        self.assertIsNotNone(out_c2["best_branch"])

        # 4) Regression guard: 100 fixed-seed profiles have 0 major-score / order diff vs legacy pool_scale
        def _legacy_pool_scale_branch_m_score(user_motives, branch_data):
            if not user_motives:
                return 0.0, []
            raw_codes = branch_data.get("micro_motive_codes", [])
            if not raw_codes:
                return 0.0, []
            user_set = {str(m).strip().lower() for m in user_motives if m and str(m).strip()}
            branch_set = self.engine._active_branch_code_set(raw_codes)
            matched = user_set & branch_set
            if not matched:
                return 0.0, []
            denom_limit = branch_data.get("m_score_denom_limit", 30)
            pool_sizes = [
                len(self.engine._active_branch_code_set(b.get("micro_motive_codes", [])))
                for b in self.engine.school_branches.values()
                if b.get("micro_motive_codes")
            ]
            mean_pool = (sum(pool_sizes) / len(pool_sizes)) if len(pool_sizes) > 1 else float(len(branch_set))
            pool_scale = (len(branch_set) / mean_pool) if mean_pool > 0 else 1.0
            denom = min(float(len(branch_set)), max(1.0, float(denom_limit) * pool_scale))
            return min(1.0, len(matched) / denom), []

        active_majors = [
            m for m in self.majors if m.get("motive_driven") is not False and m.get("micro_motive_codes")
        ]
        rng = random.Random(20261023)
        orig_fn = self.engine._compute_branch_m_score
        try:
            for _ in range(100):
                chosen = rng.sample(active_majors, k=4)
                motives_in = [c for mj in chosen for c in mj["micro_motive_codes"][:4]]
                sjt_in = {f"sjt_{i}": rng.choice("ABCDE") for i in range(1, 26)}
                conj_in = {f"conj_{i}": f"Q{i}{rng.choice('AB')}" for i in range(1, 16)}

                after_res = self.engine.discover_individuality(motives_in, sjt_in, conj_in)
                self.engine._compute_branch_m_score = _legacy_pool_scale_branch_m_score
                before_res = self.engine.discover_individuality(motives_in, sjt_in, conj_in)
                self.engine._compute_branch_m_score = orig_fn

                self.assertEqual(
                    [(m["major_id"], m["individuality_fit"]["score"]) for m in before_res["discovered_majors"]],
                    [(m["major_id"], m["individuality_fit"]["score"]) for m in after_res["discovered_majors"]],
                )
        finally:
            self.engine._compute_branch_m_score = orig_fn


if __name__ == "__main__":
    unittest.main(verbosity=2)
