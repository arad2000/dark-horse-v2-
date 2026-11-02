"""Range-V and Total-display contracts; reference weights are never modified."""
import random
import unittest
from contextlib import contextmanager, ExitStack
from copy import copy
from functools import lru_cache
from unittest.mock import patch
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





# Controlled component outputs isolate rounding without changing any reference data.


@lru_cache(maxsize=1)
def _total_reference_engine():
    return DarkHorseEngineV2()


@contextmanager
def total_boundary_engine(raw, missing=None):
    engine = copy(_total_reference_engine())
    key, major = next((k, row) for k, row in engine.majors_db.items() if row['id'] == 1)
    engine.majors_db = {key: major}
    name, branch = next(iter(engine.school_branches.items()))
    engine.school_branches = {name: branch}
    s = None if missing == 's' else raw
    v = None if missing == 'v' else raw
    with ExitStack() as stack:
        overrides = {
            '_compute_m_score': (raw, []), '_compute_branch_m_score': (raw, []),
            '_compute_s_score_for_complete_profile': (s, []),
            '_compute_s_result': {'score': s, 'status': 'complete' if s is not None else 'equal_no_evidence'},
            '_compute_v_result': {'score': v, 'highlights': [],
                'status': 'complete' if v is not None else 'value_incomplete',
                'reason': None if v is not None else 'value_incomplete', 'coverage': {'answered': 15}},
            '_find_alternative_paths': [], '_find_branch_alternative_paths': [],
        }
        for method, result in overrides.items():
            stack.enter_context(patch.object(engine, method, return_value=result))
        yield engine


