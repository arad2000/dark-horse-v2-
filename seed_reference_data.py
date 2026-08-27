"""Deterministic JSON -> PostgreSQL seed utility for Dark Horse V2 Hybrid migration.

Safety contract:
- Reference JSON files remain the source of truth.
- This utility only writes to an explicitly configured PostgreSQL database.
- It never changes scoring, ranking, Strategy, Value, or Engine logic.
- It is intended for staging/validation before any production cutover.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import engine
from models import Base, MicroMotive, ValuePole, Major, SchoolBranch, TraitOption

ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_json(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def as_records(payload: Any, candidates: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in candidates:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    raise ValueError("Unsupported JSON shape")


def seed_reference_data(db: Session, base: Path) -> dict[str, Any]:
    motives_path = base / "docs" / "data" / "micro_motives.json"
    majors_path = base / "majors_database_v2.json"
    branches_path = base / "school_branches_v2.json"
    values_path = base / "value_poles_v2.json"
    trait_path = base / "docs" / "data" / "trait_map_v3.json"

    for p in (motives_path, majors_path, branches_path, values_path, trait_path):
        if not p.exists():
            raise FileNotFoundError(p)

    motive_records = as_records(load_json(motives_path), ("micro_motives", "motives", "data"))
    major_records = as_records(load_json(majors_path), ("majors", "data"))
    branch_records = as_records(load_json(branches_path), ("school_branches", "branches", "data"))
    value_records = as_records(load_json(values_path), ("value_poles", "poles", "data"))
    trait_payload = load_json(trait_path)
    trait_records: list[dict[str, Any]] = []
    if isinstance(trait_payload, dict):
        for qcode, row in trait_payload.items():
            options = row.get("options") if isinstance(row, dict) else None
            if isinstance(options, list):
                for idx, opt in enumerate(options):
                    if isinstance(opt, dict):
                        trait_records.append({"question_code": qcode, "option_index": idx, **opt})

    # Seed by natural keys and update only reference fields. Operational tables are untouched.
    for item in motive_records:
        code = item.get("code")
        if not code:
            raise ValueError("Micro-motive without code")
        row = db.scalar(select(MicroMotive).where(MicroMotive.code == code))
        if row is None:
            row = MicroMotive(code=code, description_fa=item.get("description_fa") or item.get("text") or "")
            db.add(row)
        row.description_fa = item.get("description_fa") or item.get("text") or row.description_fa
        row.category = item.get("category")
        row.intensity_level = item.get("intensity_level")

    for item in value_records:
        code = item.get("pole_code") or item.get("code")
        if not code:
            continue
        row = db.scalar(select(ValuePole).where(ValuePole.pole_code == code))
        if row is None:
            row = ValuePole(pole_code=code, question_num=item.get("question_num", 0), option_letter=item.get("option_letter", ""), description_fa=item.get("description_fa") or item.get("text") or "")
            db.add(row)

    for item in trait_records:
        qcode = item.get("question_code")
        idx = item.get("option_index")
        if qcode is None or idx is None:
            continue
        row = db.scalar(select(TraitOption).where(TraitOption.question_code == qcode, TraitOption.option_index == idx))
        if row is None:
            row = TraitOption(question_code=qcode, option_index=idx, traits=item.get("traits"), description_fa=item.get("description_fa"))
            db.add(row)

    for item in major_records:
        mid = item.get("id") or item.get("major_id")
        name = item.get("name") or item.get("major_name_fa") or item.get("major_name")
        if mid is None or not name:
            continue
        row = db.get(Major, int(mid))
        if row is None:
            row = Major(id=int(mid), name=name, group=item.get("group") or item.get("realm_fa") or "", strategy_weights=item.get("strategy_weights") or item.get("strategy_profile") or {}, value_weights=item.get("value_weights") or {})
            db.add(row)
        row.name = name
        row.group = item.get("group") or item.get("realm_fa") or row.group
        row.cluster = item.get("cluster")
        row.subgroup = item.get("subgroup")
        row.exam_group = item.get("exam_group")
        row.high_school_branch = item.get("high_school_branch")
        row.strategy_weights = item.get("strategy_weights") or item.get("strategy_profile") or row.strategy_weights
        row.value_weights = item.get("value_weights") or row.value_weights
        row.archetype = item.get("archetype")
        row.fulfillment_source = item.get("fulfillment_source")
        row.prestige_level = item.get("prestige_level")
        row.handcrafted = item.get("handcrafted", row.handcrafted)
        row.motive_driven = item.get("motive_driven", row.motive_driven)
        row.weights_version = item.get("weights_version")

    for item in branch_records:
        bid = item.get("id") or item.get("branch_id")
        name = item.get("name") or item.get("branch_name")
        if bid is None or not name:
            continue
        row = db.get(SchoolBranch, int(bid))
        if row is None:
            row = SchoolBranch(id=int(bid), name=name, group=item.get("group") or "", strategy_weights=item.get("strategy_weights") or {}, value_weights=item.get("value_weights") or {})
            db.add(row)
        row.name = name
        row.group = item.get("group") or row.group
        row.m_score_denom_limit = item.get("m_score_denom_limit", row.m_score_denom_limit)
        row.strategy_weights = item.get("strategy_weights") or row.strategy_weights
        row.value_weights = item.get("value_weights") or row.value_weights
        row.weights_version = item.get("weights_version")
        row.source_majors_count = item.get("source_majors_count")

    db.commit()
    return {
        "counts": {
            "micro_motives": len(motive_records),
            "value_poles": len(value_records),
            "trait_options": len(trait_records),
            "majors": len(major_records),
            "school_branches": len(branch_records),
        },
        "source_sha256": {str(p.relative_to(base)): sha256_json(p) for p in (motives_path, majors_path, branches_path, values_path, trait_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-staging", action="store_true", help="Explicitly confirm this command targets staging/test DB")
    args = parser.parse_args()
    if not args.confirm_staging:
        raise SystemExit("Refusing to seed without --confirm-staging")
    if engine is None:
        raise SystemExit("DATABASE_URL is not configured")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        report = seed_reference_data(db, ROOT)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
