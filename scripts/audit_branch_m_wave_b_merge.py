"""Offline, deterministic Wave B comparison against the pinned deploy engine.

Run from repository root: python scripts/audit_branch_m_wave_b_merge.py
No network, database, real user data, or reference-data writes.
"""
import ast
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dark_horse_engine_v2 import DarkHorseEngineV2

BASE = "d053d721b0976288188178579121b8bb7e319995"
REFERENCE_FILES = (
    "docs/data/micro_motives.json", "majors_database_v2.json",
    "school_branches_v2.json", "trait_map_v3.json", "value_poles_v2.json",
)


def baseline_file(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)


def methods(source):
    engine = next(node for node in ast.parse(source).body
                  if isinstance(node, ast.ClassDef) and node.name == "DarkHorseEngineV2")
    return {node.name: ast.dump(node, include_attributes=False) for node in engine.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def main():
    for path in REFERENCE_FILES:
        assert baseline_file(path) == (ROOT / path).read_bytes(), f"Reference changed: {path}"
    old_source = baseline_file("dark_horse_engine_v2.py").decode()
    current_source = (ROOT / "dark_horse_engine_v2.py").read_text()
    before, after = methods(old_source), methods(current_source)
    assert before.keys() == after.keys()
    assert [name for name in before if before[name] != after[name]] == ["_compute_branch_m_score"]
    module = types.ModuleType("wave_b_baseline")
    exec(compile(old_source, "wave_b_baseline", "exec"), module.__dict__)
    old, new = module.DarkHorseEngineV2(), DarkHorseEngineV2()
    branches = list(new.school_branches.values())
    pools = [new._active_branch_code_set(row["micro_motive_codes"]) for row in branches]
    catalog = {code.strip().lower() for code in new.motives_map}
    assert set.union(*pools) == catalog
    assert all(not (left & right) for i, left in enumerate(pools) for right in pools[i + 1:])
    print("# موج B — شواهد تکمیلی Merge و مقایسهٔ قبل/بعد\n")
    print(f"مبنای واقعی deploy: `{BASE}`. اجرا: `python scripts/audit_branch_m_wave_b_merge.py`.\n")
    print("این پروفایل‌ها مصنوعی و قطعی‌اند، نه آمار کاربران. ترتیب بردارها: "
          + "، ".join(row["name"] for row in branches) + ".\n")
    print("برای هر N، از کدهای مرتب‌شدهٔ چهار مخزن به‌ترتیب ۳، ۴، ۵ و N−۱۲ کد انتخاب می‌شود. "
          "موتور قدیم مستقیماً از SHA مبنا اجرا می‌شود؛ پنج JSON مرجع پیش از اجرا byte-identical کنترل می‌شوند.\n")
    print("| N | k چهار شاخه | M قبل، درصد (ثابت ۳۰ با clipping) | M بعد، درصد (k/N) | تعداد عبور از ۱۵٪ قبل → بعد |")
    print("|---|---|---|---|---|")
    expected_counts = {20: (2, 4), 25: (2, 3), 30: (2, 2), 80: (2, 1)}
    for n in (20, 25, 30, 80):
        k = [3, 4, 5, n - 12]
        profile = [code for pool, count in zip(pools, k) for code in sorted(pool)[:count]]
        assert len(set(profile)) == n
        assert sum(len(set(profile) & pool) for pool in pools) == n
        previous = [old._compute_branch_m_score(profile, row)[0] for row in branches]
        current = [new._compute_branch_m_score(profile, row)[0] for row in branches]
        assert all(abs(score - count / n) < 1e-12 for score, count in zip(current, k))
        assert abs(sum(current) - 1) < 1e-12
        counts = tuple(sum(score >= 0.15 for score in scores) for scores in (previous, current))
        assert counts == expected_counts[n]
        # No rounding-edge discrepancy between raw warning and best_branch M eligibility here.
        assert all((score >= 0.15) == (round(score * 100, 1) >= 15)
                   for score in previous + current)
        vector = lambda values: ", ".join(f"{value * 100:.4f}" for value in values)
        print(f"| {n} | {k} | {vector(previous)} | {vector(current)} | {counts[0]} → {counts[1]} |")
    print("\nعبور در جدول فقط شرط M≥۱۵٪ است، نه تعداد توصیه‌های نهایی/قبولی و نه تغییر Total. "
          "برای این چهار fixture، نتیجهٔ شرط M خام و شرط گرد‌شدهٔ موجود یکسان است.\n")
    print("**در N=20 حداقل اشتراک برای گیت ۱۵٪ برابر ۳ است، نه ۵.** "
          "افزایش M برای Nهای ۲۰–۲۹ مصوب و عمدی است؛ آستانهٔ مخفی یا جداگانه‌ای اضافه نشده است.\n")
    print(f"مخزن‌ها جدا و پوشانندهٔ همهٔ {len(catalog)} کد معتبرند؛ در نتیجه برای هر زیرمجموعهٔ معتبر "
          "`Σk_b=N` برقرار است. تست نامتغیر علاوه بر پوشش/جدایی، امتیاز و شواهد واقعی را "
          "برای Nهای ۰،۱،۲۰،۲۵،۲۹،۳۰،۳۱،۴۰،۸۰ و کل کاتالوگ بررسی می‌کند.\n")
    print("کنترل AST: تنها متد تغییرکرده نسبت به deploy مبنا `_compute_branch_m_score` است؛ "
          "M رشته، S/V و Total دست‌نخورده‌اند. JSONهای مرجع نیز عین مبنا هستند.")


if __name__ == "__main__":
    main()
