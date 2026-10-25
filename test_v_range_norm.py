"""Range-V contract tests; reference weights are never modified."""
import random
import unittest
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
        w = {'Q1A': .9, 'Q1B': .1, 'Q2A': .52, 'Q2B': .5}
        self.assertAlmostEqual(self.engine._compute_v_score(['Q1A', 'Q2B'], w)[0], .8 / .82)

    def test_epsilon_boundary_and_zero_denominator(self):
        for delta, informative in ((.019, 0), (.02, 1), (.021, 1), (0, 0)):
            r = self.engine._compute_v_result(['Q1A'], {'Q1A': .5 + delta, 'Q1B': .5})
            self.assertEqual(r['coverage']['discriminative_answered'], informative)
            if not informative:
                self.assertIsNone(r['score'])
                self.assertEqual(r['status'], 'no_discriminative_evidence')

    def test_invalid_duplicate_conflicting_and_missing(self):
        w = {'Q1A': .8, 'Q1B': .2}
        for inputs, answered in ((['Q1A', 'Q1A'], 1), (['Q1A', 'Q1B'], 0),
                                 (['', None, 'Q16A', 'Q01A'], 0)):
            r = self.engine._compute_v_result(inputs, w)
            self.assertEqual(r['coverage']['answered'], answered)
        for bad in (float('nan'), float('inf'), -1, 2, None):
            self.assertIsNone(self.engine._compute_v_score(['Q1A'], {'Q1A': bad, 'Q1B': .2})[0])

    def test_coverage_does_not_penalize_score(self):
        w = {f'Q{i}{side}': (.8 if side == 'A' else .2) for i in range(1, 16) for side in 'AB'}
        for n in (1, 5, 15):
            r = self.engine._compute_v_result([f'Q{i}A' for i in range(1, n+1)], w)
            self.assertAlmostEqual(r['score'], 1)
            self.assertEqual(r['coverage']['answered'], n)

    def test_public_incomplete_not_silent_zero_or_best_branch(self):
        result = self.engine.recommend_school_branch([], {}, {})
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(len(result['incomplete_assessments']), 4)
        self.assertEqual(result['recommended_branches'], [])
        self.assertIsNone(result['best_branch'])
        self.assertEqual(result['method']['version'], '3.1-v-range-norm')


if __name__ == '__main__':
    unittest.main()
