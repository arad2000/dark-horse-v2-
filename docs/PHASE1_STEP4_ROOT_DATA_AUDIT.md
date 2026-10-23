# ممیزی گام ۴ بستهٔ ۱ — فایل‌های دادهٔ ریشهٔ `main` و وابستگی‌های تست / CI

- **شاخهٔ مرجع ممیزی:** `main` در commit `fb1e7bf6fbf0fa47e9ae10b9fdc5f8941f79db22` (پس از Mergeهای `#274`، `#275` و `#276`)
- **شاخهٔ مرجع مقایسهٔ بک‌اند زنده:** `deploy/liara-commercial-sandbox` در commit `537a00aeb718703cda4db27b4b0e08d108da017a`
- **نوع اقدام در این دور:** صرفاً ممیزی و طراحی اجرایی (هیچ فایلی حذف، جابه‌جا یا ویرایش اجرایی نشده است).

---

## حکم صریح `Go / No-Go`

> **`GO` — بله، اجرای «ریزگام A» بدون هیچ تغییری در تست‌ها هم‌اکنون ۱۰۰٪ امن است.**
> حذف ۵ فایل غیرمرجع ریشه (`program2s.json`، `majors_database_v22.json`، `school_branches_v22.json`، `trait_map_v3.json` ریشه، و `31032553.txt` ریشه — مجموعاً **`9,187,814 bytes` معادل `8.76 MiB` / `9.19 MB`**) هم با تحلیل ایستا (`git grep`) و هم با تزریق خطای عملی روی هر **۱۵ فایل `tests/test_*.js`** و گام‌های ورک‌فلوی **`Publish frontend from main`** آزمایش شد و **`0` خطا در تست‌ها، `0` ارجاع runtime فرانت‌اند و `0` اثر بر سرور زندهٔ `deploy`** دارد.

---

## کار ۱ — جدول کامل فایل‌های داده و پیکربندی خارج از `docs/` روی `main`

مجموع فایل‌های غیرکد (JSON / TXT / پیکربندی پلتفرم) در ریشهٔ `main` برابر **۱۰ فایل** به حجم کل **`10,211,075 bytes` (`9.74 MiB`)** است:

