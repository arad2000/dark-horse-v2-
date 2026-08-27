"""Controlled dual-run audit for Dark Horse V2 Hybrid migration.

The live application remains JSON-backed. This script only runs in staging/test
with an explicit confirmation flag. It materializes a second DarkHorseEngineV2
instance from PostgreSQL reference tables and compares its deterministic output
against the current JSON-backed engine for fixed fixtures.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import engine
from dark_horse_engine_v2 import DarkHorseEngineV2
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
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def rows(payload: Any, candidates: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in candidates:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    raise ValueError("Unsupported JSON collection shape")


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): normalize(value[k]) for k in sorted(value, key=lambda x: str(x))}
    if isinstance(value, list):
        return [normalize(x) for x in value]
    return value


def materialize_engine_from_db(db: Session) -> DarkHorseEngineV2:
    """Build an engine-compatible reference snapshot from PostgreSQL only."""
    motives = {row.code: row.description_fa for row in db.scalars(select(MicroMotive))}
    value_poles = {row.pole_code: row.description_fa for row in db.scalars(select(ValuePole))}
    trait_map: dict[str, dict[int, list[str]]] = {}
    for row in db.scalars(select(TraitOption)):
        trait_map.setdefault(row.question_code, {})[int(row.option_index)] = row.traits or []

    motive_code_by_id = {row.id: row.code for row in db.scalars(select(MicroMotive))}

    major_rows = list(db.scalars(select(Major)))
    major_motive_ids = {}
    for major_id, motive_id in db.execute(
        select(major_micro_motives.c.major_id, major_micro_motives.c.motive_id)
    ).all():
        major_motive_ids.setdefault(int(major_id), []).append(int(motive_id))

    majors: dict[int, dict[str, Any]] = {}
    for row in major_rows:
        majors[int(row.id)] = {
            "id": int(row.id),
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
            "micro_motive_codes": [
                motive_code_by_id[mid] for mid in major_motive_ids.get(int(row.id), [])
            ],
        }

    branch_rows = list(db.scalars(select(SchoolBranch)))
    branch_motive_ids = {}
    for branch_id, motive_id in db.execute(
        select(branch_micro_motives.c.branch_id, branch_micro_motives.c.motive_id)
    ).all():
        branch_motive_ids.setdefault(int(branch_id), []).append(int(motive_id))

    branches: list[dict[str, Any]] = []
    for row in branch_rows:
        branches.append({
            "id": row.id,
            "name": row.name,
            "group": row.group,
            "m_score_denom_limit": row.m_score_denom_limit,
            "strategy_weights": row.strategy_weights,
            "value_weights": row.value_weights,
            "weights_version": row.weights_version,
            "source_majors_count": row.source_majors_count,
            "micro_motive_codes": [
                motive_code_by_id[mid] for mid in branch_motive_ids.get(int(row.id), [])
            ],
        })

    # Construct the engine object without triggering filesystem loading.
    eng = DarkHorseEngineV2.__new__(DarkHorseEngineV2)
    eng.motives_map = motives
    eng.majors_db = majors
    eng.trait_map = trait_map
    eng.value_poles = value_poles
    eng.school_branches = {row["name"]: row for row in branches}
    eng._validate_schema_consistency()
    return eng


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    """Keep the dual-run comparison focused on semantic output."""
    return normalize(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args()

    if not args.confirm_staging:
        raise SystemExit("Refusing dual-run without --confirm-staging")
    if engine is None:
        raise SystemExit("DATABASE_URL is not configured")
    if is_postgres_runtime_enabled():
        raise SystemExit("FAIL: production PostgreSQL runtime gate is ON")

    motive_path = ROOT / "docs/data/micro_motives.json"
    major_path = ROOT / "majors_database_v2.json"
    trait_path = ROOT / "docs/data/trait_map_v3.json"
    value_path = ROOT / "value_poles_v2.json"
    branch_path = ROOT / "school_branches_v2.json"

    json_engine = DarkHorseEngineV2(
        motives_path=str(motive_path),
        majors_path=str(major_path),
        trait_map_path=str(trait_path),
        value_poles_path=str(value_path),
        school_branches_path=str(branch_path),
    )

    with Session(engine) as db:
        db_engine = materialize_engine_from_db(db)

    # Three deliberately different fixtures: motive-heavy, balanced, and branch-oriented.
    fixtures = [
        {
            "name": "motive_heavy",
            "motives": ["MED-001", "MED-004", "MED-007"],
            "sjt": {f"sjt_{i}": "A" for i in range(1, 26)},
            "conjoint": {f"conj_{i}": f"Q{i}A" for i in range(1, 16)},
        },
        {
            "name": "balanced",
            "motives": ["AI-001", "CS-001", "STAT-001"],
            "sjt": {f"sjt_{i}": ("ABCDE"[i % 5]) for i in range(1, 26)},
            "conjoint": {f"conj_{i}": f"Q{i}{'A' if i % 2 else 'B'}" for i in range(1, 16)},
        },
        {
            "name": "engineering",
            "motives": ["EE-001", "EE-004", "ME-001"],
            "sjt": {f"sjt_{i}": ("EDCBA"[i % 5]) for i in range(1, 26)},
            "conjoint": {f"conj_{i}": f"Q{i}B" for i in range(1, 16)},
        },
    ]

    fixture_reports = []
    for fixture in fixtures:
        base_major = json_engine.discover_individuality(
            fixture["motives"], fixture["sjt"], fixture["conjoint"]
        )
        db_major = db_engine.discover_individuality(
            fixture["motives"], fixture["sjt"], fixture["conjoint"]
        )
        base_branch = json_engine.recommend_school_branch(
            fixture["motives"], fixture["sjt"], fixture["conjoint"]
        )
        db_branch = db_engine.recommend_school_branch(
            fixture["motives"], fixture["sjt"], fixture["conjoint"]
        )

        major_equal = summarize(base_major) == summarize(db_major)
        branch_equal = summarize(base_branch) == summarize(db_branch)
        fixture_reports.append({
            "name": fixture["name"],
            "major_equal": major_equal,
            "branch_equal": branch_equal,
            "major_top3_json": [
                (x.get("major_id"), x["individuality_fit"]["score"])
                for x in base_major.get("discovered_majors", [])[:3]
            ],
            "branch_top": base_branch.get("best_branch"),
        })

    status = "PASS" if all(x["major_equal"] and x["branch_equal"] for x in fixture_reports) else "FAIL"
    report = {
        "status": status,
        "runtime_cutover": "OFF",
        "fixtures": fixture_reports,
        "contract": {
            "json_engine_is_live_source": True,
            "postgres_engine_used_only_for_staging_dual_run": True,
            "no_runtime_switch": not is_postgres_runtime_enabled(),
            "comparison_scope": [
                "full major discovery output",
                "full school-branch recommendation output",
                "ordering",
                "scores",
                "evidence",
                "warnings",
                "alternative paths",
            ],
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if status == "PASS" else 2)


if __name__ == "__main__":
    main()
