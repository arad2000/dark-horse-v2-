"""Scoped batch-2 tests. Do not change historical fingerprint/CI gates."""
import copy
import hashlib
import json
import subprocess
import unittest
from decimal import Decimal

from dh013_batch2_166_170 import (BASE, IDS, ROOT, build, gitbytes, global_audit,
                                 load_base, outputs, parse, to_row)


class Batch2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result,cls.catalog,cls.motives=build()
        cls.original=load_base('majors_database_v2.json')

    def test_actual_next_five_active_and_no_activation(self):
        selected=[m['id'] for m in self.original if m['id']>165 and m.get('motive_driven') is not False][:5]
        self.assertEqual(selected,IDS)
        self.assertEqual(sum(m.get('motive_driven') is not False for m in self.catalog),202)
        self.assertEqual(sum(m.get('motive_driven') is False for m in self.catalog),28)

    def test_two_weight_drafts_and_other_228_preserved(self):
        changed=[]
        for old,new in zip(self.original,self.catalog):
            self.assertEqual(old['id'],new['id'])
            self.assertEqual(set(old),set(new))
            if old!=new:
                changed.append(new['id'])
                self.assertEqual({k for k in old if old[k]!=new[k]}, {'strategy_weights','value_weights'})
        self.assertEqual(changed,[166,169])
        self.assertEqual(self.result['scope']['other_major_records_preserved'],228)

    def test_batch1_and_three_withheld_profiles_unchanged(self):
        ids=set(range(161,166))|{167,168,170}
        for old,new in zip(self.original,self.catalog):
            if old['id'] in ids:self.assertEqual(old,new)
        self.assertTrue(self.result['scope']['batch1_preserved'])

    def test_exact_35_motive_edits_only_descriptions(self):
        old=load_base('docs/data/micro_motives.json');changed=[]
        for a,b in zip(old,self.motives):
            self.assertEqual(a['code'],b['code'])
            if a!=b:
                changed.append(b['code'])
                self.assertEqual({k for k in a if a[k]!=b[k]},{'description_fa'})
        self.assertEqual(len(old),1393)
        self.assertEqual(len({m['code'] for m in self.motives}),1393)
        self.assertEqual(set(changed),{c for m in self.catalog if m['id'] in IDS for c in m['micro_motive_codes']})
        self.assertEqual(len(changed),35)

    def test_every_question_all_options_and_150_value_keys_reviewed(self):
        for major in self.result['majors']:
            strategies=major['strategy_evidence'];values=major['value_evidence']
            self.assertEqual({e['question']['id'] for e in strategies},{f'S{i:02}' for i in range(1,26)})
            self.assertEqual({o['code'] for e in values for o in e['question']['options']}, {f'Q{i}{s}' for i in range(1,16) for s in 'AB'})
            for e in strategies+values:
                q=e['question']
                self.assertTrue(q['question'])
                self.assertEqual(len(q['options']),5 if q['id'].startswith('S') else 2)
                self.assertTrue(all(o['text'] for o in q['options']))
        self.assertEqual(sum(len(m['strategy_evidence']) for m in self.result['majors']),125)
        self.assertEqual(sum(2*len(m['value_evidence']) for m in self.result['majors']),150)

    def test_local_full_witness_and_no_slopes_without_witness(self):
        for major in self.result['majors']:
            own={m['code']:m['proposed'] for m in major['motives']}
            for e in major['strategy_evidence']+major['value_evidence']:
                self.assertTrue(e['rationale'])
                for witness in e['witnesses']:
                    self.assertEqual(witness['text'],own[witness['code']])
                if e['weights'] is not None and len(set(e['weights']))>1:self.assertTrue(e['witnesses'])
                if e['status']=='EQUAL_NO_EVIDENCE':self.assertEqual(e['witnesses'],[])

    def test_insufficient_evidence_does_not_emit_numerical_profile(self):
        expected={166:6,167:7,168:7,169:6,170:7}
        for m in self.result['majors']:
            self.assertEqual(m['equal_s_count'],expected[m['id']])
            if m['equal_s_count']>6:
                self.assertEqual(m['weighting_status'],'INSUFFICIENT_EVIDENCE')
                self.assertNotIn('weight_patch',m)
                for e in m['strategy_evidence']+m['value_evidence']:
                    self.assertIsNone(e['weights']);self.assertIsNone(e['raw_weights'])
            else:
                self.assertTrue(m['requires_supervisor_equal_approval'])
                self.assertIn('weight_patch',m)
        self.assertFalse(self.result['merge_authorized'])

    def test_normalization_four_decimals_and_residual_largest_raw(self):
        self.assertEqual(to_row([1,1,1,0,0]),[.3334,.3333,.3333,0,0])
        self.assertEqual(to_row([.1,.1,.2,.1,.1]),[.1667,.1667,.3332,.1667,.1667])
        for m in self.result['majors']:
            if 'weight_patch' not in m:continue
            for row in m['weight_patch']['strategy_weights']:
                self.assertEqual(len(row),5)
                self.assertEqual(sum(Decimal(str(n)) for n in row),1)
                self.assertTrue(all(0<=n<=1 and Decimal(str(n))==Decimal(str(n)).quantize(Decimal('.0001')) for n in row))
            self.assertEqual(len(m['weight_patch']['value_weights']),30)
            self.assertTrue(all(0<=n<=1 for n in m['weight_patch']['value_weights'].values()))

    def test_bad_weights_and_illegal_witness_rejected(self):
        with self.assertRaises(AssertionError):to_row([0,0,0,0,0])
        with self.assertRaises(AssertionError):to_row([-.1,.2,.3,.3,.3])
        with self.assertRaises(AssertionError):parse('.4 .2 .2 .1 .1|-|no witness',5)
        with self.assertRaises(AssertionError):parse('.4 .2 .2 .1 .1|8|foreign witness',5)

    def test_sequential_global_signatures_and_collision_guard(self):
        self.assertEqual([a['after_major'] for a in self.result['sequential_audits']],IDS)
        for a in self.result['sequential_audits']:
            self.assertEqual(a['active_count'],202)
            self.assertEqual(a['collisions_25_25'],[])
        broken=copy.deepcopy(self.catalog)
        byid={m['id']:m for m in broken}
        byid[166]['strategy_weights']=copy.deepcopy(byid[169]['strategy_weights'])
        with self.assertRaises(AssertionError):global_audit(broken,[166,169])

    def test_semantic_peers_have_owned_full_witnesses(self):
        lookup={m['id']:m for m in self.catalog}
        for major in self.result['majors']:
            for peer in major['semantic_neighbors']:
                self.assertIn(peer['own_witness']['code'],lookup[major['id']]['micro_motive_codes'])
                self.assertIn(peer['peer_witness']['code'],lookup[peer['peer_id']]['micro_motive_codes'])
                self.assertTrue(peer['relationship'])
                if major['id'] in [167,168,170]:self.assertEqual(peer['profile_basis'],'EXISTING_PROFILE_NOT_REWEIGHTED')

    def test_high_agreement_not_hidden_or_artificially_tuned(self):
        pairs={(p['a'],p['b'],p['agree']) for p in self.result['high_agreement_rereads']}
        self.assertEqual(pairs,{(164,166,22),(165,169,20)})
        for p in self.result['high_agreement_rereads']:
            self.assertEqual(p['decision'],'HOLD_FOR_SUPERVISOR_CONTENT_REVIEW_NO_ARTIFICIAL_DECORRELATION')
            self.assertEqual(len(p['agreements'])+len(p['differences']),25)
            self.assertEqual(p['agreements_with_any_equal'],6)
            self.assertEqual(len(p['full_motives_a']),7)
            self.assertEqual(len(p['full_motives_b']),7)
            for d in p['agreements']+p['differences']:
                self.assertIsNotNone(d['rationale_a']);self.assertIsNotNone(d['rationale_b'])

    def test_critical_strategy_decisions_not_based_on_profession(self):
        for major in self.result['majors']:
            if 'weight_patch' not in major:continue
            rows=major['weight_patch']['strategy_weights']
            winner=lambda i:rows[i-1].index(max(rows[i-1]))
            self.assertEqual(winner(21),0)
            self.assertEqual(winner(23),1)
            self.assertEqual(winner(25),3) # no fabricated rescue/actual human outcome
            self.assertNotEqual(winner(9),4)
            self.assertEqual(len(set(rows[13])),1) # no emergency inference

    def test_reproducible_artifacts_and_applied_data_match(self):
        a=outputs();b=outputs();self.assertEqual(a,b)
        for path,text in a[3].items():self.assertEqual(path.read_text(),text)
        for path,wanted in [('majors_database_v2.json',self.catalog),('docs/data/micro_motives.json',self.motives),('micro_motives.json',self.motives)]:
            self.assertEqual(json.loads((ROOT/path).read_text()),wanted)
        self.assertEqual((ROOT/'micro_motives.json').read_bytes(),(ROOT/'docs/data/micro_motives.json').read_bytes())

    def test_protected_files_and_gates_untouched(self):
        for path in ['dark_horse_engine_v2.py','school_branches_v2.json','value_poles_v2.json','docs/data/questions_v2.json','reference_data_sync_audit.py']:
            self.assertEqual((ROOT/path).read_bytes(),gitbytes(BASE,path))
        changed=subprocess.check_output(['git','diff','--name-only',BASE],cwd=ROOT,text=True).splitlines()
        allowed={'majors_database_v2.json','docs/data/micro_motives.json','micro_motives.json'}
        for p in changed:self.assertTrue(p in allowed or p.startswith('docs/weight-review/'))


if __name__=='__main__':
    unittest.main()
