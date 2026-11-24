"""Independent, unconnected alternatives based on existing user-to-major S/V.

No major-to-major distance, motive gate, Total, trait extraction or fallback.
Engine/API/UI do not import this module. Caller supplies the complete active
catalog via engine.majors_db. Approval required before runtime integration.
"""
from math import isfinite
from typing import Mapping

METHOD = "user_strategy_or_value_gt70_v1"
THRESHOLD = 0.70
LIMIT = 3
LABELS = {
    "both": "هم‌راستا با پاسخ‌های راهبردی و ارزشی شما",
    "strategy": "هم‌راستا با پاسخ‌های راهبردی شما",
    "value": "هم‌راستا با پاسخ‌های ارزشی شما",
}


def _weight(value):
    return type(value) in (int, float) and isfinite(value) and 0 <= value <= 1


def _strategy_answers(answers):
    if not isinstance(answers, Mapping):
        return None
    result = []
    for i in range(1, 26):
        choice = answers.get(f"sjt_{i}")
        if not isinstance(choice, str) or choice.strip().upper() not in ("A", "B", "C", "D", "E"):
            return None
        result.append(ord(choice.strip().upper()) - ord("A"))
    return result


def _value_answers(answers):
    if not isinstance(answers, Mapping):
        return None
    result = []
    for i in range(1, 16):
        choice = answers.get(f"conj_{i}")
        if not isinstance(choice, str) or choice.strip().upper() not in (f"Q{i}A", f"Q{i}B"):
            return None
        result.append(choice.strip().upper())
    return result


def _strategy_coverage(weights):
    return (isinstance(weights, list) and len(weights) == 25
            and all(isinstance(row, list) and len(row) == 5
                    and all(_weight(w) for w in row) and max(row) > 0
                    for row in weights))


def _value_coverage(weights):
    return (isinstance(weights, Mapping)
            and all(_weight(weights.get(f"Q{i}{side}"))
                    for i in range(1, 16) for side in "AB"))


def _score_dimension(answers, weights, covered, scorer):
    if answers is None:
        return {"status": "unknown", "reason": "incomplete_or_invalid_answers", "score": None, "qualifies": False}
    if not covered:
        return {"status": "unknown", "reason": "incomplete_or_invalid_weights", "score": None, "qualifies": False}
    try:
        score, _ = scorer(answers, weights)
    except (ArithmeticError, TypeError, ValueError, KeyError, IndexError):
        return {"status": "unknown", "reason": "score_unavailable", "score": None, "qualifies": False}
    if not _weight(score):
        return {"status": "unknown", "reason": "invalid_score", "score": None, "qualifies": False}
    # Compare unrounded score. 0.70 exactly is not greater than 0.70.
    return {"status": "evaluated", "reason": None, "score": score, "qualifies": score > THRESHOLD}


