"""Regression tests for the S-score question-denominator contract."""
import unittest

from dark_horse_engine_v2 import DarkHorseEngineV2


class SScoreDenominatorTests(unittest.TestCase):
    def setUp(self):
        # Exercise the pure scoring method without loading production data files.
        self.engine = object.__new__(DarkHorseEngineV2)
        self.engine.trait_map = {}

    @staticmethod
    def weights(question_count=25):
        return [[1.0, 0.0] for _ in range(question_count)]

    def test_one_answer_cannot_create_a_high_s_score(self):
        answers = [0] + [-1] * 24
        score, _ = self.engine._compute_s_score(answers, self.weights())
        self.assertAlmostEqual(score, 1.0 / 25.0)
        self.assertLess(score, 0.10)

    def test_all_unanswered_questions_produce_zero(self):
        score, _ = self.engine._compute_s_score([-1] * 25, self.weights())
        self.assertEqual(score, 0.0)

    def test_full_answer_set_keeps_protocol_scale(self):
        score, _ = self.engine._compute_s_score([0] * 25, self.weights())
        self.assertEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
