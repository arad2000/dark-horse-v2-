"""Offline artifact tests; no application imports, DB, network, publish or DNS."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "frontend_builder", ROOT / "scripts/frontend/build_public_artifact.py"
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class PublicArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(builder.DEFAULT_CONFIG.read_text())
        cls.commit, cls.files = builder.validate_config(cls.config)
        cls.blobs, cls.evidence = builder.collect_blobs(ROOT, cls.commit, cls.files)

    def reject_path(self, name):
        config = copy.deepcopy(self.config)
        config["files"].append(name)
        with self.assertRaises(ValueError):
            builder.validate_config(config)

    def test_pinned_source_not_moving_ref(self):
        for value in ("main", "HEAD", "4b91826", "--help"):
            config = dict(self.config, source_commit=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                builder.validate_config(config)

    def test_sensitive_paths_and_globs_rejected(self):
        for name in ("data/sanjesh_riazi_1405_programs.json",
                     "data/sanjesh_record_capacity_full.json", "majors_database_v2.json",
                     "value_poles_v2.json", "program2s.json", "data/extra.json",
                     "weight-review/audit.html", "audits/internal.js", ".env", ".git/config",
                     "data/*", "free_journey_mode.js", "CNAME", "admin.html", "download.html"):
            with self.subTest(path=name):
                self.reject_path(name)

    def test_traversal_and_url_paths_rejected(self):
        for name in ("../main_v2.py", "/index.html", "data/../app.js", "./app.js",
                     "data//new.js", "data/%2e%2e/new.js", "data\\new.js", "app.js?v=1"):
            with self.subTest(path=name):
                self.reject_path(name)

    def test_duplicate_and_missing_required_rejected(self):
        config = copy.deepcopy(self.config)
        config["files"].append("app.js")
        with self.assertRaises(ValueError):
            builder.validate_config(config)
        config["files"].remove("app.js")
        config["files"].remove("app.js")
        with self.assertRaises(ValueError):
            builder.validate_config(config)

    def test_missing_dependency_rejected(self):
        blobs = dict(self.blobs)
        del blobs["shell.js"]
        with self.assertRaisesRegex(ValueError, "Missing public dependency"):
            builder.validate_dependencies(blobs)

    def test_old_manifest_prefix_rejected(self):
        blobs = dict(self.blobs)
        manifest = json.loads(blobs["manifest.json"])
        manifest["start_url"] = "/dark-horse-v2-/"
        blobs["manifest.json"] = json.dumps(manifest).encode()
        with self.assertRaisesRegex(ValueError, "root-origin"):
            builder.validate_dependencies(blobs)

    def test_missing_git_asset_rejected(self):
        with self.assertRaisesRegex(ValueError, "Absent/non-regular"):
            builder.collect_blobs(ROOT, self.commit, self.files + ["missing.js"])

    def test_symlink_blob_rejected_without_reading_target(self):
        def fake_git(repo, *args):
            if args[0] == "rev-parse":
                return self.commit.encode()
            if args[0] == "ls-tree":
                return b"120000 blob " + b"a" * 40 + b"\tdocs/app.js\0"
            self.fail("Must not read a symlink target")
        with patch.object(builder, "git", side_effect=fake_git):
            with self.assertRaisesRegex(ValueError, "non-regular"):
                builder.collect_blobs(ROOT, self.commit, ["app.js"])

    def test_exact_artifact_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "public"
            result = builder.build(ROOT, builder.DEFAULT_CONFIG, output)
            paths = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
            self.assertEqual(paths, set(self.files))
            self.assertEqual(result["source_commit"], self.commit)
            for name in self.files:
                self.assertEqual((output / name).read_bytes(), self.blobs[name], name)
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(),
                                 result["files"][name]["sha256"])
            self.assertTrue(output.with_name("public.evidence.json").is_file())
            self.assertFalse((output / "public.evidence.json").exists())
            self.assertEqual(set(p for p in paths if p.endswith(".json")), builder.PUBLIC_JSON)

    def test_reproducible_builds(self):
        with tempfile.TemporaryDirectory() as directory:
            a = builder.build(ROOT, builder.DEFAULT_CONFIG, Path(directory) / "a")
            b = builder.build(ROOT, builder.DEFAULT_CONFIG, Path(directory) / "b")
            self.assertEqual(a, b)

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "public"
            output.mkdir()
            (output / "keep.txt").write_text("keep")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                builder.build(ROOT, builder.DEFAULT_CONFIG, output)
            self.assertEqual((output / "keep.txt").read_text(), "keep")

    def test_existing_evidence_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "public"
            output.with_name("public.evidence.json").write_text("keep")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                builder.build(ROOT, builder.DEFAULT_CONFIG, output)
            self.assertFalse(output.exists())

    def test_output_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "link"
            link.symlink_to(Path(directory), target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                builder.build(ROOT, builder.DEFAULT_CONFIG, link / "public")

    def test_source_tree_output_rejected(self):
        with self.assertRaisesRegex(ValueError, "restricted"):
            builder.build(ROOT, builder.DEFAULT_CONFIG, ROOT / "docs/public")

    def test_working_tree_is_not_artifact_input(self):
        # Only Git objects are read; no docs/ file is opened from the checkout.
        original = Path.read_bytes
        def deny_worktree_docs(path):
            if ROOT / "docs" in path.parents:
                self.fail("Attempted working-tree docs read")
            return original(path)
        with tempfile.TemporaryDirectory() as directory, patch.object(Path, "read_bytes", deny_worktree_docs):
            result = builder.build(ROOT, builder.DEFAULT_CONFIG, Path(directory) / "public")
            self.assertEqual(result["files"], self.evidence)

    def test_initial_home_html_is_present_without_api(self):
        # Static evidence only, not a WebView/browser execution claim.
        html = self.blobs["index.html"].decode()
        self.assertIn('id="dh-startup-home"', html)
        self.assertIn('id="dh-startup-start"', html)
        self.assertIn("سفر اکتشافی", html)


if __name__ == "__main__":
    unittest.main()
