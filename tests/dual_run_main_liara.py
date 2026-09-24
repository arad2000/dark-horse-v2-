#!/usr/bin/env python3
"""Deterministic main-build vs Liara-build semantic dual-run audit."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "dual_run"
DATA_PATHS = (
    "docs/data/micro_motives.json",
    "majors_database_v2.json",
    "school_branches_v2.json",
    "trait_map_v3.json",
    "value_poles_v2.json",
)
ENGINE_PATH = "dark_horse_engine_v2.py"
STRICT_TOLERANCE = 1e-9
RELAXED_TOLERANCE = 1e-6
FUNCTIONS_TO_FINGERPRINT = (
    "_compute_m_score",
    "_compute_branch_m_score",
    "_compute_s_score",
    "_compute_v_score",
    "discover_individuality",
    "recommend_school_branch",
    "_precompute_alternative_paths",
    "_compute_alternative_paths",
    "_compute_branch_alternative_paths",
    "_find_alternative_paths",
    "_find_branch_alternative_paths",
)


def git(*args: str) -> bytes:
    proc = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True)
    return proc.stdout


def git_text(*args: str) -> str:
    return git(*args).decode("utf-8").strip()


def git_show(ref: str, path: str) -> bytes:
    return git("show", f"{ref}:{path}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_sha(ref: str, path: str) -> str:
    return git_text("rev-parse", f"{ref}:{path}")


def source_function_fingerprints(source: bytes) -> dict[str, str | None]:
    text = source.decode("utf-8")
    tree = ast.parse(text)
    result: dict[str, str | None] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in FUNCTIONS_TO_FINGERPRINT:
            segment = ast.get_source_segment(text, node) or ""
            result[node.name] = sha256_bytes(segment.encode("utf-8"))
    return result


def load_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise AssertionError(f"invalid JSON: {label}: {exc}") from exc


def extract_motive_codes(payload: Any) -> set[str]:
    rows = payload
    if isinstance(payload, dict):
        for key in ("micro_motives", "motives", "data"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
    if not isinstance(rows, list):
        return set()
    return {
        str(row["code"]).strip().upper()
        for row in rows
        if isinstance(row, dict) and row.get("code")
    }


def validate_fixture(fixture: dict[str, Any], motive_codes: set[str]) -> None:
    required = {"fixture_id", "target", "micro_motives", "sjt_answers", "conjoint_choices"}
    missing = required - set(fixture)
    assert not missing, f'{fixture.get("fixture_id", "unknown")}: missing fields {sorted(missing)}'
    assert fixture["target"] in {"major", "school_branch"}

    motives = fixture["micro_motives"]
    assert isinstance(motives, list) and motives, f'{fixture["fixture_id"]}: micro_motives must be non-empty'
    assert len(motives) == len(set(motives)), f'{fixture["fixture_id"]}: duplicate micro motives'
    unknown = {str(x).strip().upper() for x in motives} - motive_codes
    assert not unknown, f'{fixture["fixture_id"]}: unknown motive codes {sorted(unknown)}'

    sjt = fixture["sjt_answers"]
    expected_sjt = {f"sjt_{i}" for i in range(1, 26)}
    assert set(sjt) == expected_sjt, f'{fixture["fixture_id"]}: sjt_1..sjt_25 contract mismatch'
    assert all(str(v).upper() in {"A", "B", "C", "D", "E"} for v in sjt.values())

    conjoint = fixture["conjoint_choices"]
    expected_conj = {f"conj_{i}" for i in range(1, 16)}
    assert set(conjoint) == expected_conj, f'{fixture["fixture_id"]}: conj_1..conj_15 contract mismatch'
    for key, value in conjoint.items():
        value = str(value).strip().upper()
        q_num = int(key.split("_", 1)[1])
        assert value in {f"Q{q_num}A", f"Q{q_num}B"}, (
            f'{fixture["fixture_id"]}: invalid conjoint choice {key}={value}'
        )


def load_engine(module_name: str, engine_source: bytes, data_dir: Path):
    engine_path = data_dir / ENGINE_PATH
    engine_path.write_bytes(engine_source)
    spec = importlib.util.spec_from_file_location(module_name, engine_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load engine module: {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.DarkHorseEngineV2(
        motives_path=str(data_dir / "docs_data_micro_motives.json"),
        majors_path=str(data_dir / "majors_database_v2.json"),
        trait_map_path=str(data_dir / "trait_map_v3.json"),
        value_poles_path=str(data_dir / "value_poles_v2.json"),
        school_branches_path=str(data_dir / "school_branches_v2.json"),
    )


def materialize_data(ref: str, out_dir: Path) -> dict[str, Any]:
    mapping = {
        "docs/data/micro_motives.json": "docs_data_micro_motives.json",
        "majors_database_v2.json": "majors_database_v2.json",
        "school_branches_v2.json": "school_branches_v2.json",
        "trait_map_v3.json": "trait_map_v3.json",
        "value_poles_v2.json": "value_poles_v2.json",
    }
    out: dict[str, Any] = {}
    for path, filename in mapping.items():
        raw = git_show(ref, path)
        (out_dir / filename).write_bytes(raw)
        out[path] = {
            "git_blob_sha": blob_sha(ref, path),
            "sha256": sha256_bytes(raw),
            "bytes": len(raw),
        }
    return out


def rank_view(target: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    if target == "major":
        rows = result.get("discovered_majors", [])
        view = []
        for row in rows:
            fit = row.get("individuality_fit", {}) or {}
            view.append({
                "id": row.get("major_id"),
                "name": row.get("major_name_fa", ""),
                "score": float(fit.get("score", 0.0)),
                "components": fit.get("raw_components", {}),
                "alternative_ids": [
                    p.get("major_id") if isinstance(p, dict) else p
                    for p in (fit.get("alternative_paths") or [])
                ],
            })
        return view

    rows = result.get("recommended_branches", [])
    view = []
    for row in rows:
        view.append({
            "id": row.get("branch_name"),
            "name": row.get("branch_name", ""),
            "score": float(row.get("average_score", 0.0)),
            "components": row.get("avg_components", {}),
            "alternative_ids": [
                p.get("branch_name") if isinstance(p, dict) else p
                for p in (row.get("alternative_paths") or [])
            ],
        })
    return view


def invoke(engine: Any, fixture: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    if fixture["target"] == "major":
        raw = engine.discover_individuality(
            fixture["micro_motives"],
            fixture["sjt_answers"],
            fixture["conjoint_choices"],
        )
    else:
        raw = engine.recommend_school_branch(
            fixture["micro_motives"],
            fixture["sjt_answers"],
            fixture["conjoint_choices"],
        )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    ranked = rank_view(fixture["target"], raw)
    return {
        "elapsed_ms": round(elapsed_ms, 3),
        "ranked_ids": [x["id"] for x in ranked],
        "ranking": ranked,
        "raw_top5": (
            raw.get("discovered_majors", [])[:5]
            if fixture["target"] == "major"
            else raw.get("recommended_branches", [])[:5]
        ),
    }


def compare_runs(target: str, main_run: dict[str, Any], liara_run: dict[str, Any]) -> dict[str, Any]:
    main_top = main_run["ranking"][:5]
    liara_top = liara_run["ranking"][:5]
    main_ids = [x["id"] for x in main_top]
    liara_ids = [x["id"] for x in liara_top]

    rank1_match = main_ids[:1] == liara_ids[:1]
    top3_match = main_ids[:3] == liara_ids[:3]
    top5_match = main_ids == liara_ids

    deltas = [
        abs(float(a["score"]) - float(b["score"]))
        for a, b in zip(main_top, liara_top)
    ]
    max_delta = max(deltas, default=0.0)

    alternatives_match = True
    for a, b in zip(main_top, liara_top):
        if a["id"] != b["id"] or a["alternative_ids"] != b["alternative_ids"]:
            alternatives_match = False
            break

    expected_top_len = 5 if target == "major" else 4
    enough_ranking = len(main_run["ranking"]) >= expected_top_len and len(liara_run["ranking"]) >= expected_top_len
    strict_scores = enough_ranking and len(main_top) == len(liara_top) == expected_top_len and max_delta <= STRICT_TOLERANCE
    relaxed_scores = enough_ranking and len(main_top) == len(liara_top) == expected_top_len and max_delta <= RELAXED_TOLERANCE
    strict_pass = all((rank1_match, top3_match, top5_match, strict_scores, alternatives_match))
    relaxed_pass = all((rank1_match, top3_match, top5_match, relaxed_scores, alternatives_match))

    if strict_pass:
        status = "PASS"
        tolerance_mode = "1e-9"
    elif relaxed_pass:
        status = "PASS"
        tolerance_mode = "1e-6-relaxed"
    else:
        status = "FAIL"
        tolerance_mode = None

    return {
        "status": status,
        "tolerance_mode": tolerance_mode,
        "rank1_match": rank1_match,
        "top3_match": top3_match,
        "top5_match": top5_match,
        "scores_within_1e-9": strict_scores,
        "scores_within_1e-6": relaxed_scores,
        "alternative_order_and_id_match": alternatives_match,
        "max_score_delta": max_delta,
        "strict_tolerance": STRICT_TOLERANCE,
        "relaxed_tolerance": RELAXED_TOLERANCE,
        "rank1_main": main_top[0] if main_top else None,
        "rank1_liara": liara_top[0] if liara_top else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-ref", required=True)
    parser.add_argument("--liara-ref", required=True)
    parser.add_argument("--output", default="dual_run_report.json")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "schema": "dual-run-main-liara-v1",
        "status": "FAIL",
        "contract": {
            "comparison": "main engine build vs Liara/deploy engine build",
            "scoring_formulas_changed": False,
            "reference_data_must_be_byte_identical": True,
            "cutover_required_off": True,
            "top_n": 5,
            "primary_score_tolerance": STRICT_TOLERANCE,
            "production_input_contract": {"strategy_keys": "sjt_1..sjt_25", "conjoint_keys": "conj_1..conj_15"},
        },
        "main": {},
        "liara": {},
        "reference_data": {},
        "fixtures": [],
    }

    try:
        main_commit = git_text("rev-parse", args.main_ref)
        liara_commit = git_text("rev-parse", args.liara_ref)
        main_engine_source = git_show(args.main_ref, ENGINE_PATH)
        liara_engine_source = git_show(args.liara_ref, ENGINE_PATH)

        report["main"] = {
            "ref": args.main_ref,
            "commit": main_commit,
            "engine_blob_sha": blob_sha(args.main_ref, ENGINE_PATH),
            "engine_sha256": sha256_bytes(main_engine_source),
            "engine_bytes": len(main_engine_source),
            "function_fingerprints": source_function_fingerprints(main_engine_source),
        }
        report["liara"] = {
            "ref": args.liara_ref,
            "commit": liara_commit,
            "engine_blob_sha": blob_sha(args.liara_ref, ENGINE_PATH),
            "engine_sha256": sha256_bytes(liara_engine_source),
            "engine_bytes": len(liara_engine_source),
            "function_fingerprints": source_function_fingerprints(liara_engine_source),
        }

        with tempfile.TemporaryDirectory(prefix="dark-horse-dual-run-") as tmp:
            tmp_path = Path(tmp)
            main_data_dir = tmp_path / "main"
            liara_data_dir = tmp_path / "liara"
            main_data_dir.mkdir()
            liara_data_dir.mkdir()

            main_data = materialize_data(args.main_ref, main_data_dir)
            liara_data = materialize_data(args.liara_ref, liara_data_dir)

            reference_report: dict[str, Any] = {}
            for path in DATA_PATHS:
                main_raw = git_show(args.main_ref, path)
                liara_raw = git_show(args.liara_ref, path)
                reference_report[path] = {
                    "main": main_data[path],
                    "liara": liara_data[path],
                    "byte_identical": main_raw == liara_raw,
                }
                if main_raw != liara_raw:
                    raise AssertionError(f"reference data drift: {path}")
            report["reference_data"] = reference_report

            motive_payload = load_json_bytes(
                git_show(args.main_ref, "docs/data/micro_motives.json"),
                "docs/data/micro_motives.json",
            )
            motive_codes = extract_motive_codes(motive_payload)

            fixture_files = sorted(FIXTURE_DIR.glob("fixture_*.json"))
            fixtures = [load_json_bytes(p.read_bytes(), str(p)) for p in fixture_files]
            expected = {
                "fixture_branch_01", "fixture_branch_02", "fixture_branch_03",
                "fixture_major_01", "fixture_major_02", "fixture_major_03",
            }
            actual = {x["fixture_id"] for x in fixtures}
            assert actual == expected, (
                f"fixture set mismatch: expected={sorted(expected)} actual={sorted(actual)}"
            )
            for fixture in fixtures:
                validate_fixture(fixture, motive_codes)

            main_engine = load_engine("darkhorse_dual_main", main_engine_source, main_data_dir)
            liara_engine = load_engine("darkhorse_dual_liara", liara_engine_source, liara_data_dir)

            all_pass = True
            for fixture in fixtures:
                try:
                    main_run = invoke(main_engine, fixture)
                    liara_run = invoke(liara_engine, fixture)
                    comparison = compare_runs(fixture["target"], main_run, liara_run)
                    item = {
                        "fixture_id": fixture["fixture_id"],
                        "target": fixture["target"],
                        "status": comparison["status"],
                        "comparison": comparison,
                        "main": main_run,
                        "liara": liara_run,
                    }
                except Exception as exc:
                    all_pass = False
                    item = {
                        "fixture_id": fixture["fixture_id"],
                        "target": fixture["target"],
                        "status": "FAIL",
                        "comparison": {"error": f"{type(exc).__name__}: {exc}"},
                        "main": None,
                        "liara": None,
                    }
                if item["status"] != "PASS":
                    all_pass = False
                report["fixtures"].append(item)

        report["status"] = "PASS" if all_pass else "FAIL"
        report["verdict"] = (
            "خروجی دو build با معیارهای Dual-Run یکسان است."
            if all_pass
            else "اختلاف وجود دارد؛ ریشه اختلاف باید قبل از هر پچ بررسی شود."
        )
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"

    output = ROOT / args.output
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
