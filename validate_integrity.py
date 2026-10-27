#!/usr/bin/env python3
"""
validate_integrity.py — چک ساختاری کامل دیتابیس اسب سیاه

هم راهبرد (strategy_weights) و هم ارزش (value_weights) را برای
majors_database_v2.json و school_branches_v2.json بررسی می‌کند؛
همچنین ارجاعات بین فایل‌ها (کدهای میکرو-موتیو، کلیدهای ارزشی) و
ساختار questions_v2.json و trait_map_v3.json را چک می‌کند.

استفاده:
    python3 validate_integrity.py <پوشهٔ حاوی فایل‌های JSON>

پوشهٔ ورودی باید این فایل‌ها را داشته باشد:
    majors_database_v2.json
    school_branches_v2.json
    micro_motives.json
    value_poles_v2.json
    questions_v2.json
    trait_map_v3.json
"""
import json
import sys
from pathlib import Path

OK = "✅"
FAIL = "❌"


def load(folder: Path, name: str):
    path = folder / name
    if not path.exists():
        return None, f"{FAIL} فایل {name} در پوشه پیدا نشد"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"{FAIL} فایل {name} قابل‌خواندن نیست: {e}"


def check_strategy_weights(entries, label, errors, name_key="name"):
    ok_shape = True
    ok_sum = True
    ok_range = True
    for e in entries:
        sw = e.get("strategy_weights")
        nm = e.get(name_key, e.get("id", "؟"))
        if not sw or len(sw) != 25:
            errors.append(f"{FAIL} {label}: «{nm}» تعداد ردیف‌های strategy_weights اشتباه است ({len(sw) if sw else 0}/25)")
            ok_shape = False
            continue
        for i, row in enumerate(sw):
            if len(row) != 5:
                errors.append(f"{FAIL} {label}: «{nm}» ردیف S{i+1:02d} تعداد مقادیرش ۵ نیست")
                ok_shape = False
            if abs(sum(row) - 1.0) > 0.001:
                errors.append(f"{FAIL} {label}: «{nm}» ردیف S{i+1:02d} جمعش {sum(row):.4f} است، نه ۱")
                ok_sum = False
            if any(v < 0 or v > 1 for v in row):
                errors.append(f"{FAIL} {label}: «{nm}» ردیف S{i+1:02d} مقداری خارج از [۰,۱] دارد")
                ok_range = False
    if ok_shape:
        print(f"{OK} {label}: همهٔ strategy_weights شکل ۲۵×۵ درست دارند")
    if ok_sum:
        print(f"{OK} {label}: همهٔ سطرهای strategy_weights نرمالایز شده‌اند (جمع≈۱)")
    if ok_range:
        print(f"{OK} {label}: همهٔ مقادیر strategy_weights در بازهٔ [0,1] هستند")


def check_value_weights(entries, label, errors, name_key="name"):
    expected_keys = {f"Q{i}{l}" for i in range(1, 16) for l in ("A", "B")}
    ok_count = True
    ok_range = True
    ok_keys = True
    for e in entries:
        vw = e.get("value_weights") or {}
        nm = e.get(name_key, e.get("id", "؟"))
        if len(vw) != 30:
            errors.append(f"{FAIL} {label}: «{nm}» تعداد کلیدهای value_weights {len(vw)} است، نه ۳۰")
            ok_count = False
        missing = expected_keys - set(vw.keys())
        if missing:
            errors.append(f"{FAIL} {label}: «{nm}» کلیدهای غایب در value_weights: {sorted(missing)}")
            ok_keys = False
        for k, v in vw.items():
            if not (0 <= v <= 1):
                errors.append(f"{FAIL} {label}: «{nm}» مقدار value_weights[{k}]={v} خارج از [۰,۱] است")
                ok_range = False
    if ok_count:
        print(f"{OK} {label}: همهٔ value_weights دقیقاً ۳۰ کلید مورد انتظار دارند")
    if ok_keys:
        print(f"{OK} {label}: همهٔ کلیدهای Q1A..Q15B در value_weights موجودند")
    if ok_range:
        print(f"{OK} {label}: همهٔ مقادیر value_weights در بازهٔ [0,1] هستند")


def check_micro_motive_refs(entries, motive_codes, errors, label):
    broken = []
    for entry in entries:
        for code in entry.get("micro_motive_codes", []):
            if code not in motive_codes:
                broken.append((entry.get("name", entry.get("id", "؟")), code))
    if broken:
        for name, code in broken[:20]:
            errors.append(f"{FAIL} {label}: «{name}» کد میکرو-موتیو نامعتبر دارد: {code}")
        print(f"{FAIL} {label}: {len(broken)} ارجاع شکسته به micro_motives.json")
    else:
        print(f"{OK} {label}: همهٔ micro_motive_codes در micro_motives.json موجودند (صفر رفرنس شکسته)")

