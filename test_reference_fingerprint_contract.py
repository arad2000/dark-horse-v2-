"""Offline mutation tests for the dual reference fingerprint contract."""

from __future__ import annotations

import copy
import unittest

from reference_fingerprints import (
    membership_fingerprint,
    scientific_fingerprint,
)


def fixture_snapshot():
    strategy = [
        [0.2, 0.2, 0.2, 0.2, 0.2]
        for _ in range(25)
    ]
    values = {
        f"Q{question}{side}": 0.5
        for question in range(1, 16)
        for side in ("A", "B")
    }
    majors = [{
        # 183 is intentionally in the historical staging-candidate ID set.
        # It is active and weighted on the deployed HEAD, so it must not normalize.
        "id": 183,
        "name": "رشتهٔ آزمایشی",
        "group": "گروه الف",
        "cluster": "A",
        "subgroup": "A1",
        "exam_group": "تجربی",
        "high_school_branch": "علوم تجربی",
        "motive_driven": True,
        "weights_version": "fixture_scoring_v1",
        "micro_motive_codes": ["TEST-001"],
        "strategy_weights": strategy,
        "value_weights": values,
    }]
    branches = [{
        "id": "branch-1",
        "name": "علوم تجربی",
        "group": "نظری",
        "m_score_denom_limit": 30,
        "micro_motive_codes": ["TEST-001"],
        "strategy_weights": copy.deepcopy(strategy),
        "value_weights": copy.deepcopy(values),
        "weights_version": "fixture_branch_v1",
    }]
    motives = [{"code": "TEST-001", "description_fa": "متن آزمایشی"}]
    questions = {
        "layers": {
            "strategies": {
                "questions": [{
                    "id": "S01",
                    "number": 1,
                    "question": "پرسش آزمایشی",
                    "options": [
                        {"index": index, "text": f"گزینه {index}"}
                        for index in range(5)
                    ],
                }]
            }
        }
    }
    return majors, branches, motives, questions


def science(majors, branches, motives, questions):
    return scientific_fingerprint(
        majors, branches, motives, questions, max_major_id=215
    )


def membership(majors, branches):
    return membership_fingerprint(
        majors, branches, max_major_id=215
    )


class DualReferenceFingerprintTests(unittest.TestCase):
    def test_only_high_school_branch_changes_membership_not_science(self):
        majors, branches, motives, questions = fixture_snapshot()
        changed = copy.deepcopy(majors)
        changed[0]["high_school_branch"] = "ریاضی"

        self.assertEqual(
            science(majors, branches, motives, questions),
            science(changed, branches, motives, questions),
        )
        self.assertNotEqual(
            membership(majors, branches),
            membership(changed, branches),
        )

    def test_only_active_strategy_weight_changes_science_not_membership(self):
        majors, branches, motives, questions = fixture_snapshot()
        changed = copy.deepcopy(majors)
        changed[0]["strategy_weights"][0][0] = 0.25

        self.assertNotEqual(
            science(majors, branches, motives, questions),
            science(changed, branches, motives, questions),
        )
        self.assertEqual(
            membership(majors, branches),
            membership(changed, branches),
        )

    def test_group_cluster_subgroup_are_membership_only(self):
        majors, branches, motives, questions = fixture_snapshot()
        changed = copy.deepcopy(majors)
        changed[0]["group"] = "گروه ب"
        changed[0]["cluster"] = "B"
        changed[0]["subgroup"] = "B2"

        self.assertEqual(
            science(majors, branches, motives, questions),
            science(changed, branches, motives, questions),
        )
        self.assertNotEqual(
            membership(majors, branches),
            membership(changed, branches),
        )

    def test_weights_version_is_scientific_not_membership(self):
        majors, branches, motives, questions = fixture_snapshot()
        changed = copy.deepcopy(majors)
        changed[0]["weights_version"] = "fixture_scoring_v2"

        self.assertNotEqual(
            science(majors, branches, motives, questions),
            science(changed, branches, motives, questions),
        )
        self.assertEqual(
            membership(majors, branches),
            membership(changed, branches),
        )

    def test_non_finite_numbers_are_rejected_before_hashing(self):
        for bad_value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=bad_value):
                majors, branches, motives, questions = fixture_snapshot()
                majors[0]["strategy_weights"][0][0] = bad_value
                with self.assertRaisesRegex(ValueError, "Non-finite"):
                    science(majors, branches, motives, questions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
