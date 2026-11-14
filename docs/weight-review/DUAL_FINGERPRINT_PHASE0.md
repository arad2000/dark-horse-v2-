# فاز صفرِ به‌روزشده: قرارداد چهار دامنهٔ fingerprint و حفاظت داده

**نسخه:** 2.0-draft  
**تاریخ:** 2026-10-30  
**شاخهٔ هدف:** `deploy/liara-commercial-sandbox`  
**snapshot مبنای بررسی:** `a743ab8ddd335c49e579299f062778bd4f8e6e85`  
**وضعیت:** طراحی و ممیزی آفلاین؛ هیچ گیت چهاردامنه‌ای فعال نشده و هیچ expected/baseline تغییر نکرده است.

این نسخه جایگزین محتواییِ پیش‌نویس قدیمی #322 است، اما PR #322 را Merge یا حذف نمی‌کند. #322 بر مبنای `02f40f16e044219141a1d354d9d1aa30df416d87` قدیمی مانده؛ این نسخهٔ تازه روی snapshot فعلی deploy ساخته شده است.

---

## 1. مبانی حاکمیتی و تصمیم‌های قطعی

این طراحی تابع تصمیم‌های ناظر ثبت‌شده در [#326](https://github.com/arad2000/dark-horse-v2-/pull/326) و رجیستری پیشنهادی [#327](https://github.com/arad2000/dark-horse-v2-/pull/327) است. نقشهٔ call-siteها در [#328](https://github.com/arad2000/dark-horse-v2-/pull/328) و قرارداد mutation/validator در [#329](https://github.com/arad2000/dark-horse-v2-/pull/329) مکمل آن هستند؛ هر سه فعلاً Draft هستند.

تصمیم‌های صریح ثبت‌شده:

1. DH-013 کلان مرجع بالادستی است؛ مکمل وزن‌دهی و استاندارد نگارش در دامنهٔ تخصصی خود تابع آن هستند.
2. confidence کمتر از 0.7 به‌تنهایی باعث freeze خودکار نیست. میانگین وزنی همسایه‌ها نقش مکمل/تعدیل‌کننده دارد؛ شواهد همان رشته اصل است. فرمول عددی ترکیب هنوز باید نسخه‌دار و بازتولیدپذیر تصویب شود.
3. هر membership mismatch، حتی با scientific PASS، مستقل و مسدودکننده است. تنها استثنا Decision Record نسخه‌دار، شواهد آموزشی/داده‌ای، ثبت before/after، اثر مصرف‌کنندگان و تأیید صریح ناظر در PR جداگانه است.
4. چهار دامنه status مستقل دارند: A scientific/scoring، B membership/guidance، C evidence-content و D interpretation/presentation.
5. PASS یک دامنه هرگز FAIL دامنهٔ دیگر را خنثی نمی‌کند. ابهام مالکیت/consumer، PASS یا NOT_APPLICABLE نیست؛ تا تعیین تکلیف به‌صورت UNSCOPED/FAIL-CLOSED گزارش می‌شود.
6. هیچ یک از این تصمیم‌ها به‌خودی‌خود مجوز تغییر JSON، وزن، موتور، expected، workflow، environment، DB، Liara یا cutover نیست.

## 2. Snapshot و وضعیت واقعی کد فعلی

### 2.1 فایل‌های مرجع در snapshot

| فایل | Blob SHA در `a743ab8...` |
|---|---|
| `majors_database_v2.json` | `abce609d8a8683f0168d251718e3f743b03dd2b7` |
| `micro_motives.json` (root) | `c59ab2a5d82283d2c4a5f503c42190e1740af780` |
| `docs/data/micro_motives.json` | `c59ab2a5d82283d2c4a5f503c42190e1740af780` |
| `school_branches_v2.json` | `abb7b08a6686a570f997a872fd13b3b0683a67a8` |
| `docs/data/questions_v2.json` | `17f0d764538657e1f8b4b5efe2dad8a6bf368bb3` |
| `trait_map_v3.json` | `466280fe517b7e6ba68e54dbe8535de7444c7f4a` |
| `value_poles_v2.json` | `251d435d57b90e325ff671a4f8c69c530de61494` |

دو مسیر `micro_motives.json` در این snapshot byte-identical هستند؛ موتور مسیر root را به‌طور پیش‌فرض مصرف می‌کند و فرانت‌اند مسیر `docs/data` را. این برابری باید در هر snapshot داده با assertion مستقل حفظ شود.

### 2.2 دو projection واقعاً موجود در deploy

ماژول فعلی `reference_fingerprints.py` در blob `bffdf430f6602e2c498eff3bead1192830541045` دو projection می‌سازد. این پیاده‌سازی «چهار دامنه» را کامل نمی‌کند.

**A — scoring projection فعلی:**
- رشته: `id`، `motive_driven`، `weights_version`، `micro_motive_codes`، `strategy_weights`، `value_weights`.
- شاخه: `id`، `name`، `micro_motive_codes`، `m_score_denom_limit`، `strategy_weights`، `value_weights`، `weights_version`.
- کاتالوگ micro-motive: مجموعهٔ مرتب `code`ها؛ **`description_fa`، `category` و `intensity_level` در hash فعلی نیستند.**
- سؤال‌ها: فقط `questions_v2.layers.strategies.questions` با id/number/question و index/text گزینه‌ها؛ **۱۵ سؤال ارزشی در این projection نیستند.**

**B — membership projection فعلی:**
- رشته: `id`، `name`، `high_school_branch`، `group`، `cluster`، `subgroup`، `exam_group`.
- شاخه: `id`، `name`، `group`.

بنابراین projection فعلی B بعضی labelها/metadataهای نمایشی را نیز در خود دارد، درحالی‌که field map نشان می‌دهد برخی از آن‌ها ممکن است D یا هنوز OPEN باشند. حذف یا انتقال این فیلدها از projection فعلی فقط با نسخه‌گذاری، field map نهایی، تست mutation و PR مجاز است؛ این سند آن را انجام نمی‌دهد.

### 2.3 baselineهای موجود و تعارض نسخه

در `reference_fingerprints.py`:
- `FINGERPRINT_BASE_COMMIT = 02f40f16e044219141a1d354d9d1aa30df416d87`.
- expectedهای علمی و عضویت برای rangeهای 194، 204 و 215 تعریف شده‌اند.
- این baselineها پوشش اثبات‌شدهٔ واحدی برای تمام 230 رشته نیستند.
- snapshot ممیزی جاری `a743ab8...` است؛ تفاوت base باید forensic توضیح داده شود. تولید expected تازه، تغییر range یا refresh baseline تا ارائهٔ provenance و مجوز جداگانه ممنوع است.

گیت تاریخی و نرمال‌سازی staging نیز نباید کورکورانه روی همهٔ رشته‌های فعال اعمال شوند؛ در غیر این صورت دادهٔ واقعی `motive_driven=true` می‌تواند از fingerprint علمی حذف شود.

## 3. قرارداد چهار دامنه

### A — Scientific / Scoring

**شامل:**
- پروفایل فعال رشته‌ها و شاخه‌ها: ماتریس S، وزن‌های V، کدهای مؤثر M، eligibility و مخرج M شاخه.
- mapping موقعیتی سؤال/گزینهٔ راهبردی به ستون/ردیف وزن.
- کدهای micro-motive که در محاسبهٔ M و referential integrity اثر واقعی دارند.
- شناسهٔ پایدار لازم برای اتصال درست پروفایل به رشته/شاخه.
- `weights_version` در projection فعلی به‌عنوان metadata نسخهٔ پروفایل ثبت می‌شود؛ این فیلد به‌تنهایی وزن عددی نیست و باید جداگانه در diff توضیح داده شود.

**گیت‌ها:** schema، finite، محدودهٔ [0,1]، شکل 25×5، کلیدهای کامل V، جمع ردیف طبق tolerance مصوب، refs، eligible rows و branch matrices. Pearson صرفاً تشخیصی است. برخورد signature باید از validator ساختاری/سیاست مستقل تعیین تکلیف شود؛ نباید با تمایزسازی مصنوعی وزن‌ها رفع شود.

### B — Membership / Guidance

**شامل:**
- رابطهٔ پایدار `major_id → high_school_branch`.
- `exam_group` که در `admission_sanjesh_engine.py::_major_target_group` برای تعیین گروه هدف سنجش/پذیرش استفاده می‌شود.
- نام/شناسهٔ شاخه در حدی که موتور فعلی آن را به‌عنوان کلید lookup مصرف می‌کند؛ تا مهاجرت امن به شناسهٔ پایدار، rename شاخه نباید فقط D تلقی شود.
- سایر فیلدها فقط پس از اثبات call-site/owner در field map.

**سیاست blocking مصوب:** هر B mismatch، حتی با A PASS، status مستقل FAIL می‌دهد. Exception فقط با Decision Record نسخه‌دار شامل id، before/after، منبع، rationale آموزشی/داده‌ای، consumer impact، review evidence و تأیید صریح ناظر؛ در PR مستقل و با baseline کنترل‌شده.

**مرز:** `source_majors_count` در model/seed و dual-run materialization دیده می‌شود، اما در فرمول یا مسیر recommendation موتور مصرف مستقیم آن احراز نشده؛ فعلاً metadata شمارش/provenance است و نباید بدون قرارداد مشتق‌سازی به score input تبدیل شود. `high_school_branch` در model/seed/fingerprint/parity حضور دارد، اما consumer مستقیم runtime آن هنوز OPEN است؛ این عدم قطعیت سیاست blocking را لغو نمی‌کند.

### C — Evidence Content

**شامل:**
- `micro_motives[].code → description_fa`.
- version/status متن، تاریخچهٔ تغییر، نویسنده/منبع، دو review مستقل و رابطهٔ متن با رشته‌های مالک آن.
- category/intensity فقط پس از اثبات consumer و مالکیت.

**سیاست تغییر:** تغییر `description_fa` حتی با ثابت‌ماندن کد و وزن، C را FAIL/REVIEW می‌کند. فهرست رشته‌ها و شاخه‌های متأثر باید از mapping کدها تولید شود تا وزن‌های متکی به متن برای impact review علامت بخورند. این رویداد به‌خودی‌خود تغییر عددی وزن نیست؛ اگر review به تغییر وزن منجر شد، A نیز جداگانه تغییر می‌کند.

**بازبینی:** #285 مکمل محتوایی DH-013 است؛ PR آن فعلاً Draft و بدون review ثبت‌شده است. استاندارد نگارش تا دو بازبینی مستقل واقعی و تثبیت commit، نسخهٔ نهایی مصوب نیست. فرم Reviewer A/B یا بستهٔ auto-generated review جای امضای واقعی را نمی‌گیرد.

### D — Interpretation / Presentation

**شامل:**
- `trait_map_v3.json` و برچسب‌های صفت.
- `value_poles_v2.json` و prompt/label سؤال‌ها و گزینه‌های ارزشی.
- `archetype`، `fulfillment_source`، `prestige_level` و labelهای major/branch پس از جداسازی identity.
- `group` و سایر متون توضیحی فقط بعد از تکمیل consumer map.

**دو اثر مهم:**
- `archetype/fulfillment_source` در engine به نتیجه منتقل می‌شوند و علاوه بر UI، در `ai_counsel_service.py::_arch_bits` برای narrative مشاوره مصرف می‌شوند؛ در `operational_store.py` هم ذخیره می‌شوند. این‌ها D هستند، نه score input.
- `trait_map` و `value_poles` بر تفسیر/هایلایت/نمایش اثر می‌گذارند؛ raw M/S/V را فقط با تغییر label عوض نمی‌کنند.

متن strategy questions/optionها اثر دوگانه دارد: در D نمایش داده می‌شود و چون پاسخ S موقعیتی است، تغییر ترتیب/index/معنای اتصال به weight باید A را نیز تغییر دهد. سؤال‌های ارزشی در UI بارگذاری می‌شوند و codeهای QnA/QnB را به payload می‌فرستند؛ متن آن‌ها در D است، ولی تغییر code/order که جواب را به وزن دیگری متصل کند باید A را نیز تغییر دهد.

## 4. قرارداد خروجی و تفکیک failure

برای هر snapshot، هر دامنه status مستقل دارد:

| Domain | وضعیت‌های مجاز | شرط |
|---|---|---|
| A | PASS / FAIL / UNSCOPED | UNSCOPED یا FAIL مانع پذیرش تغییر علمی است. |
| B | PASS / FAIL / UNSCOPED | هر FAIL طبق تصمیم ناظر blocking است؛ UNSCOPED نیز fail-closed است. |
| C | PASS / FAIL / UNSCOPED | تغییر متن بدون review/provenance کامل تا بسته‌شدن review، FAIL/REVIEW است. |
| D | PASS / FAIL / UNSCOPED | تغییر محتوای تفسیری/نمایشی باید review متناسب و consumer mapping داشته باشد. |

`NOT_APPLICABLE` فقط وقتی مجاز است که diff هیچ فیلد متعلق به آن دامنه را تغییر نداده و field map پوشش آن فیلدها را ثابت کرده باشد. نبود projection یا consumer ناشناخته هرگز NOT_APPLICABLE نیست.

گزارش باید شامل diff فیلدبه‌فیلد، commit/blob input، schema version، نسخهٔ validator، command، exit code، report artifact و exception record باشد. فقط چاپ digest کافی نیست.

## 5. Mutation matrix پیشنهادی

تست‌ها روی fixture مستقل و کپی در حافظه اجرا شوند؛ JSON اصلی/production تغییر نکند.

| mutation منفرد | انتظار دامنه‌ای |
|---|---|
| تغییر یک وزن S/V رشته یا شاخه | A تغییر کند؛ B/C/D ثابت بمانند. |
| تغییر فقط `high_school_branch` یا `exam_group` | B FAIL شود، حتی اگر A PASS است؛ سایر دامنه‌ها ثابت بمانند. |
| تغییر عضویت رشته و به تبع آن pool کد/وزن شاخه | B و A هر دو تغییر خود را گزارش کنند؛ isolation ساختگی ممنوع. |
| تغییر فقط `description_fa` با code ثابت | C FAIL/REVIEW و impact list تولید شود؛ A numeric فقط در صورت تغییر score inputs عوض شود. |
| تغییر فقط `trait_map` یا label `value_poles` | D تغییر کند؛ raw score A ثابت بماند. |
| تغییر value prompt/option متن با code ثابت | D تغییر کند؛ اگر code/order mapping عوض شد، A نیز تغییر کند. |
| تغییر `archetype/fulfillment_source/prestige_level` | D تغییر کند؛ A/B/C ثابت بمانند. |
| تغییر فقط `major.name` با id ثابت | D تغییر کند؛ identity و رابطهٔ عضویت ثابت بماند؛ اگر lookup فعلی با name وابسته است، migration/lookup contract نیز باید FAIL را نشان دهد. |
| تغییر `group/cluster/subgroup/source_majors_count/handcrafted` | تا field owner/consumer به‌طور نهایی تثبیت نشده، test باید UNSCOPED بدهد؛ نباید domain دلخواه ساخته شود. |

برای هر تست، mutation تک‌فیلدی و آزمون عدم تغییر سه دامنهٔ دیگر لازم است. سناریوهای دارای اثر دوگانه باید صریحاً چند دامنه را fail کنند.

## 6. وضعیت تست‌ها و coverage gap فعلی

در snapshot deploy:
- `test_reference_fingerprint_contract.py` چند mutation را پوشش می‌دهد: high_school_branch membership-only، تغییر وزن strategy، group/cluster/subgroup در membership، weights_version و رد non-finite.
- این تست‌ها هنوز mutation متن `description_fa`، ۱۵ سؤال ارزش، labelهای `trait_map/value_poles`، فیلدهای presentation، `source_majors_count` و ماتریس وزن شاخه را به‌صورت کامل اثبات نمی‌کنند.
- `test_reference_membership_fingerprint.py` expectedهای فعلی membership را کنترل می‌کند؛ تصمیم blocking GOV-05 هنوز به workflow اجرایی منتقل نشده است.
- در module، expectedهای فعلی برای endpointهای 194/204/215 هستند و base commit آن از snapshot ممیزی قدیمی‌تر است. baseline جدید ساخته نشده است.

## 7. Validatorها و محدودیت‌های فعلی

نسخه‌های #307 در main:
- `validate_integrity.py`: blob `eec5ea7799640bf4fff85ab76559dbfbb8d08bd9`.
- `global_separation_test.py`: blob `485e2f4a7f90a223a433919e12f94c720a89f857`.

محدودیت‌های شناخته‌شده:
1. نسخهٔ موجود `validate_integrity.py` برای ماتریس S کنترل صریح finite ندارد؛ در مقایسه‌های مبتنی بر جمع/بازه، NaN می‌تواند از شرط‌های مقایسه عبور کند. قبل از اتکا به آن به‌عنوان gate نهایی، تست منفی NaN، Infinity و overflow و اصلاح نسخه‌دار لازم است.
2. `global_separation_test.py` report-only است؛ Pearson thresholds به‌تنهایی gate رد نیستند و برخورد signature را به‌تنهایی به exit غیرصفر تبدیل نمی‌کند.
3. اسکریپت global separation در نسخهٔ بررسی‌شده شرط `motive_driven=true` را صریحاً به‌عنوان فیلتر ورود enforce نمی‌کند؛ خروجی باید همراه تعداد ردیف‌های داخل/خارج و موفقیت validator ساختاری تفسیر شود.
4. دو validator #307 در main هستند، نه در snapshot deploy. اجرای آن‌ها در CI deploy نباید ادعا شود تا PR مستقل برای انتقال/اتصال مصوب شود.
5. موتور deploy در loader اصلی finite را برای JSONهای mapشده کنترل می‌کند؛ تست finite startup موجود deploy نباید حذف یا تضعیف شود. PASS موتور یا validator فعلی جای پوشش ناقص #307 را نمی‌گیرد.

ترتیب پیشنهادی پس از مجوز اجرایی: strict JSON/finite → validator ساختاری اصلاح‌شده → projection/statusهای چهار دامنه → global separation report برای تغییرات major → evidence review انسانی و دو review متن.

## 8. main/deploy و guardهای shared

- `questions_v2.json`، `trait_map_v3.json` و `value_poles_v2.json` در قرارداد فعلی ورودی‌های shared هستند و byte-sync guard موجود آن‌ها را با main مقایسه می‌کند.
- `majors_database_v2.json`، `micro_motives.json` و `school_branches_v2.json` داده‌های runtime-owned هستند؛ byte mismatch با main به‌تنهایی اثبات خطای علمی یا مجوز sync نیست.
- Hybrid Migration Audit فعلی هنوز سه فایل runtime-owned را با main byte-identical می‌خواهد و روی snapshot حاضر به‌علت mismatch قدیمی FAIL می‌شود. این failure باید با تغییر policy/guard در PR مستقل و پس از تصمیم رسمی حل شود؛ نه با کپی داده یا تغییر expected.
- #321 در شکل فعلی پایهٔ اجرایی مناسبی نیست: base قدیمی، عدم پوشش صریح مسیر root `micro_motives.json` و تغییر workflow Hybrid دارد. بازطراحی آن باید اتمیک و روی base جاری باشد؛ هیچ تغییر Hybrid/cutover با این Phase 0 مجاز نیست.

## 9. خط قرمزها و مرحلهٔ بعد

- این PR فقط سند طراحی را اضافه می‌کند؛ هیچ ماژول hash، validator، test، workflow، expected یا baseline تغییر نمی‌کند.
- هیچ JSON، وزن S/V، formula Total یا engine تغییر نمی‌کند.
- هیچ PR از Draft خارج یا Merge نمی‌شود.
- هیچ rerun دستی workflow انجام نمی‌شود.
- پس از review مستنداتی، field map #328 و mutation contract #329 باید با این سند تطبیق داده شوند؛ سپس در صورت مجوز مستقل، PRهای اجرایی اتمیک برای اصلاح validator finite و چهار دامنه ساخته شوند.
- PR قدیمی #322 به‌دلیل base قدیمی superseded است و تا تصمیم ناظر بسته/merge نمی‌شود.

