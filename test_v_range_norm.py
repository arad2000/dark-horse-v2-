"""Range-V contract tests; reference weights are never modified."""
import random
import unittest
from dark_horse_engine_v2 import DarkHorseEngineV2


class VRangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DarkHorseEngineV2()

    def test_all_active_profiles_extrema_and_complement_expectation(self):
        profiles = [m for m in self.engine.majors_db.values() if m.get('motive_driven') is not False]
        self.assertEqual(len(profiles), 202)
        self.assertEqual(len(self.engine.school_branches), 4)
        profiles += list(self.engine.school_branches.values())
        rng = random.Random(42)
        for profile in profiles:
            w = profile['value_weights']
            hi = [f'Q{i}' + ('A' if w[f'Q{i}A'] >= w[f'Q{i}B'] else 'B') for i in range(1, 16)]
            lo = [x[:-1] + ('B' if x[-1] == 'A' else 'A') for x in hi]
            self.assertAlmostEqual(self.engine._compute_v_score(hi, w)[0], 1)
            self.assertAlmostEqual(self.engine._compute_v_score(lo, w)[0], 0)
            for _ in range(20):
                choices = [f'Q{i}{rng.choice("AB")}' for i in range(1, 16)]
                opposite = [x[:-1] + ('B' if x[-1] == 'A' else 'A') for x in choices]
                self.assertAlmostEqual(sum(self.engine._compute_v_score(x, w)[0] for x in (choices, opposite)), 1)

    def test_aggregate_not_mean_of_pair_ratios(self):
        w = {f'Q{i}{side}': .5 for i in range(1, 16) for side in 'AB'}
        w.update({'Q1A': .9, 'Q1B': .1, 'Q2A': .52, 'Q2B': .5})
        self.assertAlmostEqual(self.engine._compute_v_score(['Q1A', 'Q2B'] + [f'Q{i}A' for i in range(3, 16)], w)[0], .8 / .82)

    def test_epsilon_boundary_and_zero_denominator(self):
        for delta, informative in ((.019, 0), (.02, 1), (.021, 1), (0, 0)):
            w = {f'Q{i}{side}': .5 for i in range(1, 16) for side in 'AB'}
            w['Q1A'] = .5 + delta
            r = self.engine._compute_v_result([f'Q{i}A' for i in range(1, 16)], w)
            self.assertEqual(r['coverage']['discriminative_answered'], informative)
            if not informative:
                self.assertIsNone(r['score'])
                self.assertEqual(r['status'], 'value_no_evidence')

    def test_invalid_duplicate_conflicting_and_missing(self):
        w = {'Q1A': .8, 'Q1B': .2}
        for inputs, answered in ((['Q1A', 'Q1A'], 1), (['Q1A', 'Q1B'], 0),
                                 (['', None, 'Q16A', 'Q01A'], 0)):
            r = self.engine._compute_v_result(inputs, w)
            self.assertEqual(r['coverage']['answered'], answered)
        for bad in (float('nan'), float('inf'), -1, 2, None):
            self.assertIsNone(self.engine._compute_v_score(['Q1A'], {'Q1A': bad, 'Q1B': .2})[0])

    def test_partial_coverage_is_not_issued_a_score(self):
        w = {f'Q{i}{side}': (.8 if side == 'A' else .2) for i in range(1, 16) for side in 'AB'}
        for n in (14, 0, 1, 5, 15):
            r = self.engine._compute_v_result([f'Q{i}A' for i in range(1, n+1)], w)
            if n == 15:
                self.assertAlmostEqual(r['score'], 1)
                self.assertEqual(r['status'], 'complete')
            else:
                self.assertIsNone(r['score'])
                self.assertEqual(r['reason'], 'value_incomplete')
                self.assertEqual(r['highlights'], [])
            self.assertEqual(r['coverage']['answered'], n)

    def test_public_incomplete_not_silent_zero_or_best_branch(self):
        result = self.engine.recommend_school_branch([], {}, {})
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(len(result['incomplete_assessments']), 4)
        self.assertEqual(result['recommended_branches'], [])
        self.assertIsNone(result['best_branch'])
        self.assertEqual(result['method']['version'], '3.2-v-evidence-floor')

    @staticmethod
    def full_choices():
        return [f'Q{i}A' for i in range(1, 16)]

    @staticmethod
    def full_weights():
        return {f'Q{i}{side}': (.9 if side == 'A' else .1)
                for i in range(1, 16) for side in 'AB'}

    def test_complete_with_one_available_witness_exposes_absolute_coverage(self):
        weights = {f'Q{i}{side}': .9 for i in range(1, 16) for side in 'AB'}
        weights['Q1B'] = .1
        result = self.engine._compute_v_result(self.full_choices(), weights)
        self.assertEqual(result['score'], 1)
        self.assertIsNone(result['reason'])
        self.assertEqual(result['coverage']['valid_reference_pairs'], 15)
        self.assertEqual(result['coverage']['discriminative_available'], 1)
        self.assertEqual(result['coverage']['discriminative_answered'], 1)
        self.assertEqual(len(result['highlights']), 1)
        self.assertEqual(self.engine._extract_dominant_values(self.full_choices(), weights),
                         [self.engine.value_poles.get('Q1A', 'Q1A')])

    def test_removal_cannot_inflate_other_cards_or_create_partial_traits(self):
        import copy
        weights = self.full_weights()
        unchanged = copy.deepcopy(weights)
        full = ['Q1A'] + [f'Q{i}B' for i in range(2, 16)]
        self.assertAlmostEqual(self.engine._compute_v_result(full, weights)['score'], 1 / 15)
        fixed_card = self.engine._pairwise_value_score('Q1A', weights)
        for choices in ([], full[:1], full[:14]):
            result = self.engine._compute_v_result(choices, weights)
            self.assertIsNone(result['score'])
            self.assertEqual(result['reason'], 'value_incomplete')
            self.assertEqual(result['highlights'], [])
            self.assertEqual(self.engine._extract_dominant_values(choices, weights), [])
            self.assertEqual(self.engine._extract_v_misaligned_poles(choices, weights), [])
            self.assertEqual(result['coverage']['discriminative_available'], 15)
            self.assertEqual(result['coverage']['discriminative_answered'], len(choices))
            self.assertEqual(self.engine._pairwise_value_score('Q1A', weights), fixed_card)
            self.assertEqual(weights, unchanged)

    def test_complete_answers_with_invalid_reference_fail_closed(self):
        for bad in (None, float('nan'), float('inf'), -1, 2, True, '.9', 10**1000):
            weights = self.full_weights()
            weights['Q3A'] = bad
            result = self.engine._compute_v_result(self.full_choices(), weights)
            self.assertIsNone(result['score'])
            self.assertEqual(result['reason'], 'value_reference_incomplete')
            self.assertEqual(result['coverage']['valid_reference_pairs'], 14)
            self.assertEqual(result['coverage']['invalid_reference_questions'], ['Q3'])
            self.assertEqual(result['highlights'], [])
        weights = self.full_weights()
        del weights['Q3B']
        self.assertEqual(self.engine._compute_v_result(self.full_choices(), weights)['reason'],
                         'value_reference_incomplete')

    def test_duplicate_unknown_order_and_conflict_do_not_manufacture_coverage(self):
        full, weights = self.full_choices(), self.full_weights()
        expected = self.engine._compute_v_result(full, weights)
        noisy = list(reversed(full)) + [' q1a ', 'Q16A', None, True, 5, '']
        self.assertEqual(self.engine._compute_v_result(noisy, weights), expected)
        conflicted = full + ['Q1B', 'Q1A']
        result = self.engine._compute_v_result(conflicted, weights)
        self.assertEqual(result, self.engine._compute_v_result(list(reversed(conflicted)), weights))
        self.assertIsNone(result['score'])
        self.assertEqual(result['reason'], 'value_incomplete')
        self.assertEqual(result['coverage']['answered'], 14)
        self.assertEqual(result['coverage']['conflicting_questions'], ['Q1'])

    def test_complete_medical_and_general_profiles_retain_m_s_and_recommendation(self):
        for major_id in (1, 42):
            major = next(row for row in self.engine.majors_db.values() if row['id'] == major_id)
            sjt_indices = [row.index(max(row)) for row in major['strategy_weights']]
            sjt = {f'sjt_{i}': chr(65 + choice) for i, choice in enumerate(sjt_indices, 1)}
            vw = major['value_weights']
            values = {f'conj_{i}': f'Q{i}' + ('A' if vw[f'Q{i}A'] >= vw[f'Q{i}B'] else 'B')
                      for i in range(1, 16)}
            result = self.engine.discover_individuality(major['micro_motive_codes'], sjt, values)
            rec = next(row for row in result['discovered_majors'] if int(row['major_id']) == major_id)
            components = rec['individuality_fit']['raw_components']
            self.assertEqual(components['m_score'], 100)
            self.assertEqual(components['s_score'], round(100 * self.engine._compute_s_score_for_complete_profile(
                sjt_indices, major['strategy_weights'])[0], 1))
            self.assertEqual(components['v_score'], 100)
            self.assertEqual(rec['individuality_fit']['value_assessment']['coverage']['answered'], 15)


    def test_m_s_and_total_ast_match_pinned_deploy_baseline(self):
        # Exact source contracts from deploy 2db75ec..., not new score baselines.
        import ast
        import hashlib
        from pathlib import Path
        tree = ast.parse(Path(__file__).with_name('dark_horse_engine_v2.py').read_text())
        for node in ast.walk(tree):
            if hasattr(node, 'type_params') and not node.type_params:
                delattr(node, 'type_params')
        methods = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        protected = {'_compute_m_score': '33b72a309b85adc5753fd5d249c4c4c4e71bbf7d6411cdbd966d785e10bcc507',
         '_active_branch_code_set': 'b3384e0fad22e7a592cbf08a70d4171d81b9120816b28057a81f4b90210f0eae',
         '_compute_branch_m_score': '05c3da1bfdd20f99e952b0df2640f91795140983279d8733b0e51f9561f14c5b',
         '_parse_s_strategy_answers': 'a88216c2f9c6054bbc808bd85863ff1f28fac10107a6f0d4a7403218a81a5ba6',
         '_s_item_score': '69be3057d517c1c950ee1be87889d5af8409db518b0b7475a2ff420f8382d6b3',
         '_compute_s_result': '7927ffba6f5d61ca3296652cd08da65148db2587c5faab48f98e8e56c553dc1d',
         '_compute_s_score': 'a599a5b88a334baae76bc2bb2f5b437d7167de89b667a427ca1139c41dc57dd5',
         '_compute_s_score_for_complete_profile': 'eb619f89cc5b650f5bb44f31caac9a31a354381464f5ef6391b38ebb3ff2e5ab',
         '_compute_trait_alignment_profile': 'f6ddd49fd1864e3263509a46ada9f9607f3cd07c83742dffa6a222a07b4315b6',
         '_extract_s_misaligned_traits': 'b0995b0a06f96b6635bba2b738225c81a9c94e9fee013832eee40793be01db35',
         '_extract_dominant_traits': '25d3e11aeade87085d51bf7b57cb5a1f83c9a7cc495a8de8e99783d472fe28a4'}
        for name, expected in protected.items():
            actual = hashlib.sha256(ast.dump(methods[name], include_attributes=False).encode()).hexdigest()
            self.assertEqual(actual, expected, name + ' changed from deploy baseline')
        totals = {'discover_individuality': 'dc780407654af88bb61caf302604d8dd68195f40620dbebe6b02403e29cf3fab',
         'recommend_school_branch': 'a31e6c82e598b0b05ec95db34578c9e94151f6c79b49e14715fa062d2766e550'}
        for name, expected in totals.items():
            assignments = [ast.dump(node, include_attributes=False) for node in ast.walk(methods[name])
                           if isinstance(node, ast.Assign)
                           and any(isinstance(target, ast.Name) and target.id == 'total' for target in node.targets)]
            self.assertEqual(hashlib.sha256(repr(assignments).encode()).hexdigest(), expected)



if __name__ == '__main__':
    unittest.main()
