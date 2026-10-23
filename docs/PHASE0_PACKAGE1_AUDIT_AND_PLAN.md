# فاز صفر — بستهٔ ۱: ممیزی واگرایی مخزن، افشای دادهٔ خام سنجش در GitHub Pages و اندازه‌گیری بوت اسکریپت‌ها

- **مخزن:** `arad2000/dark-horse-v2-`
- **مرجع زندهٔ فرانت‌اند (`https://asbe-siah.ir` — GitHub Pages):** شاخهٔ `main` @ `bb7da0d907671dc8393f4f333d3e8779a5e2e5e9` (`SW: darkhorse-v78`)
- **مرجع زندهٔ بک‌اند (`https://api.asbe-siah.ir` — Liara Container):** شاخهٔ `deploy/liara-commercial-sandbox` @ `537a00aeb718703cda4db27b4b0e08d108da017a` (`uvicorn main_v2:app --host 0.0.0.0 --port 80`)
- **ماهیت این تحویل:** **صرفاً ممیزی + طرح اجرایی فاز ۱ + معیارهای پذیرش** (بدون تغییر در کد اجرایی، وزن‌ها، موتور امتیازدهی، Hybrid/Cutover، S2، `PR #204` یا متغیرهای محیطی لیارا).

---

## ۱. کار ۱ — نقشهٔ واگرایی کامل (`main` در برابر `deploy/liara-commercial-sandbox`)

### ۱-۱. آمار کلان درخت Git
- تعداد کل فایل‌ها (Blob) روی `main`: **`130` فایل**
- تعداد کل فایل‌ها (Blob) روی `deploy/liara-commercial-sandbox`: **`296` فایل**

### ۱-۲. جدول دقیق واگرایی فایل‌های حیاتی بک‌اند، داده، مهاجرت و CI