| مسیر در ریشهٔ `main` | اندازه دقیق | Git Blob SHA روی `main` | آخرین commit واقعی مرتبط روی `main` | استفاده در runtime فرانت (`main/docs`)؟ | سخت‌کد در تست‌های CI (`tests/**` / ورک‌فلوها)؟ | وضعیت روی `deploy` و مقایسهٔ تازگی | پیشنهاد نهایی |
|---|---:|---|---|---|---|---|---|
| `program2s.json` | `8,577,244 B` | `f0dba97099a93d9daa8698271730c9a386dc61ec` | `e266c373ec` (`2026-09-22` — *Add files via upload*) | **خیر (`0`)** — فقط اشارهٔ متنی در سند `docs/SANJESH_ADMISSION_ENGINE_CONTRACT.md` | **خیر (`0`)** — فقط در اسکریپت آفلاین دستی `scripts/validate_program2s_admission_contract.py` | **بله؛ نسخهٔ `deploy` جدیدتر و بزرگ‌تر است** (`8,718,996 B`، SHA `0c2747057a35…`، `06bf52e624` در `2026-09-28` — *rerun Table 5 mapping*) | **حذف از ریشهٔ `main` (ریزگام A)** — آرشیو طبیعی در تاریخچهٔ Git (`fb1e7bf6`) + نسخهٔ معتبر روی `deploy` محفوظ می‌ماند |
| `majors_database_v22.json` | `568,330 B` | `c960719f96822d358a3d7cf9f40dbe9a23df6251` | `596da89d6d` (`2026-09-20` — *repair biotechnology motive-code references*؛ نسخهٔ قدیمی ۱۶۰ رشته‌ای) | **خیر (`0`)** | **خیر (`0`)** | **خیر (غایب در `deploy`)** — منسوخ‌شده توسط `majors_database_v2.json` (۲۳۰ رشته) | **حذف از ریشهٔ `main` (ریزگام A)** |
| `school_branches_v22.json` | `33,027 B` | `f6189e373a915d9bc695e844cb3fca15cb3d2f61` | `3ac1e1f562` (`2026-08-27` — *Rename school_branches_v2.json to school_branches_v22.json*) | **خیر (`0`)** | **خیر (`0`)** | **خیر (غایب در `deploy`)** — منسوخ‌شده توسط `school_branches_v2.json` (`2026-10-18`) | **حذف از ریشهٔ `main` (ریزگام A)** |
| `trait_map_v3.json` | `9,212 B` | `466280fe517b7e6ba68e54dbe8535de7444c7f4a` | `bbbbb06a6b` (`2026-08-20` — *Add files via upload*) | **خیر (`0` به ریشه)** — فرانت از `docs/data/trait_map_v3.json` (و fallback `docs/trait_map_v3.json`) می‌خواند | **خیر (`0` به ریشه)** — ۲ تست JS به `docs/trait_map_v3.json` اشاره دارند نه ریشه | **بله؛ کاملاً یکسان با `deploy`** (`466280fe51…` در `2026-08-20`) + ۲ کپی یکسان دیگر داخل `docs/` و `docs/data/` روی `main` دارد | **حذف کپی تکراری ریشهٔ `main` (ریزگام A)** — کپی‌های `docs/data/trait_map_v3.json` و `docs/trait_map_v3.json` می‌مانند |
| `31032553.txt` | `1 B` | `8b137891791fe96927ad78e64b0aad7bded08bdc` | `00ed6abaa3` (`2026-09-06` — *Update and rename docs/21182430.txt to 31032553.txt*) | **خیر (`0` به ریشه)** — GitHub Pages فقط `docs/31032553.txt` (SHA یکسان) را سرو می‌کند | **خیر (`0`)** | **خیر (غایب در `deploy`)** | **حذف کپی بی‌اثر ریشهٔ `main` (ریزگام A)** — `docs/31032553.txt` حفظ می‌شود |
| `micro_motives.json` | `234,537 B` | `9a5c32831ed3a1f2d1371add4f29f46f35969b29` | `c8c0dd2899` (`2026-10-17` — *Sync root micro_motives.json with docs data (#212)*) | **خیر (`0` به ریشه)** — فرانت فقط `docs/data/micro_motives.json` (SHA یکسان) را fetch می‌کند | **بله (`1` تست):** `tests/test_catalog_alignment.js:9` به مسیر ریشه سخت‌کد شده است (۳ تست دیگر از `docs/data/micro_motives.json` می‌خوانند) | **بله؛ کاملاً یکسان با `deploy` و `docs/data/micro_motives.json`** (`9a5c32831e…`) | **نگه در ریزگام A / حذف در ریزگام B** پس از تغییر ۱ خط مسیر در `test_catalog_alignment.js:9` |
| `majors_database_v2.json` | `749,343 B` | `64d109af28359ec692bc1e4a0647d65558e4b18b` | `1f10f991b2` (`2026-10-19` — *R1: align main majors catalog to approved 230-entry deploy*) | **خیر مستقیم** (در runtime فرانت خلاصهٔ `docs/data.js` و `docs/majors_catalog_ui_v1.json` سرو می‌شود) | **بله (`3` تست حیاتی CI):** خطوط زیر مستقیماً فایل ریشه را می‌خوانند | **بله؛ کاملاً یکسان با `deploy`** (`64d109af28…` — هم‌تراز در R1)؛ هیچ کپی کاملی از آن داخل `docs/` نیست | **نگه قطعی (`نگه`)** — منبع حقیقت ۲۳۰ رشته‌ای برای تست‌های قرارداد CI و کالیبراسیون بستهٔ ۲ |
| `value_poles_v2.json` | `991 B` | `251d435d57b90e325ff671a4f8c69c530de61494` | `30f3a094eb` (`2026-07-07` — *Add files via upload*؛ ۳۰ قطب ارزشی) | **خیر مستقیم** (در `docs/data.js` و `docs/app.js` تعبیه شده) | **بله (`1` تست حیاتی CI):** `tests/test_value_poles_contract.js:9` | **بله؛ کاملاً یکسان با `deploy`** (`251d435d57…`)؛ کپی JSON در `docs/` ندارد | **نگه قطعی (`نگه`)** — مرجع رسمی قرارداد ۳۰ قطب ارزشی در CI و بستهٔ ۲ |
| `school_branches_v2.json` | `38,246 B` | `cac4c01388a04fee5879daeefef0c6983228d976` | `7a04946a90` (`2026-10-18` — *Align school branches with majors activated since September*) | **خیر مستقیم** (معادل JS در `docs/data.js` است) | **خیر فعلاً (`0` تست JS)** | **بله؛ کاملاً یکسان با `deploy`** (`cac4c01388…` در `2026-10-18`)؛ کپی JSON در `docs/` ندارد | **نگه قطعی (`نگه`)** — چهارمین فایل مرجع کاتالوگ/شاخه‌ها برای کالیبراسیون علمی بستهٔ ۲ |
| `liara.json` | `144 B` | `b6033cd8bf9d7a1cb4f92af912bcbccf7c032b0e` | `9159c34681` (`2026-08-27` — *Create liara.json*) | **خیر (`0`)** | **خیر (`0`)** | **بله؛ کاملاً یکسان با `deploy`** (`b6033cd8bf…`) | **تفکیک به گام ۵** (همراه تصمیم‌گیری یکجا دربارهٔ فایل‌های پایتون/استقرار ریشهٔ `main`) |

> **یادداشت تکمیلی درون `docs/`:** فایل `trait_map_v3.json` درون خود `docs/` نیز در دو مسیر یکسان `docs/data/trait_map_v3.json` و `docs/trait_map_v3.json` (`9,212 B`، SHA `466280fe51…`) وجود دارد که هر دو مجاز و مورد استفادهٔ فرانت/تست‌ها هستند و در این گام دست‌نخورده می‌مانند.

---

## کار ۲ — وابستگی دقیق تست‌ها، CI، `docs/**` و `scripts/**`

### الف) جدول شمارش `git grep` و نتیجهٔ آزمون عملی حذف تک‌به‌تک

| فایل کاندیدا در ریشه | `tests/**` | `.github/workflows/**` | `docs/**` | `scripts/**` | تست‌هایی که در صورت حذف فایل ریشه **FAIL** می‌شوند |
|---|---:|---:|---:|---:|---|
| `program2s.json` | `0` | `0` | `2` *(فقط سند Markdown)* | `3` *(`validate_program2s_admission_contract.py`)* | **هیچ تستی در CI نمی‌شکند (`0/15`)** — فقط اسکریپت آفلاین دستی `scripts/validate_program2s_admission_contract.py` در صورت اجرای دستی روی `main` نیاز به فایل دارد |
| `majors_database_v22.json` | `0` | `0` | `0` | `0` | **هیچ تستی نمی‌شکند (`0/15`)** |
| `school_branches_v22.json` | `0` | `0` | `0` | `0` | **هیچ تستی نمی‌شکند (`0/15`)** |
| `trait_map_v3.json` *(ریشه)* | `0` *(۴ ارجاع به `docs/trait_map_v3.json`)* | `0` | `3` *(همگی درون `docs/`)* | `3` *(فقط لیست مجاز گارد Pages)* | **هیچ تستی نمی‌شکند (`0/15`)** — تست‌ها از `docs/trait_map_v3.json` می‌خوانند |
| `31032553.txt` *(ریشه)* | `0` | `0` | `0` *(فایل مجزای `docs/31032553.txt`)* | `0` | **هیچ تستی نمی‌شکند (`0/15`)** |
| `liara.json` | `0` | `0` | `0` | `0` | **هیچ تستی نمی‌شکند (`0/15`)** |
| `micro_motives.json` *(ریشه)* | `1` به ریشه + `12` به `docs/data/` | `4` *(همگی به `docs/data/` و `! test -f data/micro_motives.json`)* | `6` *(همگی `docs/data/`)* | `2` *(لیست مجاز گارد)* | **۱ تست می‌شکند (`1/15`):** `tests/test_catalog_alignment.js` (خط `9`: `path.join(root, 'micro_motives.json')` → job `catalog-motive-contracts` قرمز می‌شود) |
| `majors_database_v2.json` | `4` *(در ۳ فایل تست)* | `0` | `5` *(متادیتا و مستندات)* | `2` *(`validate_program2s_admission_contract.py`)* | **۳ تست می‌شکنند (`3/15`):** ۱) `tests/test_catalog_alignment.js:8` · ۲) `tests/test_motive_route_contracts.js:9` · ۳) `tests/test_p0_server_authoritative_quota_gate.js:859` (هر دو job در `Purchase UI regression` قرمز می‌شوند) |
| `value_poles_v2.json` | `3` *(در ۱ فایل تست)* | `0` | `0` | `2` *(لیست مجاز گارد)* | **۱ تست می‌شکند (`1/15`):** `tests/test_value_poles_contract.js` (خط `9`: `path.join(root, 'value_poles_v2.json')` → job `purchase-ui` قرمز می‌شود) |
| `school_branches_v2.json` | `0` | `0` | `0` | `2` *(لیست مجاز گارد)* | **فعلاً `0/15`** (اما فایل مرجع کالیبراسیون شاخه‌های پایهٔ نهم در بستهٔ ۲ است و کپی JSON در `docs/` ندارد → باید حفظ شود) |

