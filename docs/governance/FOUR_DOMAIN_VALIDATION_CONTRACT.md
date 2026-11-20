# قرارداد اعتبارسنجی و آزمون تغییرات چهار دامنه — Dark Horse V2

**نسخه:** 1.0-draft  
**تاریخ:** 2026-10-30  
**Base:** `deploy/liara-commercial-sandbox` در `a743ab8ddd335c49e579299f062778bd4f8e6e85`  
**وضعیت:** طرح مستنداتی؛ هیچ validator، تست، fingerprint یا CI gate را پیاده‌سازی/فعال نمی‌کند.

---

## 1. هدف و اصل خروجی

این قرارداد، روش سنجش تغییرات در چهار دامنهٔ تأییدشده را تعریف می‌کند:

- A — Scientific / Scoring
- B — Membership / Guidance
- C — Evidence Content
- D — Interpretation / Presentation

هر دامنه باید status مستقل `PASS`، `FAIL` یا `NOT_APPLICABLE` داشته باشد. `NOT_APPLICABLE` فقط وقتی مجاز است که diff هیچ فیلد متعلق به آن دامنه را تغییر نداده و field map نیز آن فیلدها را پوشش داده باشد. نبود projection، نبود validator یا ابهام field ownership نباید به PASS یا NOT_APPLICABLE تبدیل شود؛ وضعیت آن `UNSCOPED/FAIL-CLOSED` است.

**Integrity نهایی فقط وقتی PASS است که همهٔ دامنه‌های لازم PASS باشند یا استثنای صریح و نسخه‌دارِ همان دامنه پذیرفته شده باشد.** موفقیت یک دامنه، شکست دامنهٔ دیگر را جبران نمی‌کند.

## 2. پیش‌شرط ثابت برای هر اجرا

هر گزارش اعتبارسنجی باید به یک snapshot واحد و بازتولیدپذیر متصل باشد و این موارد را ثبت کند:

1. commit شاخه و PR head؛
2. blob SHA تمام JSONهای ورودی و مسیر دقیق آن‌ها؛
3. commit/blob نسخهٔ validator و schema projection؛
4. command line، محیط/نسخهٔ Python، خروجی کامل و exit code؛
5. لینک workflow run یا گزارش اجرای آفلاین؛
6. evidence packet، change record و امضاهای لازم.

مخلوط‌کردن validator از main با دادهٔ deploy بدون ثبت صریح دو commit و علت این جداسازی ممنوع است. در snapshot فعلی دو ابزار #307 در main هستند و در deploy حضور ندارند؛ اجرای آن‌ها در CI deploy تا زمان PR اجرایی مستقل و تأییدشده نباید ادعا شود.

## 3. قرارداد دامنه A — Scientific / Scoring

### 3.1 ورودی‌های کنترل

با field map فعلی:
- پروفایل فعال رشته: `motive_driven`، `micro_motive_codes`، `strategy_weights`، `value_weights` و شناسهٔ ثابت؛
- پروفایل شاخه: `micro_motive_codes`، `m_score_denom_limit`، `strategy_weights`، `value_weights` و کلید lookup شاخه؛
- ترتیب/شناسه/گزینه‌های strategy questions که پاسخ موقعیتی را به ردیف و ستون S متصل می‌کنند؛
- هر mapping دیگری که call-site واقعی ثابت کند بر M/S/V، eligibility یا فاصلهٔ پروفایل اثر دارد؛
- `weights_version` به‌عنوان metadata نسخهٔ پروفایل در projection فعلی ثبت می‌شود؛ این فیلد به‌خودی‌خود ضریب عددی نیست.

### 3.2 آزمون‌های لازم

- schema: S دقیقاً 25×5، عددی و finite؛ تمام مقادیر در [0,1]؛ جمع ردیف طبق tolerance مصوب.
- V دقیقاً 30 کلید Q1A..Q15B، مقدار finite و در محدودهٔ مصوب؛ قرارداد V باید با فرمول واقعی engine منطبق باشد، نه فرض نرمال‌سازی ردیفی.
- active profile: ردیف `motive_driven=true` باید پروفایل کامل و سازگار داشته باشد؛ catalog-only فقط طبق قرارداد صریح خودش گزارش شود.
- references: همهٔ کدهای فعال رشته و شاخه resolve شوند؛ کلیدهای وزن و سؤال‌ها کامل و هم‌معنا باشند.
- branch scoring: ماتریس‌ها و مخرج M شاخه نیز همانند رشته‌ها fail-closed اعتبارسنجی شوند.
- signature و Pearson: برخورد signature گزارش و طبق policy پروژه تعیین تکلیف شود؛ Pearson صرفاً تشخیصی است و thresholds آن هدف قطعی یا مجوز تمایز مصنوعی نیستند.

