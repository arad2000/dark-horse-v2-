"""Deterministic JSON -> PostgreSQL seed utility for Dark Horse V2 Hybrid.

Safety contract:
- Reference JSON files remain the source of truth.
- The command only writes when --confirm-staging is supplied.
- It does not enable production PostgreSQL runtime use.
- It preserves natural keys and many-to-many mappings from the JSON sources.
- It assumes the Alembic schema has already been applied to the staging DB.
- Any unresolved reference mapping aborts the seed before commit.
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
from models import (
    Base,
    Major,
    MicroMotive,
    SchoolBranch,
    TraitOption,
    ValuePole,
    branch_micro_motives,
    major_micro_motives,
)

ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_records(payload: Any, candidates: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in candidates:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    raise ValueError("Unsupported JSON shape")


def parse_trait_options(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("trait_map_v3.json must be an object keyed by question code")
    result: list[dict[str, Any]] = []
    for qcode, row in payload.items():
        if not isinstance(row, dict):
            continue
        options = row.get("options")
        if not isinstance(options, list):
            continue
        for idx, opt in enumerate(options):
            if isinstance(opt, dict):
                result.append({"question_code": str(qcode), "option_index": idx, **opt})
    return result


def _require_reference_codes(
    owners: list[tuple[str, dict[str, Any], list[str]]], known_codes: set[str]
) -> int:
    """Fail closed on any major/branch -> motive reference that cannot resolve."""
    missing: list[tuple[str, str, str]] = []
    total = 0
    for owner_kind, item, codes in owners:
        owner_key = str(item.get("id") or item.get("major_id") or item.get("name") or item.get("branch_name") or "?")
        for raw_code in codes:
            code = str(raw_code).strip()
            total += 1
            if code not in known_codes:
                missing.append((owner_kind, owner_key, code))
    if missing:
        preview = "; ".join(f"{kind}:{owner}:{code}" for kind, owner, code in missing[:20])
        suffix = " ..." if len(missing) > 20 else ""
        raise ValueError(
            f"Unresolved micro-motive references: {len(missing)} ({preview}{suffix})"
        )
    return total


def seed_reference_data(db: Session, base: Path) -> dict[str, Any]:
    motives_path = base / "docs" / "data" / "micro_motives.json"
    majors_path = base / "majors_database_v2.json"
    branches_path = base / "school_branches_v2.json"
    values_path = base / "value_poles_v2.json"
    trait_path = base / "docs" / "data" / "trait_map_v3.json"
    source_paths = (motives_path, majors_path, branches_path, values_path, trait_path)

    for path in source_paths:
        if not path.exists():
            raise FileNotFoundError(path)

    motive_records = as_records(load_json(motives_path), ("micro_motives", "motives", "data"))
    major_records = as_records(load_json(majors_path), ("majors", "data"))
    branch_records = as_records(load_json(branches_path), ("school_branches", "branches", "data"))
    value_records = as_records(load_json(values_path), ("value_poles", "poles", "data"))
    trait_records = parse_trait_options(load_json(trait_path))

    motive_by_code: dict[str, MicroMotive] = {}
    motive_codes: set[str] = set()

    for item in motive_records:
        code = str(item.get("code") or "").strip()
        if not code:
            raise ValueError("Micro-motive without code")
        if code in motive_codes:
            raise ValueError(f"Duplicate micro-motive code: {code}")
        row = db.scalar(select(MicroMotive).where(MicroMotive.code == code))
        if row is None:
            row = MicroMotive(code=code, description_fa=item.get("description_fa") or item.get("text") or "")
            db.add(row)
        row.description_fa = item.get("description_fa") or item.get("text") or row.description_fa
        row.category = item.get("category")
        row.intensity_level = item.get("intensity_level")
        motive_by_code[code] = row
        motive_codes.add(code)

    # Validate all JSON references before any destructive association-table operation.
    reference_owners = []
    for item in major_records:
        reference_owners.append(("major", item, [str(x) for x in (item.get("micro_motive_codes") or [])]))
    for item in branch_records:
        reference_owners.append(("branch", item, [str(x) for x in (item.get("micro_motive_codes") or [])]))
    total_references = _require_reference_codes(reference_owners, motive_codes)

    db.flush()

    value_by_code: dict[str, ValuePole] = {}
    for item in value_records:
        code = str(item.get("pole_code") or item.get("code") or "").strip()
        if not code:
            continue
        row = db.scalar(select(ValuePole).where(ValuePole.pole_code == code))
        if row is None:
            row = ValuePole(
                pole_code=code,
                question_num=int(item.get("question_num") or 0),
                option_letter=str(item.get("option_letter") or ""),
                description_fa=item.get("description_fa") or item.get("text") or "",
            )
            db.add(row)
        else:
            row.question_num = int(item.get("question_num") or row.question_num or 0)
            row.option_letter = str(item.get("option_letter") or row.option_letter or "")
            row.description_fa = item.get("description_fa") or item.get("text") or row.description_fa
        value_by_code[code] = row

    for item in trait_records:
        qcode = str(item.get("question_code") or "").strip()
        idx = item.get("option_index")
        if not qcode or idx is None:
            continue
        idx = int(idx)
        row = db.scalar(
            select(TraitOption).where(
                TraitOption.question_code == qcode,
                TraitOption.option_index == idx,
            )
        )
        if row is None:
            row = TraitOption(
                question_code=qcode,
                option_index=idx,
                traits=item.get("traits"),
                description_fa=item.get("description_fa"),
            )
            db.add(row)
        else:
            row.traits = item.get("traits")
            row.description_fa = item.get("description_fa")

    db.flush()

    major_by_id: dict[int, Major] = {}
    for item in major_records:
        if item.get("id") is None and item.get("major_id") is None:
            continue
        major_id = int(item.get("id") if item.get("id") is not None else item.get("major_id"))
        name = str(item.get("name") or item.get("major_name_fa") or item.get("major_name") or "").strip()
        if not name:
            raise ValueError(f"Major {major_id} has no name")
        row = db.get(Major, major_id)
        if row is None:
            row = Major(
                id=major_id,
                name=name,
                group=item.get("group") or item.get("realm_fa") or "",
                strategy_weights=item.get("strategy_weights") or item.get("strategy_profile") or {},
                value_weights=item.get("value_weights") or {},
            )
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
        major_by_id[major_id] = row

    branch_by_name: dict[str, SchoolBranch] = {}
    for item in branch_records:
        name = str(item.get("name") or item.get("branch_name") or "").strip()
        if not name:
            continue
        row = db.scalar(select(SchoolBranch).where(SchoolBranch.name == name))
        if row is None:
            row = SchoolBranch(
                name=name,
                group=item.get("group") or "",
                strategy_weights=item.get("strategy_weights") or {},
                value_weights=item.get("value_weights") or {},
            )
            db.add(row)
        row.group = item.get("group") or row.group
        row.m_score_denom_limit = item.get("m_score_denom_limit", row.m_score_denom_limit)
        row.strategy_weights = item.get("strategy_weights") or row.strategy_weights
        row.value_weights = item.get("value_weights") or row.value_weights
        row.weights_version = item.get("weights_version")
        row.source_majors_count = item.get("source_majors_count")
        branch_by_name[name] = row

    db.flush()

    # Rebuild reference-only associations atomically after all validation succeeds.
    db.execute(major_micro_motives.delete())
    db.execute(branch_micro_motives.delete())
    db.flush()

    major_links = 0
    for item in major_records:
        major_id = item.get("id") if item.get("id") is not None else item.get("major_id")
        if major_id is None:
            continue
        major = major_by_id.get(int(major_id))
        if major is None:
            continue
        for code in item.get("micro_motive_codes") or []:
            motive = motive_by_code[str(code).strip()]
            major.micro_motives.append(motive)
            major_links += 1

    branch_links = 0
    for item in branch_records:
        name = str(item.get("name") or item.get("branch_name") or "").strip()
        branch = branch_by_name.get(name)
        if branch is None:
            continue
        for code in item.get("micro_motive_codes") or []:
            motive = motive_by_code[str(code).strip()]
            branch.micro_motives.append(motive)
            branch_links += 1

    db.commit()

    return {
        "status": "PASS",
        "counts": {
            "micro_motives": len(motive_records),
            "value_poles": len(value_records),
            "trait_options": len(trait_records),
            "majors": len(major_records),
            "school_branches": len(branch_records),
            "major_micro_motive_references": total_references,
            "major_micro_motive_links": major_links,
            "branch_micro_motive_links": branch_links,
        },
        "source_sha256": {
            str(path.relative_to(base)): sha256_file(path) for path in source_paths
        },
        "runtime_cutover": "OFF",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Dark Horse reference data into staging PostgreSQL")
    parser.add_argument(
        "--confirm-staging",
        action="store_true",
        help="Explicitly confirm that DATABASE_URL points at a staging/test database",
    )
    args = parser.parse_args()

    if not args.confirm_staging:
        raise SystemExit("Refusing to seed without --confirm-staging")
    if engine is None:
        raise SystemExit("DATABASE_URL is not configured")

    # Do not bootstrap schema here. Schema lifecycle belongs to Alembic.
    with Session(engine) as db:
        report = seed_reference_data(db, ROOT)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
