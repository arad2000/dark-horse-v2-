from __future__ import annotations

import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from main_v2 import DarkHorseDiscoverRequest, branch_discovery_v2, discover_v2, root


class FakeEngine:
    def __init__(self):
        self.discover_calls = 0
        self.branch_calls = 0

    def discover_individuality(self, micro_motives, sjt_answers, conjoint_choices):
        self.discover_calls += 1
        return {
            "discovered_majors": [
                {
                    "major_id": 1,
                    "major_name_fa": "رشته آزمایشی",
                    "realm_fa": "آزمایشی",
                    "individuality_fit": {
                        "score": 91.0,
                        "level": "بالا",
                        "market_demand_level": 3,
                        "raw_components": {"m_score": 92.0, "s_score": 90.0, "v_score": 91.0},
                        "evidence": {"matched": ["MOT-001"]},
                        "personalized_description": "توضیح آزمایشی",
                        "archetype": {"name": "Explorer"},
                        "alternative_paths": ["مسیر جایگزین"],
                    },
                },
                {
                    "major_id": 2,
                    "major_name_fa": "رشته دوم",
                    "realm_fa": "آزمایشی",
                    "individuality_fit": {
                        "score": 72.0,
                        "level": "متوسط",
                        "market_demand_level": 2,
                        "raw_components": {"m_score": 70.0, "s_score": 74.0, "v_score": 72.0},
                        "evidence": {},
                        "personalized_description": "توضیح دوم",
                    },
                },
            ],
            "method": {"name": "test"},
            "summary": {"ok": True},
            "next_step": "ادامه",
        }

    def recommend_school_branch(self, micro_motives, sjt_answers, conjoint_choices):
        self.branch_calls += 1
        return {
            "recommended_branches": [
                {
                    "branch_name": "Test Branch",
                    "average_score": 88.0,
                    "count": 3,
                    "avg_components": {"m_score": 89.0, "s_score": 87.0, "v_score": 88.0},
                    "evidence": {"matched": ["MOT-001"]},
                    "warning": "هشدار آزمایشی",
                    "alternative_paths": ["مسیر جایگزین"],
                }
            ],
            "best_branch": "Test Branch",
            "method": {"name": "test"},
            "summary": {"ok": True},
            "next_step": "ادامه",
        }


def request_for(engine):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(engine=engine, branch_engine=engine)))


class MainApiContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_root_contract(self):
        self.assertEqual(
            await root(),
            {"name": "Dark Horse API V2.0", "status": "online"},
        )

    async def test_discover_contract_is_json_engine_owned(self):
        engine = FakeEngine()
        request = DarkHorseDiscoverRequest(
            micro_motives=["MOT-001"],
            sjt_answers={"S01": 2},
            conjoint_choices={"Q1": "A"},
        )
        result = await discover_v2(request, request_for(engine))

        self.assertEqual(engine.discover_calls, 1)
        self.assertEqual(result["discovery_result"]["total_matches"], 2)
        self.assertEqual(result["discovery_result"]["high_fit_majors"], 1)
        self.assertEqual(result["discovery_result"]["medium_fit_majors"], 1)
        self.assertEqual(result["discovery_result"]["recommendations"][0]["fit_score"], 91.0)
        self.assertIn("archetype", result["discovery_result"]["recommendations"][0])
        self.assertIn("alternative_paths", result["discovery_result"]["recommendations"][0])
        self.assertTrue(result["session_id"])

    async def test_branch_discovery_contract(self):
        engine = FakeEngine()
        request = DarkHorseDiscoverRequest(
            micro_motives=["MOT-001"],
            sjt_answers={},
            conjoint_choices={},
        )
        result = await branch_discovery_v2(request, request_for(engine))

        self.assertEqual(engine.branch_calls, 1)
        branch_result = result["branch_discovery_result"]
        self.assertEqual(branch_result["total_matches"], 1)
        self.assertEqual(branch_result["best_branch"], "Test Branch")
        self.assertEqual(branch_result["branches"][0]["fit_score"], 88.0)
        self.assertEqual(branch_result["branches"][0]["count"], 3)
        self.assertEqual(branch_result["branches"][0]["branch_name_fa"], "Test Branch")
        self.assertIn("warning", branch_result["branches"][0])
        self.assertIn("alternative_paths", branch_result["branches"][0])

    async def test_missing_engine_fails_closed(self):
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(engine=None, branch_engine=None)))
        request = DarkHorseDiscoverRequest()
        with self.assertRaises(HTTPException) as ctx:
            await discover_v2(request, req)
        self.assertEqual(ctx.exception.status_code, 503)

        with self.assertRaises(HTTPException) as ctx:
            await branch_discovery_v2(request, req)
        self.assertEqual(ctx.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main(verbosity=2)