### 3.3 Mutation tests

| تغییر در fixture | انتظار |
|---|---|
| تغییر یک وزن S یا V رشته | A باید تغییر کند؛ B/C/D ثابت بمانند. |
| تغییر یک وزن S یا V شاخه | A باید تغییر کند؛ B/C/D ثابت بمانند. |
| تغییر `motive_driven` برای یک رشته | A باید تغییر کند و eligibility diff خوانا ثبت شود؛ صرفاً metadata تلقی نشود. |
| تغییر کد فعال رشته یا شاخه | A و ref-integrity باید اثر را نشان دهند؛ کد orphan/تکراری یا pool ناقص FAIL است. |
| جابه‌جایی S question/option index یا تغییر نگاشت index-to-weight | A باید تغییر کند؛ گزارش معنایی D نیز در صورت تغییر متن/نمایش لازم است. |
| تغییر فقط `weights_version` | بر اساس projection فعلی A تغییر می‌کند، اما گزارش باید روشن کند این تغییر version metadata است و نه تغییر مقدار عددی وزن. |

## 4. قرارداد دامنه B — Membership / Guidance

### 4.1 ورودی‌های کنترل

- رابطهٔ شناسهٔ رشته به `high_school_branch`؛
- `exam_group` که در تعیین گروه هدف admission از آن استفاده می‌شود؛
- شناسه و کلید شاخه، همراه با منبع و نام شاخه؛
- سایر فیلدهای طبقه‌بندی فقط پس از اثبات call-site و owner در field map.

### 4.2 حکم blocking مصوب

هر membership mismatch، حتی با Scientific PASS، باید status مستقل `FAIL` بدهد و مانع پذیرش شود.

استثنا فقط با Decision Record نسخه‌دار شامل شناسه‌ها، مقدار قبل/بعد، source، rationale آموزشی/داده‌ای، مصرف‌کنندگان متاثر، شواهد بازبینی و تأیید صریح ناظر مجاز است. استثنا در PR جداگانه و با baseline کنترل‌شده انجام می‌شود؛ تغییر expected در همان PR برای رفع قرمزی CI مجاز نیست.

### 4.3 Mutation tests

| تغییر در fixture | انتظار |
|---|---|
| تغییر فقط `high_school_branch` یک رشته | B باید FAIL شود؛ A/C/D ثابت بمانند. |
| تغییر فقط `exam_group` | B باید FAIL شود؛ A/C/D ثابت بمانند، مگر field map جدید اثر scoring را با call-site ثابت کند. |
| تغییر عضویت یک رشته بین دو شاخه | B باید تغییر کند. اگر هم‌زمان pool کدهای شاخه یا وزن شاخه نیز عوض شود، A نیز باید مستقل تغییر خود را گزارش کند؛ نباید انتظار false isolation داشت. |
| تغییر نام شاخه درحالی‌که engine هنوز با name lookup می‌کند | حداقل B و قرارداد lookup باید FAIL شوند؛ تا migration کلید پایدار، rename قابل قبول نیست. |
| تغییر بدون Decision Record | B مستقل و blocking FAIL باشد، حتی اگر A PASS است. |
| تغییر با Decision Record معتبر | تست استثنا باید رکورد نسخه‌دار، approval ناظر و تطبیق before/after را مطالبه کند؛ مجازشدن استثنا به‌معنای حذف گزارش mismatch نیست. |

## 5. قرارداد دامنه C — Evidence Content

### 5.1 ورودی‌های کنترل

- `micro_motives[].code → description_fa`؛
- وضعیت/نسخهٔ متن، دلیل نگارش/اصلاح، دو بازبین مستقل و provenance؛
- در صورت استفادهٔ واقعی، `category` و `intensity_level` پس از اثبات consumer.

