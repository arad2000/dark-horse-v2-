# رسید پالایش ساخت و انتشار — ۲۰۲۶-۱۱-۰۲

## مبنا و دامنه

- مبنا: deploy مصوب `8ddd2aadb62d84ae6aa2c74309822a400783f0b9`، شامل #344.
- main مقایسه‌شده: `4b918261f3f7996439e6f9c98fe83f81f7df3c8d`.
- تمام کار روی شاخهٔ نشست `arena/c06041b7-dark-horse-v2` است. مبنای همین شاخه با rebase روی deploy قرار گرفت؛ شاخهٔ دیگری ساخته/تعویض نشد. گزارش‌های پیشینِ untracked محفوظ ماندند و با این تغییر اجرایی مخلوط نشدند.
- مجوز این نوبت: پیش‌برد ترتیب ساخت/بسته‌بندی، خطای syntax، تعیین تکلیف اختلاف canonical، سپس نسخهٔ وابستگی‌ها/تست مرورگر. **مشاورهٔ AI کاملاً خارج از دامنهٔ تغییر است.**

## نتیجه به ترتیب

| بخش | وضعیت | شاهد |
|---|---|---|
| ۱. ساخت backend از artifact تمیز | **انجام شد** | README مسیر main و deploy را جدا می‌کند؛ script جدید import/lifespan offline؛ artifact با git archive و venv تازه ساخته و آزموده شد |
| ۲. خطای syntax در deploy | **انجام شد** | فقط یک comma در docs/data.js اضافه شد؛ parse-only regression تمام۲۴script را کنترل می‌کند؛ متن و نگاشت کارت‌ها عوض نشد |
| ۳. اختلاف canonical | **بررسی شد؛ اصلاح داده متوقف برای تصمیم مستقل** | سه اختلاف واقعی/محتوایی وجود دارد؛ گیت همان خروجی شکست را حفظ کرده است؛ sync یا تغییر مرجع انجام نشد |
| ۴الف. نسخهٔ وابستگی‌ها و بهداشت محلی | **انجام شد، در محدودهٔ محیط آزموده‌شده** | constraints اجباریِ۲۳نسخه از نصب تمیز، بدون تغییر نسخه نسبت به رسید اولیه؛ gitignore برای محیط/bytecode/config محلی |
| ۴ب. مرورگر واقعی | **مسدود توسط محیط؛ PASS نیست** | نصب ابزار خارج مخزن انجام شد، ولی Chromium پیش از بازکردن صفحه با نبود libnspr4.so متوقف شد. آزمون Node/DOM جای آن شمرده نمی‌شود |

## ۱. تغییرات ساخت

Commit: `5caf7dc04a7f524d163b6972c2b0203aedc75ee0`.

- README دیگر clone پیش‌فرض main را مسیر اجرای backend کامل معرفی نمی‌کند؛ SHA و artifact تمیز را ثبت و نقش deploy را مشخص می‌کند.
- `scripts/backend_build_smoke.py` پوشهٔ artifact و فایل‌های لازم را کنترل می‌کند؛ interpreter نصب‌شده را با `-I` و allowlist محیط اجرا می‌کند؛ credentialها و تنظیمات عملیاتی والد منتقل نمی‌شوند. DATABASE_URL خالی، shadow/cutover/bootstrap خاموش‌اند و مسیرهای متداول socket connect مسدود می‌شوند.
- child فقط import و startup/shutdown موتور را انجام می‌دهد؛ نه listener، درخواست API، DB، migration، پرداخت یا AI. این چک جای sandbox سیستم‌عامل یا readiness عملیاتی نیست.
- شش تست جدید، حذف تنظیمات موروثی، نبود فایل، موفقیت/شکست child، timeout و guard socket را می‌سنجند. دو تست startup و یک تست تنظیم Liara موجود نیز PASS شدند؛ تنظیم Liara تغییر نکرد.

رسید عملی: از همان commit با git archive، خارج مخزن artifact ساخته شد؛ Python 3.11.2 و venv تازه؛ نصب requirements و `pip check` موفق؛ `APP_IMPORT=PASS`، `SCORING_REFERENCES=PASS`، `SHARED_ENGINE=PASS`، `LIFESPAN=PASS`. `EXTERNAL_SERVICES=NOT_TESTED` عمدی است. مقایسهٔ این رسید با نبود backend کامل در main، ادعای خرابی سرویس زنده نیست.

## ۲. اصلاح حداقلی syntax

