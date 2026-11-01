"""S-score contract: exactly 25 valid A-E responses are required."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from dark_horse_engine_v2 import DarkHorseEngineV2


class SIncompletePolicyTests(unittest.TestCase):
    def setUp(self):
        self.engine = object.__new__(DarkHorseEngineV2)
        self.engine.trait_map = {}
        self.engine.majors_db = {}
        self.engine.school_branches = {
            f"branch-{i}": {"strategy_weights": self.weights(), "value_weights": {}}
            for i in range(4)
        }
        self.engine.motives_map = {}
        self.engine.value_poles = {}

    @staticmethod
    def weights():
        return [[1.0, 0.8, 0.6, 0.4, 0.2] for _ in range(25)]

    @staticmethod
    def answers(count=25, answer="A"):
        return {f"sjt_{i}": answer for i in range(1, count + 1)}

    def test_25_valid_answers_preserve_complete_profile_formula(self):
        weights = [[0.2, 0.4, 0.6, 0.8, 1.0] for _ in range(25)]
        payload = {f"sjt_{i}": "ABCDE"[(i - 1) % 5] for i in range(1, 26)}
        answers, assessment = self.engine._parse_s_strategy_answers(payload)
        self.assertEqual(assessment["status"], "complete")
        self.assertEqual(assessment["valid_answers"], 25)
        expected = sum(row[choice] / max(row) for row, choice in zip(weights, answers)) / 25
        score, _ = self.engine._compute_s_score_for_complete_profile(answers, weights)
        self.assertAlmostEqual(score, expected, places=12)
        all_strong, _ = self.engine._compute_s_score_for_complete_profile([0] * 25, self.weights())
        self.assertEqual(all_strong, 1.0)

    def test_24_valid_answers_are_incomplete_and_not_numeric(self):
        payload = self.answers(24)
        answers, assessment = self.engine._parse_s_strategy_answers(payload)
        self.assertEqual(assessment["status"], "incomplete_s_responses")
        self.assertEqual(assessment["valid_answers"], 24)
        self.assertIsNone(self.engine._compute_s_score_for_complete_profile(answers, self.weights())[0])
        result = self.engine.discover_individuality([], payload, {})
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["s_assessment"]["status"], "incomplete_s_responses")
        self.assertIsNone(result["s_assessment"]["score"])
        self.assertEqual(result["discovered_majors"], [])

    def test_five_strong_answers_are_incomplete_not_1_or_0_2(self):
        payload = self.answers(5, "A")
        answers, assessment = self.engine._parse_s_strategy_answers(payload)
        self.assertEqual(assessment["status"], "incomplete_s_responses")
        self.assertIsNone(self.engine._compute_s_score_for_complete_profile(answers, self.weights())[0])
        result = self.engine.recommend_school_branch([], payload, {})
        self.assertEqual(result["s_assessment"]["status"], "incomplete_s_responses")
        self.assertIsNone(result["s_assessment"]["score"])
        self.assertEqual(result["recommended_branches"], [])
        self.assertIsNone(result["best_branch"])

    def test_null_or_invalid_option_and_unknown_key_are_incomplete(self):
        payload = self.answers()
        payload["sjt_12"] = None
        answers, assessment = self.engine._parse_s_strategy_answers(payload)
        self.assertIn("sjt_12", assessment["invalid_questions"])
        self.assertIsNone(self.engine._compute_s_score_for_complete_profile(answers, self.weights())[0])

        payload = self.answers()
        payload["sjt_12"] = "F"
        answers, assessment = self.engine._parse_s_strategy_answers(payload)
        self.assertEqual(assessment["status"], "incomplete_s_responses")
        self.assertIsNone(self.engine._compute_s_score_for_complete_profile(answers, self.weights())[0])

        payload = self.answers()
        payload["sjt_unknown"] = "A"
        answers, assessment = self.engine._parse_s_strategy_answers(payload)
        self.assertIn("sjt_unknown", assessment["unknown_keys"])
        self.assertEqual(assessment["status"], "incomplete_s_responses")
        self.assertIsNone(self.engine._compute_s_score_for_complete_profile(answers, self.weights())[0])


class SIncompleteApiContractTests(unittest.TestCase):
    def _request_and_req(self, sjt_answers):
        import main_v2
        request = main_v2.DarkHorseDiscoverRequest(sjt_answers=sjt_answers)
        req = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(engine=None, branch_engine=None)),
            headers={},
            client=SimpleNamespace(host="127.0.0.1"),
        )
        return main_v2, request, req

    def test_discover_api_returns_200_contract_flag_and_does_not_persist(self):
        import main_v2
        payload = {f"sjt_{i}": "A" for i in range(1, 6)}
        main_v2, request, req = self._request_and_req(payload)
        req.app.state.engine = SimpleNamespace(
            discover_individuality=lambda *args: {
                "discovered_majors": [],
                "incomplete_assessments": [],
                "status": "incomplete",
                "s_assessment": {
                    "score": None, "status": "incomplete_s_responses",
                    "valid_answers": 5, "expected_answers": 25,
                },
                "summary": {}, "method": {},
            }
        )
        route = next(r for r in main_v2.app.routes if getattr(r, "path", None) == "/api/v2/darkhorse/discover")
        self.assertEqual(route.status_code, 200)
        with patch.object(main_v2, "_enforce_public_rate_limit"), \
             patch.object(main_v2, "_enforce_payload_limit"), \
             patch.object(main_v2, "_require_charged_journey", return_value="user"), \
             patch.object(main_v2, "_persist_discovery_session", return_value=("session", "persisted")), \
             patch.object(main_v2, "_persist_major_results", side_effect=AssertionError("must not persist incomplete S")):
            response = asyncio.run(main_v2.discover_v2(request, req))
        result = response["discovery_result"]
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["s_assessment"]["status"], "incomplete_s_responses")
        self.assertEqual(result["recommendations"], [])
        self.assertFalse(response["operational_result_persisted"])

    def test_branch_api_returns_200_contract_flag_and_no_best_branch(self):
        import main_v2
        payload = {f"sjt_{i}": "A" for i in range(1, 6)}
        request = main_v2.DarkHorseDiscoverRequest(sjt_answers=payload)
        req = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(engine=None, branch_engine=None)),
            headers={},
            client=SimpleNamespace(host="127.0.0.1"),
        )
        req.app.state.branch_engine = SimpleNamespace(
            recommend_school_branch=lambda *args: {
                "recommended_branches": [],
                "incomplete_assessments": [],
                "status": "incomplete",
                "s_assessment": {
                    "score": None, "status": "incomplete_s_responses",
                    "valid_answers": 5, "expected_answers": 25,
                },
                "best_branch": None, "summary": {}, "method": {},
            }
        )
        route = next(r for r in main_v2.app.routes if getattr(r, "path", None) == "/api/v2/darkhorse/branch-discovery")
        self.assertEqual(route.status_code, 200)
        with patch.object(main_v2, "_enforce_public_rate_limit"), \
             patch.object(main_v2, "_enforce_payload_limit"), \
             patch.object(main_v2, "_require_charged_journey", return_value="user"), \
             patch.object(main_v2, "_persist_discovery_session", return_value=("session", "persisted")), \
             patch.object(main_v2, "_persist_branch_results", side_effect=AssertionError("must not persist incomplete S")):
            response = asyncio.run(main_v2.branch_discovery_v2(request, req))
        result = response["branch_discovery_result"]
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["s_assessment"]["status"], "incomplete_s_responses")
        self.assertEqual(result["branches"], [])
        self.assertIsNone(result["best_branch"])
        self.assertFalse(response["operational_result_persisted"])


class SEqualApiContractTests(unittest.IsolatedAsyncioTestCase):
    async def _call_both(self, engine, motives):
        from test_main_api_contract import request_for
        import main_v2
        payload = main_v2.DarkHorseDiscoverRequest(
            micro_motives=motives, session_id="s-equal-test",
            sjt_answers={f"sjt_{i}": "A" for i in range(1, 26)},
            conjoint_choices={f"conj_{i}": f"Q{i}A" for i in range(1, 16)})
        with patch("main_v2._enforce_public_rate_limit"), \
             patch("main_v2._require_charged_journey", return_value=7), \
             patch("main_v2._persist_discovery_session", return_value=("test", None)), \
             patch("main_v2._persist_major_results", return_value=False) as majors, \
             patch("main_v2._persist_branch_results", return_value=False) as branches:
            a = (await main_v2.discover_v2(payload, request_for(engine)))["discovery_result"]
            b = (await main_v2.branch_discovery_v2(payload, request_for(engine)))["branch_discovery_result"]
        return a, b, majors, branches

    async def test_equal_no_evidence_real_engine_reason_survives_api(self):
        import copy
        engine = DarkHorseEngineV2()
        key, major = next((key, row) for key, row in engine.majors_db.items()
                          if row.get("motive_driven") is not False)
        motives = major["micro_motive_codes"]
        engine.majors_db = {key: copy.deepcopy(major)}
        for row in list(engine.majors_db.values()) + list(engine.school_branches.values()):
            row["strategy_weights"] = [[.5] * 5 for _ in range(25)]
        a, b, majors, branches = await self._call_both(engine, motives)
        self.assertEqual(a["recommendations"], [])
        self.assertEqual(b["branches"], [])
        self.assertIsNone(b["best_branch"])
        for result in (a, b):
            self.assertEqual(result["s_assessment"]["status"], "complete")
            self.assertTrue(result["incomplete_assessments"])
            for row in result["incomplete_assessments"]:
                self.assertEqual(row["reason"], "equal_no_evidence")
                self.assertIsNone(row["strategy_assessment"]["score"])
        self.assertEqual(majors.call_args.args[1], [])
        self.assertEqual(branches.call_args.args[1], [])

    async def test_ranked_s_coverage_is_not_dropped_by_api_adapters(self):
        from test_main_api_contract import FakeEngine
        original = FakeEngine()
        assessment = {"score": .875, "status": "complete",
                      "coverage": {"answered": 25, "total": 25,
                                   "informative_answered": 1, "equal_answered": 24}}
        def major(*args):
            result = original.discover_individuality(*args)
            for row in result["discovered_majors"]:
                row["individuality_fit"]["strategy_assessment"] = assessment
            return result
        def branch(*args):
            result = original.recommend_school_branch(*args)
            for row in result["recommended_branches"]:
                row["strategy_assessment"] = assessment
            return result
        engine = SimpleNamespace(discover_individuality=major, recommend_school_branch=branch)
        a, b, _, _ = await self._call_both(engine, [])
        for row in a["recommendations"] + b["branches"]:
            self.assertEqual(row["strategy_assessment"], assessment)


if __name__ == "__main__":
    unittest.main()
