"""Regression tests for evidence-based motive separation in sibling majors."""
import json
import unittest
from pathlib import Path

from dark_horse_engine_v2 import DarkHorseEngineV2

ROOT = Path(__file__).resolve().parent


class SiblingMotiveSeparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "majors_database_v2.json").open(encoding="utf-8") as f:
            cls.majors = json.load(f)
        with (ROOT / "micro_motives.json").open(encoding="utf-8") as f:
            cls.motives = {row["code"]: row["description_fa"] for row in json.load(f)}
        cls.by_id = {int(row["id"]): row for row in cls.majors}
        cls.engine = object.__new__(DarkHorseEngineV2)
        cls.engine.motives_map = cls.motives
        cls.engine.trait_map = {}
        cls.engine.value_poles = {}

    @staticmethod
    def profile_answers(major):
        strategy = []
        for row in major.get("strategy_weights", []):
            strategy.append(row.index(max(row)) if row else -1)

        value_weights = major.get("value_weights", {})
        values = []
        for question in range(1, 16):
            key_a, key_b = f"Q{question}A", f"Q{question}B"
            values.append(
                key_a
                if value_weights.get(key_a, 0.0) >= value_weights.get(key_b, 0.0)
                else key_b
            )
        return strategy, values

    @classmethod
    def score_for_profile(cls, target_id, candidate_id):
        target = cls.by_id[target_id]
        candidate = cls.by_id[candidate_id]
        strategy_answers, value_choices = cls.profile_answers(target)
        motives = list(target.get("micro_motive_codes", []))

        m_score, _ = cls.engine._compute_m_score(motives, candidate)
        s_score, _ = cls.engine._compute_s_score(
            strategy_answers, candidate.get("strategy_weights", [])
        )
        v_score, _ = cls.engine._compute_v_score(
            value_choices, candidate.get("value_weights", {})
        )
        total = round(
            (0.55 * m_score) + (0.30 * v_score) + (0.15 * s_score), 1
        ) * 100
        return {
            "M": m_score,
            "S": s_score,
            "V": v_score,
            "Total": round(total, 1),
            "eligible": (
                candidate.get("motive_driven") is not False
                and m_score >= 0.15
                and total >= 30.0
            ),
        }

    def test_critical_sibling_code_sets_are_no_longer_identical(self):
        for left, right in ((42, 44), (34, 93)):
            with self.subTest(pair=(left, right)):
                self.assertNotEqual(
                    set(self.by_id[left]["micro_motive_codes"]),
                    set(self.by_id[right]["micro_motive_codes"]),
                )

    def test_computer_engineering_profile_ranks_42_above_44_and_reverse(self):
        score_42_as_target = self.score_for_profile(42, 42)
        score_44_as_sibling = self.score_for_profile(42, 44)
        self.assertTrue(score_42_as_target["eligible"])
        self.assertTrue(score_44_as_sibling["eligible"])
        self.assertGreater(score_42_as_target["Total"], score_44_as_sibling["Total"])

        score_44_as_target = self.score_for_profile(44, 44)
        score_42_as_sibling = self.score_for_profile(44, 42)
        self.assertTrue(score_44_as_target["eligible"])
        self.assertTrue(score_42_as_sibling["eligible"])
        self.assertGreater(score_44_as_target["Total"], score_42_as_sibling["Total"])

    def test_biotechnology_profiles_rank_the_matching_sibling_higher(self):
        medical_target = self.score_for_profile(34, 34)
        basic_sibling = self.score_for_profile(34, 93)
        self.assertTrue(medical_target["eligible"])
        self.assertTrue(basic_sibling["eligible"])
        self.assertGreater(medical_target["Total"], basic_sibling["Total"])

        basic_target = self.score_for_profile(93, 93)
        medical_sibling = self.score_for_profile(93, 34)
        self.assertTrue(basic_target["eligible"])
        self.assertTrue(medical_sibling["eligible"])
        self.assertGreater(basic_target["Total"], medical_sibling["Total"])

    def test_every_added_or_retained_distinguishing_code_is_catalogued(self):
        distinguishing_codes = {
            42: "EE-003",
            44: "CS-006",
            34: "GEN-002",
            93: "BIOINF-002",
        }
        for major_id, code in distinguishing_codes.items():
            with self.subTest(major_id=major_id, code=code):
                self.assertIn(code, self.motives)
                self.assertIn(code, self.by_id[major_id]["micro_motive_codes"])

    def test_no_active_majors_have_exact_duplicate_motive_sets(self):
        seen = {}
        duplicates = []
        for major in self.majors:
            if major.get("motive_driven") is False:
                continue
            codes = major.get("micro_motive_codes", [])
            if not codes:
                continue
            signature = tuple(sorted(set(codes)))
            if signature in seen:
                duplicates.append((seen[signature], int(major["id"])))
            else:
                seen[signature] = int(major["id"])
        self.assertEqual(duplicates, [])


if __name__ == "__main__":
    unittest.main()