| مسیر فایل | وجود روی `main` | وجود روی `deploy` | اندازه / Git Blob SHA در `main` | اندازه / Git Blob SHA در `deploy` | نسخهٔ فعال در Runtime لیارا (`api.asbe-siah.ir`) |
|---|:---:|:---:|---|---|---|
| `liara.json` | دارد | دارد | `144 B` / `b6033cd8bf` | `144 B` / `b6033cd8bf` | **یکسان** (`uvicorn main_v2:app --port 80`) |
| `requirements.txt` | دارد | دارد | `49 B` / `32e24424fd` | `132 B` / `571522ea79` | **نسخهٔ `deploy`** (شامل `SQLAlchemy`, `psycopg`, `alembic`, `httpx`) |
| `main_v2.py` | دارد (منسوخ) | دارد | `15,691 B` / `a9aa5c6df2` | `27,981 B` / `7b541d5b22` | **نسخهٔ `deploy`** (نقطهٔ ورود اصلی سرور + اثرانگشت زمان اجرا) |
| `dark_horse_engine_v2.py` | دارد (منسوخ) | دارد | `40,061 B` / `96eb6a8ba3` | `42,794 B` / `7dd20e1cd0` | **نسخهٔ `deploy`** (قفل‌شده با `__runtime_fingerprint`) |
| `ai_counsel_service.py` | دارد (منسوخ) | دارد | `8,986 B` / `a79dd9dfaf` | `31,296 B` / `b5b0843176` | **نسخهٔ `deploy`** (نسخهٔ بازنویسی‌شدهٔ ضدِتوهم و ضدِتزریق) |
| `ai_rate_limit.py` | **ندارد** | دارد | — | `3,165 B` / `a20b7932e8` | **فقط روی `deploy`** (`COUNSEL_RATE_LIMITER`, `DISCOVERY_RATE_LIMITER`) |
| `request_body_limit_middleware.py` | **ندارد** | دارد | — | `3,573 B` / `d1149a6cde` | **فقط روی `deploy`** (محافظ حجم بدنهٔ درخواست‌ها) |
| `admission_sanjesh_engine.py` | **ندارد** | دارد | — | `38,881 B` / `722e8099c9` | **فقط روی `deploy`** (موتور شانس قبولی با آزمون و سوابق) |
| `admission_chance_api.py` | دارد (منسوخ) | دارد | `16,934 B` / `b2335c1f3e` | `25,059 B` / `6d99b9246e` | **نسخهٔ `deploy`** (`/api/v1/admission/chance` — قفل‌شده در اثرانگشت) |
| `admission_exam_capacity.py` | دارد (منسوخ ۱۴۰۴) | دارد (۱۴۰۵) | `6,952 B` / `0121d3aff8` | `12,448 B` / `b8ec038570` | **نسخهٔ `deploy`** (متصل به دفترچه‌های **۱۴۰۵** پنج گروه) |
| `admission_capacity_record.py` | **ندارد** | دارد | — | `8,306 B` / `3b679b7083` | **فقط روی `deploy`** (ظرفیت سوابق تحصیلی ۱۴۰۵ + `full`) |
| `record_major_map.py` | **ندارد** | دارد | — | `1,659 B` / `56c50beadd` | **فقط روی `deploy`** |
| `commercial_api.py` | **ندارد** | دارد | — | `19,448 B` / `4bbef5070f` | **فقط روی `deploy`** (`/api/v1/auth/*`, `/me/quota`, `/me/consume-test`, `/billing/*`) |
| `auth_service.py` | **ندارد** | دارد | — | `4,953 B` / `acbb1042f5` | **فقط روی `deploy`** (`PBKDF2-SHA256 600k` + هش توکن `SHA-256`) |
| `phone_verification_service.py` | **ندارد** | دارد | — | `7,857 B` / `b3fd80f010` | **فقط روی `deploy`** (ارسال و تأیید OTP موبایل) |
| `password_reset_service.py` | **ندارد** | دارد | — | `9,501 B` / `e99060e487` | **فقط روی `deploy`** (بازیابی رمز عبور با OTP) |
| `billing_api.py` | **ندارد** | دارد | — | `4,766 B` / `462b492fc0` | **فقط روی `deploy`** (سفارش و بازگشت درگاه زرین‌پال/Mock) |
| `billing_credit_service.py` | **ندارد** | دارد | — | `9,893 B` / `f2a7541691` | **فقط روی `deploy`** (مصرف اتمیک اعتبار `pack_3_tests` / `free_1_test`) |
| `billing_models.py` | **ندارد** | دارد | — | `10,392 B` / `07144992c8` | **فقط روی `deploy`** (`User`, `Entitlement`, `Order`, `Payment`, `JourneyCreditConsumption`) |
| `payment_providers.py` | **ندارد** | دارد | — | `6,447 B` / `7ac2d9ae9e` | **فقط روی `deploy`** (`ZarinPalPaymentProvider`, `MockPaymentProvider`) |
| `production_billing_guard.py` | **ندارد** | دارد | — | `3,099 B` / `ab1f8fb50c` | **فقط روی `deploy`** (گارد Fail-Closed پروداکشن روی `BILLING_FREE_MODE`) |
| `admin_api.py` | دارد (منسوخ) | دارد | `1,858 B` / `2e000b6ca2` | `4,904 B` / `42f1af2494` | **نسخهٔ `deploy`** |
| `admin_http_api.py` | دارد (منسوخ) | دارد | `3,834 B` / `9de30bbbd5` | `3,756 B` / `75a3c7c860` | **نسخهٔ `deploy`** |
| `admin_router.py` / `admin_service.py` | **ندارد** | دارد | — | `4,039 B` (`baeebb04df`) / `3,182 B` (`40abeeb265`) | **فقط روی `deploy`** (`/api/v1/admin/*`) |
| `feedback_api.py` | **ندارد** | دارد | — | `8,288 B` / `97d2b7e590` | **فقط روی `deploy`** (`/api/v1/feedback`, `/api/feedback/submit`) |
| `database.py` / `models.py` | **ندارد** | دارد | — | `5,023 B` (`1d2be26154`) / `11,141 B` (`c6c28bc047`) | **فقط روی `deploy`** (اتصال PostgreSQL و مدل‌های عملیاتی) |
| `api_persistence_adapter.py` / `api_shadow_bridge.py` / `shadow_persistence.py` | **ندارد** | دارد | — | `3,238 B` / `1,800 B` / `2,750 B` | **فقط روی `deploy`** (لایهٔ Hybrid/Shadow — خط قرمز دست‌نخورده) |
| `alembic.ini` + `alembic/env.py` + `alembic/versions/0001..0011` | **ندارد (`0/11`)** | **دارد (`11/11`)** | — | `0001` (`bff3e3ce4e`) تا `0011_otp_request_ip` (`09ef72bba5`) | **فقط روی `deploy`** (هیچ‌یک از ۱۱ مهاجرت روی `main` نیست) |
| `majors_database_v2.json` | دارد | دارد | `749,343 B` / `64d109af28` | `749,343 B` / `64d109af28` | **یکسان در هر دو شاخه** (`230` رشته، قفل اثرانگشت) |
| `micro_motives.json` و `docs/data/micro_motives.json` | دارد | دارد | `234,537 B` / `9a5c32831e` | `234,537 B` / `9a5c32831e` | **یکسان در هر دو شاخه** (`1,393` جرقه، قفل اثرانگشت) |
| `trait_map_v3.json` / `value_poles_v2.json` / `school_branches_v2.json` | دارد | دارد | `9,212 B` / `991 B` / `38,246 B` | `9,212 B` / `991 B` / `38,246 B` | **یکسان در هر دو شاخه** (`466280fe51` / `251d435d57` / `cac4c01388`) |
| `program2s.json` | دارد (قدیمی‌تر) | دارد | `8,577,244 B` / `f0dba97099` | `8,718,996 B` / `0c2747057a` | **نسخهٔ `deploy`** (خوانده‌شده در `admission_sanjesh_engine.py:14`) |
| `majors_database_v22.json` / `school_branches_v22.json` | دارد (بلااستفاده) | **ندارد** | `568,330 B` / `33,027 B` | — | **در لیارا وجود ندارد و مصرف نمی‌شود** |
| `.github/workflows/*` | `3` فایل | `8` فایل | `prod-migration-once`, `publish-frontend-from-deploy`, `purchase-ui-regression` | `commercial-backend-ci`, `liara-runtime-lock`, `hybrid-migration-audit`, `p0-contracts`, ... | گیت CI بک‌اند و قفل اثرانگشت زنده روی `deploy` اجرا می‌شود |

### ۱-۳. جملهٔ یک‌خطی سیاست مرجع حقیقت (پیشنهادی برای تصویب ناظر)