### ب) فهرست دقیق «۴ فایل مرجع کاتالوگ / روان‌سنجی» که باید روی `main` حفظ شوند

همان‌گونه که در ممیزی فاز صفر مشخص شد، ۴ مجموعه دادهٔ مرجع هستهٔ علمی/کاتالوگ بین `main` و `deploy` بایت‌به‌بایت هم‌ترازند (`SHA` یکسان) و نباید از `main` حذف شوند (تنها مورد قابل یکپارچه‌سازی، حذف کپی دوم `micro_motives.json` در ریشه پس از اصلاح خط ۹ تست است):

1. **`majors_database_v2.json`** (ریشه — `749,343 B`، SHA `64d109af28…`): تنها نسخهٔ کامل ۲۳۰ رشته روی `main`؛ مصرف‌شده در:
   - `tests/test_catalog_alignment.js:8`
   - `tests/test_motive_route_contracts.js:9`
   - `tests/test_p0_server_authoritative_quota_gate.js:859`
2. **`docs/data/micro_motives.json`** (`234,537 B`، SHA `9a5c32831e…` — به‌همراه کپی همسان ریشه `micro_motives.json` تا پیش از ریزگام B): منبع حقیقت ۱٬۳۹۳ میکروموتیو؛ مصرف‌شده در:
   - `tests/test_catalog_alignment.js:9` *(فعلاً روی مسیر ریشه `micro_motives.json`)*
   - `tests/test_motive_route_contracts.js:10` *(مسیر `docs/data/micro_motives.json`)*
   - `tests/test_navigation_resume_and_standard_ux.js:65` *(مسیر `docs/data/micro_motives.json`)*
   - `tests/test_p0_server_authoritative_quota_gate.js:138` *(مسیر `docs/data/micro_motives.json`)*
   - `.github/workflows/publish-frontend-from-deploy.yml:38,46,79` *(مسیر `docs/data/micro_motives.json`)*