Commit: `6f4da33`.

تنها تغییر در دادهٔ UI:

```diff
 majorCodes: ['GEOG-']
- }
+ },
```

`tests/test_public_javascript_syntax.js` همهٔ فایل‌های JS زیر docs را با vm.Script **parse می‌کند و اجرا نمی‌کند**؛ ۲۴/۲۴ PASS. کنترل منفی با محتوای دست‌نخوردهٔ `8ddd2aa:docs/data.js`، همان SyntaxError را بازتولید کرد. هیچ نام/متن/prefix/ترتیب/وزن، برچسب «از۷» یا app.js تغییر نکرد. نسخهٔ main از قبل syntax سالم داشت؛ این اصلاح برای tree deploy است، نه اصلاح سایت liveِ مشاهده‌شده.

## ۳. چرا canonical را خودکار درست نکردیم؟

فرمان موجود، بدون تغییر گیت:

```sh
python reference_data_sync_audit.py --base-ref 4b918261f3f7996439e6f9c98fe83f81f7df3c8d
# exit 1؛ سه PASS و سه FAIL، همان اختلاف‌های پیشین
```

| فایل | تفاوت deploy نسبت به main، بدون افزودن/حذف شناسهٔ رکورد |
|---|---|
| docs/data/micro_motives.json | شرح `description_fa` در **۲۹۴کارت** متفاوت است |
| majors_database_v2.json | **۴۲رشته** دارای strategy_weights و value_weights متفاوت؛ high_school_branch در **۲۷رشته** متفاوت است |
| school_branches_v2.json | **۴شاخه** دارای strategy_weights متفاوت؛ micro_motive_codes و source_majors_count هرکدام در **۳شاخه** متفاوت‌اند |

این اختلاف‌ها صرفاً formatting یا metadata نیستند. questions، trait_map زیر docs/data و value_poles برابرند. منشأ runtime همان deploy مصوب باقی ماند. راه‌حل مجاز در این نوبت نه کپی همهٔ داده‌ها به main بود، نه بازگرداندن runtime به main و نه skip/rebaseline گیت. تصمیم لازم برای ادامه: دامنه و provenance پذیرش هر اختلاف در انتقال محدودِ مستقل، با تأیید ناظر؛ این رسید چنین مجوزی ایجاد نمی‌کند.

### دو شکست قدیمیِ تست که دست‌نخورده ماندند

`test_phase3_city_paths` جداگانه روی baseline استخراج‌شده و نسخهٔ اصلاح‌شده اجرا شد؛ **هر دو یک FAIL و یک ERROR یکسان**:

- `test_prefix_decks_and_city_mapping`: regex در helper `path_codes` با `unbalanced parenthesis` خطا می‌دهد؛ قبل از ارزیابی داده رخ می‌دهد.
- `test_discover_includes_all_phase3_majors`: fixture تمام۱۵پاسخ V را `Q1A` می‌گذارد؛ با قرارداد۱۵پاسخ معتبرِ متفاوتِ سوال‌ها سازگار نیست و انتظار حضور همهٔ رشته‌ها شکست می‌خورد.

هیچ‌کدام با comma یا constraints ایجاد نشده‌اند. تست، انتظار یا فرمول برای سبزشدن عوض نشد. اصلاح خودِ تست تاریخی نیز باید در دامنهٔ مستقلِ حفظ قرارداد بررسی شود؛ فعلاً ادعای all-green نداریم.

## ۴. قفل نسخه بدون ارتقای پنهان

Commit: `17ff527`.

- requirements بازه‌های اصلی را حفظ و با `-c constraints.txt` مقید می‌کند.
- ۲۳نسخهٔ runtime مستقیم/گذرا از نصب تمیزِ مرحله۱ ثبت شد. خروجی pip freeze نصب اولیه، نصب constrained و نصب از artifact جدید برابر بود؛ **تغییر نسخه نسبت به این baseline تمیز: صفر**.
- artifact commit بالا در پوشه و venv دیگری از صفر نصب شد؛ `pip check`، مقایسهٔ نسخه‌ها و smoke PASS شدند.
- `test_runtime_constraints.py` pin دقیق/یکتا، پوشش نیازمندی‌های مستقیم و نسخهٔ نصب‌شدهٔ آن‌ها را بررسی می‌کند.
- `.gitignore` فقط از ثبت محیط محلی، bytecode و فایل‌های .env جلوگیری می‌کند؛ فایل موجودی حذف یا از Git خارج نشد.

