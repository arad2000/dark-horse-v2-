"""Deterministic JSON -> PostgreSQL seed utility for Dark Horse V2 Hybrid.

Safety contract:
- Reference JSON files remain the source of truth.
- The command only writes when --confirm-staging is supplied.
- It never enables production PostgreSQL runtime use.
- It preserves natural keys and many-to-many mappings from the JSON sources.
- Alembic owns schema lifecycle; this script does not create/drop schema.
- BIOTM-* motive references are intentionally deferred; non-BIOTM unresolved
  references remain hard failures.
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
    Major,
    MicroMotive,
    SchoolBranch,
    TraitOption,
    ValuePole,
    branch_micro_motives,
    major_micro_motives,
)

ROOT = Path(__file__).resolve().parent
DEFERRED_MOTIVE_PREFIXES = ("BIOTM-",)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collection_records(payload: Any, candidates: tuple[str, ...]) -> list[dict[str, Any]]:
    """Read list-shaped reference collections."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in candidates:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    raise ValueError(f"Unsupported JSON collection shape; expected one of {candidates}")


def parse_value_poles(payload: Any) -> list[dict[str, Any]]:
    """Normalize canonical Q1A..Q15B dict into DB rows."""
    if not isinstance(payload, dict):
        raise ValueError("value_poles_v2.json must be an object")
    result: list[dict[str, Any]] = []
    for raw_code, description in payload.items():
        code = str(raw_code).strip().upper()
        if not code.startswith("Q") or len(code) < 3 or code[-1] not in {"A", "B"}:
            raise ValueError(f"Invalid value pole code: {raw_code}")
        try:
            question_num = int(code[1:-1])
        except ValueError as exc:
            raise ValueError(f"Invalid value pole question number: {raw_code}") from exc
        result.append({
            "pole_code": code,
            "question_num": question_num,
            "option_letter": code[-1],
            "description_fa": str(description),
        })
    return result


def parse_trait_options(payload: Any) -> list[dict[str, Any]]:
    """Normalize canonical trait_map_v3 S01..S25 object into option rows."""
    if not isinstance(payload, dict):
        raise ValueError("trait_map_v3.json must be an object keyed by S01..S25")

    expected_questions = [f"S{i:02d}" for i in range(1, 26)]
    actual_questions = sorted(str(k) for k in payload.keys())
    if actual_questions != expected_questions:
        raise ValueError(
            f"Strategy question IDs mismatch: expected S01..S25, got {actual_questions}"
        )

    result: list[dict[str, Any]] = []
    for qcode in expected_questions:
        row = payload[qcode]
        if not isinstance(row, dict):
            raise ValueError(f"{qcode} must map to an object of option_index -> trait list")
        option_keys = sorted(row.keys(), key=lambda x: int(str(x)) if str(x).isdigit() else 999)
        if [str(x) for x in option_keys] != ["0", "1", "2", "3", "4"]:
            raise ValueError(f"{qcode} must contain exactly options 0..4")
        for raw_index in option_keys:
            idx = int(raw_index)
            traits = row[raw_index]
            if not isinstance(traits, list) or not all(isinstance(t, str) and t.strip() for t in traits):
                raise ValueError(f"{qcode}[{idx}] must be a non-empty list of trait strings")
            result.append({
                "question_code": qcode,
                "option_index": idx,
                "traits": traits,
            })
    return result