دو مسیر فایل `micro_motives.json` ریشه و `docs/data/micro_motives.json` باید در همان commit برابر باشند یا اختلاف projection با دلیل و consumer ثبت شود. موتور مسیر root را به‌طور پیش‌فرض می‌خواند و UI مسیر docs/data را.

### 5.2 سیاست تغییر متن

تغییر `description_fa` حتی با ثابت‌بودن کد و وزن، تغییر شاهد مبنای علمی محسوب می‌شود و باید C را FAIL/REVIEW کند تا متن بازبینی و تصویب شود. از روی کدهای ارجاعی باید فهرست رشته‌ها و شاخه‌هایی که از آن شاهد استفاده می‌کنند تولید شود؛ وزن‌های متکی به آن‌ها برای بازبینی impact علامت‌گذاری شوند.

C-FAIL به‌تنهایی ادعا نمی‌کند مقدار عددی S/V تغییر کرده؛ اگر بازبینی متن به تغییر وزن منجر شد، آن تغییر باید جداگانه در A نیز دیده شود.

### 5.3 Mutation tests

| تغییر در fixture | انتظار |
|---|---|
| تغییر فقط `description_fa` با کد ثابت | C تغییر/FAIL شود؛ A numeric، B و D مستقل ثابت بمانند؛ impact list وابستگی‌ها تولید شود. |
| حذف یا تکرار `code` | C و A reference integrity هر دو FAIL شوند. |
| تغییر فقط ترتیب ردیف‌های JSON بدون تغییر mapping معنایی | canonicalization باید تغییر غیرمعنایی را نادیده بگیرد، مگر ترتیب واقعاً قرارداد مصرف‌کننده باشد. |
| تفاوت root و docs/data motive files | C fail-closed شود یا equality assertion fail کند. |

## 6. قرارداد دامنه D — Interpretation / Presentation

### 6.1 ورودی‌های کنترل

- `trait_map_v3.json` و برچسب‌های صفت؛
- `value_poles_v2.json` و برچسب‌های Q1A..Q15B؛
- prompt و متن گزینه‌های value questions؛
- متون خروجی major مثل `archetype`، `fulfillment_source`، `prestige_level`، و labelهای `name/group` پس از تفکیک identity؛
- labelهای branch که consumer آن‌ها احراز شده باشد.

متن strategy questions/option labels اثر دوگانه دارد: نمایش در D و اتصال معنایی index-to-weight در A. value question متن/label نیز D است؛ تغییر code/order که جواب کاربر را به وزن دیگری متصل کند A را هم تغییر می‌دهد.

### 6.2 Mutation tests

| تغییر در fixture | انتظار |
|---|---|
| تغییر فقط label در `trait_map` | D تغییر کند؛ numeric A ثابت بماند. |
| تغییر فقط label در `value_poles` | D تغییر کند؛ raw V در A ثابت بماند. |
| تغییر `archetype/fulfillment_source/prestige_level` | D تغییر کند؛ A/B/C ثابت بمانند. |
| تغییر فقط `major.name` با id ثابت | D تغییر کند؛ A و رابطهٔ membership ثابت بمانند. |
| تغییر branch.name با lookup مبتنی بر name | تا stable-id migration، D تنها اثر نیست؛ قرارداد lookup/membership نیز باید FAIL شود. |
| تغییر متن strategy/value question | D تغییر کند؛ اگر semantic mapping index/code تغییر کند، A نیز باید تغییر کند. |

### 6.3 مصرف downstream و فیلدهای provenance

- `archetype`، `dominant_values`، `dominant_traits` و `fulfillment_source` علاوه بر UI در `ai_counsel_service.py::_arch_bits` برای تولید narrative مشاوره مصرف می‌شوند و در `operational_store.py` در snapshot نتیجه ذخیره می‌شوند. این موارد در D هستند؛ ذخیره‌شدن/مصرف مشاوره، آن‌ها را به score input تبدیل نمی‌کند.
- `dual_run_audit.py` فیلدهای ORM را برای بازسازی موتور از PostgreSQL materialize می‌کند؛ این مسیر parity/migration comparison است و به‌تنهایی consumer الگوریتمی همهٔ فیلدهای materialized نیست.
- `handcrafted` وضعیت provenance/ساخت دستی است که در seed validation و staging parity کنترل می‌شود؛ تا وقتی call-site scoring ثابت نشده، وارد A نمی‌شود.
- `source_majors_count` در seed/ORM و dual-run materialization حضور دارد، اما در فرمول یا مسیر recommendation engine مصرف مستقیم آن احراز نشده است. نقش فعلی، metadata شمارش/سازگاری شاخه است؛ دامنهٔ نهایی آن در B فقط بعد از تعیین دقیق مبنای شمارش تثبیت می‌شود.
- `high_school_branch` در مدل و seed ذخیره و در membership projection ثبت شده است، اما consumer مستقیم آن در call-siteهای runtime بررسی‌شده هنوز احراز نشده. سیاست GOV-05 همچنان تغییرش را blocking می‌داند؛ عدم قطعیت دربارهٔ consumer نباید به PASS یا حذف گیت منجر شود.

