import copy
import json
import unittest
from decimal import Decimal

from finalize_dh013_batch1 import ROOT, S_TEXT, audit, build, parse, read_base


class FinalProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet, cls.catalog, cls.motives, cls.proposal = build()

    def test_exact_five_majors_and_only_weight_fields(self):
        baseline = read_base('majors_database_v2.json')
        changed = []
        for old, new in zip(baseline,self.catalog):
            self.assertEqual(old['id'],new['id'])
            fields = {k for k in old if old[k] != new[k]}
            if fields:
                changed.append(new['id'])
                self.assertEqual(fields,{'strategy_weights','value_weights'})
        self.assertEqual(changed,[161,162,163,164,165])
        self.assertEqual(len(baseline),len(self.catalog))

    def test_35_motive_edits_no_codes_or_metadata_changed(self):
        baseline = read_base('docs/data/micro_motives.json')
        changes = 0
        for old,new in zip(baseline,self.motives):
            self.assertEqual(old['code'],new['code'])
            if old != new:
                changes += 1
                self.assertEqual({k for k in old if old[k] != new[k]},{'description_fa'})
        self.assertEqual(changes,35)
        self.assertEqual(len(self.motives),1393)

    def test_all_rows_and_full_value_keys(self):
        for major in self.proposal['major_patches']:
            self.assertEqual(len(major['strategy_weights']),25)
            for row in major['strategy_weights']:
                self.assertEqual(len(row),5)
                self.assertEqual(sum(Decimal(str(x)) for x in row),1)
                self.assertTrue(all(0<=x<=1 for x in row))
                self.assertTrue(all(Decimal(str(x))==Decimal(str(x)).quantize(Decimal('.0001')) for x in row))
            self.assertEqual(set(major['value_weights']),{f'Q{i}{s}' for i in range(1,16) for s in 'AB'})
            self.assertTrue(all(0<=x<=1 for x in major['value_weights'].values()))

    def test_equal_policy_and_required_review(self):
        for c in self.proposal['checks']:
            self.assertLessEqual(c['equal_s_count'],6)
            self.assertTrue(c['requires_batch_supervisor_approval'])
            expected=[10,12,17,19,20] if c['major_id']==163 else [10,12,14,17,19,20]
            self.assertEqual(c['equal_s'],expected)
            self.assertEqual(c['sequential_global_audit']['active_count'],202)
            self.assertEqual(c['sequential_global_audit']['collisions'],[])

    def test_full_question_options_and_same_major_witnesses(self):
        own={m['id']:{n['code']:n['proposed'] for n in m['motives']} for m in self.packet['majors']}
        evidence=self.proposal['evidence']
        self.assertEqual(sum(e['layer']=='S' for e in evidence),125)
        self.assertEqual(sum(e['layer']=='V' for e in evidence),75)
        for e in evidence:
            self.assertEqual(len(e['question']['options']),5 if e['layer']=='S' else 2)
            if len(set(e['weights']))>1:
                self.assertTrue(e['witnesses'])
            for w in e['witnesses']:
                self.assertEqual(w['text'],own[e['major_id']][w['code']])
            self.assertFalse(e['empirically_validated'])

    def test_critical_questions_and_global_collision_guard(self):
        patches={m['id']:m for m in self.proposal['major_patches']}
        for mid,m in patches.items():
            winner=lambda q:m['strategy_weights'][q-1].index(max(m['strategy_weights'][q-1]))
            self.assertEqual(winner(21),2 if mid==163 else 0)
            self.assertEqual(winner(25),3 if mid==164 else 0)
            self.assertNotEqual(winner(9),4)
        self.assertEqual(self.proposal['global_audit']['pairs_20_24'],[])
        broken=copy.deepcopy(self.catalog)
        broken[161]['strategy_weights']=copy.deepcopy(broken[160]['strategy_weights'])
        with self.assertRaises(AssertionError):
            audit(broken,range(161,166))

    def test_semantic_neighbors_have_real_owned_witnesses(self):
        lookup={m['id']:m for m in self.catalog}
        for mid,peers in self.proposal['semantic_neighbors'].items():
            for p in peers:
                self.assertIn(p['own_witness']['code'],lookup[mid]['micro_motive_codes'])
                self.assertIn(p['peer_witness']['code'],lookup[p['peer_id']]['micro_motive_codes'])
                self.assertTrue(-1<=p['pearson_informational_only']<=1)

    def test_applied_files_match_and_remain_synchronized(self):
        for path,wanted in [('majors_database_v2.json',self.catalog),('docs/data/micro_motives.json',self.motives),('micro_motives.json',self.motives)]:
            self.assertEqual(json.loads((ROOT/path).read_text()),wanted)

    def test_reproducible_and_bad_sum_rejected(self):
        self.assertEqual(build(),build())
        with self.assertRaises(AssertionError):
            parse('.2 .2 .2 .2 .3|1|invalid sum',5)
        for text in S_TEXT.values():
            self.assertEqual(len(parse(text,5)),25)


if __name__=='__main__':
    unittest.main()
