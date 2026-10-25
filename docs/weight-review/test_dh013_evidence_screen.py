"""Review-tool tests; deliberately separate from the runtime test suite."""
import json
import unittest

from screen_dh013_batch1_evidence import OUT, REPORT, build, validate_mapping


class EvidenceScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build()
        cls.packet = json.loads(cls.outputs[OUT])

    def test_all_125_questions_are_present_with_five_options(self):
        count = 0
        for major in self.packet['majors']:
            rows = major['strategy_evidence']
            self.assertEqual({r['question']['id'] for r in rows}, {f'S{i:02}' for i in range(1,26)})
            for row in rows:
                self.assertEqual(len(row['question']['options']), 5)
                count += 1
        self.assertEqual(count, 125)

    def test_all_150_value_keys_are_present(self):
        for major in self.packet['majors']:
            keys = [o['code'] for r in major['value_evidence'] for o in r['question']['options']]
            self.assertEqual(len(keys), 30)
            self.assertEqual(set(keys), {f'Q{i}{p}' for i in range(1,16) for p in 'AB'})

    def test_witnesses_are_complete_and_local(self):
        for major in self.packet['majors']:
            motives = {m['code']: m['proposed'] for m in major['motives']}
            for row in major['strategy_evidence'] + major['value_evidence']:
                for witness in row['witnesses']:
                    self.assertEqual(witness['text'], motives[witness['code']])
                if row['status'] == 'EQUAL_NO_EVIDENCE':
                    self.assertTrue(row['reason'])
                    self.assertEqual(row['witnesses'], [])
                else:
                    self.assertTrue(row['witnesses'])

    def test_gate_prevents_any_weight_object(self):
        expected = {161:14, 162:14, 163:18, 164:15, 165:15}
        for major in self.packet['majors']:
            self.assertEqual(major['equal_s_count'], expected[major['id']])
            self.assertGreater(major['equal_s_count'], self.packet['max_equal_s'])
            self.assertFalse(major['weighting_eligible'])
            self.assertFalse(major['weights_emitted'])
            self.assertNotIn('strategy_weights', major)
            self.assertNotIn('value_weights', major)

    def test_invalid_option_and_foreign_witness_are_rejected(self):
        with self.assertRaises(AssertionError):
            validate_mapping([5], [1], {1}, range(5))
        with self.assertRaises(AssertionError):
            validate_mapping([0], [8], {1,2,3,4,5,6,7}, range(5))
        with self.assertRaises(AssertionError):
            validate_mapping([0,0], [1], {1}, range(5))

    def test_deterministic_and_outputs_are_review_only(self):
        self.assertEqual(self.outputs, build())
        self.assertEqual(set(self.outputs), {OUT, REPORT})
        for path in self.outputs:
            self.assertEqual(path.parent.name, 'weight-review')
        self.assertEqual(self.packet['independent_reviews_completed'], 0)


if __name__ == '__main__':
    unittest.main()