3. **`value_poles_v2.json`** (ریشه — `991 B`، SHA `251d435d57…`): مرجع ۳۰ قطب ارزشی؛ مصرف‌شده در:
   - `tests/test_value_poles_contract.js:9`
4. **`school_branches_v2.json`** (ریشه — `38,246 B`، SHA `cac4c01388…`): مرجع ۴ شاخهٔ تحصیلی هم‌تراز با کاتالوگ ۲۳۰ رشته (`2026-10-18`)؛ فاقد کپی JSON در `docs/` و مورد نیاز مستقیم کالیبراسیون علمی بستهٔ ۲.

*(به‌علاوه در داخل `docs/` فایل‌های مرجع زندهٔ فرانت `docs/majors_catalog_ui_v1.json`، `docs/data/questions_v2.json` و `docs/data/trait_map_v3.json` + `docs/trait_map_v3.json` دست‌نخورده باقی می‌مانند.)*

### ج) پاسخ صریح دربارهٔ `program2s.json` ریشه

- **آیا `program2s.json` ریشه توسط هیچ loader فرانت‌اند خوانده می‌شود؟** **خیر، مطلقاً خیر (`0` ارجاع اجرایی در کل `docs/**/*.{js,html,css}`).**
- حتی از طریق GitHub Pages منتشر هم نمی‌شود (چون خارج از `docs/` است) و در هیچ‌یک از ورک‌فلوهای GitHub Actions یا ۱۵ تست JS نیز خوانده نمی‌شود.
- این فایل صرفاً میراث قدیمی بک‌اند از تاریخ `2026-09-22` (`4,150` برنامه، `8,577,244 B`) است، در حالی که شاخهٔ زندهٔ `deploy/liara-commercial-sandbox` نسخهٔ به‌روزشدهٔ بزرگ‌تر (`8,718,996 B` مورخ `2026-09-28`) را در اختیار دارد.

---

## کار ۳ — تفکیک بر اساس مرز حاکمیت (`main/docs` در برابر `deploy`)

1. **فقط زباله / تکرار مرده روی `main` (غایب در `deploy` و بی‌مصرف در فرانت و تست‌ها):**
   - `majors_database_v22.json` (`568,330 B` — نسخهٔ منسوخ ۱۶۰ رشته‌ای)
   - `school_branches_v22.json` (`33,027 B` — نسخهٔ منسوخ پیش از مهر)
   - `31032553.txt` ریشه (`1 B` — کپی بیرون از `docs/`؛ نسخهٔ اصلی در `docs/31032553.txt` است)
