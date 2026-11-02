# شواهد D1 — حذف metadata گمراه‌کنندهٔ مخرج M شاخه

مبنا: `deploy/liara-commercial-sandbox` در `3c51ac0545e7aa5f45eea3abca33d00fa2c6ab4c`؛ [قرارداد ۱۵خطی](BRANCH_M_METHOD_METADATA_CONTRACT.md). گزینهٔ D1 به‌دلیل صفر مصرف وابسته در مخزن انتخاب شد. Draft؛ Merge فقط با دستور مستقل ناظر.

## جدول مصرف کلید، پیش از تغییر

جست‌وجو روی **خود SHA مبنا** انجام شد، نه نتیجهٔ جست‌وجوی پس از افزودن تست‌های نبود کلید. `m_denom_limit` با `m_score_denom_limit` یکی نیست.

| مسیر | خواندن/نوشتن | آیا می‌توان حذف کرد؟ |
|---|---|---|
| `dark_horse_engine_v2.py:1117`، method در `recommend_school_branch` | تنها writer اجرایی `m_denom_limit`؛ رشتهٔ min/max قدیمی | **بله، هدف D1؛ همین یک خط حذف شد** |
| `main_v2.py:616,689` | عبور کل method در دو API؛ هیچ lookup یا شرط روی `m_denom_limit` ندارد | کلید قدیمی می‌تواند غایب باشد؛ خود شیء method باقی می‌ماند؛ API بدون تغییر |
| `docs/app.js` | هیچ خواندن metadata method یا دو کلید ندارد؛ موارد `method: POST` مربوط HTTP هستند | وابستگی محصولی به کلید حذف‌شده ندارد؛ UI بدون تغییر |
| تست‌های محصول/API در SHA مبنا | هیچ assertion یا fixture وابسته به وجود `m_denom_limit` یافت نشد | بله؛ تست نبود کلید در این موج اضافه شد |
| `docs/weight-review/BRANCH_M_DOCS_ALIGNMENT.md` | نقل تاریخی رشتهٔ خروجی و گزارش خارج از scope بودن اصلاح در PR #340 | مصرف اجرایی نیست؛ تاریخچه حفظ شده، قرارداد جاری این سند D1 است |
| `school_branches_v2.json` | writer مرجع `m_score_denom_limit=30` در چهار رکورد؛ نام متفاوت | **خیر؛ خارج از حذف D1، عین مبنا** |
| `dark_horse_engine_v2.py:185–199,260–263` | validation و getter خصوصیِ `m_score_denom_limit`؛ getter فراخوانی مخزنی ندارد | خیر؛ نه کلید خروجی D1 و نه محاسبهٔ M؛ دست‌نخورده |
| `models.py:124` و `alembic/versions/0001_initial_hybrid_schema.py:88` | تعریف ستون DB با نام `m_score_denom_limit` | خیر؛ schema/Hybrid بدون تغییر |
| `seed_reference_data.py:885` | نوشتن همان ستون تاریخی از مرجع | خیر؛ seed بدون اجرا/تغییر |
| `dual_run_audit.py:75` | خواندن همان ستون برای snapshot ممیزی | خیر؛ ممیزی/Hybrid بدون تغییر |
| `reference_fingerprints.py:253` | projection علمی فیلد مرجع `m_score_denom_limit` | خیر؛ fingerprint و expected بدون تغییر |
| `test_engine_psychometrics.py` و `test_reference_fingerprint_contract.py` | آزمون مقدار۳۰ مرجع، رد مقدار۲۹ و fixture fingerprint؛ همه برای `m_score_denom_limit` | خیر؛ این گیت‌های مستقل حفظ و PASS شدند |
| `docs/weight-review/BRANCH_M_WAVE_B_CONTRACT.md` و `DUAL_FINGERPRINT_IMPLEMENTATION.md` | شرح داده/حفاظت تاریخی `m_score_denom_limit` | سند تاریخی/مرجع است، مصرف کلید method نیست؛ بدون تغییر |

در مخزن، مصرف وابستهٔ مستقیم یا غیرمستقیمِ محصول/تست برای **کلید خروجی** یافت نشد؛ API صرفاً شیء را عبور می‌دهد و frontend آن را نمی‌خواند. کلاینت ناشناختهٔ خارج از مخزن قابل ممیزی نیست؛ عدم استفادهٔ بیرونی تضمین نمی‌شود. حذف خروجی صریحاً در قرارداد اعلام شده، نه اینکه key=null یا مخرج۳۰ دوباره معنا شود.

بازتولید جست‌وجوی پیش از تغییر:

```sh
git grep -n -I -E 'm_denom_limit|m_score_denom_limit' 3c51ac0545e7aa5f45eea3abca33d00fa2c6ab4c
git grep -n -E 'method|_get_branch_denom_limit' 3c51ac0545e7aa5f45eea3abca33d00fa2c6ab4c -- main_v2.py docs/app.js dark_horse_engine_v2.py
```

## تغییر و اثبات عدم تغییر نمره

