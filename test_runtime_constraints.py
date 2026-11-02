"""Runtime packaging contracts, not a vulnerability or scientific audit."""
from importlib import metadata
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def pins():
    result = {}
    for line in (ROOT / "constraints.txt").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)", line)
        if not match:
            raise AssertionError(f"Constraint must be one exact version pin: {line}")
        key = normalized(match[1])
        if key in result:
            raise AssertionError(f"Duplicate constraint: {key}")
        result[key] = match[2]
    return result


class RuntimeConstraintsTests(unittest.TestCase):
    def test_pins_are_exact_unique_and_nonempty(self):
        self.assertTrue(pins())

    def test_constraints_are_mandatory_and_cover_direct_requirements(self):
        source = (ROOT / "requirements.txt").read_text().splitlines()
        self.assertIn("-c constraints.txt", source)
        versions = pins()
        for line in source:
            if not line.strip() or line.lstrip().startswith(("#", "-")):
                continue
            match = re.match(r"([A-Za-z0-9_.-]+)", line)
            self.assertIsNotNone(match)
            self.assertIn(normalized(match[1]), versions)

    def test_installed_direct_runtime_versions_match_pins(self):
        versions = pins()
        for line in (ROOT / "requirements.txt").read_text().splitlines():
            if not line.strip() or line.lstrip().startswith(("#", "-")):
                continue
            name = re.match(r"([A-Za-z0-9_.-]+)", line)[1]
            with self.subTest(distribution=name):
                self.assertEqual(metadata.version(name), versions[normalized(name)])


if __name__ == "__main__":
    unittest.main()
