"""P0.1 contract: every user-facing recommendation path uses backend results."""
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_JS = ROOT / "docs" / "app.js"
MAIN_API = ROOT / "main_v2.py"
MAJORS_JSON = ROOT / "majors_database_v2.json"


class ResultCatalogFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_source = APP_JS.read_text(encoding="utf-8")
        cls.api_source = MAIN_API.read_text(encoding="utf-8")
        cls.majors = json.loads(MAJORS_JSON.read_text(encoding="utf-8"))

    def test_deploy_major_catalog_is_the_complete_230_id_set(self):
        self.assertEqual(len(self.majors), 230)
        ids = {major.get("id") for major in self.majors}
        self.assertEqual(ids, set(range(1, 231)))

    def test_both_frontend_result_paths_submit_to_backend_api(self):
        self.assertIn("API_BASE + '/api/v2/darkhorse/discover'", self.app_source)
        self.assertIn("API_BASE + '/api/v2/darkhorse/branch-discovery'", self.app_source)
        self.assertIn("data.discovery_result?.recommendations", self.app_source)
        self.assertIn("data.branch_discovery_result?.branches", self.app_source)
        self.assertIn('majors_path="majors_database_v2.json"', self.api_source)
        self.assertIn("engine.discover_individuality", self.api_source)
        self.assertIn("engine.recommend_school_branch", self.api_source)

    def test_frontend_does_not_load_a_local_major_database_for_scoring(self):
        self.assertNotRegex(
            self.app_source,
            re.compile(r"fetch\s*\([^)]*majors_database_v2\.json", re.IGNORECASE),
        )
        self.assertNotRegex(
            self.app_source,
            re.compile(r"0\.55\s*\*\s*(?:m_score|mScore)", re.IGNORECASE),
        )


if __name__ == "__main__":
    unittest.main()
