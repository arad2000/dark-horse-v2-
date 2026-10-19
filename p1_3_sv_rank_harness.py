"""Reproducible S-only / V-only / current-Total rank harness.

Run from repository root:
    python p1_3_sv_rank_harness.py --target-id 42

The synthetic response profile selects maximum-weight SJT and conjoint options
from one target major's existing database row. This is an idealized target-aligned
benchmark, not observed participant data and not a psychometric validation.
"""
import argparse
import json
import math
from dark_horse_engine_v2 import DarkHorseEngineV2


def max_aligned_answers(target):
    strategy_answers = []
    for row in target.get("strategy_weights", []):
        if not row:
            strategy_answers.append(-1)
        else:
            strategy_answers.append(row.index(max(row)))

    value_weights = target.get("value_weights", {})
    value_choices = []
    for question in range(1, 16):
        key_a, key_b = f"Q{question}A", f"Q{question}B"
        value_choices.append(
            key_a if value_weights.get(key_a, 0.0) >= value_weights.get(key_b, 0.0) else key_b
        )
    return strategy_answers, value_choices


def round_percent(score):
    return math.floor(score * 1000 + 0.5) / 10


def rank_target(rows, key, target_id):
    if not rows or not any(row["major_id"] == target_id for row in rows):
        return {"rank": None, "universe_size": len(rows), "score": None, "ties_at_score": 0}
    target_row = next(row for row in rows if row["major_id"] == target_id)
    target_score = target_row[key]
    greater = sum(1 for row in rows if row[key] > target_score + 1e-12)
    ties = sum(1 for row in rows if abs(row[key] - target_score) <= 1e-12)
    return {
        "rank": 1 + greater,
        "universe_size": len(rows),
        "score": round_percent(target_score) if key != "total_score" else target_score,
        "ties_at_score": ties,
    }


def analyze_target(target_id=42):
    engine = DarkHorseEngineV2()
    target = engine.majors_db.get(target_id) or engine.majors_db.get(str(target_id))
    if not target:
        raise RuntimeError(f"Target major id={target_id} was not found")
    user_motives = list(target.get("micro_motive_codes", []))
    strategy_answers, value_choices = max_aligned_answers(target)

    rows = []
    for major_id, major in engine.majors_db.items():
        if major.get("motive_driven") is False:
            continue
        m_score, _ = engine._compute_m_score(user_motives, major)
        s_score, _ = engine._compute_s_score(strategy_answers, major.get("strategy_weights", []))
        v_score, _ = engine._compute_v_score(value_choices, major.get("value_weights", {}))
        total_score = round_percent(0.55 * m_score + 0.30 * v_score + 0.15 * s_score)
        rows.append({
            "major_id": int(major_id),
            "major_name": major.get("name", ""),
            "m_score": m_score,
            "s_score": s_score,
            "v_score": v_score,
            "total_score": total_score,
        })

    # S/V are ranked over the active catalog, independently of motive/Total output filters.
    # The Total rank follows production discovery gates: M >= 15% and Total >= 30%.
    total_results = [
        row for row in rows
        if row["m_score"] >= 0.15 and row["total_score"] >= 30.0
    ]
    target_row = next(row for row in rows if row["major_id"] == target_id)
    target_total = next((row for row in total_results if row["major_id"] == target_id), None)
    if target_total is None:
        raise RuntimeError("Target was excluded by the production M / Total result filters")

    return {
        "protocol": {
            "target_id": target_id,
            "target_name": target.get("name", ""),
            "motive_codes": user_motives,
            "strategy_answer_indices_zero_based": strategy_answers,
            "conjoint_choices": value_choices,
            "active_catalog_size": len(rows),
            "total_result_filters": "motive_driven is not false; M >= 15%; Total >= 30%",
            "total_formula": "0.55*M + 0.30*V + 0.15*S",
            "note": "S/V ranks use the 202-item active catalog; Total rank uses the actual filtered result set.",
        },
        "target_components_pct": {
            "M": round_percent(target_row["m_score"]),
            "S": round_percent(target_row["s_score"]),
            "V": round_percent(target_row["v_score"]),
            "Total": target_row["total_score"],
        },
        "rank": {
            "S_only": rank_target(rows, "s_score", target_id),
            "V_only": rank_target(rows, "v_score", target_id),
            "current_Total": rank_target(total_results, "total_score", target_id),
        },
        "eligible_total_results": [
            {
                "major_id": row["major_id"],
                "major_name": row["major_name"],
                "M": round_percent(row["m_score"]),
                "S": round_percent(row["s_score"]),
                "V": round_percent(row["v_score"]),
                "Total": row["total_score"],
            }
            for row in sorted(total_results, key=lambda item: (-item["total_score"], item["major_id"]))
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-id", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(analyze_target(args.target_id), ensure_ascii=False, indent=2))
