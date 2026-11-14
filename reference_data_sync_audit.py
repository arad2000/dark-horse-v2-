"""CI guard for the documented main/deploy reference-data contract.

Exact Git-blob equality is required only for the reference inputs that are shared
between main and deploy. The runtime-owned scientific files may intentionally
differ during the controlled review period described in
docs/audits/MAIN_DEPLOY_CONTRACT.md. They are not silently trusted: this guard
requires strict JSON and the downstream reference_contract_audit.py plus
finite-reference startup tests validate their structure and references.

This audit is read-only. It does not modify data or authorize Hybrid cutover.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

SHARED_REFERENCE_FILES = (
    "docs/data/questions_v2.json",
    "docs/data/trait_map_v3.json",
    "value_poles_v2.json",
)

RUNTIME_OWNED_REFERENCE_FILES = (
    "docs/data/micro_motives.json",
    "majors_database_v2.json",
    "school_branches_v2.json",
)


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def blob_sha(ref: str, path: str) -> str:
    return run("git", "rev-parse", f"{ref}:{path}")


def _reject_non_finite(raw: str) -> None:
    raise ValueError(f"non-standard or non-finite JSON number: {raw}")


def _parse_finite_float(raw: str) -> float:
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"non-finite JSON number: {raw}")
    return value


def load_strict_json(path: Path) -> Any:
    """Reject NaN/Infinity and exponent overflow before structural validation."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(
            handle,
            parse_constant=_reject_non_finite,
            parse_float=_parse_finite_float,
        )


def validate_runtime_owned_file(relative_path: str, root: Path = Path(".")) -> dict[str, Any]:
    path = root / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"runtime-owned reference missing: {relative_path}")
    payload = load_strict_json(path)
    if not isinstance(payload, list) or not payload:
        raise ValueError(
            f"runtime-owned reference must be a non-empty JSON array: {relative_path}"
        )
    if any(not isinstance(row, dict) for row in payload):
        raise ValueError(f"reference contains a non-object row: {relative_path}")
    return {
        "path": relative_path,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(payload),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="origin/main")
    args = parser.parse_args()

    failures: list[str] = []
    shared_report: list[dict[str, str | bool]] = []
    runtime_report: list[dict[str, str | int]] = []

    print("Reference-data governance audit")
    print(f"Shared-byte-equality base: {args.base_ref}")

    for path in SHARED_REFERENCE_FILES:
        try:
            head_sha = blob_sha("HEAD", path)
            base_sha = blob_sha(args.base_ref, path)
        except subprocess.CalledProcessError as exc:
            failures.append(f"{path}: missing/unresolvable ({exc})")
            continue

        same = head_sha == base_sha
        shared_report.append(
            {
                "path": path,
                "same": same,
                "head_blob_sha": head_sha,
                "main_blob_sha": base_sha,
            }
        )
        if not same:
            failures.append(
                f"{path}: HEAD blob {head_sha} != {args.base_ref} blob {base_sha}"
            )

    print("\nShared reference inputs (exact equality required):")
    for row in shared_report:
        print(
            f"[{'PASS' if row['same'] else 'FAIL'}] {row['path']} "
            f"HEAD={row['head_blob_sha']} MAIN={row['main_blob_sha']}"
        )

    print(
        "\nRuntime-owned reference inputs (not compared byte-for-byte to main; "
        "strict JSON/existence checked here and full contracts remain required):"
    )
    for path in RUNTIME_OWNED_REFERENCE_FILES:
        try:
            row = validate_runtime_owned_file(path)
            runtime_report.append(row)
            print(
                f"[PASS] {row['path']} rows={row['rows']} sha256={row['sha256']}"
            )
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"{path}: strict runtime reference check failed: {exc}")
            print(f"[FAIL] {path}: {exc}")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        print("\nGovernance audit failed. Hybrid cutover remains prohibited.")
        return 1

    print(
        "\nPASS: shared inputs match main and runtime-owned inputs are present "
        "and strict-JSON parseable."
    )
    print(
        "NOTE: this is not the final data-quality verdict. The downstream "
        "reference_contract_audit.py, finite-reference startup contracts, "
        "and all CI checks remain mandatory. POSTGRES_RUNTIME_CUTOVER_APPROVED "
        "must remain false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