class TotalThresholdTests(unittest.TestCase):
    sjt = {f'sjt_{i}': 'A' for i in range(1, 26)}
    values = {f'conj_{i}': f'Q{i}A' for i in range(1, 16)}

    def test_major_30_boundary_is_rounded_not_raw(self):
        for raw, expected in ((.2990, None), (.2994, None), (.2996, 30.0),
                              (.3000, 30.0), (.3004, 30.0), (.301, 30.1)):
            with self.subTest(raw=raw), total_boundary_engine(raw) as engine:
                result = engine.discover_individuality([], self.sjt, self.values)
                rows = result['discovered_majors']
                if expected is None:
                    self.assertEqual(rows, [])
                else:
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]['individuality_fit']['score'], expected)
                    self.assertEqual(rows[0]['individuality_fit']['level'], 'همخوانی پایین')

    def test_40_60_80_levels_and_summary_use_the_same_rounded_score(self):
        for threshold, below, above in ((40, 'همخوانی پایین', 'همخوانی متوسط'),
                                        (60, 'همخوانی متوسط', 'همخوانی بالا'),
                                        (80, 'همخوانی بالا', 'همخوانی بسیار بالا')):
            for offset in (-.10, -.04, 0, .04):
                raw = (threshold + offset) / 100
                expected = threshold - .1 if offset == -.10 else float(threshold)
                with self.subTest(threshold=threshold, offset=offset), total_boundary_engine(raw) as engine:
                    result = engine.discover_individuality([], self.sjt, self.values)
                    fit = result['discovered_majors'][0]['individuality_fit']
                    self.assertEqual(fit['score'], expected)
                    self.assertEqual(fit['level'], below if offset == -.10 else above)
                    # Summary deliberately has three bands, not four fit levels.
                    summary = result['summary']
                    self.assertEqual(summary['high_compatibility'], int(expected >= 80))
                    self.assertEqual(summary['medium_compatibility'], int(60 <= expected < 80))
                    self.assertEqual(summary['low_compatibility'], int(expected < 60))

    def test_branch_server_retains_below_30_and_reports_one_decimal(self):
        cases = [(.2990, 29.9), (.2994, 29.9), (.2996, 30.0), (.3000, 30.0), (.3004, 30.0)]
        cases += [((threshold + offset) / 100, threshold - .1 if offset == -.10 else float(threshold))
                  for threshold in (40, 60, 80) for offset in (-.10, -.04, 0, .04)]
        for raw, expected in cases:
            with self.subTest(raw=raw), total_boundary_engine(raw) as engine:
                result = engine.recommend_school_branch([], self.sjt, self.values)
                self.assertEqual(len(result['recommended_branches']), 1)
                row = result['recommended_branches'][0]
                for field in ('average_score', 'max_score', 'min_score'):
                    self.assertEqual(row[field], expected)
                self.assertEqual(result['best_branch'], row['branch_name'])
                self.assertNotIn('level', row)  # Do not invent branch 40/60/80 levels.

    def test_python_binary_float_ties_to_even_is_not_decimal_half_away(self):
        for raw, expected in ((.3125, 31.2), (.3175, 31.8)):
            with self.subTest(raw=raw), total_boundary_engine(raw) as engine:
                major = engine.discover_individuality([], self.sjt, self.values)['discovered_majors'][0]
                branch = engine.recommend_school_branch([], self.sjt, self.values)['recommended_branches'][0]
                self.assertEqual(major['individuality_fit']['score'], expected)
                self.assertEqual(branch['average_score'], expected)
        self.assertEqual(round(30.05, 1), 30.1)
        self.assertEqual(round(30.25, 1), 30.2)

    def test_null_s_or_v_never_constructs_a_numeric_total(self):
        for missing in ('s', 'v'):
            with self.subTest(missing=missing), total_boundary_engine(.8, missing) as engine:
                a = engine.discover_individuality([], self.sjt, self.values)
                b = engine.recommend_school_branch([], self.sjt, self.values)
                self.assertEqual(a['discovered_majors'], [])
                self.assertEqual(b['recommended_branches'], [])
                self.assertIsNone(b['best_branch'])
                for result in (a, b):
                    self.assertEqual(len(result['incomplete_assessments']), 1)
                    self.assertIsNone(result['incomplete_assessments'][0]['score'])

    def test_medical_and_general_recommendation_matches_deploy_snapshot(self):
        engine = DarkHorseEngineV2()
        for major_id, expected_score, expected_s in ((1, 100.0, 100.0), (42, 99.6, 97.0)):
            major = next(row for row in engine.majors_db.values() if row['id'] == major_id)
            sjt = {f'sjt_{i}': chr(65 + row.index(max(row)))
                   for i, row in enumerate(major['strategy_weights'], 1)}
            w = major['value_weights']
            values = {f'conj_{i}': f'Q{i}' + ('A' if w[f'Q{i}A'] >= w[f'Q{i}B'] else 'B')
                      for i in range(1, 16)}
            result = engine.discover_individuality(major['micro_motive_codes'], sjt, values)
            fit = next(row['individuality_fit'] for row in result['discovered_majors']
                       if int(row['major_id']) == major_id)
            self.assertEqual(fit['score'], expected_score)
            self.assertEqual(fit['raw_components'], {'m_score': 100.0, 's_score': expected_s, 'v_score': 100.0})


    def test_total_uses_raw_components_not_rounded_component_percentages(self):
        with total_boundary_engine(.2994) as engine, patch.object(engine, '_compute_v_result',
                return_value={'score': .4004, 'highlights': [], 'status': 'complete', 'reason': None}):
            fit = engine.discover_individuality([], self.sjt, self.values)['discovered_majors'][0]['individuality_fit']
            self.assertEqual(fit['score'], 33.0)
            c = fit['raw_components']
            reconstructed = round(.55*c['m_score'] + .30*c['v_score'] + .15*c['s_score'], 1)
            self.assertEqual(reconstructed, 32.9)
            self.assertNotEqual(fit['score'], reconstructed)

    def test_v_contract_ast_matches_current_deploy(self):
        # M/S and both Total expressions are already pinned by VRangeTests.
        import ast
        import hashlib
        from pathlib import Path
        tree = ast.parse(Path(__file__).with_name('dark_horse_engine_v2.py').read_text())
        for node in ast.walk(tree):
            if hasattr(node, 'type_params') and not node.type_params:
                delattr(node, 'type_params')
        methods = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        expected = {'_compute_v_result': '57de9e2d2864a1d93f68f31c7cab26a90bebdd61e3ddf2aab2c9355b39961afd',
         '_compute_v_score': 'fce5e640e03bb563f5c53d5d333e89a04e8bf9f2d451db4c38f31f170c26ddad',
         '_extract_dominant_values': '270e107b9b381012e43a12c9ee6cc458b2d27f55b286b94d607b24eae55ccf2b',
         '_extract_v_misaligned_poles': '5534faac5205892c61f0b794043c5948f290174f70cefd52cefc1bdea2489d22',
         '_pairwise_value_score': '9ae2e7557f7414fdccddf1d5c58e27a0f462da52e96b9f7e0b4780e02405a28a',
         '_v_method': '451fb5d406ed00036d5426aca67f0c41f90d079b4825b9e2897c8181f110a39f',
         '_valid_value_code': '88242abf40ce80f048db5a660ffab328085a4c692455290d9ad90495400bcaac',
         '_valid_value_pair': '1cf6e11b3fc6084b5c55c3bd5bcfa09185a204dbc4f5914eb451ecbcc77f8690'}
        for name, digest in expected.items():
            actual = hashlib.sha256(ast.dump(methods[name], include_attributes=False).encode()).hexdigest()
            self.assertEqual(actual, digest, name + ' changed from deploy 46456a6')