def check_value_poles_coverage(entries, value_pole_keys, label, errors):
    all_covered = True
    for e in entries:
        vw = e.get("value_weights") or {}
        missing = set(vw.keys()) - value_pole_keys
        if missing:
            errors.append(f"{FAIL} {label}: «{e.get('name', e.get('id','؟'))}» کلیدهایی دارد که در value_poles.json تعریف نشده: {sorted(missing)}")
            all_covered = False
    if all_covered:
        print(f"{OK} {label}: همهٔ کلیدهای value_weights در value_poles.json پوشش دارند")


def is_complete_strategy_profile(entry):
    sw = entry.get("strategy_weights")
    return (
        isinstance(sw, list)
        and len(sw) == 25
        and all(
            isinstance(row, list)
            and len(row) == 5
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in row)
            for row in sw
        )
    )


def check_signature_collisions(majors, errors):
    from collections import defaultdict

    eligible = [m for m in majors if is_complete_strategy_profile(m)]

    def sig(m):
        return tuple(row.index(max(row)) for row in m["strategy_weights"])

    groups = defaultdict(list)
    for m in eligible:
        groups[sig(m)].append(m.get("name", m.get("id", "؟")))
    repeated = {s: names for s, names in groups.items() if len(names) > 1}
    total_dupes = sum(len(v) for v in repeated.values())
    if repeated:
        for names in repeated.values():
            errors.append(f"{FAIL} signature کاملاً یکسان بین: {names}")
        print(f"{FAIL} majors_database: {total_dupes} رشته درگیر signature کاملاً یکسان هستند")
    else:
        print(f"{OK} majors_database: صفر رشته با signature کاملاً یکسان (از {len(eligible)} رشتهٔ فعالِ دارای پروفایل)")

def check_school_branches_coverage(branches, active_majors, errors):
    from collections import Counter

    branch_names = {b.get("name") for b in branches}
    active_counts = Counter(m.get("high_school_branch") for m in active_majors)
    unassigned = [
        m for m in active_majors
        if m.get("high_school_branch") not in branch_names
    ]
    if unassigned:
        for m in unassigned[:20]:
            errors.append(
                f"{FAIL} active major «{m.get('name', m.get('id', '؟'))}» high_school_branch نامعتبر/خالی دارد: {m.get('high_school_branch')!r}"
            )
        print(f"{FAIL} school_branches: {len(unassigned)} رشتهٔ فعال به شاخهٔ معتبر تخصیص ندارند")
    else:
        print(f"{OK} school_branches: همهٔ {len(active_majors)} رشتهٔ فعال high_school_branch معتبر دارند")

    count_mismatches = []
    for branch in branches:
        name = branch.get("name")
        expected = active_counts.get(name, 0)
        actual = branch.get("source_majors_count")
        if actual != expected:
            count_mismatches.append((name, actual, expected))
            errors.append(
                f"{FAIL} school_branches: «{name}» source_majors_count={actual} است؛ count(high_school_branch) روی فعال‌ها={expected}"
            )
    if count_mismatches:
        print(f"{FAIL} school_branches: {len(count_mismatches)} source_majors_count با شمارش رشته‌های فعال هم‌خوان نیست")
    else:
        total = sum(active_counts.get(b.get("name"), 0) for b in branches)
        print(f"{OK} school_branches: source_majors_count هر شاخه با count(high_school_branch) روی رشته‌های فعال تطبیق دارد (جمع={total})")

def check_questions(questions_data, errors):
    strat_qs = questions_data.get("layers", {}).get("strategies", {}).get("questions", [])
    expected_ids = [f"S{i:02d}" for i in range(1, 26)]
    actual_ids = [q.get("id") for q in strat_qs]
    if actual_ids == expected_ids:
        print(f"{OK} questions_v2: ترتیب 25 سؤال راهبردی دقیقاً S01..S25 است")
    else:
        errors.append(f"{FAIL} questions_v2: ترتیب/تعداد سؤالات راهبردی اشتباه است: {actual_ids}")

    for q in strat_qs:
        opts = q.get("options", [])
        if len(opts) != 5:
            errors.append(f"{FAIL} questions_v2: سؤال {q.get('id')} تعداد گزینه‌هایش ۵ نیست")

    val_qs = questions_data.get("layers", {}).get("values", {}).get("questions", [])
    val_ids = [q.get("id") for q in val_qs]
    if len(val_qs) == 15 and len(set(val_ids)) == 15:
        print(f"{OK} questions_v2: 15 سؤال ارزشی، بدون شناسهٔ تکراری")
    else:
        errors.append(f"{FAIL} questions_v2: تعداد/یکتایی سؤالات ارزشی اشتباه است (تعداد={len(val_qs)})")


