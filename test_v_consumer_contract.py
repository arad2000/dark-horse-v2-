"""Exercise actual endpoint adapters with unavailable and real-engine results."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from test_main_api_contract import request_for
from main_v2 import DarkHorseDiscoverRequest, discover_v2, branch_discovery_v2
from dark_horse_engine_v2 import DarkHorseEngineV2


class VConsumerTests(unittest.IsolatedAsyncioTestCase):
    async def test_nulls_are_not_ranked_or_persisted_and_metadata_survives(self):
        engine = SimpleNamespace(
            discover_individuality=lambda *a: {'discovered_majors': [{
                'major_id': 1, 'individuality_fit': {'score': 80, 'status': 'no_discriminative_evidence',
                'raw_components': {'v_score': None}}}], 'method': {'version': '3.1-v-range-norm'}},
            recommend_school_branch=lambda *a: {'recommended_branches': [{
                'branch_name': 'null', 'average_score': None, 'status':'no_discriminative_evidence',
                'avg_components': {'v_score':None}}], 'best_branch':'null',
                'method': {'version':'3.1-v-range-norm'}})
        request = DarkHorseDiscoverRequest(micro_motives=[], session_id='v-null-test')
        with patch('main_v2._require_charged_journey', return_value=7), \
             patch('main_v2._persist_discovery_session', return_value=('test', None)), \
             patch('main_v2._persist_major_results') as major_store, \
             patch('main_v2._persist_branch_results') as branch_store:
            a = (await discover_v2(request, request_for(engine)))['discovery_result']
            b = (await branch_discovery_v2(request, request_for(engine)))['branch_discovery_result']
        for result, key in ((a,'recommendations'),(b,'branches')):
            self.assertEqual(result[key], [])
            self.assertEqual(result['status'], 'incomplete')
            self.assertEqual(result['incomplete_assessments'][0]['v_result']['status'], 'no_discriminative_evidence')
            self.assertEqual(result['method']['version'], '3.1-v-range-norm')
        self.assertIsNone(b['best_branch'])
        self.assertEqual(major_store.call_args.args[1], [])
        self.assertEqual(branch_store.call_args.args[1], [])

    async def test_equal_pairs_real_engine_preserves_no_evidence_and_coverage(self):
        engine = DarkHorseEngineV2()
        # Test-only weights; production JSON and engine class are not mutated.
        engine.school_branches = {"equal": {"micro_motive_codes": [],
            "strategy_weights": [[.2] * 5 for _ in range(25)],
            "value_weights": {f"Q{i}{side}": .5 for i in range(1,16) for side in "AB"}}}
        request = DarkHorseDiscoverRequest(micro_motives=[], session_id='v-equal-test',
            sjt_answers={f'sjt_{i}':'A' for i in range(1,26)},
            conjoint_choices={f'conj_{i}':f'Q{i}A' for i in range(1,16)})
        with patch('main_v2._require_charged_journey', return_value=7), \
             patch('main_v2._persist_discovery_session', return_value=('test', None)), \
             patch('main_v2._persist_branch_results', return_value=False) as persist:
            result = (await branch_discovery_v2(request, request_for(engine)))['branch_discovery_result']
        self.assertEqual(result['branches'], [])
        self.assertIsNone(result['best_branch'])
        assessment = result['incomplete_assessments'][0]['v_result']
        self.assertIsNone(assessment['score'])
        self.assertEqual(assessment['status'], 'value_no_evidence')
        self.assertEqual(assessment['coverage']['answered'], 15)
        self.assertEqual(assessment['coverage']['total'], 15)
        self.assertEqual(assessment['coverage']['discriminative_answered'], 0)
        self.assertEqual(assessment['coverage']['valid_reference_pairs'], 15)
        self.assertEqual(assessment['coverage']['discriminative_available'], 0)
        self.assertEqual(persist.call_args.args[1], [])

    async def test_real_engine_incomplete_payload_passes_api_adapter(self):
        request = DarkHorseDiscoverRequest(micro_motives=[], session_id='v-real-test')
        with patch('main_v2._require_charged_journey', return_value=7), \
             patch('main_v2._persist_discovery_session', return_value=('test', None)), \
             patch('main_v2._persist_branch_results', return_value=False):
            data = (await branch_discovery_v2(request, request_for(DarkHorseEngineV2())))['branch_discovery_result']
        self.assertEqual(len(data['incomplete_assessments']), 4)
        self.assertEqual(data['method']['version'], '3.2-v-evidence-floor')
        self.assertEqual(data['branches'], [])

    async def _call_values_endpoints(self, values, sjt=None):
        engine = DarkHorseEngineV2()
        major = next(row for row in engine.majors_db.values() if row['id'] == 1)
        request = DarkHorseDiscoverRequest(micro_motives=major['micro_motive_codes'],
            session_id='values-floor-test',
            sjt_answers=sjt if sjt is not None else {f'sjt_{i}':'A' for i in range(1, 26)},
            conjoint_choices=values)
        with patch('main_v2._enforce_public_rate_limit'), \
             patch('main_v2._require_charged_journey', return_value=7), \
             patch('main_v2._persist_discovery_session', return_value=('test', None)), \
             patch('main_v2._persist_major_results', return_value=False) as majors, \
             patch('main_v2._persist_branch_results', return_value=False) as branches:
            a = (await discover_v2(request, request_for(engine)))['discovery_result']
            b = (await branch_discovery_v2(request, request_for(engine)))['branch_discovery_result']
        return a, b, majors, branches

    async def test_partial_v_null_reason_survives_both_api_adapters_without_s_confusion(self):
        values = {f'conj_{i}': f'Q{i}A' for i in range(1, 15)}
        a, b, majors, branches = await self._call_values_endpoints(values)
        for result, key in ((a, 'recommendations'), (b, 'branches')):
            self.assertEqual(result[key], [])
            self.assertEqual(result['s_assessment']['status'], 'complete')
            self.assertTrue(result['incomplete_assessments'])
            for row in result['incomplete_assessments']:
                self.assertEqual(row['status'], 'value_incomplete')
                self.assertEqual(row['reason'], 'value_incomplete')
                self.assertEqual(row['strategy_assessment']['status'], 'complete')
                self.assertIsNone(row['v_result']['score'])
                self.assertEqual(row['v_result']['reason'], 'value_incomplete')
                self.assertEqual(row['v_result']['coverage']['answered'], 14)
                self.assertEqual(row['v_result']['highlights'], [])
        self.assertIsNone(b['best_branch'])
        self.assertEqual(majors.call_args.args[1], [])
        self.assertEqual(branches.call_args.args[1], [])

    async def test_complete_v_coverage_survives_ranked_api_outputs(self):
        values = {f'conj_{i}': f'Q{i}A' for i in range(1, 16)}
        a, b, _, _ = await self._call_values_endpoints(values)
        self.assertTrue(a['recommendations'])
        self.assertTrue(b['branches'])
        for row in a['recommendations'] + b['branches']:
            v = row['value_assessment']
            self.assertEqual(v['status'], 'complete')
            self.assertIsNone(v['reason'])
            self.assertTrue(0 <= v['score'] <= 1)
            self.assertEqual(v['coverage']['answered'], 15)
            self.assertEqual(v['coverage']['valid_reference_pairs'], 15)
            self.assertEqual(v['coverage']['discriminative_answered'],
                             v['coverage']['discriminative_available'])

    async def test_simultaneous_s_and_v_incomplete_keep_independent_reasons(self):
        a, b, _, _ = await self._call_values_endpoints({}, sjt={})
        for result in (a, b):
            self.assertEqual(result['s_assessment']['reason'], 'incomplete_s_responses')
            self.assertTrue(result['incomplete_assessments'])
            for row in result['incomplete_assessments']:
                self.assertEqual(row['reason'], 'incomplete_s_responses')
                self.assertEqual(row['v_result']['reason'], 'value_incomplete')
                self.assertNotEqual(row['v_result']['reason'], 'equal_no_evidence')