def require_no_duplicate(values: list[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    if duplicates:
        raise ValueError(f"Duplicate {label}: {duplicates}")


def validate_motive_references(
    major_records: list[dict[str, Any]],
    branch_records: list[dict[str, Any]],
    known_codes: set[str],
) -> tuple[int, int, list[str]]:
    """Fail closed on unknown refs, except intentionally deferred BIOTM-* refs."""
    major_refs = 0
    branch_refs = 0
    missing: list[str] = []
    deferred: list[str] = []

    for item in major_records:
        for raw_code in item.get("micro_motive_codes") or []:
            major_refs += 1
            code = str(raw_code).strip()
            if code not in known_codes:
                finding = f"major:{item.get('id') or item.get('major_id')}:{code}"
                if code.startswith(DEFERRED_MOTIVE_PREFIXES):
                    deferred.append(finding)
                else:
                    missing.append(finding)

    for item in branch_records:
        for raw_code in item.get("micro_motive_codes") or []:
            branch_refs += 1
            code = str(raw_code).strip()
            if code not in known_codes:
                finding = f"branch:{item.get('id') or item.get('branch_id') or item.get('name')}:{code}"
                if code.startswith(DEFERRED_MOTIVE_PREFIXES):
                    deferred.append(finding)
                else:
                    missing.append(finding)

    if missing:
        preview = ", ".join(missing[:20])
        suffix = " ..." if len(missing) > 20 else ""
        raise ValueError(f"Unresolved micro-motive references ({len(missing)}): {preview}{suffix}")
    return major_refs, branch_refs, deferred


def seed_reference_data(db: Session, base: Path) -> dict[str, Any]:
    motives_path = base / "docs/data/micro_motives.json"
    majors_path = base / "majors_database_v2.json"
    branches_path = base / "school_branches_v2.json"
    values_path = base / "value_poles_v2.json"
    trait_path = base / "docs/data/trait_map_v3.json"
    source_paths = (motives_path, majors_path, branches_path, values_path, trait_path)

    for path in source_paths:
        if not path.exists():
            raise FileNotFoundError(path)

    motive_records = collection_records(load_json(motives_path), ("micro_motives", "motives", "data"))
    major_records = collection_records(load_json(majors_path), ("majors", "data"))
    branch_records = collection_records(load_json(branches_path), ("school_branches", "branches", "data"))
    value_records = parse_value_poles(load_json(values_path))
    trait_records = parse_trait_options(load_json(trait_path))

    motive_codes = [str(item.get("code") or "").strip() for item in motive_records]
    require_no_duplicate(motive_codes, "micro-motive codes")
    known_codes = set(motive_codes)
    major_refs, branch_refs, deferred_refs = validate_motive_references(
        major_records, branch_records, known_codes
    )

    major_ids = [
        int(item.get("id") if item.get("id") is not None else item.get("major_id"))
        for item in major_records
        if item.get("id") is not None or item.get("major_id") is not None
    ]
    if sorted(major_ids) != list(range(1, 161)):
        raise ValueError("Major IDs are not exactly 1..160")

    value_codes = [item["pole_code"] for item in value_records]
    require_no_duplicate(value_codes, "value pole codes")
    trait_keys = [(item["question_code"], item["option_index"]) for item in trait_records]
    if len(trait_keys) != len(set(trait_keys)):
        raise ValueError("Duplicate trait option keys")

    motive_by_code: dict[str, MicroMotive] = {}
    for item in motive_records:
        code = str(item["code"]).strip()
        row = db.scalar(select(MicroMotive).where(MicroMotive.code == code))
        if row is None:
            row = MicroMotive(code=code, description_fa=str(item.get("description_fa") or item.get("text") or ""))
            db.add(row)
        row.description_fa = str(item.get("description_fa") or item.get("text") or row.description_fa)
        row.category = item.get("category")
        row.intensity_level = item.get("intensity_level")
        motive_by_code[code] = row

    db.flush()

    for item in value_records:
        code = item["pole_code"]
        row = db.scalar(select(ValuePole).where(ValuePole.pole_code == code))
        if row is None:
            row = ValuePole(
                pole_code=code,
                question_num=int(item["question_num"]),
                option_letter=item["option_letter"],
                description_fa=item["description_fa"],
            )
            db.add(row)
        else:
            row.question_num = int(item["question_num"])
            row.option_letter = item["option_letter"]
            row.description_fa = item["description_fa"]

    for item in trait_records:
        qcode = item["question_code"]
        idx = int(item["option_index"])
        row = db.scalar(
            select(TraitOption).where(
                TraitOption.question_code == qcode,
                TraitOption.option_index == idx,
            )
        )
        if row is None:
            row = TraitOption(question_code=qcode, option_index=idx, traits=item["traits"])
            db.add(row)
        else:
            row.traits = item["traits"]

    db.flush()

    major_by_id: dict[int, Major] = {}
    for item in major_records:
        mid = int(item.get("id") if item.get("id") is not None else item.get("major_id"))
        name = str(item.get("name") or item.get("major_name_fa") or item.get("major_name") or "").strip()
        if not name:
            raise ValueError(f"Major {mid} has no name")
        row = db.get(Major, mid)
        if row is None:
            row = Major(
                id=mid,
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
        major_by_id[mid] = row

    branch_by_name: dict[str, SchoolBranch] = {}
    for item in branch_records:
        name = str(item.get("name") or item.get("branch_name") or "").strip()
        if not name:
            raise ValueError("School branch has no name")
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

    # Rebuild only valid reference associations. Deferred BIOTM-* mappings remain
    # absent from PostgreSQL until the dedicated BIOTM correction phase.
    db.execute(major_micro_motives.delete())
    db.execute(branch_micro_motives.delete())
    db.flush()

    major_links = 0
    for item in major_records:
        mid = int(item.get("id") if item.get("id") is not None else item.get("major_id"))
        major = major_by_id[mid]
        for raw_code in item.get("micro_motive_codes") or []:
            code = str(raw_code).strip()
            motive = motive_by_code.get(code)
            if motive is None:
                continue
            major.micro_motives.append(motive)
            major_links += 1

    branch_links = 0
    for item in branch_records:
        name = str(item.get("name") or item.get("branch_name") or "").strip()
        branch = branch_by_name[name]
        for raw_code in item.get("micro_motive_codes") or []:
            code = str(raw_code).strip()
            motive = motive_by_code.get(code)
            if motive is None:
                continue
            branch.micro_motives.append(motive)
            branch_links += 1

    db.commit()

    return {
        "status": "PASS",
        "runtime_cutover": "OFF",
        "deferred": {
            "motive_references": deferred_refs,
            "count": len(deferred_refs),
            "prefixes": list(DEFERRED_MOTIVE_PREFIXES),
        },
        "counts": {
            "micro_motives": len(motive_records),
            "value_poles": len(value_records),
            "trait_options": len(trait_records),
            "majors": len(major_records),
            "school_branches": len(branch_records),
            "major_micro_motive_references": major_refs,
            "branch_micro_motive_references": branch_refs,
            "major_micro_motive_links": major_links,
            "branch_micro_motive_links": branch_links,
        },
        "source_sha256": {
            str(path.relative_to(base)): sha256_file(path) for path in source_paths
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Dark Horse reference data into staging PostgreSQL")
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args()
    if not args.confirm_staging:
        raise SystemExit("Refusing to seed without --confirm-staging")
    if engine is None:
        raise SystemExit("DATABASE_URL is not configured")

    try:
        with Session(engine) as db:
            report = seed_reference_data(db, ROOT)
    except Exception:
        raise
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