> **سیاست مصوب پیشنهادی:** «مرجع حقیقت مطلق بک‌اند، دیتابیس، مهاجرت‌های Alembic و داده‌های ظرفیت سرور منحصراً شاخهٔ `deploy/liara-commercial-sandbox` و مرجع حقیقت مطلق فرانت‌اند عمومی (`GitHub Pages`) منحصراً دایرکتوری `docs/` و تست‌های `tests/` در شاخهٔ `main` است؛ هرگونه کپی کور دوطرفه ممنوع بوده و همگام‌سازی در فاز ۱ صرفاً به‌صورت پاک‌سازی فایل‌های منسوخ/بی‌مصرف از `main` انجام می‌شود.»

### ۱-۴. فهرست فایل‌هایی که همگام‌سازی اشتباهشان در فاز ۱ خطر شکستن Production دارد

1. **خطر شکستن فوری `api.asbe-siah.ir` (در صورت کپی از `main` به `deploy` یا حذف روی `deploy`):**
   - `main_v2.py`، `dark_horse_engine_v2.py`، `ai_counsel_service.py`، `admission_chance_api.py`، `admission_exam_capacity.py`، `admin_api.py`، `admin_http_api.py`، `requirements.txt` و `program2s.json`: نسخهٔ `main` فاقد احراز هویت تجاری، محدودکنندهٔ نرخ، دفترکل سهمیه، موتور ۱۴۰۵ و قفل `__runtime_fingerprint` است و استقرار آن روی لیارا کل سرویس تجاری و CI قفل زنده (`liara-runtime-lock.yml`) را از کار می‌اندازد.
   - `docs/data/sanjesh_{riazi,tajrobi,ensani,honar,zaban}_1405_programs.json` و `docs/data/sanjesh_record_capacity_full.json` روی شاخهٔ `deploy`: حذف یا جابه‌جایی آن‌ها روی `deploy` بدون اصلاح هم‌زمان کد بک‌اند، مستقیماً مسیرهای `/api/v1/admission/chance` (`source="capacity"` در هر دو حالت `exam` و `record`) را با خطای `FileNotFoundError` می‌شکند.
2. **خطر افشای دادهٔ حساس و تخریب فرانت زندهٔ `asbe-siah.ir` (در صورت کپی از `deploy` به `main`):**
   - `docs/index.html`، `docs/app.js`، `docs/shell.js`، `docs/commercial_ui.js`، `docs/quota_runtime.js`: نسخه‌های موجود روی `deploy` بسیار قدیمی‌تر از `main` هستند (`app.js` روی `deploy` معادل `100 KB` در برابر `212 KB` روی `main`) و بازگرداندن آن‌ها تمام اصلاحات Home v2، PWA v78 و وصلهٔ P0 سهمیه (`PR #272`) را نابود می‌کند.
   - `deploy:docs/data/sanjesh_*_1405_programs.json` (`19.55 MB`) و `deploy:docs/data/sanjesh_record_capacity_full.json` (`6.48 MB`): کپی کردن آن‌ها به `main/docs/data/` باعث انتشار عمومی فوری **`26.03 MB`** دیتاست خام ۱۴۰۵ و کل ظرفیت سوابق روی سایت عمومی GitHub Pages می‌شود!

---

## ۲. کار ۲ — ممیزی دقیق مصرف کلاینتی و سروری فایل‌های سنجش ۱۴۰۴ و ۱۴۰۵

### ۲-۱. نتیجهٔ Grep سراسری فرانت‌اند (`docs/**/*.js`, `docs/**/*.html`, `docs/**/*.css`)
- جستجوی دقیق تمام الگوهای `1404_programs`، `1405_programs`، `sanjesh_riazi`، `sanjesh_tajrobi`، `sanjesh_ensani`، `sanjesh_honar`، `sanjesh_zaban` و `sanjesh_record_capacity` در کل درخت فرانت‌اند (`docs/**/*.{js,html,css}` و `docs/sw.js`):
  - **تعداد ارجاع در کل کدهای فرانت‌اند = دقیقاً `0` مورد.**
  - ماژول کلاینتی سنجش (`docs/admission_chance_ui.js`) صددرصد داده‌های شانس قبولی و ظرفیت را از API سرور (`https://api.asbe-siah.ir/api/v1/admission/chance`) دریافت می‌کند و هیچ فایل JSON ظرفیت محلی را از روی دامنهٔ GitHub Pages (`asbe-siah.ir/data/...`) نمی‌خواند.
  - تنها ارجاع به نام فایل‌های `1404_programs.json` در شاخهٔ `main`، فایل پایتون منسوخ ریشهٔ مخزن (`main:admission_exam_capacity.py:21-25`) است که نه توسط GitHub Pages پابلیش می‌شود و نه روی لیارا اجرا می‌گردد (زیرا لیارا از شاخهٔ `deploy` اجرا می‌شود که به فایل‌های `1405` مهاجرت کرده است).

### ۲-۲. جدول عددی کامل فایل‌های دادهٔ سنجش در `docs/data/`