این **version constraints** است، نه hash-lock تمام wheelها یا نتیجهٔ اسکن CVE. اعتبارسنجی محلی Linux/Python 3.11.2 انجام شد؛ Python 3.12 مرجع CI و سایر platformها جدا باید ارزیابی شوند. تنظیمات/نسخهٔ API یا prompt مشاوره دست‌نخورده است؛ pinهای httpx و سایر بسته‌ها همان نسخهٔ نصب اولیه‌اند، نه تغییر هدفمند AI.

### وضعیت تست مرورگر

Playwright و Chromium فقط خارج مخزن و برای آزمایش محلی نصب شدند؛ Chromium به خطای loader `libnspr4.so: cannot open shared object file` رسید. هیچ صفحه یا سفر کاربر آزمایش نشد و نتیجهٔ real-browser ناموفق به‌عنوان نقص برنامه تعبیر نمی‌شود. node_modules، binary، screenshot یا وابستگی frontend جدید وارد Git نشدند. تست کامل مرورگر/PWA/auth/پرداخت همچنان باقی است.

## ۵. نتایج نهایی محلی

| کنترل | نتیجه |
|---|---|
| unittest منتخب موتور/API/finite/fingerprint/null/بدنه/rate limit و ساخت/constraints | **۱۱۱ تست PASS** |
| parse تمام public JS | **۲۴script PASS**؛ baseline خراب به‌درستی رد شد |
| مصرف‌کنندهٔ null و Total | PASS؛ ۸مرز × ۴شکل، DOM-stub؛ نه browser E2E |
| tests/test_security_contracts.js | PASS |
| artifact مستقل + venv جدید + pip check + smoke | PASS؛ سرویس‌های خارجی آزمون نشدند |
| canonical | **FAIL تاریخی، سه اختلاف**؛ دست‌نخورده |
| test_phase3_city_paths، جدا از suite منتخب | **یک FAIL و یک ERROR، برابر baseline**؛ دست‌نخورده |
| real-browser | **مسدود محیط**؛ به PASS تبدیل نشده |
| Python 3.12 / GitHub CI برای این patch | نتیجه فقط از چک‌های طبیعی PR قابل احراز است؛ هیچ dispatch یا rerun دستی انجام نشد |

فرمان suite منتخب:

```sh
python -m unittest test_runtime_constraints test_backend_build_smoke \
  test_startup_engine_contract test_liara_startup_contract \
  test_engine_psychometrics test_v_range_norm test_v_consumer_contract \
  test_alternative_cache_equivalence test_main_api_contract \
  test_reference_finite_startup test_reference_fail_closed_startup \
  test_reference_fingerprint_contract test_reference_membership_fingerprint \
  test_genz_results_layer test_genz_visual_layer test_ai_rate_limit \
  test_request_body_limit_middleware -q
```

workflowها تغییر نکرده‌اند؛ دو فایل تست Python جدید و تست parse به‌طور محلی اجرا شدند، اما hook تازه به CI موجود اضافه نشده است. نباید فرض کرد همهٔ این تست‌های جدید خودکار در jobهای قدیمی اجرا می‌شوند. constraints به‌طور معمول همراه requirements در نصب‌های CI اعمال می‌شود.

## ۶. کنترل عدم تغییر و انتشار

با `git diff --exit-code 8ddd2aa -- dark_horse_engine_v2.py main_v2.py ai_counsel_service.py docs/app.js '*.json' .github` بررسی شد: **کد امتیاز، AI، app.js، تمام JSONهای مرجع و workflowها عین مبنا هستند.**

M شاخه k/N، S/EQUAL، V0=۰٫۰۲، کف شواهد، Total، rounding و گیت‌ها محفوظ‌اند. صف فرمول و موضوع e_b باز نشدند. هیچ migration، DB/پرداخت/AI request، تنظیم Liara، تغییر secret، انتشار main/Pages یا Merge مجاز/اجرا نشده است. تغییرات برای بازبینی روی همین شاخه‌اند؛ در صورت PR، Draft به deploy، بدون Merge تا مجوز مستقل.

**نتیجه:** ساخت و syntax و نسخهٔ dependency بهبود یافتند؛ canonical و تست‌های تاریخی همچنان صریحاً باز هستند و browser به محیط مناسب نیاز دارد. از این مرحله نمرهٔ بالای۸ یا آمادگی انتشار نتیجه گرفته نمی‌شود.
