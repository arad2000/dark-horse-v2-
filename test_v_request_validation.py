"""HTTP V input-type boundary; real scoring, no DB/network/paid session required.

Text semantics (including incomplete answers and trim/case normalization) remain
engine-owned. Only non-text JSON values are rejected by the request model.
"""
from contextlib import ExitStack
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

import main_v2
from dark_horse_engine_v2 import DarkHorseEngineV2


ROUTES = (
    ("/api/v2/darkhorse/discover", "discovery_result", "recommendations"),
    ("/api/v2/darkhorse/branch-discovery", "branch_discovery_result", "branches"),
)


class VRequestValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DarkHorseEngineV2(
            motives_path="docs/data/micro_motives.json",
            majors_path="majors_database_v2.json",
            trait_map_path="trait_map_v3.json",
            value_poles_path="value_poles_v2.json",
            school_branches_path="school_branches_v2.json",
        )

    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(main_v2.app.state, "engine", self.engine, create=True))
        stack.enter_context(patch.object(main_v2.app.state, "branch_engine", self.engine, create=True))
        self.auth = stack.enter_context(patch("main_v2._require_charged_journey", return_value=7))
        self.session = stack.enter_context(patch(
            "main_v2._persist_discovery_session", return_value=("v-boundary-test", None),
        ))
        stack.enter_context(patch("main_v2._persist_major_results", return_value=False))
        stack.enter_context(patch("main_v2._persist_branch_results", return_value=False))
        stack.enter_context(patch("main_v2._enforce_public_rate_limit"))
        self.major_call = stack.enter_context(patch.object(
            self.engine, "discover_individuality", wraps=self.engine.discover_individuality,
        ))
        self.branch_call = stack.enter_context(patch.object(
            self.engine, "recommend_school_branch", wraps=self.engine.recommend_school_branch,
        ))
        # No lifespan: engine is explicitly supplied above; no service is started.
        self.client = TestClient(main_v2.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def payload(self, answers):
        return {
            "micro_motives": self.engine.majors_db[1]["micro_motive_codes"],
            "sjt_answers": {f"sjt_{i}": "A" for i in range(1, 26)},
            "conjoint_choices": answers,
            "session_id": "v-boundary-test",
        }

    def test_non_text_json_values_return_422_before_handler(self):
        for route, _, _ in ROUTES:
            for invalid in (None, False, True, 0, 17, 1.5, [], ["Q1A"], {}, {"answer": "Q1A"}):
                with self.subTest(route=route, value=invalid):
                    response = self.client.post(route, json=self.payload({"conj_1": invalid}))
                    self.assertEqual(response.status_code, 422, response.text)
                    error = response.json()["detail"][0]
                    self.assertEqual(error["loc"], ["body", "conjoint_choices", "conj_1"])
                    self.assertEqual(error["type"], "string_type")
                    self.assertEqual(error["msg"], "Input should be a valid string")
        self.auth.assert_not_called()
        self.session.assert_not_called()
        self.major_call.assert_not_called()
        self.branch_call.assert_not_called()

    def test_non_dictionary_field_keeps_existing_422_contract(self):
        for route, _, _ in ROUTES:
            for invalid in (None, [], "Q1A", 17):
                with self.subTest(route=route, field=invalid):
                    response = self.client.post(route, json=self.payload(invalid))
                    self.assertEqual(response.status_code, 422, response.text)
        self.auth.assert_not_called()
        self.major_call.assert_not_called()
        self.branch_call.assert_not_called()

    def test_existing_fifteen_item_cap_is_preserved(self):
        answers = {f"conj_{i}": f"Q{i}A" for i in range(1, 17)}
        for route, _, _ in ROUTES:
            with self.subTest(route=route):
                response = self.client.post(route, json=self.payload(answers))
                self.assertEqual(response.status_code, 422, response.text)
        self.auth.assert_not_called()

    def test_omitted_empty_and_invalid_text_remain_engine_owned_incomplete(self):
        complete = {f"conj_{i}": f"Q{i}A" for i in range(1, 16)}
        cases = [None, {}, {"unknown": "Q1A"}]
        cases.extend({**complete, "conj_1": value}
                     for value in ("", "   ", "Q1C", "Q16A", "Q2A", "not-an-answer"))
        for route, result_key, items_key in ROUTES:
            for answers in cases:
                with self.subTest(route=route, answers=answers):
                    payload = self.payload(answers)
                    if answers is None:
                        del payload["conjoint_choices"]
                    response = self.client.post(route, json=payload)
                    self.assertEqual(response.status_code, 200, response.text)
                    result = response.json()[result_key]
                    self.assertEqual(result[items_key], [])
                    self.assertEqual(result["status"], "incomplete")
                    self.assertTrue(result["incomplete_assessments"])
                    for assessment in result["incomplete_assessments"]:
                        self.assertIsNone(assessment["v_result"]["score"])
                        self.assertEqual(assessment["v_result"]["status"], "value_incomplete")

    def test_complete_text_answers_preserve_real_engine_scores(self):
        for side in ("A", "B", "mixed"):
            clean = {f"conj_{i}": f"Q{i}{'B' if side == 'B' or side == 'mixed' and i % 2 == 0 else 'A'}"
                     for i in range(1, 16)}
            for normalize in (False, True):
                answers = {key: f"  {value.lower()}  " if normalize else value
                           for key, value in clean.items()}
                payload = self.payload(answers)
                for route, result_key, items_key in ROUTES:
                    with self.subTest(route=route, side=side, normalized=normalize):
                        args = (payload["micro_motives"], payload["sjt_answers"], clean)
                        if items_key == "recommendations":
                            reference = self.engine.discover_individuality(*args)
                            expected = {item["major_id"]: item["individuality_fit"]["score"]
                                        for item in reference["discovered_majors"]}
                            id_key = "major_id"
                        else:
                            reference = self.engine.recommend_school_branch(*args)
                            expected = {item["branch_name"]: item["average_score"]
                                        for item in reference["recommended_branches"]}
                            id_key = "branch_name_fa"
                        self.assertTrue(expected, "fixture must produce numeric recommendations")
                        response = self.client.post(route, json=payload)
                        self.assertEqual(response.status_code, 200, response.text)
                        actual = {item[id_key]: item["fit_score"]
                                  for item in response.json()[result_key][items_key]}
                        self.assertEqual(actual, expected)

    def test_valid_payload_still_requires_charged_journey(self):
        self.auth.side_effect = HTTPException(status_code=401, detail="authentication required")
        for route, _, _ in ROUTES:
            with self.subTest(route=route):
                response = self.client.post(route, json=self.payload({"conj_1": "Q1A"}))
                self.assertEqual(response.status_code, 401)
        self.session.assert_not_called()
        self.major_call.assert_not_called()
        self.branch_call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