| مسیر فایل | حجم دقیق (بایت) | وضعیت فعلی در GitHub Pages (`main`) | ارجاع فرانت (`docs/**/*.{js,html,css}`) | مصرف در Loader/API زندهٔ سرور (`deploy @ api.asbe-siah.ir`) | قابل حذف از Pages (`main`)؟ |
|---|---:|---|:---:|---|:---:|
| `docs/data/sanjesh_riazi_1404_programs.json` | `4,192,496 B` (`4.00 MiB`) | **در حال سرو عمومی در Pages!** | **`0`** | **مصرف زنده = `0`** (سرور به ۱۴۰۵ کوچ کرده؛ فقط در اسکریپت آفلاین `scripts/audit_riazi_1404_programs.py` روی `deploy`) | **بله — ۱۰۰٪ امن** |
| `docs/data/sanjesh_tajrobi_1404_programs.json` | `4,737,492 B` (`4.52 MiB`) | **در حال سرو عمومی در Pages!** | **`0`** | **مصرف زنده = `0`** (فقط در اسکریپت آفلاین `scripts/audit_tajrobi_1404_programs.py` روی `deploy`) | **بله — ۱۰۰٪ امن** |
| `docs/data/sanjesh_ensani_1404_programs.json` | `3,823,134 B` (`3.65 MiB`) | **در حال سرو عمومی در Pages!** | **`0`** | **مصرف زنده = `0`** (فقط در اسکریپت آفلاین `scripts/audit_ensani_1404_programs.py` روی `deploy`) | **بله — ۱۰۰٪ امن** |
| `docs/data/sanjesh_honar_1404_programs.json` | `3,365,595 B` (`3.21 MiB`) | **در حال سرو عمومی در Pages!** | **`0`** | **مصرف زنده = `0`** (فقط در اسکریپت آفلاین `scripts/audit_honar_1404_programs.py` روی `deploy`) | **بله — ۱۰۰٪ امن** |
| `docs/data/sanjesh_zaban_1404_programs.json` | `3,295,095 B` (`3.14 MiB`) | **در حال سرو عمومی در Pages!** | **`0`** | **مصرف زنده = `0`** (فقط در اسکریپت آفلاین `scripts/audit_zaban_1404_programs.py` روی `deploy`) | **بله — ۱۰۰٪ امن** |
| **جمع ۵ فایل ۱۴۰۴ در `main/docs/data/`** | **`19,413,812 B` (`18.51 MiB`)** | **هر ۵ فایل عمومی‌اند (`54,052` ردیف)** | **`0`** | **مصرف Runtime در لیارا = `0`** | **بله — حذف کامل از `main`** |
| `docs/data/sanjesh_riazi_1405_programs.json` | `4,145,106 B` (`3.95 MiB`) | روی `main` **وجود ندارد** (سرو نمی‌شود) | **`0`** | **ضروری در Runtime سرور** (`admission_exam_capacity.py:23` و `admission_capacity_record.py:25` از دیسک محلی کانتینر لیارا) | در Pages نیست؛ **در `deploy` حفظ شود** |
| `docs/data/sanjesh_tajrobi_1405_programs.json` | `4,955,859 B` (`4.73 MiB`) | روی `main` **وجود ندارد** (سرو نمی‌شود) | **`0`** | **ضروری در Runtime سرور** (`admission_exam_capacity.py:24` و `admission_capacity_record.py:26`) | در Pages نیست؛ **در `deploy` حفظ شود** |
| `docs/data/sanjesh_ensani_1405_programs.json` | `3,777,215 B` (`3.60 MiB`) | روی `main` **وجود ندارد** (سرو نمی‌شود) | **`0`** | **ضروری در Runtime سرور** (`admission_exam_capacity.py:25` و `admission_capacity_record.py:27`) | در Pages نیست؛ **در `deploy` حفظ شود** |
| `docs/data/sanjesh_honar_1405_programs.json` | `3,357,517 B` (`3.20 MiB`) | روی `main` **وجود ندارد** (سرو نمی‌شود) | **`0`** | **ضروری در Runtime سرور** (`admission_exam_capacity.py:26` و `admission_capacity_record.py:28`) | در Pages نیست؛ **در `deploy` حفظ شود** |
| `docs/data/sanjesh_zaban_1405_programs.json` | `3,314,123 B` (`3.16 MiB`) | روی `main` **وجود ندارد** (سرو نمی‌شود) | **`0`** | **ضروری در Runtime سرور** (`admission_exam_capacity.py:27` و `admission_capacity_record.py:29`) | در Pages نیست؛ **در `deploy` حفظ شود** |
| `docs/data/sanjesh_record_capacity_full.json` | `6,484,283 B` (`6.18 MiB`) | روی `main` **وجود ندارد** (سرو نمی‌شود) | **`0`** | **ضروری در Runtime سرور** (`admission_capacity_record.py:23` به‌عنوان fallback سوابق) | در Pages نیست؛ **در `deploy` حفظ شود** |

> **جمع‌بندی کلیدی کار ۲:** سرور لیارا (`main_v2.py`) هیچ دایرکتوری استاتیکی (`StaticFiles`) را روی وب mount نکرده است و فایل‌های `1405` و `record_capacity_full` را صرفاً از دیسک داخلی کانتینر می‌خواند. بنابراین **تنها محل افشای عمومی داده‌های خام سنجش در کل اینترنت، حضور ۵ فایل `1404_programs.json` (`19,413,812 B`) در شاخهٔ `main/docs/data/` است.**

---

## ۳. کار ۳ — طرح معماری حذف امن از انتشار عمومی (بدون اجرا در فاز صفر)

### ۳-۱. مقایسهٔ گزینه‌های معماری و انتخاب الگوی بهینه

