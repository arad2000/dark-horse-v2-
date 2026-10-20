import json
from pathlib import Path

from dark_horse_engine_v2 import DarkHorseEngineV2


ROOT = Path(__file__).resolve().parent


def _engine_with_trait_map(trait_map):
    engine = DarkHorseEngineV2.__new__(DarkHorseEngineV2)
    engine.trait_map = trait_map
    return engine


def _load_trait_map():
    raw = json.loads((ROOT / "trait_map_v3.json").read_text(encoding="utf-8"))
    return {question: {int(index): traits for index, traits in options.items()}
            for question, options in raw.items()}


def test_medical_major_no_dominant_misaligned_overlap():
    majors = json.loads((ROOT / "majors_database_v2.json").read_text(encoding="utf-8"))
    medical = next(major for major in majors if str(major.get("id")) == "1")
    engine = _engine_with_trait_map(_load_trait_map())

    # This previously contradictory fixture: S01/A makes «تحلیل‌محور» dominant,
    # while S03/A has a low raw cell weight for the same trait.
    answers = [-1] * 25
    answers[0] = 0
    answers[2] = 0
    weights = medical["strategy_weights"]

    dominant = engine._extract_dominant_traits(answers, weights, threshold=0.70, top_n=25)
    misaligned = engine._extract_s_misaligned_traits(
        answers, weights, threshold=0.35, dominant_threshold=0.70
    )

    assert "تحلیل‌محور" in dominant
    assert set(dominant).isdisjoint(misaligned)


def test_misalignment_threshold_uses_normalized_not_raw_weight():
    engine = _engine_with_trait_map({"S01": {0: ["نسبت‌محور"]}})
    # Raw 0.20 is below the old 0.30 cutoff, but normalized 0.20/0.50 = 0.40.
    answers = [0]
    weights = [[0.20, 0.50]]

    assert engine._normalized_strategy_weight(weights[0], 0) == 0.40
    assert engine._extract_s_misaligned_traits(answers, weights) == []
