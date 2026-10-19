"""Reproducible audit of cross-cluster alternative paths.

Run from repository root:
    python p1_4_intercluster_audit.py
"""
import json
from pathlib import Path

from dark_horse_engine_v2 import DarkHorseEngineV2

ROOT = Path(__file__).resolve().parent
SAMPLE_PAIRS = (
    (24, 113),  # health economics -> economics
    (35, 93),   # medical nanotechnology -> basic-science biotechnology
    (57, 97),   # geomatics engineering -> geophysics
    (18, 105),  # radiotherapy -> Islamic jurisprudence and law
    (1, 104),   # medicine -> foundations of jurisprudence and law
)


def load_engine_for_audit():
    """Load catalog rows without precomputing every alternative path at startup."""
    engine = object.__new__(DarkHorseEngineV2)
    with (ROOT / "majors_database_v2.json").open(encoding="utf-8") as f:
        rows = json.load(f)
    # Mirrors the production loader: the catalog row ID is the dictionary key.
    engine.majors_db = {row["id"]: row for row in rows}
    return engine


def build_audit(engine=None):
    engine = engine or load_engine_for_audit()
    active_targets = [
        row for row in engine.majors_db.values()
        if row.get("motive_driven") is not False
    ]
    all_rows = engine.majors_db
    records = []
    source_cluster_summary = {}

    same_slots = cross_slots = unknown_slots = 0
    unassigned_source_slots = 0
    known_cluster_targets = 0
    targets_with_cross = 0
    inactive_candidates_in_top3 = 0

    for target in active_targets:
        top_paths = engine._compute_alternative_paths(target["id"], top_n=3)
        if len(top_paths) != 3:
            raise AssertionError(
                f"Major {target['id']} returned {len(top_paths)} alternatives, expected 3"
            )

        target_cluster = target.get("cluster")
        target_has_cross = False
        path_rows = []
        if target_cluster:
            known_cluster_targets += 1
            bucket = source_cluster_summary.setdefault(target_cluster, {
                "targets": 0,
                "slots": 0,
                "same_cluster": 0,
                "cross_cluster": 0,
                "unknown_destination_cluster": 0,
                "targets_with_cross_cluster": 0,
            })
            bucket["targets"] += 1
            bucket["slots"] += len(top_paths)

        for rank, path in enumerate(top_paths, start=1):
            alt_id = int(path["major_id"])
            alternative = all_rows.get(alt_id, {})
            alt_cluster = alternative.get("cluster")
            active = alternative.get("motive_driven") is not False

            if not active:
                inactive_candidates_in_top3 += 1

            if not target_cluster:
                relation = "unknown_cluster"
                unassigned_source_slots += 1
            elif not alt_cluster:
                relation = "unknown_cluster"
                unknown_slots += 1
                source_cluster_summary[target_cluster]["unknown_destination_cluster"] += 1
            elif target_cluster == alt_cluster:
                relation = "same_cluster"
                same_slots += 1
                source_cluster_summary[target_cluster]["same_cluster"] += 1
            else:
                relation = "cross_cluster"
                cross_slots += 1
                target_has_cross = True
                source_cluster_summary[target_cluster]["cross_cluster"] += 1

            path_rows.append({
                "rank": rank,
                "major_id": alt_id,
                "major_name": path.get("major_name", ""),
                "group": path.get("group", ""),
                "cluster": alt_cluster or "",
                "motive_driven": active,
                "distance": path["distance"],
                "value_distance": path["value_distance"],
                "strategy_distance": path["strategy_distance"],
                "relation": relation,
            })

        if target_cluster and target_has_cross:
            targets_with_cross += 1
            source_cluster_summary[target_cluster]["targets_with_cross_cluster"] += 1

        records.append({
            "target_id": int(target["id"]),
            "target_name": target.get("name", ""),
            "group": target.get("group", ""),
            "cluster": target_cluster or "",
            "alternatives": path_rows,
        })

    classifiable = same_slots + cross_slots
    known_source_slots = known_cluster_targets * 3

    records_by_target = {item["target_id"]: item for item in records}
    sample_paths = []
    for source_id, alternative_id in SAMPLE_PAIRS:
        source = records_by_target.get(source_id)
        if not source:
            continue
        path = next(
            (p for p in source["alternatives"] if p["major_id"] == alternative_id),
            None,
        )
        if path:
            sample_paths.append({
                "target_id": source_id,
                "target_name": source["target_name"],
                "target_cluster": source["cluster"],
                **path,
            })

    summary = {
        "major_count": len(all_rows),
        "active_target_count": len(active_targets),
        "known_cluster_target_count": known_cluster_targets,
        "target_cluster_missing_count": len(active_targets) - known_cluster_targets,
        "slots_for_known_cluster_targets": known_source_slots,
        "same_cluster_slots": same_slots,
        "cross_cluster_slots": cross_slots,
        "unknown_cluster_slots": unknown_slots,
        "unassigned_source_cluster_slots": unassigned_source_slots,
        "cross_pct_of_known_source_slots": round(100 * cross_slots / known_source_slots, 2)
        if known_source_slots else 0.0,
        "cross_pct_of_classifiable_slots": round(100 * cross_slots / classifiable, 2)
        if classifiable else 0.0,
        "same_pct_of_classifiable_slots": round(100 * same_slots / classifiable, 2)
        if classifiable else 0.0,
        "targets_with_at_least_one_cross_cluster_path": targets_with_cross,
        "pct_known_cluster_targets_with_cross_cluster_path": round(
            100 * targets_with_cross / known_cluster_targets, 2
        ) if known_cluster_targets else 0.0,
        "inactive_candidates_in_top3": inactive_candidates_in_top3,
        "percent_inactive_candidates_in_top3": round(
            100 * inactive_candidates_in_top3 / known_source_slots, 2
        ) if known_source_slots else 0.0,
    }

    return {
        "protocol": {
            "distance": "sqrt(0.60 * RMS(value)^2 + 0.40 * RMS(strategy)^2)",
            "strategy_vector": "25 questions x 5 options",
            "value_vector": "15 questions x 2 poles",
            "selection": "three lowest distances, rounded to 3 decimals by production method",
            "cross_cluster_rule": "count as cross only when both cluster labels exist and differ",
            "scope": "all current motive-driven majors as targets; production alternative method supplies candidates",
            "runtime_changes": "none; audit only",
        },
        "summary": summary,
        "source_cluster_summary": source_cluster_summary,
        "sample_cross_cluster_paths": sample_paths,
        "targets": records,
    }


if __name__ == "__main__":
    print(json.dumps(build_audit(), ensure_ascii=False, indent=2))