- **انتخاب پیشنهادی: الگوی `A` — حذف کامل فایل‌های خام سنجش از `docs/data/` در شاخهٔ `main` (GitHub Pages) + نگه داشتن داده‌های ظرفیت `1405` منحصراً روی شاخهٔ سرور (`deploy`) همراه با گارد خودکار CI روی `main`.**
- **دلایل برتری قاطع الگوی `A` نسبت به `B` و `C`:**
  1. **ریسک صفر برای `api.asbe-siah.ir`:** شاخهٔ `deploy/liara-commercial-sandbox` اصلاً به GitHub Pages پابلیش نمی‌شود (`if: github.event_name == 'push' && github.ref == 'refs/heads/main'`) و FastAPI در `main_v2.py` فایل استاتیک سرو نمی‌کند؛ پس نگه داشتن `docs/data/sanjesh_*_1405_programs.json` روی دیسک کانتینر `deploy` هم هیچ افشای عمومی روی وب ندارد و هم نیاز به دست‌کاری فوری `admission_exam_capacity.py` / `admission_capacity_record.py` روی لیارا را به صفر می‌رساند.
  2. **کاهش ۹۸.۶٪ حجم `docs/data/` در GitHub Pages:** با حذف ۵ فایل `1404_programs.json` از `main/docs/data/`، حجم پوشهٔ دادهٔ عمومی سایت از **`19.69 MB`** به **`280 KB`** (`micro_motives.json` + `questions_v2.json` + `trait_map_v3.json`) کاهش می‌یابد (`-19,413,812 B`).
  3. **بررسی ۴ شرط ایمنی اجباری طرح:**
     - **`Publish frontend from main` نمی‌شکند:** این workflow فقط وجود `docs/index.html`، `docs/data.js`، `docs/data/micro_motives.json` و `docs/majors_catalog_ui_v1.json` را بررسی می‌کند و هیچ وابستگی‌ای به `sanjesh_*` ندارد.
     - **مسیرهای `exam` و `record` در `api.asbe-siah.ir` برای هر ۵ گروه (`riazi`, `tajrobi`, `ensani`, `honar`, `zaban`) دست‌نخورده می‌مانند:** چون `api.asbe-siah.ir` از دیسک داخلی کانتینر `deploy` فایل‌های `1405`، `sanjesh_record_capacity_full.json` و `program2s.json` را می‌خواند و هیچ درخواستی به GitHub Pages نمی‌فرستد.
     - **عدم وابستگی کش / Service Worker:** فایل `docs/sw.js` لیست Precache ندارد و هیچ فرضی مبنی بر وجود `sanjesh_*` در کنار `index.html` نمی‌کند.
     - **جداسازی صریح داده‌های ۱۴۰۵ سرور:** داده‌های `1405` و `record_capacity_full` صراحتاً به‌عنوان «دارایی داخلی کانتینر سرور در `deploy`» علامت‌گذاری می‌شوند و گارد جدید در `publish-frontend-from-deploy.yml` مانع ورود تصادفی هرگونه `docs/data/sanjesh_*` به `main` در آینده خواهد شد. *(در فاز بعدی سخت‌سازی بک‌اند، در صورت صلاحدید ناظر می‌توان مسیر داخلی روی `deploy` را هم از `ROOT/docs/data/` به `ROOT/server_data/sanjesh/` منتقل کرد تا نام پوشهٔ `docs/` دیگر روی بک‌اند باعث سوءتفاهم نشود.)*

### ۳-۲. چک‌لیست اجرایی فاز ۱ (۶ گام اتمیک — هر گام یک PR کوچک و مستقل با Rollback یک‌خطی)

