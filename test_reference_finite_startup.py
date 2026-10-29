"""Real-file scoring-reference contracts; no mocked loader/engine/lifespan.

Run: DATABASE_URL= python -m unittest -v test_reference_finite_startup
Only temporary copies are mutated. No questions file is copied or required.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import main_v2
from dark_horse_engine_v2 import DarkHorseEngineV2


ROOT = Path(__file__).resolve().parent
REFERENCE_PATHS = {
    "motives_path": "docs/data/micro_motives.json",
    "majors_path": "majors_database_v2.json",
    "trait_map_path": "trait_map_v3.json",
    "value_poles_path": "value_poles_v2.json",
    "school_branches_path": "school_branches_v2.json",
}
STRICT_REFERENCES = (
    "majors_database_v2.json",
    "docs/data/micro_motives.json",
    "school_branches_v2.json",
)


@contextmanager
def temporary_references():
    previous_cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for relative in REFERENCE_PATHS.values():
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        try:
            os.chdir(root)
            yield root
        finally:
            os.chdir(previous_cwd)


def edit_json(relative, mutate):
    path = Path(relative)
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def edit_active_major(mutate):
    def edit(rows):
        # Use the last active major so validation cannot stop after the first.
        major = next(row for row in reversed(rows) if row.get("motive_driven") is True)
        mutate(major)
    edit_json("majors_database_v2.json", edit)


class FiniteReferenceStartupTests(unittest.IsolatedAsyncioTestCase):
    async def assert_rejected_before_yield(self, message):
        with self.assertRaisesRegex(ValueError, message):
            DarkHorseEngineV2(**REFERENCE_PATHS)

        # A failed retry must also clear any previously ready state.
        main_v2.app.state.engine = object()
        main_v2.app.state.branch_engine = object()
        with self.assertRaisesRegex(RuntimeError, "refusing startup") as raised:
            async with main_v2.lifespan(main_v2.app):
                self.fail("Invalid real reference files must never reach lifespan yield")
        self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.assertIsNone(main_v2.app.state.engine)
        self.assertIsNone(main_v2.app.state.branch_engine)

    async def assert_ready(self):
        async with main_v2.lifespan(main_v2.app):
            engine = main_v2.app.state.engine
            self.assertIsInstance(engine, DarkHorseEngineV2)
            self.assertIs(main_v2.app.state.branch_engine, engine)
            self.assertEqual(len(engine.majors_db), 230)
            self.assertEqual(len(engine.motives_map), 1393)
            self.assertEqual(len(engine.school_branches), 4)

    async def test_current_deploy_references_ready_without_questions(self):
        with temporary_references() as root:
            self.assertFalse((root / "questions_v2.json").exists())
            self.assertFalse((root / "docs/data/questions_v2.json").exists())
            engine = DarkHorseEngineV2(**REFERENCE_PATHS)
            self.assertEqual(len(engine.value_poles), 30)
            await self.assert_ready()

    async def test_nan_in_each_reference_aborts_constructor_and_lifespan(self):
        for relative in STRICT_REFERENCES:
            with self.subTest(reference=relative), temporary_references():
                # NaN in otherwise unused metadata must still be rejected.
                edit_json(relative, lambda rows: rows[0].update(
                    {"finite_gate_probe": {"nested": [float("nan")]}}
                ))
                await self.assert_rejected_before_yield("non-finite")

    async def test_infinities_and_exponent_overflow_in_each_reference(self):
        for relative in STRICT_REFERENCES:
            for token in ("Infinity", "-Infinity", "1e999", "-1e999"):
                with self.subTest(reference=relative, token=token), temporary_references():
                    edit_json(relative, lambda rows: rows[0].update(
                        {"finite_gate_probe": ["__NONFINITE_LITERAL__"]}
                    ))
                    path = Path(relative)
                    path.write_text(path.read_text(encoding="utf-8").replace(
                        '"__NONFINITE_LITERAL__"', token
                    ), encoding="utf-8")
                    await self.assert_rejected_before_yield("non-finite")

    async def test_nonfinite_words_in_strings_are_not_rejected(self):
        with temporary_references():
            for relative in STRICT_REFERENCES:
                edit_json(relative, lambda rows: rows[0].update(
                    {"finite_gate_probe": "NaN Infinity -Infinity 1e999"}
                ))
            await self.assert_ready()

    async def test_active_strategy_requires_exact_shape_finite_numbers_and_range(self):
        def cell(value):
            return lambda major: major["strategy_weights"][-1].__setitem__(-1, value)

        cases = {
            "missing": lambda major: major.pop("strategy_weights"),
            "null": lambda major: major.update(strategy_weights=None),
            "object": lambda major: major.update(strategy_weights={}),
            "empty": lambda major: major.update(strategy_weights=[]),
            "24 rows": lambda major: major["strategy_weights"].pop(),
            "26 rows": lambda major: major["strategy_weights"].append([0] * 5),
            "4 columns": lambda major: major["strategy_weights"][-1].pop(),
            "6 columns": lambda major: major["strategy_weights"][-1].append(0),
            "scalar row": lambda major: major["strategy_weights"].__setitem__(-1, 0),
            "object row": lambda major: major["strategy_weights"].__setitem__(-1, {}),
            "null cell": cell(None),
            "string cell": cell("0.5"),
            "boolean cell": cell(True),
            "negative": cell(-0.01),
            "over one": cell(1.01),
        }
        for label, mutate in cases.items():
            with self.subTest(case=label), temporary_references():
                edit_active_major(mutate)
                await self.assert_rejected_before_yield("strategy_weights")

    async def test_active_values_require_exact_30_poles_and_finite_numeric_values(self):
        def pole(value):
            return lambda major: major["value_weights"].update(Q15B=value)

        def replace_key(major):
            major["value_weights"]["Q16B"] = major["value_weights"].pop("Q15B")

        cases = {
            "missing": lambda major: major.pop("value_weights"),
            "null": lambda major: major.update(value_weights=None),
            "array": lambda major: major.update(value_weights=[]),
            "empty": lambda major: major.update(value_weights={}),
            "missing pole": lambda major: major["value_weights"].pop("Q15B"),
            "extra pole": lambda major: major["value_weights"].update(Q16B=0),
            "30 wrong poles": replace_key,
            "null pole": pole(None),
            "string pole": pole("0.5"),
            "boolean pole": pole(False),
            "overflowing integer": pole(10 ** 400),
        }
        for label, mutate in cases.items():
            with self.subTest(case=label), temporary_references():
                edit_active_major(mutate)
                await self.assert_rejected_before_yield("value_weights")

    async def test_nonfinite_active_weight_cells_are_rejected(self):
        for field in ("strategy_weights", "value_weights"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(field=field, value=value), temporary_references():
                    def mutate(major):
                        if field == "strategy_weights":
                            major[field][-1][-1] = value
                        else:
                            major[field]["Q15B"] = value
                    edit_active_major(mutate)
                    await self.assert_rejected_before_yield("non-finite")

    async def test_strategy_boundaries_and_finite_values_outside_unit_interval(self):
        with temporary_references():
            def mutate(major):
                major["strategy_weights"][-1] = [0, 1, 0.5, 0, 1]
                # Only S has the [0,1] constraint in this gate; V must be finite.
                major["value_weights"].update(Q1A=-1, Q1B=2)
            edit_active_major(mutate)
            await self.assert_ready()

    async def test_inactive_major_does_not_gain_active_weight_requirements(self):
        with temporary_references():
            def mutate(rows):
                inactive = next(row for row in rows if row.get("motive_driven") is False)
                inactive.update(strategy_weights=None, value_weights=None)
            edit_json("majors_database_v2.json", mutate)
            await self.assert_ready()


if __name__ == "__main__":
    unittest.main(verbosity=2)
