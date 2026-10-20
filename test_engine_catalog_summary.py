import logging

from dark_horse_engine_v2 import DarkHorseEngineV2


VALUE_CODES = {
    f"Q{question}{option}": 0.5
    for question in range(1, 16)
    for option in ("A", "B")
}


def _major(*, motive_driven=True, strategy_complete=True, values_complete=True, name="fixture"):
    strategy = [[0.1, 0.2, 0.3, 0.4, 0.5] for _ in range(25)] if strategy_complete else [[0.1, 0.2]]
    values = dict(VALUE_CODES) if values_complete else {"Q1A": 0.5}
    return {
        "name": name,
        "motive_driven": motive_driven,
        "micro_motive_codes": ["FIX-001"],
        "strategy_weights": strategy,
        "value_weights": values,
        "prestige_level": 1,
    }


def _engine(majors):
    engine = DarkHorseEngineV2.__new__(DarkHorseEngineV2)
    engine.majors_db = majors
    engine.trait_map = {f"S{i:02d}": {} for i in range(1, 26)}
    return engine


def test_total_majors_analyzed_excludes_disabled_and_incomplete_records():
    engine = _engine({
        "active-complete": _major(name="active-complete"),
        "disabled": _major(motive_driven=False, strategy_complete=False, values_complete=False, name="disabled"),
        "missing-strategy": _major(strategy_complete=False, name="missing-strategy"),
        "missing-values": _major(values_complete=False, name="missing-values"),
    })

    assert engine._count_eligible_major_records() == 1
    result = engine.discover_individuality([], {}, {})
    assert result["summary"]["total_majors_analyzed"] == 1


def test_incomplete_active_records_produce_one_aggregate_warning_not_one_per_record(caplog):
    engine = _engine({
        "active-complete": _major(name="active-complete"),
        "disabled": _major(motive_driven=False, strategy_complete=False, values_complete=False, name="disabled"),
        "missing-strategy-a": _major(strategy_complete=False, name="missing-strategy-a"),
        "missing-strategy-b": _major(strategy_complete=False, name="missing-strategy-b"),
    })

    with caplog.at_level(logging.WARNING):
        engine._validate_schema_consistency()

    warnings = [record for record in caplog.records if record.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "2 رکوردِ فعال/نامشخص" in warnings[0].getMessage()
    assert "disabled" not in warnings[0].getMessage()
