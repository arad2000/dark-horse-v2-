from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main_v2
from dark_horse_engine_v2 import DarkHorseEngineV2


ROOT = Path(__file__).resolve().parent
REFERENCE_PATHS = {
    "motives_path": ROOT / "docs" / "data" / "micro_motives.json",
    "majors_path": ROOT / "majors_database_v2.json",
    "trait_map_path": ROOT / "trait_map_v3.json",
    "value_poles_path": ROOT / "value_poles_v2.json",
    "school_branches_path": ROOT / "school_branches_v2.json",
}


class RequiredReferenceLoadingTests(unittest.TestCase):
    def test_healthy_reference_set_constructs_a_complete_engine(self):
        engine = DarkHorseEngineV2(**{key: str(path) for key, path in REFERENCE_PATHS.items()})
        self.assertEqual(len(engine.motives_map), 1393)
        self.assertEqual(len(engine.majors_db), 230)
        self.assertEqual(set(engine.trait_map), {f"S{i:02d}" for i in range(1, 26)})
        self.assertEqual(len(engine.value_poles), 30)
        self.assertEqual(len(engine.school_branches), 4)

    def test_every_required_reference_file_is_mandatory(self):
        for field, source_path in REFERENCE_PATHS.items():
            with self.subTest(reference=field), tempfile.TemporaryDirectory() as tmp:
                missing_path = Path(tmp) / source_path.name
                paths = {key: str(path) for key, path in REFERENCE_PATHS.items()}
                paths[field] = str(missing_path)
                with self.assertRaises(FileNotFoundError):
                    DarkHorseEngineV2(**paths)

    def test_every_required_reference_must_be_valid_json(self):
        for field, source_path in REFERENCE_PATHS.items():
            with self.subTest(reference=field), tempfile.TemporaryDirectory() as tmp:
                broken_path = Path(tmp) / source_path.name
                broken_path.write_text('{"broken": ', encoding="utf-8")
                paths = {key: str(path) for key, path in REFERENCE_PATHS.items()}
                paths[field] = str(broken_path)
                with self.assertRaises(json.JSONDecodeError):
                    DarkHorseEngineV2(**paths)


class RuntimeFailClosedStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_engine_construction_error_aborts_lifespan_before_yield(self):
        with patch(
            "main_v2.DarkHorseEngineV2",
            side_effect=RuntimeError("simulated engine construction failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "refusing startup"):
                async with main_v2.lifespan(main_v2.app):
                    self.fail("lifespan must not yield when engine construction fails")

        self.assertIsNone(main_v2.app.state.engine)
        self.assertIsNone(main_v2.app.state.branch_engine)

    async def test_missing_reference_aborts_lifespan_before_yield(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "micro_motives_missing.json"
            paths = {key: str(path) for key, path in REFERENCE_PATHS.items()}
            paths["motives_path"] = str(missing_path)

            def build_engine_with_missing_reference(**_kwargs):
                return DarkHorseEngineV2(**paths)

            with patch(
                "main_v2.DarkHorseEngineV2",
                side_effect=build_engine_with_missing_reference,
            ):
                with self.assertRaisesRegex(RuntimeError, "refusing startup"):
                    async with main_v2.lifespan(main_v2.app):
                        self.fail("lifespan must not yield with a missing required reference")

        self.assertIsNone(main_v2.app.state.engine)
        self.assertIsNone(main_v2.app.state.branch_engine)

    async def test_healthy_engine_allows_lifespan_to_yield_ready(self):
        paths = {key: str(path) for key, path in REFERENCE_PATHS.items()}

        def build_healthy_engine(**_kwargs):
            return DarkHorseEngineV2(**paths)

        with patch("main_v2.DarkHorseEngineV2", side_effect=build_healthy_engine):
            async with main_v2.lifespan(main_v2.app):
                self.assertIsInstance(main_v2.app.state.engine, DarkHorseEngineV2)
                self.assertIs(main_v2.app.state.branch_engine, main_v2.app.state.engine)
                self.assertEqual(len(main_v2.app.state.engine.motives_map), 1393)


if __name__ == "__main__":
    unittest.main(verbosity=2)