| گام | شاخهٔ هدف | عنوان PR اتمیک | تغییر دقیق | معیار پذیرش (Acceptance Criteria) | فرمان Rollback فوری |
|:---:|---|---|---|---|---|
| **۱** | `main` | **حذف ۵ فایل خام `1404` از `docs/data/`** | `git rm docs/data/sanjesh_{riazi,tajrobi,ensani,honar,zaban}_1404_programs.json` | سبز شدن `Publish frontend from main` و `Purchase UI regression`؛ بازگرداندن کد `404` روی `https://asbe-siah.ir/data/sanjesh_riazi_1404_programs.json` پس از پابلیش؛ پاسخ `200` سالم روی `/api/v1/admission/chance` | `git revert <merge_sha>` روی `main` |
| **۲** | `main` | **نصب گیت محافظ ضدِافشا در CI فرانت‌اند** | افزودن گام `Verify no raw Sanjesh datasets in docs/` به `.github/workflows/publish-frontend-from-deploy.yml` (`! compgen -G "docs/data/sanjesh_*programs*.json"` و `! test -f docs/data/sanjesh_record_capacity_full.json`) | خطا دادن فوری CI در صورت تلاش اشتباه برای افزودن هر فایل `sanjesh_*` به `docs/`؛ سبز بودن کامل PR روی وضعیت تمیز | `git revert <merge_sha>` روی `main` |
| **۳** | `main` | **به‌روزرسانی سند حکمرانی مرجع حقیقت (`MAIN_BRANCH_GOVERNANCE.md`)** | ثبت رسمی سیاست مرز دقیق `main` (صرفاً فرانت عمومی + تست‌های JS) و `deploy/liara-commercial-sandbox` (کد اجرایی سرور، Alembic و داده‌های ظرفیت) | تأیید مستند مرجع حقیقت توسط ناظر و سبز ماندن CI | `git revert <merge_sha>` روی `main` |
| **۴** | `main` | **پاک‌سازی فایل‌های دادهٔ مردهٔ ریشهٔ `main` خارج از `docs/`** | حذف فایل‌های بزرگ بلااستفاده در ریشهٔ `main`: `program2s.json` (`8.58 MB` قدیمی)، `majors_database_v22.json` (`568 KB`)، `school_branches_v22.json` (`33 KB`) و `31032553.txt` (با حفظ کامل ۴ فایل مرجع تست‌های کاتالوگ JS یعنی `majors_database_v2.json`, `micro_motives.json`, `trait_map_v3.json`, `value_poles_v2.json`) | پاس شدن تمام `15/15` سوئیت `tests/test_*.js` و هر دو Workflow روی `main`؛ کاهش `9.18 MB` دیگر از حجم کاری مخزن | `git revert <merge_sha>` روی `main` |
| **۵** | `main` | **پاک‌سازی اسکریپت‌ها و تست‌های پایتون منسوخ ریشهٔ `main`** | حذف فایل‌های پایتونِ منسوخ و غیرمنطبق با پروداکشن از ریشهٔ `main` (`main_v2.py` قدیمی، `admission_chance_api.py` قدیمی، `admission_exam_capacity.py` ۱۴۰۴، `ai_counsel_service.py` قدیمی و تست‌های پایتون شکستهٔ ریشه) و درج `BACKEND_SOURCE_OF_TRUTH.md` | صفر شدن ابهام Split-Brain در ریشهٔ `main`؛ سبز ماندن ۱۰۰٪ تست‌های JS و Workflowهای `main` *(توجه: `dark_horse_engine_v2.py` در صورت نیاز صرفاً با تأیید جداگانهٔ ناظر دست می‌خورد)* | `git revert <merge_sha>` روی `main` |
| **۶** *(اختیاری — با مجوز جداگانه روی `deploy`)* | `deploy` | **جداسازی فیزیکی پوشهٔ `server_data/` روی سرور** | انتقال فایل‌های `1405` و `sanjesh_record_capacity_full.json` در شاخهٔ `deploy` از `docs/data/` به `server_data/sanjesh/` + به‌روزرسانی ثابت مسیر در `admission_exam_capacity.py` و `admission_capacity_record.py` | سبز شدن کامل `Commercial Backend CI` (`test_admission_capacity_record.py` و `test_exam_capacity*.py`) و `liara-runtime-lock.yml` | `git revert <merge_sha>` روی `deploy` |

---

## ۴. کار ۴ — اندازه‌گیری دقیق تگ‌های `<script>` در `docs/index.html` (صرفاً اندازه‌گیری، بدون Bundle)

### ۴-۱. خلاصهٔ عددی دقیق بوت فعلی صفحهٔ خانه
- **تعداد کل تگ‌های `<script>` در `docs/index.html`:** **`29` تگ**
  - **`2` اسکریپت درون‌خطی (`Inline <script>` در `<head>`):** جمعاً **`3,073 B` (`3.0 KB`)**
  - **`27` اسکریپت خارجی (`<script defer src="...">`):** جمعاً **`693,040 B` (`676.8 KB` Uncompressed)**
- **مجموع کل جاوااسکریپت واکشی و پارس‌شده در بارگذاری اول خانه:** **`696,113 B` (`679.8 KB`)**

### ۴-۲. جدول کامل ۲۹ تگ اسکریپت و دسته‌بندی اولویت Lazy-Load برای فازهای بعدی

> **یافتهٔ مهم معماری در `docs/shell.js:619-626`:** پوستهٔ خانه (`renderHome`) از قبل برای متدهای پیش‌نمایش چهار ماژول فرعی (`DHSparkGame.peek`، `DHStories.peek`، `DHPoems.peek`، `DHParents.peek`) مقادیر پیش‌فرض ایمن دارد و فقط هنگام کلیک کاربر متد `.open()` / `openHome()` را صدا می‌زند. بنابراین Lazy-Load کردن ماژول‌های فرعی در فاز بعد نیازی به بازنویسی معماری خانه ندارد (تنها باید تست‌های قراردادی رجکس تگ‌های `index.html` در `tests/` هم‌زمان به‌روزرسانی شوند).