def build_strategy_value_alternatives(engine, sjt_answers, conjoint_choices, current_major_id):
    """Return at most three alternatives; does not mutate engine or its caches.

    Missing data is unknown independently in each dimension, never score zero.
    Uniform rows/pairs retain existing scorer behavior; counts disclose their
    lack of discrimination, without inventing a new coverage threshold.
    Sorting: both first, min(S,V) descending; single-axis by qualifying score;
    exact ties by numeric ID only (stable display, not scientific superiority).
    """
    if type(current_major_id) is not int or current_major_id not in engine.majors_db:
        raise ValueError("current_major_id must identify an active catalog major")
    strategies = _strategy_answers(sjt_answers)
    values = _value_answers(conjoint_choices)
    items = []
    evaluated = 0
    partial = 0
    unknown = 0
    candidate_count = 0
    for major_id, major in engine.majors_db.items():
        if major_id == current_major_id:
            continue
        if type(major_id) is not int or not isinstance(major, Mapping) or not isinstance(major.get("name"), str) or not major["name"].strip():
            raise ValueError("active catalog entries must have integer IDs and nonempty names")
        sw = major.get("strategy_weights")
        vw = major.get("value_weights")
        s_covered, v_covered = _strategy_coverage(sw), _value_coverage(vw)
        s = _score_dimension(strategies, sw, s_covered, engine._compute_s_score)
        v = _score_dimension(values, vw, v_covered, engine._compute_v_score)
        known = sum(d["status"] == "evaluated" for d in (s, v))
        evaluated += known == 2
        partial += known == 1
        unknown += known == 0
        if not s["qualifies"] and not v["qualifies"]:
            continue
        candidate_count += 1
        basis = "both" if s["qualifies"] and v["qualifies"] else "strategy" if s["qualifies"] else "value"
        items.append({
            "major_id": major_id,
            "major_name": major["name"],
            "basis": basis,
            "reason": LABELS[basis],
            "strategy": s,
            "value": v,
            "evidence": {
                "strategy_question_ids": [f"S{i:02d}" for i in range(1, 26)] if s["status"] == "evaluated" else [],
                "value_choice_codes": list(values) if v["status"] == "evaluated" else [],
                "strategy_weights_field": "strategy_weights" if s_covered else None,
                "value_weights_field": "value_weights" if v_covered else None,
                "uniform_strategy_rows": sum(max(row) == min(row) for row in sw) if s_covered else None,
                "equal_value_pairs": sum(vw[f"Q{i}A"] == vw[f"Q{i}B"] for i in range(1, 16)) if v_covered else None,
            },
        })

    def ordering(item):
        s, v = item["strategy"]["score"], item["value"]["score"]
        both = item["basis"] == "both"
        strength = min(s, v) if both else s if item["basis"] == "strategy" else v
        return (0 if both else 1, -strength, item["major_id"])

    items.sort(key=ordering)
    incomplete = partial > 0 or unknown > 0
    if items:
        status, reason = "ready", None
    elif evaluated or partial:
        status = "no_matches_in_evaluated_dimensions"
        reason = "incomplete_coverage" if incomplete else "no_score_above_threshold"
    else:
        status, reason = "insufficient_data", "no_evaluable_dimensions"
    return {
        "status": status,
        "reason": reason,
        "method": METHOD,
        "threshold": THRESHOLD,
        "comparison": ">",
        "limit": LIMIT,
        "candidate_count": candidate_count,
        "coverage": {
            "catalog_count": len(engine.majors_db),
            "excluded_current_major_id": current_major_id,
            "both_dimensions_evaluated": evaluated,
            "one_dimension_evaluated": partial,
            "neither_dimension_evaluated": unknown,
            "incomplete": incomplete,
        },
        "items": items[:LIMIT],
    }


def attach_strategy_value_alternatives(engine, discovered_majors, sjt_answers, conjoint_choices):
    """Copy result envelopes and replace legacy alternatives, including nested ones.

    Request-local memoization reuses unchanged S/V scores across result cards.
    No engine cache, original discovery or catalog data is modified.
    """
    from types import SimpleNamespace
    s_cache, v_cache = {}, {}

    def memoized(scorer, cache):
        def score(answers, weights):
            key = id(weights)
            if key not in cache:
                cache[key] = scorer(answers, weights)
            return cache[key]
        return score

    proxy = SimpleNamespace(
        majors_db=engine.majors_db,
        _compute_s_score=memoized(engine._compute_s_score, s_cache),
        _compute_v_score=memoized(engine._compute_v_score, v_cache),
    )
    result = []
    for original in discovered_majors:
        item = dict(original)
        fit = dict(item.get("individuality_fit") or {})
        selection = build_strategy_value_alternatives(proxy, sjt_answers, conjoint_choices, item["major_id"])
        item["strategy_value_alternatives"] = selection
        item["alternative_paths"] = selection["items"]
        fit["strategy_value_alternatives"] = selection
        fit["alternative_paths"] = selection["items"]
        item["individuality_fit"] = fit
        result.append(item)
    return result
