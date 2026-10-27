#!/usr/bin/env python3
"""
global_separation_test.py — تست جداسازی آماری (همبستگی Pearson) اسب سیاه

پروفایل کامل هر رشته را (strategy_weights + value_weights، هردو با هم)
می‌سازد و همبستگی Pearson بین هر دو رشته را حساب می‌کند. دو نوع نقض
گزارش می‌شود:
  - درون‌خوشه‌ای (آستانهٔ پیش‌فرض ۷۰٪): دو رشتهٔ هم‌خوشه که بیش‌ازحد شبیه‌اند
  - بین‌زیرگروهی (آستانهٔ پیش‌فرض ۵۰٪): دو رشتهٔ خوشهٔ متفاوت که بیش‌ازحد شبیه‌اند

⚠️ این معیار صرفاً برای آگاهی است، نه هدف سخت‌گیرانه. رشته‌های واقعاً
هم‌خانواده (مثلاً دو مهندسی دقیق) طبیعتاً همبستگی بالا دارند حتی با
شواهد کاملاً صادقانه. تلاش برای کاهش مصنوعی این عدد به قیمت دورشدن از
شواهد واقعی اشتباه است.

استفاده:
    python3 global_separation_test.py <مسیر majors_database_v2.json> [--strategy-only] [--value-only]
"""
import json
import sys
import itertools
from statistics import mean

STRATEGY_THRESHOLD_INTRA = 0.70
STRATEGY_THRESHOLD_INTER = 0.50


def profile_vector(m, include_strategy=True, include_value=True):
    v = []
    if include_strategy:
        for row in m["strategy_weights"]:
            v.extend(row)
    if include_value:
        for i in range(1, 16):
            v.append(m["value_weights"].get(f"Q{i}A", 0))
            v.append(m["value_weights"].get(f"Q{i}B", 0))
    return v


def pearson(a, b):
    n = len(a)
    ma, mb = mean(a), mean(b)
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    return cov / (va * vb) ** 0.5 if va > 0 and vb > 0 else 0


def run(majors, include_strategy, include_value, label):
    print(f"\n=== {label} — {len(majors)} رشته ===\n")

    by_cluster = {}
    for m in majors:
        by_cluster.setdefault(m.get("cluster", "؟"), []).append(m)

    intra_viol, intra_total = 0, 0
    worst = []
    for cluster, members in by_cluster.items():
        for m1, m2 in itertools.combinations(members, 2):
            sim = pearson(
                profile_vector(m1, include_strategy, include_value),
                profile_vector(m2, include_strategy, include_value),
            )
            intra_total += 1
            if sim > STRATEGY_THRESHOLD_INTRA:
                intra_viol += 1
            worst.append((sim, m1.get("name", m1.get("id")), m2.get("name", m2.get("id")), "درون‌خوشه‌ای"))

    clusters = list(by_cluster.keys())
    inter_viol, inter_total = 0, 0
    for c1, c2 in itertools.combinations(clusters, 2):
        for m1 in by_cluster[c1]:
            for m2 in by_cluster[c2]:
                sim = pearson(
                    profile_vector(m1, include_strategy, include_value),
                    profile_vector(m2, include_strategy, include_value),
                )
                inter_total += 1
                if sim > STRATEGY_THRESHOLD_INTER:
                    inter_viol += 1

    pct_intra = 100 * intra_viol / intra_total if intra_total else 0
    pct_inter = 100 * inter_viol / inter_total if inter_total else 0
    print(f"درون‌خوشه‌ای (آستانه {STRATEGY_THRESHOLD_INTRA*100:.0f}%): {intra_viol}/{intra_total} نقض ({pct_intra:.1f}%)")
    print(f"بین‌زیرگروهی (آستانه {STRATEGY_THRESHOLD_INTER*100:.0f}%): {inter_viol}/{inter_total} نقض ({pct_inter:.1f}%)")

    worst.sort(key=lambda x: -x[0])
    print(f"\n۱۰ نزدیک‌ترین جفت ({label}):")
    for sim, n1, n2, kind in worst[:10]:
        print(f"  [{kind}] {n1} <-> {n2} : {sim:.4f}")


def check_signature_collisions(majors):
    from collections import defaultdict

    def sig(m):
        return tuple(row.index(max(row)) for row in m["strategy_weights"])

    groups = defaultdict(list)
    for m in majors:
        groups[sig(m)].append(m.get("name", m.get("id")))
    repeated = {s: names for s, names in groups.items() if len(names) > 1}
    total = sum(len(v) for v in repeated.values())
    print(f"\n=== چک signature کامل (گسسته) ===")
    print(f"رشته‌های signature کاملاً یکسان: {total} از {len(majors)}")
    for names in repeated.values():
        print("  ", names)


def main():
    if len(sys.argv) < 2:
        print("استفاده: python3 global_separation_test.py <مسیر majors_database_v2.json> [--strategy-only] [--value-only]")
        sys.exit(1)

    majors = json.load(open(sys.argv[1], encoding="utf-8"))
    flags = sys.argv[2:]

    check_signature_collisions(majors)

    if "--value-only" in flags:
        run(majors, False, True, "فقط ارزش (value_weights)")
    elif "--strategy-only" in flags:
        run(majors, True, False, "فقط راهبرد (strategy_weights)")
    else:
        run(majors, True, False, "فقط راهبرد (strategy_weights)")
        run(majors, False, True, "فقط ارزش (value_weights)")
        run(majors, True, True, "ترکیبی (راهبرد + ارزش)")


if __name__ == "__main__":
    main()