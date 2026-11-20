# فاز صفر: قرارداد دو fingerprint مستقل (فقط ممیزی و طراحی)

**وضعیت:** سند طراحی آفلاین؛ هیچ گیت دوگیتی فعال نشده و هیچ expected جدیدی تثبیت نشده است.  
**Snapshot مبنا:** شاخهٔ `deploy/liara-commercial-sandbox` در commit `02f40f16e044219141a1d354d9d1aa30df416d87` (Merge مربوط به #320).  
**سیاست مرجع:** [HIGH_SCHOOL_BRANCH_FINGERPRINT_POLICY.md در PR #321](https://github.com/arad2000/dark-horse-v2-/blob/53631a35fff4bc00299858a41073a0694a782f1b/docs/weight-review/HIGH_SCHOOL_BRANCH_FINGERPRINT_POLICY.md)، گزینهٔ «ج: دو fingerprint مستقل». #321 همچنان Draft و مسدود است.

## A) ورودی‌ها از روی کد واقعی

جدول‌های زیر **پیشنهاد projection برای بازبینی ناظر** هستند، نه قرارداد فعال. «علمی» در این سند یعنی ورودی‌ای که روی امتیاز عددی، واجدشرایط‌بودن برای امتیازدهی، محاسبهٔ مؤلفه‌ها یا تطبیق پروفایلِ تولیدشده توسط موتور اثر دارد. هر ورودی‌ای که فقط در توضیح، معنای سؤال یا دسته‌بندی اثر دارد و مرزش با خروجی/عضویت قطعی نیست، در جدول مبهم آمده است.

### جدول ۱ — ورودی‌های fingerprint علمی پیشنهادی

| مسیر/فیلد | دلیل اثر بر امتیاز یا تطبیق علمی | منبع کد |
|---|---|---|
| `majors_database_v2.json#/id` | شناسهٔ ردیف لازم است تا پروفایل وزن‌ها به رشتهٔ درست متصل بماند؛ تغییر شناسه، پیوند امتیاز به رشته را عوض می‌کند. | [بارگذاری کلیدها و رشته‌ها، موتور](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L30-L55) |
| `majors_database_v2.json#/motive_driven` | موتور رشته‌های فعال را با این پرچم تشخیص می‌دهد و رشته‌های غیرموتیو‌محور را از discovery فردی کنار می‌گذارد؛ تغییر آن می‌تواند واجدشرایط‌بودن را تغییر دهد. | [فیلتر فعال‌ها](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L47-L54)، [فیلتر در تحلیل](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L765-L780) |
| `majors_database_v2.json#/micro_motive_codes` | مجموعهٔ کدهای رشته، صورت و مخرج M-Score و شرط حداقلی هم‌پوشانی را شکل می‌دهد. | [محاسبهٔ M-Score رشته](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L245-L285) |
| `majors_database_v2.json#/strategy_weights` | ماتریس ۲۵×۵ در S-Score و بردار پروفایل/فاصله‌های جایگزین استفاده می‌شود؛ ترتیب ردیف و گزینه معنایی است. | [اعتبارسنجی ماتریس](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L205-L238)، [S-Score](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L324-L355) |
| `majors_database_v2.json#/value_weights` | وزن‌های قطب‌های ارزش در V-Score، برجسته‌سازی‌ها و فاصلهٔ پروفایل استفاده می‌شوند. | [محاسبهٔ V-Score](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L372-L432)، [Total و مصرف وزن‌ها](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L776-L810) |
| `school_branches_v2.json#/name` به‌عنوان کلید پروفایل | موتور شاخه را با نام lookup می‌کند؛ نام باید برای اتصال ردیف نتیجه به پروفایل درست حفظ شود. این وابستگی هویتی است و باید در projection مستند و آزمون‌پذیر باشد. | [بارگذاری شاخه‌ها](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L95-L125)، [lookup مسیرهای جایگزین](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L560-L590) |
| `school_branches_v2.json#/micro_motive_codes` و `#/m_score_denom_limit` | کدهای شاخه برای M-Score شاخه به‌کار می‌روند؛ `m_score_denom_limit` در مخرج محاسبه وارد می‌شود. | [M-Score شاخه](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L286-L321) |
| `school_branches_v2.json#/strategy_weights` و `#/value_weights` | در بردارهای پروفایل و محاسبهٔ فاصله برای مسیرهای جایگزین شاخه‌ای استفاده می‌شوند؛ تغییرشان می‌تواند خروجی تطبیق را عوض کند. | [فاصلهٔ پروفایل شاخه‌ها](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L560-L590) |
| `micro_motives.json#/[].code` | کدهای کاتالوگ در فیلتر `_active_branch_code_set` مصرف می‌شوند و ممکن است set کدهای شاخهٔ مؤثر در M-Score را تغییر دهند. | [نرمال‌سازی set کدهای شاخه و M-Score](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L286-L321) |
| `docs/data/questions_v2.json#/layers/strategies/questions` — دست‌کم ترتیب و نگاشت گزینه‌ها | UI این فهرست را بارگیری می‌کند؛ موتور پاسخ‌های S را به‌صورت آرایهٔ موقعیتی در کنار ردیف‌های `strategy_weights` مصرف می‌کند. تغییر ترتیب یا معنای گزینه‌ها می‌تواند معنای امتیاز پاسخ یکسان را تغییر دهد، حتی اگر خود ماتریس عوض نشود. | [بارگیری سؤال‌ها در UI](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/docs/app.js#L353-L358)، [مصرف آرایهٔ موقعیتی](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L324-L355) |

**یادداشت دربارهٔ دامنه:** این فهرست، کاندیدای fingerprint علمیِ موتور فردیت/هدایت شاخه است؛ گسترش آن به همهٔ قراردادهای پذیرش دانشگاهی، سنجش یا محتوای رابط کاربری خارج از این مسیرها باید جداگانه ممیزی شود. `id` و `name` کلیدهای هویتی‌اند، نه وزن علمی؛ نگه‌داشتنشان برای اتصال صحیح ورودی‌های عددی است.

### جدول ۲ — ورودی‌های fingerprint membership / هدایت تحصیلی پیشنهادی

| مسیر/فیلد | نمونه یا نقش membership | منبع کد |
|---|---|---|
| `majors_database_v2.json#/high_school_branch` | نمونهٔ اصلی: رشتهٔ «پزشکی» به شاخهٔ «علوم تجربی» متصل است. این فیلد به‌عنوان metadata در مدل Major ذخیره می‌شود و در مسیر عددی S/V/M داخل `DarkHorseEngineV2` مصرف مستقیم ندارد. | [ثبت فیلد در seed](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/seed_reference_data.py#L755-L763)؛ مقادیر snapshot در [کاتالوگ](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/majors_database_v2.json#L1-L16) |
| `majors_database_v2.json#/exam_group` | دسته‌بندی گروه آزمون برای تعیین گروه سنجش/پذیرش؛ این رابطه با هدایت یا ظرفیت سنجش است، نه وزن S/V/M. | [نگاشت exam_group در موتور سنجش](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/admission_sanjesh_engine.py#L454-L466)، [ثبت در seed](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/seed_reference_data.py#L755-L763) |
| رابطهٔ شناسهٔ رشته به `high_school_branch` و نام شاخه در `school_branches_v2.json` | رابطهٔ عضویت و اتصال کاتالوگ رشته به شاخه؛ باید همراه با شناسه‌های ثابت ثبت شود تا تغییر مسیر عضویت قابل گزارش باشد. | [فیلدهای Major در seed](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/seed_reference_data.py#L755-L763)، [نام و کلیدهای شاخه در موتور](https://github.com/arad2000/dark-horse-v2-/blob/02f40f16e044219141a1d354d9d1aa30df416d87/dark_horse_engine_v2.py#L95-L125) |

### جدول ۳ — موارد مبهم؛ نیازمند تصمیم ناظر

| مسیر/فیلد | چرا فعلاً در علمی قرار نمی‌گیرد | تصمیم لازم |
|---|---|---|
| `majors_database_v2.json#/group` | در موتور در برچسب/خروجی `realm_fa` و اطلاعات مسیر جایگزین مصرف می‌شود؛ مصرفش صرفاً امتیاز عددی نیست. | آیا خروجی دسته‌بندی باید fingerprint مستقلِ presentation/identity داشته باشد؟ |
| `majors_database_v2.json#/cluster` و `#/subgroup` | در seed ذخیره می‌شوند، اما این ممیزی مصرف کامل و نهایی‌شان را در همهٔ مسیرهای admission/UX اثبات نکرده است. | مالکیت membership و مصرف‌کنندگان واقعی این فیلدها تأیید شوند. |
| `majors_database_v2.json#/name`، `#/archetype`، `#/fulfillment_source`، `#/prestige_level` | بر عنوان رشته، شرح شخصی‌سازی، توضیح کهن‌الگو یا سطح تقاضای نمایشی اثر دارند؛ لزوماً روی Total عددی اثر مستقیم ندارند. `name` همچنین برای اتصال معنایی ردیف لازم است. | آیا fingerprint جداگانهٔ محتوای توضیحی/خروجی لازم است؟ شناسهٔ رشته باید مستقل و قطعی باقی بماند. |
| `majors_database_v2.json#/handcrafted` و `#/weights_version` | در تست‌ها/ممیزی provenance و وضعیت تدوین را بیان می‌کنند؛ مسیر عددی موتور از آن‌ها به‌عنوان ضریب استفاده نمی‌کند. | آیا نسخه/تأیید پروفایل باید بخشی از scientific fingerprint باشد یا قرارداد provenance جدا بماند؟ |
| `micro_motives.json#/[]/(description_fa, category, intensity_level)` | `description_fa` در evidence خروجی می‌آید؛ کدها برای محاسبه مهم‌اند، ولی متن و دسته‌بندی خودشان مستقیماً در فرمول M/S/V وارد نمی‌شوند. | fingerprint متون/برچسب‌ها جدا از امتیاز عددی تعریف شود یا خیر؟ |
| `value_poles_v2.json` و `docs/data/trait_map_v3.json` | قطب‌های ارزش برای برچسب و صفت‌های `trait_map` برای تفسیر پاسخ‌ها استفاده می‌شوند؛ مستقیماً ضریب Total را تعیین نمی‌کنند، اما می‌توانند تفسیر و متن خروجی را تغییر دهند. | دامنهٔ علمی فقط Total عددی باشد یا معنای تفسیری خروجی‌ها نیز قرارداد مستقل داشته باشد؟ |
| `school_branches_v2.json#/group`، `#/weights_version` و `#/source_majors_count` | group و فیلدهای provenance/شمارش می‌توانند طبقه‌بندی یا گزارش را عوض کنند، اما مصرف عددی یکسانی با ماتریس وزن‌ها ندارند. | قرارداد identity/membership در کنار پروفایل عددی مشخص شود. |

## B) سناریوهای آفلاین روی snapshot فعلی

این بررسی فقط روی یک کپی در حافظه از `majors_database_v2.json` در commit `02f40f16e044219141a1d354d9d1aa30df416d87` انجام شده است. از همان نرمال‌سازی و سریال‌سازی تابع `_catalog_fingerprint` و hash فعلی استفاده شد؛ هیچ فایل مخزن یا expected تغییر نکرد. ردیف آزمایشی، شناسهٔ ۱ است که در مجموعهٔ شناسه‌های نرمال‌سازی مرحله‌ای قرار ندارد.

| حالت | تغییر آزمایشی در کپی حافظه | hash فعلی ۱–۱۹۴ | نتیجهٔ گیت فعلی با expected ثابت | نتیجهٔ مورد انتظار در قرارداد دوگیتی |
|---|---|---|---|---|
| ۱) فقط membership تغییر کند | `high_school_branch` شناسهٔ ۱: «علوم تجربی» ← «ریاضی» | `8b4ba780da5e5255` (base: `f533be54c5fef0d6`) | **می‌شکند**؛ فیلد داخل متن هش تاریخی است، پس تغییر metadata و علمی از هم تفکیک نمی‌شوند. | scientific: **بدون تغییر**؛ membership: **FAIL/تغییر قابل‌بررسی**. |
| ۲) فقط یک وزن علمی تغییر کند | `strategy_weights[0][0]` شناسهٔ ۱: `0.4` ← `0.4005`؛ جمع ردیف `1.0005` است و در تلورانس فعلی `0.002` می‌ماند. | `a4062e110b847d77` (base: `f533be54c5fef0d6`) | **می‌شکند**؛ fingerprint تاریخی تغییر وزن را تشخیص می‌دهد، اما نوع تغییر را از metadata تفکیک نمی‌کند. | scientific: **FAIL**؛ membership: **بدون تغییر**. |
| ۳) بدون تغییر | snapshot همان‌طور که هست | `f533be54c5fef0d6` | **همین حالا FAIL است**: expected موجود برای ۱–۱۹۴ برابر `5189181b82aab0e6` است. این اختلاف پیش از هر جهش آزمایشی وجود دارد و نباید با تغییر expected پنهان شود. | چون هنوز هیچ expected دوگیتی تصویب/فعال نشده، نتیجهٔ واقعی از این سند صادر نمی‌شود؛ در baseline مصوب و ثابت، نبود تغییر باید در هر دو projection بدون اختلاف باشد. |

نتیجهٔ عملی: آزمون hash، حساسیت فعلی را تأیید می‌کند، اما گیت واحد نمی‌گوید شکست از علمی است یا membership. مقادیر دو سناریوی آزمایشی hash جدید یا expected تولیدی نیستند؛ فقط خروجی موقت از دو کپی تغییر‌یافته‌اند. **هیچ expected در CI به این مقادیر تغییر نمی‌کند.**

مبنای وضعیت قرمز snapshot: اجرای Commercial Backend CI روی commit `02f40f16e044219141a1d354d9d1aa30df416d87` در [run 40937940187](https://github.com/arad2000/dark-horse-v2-/actions/runs/40937940187) در مرحلهٔ Reference-data integrity با expected/actual بالا شکست خورده است.

## C) قرارداد پیشنهادی دو گیت — ۱۰ خط

1. توابع طراحی‌شده: `build_scoring_projection(snapshot)` و `scientific_fingerprint(snapshot)`.
2. توابع طراحی‌شده: `build_membership_projection(snapshot)` و `membership_fingerprint(snapshot)`.
3. projection علمی فقط فیلدهای تأییدشدهٔ اثرگذار بر S/V/M، واجدشرایط‌بودن، مخرج M شاخه و فاصلهٔ پروفایل را به همراه کلید هویتی لازم نگه دارد.
4. projection membership رابطهٔ `major_id → high_school_branch` و فیلدهای هدایت تأییدشده مانند `exam_group` را جداگانه و با کلیدهای پایدار نگه دارد.
5. قبل از hash، JSON باید با همان قرارداد fail-closed بارگذاری شود؛ NaN، Infinity و float overflow همچنان رد شوند؛ رفتار #320 حفظ شود.
6. canonicalization قطعی باشد: کلیدهای map مرتب، ترتیب ماتریس ۲۵×۵ و ترتیب/شناسهٔ سؤال‌ها حفظ، و تغییر نام/شناسه به‌صورت diff قابل‌فهم گزارش شود.
7. اجرای آینده پس از اعتبارسنجی ورودی و قرارداد schema: scientific fingerprint، سپس membership fingerprint؛ این ترتیب در Phase 0 فقط پیشنهاد است.
8. **scientific FAIL ⇒ شکست کل integrity**؛ خطای علمی هرگز با PASS عضویت جبران یا پوشانده نشود.
9. **membership-only FAIL** با status و گزارش مشخصِ خودش نمایش داده شود؛ PASS علمی نباید به PASS کلی کاذب تبدیل شود. سیاست نهایی blocking بودن status عضویت باید پیش از فعال‌سازی تصویب شود.
10. هیچ یک از دو گیت در CI فعلی متصل یا فعال نمی‌شود تا ناظر این سند را تأیید کند؛ این سند expected یا baseline تعیین نمی‌کند.

### سازگاری با نرمال‌سازی مرحله‌ای S/V فعلی

گیت تاریخی فعلی با `_restore_f1_approved_rows_for_historical_fingerprint` ردیف‌های نامزد زیر را با stub مرجع جایگزین می‌کند: F1 `183,184,185,186,187,189`؛ F1b `177,178,180,181,182`؛ F2 `199,201,202,203,204`؛ F3 `205,209,210,211,212,213,214`؛ F4 `208,219,220`. فیلدهای بازنویسی‌شده عبارت‌اند از `handcrafted`، `motive_driven`، `weights_version`، `micro_motive_codes`، `strategy_weights`، `value_weights`، `archetype` و `fulfillment_source`. به همین دلیل، این فیلدها برای شناسه‌های مذکور در checksum تاریخی به شکل فعلی‌شان پوشش داده نمی‌شوند؛ `high_school_branch` جزو این فهرست نیست و در hash باقی می‌ماند.

**قرارداد پیشنهادی جدید نباید این نرمال‌سازی تاریخی را کورکورانه روی همهٔ ردیف‌های فعال دوباره اعمال کند**؛ در غیر این صورت پروفایل واقعی رشته‌های `motive_driven=true` از fingerprint علمی حذف می‌شود. گیت تاریخی فعلی بدون تغییر باقی می‌ماند؛ projection علمی تازه باید فیلدهای score-driving واقعی ردیف‌های فعال را ببیند و ردیف‌های غیرفعال/catalog-only را طبق قاعده‌ای روشن و نسخه‌دار مدیریت کند. این یک قاعدهٔ طراحی برای تصمیم ناظر است، نه تغییر اجرایی در این PR.

## D) محدوده و خط قرمز

- این PR فقط مجاز به افزودن همین سند طراحی است؛ هیچ ماژول hash، تست اجرایی یا workflow جدیدی اضافه نمی‌شود.
- `strategy_weights`، `value_weights` و `motive_driven` دست‌کاری نمی‌شوند؛ `majors_database_v2.json` و سایر JSONهای scoring بازنویسی نمی‌شوند.
- expected fingerprintهای فعلی و شرط pass/fail گیت اصلی بدون تغییر می‌مانند؛ هیچ baseline تولیدی برای سبزشدن عوض نمی‌شود.
- fail-closed حفظ می‌شود؛ loader با رفتار #320 در رد NaN/Infinity تغییر نمی‌کند.
- Hybrid، cutover، env لیارا، UI و داده‌های پرداخت خارج از scope هستند و دست نمی‌خورند.
- #321 تغییر داده یا Merge نمی‌شود؛ هیچ همسان‌سازی مصنوعی با main انجام نمی‌گیرد.
- **Merge = خیر.** فعال‌سازی گیت‌های جدید منوط به تأیید صریح ناظر بر این سند و تصمیم‌های موارد مبهم است.
