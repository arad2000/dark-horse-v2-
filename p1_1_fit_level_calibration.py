"""Reproducible P1.1 label-calibration simulation using production scoring helpers.

Run from the repository root:
    python p1_1_fit_level_calibration.py

The "random" fixture holds target #42's seven motive codes constant and randomizes
only the 25 SJT answers and 15 conjoint choices. This isolates label inflation from
S/V answer randomness conditional on a viable motive profile; it is not a fully
random draw of 1,393 motive codes.
"""
import json
import math
from collections import Counter
from dark_horse_engine_v2 import DarkHorseEngineV2

MASK32 = 0xFFFFFFFF
SEED_COUNT = 300


def mulberry32(seed):
    """Yield the same deterministic 32-bit PRNG stream used for the report."""
    state = seed & MASK32
    while True:
        state = (state + 0x6D2B79F5) & MASK32
        t = state
        t = ((t ^ (t >> 15)) * (t | 1)) & MASK32
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & MASK32)) & MASK32
        yield ((t ^ (t >> 14)) & MASK32) / 4294967296.0


def random_answers(seed):
    rng = mulberry32(seed)
    strategy_answers = [int(next(rng) * 5) for _ in range(25)]
    value_choices = [
        f"Q{i}{'A' if next(rng) < 0.5 else 'B'}" for i in range(1, 16)
    ]
    return strategy_answers, value_choices


def aligned_answers(target):
    strategy_answers = []
    for row in target.get("strategy_weights", []):
        if not row:
            strategy_answers.append(-1)
            continue
        max_weight = max(row)
        strategy_answers.append(row.index(max_weight))

    weights = target.get("value_weights", {})
    value_choices = []
    for question in range(1, 16):
        key_a, key_b = f"Q{question}A", f"Q{question}B"
        value_choices.append(key_a if weights.get(key_a, 0.0) >= weights.get(key_b, 0.0) else key_b)
    return strategy_answers, value_choices


def score_fixture(engine, user_motives, strategy_answers, value_choices):
    observations = []
    for major_id, major in engine.majors_db.items():
        if major.get("motive_driven") is False:
            continue
        m_score, _ = engine._compute_m_score(user_motives, major)
        if m_score < 0.15:
            continue
        s_score, _ = engine._compute_s_score(strategy_answers, major.get("strategy_weights", []))
        v_score, _ = engine._compute_v_score(value_choices, major.get("value_weights", {}))
        total = (0.55 * m_score) + (0.30 * v_score) + (0.15 * s_score)
        score = math.floor(total * 1000 + 0.5) / 10
        if score < 30.0:
            continue
        observations.append({
            "major_id": int(major_id),
            "major_name": major.get("name", ""),
            "score": score,
            "m_score": round(m_score * 100, 1),
            "s_score": round(s_score * 100, 1),
            "v_score": round(v_score * 100, 1),
        })
    return observations


def level_before(score):
    if score >= 80:
        return "very_high"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def level_after(score):
    if score >= 90:
        return "very_high"
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def label_distribution(observations, level_function):
    counts = Counter(level_function(item["score"]) for item in observations)
    total = len(observations)
    return {
        name: {
            "n": counts[name],
            "pct": round(100.0 * counts[name] / total, 2) if total else 0.0,
        }
        for name in ("very_high", "high", "medium", "low")
    }


def distribution_summary(observations):
    values = sorted(item["score"] for item in observations)

    def percentile(p):
        return values[int((len(values) - 1) * p)] if values else None

    return {
        "n": len(values),
        "mean": round(sum(values) / len(values), 2) if values else None,
        "min": values[0] if values else None,
        "p25": percentile(0.25),
        "median": percentile(0.50),
        "p75": percentile(0.75),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "max": values[-1] if values else None,
        "before": label_distribution(observations, level_before),
        "after": label_distribution(observations, level_after),
    }


def run_calibration():
    engine = DarkHorseEngineV2()
    target = engine.majors_db.get(42) or engine.majors_db.get("42")
    if not target:
        raise RuntimeError("Target major id=42 is missing from majors_database_v2.json")
    target_codes = list(target.get("micro_motive_codes", []))
    if len(target_codes) < 2:
        raise RuntimeError("Target major id=42 requires at least two motive codes")

    random_observations = []
    low_spark_observations = []
    for seed in range(1, SEED_COUNT + 1):
        strategy_answers, value_choices = random_answers(seed)
        random_observations.extend(score_fixture(
            engine, target_codes, strategy_answers, value_choices
        ))
        low_spark_observations.extend(score_fixture(
            engine, target_codes[:2], strategy_answers, value_choices
        ))

    aligned_s, aligned_v = aligned_answers(target)
    full_aligned_observations = score_fixture(engine, target_codes, aligned_s, aligned_v)

    observations = {
        "random_sv_given_target_motives": random_observations,
        "low_spark_random_sv": low_spark_observations,
        "full_aligned_target": full_aligned_observations,
    }
    return {
        "protocol": {
            "target_major_id": int(target.get("id", 42)),
            "target_major_name": target.get("name", ""),
            "target_motive_codes": target_codes,
            "seed_count": SEED_COUNT,
            "random_fixture": "fixed target motive profile; random SJT/conjoint only",
            "low_spark_fixture": "first two target motive codes; same SJT/conjoint seeds",
            "full_aligned_fixture": "all target motives plus maximum-weight SJT/conjoint choices",
            "filters": "motive_driven is not false; M >= 15%; Total >= 30%",
            "total_formula": "0.55*M + 0.30*V + 0.15*S",
        },
        "summary": {
            name: distribution_summary(items) for name, items in observations.items()
        },
        "full_aligned_records": full_aligned_observations,
    }


if __name__ == "__main__":
    print(json.dumps(run_calibration(), ensure_ascii=False, indent=2))
