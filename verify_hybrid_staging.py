"""Read-only verification for a staged Hybrid PostgreSQL import.

This script never changes the database and never enables production runtime use.
It checks that database row counts and natural keys agree with the JSON source of truth.
Run only against a staging/test DATABASE_URL after Alembic has been applied and the
seed utility has completed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import engine
from models import Major, MicroMotive, SchoolBranch, TraitOption, ValuePole

ROOT = Path(__file__).resolve().parent


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_records(payload: Any, candidates: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in candidates:
            rows = payload.get(key)
            if isinstance(rows, list):
                return [x for x in rows if isinstance(x, dict)]
    raise ValueError("Unsupported JSON shape")


def expected_trait_pairs(payload: Any) -> set[tuple[str, int]]:
    if not isinstance(payload, dict):
        raise ValueError("trait_map must be an object")
    pairs: set[tuple[str, int]] = set()
    for qcode, row in payload.items():
        if not isinstance(row, dict):
            continue
        options = row.get("options")
        if isinstance(options, list):
            pairs.update((str(qcode), idx) for idx, _ in enumerate(options))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args()
    if not args.confirm_staging:
        raise SystemExit("Refusing verification without --confirm-staging")
    if engine is None:
        raise SystemExit("DATABASE_URL is not configured")

    files = {
        "micro_motives": ROOT / "docs/data/micro_motives.json",
        "majors": ROOT / "majors_database_v2.json",
        "school_branches": ROOT / "school_branches_v2.json",
        "value_poles": ROOT / "value_poles_v2.json",
        "trait_map": ROOT / "docs/data/trait_map_v3.json",
    }
    for path in files.values():
        if not path.exists():
            raise SystemExit(f"missing:{path}")

    motives = as_records(load(files["micro_motives"]), ("micro_motives", "motives", "data"))
    majors = as_records(load(files["majors"]), ("majors", "data"))
    branches = as_records(load(files["school_branches"]), ("school_branches", "branches", "data"))
    values = as_records(load(files["value_poles"]), ("value_poles", "poles", "data"))
    traits = expected_trait_pairs(load(files["trait_map"]))

    expected_motive_codes = {str(r.get("code")) for r in motives if r.get("code")}
    expected_major_ids = {int(r.get("id") if r.get("id") is not None else r.get("major_id")) for r in majors if r.get("id") is not None or r.get("major_id") is not None}
    expected_branch_names = {str(r.get("name") or r.get("branch_name")).strip() for r in branches if r.get("name") or r.get("branch_name")}
    expected_value_codes = {str(r.get("pole_code") or r.get("code")) for r in values if r.get("pole_code") or r.get("code")}

    with Session(engine) as db:
        actual_motive_codes = set(db.scalars(select(MicroMotive.code)))
        actual_major_ids = set(db.scalars(select(Major.id)))
        actual_branch_names = set(db.scalars(select(SchoolBranch.name)))
        actual_value_codes = set(db.scalars(select(ValuePole.pole_code)))
        actual_trait_pairs = set(db.execute(select(TraitOption.question_code, TraitOption.option_index)).all())

        counts = {
            "micro_motives": db.scalar(select(func.count()).select_from(MicroMotive)),
            "majors": db.scalar(select(func.count()).select_from(Major)),
            "school_branches": db.scalar(select(func.count()).select_from(SchoolBranch)),
            "value_poles": db.scalar(select(func.count()).select_from(ValuePole)),
            "trait_options": db.scalar(select(func.count()).select_from(TraitOption)),
        }

    comparisons = {
        "micro_motives_exact_codes": expected_motive_codes == actual_motive_codes,
        "majors_exact_ids": expected_major_ids == actual_major_ids,
        "school_branches_exact_names": expected_branch_names == actual_branch_names,
        "value_poles_exact_codes": expected_value_codes == actual_value_codes,
        "trait_option_keys_exact": traits == actual_trait_pairs,
    }

    report = {
        "status": "PASS" if all(comparisons.values()) else "FAIL",
        "runtime_cutover": "OFF",
        "counts": counts,
        "expected_counts": {
            "micro_motives": len(motives),
            "majors": len(majors),
            "school_branches": len(branches),
            "value_poles": len(values),
            "trait_options": len(traits),
        },
        "comparisons": comparisons,
        "source_sha256": {name: sha256(path) for name, path in files.items()},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
