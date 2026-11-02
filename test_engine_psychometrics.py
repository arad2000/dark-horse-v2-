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

    def test_p1_branch_m_valid_selection_share_with_real_reference_codes(self) -> None:
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

        # Equal overlaps have equal shares at every required profile size.
        for profile_length in (20, 25, 29, 30, 31, 40, 80):
            profile = five_fani + five_riazi + padding[:profile_length - 10]
            fani_score, _ = self.engine._compute_branch_m_score(
                profile, branches["فنی و حرفه‌ای"]
            )
            riazi_score, _ = self.engine._compute_branch_m_score(
                profile, branches["ریاضی فیزیک"]
            )
            self.assertAlmostEqual(fani_score, 5 / profile_length, places=12)
            self.assertAlmostEqual(riazi_score, 5 / profile_length, places=12)
            self.assertAlmostEqual(fani_score, riazi_score, places=12)

        # Fixed overlap represents a smaller share as valid nonmatching selections grow.
        profile_20 = five_fani + five_riazi + padding[:10]
        profile_30 = five_fani + five_riazi + padding[:20]
        score_20, _ = self.engine._compute_branch_m_score(
            profile_20, branches["فنی و حرفه‌ای"]
        )
        score_30, _ = self.engine._compute_branch_m_score(
            profile_30, branches["فنی و حرفه‌ای"]
        )
        self.assertAlmostEqual(score_20, 5 / 20, places=12)
        self.assertAlmostEqual(score_30, 5 / 30, places=12)
        self.assertGreater(score_20, score_30)

        # Three shared sparks in a 20-spark profile reach the unchanged 15% gate.
        profile_three_matches = five_fani[:3] + five_riazi + padding[:12]
        score_three, _ = self.engine._compute_branch_m_score(
            profile_three_matches, branches["فنی و حرفه‌ای"]
        )
        self.assertAlmostEqual(score_three, 3 / 20, places=12)
        self.assertEqual(score_three, 0.15)

        # Adding a valid nonmatching spark reduces share; unknown codes do not.
        score_before, _ = self.engine._compute_branch_m_score(
            profile_20, branches["فنی و حرفه‌ای"]
        )
        score_after, _ = self.engine._compute_branch_m_score(
            profile_20 + [padding[10]], branches["فنی و حرفه‌ای"]
        )
        self.assertAlmostEqual(score_before, 5 / 20, places=12)
        self.assertAlmostEqual(score_after, 5 / 21, places=12)

    def _wave_b_codes(self):
        branch = next(iter(self.engine.school_branches.values()))
        catalog = {code.lower() for code in self.engine.motives_map}
        own = self.engine._active_branch_code_set(branch["micro_motive_codes"]) & catalog
        return branch, sorted(own), sorted(catalog - own)

    def test_wave_b_normalizes_valid_unique_inputs_and_evidence(self):
        branch, own, other = self._wave_b_codes()
        clean = own[:5] + other[:15]
        noisy = clean + [own[0].upper(), " " + own[0] + " ", "unknown-wave-b", "", " ", None, False, 123]
        score, evidence = self.engine._compute_branch_m_score(noisy, branch)
        self.assertAlmostEqual(score, 5 / 20, places=12)
        self.assertEqual(len(evidence), 5)
        self.assertEqual(len({row["code"].lower() for row in evidence}), 5)
        for row in evidence:
            self.assertEqual(row["description"], self.engine.motives_map[row["code"]])
        for empty in ([], ["unknown-wave-b", " ", None, True, 7]):
            self.assertEqual(self.engine._compute_branch_m_score(empty, branch), (0.0, []))
        self.assertEqual(self.engine._compute_branch_m_score(clean, {"micro_motive_codes": ["unknown-wave-b"]}), (0.0, []))

    def test_wave_b_nested_growth_and_no_30_cap_or_15_floor(self):
        branch, own, other = self._wave_b_codes()
        previous = None
        for n in (20, 25, 29, 30, 31, 40, 80):
            with self.subTest(N=n):
                profile = own[:5] + other[:n - 5]
                score, _ = self.engine._compute_branch_m_score(profile, branch)
                self.assertAlmostEqual(score, 5 / n, places=12)
                if previous is not None:
                    self.assertLess(score, previous)
                previous = score
                extended, _ = self.engine._compute_branch_m_score(profile + [own[5]], branch)
                self.assertAlmostEqual(extended, 6 / (n + 1), places=12)
                self.assertGreater(extended, score)
                # Distinguish from both actual fixed-30 base and older capped formula.
                if n <= 30:
                    self.assertAlmostEqual(score, 5 / min(30, max(15, n)), places=12)
                else:
                    self.assertLess(score, 5 / 30)
        self.assertAlmostEqual(self.engine._compute_branch_m_score(own[:5] + other[:5], branch)[0], 0.5)
        self.assertAlmostEqual(self.engine._compute_branch_m_score(own[:40] + other[:40], branch)[0], 0.5)
        self.assertAlmostEqual(self.engine._compute_branch_m_score(own[:80], branch)[0], 1.0)

    def test_wave_b_15_percent_gate_and_real_best_branch_contract(self):
        import math
        branch, own, other = self._wave_b_codes()
        sjt = {f"sjt_{i}": "A" for i in range(1, 26)}
        values = {f"conj_{i}": f"Q{i}A" for i in range(1, 16)}
        for n in (20, 25, 29, 30, 31, 40, 80):
            minimum = math.ceil(0.15 * n)
            for k in (minimum - 1, minimum):
                with self.subTest(N=n, k=k):
                    profile = own[:k] + other[:n - k]
                    score, _ = self.engine._compute_branch_m_score(profile, branch)
                    self.assertEqual(score >= 0.15, k == minimum)
                    result = self.engine.recommend_school_branch(profile, sjt, values)
                    ranked = result["recommended_branches"]
                    self.assertEqual(len(ranked), 4)
                    expected = next((row["branch_name"] for row in ranked
                                     if row["avg_components"]["m_score"] >= 15), None)
                    self.assertEqual(result["best_branch"], expected)
                    target = next(row for row in ranked if row["branch_name"] == branch["name"])
                    self.assertEqual(target["avg_components"]["m_score"], round(score * 100, 1))
                    self.assertEqual("warning" in target, k < minimum)
                    if k < minimum:
                        self.assertNotEqual(result["best_branch"], branch["name"])

    def test_wave_b_disjoint_pools_partition_catalog_and_sum_k_equals_n(self):
        from itertools import combinations

        catalog = {code.strip().lower() for code in self.engine.motives_map}
        branches = list(self.engine.school_branches.values())
        pools = [self.engine._active_branch_code_set(row["micro_motive_codes"])
                 for row in branches]
        self.assertEqual(set.union(*pools), catalog)
        for left, right in combinations(pools, 2):
            self.assertFalse(left & right, "Branch pools must remain disjoint")
        # Partition + coverage prove the identity for every valid subset;
        # also exercise real scoring/evidence at the requested sizes and full catalog.
        rng = random.Random(20261101)
        for n in (0, 1, 20, 25, 29, 30, 31, 40, 80, len(catalog)):
            with self.subTest(N=n):
                profile = rng.sample(sorted(catalog), n)
                k = [len(set(profile) & pool) for pool in pools]
                self.assertEqual(sum(k), n)
                scores = [self.engine._compute_branch_m_score(profile, row)
                          for row in branches]
                self.assertEqual([len(evidence) for _, evidence in scores], k)
                self.assertAlmostEqual(sum(score for score, _ in scores),
                                       1.0 if n else 0.0, places=12)

    def test_wave_b_does_not_change_seven_motive_major_m(self):
        major = next(row for row in self.engine.majors_db.values()
                     if row.get("motive_driven") is True
                     and isinstance(row.get("micro_motive_codes"), list)
                     and len(row["micro_motive_codes"]) == 7)
        codes = major["micro_motive_codes"]
        self.assertAlmostEqual(self.engine._compute_m_score(codes[:3], major)[0], 3 / 7, places=12)
        self.assertEqual(self.engine._compute_m_score(codes, major)[0], 1.0)

    def test_wave_b_equal_counts_are_equal_without_pool_size_bias(self):
        branches = list(self.engine.school_branches.values())
        for n in (20, 40, 80):
            each = n // 4
            profile = [code for branch in branches
                       for code in sorted(self.engine._active_branch_code_set(branch["micro_motive_codes"]))[:each]]
            for branch in branches:
                self.assertAlmostEqual(self.engine._compute_branch_m_score(profile, branch)[0], 0.25, places=12)

    def test_s_equal_real_catalog_preserves_untied_rows_and_orders_ties(self):
        rows = [row for destination in list(self.engine.majors_db.values()) + list(self.engine.school_branches.values())
                if destination.get("motive_driven") is not False
                for row in destination["strategy_weights"]]
        for row in rows:
            scores = [self.engine._s_item_score(row, i) for i in range(5)]
            if len(set(row)) == 1:
                self.assertEqual(scores, [None] * 5)
                continue
            self.assertTrue(all(0 <= score <= 1 for score in scores))
            for i in range(5):
                for j in range(5):
                    if row[i] == row[j]:
                        self.assertEqual(scores[i], scores[j])
                    if row[i] < row[j]:
                        self.assertLess(scores[i], scores[j])
            if len(set(row)) == 5:
                self.assertEqual(scores, [value / max(row) for value in row])
            if row.count(max(row)) > 1:
                self.assertLess(max(scores), 1)
            else:
                self.assertEqual(max(scores), 1)

    def test_s_equal_midrank_and_monotonicity(self):
        from itertools import permutations
        score = self.engine._s_item_score
        for row in ([.1, .2, .3, 1, 1], [.1, .2, 1, 1, 1], [.1, .1, .3, .5, 1]):
            actual = [score(row, i) for i in range(5)]
            self.assertEqual(actual, sorted(actual))
            for permuted in set(permutations(row)):
                self.assertEqual([score(permuted, i) for i in range(5)],
                                 [actual[row.index(value)] for value in permuted])
        self.assertEqual(score([.1, .2, .3, 1, 1], 4), .875)
        self.assertEqual(score([.1, .2, 1, 1, 1], 4), .75)
        self.assertEqual(score([.1, .1, .3, .5, 1], 4), 1)
        for i in range(5):
            self.assertAlmostEqual(score([.1, .2, .3, .4, .5], i), (i + 1) / 5)

    def test_s_equal_flat_rows_have_no_score_or_traits(self):
        for value in (.4, 1, 0):
            weights = [[value] * 5 for _ in range(25)]
            self.assertEqual(self.engine._compute_s_score([0] * 25, weights), (None, []))
            result = self.engine._compute_s_result([0] * 25, weights)
            self.assertIsNone(result["score"])
            self.assertEqual(result["status"], "equal_no_evidence")
            self.assertEqual(result["coverage"], {"answered": 25, "total": 25,
                                                "informative_answered": 0, "equal_answered": 25})
            self.assertEqual(result["highlights"], [])
            self.assertEqual(self.engine._extract_dominant_traits([0] * 25, weights), [])
            self.assertEqual(self.engine._extract_s_misaligned_traits([0] * 25, weights), [])

    def test_s_equal_aggregation_excludes_only_flat_not_missing_responses(self):
        weights = [[.5] * 5 for _ in range(24)] + [[.1, .2, .3, 1, 1]]
        result = self.engine._compute_s_result([4] * 25, weights)
        self.assertEqual(result["score"], .875)
        self.assertEqual(result["coverage"]["informative_answered"], 1)
        self.assertEqual(len(result["highlights"]), 1)
        self.assertIsNone(self.engine._compute_s_score_for_complete_profile([4] * 24, weights)[0])
        self.assertIsNone(self.engine._compute_s_score([4] * 24, weights)[0])
        tied = [[.1, .2, .3, 1, 1]] * 25
        self.assertAlmostEqual(self.engine._compute_s_score([4] * 25, tied)[0], .875)
        dominant = set(self.engine._extract_dominant_traits([4] * 25, tied))
        misaligned = set(self.engine._extract_s_misaligned_traits([4] * 25, tied))
        self.assertFalse(dominant & misaligned)

    def test_s_equal_complete_profile_no_evidence_uses_existing_null_ranking_path(self):
        import copy
        e = copy.copy(self.engine)
        e.school_branches = copy.deepcopy(self.engine.school_branches)
        key, major = next((key, row) for key, row in self.engine.majors_db.items()
                          if row.get("motive_driven") is not False)
        e.majors_db = {key: copy.deepcopy(major)}
        for row in list(e.school_branches.values()) + list(e.majors_db.values()):
            row["strategy_weights"] = [[.5] * 5 for _ in range(25)]
        sjt = {f"sjt_{i}": "A" for i in range(1, 26)}
        values = {f"conj_{i}": f"Q{i}A" for i in range(1, 16)}
        motives = major["micro_motive_codes"]
        branch = e.recommend_school_branch(motives, sjt, values)
        self.assertEqual(branch["s_assessment"]["status"], "complete")
        self.assertIsNone(branch["best_branch"])
        self.assertEqual(branch["recommended_branches"], [])
        self.assertEqual(len(branch["incomplete_assessments"]), 4)
        major_result = e.discover_individuality(motives, sjt, values)
        self.assertEqual(len(major_result["incomplete_assessments"]), 1)
        for row in branch["incomplete_assessments"] + major_result["incomplete_assessments"]:
            self.assertIsNone(row["score"])
            self.assertEqual(row["reason"], "equal_no_evidence")
            self.assertEqual(row["strategy_assessment"]["coverage"]["equal_answered"], 25)

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