2. **حذف از ریشهٔ `main` کاملاً بی‌خطر برای Production به شرط دست‌نخورده ماندن `deploy`:**
   - `program2s.json` (`8,577,244 B` — سرور لیارا از نسخهٔ جدیدتر روی `deploy` استفاده می‌کند و Pages به ریشهٔ `main` کاری ندارد)
   - `trait_map_v3.json` ریشه (`9,212 B` — سرور لیارا کپی ریشهٔ `deploy` را دارد و فرانت/تست‌های `main` کپی‌های `docs/data/trait_map_v3.json` و `docs/trait_map_v3.json` را می‌خوانند)
   - `micro_motives.json` ریشه (`234,537 B` — **فقط پس از اصلاح ۱ خط در `tests/test_catalog_alignment.js:9`**؛ فرانت `main` از `docs/data/micro_motives.json` و بک‌اند `deploy` از کپی خود می‌خواند)
3. **حذف از ریشهٔ `main` خطرناک یا شکنندهٔ CI / کالیبراسیون علمی (باید روی `main` بمانند):**
   - `majors_database_v2.json` (شکست فوری ۳ تست CI + حذف تنها مرجع کامل ۲۳۰ رشته روی `main`)
   - `value_poles_v2.json` (شکست فوری `test_value_poles_contract.js`)
   - `micro_motives.json` ریشه **قبل از اصلاح خط ۹ تست** (شکست فوری `test_catalog_alignment.js`)
   - `school_branches_v2.json` (حذف تنها JSON هم‌تراز شاخه‌های دبیرستان روی `main` پیش از کالیبراسیون بستهٔ ۲)

---

## کار ۴ — طرح پیشنهادی برای فاز اجرای بعدی (طرح پیشنهادی؛ در این PR اجرا نشده است)

| ریزگام پیشنهادی | دامنهٔ دقیق تغییر روی `main` | حجم آزادشده | ریسک یک‌خطی | دستور Rollback اتمیک |
|---|---|---:|---|---|
| **ریزگام A** *(حذف خالص بدون تغییر هیچ تستی — اولویت اول)* | `git rm` روی دقیقاً ۵ مسیر: `program2s.json`، `majors_database_v22.json`، `school_branches_v22.json`، `trait_map_v3.json` (ریشه)، `31032553.txt` (ریشه) | **`9,187,814 B`** (`8.76 MiB`) | اسکریپت آفلاین دستی `scripts/validate_program2s_admission_contract.py` اگر به‌صورت دستی روی `main` اجرا شود فایل `program2s.json` قدیمی ریشه را نخواهد دید (در CI اجرا نمی‌شود و نسخهٔ جدیدتر روی `deploy` است). | `git revert <merge_sha>` یا `git checkout fb1e7bf6fbf0fa47e9ae10b9fdc5f8941f79db22 -- program2s.json majors_database_v22.json school_branches_v22.json trait_map_v3.json 31032553.txt` |
| **ریزگام B** *(یکپارچه‌سازی مسیر تست و حذف تکرار `micro_motives.json` ریشه)* | ۱ خط تغییر در `tests/test_catalog_alignment.js:9` به `path.join(root, 'docs', 'data', 'micro_motives.json')` + `git rm micro_motives.json` (ریشه) | **`234,537 B`** (`229.0 KiB`) | اگر PR قدیمی یا اسکریپت محلی بیرون از مخزن به مسیر ریشهٔ `micro_motives.json` تکیه کرده باشد با خطای مسیر روبه‌رو می‌شود (در تمام CI سبز است). | `git revert <merge_sha>` یا `git checkout <base_sha> -- tests/test_catalog_alignment.js micro_motives.json` |
| **ریزگام C** *(تثبیت مراجع کاتالوگ روی `main`)* | نگهداشت صریح `majors_database_v2.json`، `value_poles_v2.json` و `school_branches_v2.json` در ریشهٔ `main` بدون تغییر (و موکول کردن تصمیم دربارهٔ فایل‌های `*.py` منسوخ ریشه و `liara.json` به **گام ۵** مستقل) | `0 B` | هیچ ریسک اجرایی ندارد؛ تنها ~`788 KB` دادهٔ مرجع معتبر برای تست‌های قرارداد و بستهٔ ۲ در ریشه باقی می‌ماند. | نیاز به Rollback ندارد (بدون تغییر فایل). |