| ردیف | نوع | نام فایل در `docs/index.html` | حجم دقیق (بایت) | سهم از کل JS | طبقهٔ ضرورت در First Paint خانه | اولویت Lazy-Load در فاز بعد |
|:---:|:---:|---|---:|---:|---|---|
| ۱ | Inline | `<head>` اسکریپت ۱ (تم و آماده‌سازی اولیهٔ نمایش) | `770 B` | `0.1%` | **ضروری برای First Paint** | حفظ در `<head>` (غیرقابل تعویق) |
| ۲ | `defer` | `payment_hop_boot.js` | `3,571 B` | `0.5%` | **ضروری (جهش بازگشت بانک)** | حفظ در بوت اولیه |
| ۳ | Inline | `<head>` اسکریپت ۲ (`__dhRequestStartupJourney` / `Sanjesh` queue) | `2,303 B` | `0.3%` | **ضروری برای First Paint تعاملی** | حفظ در `<head>` (صف کلیک قبل از بوت) |
| ۴ | `defer` | `quotes_darkhorse.js` | `6,067 B` | `0.9%` | **ضروری برای محتوای خانه** (`DHQuote.todayBundle`) | حفظ در بوت اولیه |
| ۵ | `defer` | `auth_api_client.js` | `9,714 B` | `1.4%` | **ضروری برای پوسته/وضعیت کاربر** | حفظ در بوت اولیه |
| ۶ | `defer` | `quota_state_reconciler.js` | `4,378 B` | `0.6%` | **ضروری برای گیت تجاری P0** | حفظ در بوت اولیه |
| ۷ | `defer` | `shell_runtime_fix.js` | `2,596 B` | `0.4%` | **ضروری برای پوستهٔ خانه** | حفظ (قابل ادغام در `shell.js` در فاز تجمیع) |
| ۸ | `defer` | `shell.js` | `75,971 B` | `10.9%` | **ضروری برای رندر اصلی خانه و تب‌بار** | حفظ در بوت اولیه |
| ۹ | `defer` | `quota_runtime.js` | `24,942 B` | `3.6%` | **ضروری برای گیت سهمیه P0** | حفظ در بوت اولیه |
| ۱۰ | `defer` | `commercial_ui.js` | `55,574 B` | `8.0%` | **ضروری برای CTA شروع سفر / خرید / ورود** | حفظ در بوت اولیه |
| ۱۱ | `defer` | `external_links_fix_v1.js` | `4,296 B` | `0.6%` | **سبک — محافظ لینک‌های خارجی PWA** | حفظ در بوت اولیه |
| ۱۲ | `defer` | `purchase_ui_fix.js` | `9,348 B` | `1.3%` | **مرتبط با گیت خرید P0** | حفظ در بوت اولیه (حساسیت P0) |
| ۱۳ | `defer` | `payment_return_reconcile.js` | `4,007 B` | `0.6%` | **ضروری هنگام بازگشت از درگاه پرداخت** | حفظ یا بارگذاری شرطی با پارامتر URL |
| ۱۴ | `defer` | `post_auth_flow_policy.js` | `6,440 B` | `0.9%` | **سیاست پس از احراز هویت** | حفظ در بوت اولیه |
| ۱۵ | `defer` | `pwa-boot.js` | `4,543 B` | `0.7%` | **ضروری برای ثبت و ارتقای SW** | حفظ در بوت اولیه |
| ۱۶ | `defer` | `admission_chance_ui.js` | `54,061 B` | **`7.8%`** | **غیرضروری در First Paint خانه** (فقط بخش سنجش) | **موج ۱ Lazy-Load (بالاترین اثر تک‌فایلی — بارگذاری با کلیک روی «سنجش»)** |
| ۱۷ | `defer` | `poems.js` | `25,284 B` | **`3.6%`** | **غیرضروری در First Paint خانه** (فقط ماژول اشعار) | **موج ۱ Lazy-Load (بارگذاری با کلیک روی کارت «حکمت و شعر»)** |
| ۱۸ | `defer` | `spark_game.js` | `18,452 B` | **`2.7%`** | **غیرضروری در First Paint خانه** (فقط مینی‌گیم جرقه‌یاب) | **موج ۱ Lazy-Load (بارگذاری با کلیک روی کارت «جرقه‌یاب» یا `requestIdleCallback`)** |
| ۱۹ | `defer` | `profile_ux_v1.js` | `17,308 B` | **`2.5%`** | **غیرضروری در First Paint خانه** (فقط تب پروفایل) | **موج ۱ Lazy-Load (بارگذاری با ورود به تب «پروفایل»)** |
| ۲۰ | `defer` | `stories.js` | `16,408 B` | **`2.4%`** | **غیرضروری در First Paint خانه** (فقط ماژول روایت‌ها) | **موج ۱ Lazy-Load (بارگذاری با کلیک روی کارت «داستان‌های اسب سیاه»)** |
| ۲۱ | `defer` | `parents.js` | `10,407 B` | **`1.5%`** | **غیرضروری در First Paint خانه** (فقط میثاق والدین) | **موج ۱ Lazy-Load (بارگذاری با کلیک روی کارت «سخنی با والدین»)** |
| ۲۲ | `defer` | `admin_feedback_ui_v1.js` | `9,165 B` | **`1.3%`** | **غیرضروری برای ۹۹.۹٪ کاربران عادی** (پنل ادمین) | **موج ۱ Lazy-Load (بارگذاری صرفاً اگر `user.role === 'admin'`)** |
| ۲۳ | `defer` | `feedback_bridge.js` | `8,249 B` | **`1.2%`** | **غیرضروری در First Paint خانه** (بازخورد پایان آزمون) | **موج ۱ Lazy-Load (پس از تکمیل سفر)** |
| ۲۴ | `defer` | `password_reset_ui.js` | `7,548 B` | **`1.1%`** | **غیرضروری در First Paint خانه** (فقط فراموشی رمز) | **موج ۱ Lazy-Load (هنگام کلیک روی «فراموشی رمز عبور»)** |
| ۲۵ | `defer` | `data.js` | `84,480 B` | **`12.1%`** | **غیرضروری برای First Paint خانه** (موردنیاز در شروع سفر / جرقه‌یاب) | **موج ۲ Lazy-Load / Idle Prefetch (`requestIdleCallback` پس از First Paint خانه)** |
| ۲۶ | `defer` | `app.js` | `212,334 B` | **`30.5%`** | **موتور شهر رؤیاها و نتایج** (در لحظهٔ نمایش اولیهٔ خانه اجرا نمی‌شود) | **موج ۲ Idle Prefetch** (با دقت بالا به دلیل اشتراک `state` سراسری با `shell.js`) |
| ۲۷ | `defer` | `journey_experience.js` | `12,894 B` | **`1.9%`** | **مکمل تجربهٔ داخل سفر** | **موج ۲ (همراه با `app.js`)** |
| ۲۸ | `defer` | `ux_v2_patch.js` | `3,601 B` | `0.5%` | **پچ تکمیلی رابط سفر** | **موج ۲ (همراه با `app.js`)** |
| ۲۹ | `defer` | `genz_results_enhance.js` | `1,402 B` | `0.2%` | **فقط در صفحهٔ نتایج** | **موج ۲ (هنگام رندر نتایج)** |

