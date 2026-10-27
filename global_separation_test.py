#!/usr/bin/env python3
"""
global_separation_test.py — گزارش Pearson و برخورد امضای راهبردی رشته‌ها.

فقط رشته‌هایی وارد Pearson و چک signature کامل می‌شوند که
strategy_weights کامل با شکل 25×5 داشته باشند. ردیف‌های بدون/ناقص پروفایل
بدون تغییر وزن کنار گذاشته و تعدادشان گزارش می‌شود.

آستانه‌های Pearson صرفاً تشخیصی‌اند و تغییر نکرده‌اند:
  - درون‌خوشه‌ای: 0.70
  - بین‌خوشه‌ای: 0.50

استفاده:
    python3 global_separation_test.py <مسیر majors_database_v2.json> [--strategy-only] [--value-only]
"""
import itertools
import json
import math
import sys
from collections import defaultdict
from statistics import mean, StatisticsError

STRATEGY_THRESHOLD_INTRA = 0.70
STRATEGY_THRESHOLD_INTER = 0.50


def is_complete_strategy_profile(major):
    sw = major.get("strategy_weights")
    return (
        isinstance(sw, list)
        and len(sw) == 25
        and all(
            isinstance(row, list)
            and len(row) == 5
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in row)
            for row in sw
        )
    )


def profile_vector(major, include_strategy=True, include_value=True):
    vector = []
    if include_strategy:
        if not is_complete_strategy_profile(major):
            raise ValueError(f"major {major.get('id', major.get('name', '?'))} has incomplete strategy_weights")
        for row in major["strategy_weights"]:
            vector.extend(row)
    if include_value:
        value_weights = major.get("value_weights") or {}
        for i in range(1, 16):
            vector.append(value_weights.get(f"Q{i}A", 0))
            vector.append(value_weights.get(f"Q{i}B", 0))
    return vector


def pearson(a, b):
    if not a or not b:
        raise ValueError("Pearson requires non-empty vectors; empty profiles must be filtered before comparison")
    if len(a) != len(b):
        raise ValueError(f"Pearson vector length mismatch: {len(a)} != {len(b)}")
    ma, mb = mean(a), mean(b)
    covariance = sum((a[i] - ma) * (b[i] - mb) for i in range(len(a)))
    variance_a = sum((x - ma) ** 2 for x in a)
    variance_b = sum((x - mb) ** 2 for x in b)
    return covariance / (variance_a * variance_b) ** 0.5 if variance_a > 0 and variance_b > 0 else 0.0


def run(majors, include_strategy, include_value, label):
    print(f"\n=== {label} — {len(majors)} رشتهٔ دارای strategy_weights کامل ===\n")
    if len(majors) < 2:
        print("اطلاعات کافی برای مقایسهٔ زوجی وجود ندارد (حداقل دو رشتهٔ دارای پروفایل لازم است).")
        return

    by_cluster = defaultdict(list)
    for major in majors:
        by_cluster[major.get("cluster") or "؟"].append(major)

    intra_viol, intra_total = 0, 0
    worst = []
    for cluster, members in by_cluster.items():
        for major_a, major_b in itertools.combinations(members, 2):
            sim = pearson(
                profile_vector(major_a, include_strategy, include_value),
                profile_vector(major_b, include_strategy, include_value),
            )
            intra_total += 1
            if sim > STRATEGY_THRESHOLD_INTRA:
                intra_viol += 1
            worst.append((sim, major_a.get("name", major_a.get("id")), major_b.get("name", major_b.get("id")), "درون‌خوشه‌ای"))

    clusters = list(by_cluster.keys())
    inter_viol, inter_total = 0, 0
    for c1, c2 in itertools.combinations(clusters, 2):
        for major_a in by_cluster[c1]:
            for major_b in by_cluster[c2]:
                sim = pearson(
                    profile_vector(major_a, include_strategy, include_value),
                    profile_vector(major_b, include_strategy, include_value),
                )
                inter_total += 1
                if sim > STRATEGY_THRESHOLD_INTER:
                    inter_viol += 1

    pct_intra = 100 * intra_viol / intra_total if intra_total else 0
    pct_inter = 100 * inter_viol / inter_total if inter_total else 0
    print(f"درون‌خوشه‌ای (آستانه {STRATEGY_THRESHOLD_INTRA*100:.0f}%): {intra_viol}/{intra_total} نقض ({pct_intra:.1f}%)")
    print(f"بین‌خوشه‌ای (آستانه {STRATEGY_THRESHOLD_INTER*100:.0f}%): {inter_viol}/{inter_total} نقض ({pct_inter:.1f}%)")

    worst.sort(key=lambda item: -item[0])
    print(f"\n۱۰ نزدیک‌ترین جفت ({label}):")
    for sim, name_a, name_b, kind in worst[:10]:
        print(f"  [{kind}] {name_a} <-> {name_b} : {sim:.4f}")


def check_signature_collisions(majors):
    eligible = [m for m in majors if is_complete_strategy_profile(m)]
    groups = defaultdict(list)
    for major in eligible:
        signature = tuple(row.index(max(row)) for row in major["strategy_weights"])
        groups[signature].append(major.get("name", major.get("id")))
    repeated = {signature: names for signature, names in groups.items() if len(names) > 1}
    collision_count = sum(len(names) for names in repeated.values())
    print("\n=== چک signature کامل (گسسته) ===")
    print(f"رشته‌های واردشده به چک signature: {len(eligible)} از {len(majors)}")
    print(f"رشته‌های درگیر signature کاملاً یکسان: {collision_count}")
    for names in repeated.values():
        print("  ", names)
    return collision_count


def main():
    if len(sys.argv) < 2:
        print("استفاده: python3 global_separation_test.py <مسیر majors_database_v2.json> [--strategy-only] [--value-only]")
        sys.exit(2)

    path = sys.argv[1]
    flags = sys.argv[2:]
    try:
        with open(path, encoding="utf-8") as fp:
            all_majors = json.load(fp)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"خطا در خواندن majors_database_v2.json: {exc}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(all_majors, list):
        print("خطای ورودی: انتظار می‌رود ریشهٔ majors_database_v2.json یک آرایه باشد.", file=sys.stderr)
        sys.exit(2)

    eligible = [major for major in all_majors if isinstance(major, dict) and is_complete_strategy_profile(major)]
    skipped = len(all_majors) - len(eligible)
    print(f"کل رشته‌های کاتالوگ: {len(all_majors)}")
    print(f"رشته‌های دارای strategy_weights کامل و واردشده به تحلیل: {len(eligible)}")
    print(f"ردیف‌های حذف‌شده از Pearson/signature به‌علت پروفایل ناقص: {skipped}")

    if not eligible:
        print("خطای ورودی: هیچ رشته‌ای strategy_weights کامل 25×5 ندارد؛ تحلیل انجام نشد.", file=sys.stderr)
        sys.exit(1)

    check_signature_collisions(eligible)

    try:
        if "--value-only" in flags:
            run(eligible, False, True, "فقط ارزش (value_weights)")
        elif "--strategy-only" in flags:
            run(eligible, True, False, "فقط راهبرد (strategy_weights)")
        else:
            run(eligible, True, False, "فقط راهبرد (strategy_weights)")
            run(eligible, False, True, "فقط ارزش (value_weights)")
            run(eligible, True, True, "ترکیبی (راهبرد + ارزش)")
    except (ValueError, TypeError, KeyError, StatisticsError) as exc:
        print(f"خطای محاسبهٔ جداسازی: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
