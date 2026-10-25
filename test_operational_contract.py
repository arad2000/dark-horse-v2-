from __future__ import annotations

import math
import unittest

from operational_contract import validate_branch_payload, validate_discovery_payload, validate_scores


class OperationalContractTests(unittest.TestCase):
    def test_fit_score_alias_is_range_checked(self):
        with self.assertRaises(ValueError):
            validate_discovery_payload([{"major_id": 1, "fit_score": 101.0}])

    def test_average_score_alias_is_range_checked(self):
        with self.assertRaises(ValueError):
            validate_branch_payload([{"branch_name": "A", "average_score": -0.1}])

    def test_nested_individuality_fit_is_range_checked(self):
        with self.assertRaises(ValueError):
            validate_discovery_payload(
                [{"major_id": 1, "individuality_fit": {"score": 101.0}}]
            )

    def test_non_finite_values_are_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_scores({"fit_score": value})


if __name__ == "__main__":
    unittest.main(verbosity=2)
