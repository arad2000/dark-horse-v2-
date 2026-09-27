"""Validate savabegh_dolati bomi_type against Sanjesh 1404 Table 5.

Offline/reference-data audit only. It never modifies program2s.json.
"""
from __future__ import annotations
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ROOT / "program2s.json"
MAJORS = ROOT / "majors_database_v2.json"
TABLE5 = ROOT / "docs" / "sanjesh_table5_major_bomi_v1.json"

KINDS = ("ostani", "nahiyei", "ghotbi", "keshvari", None)

def norm(value: object) -> str:
    return (
        unicodedata.normalize("NFKC", str(value or ""))
        .replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
        .replace("\u200c", " ").replace("\u200f", " ")
        .strip()
    )

def main() -> int:
    programs_payload = json.loads(PROGRAMS.read_text(encoding="utf-8"))
    programs = programs_payload["programs"]
    majors = {str(x["id"]): x["name"] for x in json.loads(MAJORS.read_text(encoding="utf-8"))}
    table = json.loads(TABLE5.read_text(encoding="utf-8"))
    daily = table["daily_major_bomi"]
    aliases = table.get("name_aliases", {})
    lookup = {norm(k): v for k, v in daily.items()}
    for alias, target in aliases.items():
        if target in daily:
            lookup[norm(alias)] = daily[target]

    before = {k: 0 for k in ("ostani","nahiyei","ghotbi","keshvari","null")}
    after = {k: 0 for k in ("ostani","nahiyei","ghotbi","keshvari","null")}
    changed = unresolved = total = 0
    examples = {"nahiyei": [], "ghotbi": [], "unresolved": []}

    for p in programs:
        a = p.get("admission_info") or {}
        if a.get("method") != "سوابق تحصیلی" or a.get("course_type") != "savabegh_dolati":
            continue
        total += 1
        old = a.get("bomi_type")
        before[old if old in before else "null"] += 1
        name = majors.get(str(p.get("major_id")))
        resolved = lookup.get(norm(name)) if name else None
        expected = resolved or None
        after[expected if expected in after else "null"] += 1
        if old != expected:
            changed += 1
        if expected is None:
            unresolved += 1
            if len(examples["unresolved"]) < 3:
                examples["unresolved"].append({
                    "program_id": p.get("program_id"), "major_id": p.get("major_id"),
                    "major_name": name, "rule": "unresolved_table5"
                })
        elif expected in examples and len(examples[expected]) < 3:
            examples[expected].append({
                "program_id": p.get("program_id"), "major_id": p.get("major_id"),
                "major_name": name, "bomi_type": expected
            })

    result = {
        "savabegh_dolati": total,
        "before": before,
        "after": after,
        "changed": changed,
        "unresolved_table5": unresolved,
        "examples": examples,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if changed == 0 and unresolved == 322 else 1

if __name__ == "__main__":
    raise SystemExit(main())
