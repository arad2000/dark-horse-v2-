from pathlib import Path
import ast
import unittest


class StartupEngineContractTests(unittest.TestCase):
    def test_lifespan_constructs_one_engine_and_shares_it(self):
        source = Path("main_v2.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        constructors = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "DarkHorseEngineV2"
        ]
        self.assertEqual(len(constructors), 1, "startup must construct exactly one DarkHorseEngineV2")
        text = source
        self.assertIn("app.state.engine = engine", text)
        self.assertIn("app.state.branch_engine = engine", text)

    def test_both_discovery_routes_keep_separate_state_contracts(self):
        source = Path("main_v2.py").read_text(encoding="utf-8")
        self.assertIn("engine = req.app.state.engine", source)
        self.assertIn("engine = req.app.state.branch_engine", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
