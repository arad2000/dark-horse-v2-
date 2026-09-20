"""CI guard: canonical reference JSON must match main exactly.

The scoring engine may legitimately differ between deployment branches while the
psychometric/reference data used by scoring must remain identical. This guard
compares only the canonical reference files listed below against origin/main.
"""

from __future__ import annotations

import argparse
import subprocess

REFERENCE_FILES = (
    "docs/data/micro_motives.json",
    "docs/data/questions_v2.json",
    "docs/data/trait_map_v3.json",
    "majors_database_v2.json",
    "school_branches_v2.json",
    "value_poles_v2.json",
)


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def blob_sha(ref: str, path: str) -> str:
    return run("git", "rev-parse", f"{ref}:{path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="origin/main")
    args = parser.parse_args()

    failures: list[str] = []
    report: list[dict[str, str | bool]] = []

    for path in REFERENCE_FILES:
        try:
            head_sha = blob_sha("HEAD", path)
            base_sha = blob_sha(args.base_ref, path)
        except subprocess.CalledProcessError as exc:
            failures.append(f"{path}: missing/unresolvable ({exc})")
            continue

        same = head_sha == base_sha
        report.append({
            "path": path,
            "same": same,
            "head_sha": head_sha,
            "main_sha": base_sha,
        })
        if not same:
            failures.append(
                f"{path}: HEAD blob {head_sha} != {args.base_ref} blob {base_sha}"
            )

    print("Reference-data sync audit")
    for row in report:
        print(
            f"[{'PASS' if row['same'] else 'FAIL'}] {row['path']} "
            f"HEAD={row['head_sha']} MAIN={row['main_sha']}"
        )

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        print(
            "\nScoring/reference JSON must remain synchronized with main. "
            "Do not enable Hybrid cutover while this guard fails."
        )
        return 1

    print("\nPASS: all canonical reference files match origin/main exactly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