تنها diff اجرایی، **حذف یک خط دیکشنری method** است؛ هیچ helper، فرمول جایگزین یا فیلد تازه اضافه نشده است. M شاخه همچنان k_b/N و M رشته همان قبلی است. تست AST سه متد M و هر دو تابع توصیه را به مبنا قفل می‌کند؛ برای محاسبهٔ hash مبنا تنها همان جفت کلید/مقدار تاریخیِ دقیق حذف شده، نه کل دیکشنری/بدنه. در منبع جاری هیچ نادیده‌گیری گسترده‌ای انجام نمی‌شود.

سه پروفایل قطعی از کدهای مرتب‌شدهٔ چهار مخزن واقعی؛ ترتیب بردارها: تجربی، ریاضی، انسانی، فنی. ورودی‌های noisy شامل تکرار، حروف متفاوت، فاصله، ناشناخته، خالی و غیررشته‌ای‌اند؛ N مؤثر تغییر نمی‌کند. در API فقط نوع رشته‌ایِ مجاز schema فرستاده می‌شود؛ هیچ bypass اعتبارسنجی ورودی نداریم. پاسخ‌های ثابت S=همه A و V=Q1A..Q15A کامل‌اند.

| N مؤثر | k چهار شاخه | M خام قبل = بعد | M درصدی قبل = بعد |
|---:|---|---|---|
| 20 | 3,4,5,8 | 0.15,0.20,0.25,0.40 | 15,20,25,40 |
| 40 | 10,10,10,10 | 0.25,0.25,0.25,0.25 | 25,25,25,25 |
| 80 | 40,20,10,10 | 0.50,0.25,0.125,0.125 | 50,25,12.5,12.5 |
| 0، کنترل اضافه | 0,0,0,0 | 0,0,0,0 | 0,0,0,0 |

موتور مبنا مستقیماً از Git بارگذاری و اجرا شد: برای هر چهار fixture، **تمام پاسخ قبل/بعد** (امتیازها، S/V، Total، ترتیب، شواهد، best_branch و دیگر methodها) پس از حذف فقط کلید legacy از پاسخ قدیم، دقیقاً برابر بود. این اثبات هم‌نسخهٔ Python است؛ ادعای byte-equality نامحدود میان نسخه‌های مختلف Python نیست. تست‌های CI علاوه بر این، M خام k/N و درصدهای همین جدول را با baseline قفل می‌کنند.

تست نبود کلید روی خود موتور untouched مبنا با assertion failure شکست می‌خورد (نه خطای setup) و روی Draft موفق است. حالت ورودی ناقص S/V هم method بدون کلید دارد؛ رفتار null یا رتبه‌بندی آن تغییر نکرده است.

## تست و CI

- Draft: **۷۸ تست مرتبط PASS**؛ snapshot کامل مبنا: **۷۴ PASS**؛ چهار تست اضافه (سه موتور/AST، یک API چند fixture).
- fingerprint علمی/عضویت/mutation: **۲۰ تست + ۳ subtest PASS**؛ projection و expectedها عین مبنا.
- Node قبلی: V-null و ۳۲ مصرف مرزی Total B **PASS**؛ UI و فایل Node تغییر نکردند.
- موتور و API واقعی روی خروجی نمونه assert می‌کنند `m_denom_limit` موجود نیست؛ سایر فیلدهای method عیناً عبور می‌کنند.
- AST موجود M/S/V و ضرایب Total محفوظ است؛ قفل تازه دو تابع توصیه فقط حذف metadata مصوب را اجازه می‌دهد. فیلد خالی type_params برای Python 3.11/3.12 canonical می‌شود.
- `git diff --check`: PASS؛ هیچ workflow یا گیت تاریخی تغییر نکرده است.

```sh
DATABASE_URL= PYTHONDONTWRITEBYTECODE=1 python -m unittest \
 test_v_range_norm test_engine_psychometrics test_p0_s_score test_v_consumer_contract \
 test_main_api_contract test_reference_fail_closed_startup test_alternative_cache_equivalence -q
python -m pytest -q -p no:cacheprovider test_reference_data_integrity.py \
 test_reference_membership_fingerprint.py test_reference_fingerprint_contract.py
node tests/test_v_null_consumer.js
```

بازپخش ممیزی تاریخی V از snapshot مبنا و Draft در هر دو، پس از AST/parity در **خط۱۹۲، assert reference_weights_unchanged** شکست می‌خورد؛ اسکریپت و BASE تاریخی دست‌نخورده‌اند. JSON و canonical عین مبنا هستند. CI ابری head نهایی با PR #342 هم‌دامنه مقایسه و نتیجه در خود Draft ثبت می‌شود؛ قبل از پایان آن ادعای all-green یا نبود شکست تازه نمی‌کنیم.

**صفر diff معنایی روی نمره‌ها؛ صفر تغییر وزن majors/micro_motives و تمام JSONها، UI، Hybrid، fingerprint علمی، گیت۱۵٪، N، e_b و گیت‌های تاریخی.** موتور فقط یک خط metadata کمتر دارد؛ API اجرایی تغییری نکرده است. Draft؛ بدون Merge یا عملیات runtime/env/DB عملیاتی یا dispatch/rerun.
