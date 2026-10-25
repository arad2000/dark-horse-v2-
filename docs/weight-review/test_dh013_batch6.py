"""Batch 6 scope, honest withholding, own evidence, provenance and scan tests."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

path=Path(__file__).with_name('dh013_batch6_187_189_199_201_202.py')
spec=importlib.util.spec_from_file_location('batch6',path)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class Batch6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p,cls.majors,cls.motives=b.build()
        cls.old=b.baseline('majors_database_v2.json')

    def test_next_five_active(self):
        self.assertEqual([m['id'] for m in self.old if m['id']>186 and m['motive_driven']][:5],b.IDS)
        self.assertEqual(b.IDS,[187,189,199,201,202])

    def test_eleven_skips_named_and_preserved(self):
        self.assertEqual([m['id'] for m in self.p['skipped_inactive']],[188,190,191,192,193,194,195,196,197,198,200])
        by={m['id']:m for m in self.majors}
        for m in self.p['skipped_inactive']:
            self.assertEqual(m['name'],by[m['id']]['name']);self.assertFalse(by[m['id']]['motive_driven'])

    def test_active_202_and_28_inactive(self):
        self.assertEqual(len(self.majors),230)
        self.assertEqual(sum(m['motive_driven'] for m in self.majors),202)
        self.assertEqual([m['id'] for m in self.old if not m['motive_driven']],[m['id'] for m in self.majors if not m['motive_driven']])

    def test_all_major_records_unchanged_not_only_flat_rows(self):
        self.assertEqual(self.old,self.majors)
        self.assertEqual((b.ROOT/'majors_database_v2.json').read_bytes(),subprocess.check_output(['git','show',f'{b.BASE}:majors_database_v2.json'],cwd=b.ROOT))
        self.assertEqual(self.p['new_runtime_weights_in_this_draft'],0)
        self.assertEqual(self.p['merged_new_major_count_before_batch'],25)

    def test_equal_counts_and_whole_sv_withholding(self):
        self.assertEqual([p['equal'] for p in self.p['proposals']],[9,9,9,9,10])
        for p in self.p['proposals']:
            self.assertGreater(p['equal'],6);self.assertFalse(p['write_weights'])
            self.assertEqual(p['write_weights'],b.h.permitted(p['strategies']))

    def test_six_allowed_seven_withheld_in_integration(self):
        # Synthetic test data and mock scanner confined to this test. Never
        # mutate a real runtime gate or proposal to obtain permission.
        lines=b.S[187].strip().splitlines()
        flat=[i for i,l in enumerate(lines) if l.startswith('-|')]
        for count,written in [(2,False),(3,True)]:
            rows=lines.copy()
            for i in flat[:count]:rows[i]='.30 .25 .20 .15 .10|1|شاهد مصنوعی فقط در تست مرز، نه پیشنهاد واقعی.'
            with patch.dict(b.S,{187:'\n'.join(rows)}),patch.object(b.h,'scan',return_value=[]):
                p,majors,_=b.build()
            q=next(p for p in p['proposals'] if p['id']==187)
            self.assertEqual(q['equal'],9-count);self.assertEqual(q['write_weights'],written)
            m=next(m for m in majors if m['id']==187);old=next(m for m in self.old if m['id']==187)
            self.assertEqual(m==old,not written)
            if written:self.assertEqual(m['value_weights'],q['value_weights'])

    def test_35_own_descriptions_only(self):
        old=b.baseline('micro_motives.json');allowed={t['code'] for p in self.p['proposals'] for t in p['texts']}
        changes=[]
        for a,z in zip(old,self.motives):
            if a!=z:
                changes.append(a['code']);self.assertEqual({k for k in a if a[k]!=z[k]},{'description_fa'})
        self.assertEqual(len(old),len(self.motives));self.assertEqual(len(changes),35);self.assertEqual(set(changes),allowed)

    def test_prior_five_batches_motives_frozen(self):
        old={m['code']:m for m in b.baseline('micro_motives.json')};new={m['code']:m for m in self.motives}
        for m in self.old:
            if m['id']<=186:
                for c in m['micro_motive_codes']:self.assertEqual(old[c],new[c])

    def test_all_seven_texts_and_author_label(self):
        for p in self.p['proposals']:
            self.assertEqual(len(p['texts']),7)
            for t in p['texts']:
                self.assertNotEqual(t['before'],t['after']);self.assertIn('پیشنهاد نویسنده',t['provenance'])
                self.assertTrue('لذت می‌بری' in t['after'] or 'احساس رضایت' in t['after'])
        self.assertFalse(self.p['empirical_calibration_performed']);self.assertFalse(self.p['independent_review_performed'])

    def test_full_own_witnesses_and_reasons(self):
        for p in self.p['proposals']:
            own={t['code']:t['after'] for t in p['texts']}
            for r in p['strategies']+p['values']:
                self.assertTrue(r['reason'])
                for w in r['full_witnesses']:self.assertEqual(w['text'],own[w['code']])
                if r['status']!='EQUAL_NO_EVIDENCE' and r['motives']:self.assertTrue(r['full_witnesses'])

    def test_125_normalized_rows_four_decimals(self):
        for p in self.p['proposals']:
            self.assertEqual(len(p['strategies']),25)
            for r in p['strategies']:
                self.assertEqual(len(r['weights']),5);self.assertAlmostEqual(sum(r['weights']),1,4)
                self.assertTrue(all(0<=x<=1 and round(x,4)==x for x in r['weights']))
                if r['status']=='EQUAL_NO_EVIDENCE':self.assertEqual(r['weights'],[.2]*5)
                else:self.assertEqual(r['weights'],b.h.normalize(r['raw']))

    def test_residual_on_largest_raw(self):
        raw=[1,2,7,3,4];r=b.h.normalize(raw)
        for i in [0,1,3,4]:self.assertEqual(r[i],round(raw[i]/sum(raw),4))
        self.assertAlmostEqual(sum(r),1,4)

    def test_150_independent_poles(self):
        for p in self.p['proposals']:
            self.assertEqual(len(p['values']),15)
            self.assertEqual(set(p['value_weights']),{f'Q{i}{a}' for i in range(1,16) for a in 'AB'})
            self.assertTrue(all(0<=x<=1 for x in p['value_weights'].values()))
            self.assertTrue(any(sum(r['weights'])!=1 for r in p['values']))
            for i in [8,10,12]:self.assertEqual(p['values'][i-1]['weights'],[.5,.5])

    def test_no_s03_from_two_settings_or_s09_from_precision(self):
        for p in self.p['proposals']:
            for i in [3,9]:self.assertEqual(p['strategies'][i-1]['status'],'EQUAL_NO_EVIDENCE')

    def test_no_law_group_recovery_environment_inferences(self):
        for p in self.p['proposals']:
            for i in [12,16,17,19,20]:self.assertEqual(p['strategies'][i-1]['weights'],[.2]*5)

    def test_pressure_only_explicit_short_time(self):
        for p in self.p['proposals']:
            r=p['strategies'][13]
            if p['id'] in [199,201]:
                self.assertEqual(r['weights'].index(max(r['weights'])),0)
                self.assertTrue(any('پنجره تصمیم کوتاه' in w['text'] or 'چند لحظه' in w['text'] for w in r['full_witnesses']))
            else:self.assertEqual(r['weights'],[.2]*5)

    def test_s25_help_not_beauty_safety_or_all_effort(self):
        for p in self.p['proposals']:
            r=p['strategies'][24]
            if p['id']==187:
                self.assertEqual(r['weights'].index(max(r['weights'])),0)
                self.assertIn('راحت‌تر',r['full_witnesses'][0]['text'])
            else:self.assertEqual(r['weights'],[.2]*5)

    def test_multiple_flight_indicators_not_multiple_projects(self):
        for p in self.p['proposals']:
            if p['id'] in [199,201,202]:self.assertEqual(p['strategies'][20]['weights'],[.2]*5)

    def test_global_scans_202_and_no_25(self):
        self.assertEqual(self.p['scans']['runtime'],b.h.scan(self.majors))
        self.assertEqual(self.p['scans']['runtime'],self.p['scans']['baseline'])
        self.assertEqual(len(self.p['scans']['runtime']),121);self.assertEqual(len(self.p['scans']['hypothetical']),149)
        for fs in self.p['scans'].values():self.assertFalse(any(f['agreement']==25 for f in fs))

    def test_runtime_and_hypothetical_distinct_complete_rereads(self):
        for mode,count in [('runtime',3),('hypothetical',31)]:
            flags=[f for f in self.p['scans'][mode] if set(f['ids'])&set(b.IDS)]
            rr=[r for r in self.p['rereads'] if r['mode']==mode]
            self.assertEqual(len(rr),count);self.assertEqual({tuple(f['ids']) for f in flags},{tuple(f['ids']) for f in rr})
            for f in rr:
                self.assertIn(tuple(f['ids']),b.PAIR_NOTES);self.assertEqual(len(f['rows']),f['agreement'])
                self.assertEqual(f['directional_only']+len(f['flat_agreements'])+len(f['one_side_flat']),f['agreement'])
                self.assertTrue(all(len(s['texts'])==7 for s in f['both_sides']))
                for r in f['rows']:self.assertTrue(all(s['reason'] for s in r['sides']))

    def test_legacy_gap_explicit_not_posthoc_justified(self):
        rows=[r for f in self.p['rereads'] if f['mode']=='runtime' for r in f['rows']]
        for r in rows:
            for side in r['sides']:
                self.assertEqual(side['status'],'LEGACY_ORIGIN_NOT_REVALIDATED');self.assertEqual(side['full_witnesses'],[])
        mm={m['code']:m['description_fa'] for m in self.motives}
        for f in self.p['rereads']:
            for side in f['both_sides']:
                for t in side['texts']:self.assertEqual(t['text'],mm[t['code']])

    def test_open_flags_not_hidden(self):
        real={tuple(f['ids']):f['agreement'] for f in self.p['scans']['runtime']}
        self.assertEqual(real[(182,183)],24);self.assertEqual(real[(177,185)],23)
        f=next(f for f in self.p['rereads'] if f['mode']=='hypothetical' and f['ids']==[189,202])
        self.assertEqual(f['agreement'],24);self.assertEqual(f['directional_only'],14)
        self.assertEqual(len(f['flat_agreements']),9);self.assertEqual(f['one_side_flat'],[21])

    def test_content_peers_predeclared_not_numeric(self):
        for p in self.p['proposals']:self.assertEqual(p['content_peers'],b.PEERS[p['id']])
        self.assertTrue(all(c['active'] and len(c['full_texts'])==7 for c in self.p['peer_checks']))

    def test_full_questions_options_and_poles(self):
        self.assertEqual(len(self.p['strategy_questions']),25);self.assertEqual(len(self.p['value_questions']),15)
        self.assertTrue(all(len(q['options'])==5 for q in self.p['strategy_questions']))
        self.assertTrue(all(len(q['options'])==2 for q in self.p['value_questions']))
        self.assertEqual(len(self.p['value_poles']),30)

    def test_reproduction_and_synchronized_copies(self):
        self.assertEqual(b.STEM.with_suffix('.json').read_text(),b.serial(self.p))
        self.assertEqual(b.STEM.with_suffix('.md').read_text(),b.render(self.p))
        self.assertEqual(json.loads((b.ROOT/'micro_motives.json').read_text()),self.motives)
        self.assertEqual((b.ROOT/'micro_motives.json').read_bytes(),(b.ROOT/'docs/data/micro_motives.json').read_bytes())

if __name__=='__main__':unittest.main()