## 7. محدودیت validatorهای شناخته‌شده

نسخه‌های مرجع #307 در main:
- `validate_integrity.py` blob `eec5ea7799640bf4fff85ab76559dbfbb8d08bd9`
- `global_separation_test.py` blob `485e2f4a7f90a223a433919e12f94c720a89f857`

**پیش از اتکا به نسخهٔ فعلی validate_integrity.py به‌عنوان gate نهایی، نقص finite در ماتریس S باید رفع شود.** در کد فعلی، کنترل S از روی جمع ردیف و بازه است؛ برای NaN، مقایسه‌های `abs(sum(row)-1) > tolerance` و `v < 0 or v > 1` می‌توانند False برگردند و NaN از آن کنترل‌ها عبور کند. تست منفی NaN، Infinity و exponent overflow باید اضافه شود.

محدودیت‌های نسخهٔ فعلی `global_separation_test.py`:
- ابزار signature collision را گزارش می‌کند، ولی collision را به‌تنهایی به exit غیرصفر تبدیل نمی‌کند.
- eligibility را صریحاً به `motive_driven=true` محدود نمی‌کند؛ هر ردیف با S کامل می‌تواند وارد تحلیل شود.
- در value-only، کلیدهای V غایب را با صفر پر می‌کند؛ بنابراین باید پس از validator ساختاری موفق اجرا شود.
- Pearson thresholds صرفاً تشخیصی‌اند؛ نباید gate علمی یا هدف تنظیم وزن تلقی شوند.

ترتیب پیشنهادی: strict JSON/finite startup → validator ساختاری اصلاح‌شده → fingerprintهای چهار دامنه → global separation report برای تغییرات major → evidence review انسانی. تا رفع نقص‌ها، تست finite موجود deploy باید حفظ شود و هیچ PASS محدود به یک ابزار به PASS کل تبدیل نشود.

## 8. تجمیع نتیجه و exception flow

گزارش نهایی باید ماتریسی شبیه این داشته باشد:

| Domain | Status | Changed paths/fields | Evidence/consumer | Exception record |
|---|---|---|---|---|
| A | PASS/FAIL/UNSCOPED | ... | ... | ... |
| B | PASS/FAIL/UNSCOPED | ... | ... | ... |
| C | PASS/FAIL/UNSCOPED | ... | ... | ... |
| D | PASS/FAIL/UNSCOPED | ... | ... | ... |

قواعد:
- `UNSCOPED` در دامنهٔ متاثر معادل عدم احراز و blocking است.
- هر membership FAIL طبق GOV-05 blocking است؛ scientific PASS نمی‌تواند آن را نادیده بگیرد.
- evidence-content FAIL تا دو بازبینی مستقل و تثبیت متن بسته نمی‌شود.
- Pearson گزارش‌محور است؛ collision signature و نقص‌های ساختاری باید مطابق گیت‌های اختصاصی بررسی شوند.
- confidence زیر 0.7: neighbor average مکمل شواهد محلی است؛ formula عددی آن تا تصویب نسخه‌دار تعیین نمی‌شود و به validatorها تحمیل نمی‌شود.

## 9. خط قرمزها

- این سند فقط قرارداد پیشنهادی است؛ هیچ کد validator، تست، fingerprint، expected، baseline یا workflow را تغییر نمی‌دهد.
- هیچ JSON یا وزن S/V تغییر نمی‌کند.
- هیچ PR از Draft خارج یا Merge نمی‌شود.
- اجرای دستی workflow یا rerun انجام نمی‌شود.
- هر پیاده‌سازی باید PR اتمیک مستقل با testهای مثبت/منفی و permission جداگانه داشته باشد.