#### جمع‌بندی بازده Lazy-Load برای فاز بعد:
- **موج ۱ (۹ ماژول کاملاً مستقل از خانه و سفر):** صرفه‌جویی فوری **`166,882 B` (`24.0%` کل JS)** با ریسک نزدیک به صفر.
- **موج ۲ (پیش‌بارگذاری پس‌زمینهٔ موتور سفر پس از First Paint خانه):** صرفه‌جویی مجموعاً **`481,593 B` (`69.2%` کل JS در مسیر بحرانی رندر اولیه)**.

---

## ۵. جمع‌بندی نهایی فاز صفر: توصیهٔ `Go / No-Go` و جدول ریسک‌ها

### ۵-۱. توصیهٔ رسمی به ناظر: **`GO` مشروط و مرحله‌به‌مرحله برای شروع فاز ۱ (بستهٔ ۱ — گام‌های ۱ تا ۵ روی `main`)**
- تمامی ابهامات برطرف شده و با اثبات خط‌به‌خط کد مسجل گردید که ۵ فایل `docs/data/sanjesh_*_1404_programs.json` (`19.41 MB`) در فرانت‌اند **`0`** مصرف‌کننده و در بک‌اند زندهٔ لیارا (`deploy`) نیز **`0`** مصرف‌کنندهٔ زمان اجرا دارند؛ بنابراین اجرای گام ۱ تا ۵ فاز ۱ روی شاخهٔ `main` کاملاً ایمن، اتمیک و بدون کوچک‌ترین اثر جانبی بر امتیازدهی، سهمیه یا API ظرفیت زنده است.

### ۵-۲. جدول ریسک‌ها و راه برگشت (یک خط برای هر ریسک)

1. **ریسک ۱ — حذف اشتباهی فایل‌های دادهٔ فعال فرانت (`micro_motives.json`, `questions_v2.json`, `trait_map_v3.json`, `majors_catalog_ui_v1.json`) به‌همراه فایل‌های سنجش:** در گام ۱ فقط ۵ مسیر صریح `docs/data/sanjesh_*_1404_programs.json` حذف می‌شوند و CI موجود (`publish-frontend-from-deploy.yml`) وجود تک‌تک فایل‌های فعال را چک می‌کند؛ **راه برگشت:** `git revert <merge_sha>` روی `main` و بازنشر خودکار Pages در کمتر از ۶۰ ثانیه.
2. **ریسک ۲ — کپی ناخواستهٔ فایل‌های `1405` یا `sanjesh_record_capacity_full.json` از `deploy` به `main` در آینده:** با افزودن گیت محافظ در گام ۲ به `.github/workflows/publish-frontend-from-deploy.yml` هرگونه ورود فایل `sanjesh_*` به `docs/` در سطح PR مسدود می‌شود؛ **راه برگشت:** `git revert <merge_sha>` در صورت نیاز به تغییر قاعدهٔ workflow.
3. **ریسک ۳ — دست‌کاری ناخواستهٔ فایل‌های ظرفیت `1405` روی شاخهٔ زندهٔ `deploy/liara-commercial-sandbox`:** در فاز ۱ هیچ تغییری روی شاخهٔ `deploy` اعمال نمی‌شود تا `/api/v1/admission/chance` (`exam` + `record`) صددرصد دست‌نخورده بماند؛ **راه برگشت:** در صورت اجرای اختیاری گام ۶ در آینده، استقرار مجدد تگ قبلی `deploy` (`537a00ae`) در لیارا.
4. **ریسک ۴ — حذف اشتباه فایل‌های JSON ریشهٔ `main` که مورد نیاز تست‌های JS کاتالوگ هستند (`majors_database_v2.json` و غیره):** در گام ۴ صرفاً فایل‌های تاییدشدهٔ بدون ارجاع (`program2s.json`, `majors_database_v22.json`, `school_branches_v22.json`) حذف می‌شوند و اجرای کامل ۱۵ سوئیت `tests/test_*.js` پیش از Merge الزامی است؛ **راه برگشت:** `git revert <merge_sha>`.
5. **ریسک ۵ — باقی ماندن فایل‌های قدیمی در کش CDN مرورگر برای کاربران قبلی:** چون کلاینت هرگز این فایل‌ها را کش یا درخواست نکرده است، حذف از GitHub Pages بلافاصله دسترسی عمومی URL را به `404` تبدیل می‌کند؛ **راه برگشت:** `git revert <merge_sha>`.
