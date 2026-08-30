"""Controlled semantic dual-run audit for Dark Horse V2 Hybrid migration."""
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
from models import Major, MicroMotive, SchoolBranch, TraitOption, ValuePole, branch_micro_motives, major_micro_motives

ROOT = Path(__file__).resolve().parent
NON_SEMANTIC_BRANCH_FIELDS = {"count", "max_score", "min_score"}


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): normalize(value[k])
            for k in sorted(value, key=lambda x: str(x))
            if str(k) not in NON_SEMANTIC_BRANCH_FIELDS
        }
    if isinstance(value, list):
        return [normalize(x) for x in value]
    return value


def materialize_engine_from_db(db: Session) -> DarkHorseEngineV2:
    motives = {row.code: row.description_fa for row in db.scalars(select(MicroMotive))}
    values = {row.pole_code: row.description_fa for row in db.scalars(select(ValuePole))}
    traits: dict[str, dict[int, list[str]]] = {}
    for row in db.scalars(select(TraitOption)):
        traits.setdefault(row.question_code, {})[int(row.option_index)] = row.traits or []

    motive_code_by_id = {row.id: row.code for row in db.scalars(select(MicroMotive))}
    major_links: dict[int, list[str]] = {}
    for major_id, motive_id in db.execute(
        select(major_micro_motives.c.major_id, major_micro_motives.c.motive_id)
    ).all():
        major_links.setdefault(int(major_id), []).append(motive_code_by_id[int(motive_id)])

    majors: dict[int, dict[str, Any]] = {}
    for row in db.scalars(select(Major)):
        majors[int(row.id)] = {
            "id": int(row.id), "name": row.name, "group": row.group,
            "cluster": row.cluster, "subgroup": row.subgroup, "exam_group": row.exam_group,
            "high_school_branch": row.high_school_branch, "strategy_weights": row.strategy_weights,
            "value_weights": row.value_weights, "archetype": row.archetype,
            "fulfillment_source": row.fulfillment_source, "prestige_level": row.prestige_level,
            "handcrafted": row.handcrafted, "motive_driven": row.motive_driven,
            "weights_version": row.weights_version, "micro_motive_codes": major_links.get(int(row.id), []),
        }

    branch_links: dict[int, list[str]] = {}
    for branch_id, motive_id in db.execute(
        select(branch_micro_motives.c.branch_id, branch_micro_motives.c.motive_id)
    ).all():
        branch_links.setdefault(int(branch_id), []).append(motive_code_by_id[int(motive_id)])

    branches: list[dict[str, Any]] = []
    for row in db.scalars(select(SchoolBranch)):
        branches.append({
            "id": row.id, "name": row.name, "group": row.group,
            "m_score_denom_limit": row.m_score_denom_limit, "strategy_weights": row.strategy_weights,
            "value_weights": row.value_weights, "weights_version": row.weights_version,
            "source_majors_count": row.source_majors_count,
            "micro_motive_codes": branch_links.get(int(row.id), []),
        })

    eng = DarkHorseEngineV2.__new__(DarkHorseEngineV2)
    eng.motives_map = motives
    eng.majors_db = majors
    eng.trait_map = traits
    eng.value_poles = values
    eng.school_branches = {row["name"]: row for row in branches}
    eng._validate_schema_consistency()
    return eng


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

    json_engine = DarkHorseEngineV2(
        motives_path=str(ROOT / "docs/data/micro_motives.json"),
        majors_path=str(ROOT / "majors_database_v2.json"),
        trait_map_path=str(ROOT / "docs/data/trait_map_v3.json"),
        value_poles_path=str(ROOT / "value_poles_v2.json"),
        school_branches_path=str(ROOT / "school_branches_v2.json"),
    )
    with Session(engine) as db:
        db_engine = materialize_engine_from_db(db)

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
            "sjt": {f"sjt_{i}": "ABCDE"[i % 5] for i in range(1, 26)},
            "conjoint": {f"conj_{i}": f"Q{i}{'A' if i % 2 else 'B'}" for i in range(1, 16)},
        },
        {
            "name": "engineering",
            "motives": ["EE-001", "EE-004", "ME-001"],
            "sjt": {f"sjt_{i}": "EDCBA"[i % 5] for i in range(1, 26)},
            "conjoint": {f"conj_{i}": f"Q{i}B" for i in range(1, 16)},
        },
    ]

    reports = []
    for fixture in fixtures:
        jm = json_engine.discover_individuality(fixture["motives"], fixture["sjt"], fixture["conjoint"])
        pm = db_engine.discover_individuality(fixture["motives"], fixture["sjt"], fixture["conjoint"])
        jb = json_engine.recommend_school_branch(fixture["motives"], fixture["sjt"], fixture["conjoint"])
        pb = db_engine.recommend_school_branch(fixture["motives"], fixture["sjt"], fixture["conjoint"])

        major_equal = normalize(jm) == normalize(pm)
        branch_equal = normalize(jb) == normalize(pb)
        reports.append({
            "name": fixture["name"],
            "major_equal": major_equal,
            "branch_equal": branch_equal,
            "major_top3": [
                (x.get("major_id"), x["individuality_fit"]["score"])
                for x in jm.get("discovered_majors", [])[:3]
            ],
            "json_best_branch": jb.get("best_branch"),
            "postgres_best_branch": pb.get("best_branch"),
        })

    status = "PASS" if all(r["major_equal"] and r["branch_equal"] for r in reports) else "FAIL"
    report = {
        "status": status,
        "runtime_cutover": "OFF",
        "semantic_comparison": True,
        "ignored_branch_metadata": sorted(NON_SEMANTIC_BRANCH_FIELDS),
        "fixtures": reports,
        "contract": {
            "json_engine_is_live_source": True,
            "postgres_engine_used_only_for_staging_dual_run": True,
            "comparison_scope": [
                "recommendations", "ordering", "scores", "components",
                "evidence", "warnings", "best_branch", "alternative_paths",
            ],
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if status == "PASS" else 2)


if __name__ == "__main__":
    main()
