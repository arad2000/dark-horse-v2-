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
            discover_individuality=lambda *a: {'s_assessment': {'status': 'complete', 'valid_answers': 25, 'expected_answers': 25}, 'discovered_majors': [{
                'major_id': 1, 'individuality_fit': {'score': 80, 'status': 'no_discriminative_evidence',
                'raw_components': {'v_score': None}}}], 'method': {'version': '3.1-v-range-norm'}},
            recommend_school_branch=lambda *a: {'s_assessment': {'status': 'complete', 'valid_answers': 25, 'expected_answers': 25}, 'recommended_branches': [{
                'branch_name': 'null', 'average_score': None, 'status':'no_discriminative_evidence',
                'avg_components': {'v_score':None}}], 'best_branch':'null',
                'method': {'version':'3.1-v-range-norm'}})
        request = DarkHorseDiscoverRequest(micro_motives=[], session_id='v-null-test', sjt_answers={f'sjt_{i}': 'A' for i in range(1, 26)})
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
        self.assertEqual(assessment['status'], 'no_discriminative_evidence')
        self.assertEqual(assessment['coverage'], {'answered':15,'total':15,'discriminative_answered':0})
        self.assertEqual(persist.call_args.args[1], [])

    async def test_real_engine_incomplete_payload_passes_api_adapter(self):
        request = DarkHorseDiscoverRequest(micro_motives=[], session_id='v-real-test')
        with patch('main_v2._require_charged_journey', return_value=7), \
             patch('main_v2._persist_discovery_session', return_value=('test', None)), \
             patch('main_v2._persist_branch_results', return_value=False):
            data = (await branch_discovery_v2(request, request_for(DarkHorseEngineV2())))['branch_discovery_result']
        self.assertEqual(len(data['incomplete_assessments']), 4)
        self.assertEqual(data['method']['version'], '3.1-v-range-norm')
        self.assertEqual(data['branches'], [])
