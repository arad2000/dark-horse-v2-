"""Read-only DH-013 7A audit; no weights are generated or applied here.

Run: python -m unittest discover -s docs/weight-review -p test_dh013_batch7a.py -v
The prospective deploy merge tree preserves deploy's existing batch 1–6 work
when this fixed work branch originated on main. merge-tree creates only Git
objects: it does not merge a PR, update a ref, or check out runtime files.
B7A_TREE may select a precomputed staged prospective tree before committing.
"""
import ast
import copy
import itertools
import json
import math
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = 'd56c1c4e4cb6e23badad6c843d0d1560d7db2b4f'
IDS = [203, 204, 205, 208, 209, 210]
REPORT = 'docs/weight-review/DH013_BATCH7A_203_204_205_208_209_210.md'
RUNTIME = {'majors_database_v2.json', 'micro_motives.json',
           'docs/data/micro_motives.json'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def data(rev, path):
    return json.loads(git('show', f'{rev}:{path}'))


def signature(m):
    return tuple(r.index(max(r)) for r in m['strategy_weights'])


def flags(majors):
    active = [m for m in majors if m['motive_driven']]
    assert len(active) == 202
    return [(a['id'], b['id'], sum(x == y for x, y in
            zip(signature(a), signature(b))))
            for a, b in itertools.combinations(active, 2)
            if sum(x == y for x, y in zip(signature(a), signature(b))) >= 20]


class Batch7A(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = os.environ.get('B7A_TREE') or git(
            'merge-tree', '--write-tree', BASE, 'HEAD').splitlines()[0]
        cls.before = data(BASE, 'majors_database_v2.json')
        cls.after = data(cls.tree, 'majors_database_v2.json')
        cls.old = {m['id']: m for m in cls.before}
        cls.new = {m['id']: m for m in cls.after}
        cls.old_mm = data(BASE, 'micro_motives.json')
        cls.new_mm = data(cls.tree, 'micro_motives.json')
        cls.old_codes = {m['code']: m for m in cls.old_mm}
        cls.new_codes = {m['code']: m for m in cls.new_mm}
        cls.allowed = {c for mid in IDS for c in cls.old[mid]['micro_motive_codes']}
        cls.text = git('show', cls.tree + ':' + REPORT)
        body = cls.text.split('## ۴.')[0]
        cls.s = [(ast.literal_eval(raw), ast.literal_eval(w)) for raw, w in
                 re.findall(r'- RAW: `([^`]+)`؛ وزن: `([^`]+)`', body)]
        cls.v = [ast.literal_eval(w) for w in
                 re.findall(r'- A/B مستقل: `([^`]+)`', body)]

    def test_exact_major_scope(self):
        changed = [m['id'] for m in self.after if m != self.old[m['id']]]
        self.assertEqual(changed, IDS)

    def test_totals_and_inactive(self):
        self.assertEqual(len(self.after), 230)
        self.assertEqual(sum(m['motive_driven'] for m in self.after), 202)
        self.assertEqual(sum(not m['motive_driven'] for m in self.after), 28)

    def test_only_two_fields_of_selected_majors(self):
        for mid in IDS:
            diff = {k for k in self.old[mid] if self.old[mid][k] != self.new[mid][k]}
            self.assertEqual(diff, {'strategy_weights', 'value_weights'})

    def test_all_other_224_whole_records_frozen(self):
        for mid, m in self.old.items():
            if mid not in IDS:
                self.assertEqual(m, self.new[mid], mid)

    def test_historical_and_inactive_frozen(self):
        for mid, m in self.old.items():
            if mid <= 160 or not m['motive_driven']:
                self.assertEqual(m, self.new[mid], mid)

    def test_report_150_s_and_180_poles(self):
        self.assertEqual(len(self.s), 150)
        self.assertEqual(len(self.v), 90)
        for i, mid in enumerate(IDS):
            self.assertEqual([w for _, w in self.s[i*25:(i+1)*25]],
                             self.new[mid]['strategy_weights'])
            expected = {f'Q{n}{a}': self.v[i*15+n-1][j]
                        for n in range(1, 16) for j, a in enumerate('AB')}
            self.assertEqual(expected, self.new[mid]['value_weights'])

    def test_normalization_and_residual_to_max_raw(self):
        for raw, w in self.s:
            self.assertEqual(len(w), 5)
            self.assertTrue(all(math.isfinite(x) and 0 <= x <= 1 for x in w))
            self.assertAlmostEqual(sum(w), 1, places=8)
            self.assertTrue(all(round(x, 4) == x for x in w))
            if raw is None:
                self.assertEqual(w, [.2]*5)
            else:
                expected = [round(x/sum(raw), 4) for x in raw]
                k = max(range(5), key=raw.__getitem__)
                expected[k] = round(expected[k]+round(1-sum(expected), 4), 4)
                self.assertEqual(w, expected)

    def test_equal_gate_for_every_written_id(self):
        for mid in IDS:
            self.assertEqual(sum(r == [.2]*5 for r in
                                 self.new[mid]['strategy_weights']), 6)

    def test_values_independent_not_pair_normalized(self):
        keys = {f'Q{n}{a}' for n in range(1, 16) for a in 'AB'}
        for mid in IDS:
            v = self.new[mid]['value_weights']
            self.assertEqual(set(v), keys)
            self.assertTrue(all(math.isfinite(x) and 0 <= x <= 1 for x in v.values()))
            self.assertTrue(any(abs(v[f'Q{n}A']+v[f'Q{n}B']-1) > .01
                                for n in range(1, 16)))
            self.assertEqual([v['Q8A'], v['Q8B']], [.5, .5])

    def test_exact_42_description_changes_only(self):
        changed = {c for c in self.old_codes if self.old_codes[c] != self.new_codes[c]}
        self.assertEqual(changed, self.allowed)
        self.assertEqual(len(changed), 42)
        self.assertEqual(set(self.old_codes), set(self.new_codes))
        for c in changed:
            diff = {k for k in self.old_codes[c]
                    if self.old_codes[c][k] != self.new_codes[c][k]}
            self.assertEqual(diff, {'description_fa'})

    def test_authored_labels_and_full_quotes(self):
        for c in self.allowed:
            old = self.old_codes[c]['description_fa']
            new = self.new_codes[c]['description_fa']
            self.assertTrue(new.startswith('پیشنهاد نویسنده — '), c)
            self.assertIn('- قبل: ' + old, self.text)
            self.assertIn('- تازه: ' + new, self.text)

    def test_root_and_docs_motive_mirror(self):
        self.assertEqual(git('show', self.tree + ':micro_motives.json'),
                         git('show', self.tree + ':docs/data/micro_motives.json'))

    def test_runtime_file_allowlist(self):
        changed = set(git('diff', '--name-only', BASE, self.tree).splitlines())
        self.assertEqual({p for p in changed if not p.startswith('docs/weight-review/')},
                         RUNTIME)

    def test_final_global_scan(self):
        fs = flags(self.after)
        self.assertEqual(len(fs), 157)
        self.assertFalse(any(n == 25 for _, _, n in fs))
        self.assertEqual(sum(a in IDS or b in IDS for a, b, _ in fs), 24)

    def test_each_incremental_global_scan(self):
        state = copy.deepcopy(self.before)
        for mid in IDS:
            state = [copy.deepcopy(self.new[mid]) if m['id'] == mid else m
                     for m in state]
            self.assertFalse(any(n == 25 for _, _, n in flags(state)), mid)

    def test_hazard_questions_explicit_policy(self):
        for mid in IDS:
            self.assertEqual(self.new[mid]['strategy_weights'][8].index(
                max(self.new[mid]['strategy_weights'][8])), 0)
        for mid in [203, 204, 208]:
            self.assertEqual(signature(self.new[mid])[24], 0)
        for mid in [205, 209, 210]:
            self.assertEqual(signature(self.new[mid])[24], 3)
            self.assertEqual(self.new[mid]['strategy_weights'][13], [.2]*5)
        self.assertEqual(signature(self.new[203])[13], 0)
        self.assertEqual(signature(self.new[204])[13], 1)
        self.assertEqual(signature(self.new[208])[13], 0)

    def test_batch7b_unmodified(self):
        for mid in [211, 212, 213, 214, 219, 220]:
            self.assertEqual(self.old[mid], self.new[mid])
            for c in self.old[mid]['micro_motive_codes']:
                self.assertEqual(self.old_codes[c], self.new_codes[c])


if __name__ == '__main__':
    unittest.main()
