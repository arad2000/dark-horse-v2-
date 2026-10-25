"""Scope, traceability and withholding regressions for the draft batch."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

PATH=Path(__file__).with_name('dh013_batch3_171_175.py')
spec=importlib.util.spec_from_file_location('batch3',PATH)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class Batch3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.packet,cls.majors,cls.motives=b.build()

    def test_next_five_active(self):
        self.assertEqual([m['id'] for m in b.baseline('majors_database_v2.json') if m['id']>170 and m['motive_driven']][:5],b.IDS)

    def test_225_other_records_unchanged(self):
        old=b.baseline('majors_database_v2.json')
        self.assertEqual([m for m in old if m['id'] not in b.IDS],[m for m in self.majors if m['id'] not in b.IDS])
        self.assertEqual(len([m for m in old if m['id'] not in b.IDS]),225)

    def test_only_eligible_sv_changes_metadata_preserved(self):
        old=b.baseline('majors_database_v2.json')
        changed=[]
        for x,y in zip(old,self.majors):
            if x!=y:
                changed.append(x['id'])
                self.assertLessEqual({k for k in x if x[k]!=y[k]},{'strategy_weights','value_weights'})
        self.assertEqual(changed,[171,174])

    def test_withheld_full_records_unchanged(self):
        old={m['id']:m for m in b.baseline('majors_database_v2.json')}
        for mid in [172,173,175]:self.assertEqual(next(m for m in self.majors if m['id']==mid),old[mid])

    def test_policy_not_hardcoded_ids(self):
        rows=copy.deepcopy(self.packet['proposals'][0]['strategies'])
        self.assertTrue(b.permitted(rows))
        for r in rows:
            if len(set(r['weights']))!=1:r['weights']=[.2]*5;break
        self.assertEqual(b.equal_count(rows),7)
        self.assertFalse(b.permitted(rows))

    def test_motive_scope_only_35_descriptions(self):
        old=b.baseline('micro_motives.json')
        codes={t['code'] for p in self.packet['proposals'] for t in p['texts']}
        changed=[]
        for x,y in zip(old,self.motives):
            if x!=y:
                changed.append(x['code']);self.assertEqual(set(k for k in x if x[k]!=y[k]),{'description_fa'})
        self.assertEqual(set(changed),codes);self.assertEqual(len(changed),35)

    def test_active_flags_untouched(self):
        self.assertEqual(sum(m['motive_driven'] for m in self.majors),202)
        self.assertEqual(len(self.majors),230)

    def test_125_rows_normalized(self):
        for p in self.packet['proposals']:
            self.assertEqual(len(p['strategies']),25)
            for r in p['strategies']:
                self.assertEqual(len(r['weights']),5)
                self.assertAlmostEqual(sum(r['weights']),1,places=4)
                self.assertTrue(all(0<=x<=1 for x in r['weights']))

    def test_150_value_keys_independent(self):
        for p in self.packet['proposals']:
            self.assertEqual(set(p['value_weights']),{f'Q{i}{a}' for i in range(1,16) for a in 'AB'})
            self.assertTrue(all(0<=x<=1 for x in p['value_weights'].values()))
            self.assertTrue(any(sum(r['weights'])!=1 for r in p['values']))

    def test_own_full_witnesses(self):
        for p in self.packet['proposals']:
            own={t['code']:t['after'] for t in p['texts']}
            for r in p['strategies']+p['values']:
                self.assertTrue(r['reason'])
                for w in r['full_witnesses']:self.assertEqual(own[w['code']],w['text'])
                if r['status']=='EXPERT_TRANSFER':self.assertTrue(r['full_witnesses'])

    def test_equal_reasons_and_flat_rows(self):
        self.assertEqual([p['equal'] for p in self.packet['proposals']],[6,8,9,6,9])
        for p in self.packet['proposals']:
            for r in p['strategies']:
                if r['status']=='EQUAL_NO_EVIDENCE':self.assertEqual(r['weights'],[.2]*5)

    def test_inherited_global_flags_not_hidden(self):
        self.assertEqual(self.packet['runtime_scan'],self.packet['baseline_scan'])
        self.assertEqual(len(self.packet['baseline_scan']),94)

    def test_signatures_global_no_25_collision(self):
        for key in ['runtime_scan','hypothetical_scan']:
            self.assertFalse(any(f['agreement']==25 for f in self.packet[key]))

    def test_high_flags_have_both_sides_and_each_question(self):
        flagged=[f for f in self.packet['hypothetical_scan'] if set(f['ids'])&set(b.IDS)]
        reread=self.packet['high_agreement_rereads']
        self.assertEqual(len(flagged),len(reread))
        for f in reread:
            self.assertEqual(len(f['agreement_reread']),f['agreement'])
            self.assertEqual(len(f['both_sides']),2)
            self.assertTrue(f['explanation'])
            self.assertTrue(all(len(s['texts'])==7 for s in f['both_sides']))

    def test_content_peers_not_ranked_and_active(self):
        for p in self.packet['proposals']:self.assertEqual(p['content_peers'],b.PEERS[p['id']])
        self.assertTrue(all(x['active'] for x in self.packet['content_peer_checks']))

    def test_originals_and_added_texts_provenance(self):
        old={m['code']:m['description_fa'] for m in b.baseline('micro_motives.json')}
        for p in self.packet['proposals']:
            for t in p['texts']:
                self.assertEqual(t['before'],old[t['code']]);self.assertIn('پیشنهاد نویسنده',t['provenance'])

    def test_reproducible_artifacts_and_runtime(self):
        self.assertEqual(b.STEM.with_suffix('.json').read_text(),b.serial(self.packet))
        self.assertEqual(b.STEM.with_suffix('.md').read_text(),b.render(self.packet))
        self.assertEqual(b.load('majors_database_v2.json'),self.majors)
        self.assertEqual(b.load('micro_motives.json'),self.motives)
        self.assertEqual((b.ROOT/'micro_motives.json').read_bytes(),(b.ROOT/'docs/data/micro_motives.json').read_bytes())

if __name__=='__main__':unittest.main()
