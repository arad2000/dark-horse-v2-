# گزارش اجرای جداسازی دو fingerprint مرجع

**وضعیت:** Draft PR؛ پیاده‌سازی در شاخهٔ مستقل و بدون Merge.  
**HEAD مبنای محاسبهٔ expectedها:** `deploy/liara-commercial-sandbox` در commit `02f40f16e044219141a1d354d9d1aa30df416d87` (Merge #320).  
**سیاست ناظر:** `group/cluster/subgroup` در membership؛ `weights_version` در علمی؛ نرمال‌سازی فقط برای stagingهای واقعاً غیرفعال و صریح.

## ۱) فهرست فیلدهای دو لایه

### Fingerprint علمی

| مسیر/فیلد | علت ورود | قرارداد |
|---|---|---|
| `majors_database_v2.json#/id` | کلید اتصال پروفایل به رشته | هویت رکورد علمی |
| `majors_database_v2.json#/motive_driven` | واجدشرایط‌بودن رشته برای discovery فردی | علمی |
| `majors_database_v2.json#/weights_version` | نسخهٔ پروفایل امتیازدهی و منشأ وزن‌های فعال | علمی، مطابق تصمیم ناظر |
| `majors_database_v2.json#/micro_motive_codes` | مجموعهٔ ورودی M-score و هم‌پوشانی جرقه‌ها | علمی |
| `majors_database_v2.json#/strategy_weights` | ماتریس ۲۵×۵ برای S-score و تطبیق پروفایل | علمی |
| `majors_database_v2.json#/value_weights` | ۳۰ قطب Q1A..Q15B برای V-score و تطبیق پروفایل | علمی |
| `school_branches_v2.json#/name` | کلید lookup پروفایل شاخه در موتور | کلید هویتی لازم برای علمی |
| `school_branches_v2.json#/micro_motive_codes` | مجموعهٔ کدهای مؤثر بر M-score شاخه | علمی |
| `school_branches_v2.json#/m_score_denom_limit` | مخرج M-score شاخه | علمی |
| `school_branches_v2.json#/strategy_weights`, `#/value_weights`, `#/weights_version` | پروفایل S/V و نسخهٔ پروفایل شاخه برای مسیرهای جایگزین | علمی |
| `micro_motives.json#/[].code` | فهرست مجاز کدها؛ در فیلتر کدهای مؤثر شاخه استفاده می‌شود | علمی |
| `docs/data/questions_v2.json#/layers/strategies/questions` (شناسه، ترتیب، متن سؤال و متن/ترتیب گزینه‌ها) | پاسخ‌ها موقعیتی‌اند؛ تغییر معنای گزینه می‌تواند معنای وزن اعمال‌شده بر پاسخ یکسان را عوض کند | قرارداد ورودی علمی |

### Fingerprint عضویت / کاتالوگ / هدایت

| مسیر/فیلد | علت ورود | قرارداد |
|---|---|---|
| `majors_database_v2.json#/high_school_branch` | اتصال رشته به شاخهٔ دبیرستان | membership |
| `majors_database_v2.json#/group` | دسته‌بندی کاتالوگی | membership |
| `majors_database_v2.json#/cluster`، `#/subgroup` | خوشه‌بندی و طبقه‌بندی رشته | membership |
| `majors_database_v2.json#/exam_group` | نگاشت گروه آزمون/هدایت پذیرش | membership |
| `majors_database_v2.json#/name` | برچسب و هویت نمایشی رشته در کاتالوگ | membership |
| `school_branches_v2.json#/id`, `#/name`, `#/group` | فهرست شاخه‌ها و طبقه‌بندی آن‌ها | membership |

**موارد خارج از projection علمی در این نسخه:** `trait_map_v3.json`، `value_poles_v2.json`، توضیحات/دسته‌بندی خرده‌انگیزه‌ها، `handcrafted`، `archetype`، `fulfillment_source`، `prestige_level` و `source_majors_count`. این موارد طبق Phase0 روی تفسیر/نمایش/پرووننس اثر می‌گذارند یا هنوز نیازمند تعیین دامنه‌اند؛ در این PR به‌عنوان ورودی عددی امتیازدهی فرض نشده‌اند. تغییر این قرارداد نیازمند تصمیم جداگانه است.

## ۲) expectedهای مستقل از HEAD

روش hash: SHA-256 روی projection نسخه‌دار و canonical؛ کلیدهای object مرتب می‌شوند، ترتیب ماتریس وزن و سؤال/گزینه حفظ می‌شود و اعداد به نمایش دقیق IEEE-754 binary64 کد می‌شوند. قبل از projection، کل درخت داده از نظر NaN/Infinity/overflow بررسی می‌شود.

| دامنهٔ کاتالوگ | Scientific expected | Membership expected |
|---|---|---|
| شناسه‌های ۱–۱۹۴ | `a8107f53800f66c005244503df50d43df57c06ebf2e8625674f03f958a53e9d1` | `1b1be8f6e40bf498512827346593b7010cc04feea5357c470579a03a6f77d4e9` |
| شناسه‌های ۱–۲۰۴ | `0e1075f6d53f6939e0e543232a1f696b5a9ab4c127c7487490461361a33a449c` | `cf9e0adcfb72b2b65ad60eadef633db50b88b07228ea1824d3b8ccd1bc1d0c49` |
| شناسه‌های ۱–۲۱۵ | `136a465802694ddc11a1d14b5a612fdfe9df1ae3f5c4a97bec23b281980ff0cf` | `26457ea856fa9b975dd0cc23fd2cd690104257ff68a5566571a7772986e7af7c` |

این مقادیر expected پیشنهادیِ نسخهٔ اول برای HEAD فوق هستند و در تست‌های مستقل ثبت شده‌اند. با تغییر HEAD یا هر ورودی projection باید جدول شواهد و expected متناظر مجدداً بازبینی شود؛ این PR هیچ baseline تاریخی قدیمی را بازنویسی نمی‌کند.

## ۳) علت اختلاف fingerprint ترکیبی قبلی

expected ترکیبیِ قدیمیِ ردیف‌های ۱–۱۹۴ برابر `5189181b82aab0e6` بود؛ actual روی deploy در HEAD مبنا `f533be54c5fef0d6` است. محاسبهٔ همان تابع قدیمی روی snapshot فعلی main مقدار expected را بازتولید می‌کند. اختلاف deploy را نباید صرفاً به `high_school_branch` نسبت داد:

| شاهد اختلاف deploy نسبت به main در `majors_database_v2.json` | تعداد | اثر بر گیت قدیمی |
|---|---:|---|
| تغییر `strategy_weights` | ۴۲ ردیف | تغییر علمی؛ تغییرهای ردیف‌های ۱۶۱–۱۷۶ پس از نرمال‌سازی قدیمی همچنان در hash می‌مانند |
| تغییر `value_weights` | ۴۲ ردیف | تغییر علمی؛ تغییرهای ردیف‌های ۱۶۱–۱۷۶ پس از نرمال‌سازی قدیمی همچنان در hash می‌مانند |
| تغییر `high_school_branch` | ۲۷ ردیف | تغییر membership که داخل hash ترکیبی باقی می‌ماند |

در گیت تاریخی قدیمی، فیلدهای پروفایل ۲۶ شناسهٔ نامزد staging با مجموعهٔ شناسه‌ها بازنویسی می‌شدند، بدون اینکه وضعیت فعال‌بودن فعلی رکورد بررسی شود. در HEAD مبنا **هر ۲۶ شناسهٔ نامزد، `motive_driven=true` و دارای ۲۵ ردیف strategy و ۳۰ مقدار value است**؛ پس نرمال‌سازی قدیمی، وزن‌های فعالِ واقعی را از hash حذف می‌کرد. در نسخهٔ جدید، شناسه به‌تنهایی مجوز نرمال‌سازی نیست.

سه محاسبهٔ کنترل برای ردیف‌های ۱–۱۹۴ نشان می‌دهد دو دسته اختلاف مستقل‌اند: جایگزینی فقط `high_school_branch`های deploy با مقدارهای main، hash را به `b358ff2f4a29c667` می‌رساند و هنوز expected قدیمی نیست؛ جایگزینی فقط وزن‌های غیرنرمال‌شوندهٔ ردیف‌های ۱۶۱–۱۷۶ با main، hash را به `6255fdada48ce1fd` می‌رساند و باز هم expected قدیمی نیست. بنابراین expected قدیمی محصول یک قرارداد ترکیبی بود که هم تغییر علمی و هم metadata را با هم قفل می‌کرد؛ تغییرهای metadata به‌تنهایی توضیح کامل mismatch نیستند.

### سیاست نرمال‌سازی staging جدید

نرمال‌سازی فقط وقتی مجاز است که هر سه شرط برقرار باشند: شناسه در مجموعهٔ صریح candidateهای staging باشد؛ `motive_driven is false`؛ و `weights_version == "deferred_catalog_only_v1"`. علاوه بر آن، کدهای خرده‌انگیزه و ماتریس/وزن‌ها باید خالی باشند؛ وجود دادهٔ پروفایل در چنین رکوردی به‌جای حذف/پنهان‌سازی، خطای قرارداد ایجاد می‌کند. رکورد فعال، حتی با شناسهٔ candidate قدیمی، بدون نرمال‌سازی و با وزن‌های واقعی fingerprint می‌شود.

## ۴) حداقل تست‌ها

| تست | انتظار | محل تست |
|---|---|---|
| فقط تغییر `high_school_branch` | scientific ثابت؛ membership تغییر کند | `test_reference_fingerprint_contract.py::test_only_high_school_branch_changes_membership_not_science` |
| فقط تغییر یک `strategy_weight` در major فعال | scientific تغییر کند؛ membership ثابت بماند | `test_reference_fingerprint_contract.py::test_only_active_strategy_weight_changes_science_not_membership` |
| NaN و ±Infinity | قبل از hash رد شوند | `test_reference_fingerprint_contract.py::test_non_finite_numbers_are_rejected_before_hashing` |
| loader #320 | تست‌های رد NaN/Infinity و exponent overflow بدون تغییر باقی مانده‌اند و همچنان در CI اجرا می‌شوند | `test_seed_reference_json.py` و گام `Strict seed JSON parsing contracts` |

همچنین تست مستقل، سیاست `group/cluster/subgroup` و `weights_version` را assert می‌کند. عضویت در workflow با گام مستقل `Reference-data integrity (membership fingerprint)` اجرا می‌شود؛ این گام با `if: always()` حتی در صورت شکست گیت علمی نیز نتیجهٔ خودش را گزارش می‌دهد. شکست scientific همچنان گام اصلی Reference-data integrity را قرمز می‌کند؛ شکست membership فقط در گام membership مشخص می‌شود و PASS علمی را به PASS کلی کاذب تبدیل نمی‌کند.

## ۵) دامنهٔ تغییر و وضعیت Merge

- گیت قدیمیِ ترکیبی فقط به‌عنوان گزارش forensic نگه داشته شده است؛ دیگر معیار pass/fail نیست، چون دو لایهٔ متفاوت و وزن‌های مرحله‌ای فعال را در یک hash مخلوط می‌کرد. expectedهای قدیمی دست‌نخورده و در گزارش باقی‌اند.
- گیت scientific و membership با expectedهای جدا و مبتنی بر HEAD جایگزین شده‌اند؛ هر دو مستقل و fail-closed هستند.
- loader/seed و تست‌های سخت‌گیرانهٔ #320 تغییر نکرده‌اند.
- `majors_database_v2.json`، `school_branches_v2.json`، `micro_motives.json`، `questions_v2.json`، وزن‌ها، engine، Hybrid، cutover، env لیارا، UI و درگاه تغییر نکرده‌اند.
- هیچ فایل اجرایی به #321 یا #322 اضافه نشده و هیچ‌کدام Merge نشده‌اند.
- **Merge = خیر؛ پیاده‌سازی فقط برای بازبینی در Draft PR است.**

مراجع طراحی: [سند سیاست fingerprint](https://github.com/arad2000/dark-horse-v2-/blob/53631a35fff4bc00299858a41073a0694a782f1b/docs/weight-review/HIGH_SCHOOL_BRANCH_FINGERPRINT_POLICY.md) و [سند Phase0](https://github.com/arad2000/dark-horse-v2-/blob/2ed948409184572617cfa0b179f4946ebb392a1a/docs/weight-review/DUAL_FINGERPRINT_PHASE0.md).