def v_epsilon_snapshot(engine):
    """Read-only census; counts cards, never the two poles as two witnesses."""
    rows = []
    for major in engine.majors_db.values():
        if major.get('motive_driven') is False:
            continue
        pairs = [engine._valid_value_pair(f'Q{i}', major['value_weights']) for i in range(1, 16)]
        if any(pair is None for pair in pairs):
            raise AssertionError('Invalid reference in census: ' + str(major['id']))
        spans = [round(abs(a - b), 12) for a, b in pairs]
        result = engine._compute_v_result([f'Q{i}A' for i in range(1, 16)], major['value_weights'])
        kept = sum(span >= engine.V_EPSILON for span in spans)
        if result['coverage']['discriminative_available'] != kept:
            raise AssertionError('Coverage diverges from span predicate')
        rows.append({'id': major['id'], 'name': major['name'], 'group': major.get('group'),
                     'retained': kept, 'excluded': 15 - kept,
                     'equal': sum(a == b for a, b in pairs),
                     'positive_subthreshold': sum(a != b and span < engine.V_EPSILON
                                                 for (a, b), span in zip(pairs, spans)),
                     'at_boundary': spans.count(engine.V_EPSILON)})
    return {
        'active_majors': len(rows), 'total_pairs': 15 * len(rows),
        'excluded': sum(r['excluded'] for r in rows),
        'retained': sum(r['retained'] for r in rows),
        'equal': sum(r['equal'] for r in rows),
        'positive_subthreshold': sum(r['positive_subthreshold'] for r in rows),
        'at_boundary': sum(r['at_boundary'] for r in rows),
        'distribution': {'0': sum(r['retained'] == 0 for r in rows),
                         '1-3': sum(1 <= r['retained'] <= 3 for r in rows),
                         '4-7': sum(4 <= r['retained'] <= 7 for r in rows),
                         '8+': sum(r['retained'] >= 8 for r in rows)},
        'lowest': sorted(rows, key=lambda r: (r['retained'], r['id']))[:5],
    }


class VEpsilonContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DarkHorseEngineV2()

    @staticmethod
    def weights():
        return {f'Q{i}{side}': .5 for i in range(1, 16) for side in 'AB'}

    @staticmethod
    def choices():
        return [f'Q{i}A' for i in range(1, 16)]

    def test_v0_constant_and_rounded_boundary_both_choices(self):
        self.assertEqual(self.engine.V_EPSILON, .02)
        self.assertEqual(self.engine._v_method()['v_epsilon'], .02)
        for diff, retained in ((.019, 0), (.020, 1), (.021, 1),
                               (.0199999999994, 0), (.0199999999996, 1)):
            for pole in ('A', 'B'):
                with self.subTest(diff=diff, pole=pole):
                    w = self.weights()
                    w['Q1A'] = .5 + diff
                    choices = [f'Q1{pole}'] + self.choices()[1:]
                    result = self.engine._compute_v_result(choices, w)
                    self.assertEqual(result['coverage']['discriminative_available'], retained)
                    self.assertEqual(result['coverage']['discriminative_answered'], retained)
                    if retained:
                        self.assertEqual(result['status'], 'complete')
                        self.assertAlmostEqual(result['score'], 1 if pole == 'A' else 0, places=8)
                    else:
                        self.assertIsNone(result['score'])
                        self.assertEqual(result['reason'], 'value_no_evidence')
                    pairwise, _ = self.engine._pairwise_value_score(f'Q1{pole}', w)
                    self.assertAlmostEqual(pairwise, int(bool(retained) and pole == 'A'), places=8)

    def test_excluded_pair_is_absent_from_both_sums_and_traits(self):
        w = self.weights()
        w.update({'Q1A': .9, 'Q1B': .1, 'Q2A': .99, 'Q2B': .98, 'Q3A': .6, 'Q3B': .4})
        choices = self.choices()
        choices[2] = 'Q3B'
        # Unique test-only pole labels make absence of the excluded card observable.
        with patch.object(self.engine, 'value_poles', {k: k for k in w}):
            for q2 in ('Q2A', 'Q2B'):
                choices[1] = q2
                result = self.engine._compute_v_result(choices, w)
                self.assertAlmostEqual(result['score'], .8)  # .8/(.8+.2), not .8/(.8+.01+.2)
                self.assertEqual(result['coverage']['discriminative_available'], 2)
                self.assertNotIn('Q2', ' '.join(result['highlights']))
                self.assertNotIn(q2, self.engine._extract_dominant_values(choices, w))
                self.assertNotIn(q2, self.engine._extract_v_misaligned_poles(choices, w))

    def test_zero_evidence_full_answers_is_distinct_from_missing_or_conflict(self):
        w = {f'Q{i}{side}': (.519 if side == 'A' else .5)
             for i in range(1, 16) for side in 'AB'}
        for choices, reason in ((self.choices(), 'value_no_evidence'),
                                (self.choices()[:14], 'value_incomplete'),
                                (self.choices() + ['Q1B'], 'value_incomplete')):
            result = self.engine._compute_v_result(choices, w)
            self.assertIsNone(result['score'])
            self.assertEqual(result['reason'], reason)
            self.assertEqual(result['coverage']['valid_reference_pairs'], 15)
            self.assertEqual(result['coverage']['discriminative_available'], 0)
            self.assertEqual(result['highlights'], [])
            self.assertEqual(self.engine._extract_dominant_values(choices, w), [])
            self.assertEqual(self.engine._extract_v_misaligned_poles(choices, w), [])

    def test_current_reference_coverage_snapshot(self):
        snapshot = v_epsilon_snapshot(self.engine)
        for field, expected in {'active_majors': 202, 'total_pairs': 3030, 'excluded': 332,
                                'retained': 2698, 'equal': 329, 'positive_subthreshold': 3,
                                'at_boundary': 21}.items():
            self.assertEqual(snapshot[field], expected, field)
        self.assertEqual(snapshot['distribution'], {'0': 0, '1-3': 0, '4-7': 14, '8+': 188})
        self.assertEqual([(r['id'], r['retained']) for r in snapshot['lowest']],
                         [(170, 4), (164, 5), (166, 6), (169, 6), (205, 6)])
        # The same reconstruction of exclusions is valid for all four branches too.
        for profile in list(self.engine.majors_db.values()) + list(self.engine.school_branches.values()):
            if profile.get('motive_driven') is False:
                continue
            w = profile['value_weights']
            coverage = self.engine._compute_v_result(self.choices(), w)['coverage']
            excluded = sum(round(abs(w[f'Q{i}A'] - w[f'Q{i}B']), 12) < .02 for i in range(1, 16))
            self.assertEqual(coverage['valid_reference_pairs'] - coverage['discriminative_available'], excluded)
            self.assertEqual(coverage['discriminative_answered'], coverage['discriminative_available'])

    def test_low_evidence_major_still_requires_answering_even_equal_cards(self):
        major = next(m for m in self.engine.majors_db.values() if m['id'] == 164)
        w = major['value_weights']
        hi = [f'Q{i}' + ('A' if w[f'Q{i}A'] >= w[f'Q{i}B'] else 'B') for i in range(1, 16)]
        full = self.engine._compute_v_result(hi, w)
        self.assertEqual(full['coverage']['discriminative_available'], 5)
        self.assertAlmostEqual(full['score'], 1)
        omitted = next(i for i in range(1, 16) if w[f'Q{i}A'] == w[f'Q{i}B'])
        partial = self.engine._compute_v_result([c for c in hi if c[:-1] != f'Q{omitted}'], w)
        self.assertEqual(partial['coverage']['answered'], 14)
        self.assertEqual(partial['coverage']['discriminative_answered'], 5)
        self.assertIsNone(partial['score'])
        self.assertEqual(partial['reason'], 'value_incomplete')

    def test_invalid_reference_is_not_a_threshold_exclusion(self):
        w = self.weights()
        w['Q15A'] = float('nan')
        full = self.engine._compute_v_result(self.choices(), w)
        c = full['coverage']
        self.assertEqual(c['valid_reference_pairs'], 14)
        self.assertEqual(c['discriminative_available'], 0)
        self.assertEqual(c['valid_reference_pairs'] - c['discriminative_available'], 14)
        self.assertEqual(c['invalid_reference_questions'], ['Q15'])
        self.assertEqual(full['reason'], 'value_reference_incomplete')
        self.assertIsNone(full['score'])
        self.assertEqual(self.engine._compute_v_result(self.choices()[:14], w)['reason'], 'value_incomplete')

    def test_full_medical_technical_and_law_v_matches_deploy(self):
        # Actual deploy ac02193, alternating A/B for V; not only trivial best-pole scores.
        cases = ((1, .5432873274780426, 15, 86.3, 100.0),
                 (42, .7693920335429768, 12, 92.6, 97.0),
                 (101, .6314199395770391, 15, 88.7, 98.5))
        choices = [f'Q{i}' + ('A' if i % 2 else 'B') for i in range(1, 16)]
        for major_id, expected_v, count, total, s in cases:
            with self.subTest(major_id=major_id):
                m = next(m for m in self.engine.majors_db.values() if m['id'] == major_id)
                v = self.engine._compute_v_result(choices, m['value_weights'])
                self.assertAlmostEqual(v['score'], expected_v, places=12)
                self.assertEqual(v['coverage']['answered'], 15)
                self.assertEqual(v['coverage']['discriminative_available'], count)
                sjt = {f'sjt_{i}': chr(65 + row.index(max(row))) for i, row in enumerate(m['strategy_weights'], 1)}
                values = {f'conj_{i}': choice for i, choice in enumerate(choices, 1)}
                rows = self.engine.discover_individuality(m['micro_motive_codes'], sjt, values)['discovered_majors']
                fit = next(r['individuality_fit'] for r in rows if int(r['major_id']) == major_id)
                self.assertEqual(fit['score'], total)
                self.assertEqual(fit['raw_components']['m_score'], 100)
                self.assertEqual(fit['raw_components']['s_score'], s)


if __name__ == '__main__':
    unittest.main()