def branch_metadata_profile_inputs(engine, counts):
    pools = [sorted(engine._active_branch_code_set(row['micro_motive_codes']))
             for row in engine.school_branches.values()]
    selected = [code for pool, k in zip(pools, counts) for code in pool[:k]]
    if selected:
        selected += [selected[0], ' ' + selected[0].upper() + ' ', 'not-a-valid-motive', '', None, True]
    return selected


class BranchMethodMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DarkHorseEngineV2()

    def test_d1_key_absent_in_empty_and_three_nonempty_output_fixtures(self):
        sjt = {f'sjt_{i}': 'A' for i in range(1, 26)}
        values = {f'conj_{i}': f'Q{i}A' for i in range(1, 16)}
        for counts in ((0, 0, 0, 0), (3, 4, 5, 8), (10, 10, 10, 10), (40, 20, 10, 10)):
            with self.subTest(counts=counts):
                result = self.engine.recommend_school_branch(
                    branch_metadata_profile_inputs(self.engine, counts), sjt, values)
                self.assertNotIn('m_denom_limit', result['method'])
                self.assertEqual(result['method']['scoring'], 'Total = 0.60×M + 0.20×S + 0.20×V')
                self.assertEqual(result['method']['v_epsilon'], .02)
                self.assertEqual(len(result['recommended_branches']), 4)
                expected = {name: round(100 * k / sum(counts), 1) if sum(counts) else 0.0
                            for name, k in zip(self.engine.school_branches, counts)}
                actual = {row['branch_name']: row['avg_components']['m_score']
                          for row in result['recommended_branches']}
                self.assertEqual(actual, expected)
        incomplete = self.engine.recommend_school_branch([], {}, {})
        self.assertNotIn('m_denom_limit', incomplete['method'])
        self.assertEqual(incomplete['recommended_branches'], [])

    def test_raw_branch_m_unchanged_for_three_fixed_profiles_and_noisy_inputs(self):
        for counts in ((3, 4, 5, 8), (10, 10, 10, 10), (40, 20, 10, 10)):
            inputs = branch_metadata_profile_inputs(self.engine, counts)
            for (name, branch), k in zip(self.engine.school_branches.items(), counts):
                with self.subTest(N=sum(counts), branch=name):
                    score, evidence = self.engine._compute_branch_m_score(inputs, branch)
                    self.assertEqual(score, k / sum(counts))
                    self.assertEqual(len(evidence), k)

    def test_m_paths_and_both_recommendations_ast_match_baseline_except_deleted_metadata(self):
        import ast
        import hashlib
        tree = ast.parse((ROOT / 'dark_horse_engine_v2.py').read_text())
        for node in ast.walk(tree):
            if hasattr(node, 'type_params') and not node.type_params:
                delattr(node, 'type_params')
        # Baseline hashes omit only the exact legacy key/value pair. Current source
        # must omit it, so no broad AST exemption or live calculation can hide here.
        methods = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        expected = {'_active_branch_code_set': 'b3384e0fad22e7a592cbf08a70d4171d81b9120816b28057a81f4b90210f0eae',
         '_compute_branch_m_score': '05c3da1bfdd20f99e952b0df2640f91795140983279d8733b0e51f9561f14c5b',
         '_compute_m_score': '33b72a309b85adc5753fd5d249c4c4c4e71bbf7d6411cdbd966d785e10bcc507',
         'discover_individuality': '73ab2993fad90c086cfb61ffa1441103fe03037c075a5c400292a3c6493e4787',
         'recommend_school_branch': '04cb1c67efb4b7f8994468d7b5a7a7dd214d4d452e76806eb0edee2d43ba5a57'}
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256(ast.dump(methods[name], include_attributes=False).encode()).hexdigest(),
                             digest, name + ' changed beyond approved metadata removal')


if __name__ == "__main__":
    unittest.main(verbosity=2)
