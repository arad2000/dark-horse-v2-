"""Batch 5 invariants: scope, withholding, own evidence and global audit."""
import copy
import importlib.util
import itertools
from pathlib import Path
import unittest
from unittest.mock import patch

PATH=Path(__file__).with_name('dh013_batch5_182_186.py')
spec=importlib.util.spec_from_file_location('batch5',PATH)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class Batch5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet,cls.majors,cls.motives=b.build()
        cls.old=b.baseline('majors_database_v2.json')

    def test_next_five_active_skip_179(self):
        self.assertEqual([m['id'] for m in self.old if m['id']>181 and m['motive_driven']][:5],[182,183,184,185,186])
        self.assertFalse(next(m for m in self.majors if m['id']==179)['motive_driven'])

    def test_225_other_major_objects_unchanged(self):
        old=[m for m in self.old if m['id'] not in b.IDS]
        self.assertEqual(len(old),225)
        self.assertEqual(old,[m for m in self.majors if m['id'] not in b.IDS])

    def test_only_two_eligible_sv_changes_all_metadata_unchanged(self):
        self.assertEqual([a['id'] for a,z in zip(self.old,self.majors) if a!=z],[182,185])
        for a,z in zip(self.old,self.majors):
            self.assertLessEqual({k for k in a if a[k]!=z[k]},{'strategy_weights','value_weights'})

    def test_batch4_records_and_motives_preserved(self):
        now={m['id']:m for m in self.majors};old={m['id']:m for m in self.old}
        before={m['code']:m for m in b.baseline('micro_motives.json')};after={m['code']:m for m in self.motives}
        for mid in [176,177,178,180,181]:
            self.assertEqual(now[mid],old[mid])
            for c in old[mid]['micro_motive_codes']:self.assertEqual(before[c],after[c])

    def test_35_motive_descriptions_only(self):
        before=b.baseline('micro_motives.json');changes=[]
        allowed={t['code'] for p in self.packet['proposals'] for t in p['texts']}
        self.assertEqual(len(before),len(self.motives))
        for a,z in zip(before,self.motives):
            if a!=z:
                changes.append(a['code']);self.assertEqual({k for k in a if a[k]!=z[k]},{'description_fa'})
        self.assertEqual(set(changes),allowed);self.assertEqual(len(changes),35)

    def test_flags_and_major_count_unchanged(self):
        self.assertEqual(len(self.majors),230)
        self.assertEqual(sum(m['motive_driven'] for m in self.majors),202)
        self.assertEqual([m['id'] for m in self.old if not m['motive_driven']], [m['id'] for m in self.majors if not m['motive_driven']])

    def test_125_normalized_rows(self):
        for p in self.packet['proposals']:
            self.assertEqual(len(p['strategies']),25)
            for r in p['strategies']:
                self.assertEqual(len(r['weights']),5)
                self.assertAlmostEqual(sum(r['weights']),1,places=4)
                self.assertTrue(all(0<=x<=1 and round(x,4)==x for x in r['weights']))

    def test_residual_on_largest_raw(self):
        raw=[1,2,7,3,4]
        rounded=[round(v/sum(raw),4) for v in raw];out=b.normalize(raw)
        for i in [0,1,3,4]:self.assertEqual(rounded[i],out[i])
        self.assertAlmostEqual(sum(out),1,places=4)

    def test_150_independent_value_keys(self):
        for p in self.packet['proposals']:
            self.assertEqual(len(p['values']),15)
            self.assertEqual(set(p['value_weights']),{f'Q{i}{a}' for i in range(1,16) for a in 'AB'})
            self.assertTrue(all(0<=x<=1 for x in p['value_weights'].values()))
            self.assertTrue(any(sum(r['weights'])!=1 for r in p['values']))

    def test_full_own_text_witnesses(self):
        for p in self.packet['proposals']:
            own={t['code']:t['after'] for t in p['texts']}
            for r in p['strategies']+p['values']:
                self.assertTrue(r['reason'])
                for w in r['full_witnesses']:self.assertEqual(own[w['code']],w['text'])
                if r['status']=='EXPERT_TRANSFER':self.assertTrue(r['full_witnesses'])

    def test_equal_counts_and_reasons(self):
        self.assertEqual([p['equal'] for p in self.packet['proposals']],[6,8,9,6,8])
        for p in self.packet['proposals']:
            self.assertEqual(p['write_weights'],p['equal']<=6)
            for r in p['strategies']:
                if r['status']=='EQUAL_NO_EVIDENCE':
                    self.assertEqual(r['weights'],[.2]*5);self.assertTrue(r['reason'])

    def test_no_silence_or_recovery_from_precision(self):
        for p in self.packet['proposals']:
            for n in [19,20]:self.assertEqual(p['strategies'][n-1]['status'],'EQUAL_NO_EVIDENCE')

    def test_no_beauty_to_all_effort_or_direct_help(self):
        for mid in [184,185]:
            p=next(p for p in self.packet['proposals'] if p['id']==mid)
            self.assertEqual(p['strategies'][24]['status'],'EQUAL_NO_EVIDENCE')

    def test_pressure_witness_not_inferred_from_title(self):
        for p in self.packet['proposals']:
            if p['id']==185:
                r=p['strategies'][13]
                self.assertEqual(r['weights'].index(max(r['weights'])),0)
                self.assertIn('چند لحظه',r['full_witnesses'][0]['text'])
            else:self.assertEqual(p['strategies'][13]['status'],'EQUAL_NO_EVIDENCE')

    def test_withhold_above_six_integration(self):
        # Mock only S182 and audit in this unit test, never the real runtime/gates.
        rows=b.S[182].strip().splitlines();rows[0]='-|1|شاهد جهت‌دار آزمایشاً حذف شده است.'
        with patch.dict(b.S,{182:'\n'.join(rows)}),patch.object(b,'scan',return_value=[]):
            packet,majors,_=b.build()
        p=next(p for p in packet['proposals'] if p['id']==182)
        self.assertEqual(p['equal'],7);self.assertFalse(p['write_weights'])
        self.assertEqual(next(m for m in majors if m['id']==182),next(m for m in self.old if m['id']==182))

    def test_global_scan_all_202_no_25_collision(self):
        self.assertEqual(self.packet['runtime_scan'],b.scan(self.majors))
        for key in ['baseline_scan','runtime_scan','hypothetical_scan']:
            self.assertFalse(any(f['agreement']==25 for f in self.packet[key]))

    def test_unrelated_inherited_flags_not_hidden_or_changed(self):
        def outside(fs):return [f for f in fs if not set(f['ids'])&set(b.IDS)]
        self.assertEqual(outside(self.packet['baseline_scan']),outside(self.packet['runtime_scan']))
        self.assertEqual(len(self.packet['baseline_scan']),100)

    def test_all_21_hypothetical_flags_complete_reread(self):
        flags=[f for f in self.packet['hypothetical_scan'] if set(f['ids'])&set(b.IDS)]
        rr=self.packet['high_agreement_rereads']
        self.assertEqual(len(rr),21)
        self.assertEqual({tuple(f['ids']) for f in flags},{tuple(f['ids']) for f in rr})
        for f in rr:
            self.assertTrue(f['explanation'])
            self.assertEqual(len(f['agreement_reread']),f['agreement'])
            self.assertTrue(all(len(s['texts'])==7 for s in f['both_sides']))
            self.assertEqual(f['directional_only_agreement']+len(f['flat_agreements'])+len(f['one_side_flat_agreements']),f['agreement'])
            for r in f['agreement_reread']:
                self.assertEqual(len(r['sides']),2)
                self.assertTrue(all(s['reason'] for s in r['sides']))

    def test_withheld_three_full_major_records_preserved(self):
        old={m['id']:m for m in self.old};new={m['id']:m for m in self.majors}
        for mid in [183,184,186]:self.assertEqual(old[mid],new[mid])

    def test_no_inactive_skip_in_selection_interval(self):
        self.assertEqual(self.packet['skipped_inactive_ids'],[])
        self.assertFalse(next(m for m in self.majors if m['id']==179)['motive_driven'])

    def test_runtime_vs_hypothetical_not_confused(self):
        real=[f for f in self.packet['runtime_scan'] if set(f['ids'])&set(b.IDS)]
        hypo=[f for f in self.packet['hypothetical_scan'] if set(f['ids'])&set(b.IDS)]
        self.assertEqual(len(real),7);self.assertEqual(len(hypo),21)
        self.assertTrue(all(not(set(f['ids'])&{183,184,186}) for f in real))
        self.assertEqual(next(f['agreement'] for f in real if f['ids']==[177,185]),23)

    def test_content_peers_predeclared_not_numeric_ranking(self):
        for p in self.packet['proposals']:self.assertEqual(p['content_peers'],b.PEERS[p['id']])
        self.assertTrue(all(c['active'] for c in self.packet['content_peer_checks']))
        self.assertTrue(all(len(c['full_peer_texts'])==7 for c in self.packet['content_peer_checks']))

    def test_source_and_provenance_not_empirical_claim(self):
        self.assertFalse(self.packet['empirical_calibration_performed'])
        self.assertFalse(self.packet['independent_reviews_completed'])
        before={m['code']:m['description_fa'] for m in b.baseline('micro_motives.json')}
        for p in self.packet['proposals']:
            for t in p['texts']:
                self.assertEqual(t['before'],before[t['code']]);self.assertIn('پیشنهاد نویسنده',t['provenance'])

    def test_reproduction_and_synchronized_copies(self):
        self.assertEqual(b.STEM.with_suffix('.json').read_text(),b.serial(self.packet))
        self.assertEqual(b.STEM.with_suffix('.md').read_text(),b.render(self.packet))
        self.assertEqual(b.load('majors_database_v2.json'),self.majors)
        self.assertEqual(b.load('micro_motives.json'),self.motives)
        self.assertEqual((b.ROOT/'micro_motives.json').read_bytes(),(b.ROOT/'docs/data/micro_motives.json').read_bytes())

if __name__=='__main__':unittest.main()
