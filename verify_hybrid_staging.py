"""Read-only verification for a staged Hybrid PostgreSQL import.

The JSON files remain the source of truth. This verifier connects only to the
explicit staging DATABASE_URL and compares exact key/content sets. It never
modifies the database and never enables production PostgreSQL runtime use.

All motive associations, including BIOTM-001..007, are compared exactly.
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
from migration_control import is_postgres_runtime_enabled
from models import (
    Major,
    MicroMotive,
    SchoolBranch,
    TraitOption,
    ValuePole,
    branch_micro_motives,
    major_micro_motives,
)

ROOT = Path(__file__).resolve().parent

def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collection_records(payload: Any, candidates: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in candidates:
            rows = payload.get(key)
            if isinstance(rows, list):
                return [x for x in rows if isinstance(x, dict)]
    raise ValueError(f"Unsupported JSON collection shape; expected {candidates}")


def parse_value_poles(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("value_poles_v2.json must be an object")
    result: dict[str, dict[str, Any]] = {}
    for raw_code, description in payload.items():
        code = str(raw_code).strip().upper()
        if not code.startswith("Q") or len(code) < 3 or code[-1] not in {"A", "B"}:
            raise ValueError(f"Invalid value pole code: {raw_code}")
        try:
            question_num = int(code[1:-1])
        except ValueError as exc:
            raise ValueError(f"Invalid value pole question number: {raw_code}") from exc
        result[code] = {
            "pole_code": code,
            "question_num": question_num,
            "option_letter": code[-1],
            "description_fa": str(description),
        }
    return result


def parse_traits(payload: Any) -> dict[tuple[str, int], list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("trait_map_v3.json must be an object")
    expected_questions = [f"S{i:02d}" for i in range(1, 26)]
    actual_questions = sorted(str(k) for k in payload)
    if actual_questions != expected_questions:
        raise ValueError(f"Strategy question IDs mismatch: {actual_questions}")

    result: dict[tuple[str, int], list[str]] = {}
    for qcode in expected_questions:
        row = payload[qcode]
        if not isinstance(row, dict):
            raise ValueError(f"{qcode} must be an object")
        raw_keys = list(row.keys())
        numeric_keys = []
        for raw in raw_keys:
            key = str(raw)
            if not key.isdigit():
                raise ValueError(f"{qcode} has non-numeric option key: {raw}")
            numeric_keys.append(int(key))
        if sorted(numeric_keys) != [0, 1, 2, 3, 4]:
            raise ValueError(f"{qcode} must contain exactly options 0..4")
        for raw, idx in sorted(((str(k), int(str(k))) for k in raw_keys), key=lambda x: x[1]):
            traits = row[raw]
            if not isinstance(traits, list) or not all(isinstance(t, str) and t.strip() for t in traits):
                raise ValueError(f"{qcode}[{idx}] must be a non-empty list of trait strings")
            result[(qcode, idx)] = [str(t) for t in traits]
    return result


def expected_major(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row.get("id") if row.get("id") is not None else row["major_id"]),
        "name": row.get("name") or row.get("major_name_fa") or row.get("major_name"),
        "group": row.get("group") or row.get("realm_fa") or "",
        "cluster": row.get("cluster"),
        "subgroup": row.get("subgroup"),
        "exam_group": row.get("exam_group"),
        "high_school_branch": row.get("high_school_branch"),
        "strategy_weights": row.get("strategy_weights") or row.get("strategy_profile") or {},
        "value_weights": row.get("value_weights") or {},
        "archetype": row.get("archetype"),
        "fulfillment_source": row.get("fulfillment_source"),
        "prestige_level": row.get("prestige_level"),
        "handcrafted": row.get("handcrafted", True),
        "motive_driven": row.get("motive_driven", True),
        "weights_version": row.get("weights_version"),
    }


def actual_major(row: Major) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "group": row.group,
        "cluster": row.cluster,
        "subgroup": row.subgroup,
        "exam_group": row.exam_group,
        "high_school_branch": row.high_school_branch,
        "strategy_weights": row.strategy_weights,
        "value_weights": row.value_weights,
        "archetype": row.archetype,
        "fulfillment_source": row.fulfillment_source,
        "prestige_level": row.prestige_level,
        "handcrafted": row.handcrafted,
        "motive_driven": row.motive_driven,
        "weights_version": row.weights_version,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args()
    if not args.confirm_staging:
        raise SystemExit("Refusing verification without --confirm-staging")
    if engine is None:
        raise SystemExit("DATABASE_URL is not configured")
    if is_postgres_runtime_enabled():
        raise SystemExit("FAIL: production PostgreSQL runtime gate is ON")

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

    motive_rows = collection_records(load(files["micro_motives"]), ("micro_motives", "motives", "data"))
    major_rows = collection_records(load(files["majors"]), ("majors", "data"))
    branch_rows = collection_records(load(files["school_branches"]), ("school_branches", "branches", "data"))
    value_rows = parse_value_poles(load(files["value_poles"]))
    trait_rows = parse_traits(load(files["trait_map"]))

    expected_motives = {
        str(r["code"]).strip(): str(r.get("description_fa") or r.get("text") or "")
        for r in motive_rows if r.get("code")
    }
    expected_majors = {
        int(r.get("id") if r.get("id") is not None else r["major_id"]): expected_major(r)
        for r in major_rows if r.get("id") is not None or r.get("major_id") is not None
    }
    expected_branches = {
        str(r.get("name") or r.get("branch_name")).strip(): r
        for r in branch_rows if r.get("name") or r.get("branch_name")
    }

    expected_major_links = {
        (int(r.get("id") if r.get("id") is not None else r["major_id"]), str(code).strip())
        for r in major_rows
        for code in (r.get("micro_motive_codes") or [])
    }
    expected_branch_links = {
        (str(r.get("name") or r.get("branch_name")).strip(), str(code).strip())
        for r in branch_rows
        for code in (r.get("micro_motive_codes") or [])
    }
    with Session(engine) as db:
        db_motives = {row.code: row.description_fa for row in db.scalars(select(MicroMotive))}
        db_majors = {row.id: actual_major(row) for row in db.scalars(select(Major))}
        db_branches = {row.name: row for row in db.scalars(select(SchoolBranch))}
        db_values = {
            row.pole_code: {
                "pole_code": row.pole_code,
                "question_num": row.question_num,
                "option_letter": row.option_letter,
                "description_fa": row.description_fa,
            }
            for row in db.scalars(select(ValuePole))
        }
        db_traits = {
            (row.question_code, int(row.option_index)): row.traits or []
            for row in db.scalars(select(TraitOption))
        }
        motive_id_to_code = {row.id: row.code for row in db.scalars(select(MicroMotive))}
        branch_id_to_name = {row.id: row.name for row in db.scalars(select(SchoolBranch))}
        db_major_links = {
            (int(major_id), motive_id_to_code[int(motive_id)])
            for major_id, motive_id in db.execute(
                select(major_micro_motives.c.major_id, major_micro_motives.c.motive_id)
            ).all()
        }
        db_branch_links = {
            (branch_id_to_name[int(branch_id)], motive_id_to_code[int(motive_id)])
            for branch_id, motive_id in db.execute(
                select(branch_micro_motives.c.branch_id, branch_micro_motives.c.motive_id)
            ).all()
        }
        counts = {
            "micro_motives": db.scalar(select(func.count()).select_from(MicroMotive)),
            "majors": db.scalar(select(func.count()).select_from(Major)),
            "school_branches": db.scalar(select(func.count()).select_from(SchoolBranch)),
            "value_poles": db.scalar(select(func.count()).select_from(ValuePole)),
            "trait_options": db.scalar(select(func.count()).select_from(TraitOption)),
        }

    comparisons = {
        "micro_motive_content_exact": expected_motives == db_motives,
        "major_content_exact": expected_majors == db_majors,
        "school_branch_names_exact": set(expected_branches) == set(db_branches),
        "value_pole_content_exact": value_rows == db_values,
        "trait_option_content_exact": trait_rows == db_traits,
        "major_motive_routes_exact": expected_major_links == db_major_links,
        "branch_motive_routes_exact": expected_branch_links == db_branch_links,
    }

    report = {
        "status": "PASS" if all(comparisons.values()) else "FAIL",
        "runtime_cutover": "OFF",
        "counts": counts,
        "expected_counts": {
            "micro_motives": len(expected_motives),
            "majors": len(expected_majors),
            "school_branches": len(expected_branches),
            "value_poles": len(value_rows),
            "trait_options": len(trait_rows),
        },
        "comparisons": comparisons,
        "deferred": {
            "prefixes": [],
            "major_motive_routes": 0,
            "branch_motive_routes": 0,
            "total": 0,
            "note": "BIOTM correction complete; no deferred motive prefixes remain",
        },
        "source_sha256": {name: sha256(path) for name, path in files.items()},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
