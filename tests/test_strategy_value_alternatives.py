"""Offline tests for the approved S>70 OR V>70 independent selector."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dark_horse_engine_v2 import DarkHorseEngineV2
from strategy_value_alternatives import build_strategy_value_alternatives


def major(mid, s=.8, v=.8):
    return {'id': mid, 'name': f'fixture-{mid}',
            'strategy_weights': [[s, 1., .1, .2, .3] for _ in range(25)],
            'value_weights': {f'Q{i}{side}': v if side == 'A' else .2
                              for i in range(1, 16) for side in 'AB'}}


class StrategyValueAlternativesTest(unittest.TestCase):
    def setUp(self):
        self.engine = DarkHorseEngineV2.__new__(DarkHorseEngineV2)
        self.engine.trait_map = {}
        self.engine.value_poles = {}
        self.engine.majors_db = {1: major(1)}
        self.s = {f'sjt_{i}': 'A' for i in range(1, 26)}
        self.v = {f'conj_{i}': f'Q{i}A' for i in range(1, 16)}

    def run_selector(self):
        return build_strategy_value_alternatives(self.engine, self.s, self.v, 1)

    def add(self, *majors):
        self.engine.majors_db.update({m['id']: m for m in majors})

    def test_both_strategy_and_value_reasons(self):
        self.add(major(2, .9, .9), major(3, .95, .6), major(4, .5, .99))
        rows = self.run_selector()['items']
        self.assertEqual([(r['major_id'], r['basis']) for r in rows],
                         [(2, 'both'), (4, 'value'), (3, 'strategy')])
        for row in rows:
            self.assertTrue(row['reason'])
            m = self.engine.majors_db[row['major_id']]
            self.assertEqual(row['strategy']['score'], self.engine._compute_s_score([0]*25, m['strategy_weights'])[0])
            self.assertEqual(row['value']['score'], self.engine._compute_v_score(list(self.v.values()), m['value_weights'])[0])

    def test_strict_threshold_unrounded(self):
        # Isolate the comparison contract from floating-point averaging artifacts.
        self.engine._compute_s_score = lambda a, w: (w[0][0], [])
        self.engine._compute_v_score = lambda a, w: (w['Q1A'], [])
        self.add(major(2, .7, .7), major(3, .70001, .6))
        self.assertEqual([r['major_id'] for r in self.run_selector()['items']], [3])

    def test_both_first_weakest_dimension_then_single_score(self):
        self.add(major(2, .99, .71), major(3, .81, .81), major(4, .99, .1), major(5, .5, .98))
        result = self.run_selector()
        self.assertEqual(result['candidate_count'], 4)
        self.assertEqual([r['major_id'] for r in result['items']], [3, 2, 4])

    def test_zero_one_two_and_no_padding(self):
        self.add(major(2, .1, .1))
        self.assertEqual(self.run_selector()['items'], [])
        self.assertEqual(self.run_selector()['status'], 'no_matches_in_evaluated_dimensions')
        self.add(major(3, .8, .8))
        self.assertEqual(len(self.run_selector()['items']), 1)
        self.add(major(4, .8, .8))
        self.assertEqual(len(self.run_selector()['items']), 2)

    def test_unknown_is_not_zero_and_does_not_block_other_dimension(self):
        m = major(2, .9, .9)
        m['strategy_weights'] = []
        self.add(m)
        row = self.run_selector()['items'][0]
        self.assertEqual(row['basis'], 'value')
        self.assertIsNone(row['strategy']['score'])
        self.assertEqual(row['strategy']['status'], 'unknown')
        self.assertEqual(row['strategy']['reason'], 'incomplete_or_invalid_weights')
        del self.v['conj_15']
        self.assertEqual(self.run_selector()['status'], 'insufficient_data')

    def test_wrong_question_value_code_and_partial_answers(self):
        self.add(major(2, .9, .9))
        self.v['conj_1'] = 'Q2A'
        self.assertEqual(self.run_selector()['items'][0]['basis'], 'strategy')
        self.s['sjt_25'] = 'AA'
        result = self.run_selector()
        self.assertEqual(result['items'], [])
        self.assertEqual(result['status'], 'insufficient_data')

    def test_invalid_weights_nan_boolean_zero_row(self):
        for invalid in (float('nan'), float('inf'), True, -1, 2):
            m = major(2)
            m['strategy_weights'][0][0] = invalid
            m['value_weights']['Q1A'] = invalid
            self.add(m)
            self.assertEqual(self.run_selector()['status'], 'insufficient_data')
        m = major(2)
        m['strategy_weights'][0] = [0]*5
        self.add(m)
        self.assertEqual(self.run_selector()['items'][0]['basis'], 'value')

    def test_ties_stable_and_current_excluded(self):
        self.add(major(4), major(2), major(3), major(5))
        expected = self.run_selector()
        self.assertEqual([r['major_id'] for r in expected['items']], [2, 3, 4])
        self.engine.majors_db = dict(reversed(list(self.engine.majors_db.items())))
        self.assertEqual(self.run_selector(), expected)

    def test_full_catalog_no_motive_total_or_distance_gate_and_no_mutation(self):
        self.add(major(2, .9, .9))
        self.engine.majors_db[2]['micro_motive_codes'] = []
        self.engine._hybrid_profile_distance = lambda *a, **kw: self.fail('distance called')
        self.engine._compute_m_score = lambda *a, **kw: self.fail('motive gate called')
        before = copy.deepcopy((self.engine.majors_db, self.s, self.v))
        self.assertEqual(self.run_selector()['items'][0]['major_id'], 2)
        self.assertEqual(before, (self.engine.majors_db, self.s, self.v))

    def test_uniform_weights_disclosed_not_reinterpreted(self):
        m = major(2)
        m['strategy_weights'] = [[.2]*5 for _ in range(25)]
        m['value_weights'] = {f'Q{i}{side}': .8 for i in range(1, 16) for side in 'AB'}
        self.add(m)
        row = self.run_selector()['items'][0]
        self.assertEqual(row['strategy']['score'], 1.)
        self.assertEqual(row['evidence']['uniform_strategy_rows'], 25)
        self.assertEqual(row['evidence']['equal_value_pairs'], 15)

    def test_real_catalog_scans_every_other_major(self):
        self.engine.majors_db = {m['id']: m for m in json.loads((ROOT/'majors_database_v2.json').read_text())}
        result = self.run_selector()
        coverage = result['coverage']
        self.assertEqual(coverage['catalog_count'], 230)
        self.assertEqual(sum(coverage[k] for k in ('both_dimensions_evaluated', 'one_dimension_evaluated', 'neither_dimension_evaluated')), 229)
        self.assertLessEqual(len(result['items']), 3)
        for row in result['items']:
            self.assertNotEqual(row['major_id'], 1)
            self.assertTrue(row['strategy']['qualifies'] or row['value']['qualifies'])


class AlternativesEnrichmentTest(unittest.TestCase):
    def test_replaces_legacy_top_and_nested_without_changing_scores_or_input(self):
        from strategy_value_alternatives import attach_strategy_value_alternatives
        engine = DarkHorseEngineV2.__new__(DarkHorseEngineV2)
        engine.trait_map, engine.value_poles = {}, {}
        engine.majors_db = {1: major(1), 2: major(2), 3: major(3)}
        s = {f'sjt_{i}': 'A' for i in range(1,26)}
        v = {f'conj_{i}': f'Q{i}A' for i in range(1,16)}
        originals = [{'major_id': mid, 'alternative_paths': [{'major_id':999}],
                      'individuality_fit': {'score': 52.3, 'raw_components': {'m_score':20},
                                           'alternative_paths': [{'major_id':999}]}}
                     for mid in (1,2)]
        before = copy.deepcopy(originals)
        result = attach_strategy_value_alternatives(engine, originals, s, v)
        self.assertEqual(originals, before)
        for item in result:
            self.assertEqual(item['individuality_fit']['score'], 52.3)
            self.assertEqual(item['individuality_fit']['raw_components'], {'m_score':20})
            self.assertEqual(item['alternative_paths'], item['individuality_fit']['alternative_paths'])
            self.assertTrue(item['alternative_paths'])
            self.assertNotIn(item['major_id'], [x['major_id'] for x in item['alternative_paths']])
            self.assertNotIn(999, [x['major_id'] for x in item['alternative_paths']])

    def test_api_wires_enrichment_before_persistence(self):
        import ast
        tree = ast.parse((ROOT/'main_v2.py').read_text())
        endpoint = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'discover_v2')
        text = ast.unparse(endpoint)
        self.assertIn('attach_strategy_value_alternatives', text)
        self.assertLess(text.index('enriched_majors ='), text.index('_persist_major_results('))
        self.assertIn('for item in enriched_majors', text)
        self.assertIn("rec['alternative_paths'] = fit['alternative_paths']", text)


if __name__ == '__main__':
    unittest.main()
