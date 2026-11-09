#!/usr/bin/env python3
"""Extract an explicit public allowlist from a pinned Git commit; never publish.

No imports of application code, checkout, source rewriting, networking or runtime
configuration. Evidence lives beside (not inside) the public directory.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit

DEFAULT_CONFIG = Path(__file__).with_name("public_allowlist.json")
PUBLIC_JSON = frozenset({
    "manifest.json", "majors_catalog_ui_v1.json", "trait_map_v3.json",
    "data/micro_motives.json", "data/questions_v2.json", "data/trait_map_v3.json",
})
DENIED_NAMES = frozenset({"free_journey_mode.js", "CNAME", ".nojekyll"})
ALLOWED_SUFFIXES = {".html", ".js", ".css", ".json", ".png", ".jpg", ".svg", ".woff2", ".txt"}


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def validate_config(config: dict) -> tuple[str, list[str]]:
    if not isinstance(config, dict):
        raise ValueError("Allowlist must be a JSON object")
    if config.get("schema_version") != 1 or config.get("source_root") != "docs":
        raise ValueError("Expected schema_version=1 and source_root=docs")
    commit = config.get("source_commit", "")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("source_commit must be a full pinned SHA, not a moving ref")
    files = config.get("files")
    if not isinstance(files, list) or not files or any(not isinstance(p, str) for p in files):
        raise ValueError("files must be an explicit non-empty string list")
    if len(files) != len(set(files)):
        raise ValueError("Duplicate allowlist path")
    for name in files:
        p = PurePosixPath(name)
        if (p.is_absolute() or str(p) != name or any(x in {".", ".."} for x in p.parts)
                or "\\" in name or unquote(name) != name or "?" in name or "#" in name
                or any(x.startswith(".") for x in p.parts)):
            raise ValueError(f"Unsafe path: {name}")
        # No directory glob, audit/document dump, scientific server reference or APK.
        if len(p.parts) > 1 and p.parts[0] not in {"data", "fonts"}:
            raise ValueError(f"Non-public directory: {name}")
        if (any(ch in name for ch in "*[]\x00") or "sanjesh" in name.lower()
                or "program2s" in name.lower() or name in DENIED_NAMES
                or p.suffix not in ALLOWED_SUFFIXES
                or (p.suffix == ".json" and name not in PUBLIC_JSON)
                or (p.suffix == ".txt" and name != "31032553.txt")
                or (p.suffix == ".html" and name not in {"index.html", "privacy.html"})):
            raise ValueError(f"Forbidden public asset: {name}")
    required = {"index.html", "app.js", "shell.js", "sw.js", "manifest.json"}
    if not required.issubset(files):
        raise ValueError("Required entrypoint assets absent")
    return commit, sorted(files)


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "img"} and attrs.get("src"):
            self.urls.append(attrs["src"])
        if tag == "link" and attrs.get("href"):
            self.urls.append(attrs["href"])
        if tag == "img" and attrs.get("srcset"):
            self.urls.extend(part.strip().split()[0] for part in attrs["srcset"].split(","))


def validate_dependencies(blobs: dict[str, bytes]) -> None:
    """Fail on missing HTML/CSS/manifest dependencies, not auto-expand allowlist.

    Arbitrary dynamic JavaScript URLs cannot be proven by this static check;
    their explicitly reviewed paths remain in the allowlist and browser checklist.
    """
    urls = []
    for name, payload in blobs.items():
        if name.endswith(".html"):
            parser = AssetParser()
            parser.feed(payload.decode("utf-8"))
            urls.extend((name, url) for url in parser.urls)
        if name.endswith((".css", ".html")):
            urls.extend((name, match.strip(" '\"")) for match in re.findall(
                r"url\(([^)]+)\)", payload.decode("utf-8")))
    manifest = json.loads(blobs["manifest.json"])
    if any(manifest.get(key) != "/" for key in ("id", "start_url", "scope")):
        raise ValueError("Manifest must describe root-origin deployment")
    urls.extend(("manifest.json", icon["src"]) for icon in manifest.get("icons", []))
    for source, url in urls:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue  # External resources are not fetched or repackaged.
        path = parsed.path.lstrip("/") if parsed.path.startswith("/") else str(
            PurePosixPath(source).parent / parsed.path)
        if path not in blobs:
            raise ValueError(f"Missing public dependency: {source} -> {url}")


def collect_blobs(repo: Path, commit: str, files: list[str]) -> tuple[dict, dict]:
    resolved = git(repo, "rev-parse", f"{commit}^{{commit}}").decode().strip()
    if resolved != commit:
        raise ValueError("Resolved commit differs from pin")
    tree = {}
    for record in git(repo, "ls-tree", "-r", "-z", commit, "--", "docs/").split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        tree[raw_path.decode()] = (mode, kind, oid)
    blobs, evidence = {}, {}
    for name in files:
        entry = tree.get("docs/" + name)
        if entry is None or entry[0] not in {"100644", "100755"} or entry[1] != "blob":
            raise ValueError(f"Absent/non-regular Git asset (symlinks forbidden): {name}")
        payload = git(repo, "cat-file", "blob", entry[2])
        blobs[name] = payload
        evidence[name] = {"git_blob": entry[2], "sha256": hashlib.sha256(payload).hexdigest(),
                          "bytes": len(payload)}
    validate_dependencies(blobs)
    return blobs, evidence


def build(repo: Path, config_path: Path, output: Path) -> dict:
    raw_config = config_path.read_bytes()
    config = json.loads(raw_config)
    commit, files = validate_config(config)
    repo = repo.resolve()
    output = output.absolute()
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Output path must not traverse a symlink")
    output = output.resolve()
    # Do not overwrite checkout files. Only dist/ is an optional in-repo output.
    if output == repo or (repo in output.parents and output.relative_to(repo).parts[0] != "dist"):
        raise ValueError("In-repository output is restricted to dist/<new directory>")
    sidecar = output.with_name(output.name + ".evidence.json")
    if output.exists() or sidecar.exists():
        raise ValueError("Refusing to overwrite an existing output or evidence file")
    blobs, evidence = collect_blobs(repo, commit, files)
    result = {"schema_version": 1, "source_commit": commit, "source_root": "docs",
              "allowlist_sha256": hashlib.sha256(raw_config).hexdigest(),
              "pages_workflow_run": config.get("pages_workflow_run"),
              "file_count": len(evidence), "files": evidence}
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage only these blobs; never walk/copy the working tree or all docs/.
    with tempfile.TemporaryDirectory(prefix=".frontend-build-", dir=output.parent) as staging:
        public = Path(staging) / "public"
        public.mkdir()
        for name, payload in blobs.items():
            target = public / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        if output.exists() or output.is_symlink():
            raise ValueError("Output appeared during build; refusing replacement")
        os.rename(public, output)
    with sidecar.open("x", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True, help="New public/ directory; never overwritten")
    args = parser.parse_args()
    try:
        result = build(args.repo, args.allowlist, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Build refused: {exc}\n")
    print(f"Built {result['file_count']} files from {result['source_commit']}; no publish performed")


if __name__ == "__main__":
    main()