def check_trait_map(trait_map, errors):
    expected = {f"S{i:02d}" for i in range(1, 26)}
    actual = set(trait_map.keys())
    if actual == expected:
        print(f"{OK} trait_map_v3: دقیقاً کلیدهای S01..S25 موجودند")
    else:
        errors.append(f"{FAIL} trait_map_v3: کلیدهای غایب/اضافه: {expected ^ actual}")

    all_5 = True
    for k, v in trait_map.items():
        n_opts = len(v) if isinstance(v, (list, dict)) else 0
        if n_opts != 5:
            all_5 = False
            errors.append(f"{FAIL} trait_map_v3: سؤال {k} تعداد گزینه‌هایش ۵ نیست")
    if all_5:
        print(f"{OK} trait_map_v3: همهٔ سؤالات دقیقاً ۵ گزینه (0..4) دارند")


def main():
    if len(sys.argv) < 2:
        print("استفاده: python3 validate_integrity.py <پوشهٔ فایل‌های JSON>")
        sys.exit(1)

    folder = Path(sys.argv[1])
    errors = []

    majors, err = load(folder, "majors_database_v2.json")
    if err:
        print(err)
        sys.exit(1)

    school_branches, err_sb = load(folder, "school_branches_v2.json")
    micro_motives, err_mm = load(folder, "micro_motives.json")
    value_poles, err_vp = load(folder, "value_poles_v2.json")
    questions, err_q = load(folder, "questions_v2.json")
    trait_map, err_tm = load(folder, "trait_map_v3.json")

    active_majors = [m for m in majors if m.get("motive_driven") is True]
    expected_value_keys = {f"Q{i}{l}" for i in range(1, 16) for l in ("A", "B")}

    def has_complete_profile(entry):
        sw = entry.get("strategy_weights")
        vw = entry.get("value_weights")
        return (
            is_complete_strategy_profile(entry)
            and isinstance(vw, dict)
            and len(vw) == 30
            and set(vw.keys()) == expected_value_keys
        )

    catalog_only_unweighted = [
        m for m in majors
        if m.get("motive_driven") is not True and not has_complete_profile(m)
    ]

    print("\n=== validation scope ===")
    print(f"{OK} motive_driven=true: {len(active_majors)} active majors are subject to S/V, signature, and active-major reference checks")
    print(f"{OK} catalog-only/unweighted: {len(catalog_only_unweighted)} inactive rows are reported, not failed for missing profiles")
    for entry in catalog_only_unweighted:
        print(f"  catalog-only/unweighted id={entry.get('id', '؟')} name={entry.get('name', '؟')}")

    motive_codes = set()
    vp_keys = set()

    print("\n=== majors_database_v2.json (active only) ===")
    check_strategy_weights(active_majors, "active majors", errors)
    check_value_weights(active_majors, "active majors", errors)
    check_signature_collisions(active_majors, errors)

    if micro_motives is not None:
        motive_codes = {d["code"] for d in micro_motives}
        check_micro_motive_refs(active_majors, motive_codes, errors, "active majors")
    else:
        errors.append(err_mm)
        print(err_mm)

    if value_poles is not None:
        if isinstance(value_poles, dict):
            vp_keys = set(value_poles.keys())
        else:
            vp_keys = {d.get("key") for d in value_poles if isinstance(d, dict)}
        check_value_poles_coverage(active_majors, vp_keys, "active majors", errors)
    else:
        errors.append(err_vp)
        print(err_vp)

    if school_branches is not None:
        print("\n=== school_branches_v2.json (all four active branches) ===")
        check_strategy_weights(school_branches, "school_branches", errors)
        check_value_weights(school_branches, "school_branches", errors)
        if micro_motives is not None:
            check_micro_motive_refs(school_branches, motive_codes, errors, "school_branches")
        if value_poles is not None:
            check_value_poles_coverage(school_branches, vp_keys, "school_branches", errors)
        check_school_branches_coverage(school_branches, active_majors, errors)
    else:
        errors.append(err_sb)
        print(err_sb)

    if questions is not None:
        print("\n=== questions_v2.json ===")
        check_questions(questions, errors)
    else:
        errors.append(err_q)
        print(err_q)

    if trait_map is not None:
        print("\n=== trait_map_v3.json ===")
        check_trait_map(trait_map, errors)
    else:
        errors.append(err_tm)
        print(err_tm)

    print("\n" + "=" * 50)
    if errors:
        print(f"{FAIL} مجموعاً {len(errors)} خطا پیدا شد:\n")
        for e in errors:
            print(" ", e)
        sys.exit(1)
    else:
        print(f"{OK} همهٔ تست‌ها موفق بودند.")
        sys.exit(0)

if __name__ == "__main__":
    main()