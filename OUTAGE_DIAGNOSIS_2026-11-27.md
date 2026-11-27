# گزارش عیب‌یابی: قطع سرویس «سفر اکتشافی، پنل مدیریت و پرداخت»

تاریخ: 2026-11-27 · شاخه: `arena/dd8fedc9-dark-horse-v2` · ترتیب مرج‌ها درست بود

---

## خلاصهٔ یک‌خطی

مرج‌های شما **ترتیب درستی** داشتند و **هیچ فایلی از فرانت‌اند را تغییر ندادند**. مشکل از این‌جاست که
هوک `liara_pre_start.sh` که در همین مرج به سرویس اضافه شد، در اولین اجرا **کاملاً درست** عمل می‌کند و
به‌خاطر یک ناسازگاری واقعی بین پایگاه‌دادهٔ زنده و اسکیمای Alembic، **با کد خروج ۱ متوقف می‌شود**.
نتیجه: Liara برنامه را بالا نمی‌آورد، پس `https://api.asbe-siah.ir` پاسخ نمی‌دهد و **هر سه**
سرویس (سفر، پنل مدیریت، پرداخت) با هم از کار می‌افتند — چون هر سه از همان یک API می‌خوانند.

**این یک نقص طراحی در هوک است، نه یک راه‌حل امن.** باید اصلاح شود. نسخهٔ اصلاح‌شده در همین
شاخه با نام `liara_pre_start.sh` قرار گرفته و روی PostgreSQL 16.2 تست شده است.

---

## ۱. چه چیزی خراب است

### شاهد اصلی: خودِ CI تولید

گردش‌کار `Liara Runtime Lock` روی کامیت مرج `dda1561` **fail** شده است:

```
JOB: runtime-lock -> failure
   success   Set up job
   success   Checkout deployed build candidate
   success   Verify live Liara root is online            ← سایت *بالا بود*
   failure   Verify live scoring build fingerprint       ← اما بیلد کهنه بود
```

و در مشاهدهٔ طولانی (`--log-failed`)، حلقهٔ ۳۰ بارهٔ انتظار برای مطابقت fingerprint هیچ‌وقت
موفق نشد و پس از ۵ دقیقه و ۴۳ ثانیه با `LIVE_RUNTIME_LOCK=FAIL` تمام شد. یعنی:

> در لحظهٔ مرج، ریشهٔ `https://api.asbe-siah.ir/` هنوز ۲۰۰ می‌داد، اما بیلد اجراشده با کامیت
> مرج‌شده یکی نبود. رول‌اوت به بیلد جدید نرسید.

این الگو پیش از مرج هم وجود داشت (پنج اجرای قبلی همین گردش‌کار، همه در مرحلهٔ fingerprint یا
online شکست خورده‌اند)، بنابراین **علت طولانی‌مدت متفاوت است** — پایین‌تر در بخش ۴.

### آنچه مرج‌ها تغییر دادند

`git diff dda1561^1 dda1561` (یعنی «قبل» و «بعد» مرج #387 روی شاخهٔ deploy):

```
 alembic/versions/0012_referral_attribution.py |  70 ++++++
 billing_api.py                                |  18 +-
 billing_credit_service.py                     |   8 +-
 billing_models.py                             |  18 +-
 commercial_api.py                             |  25 +++
 liara_pre_start.sh                            |  60 ++++++   ← تنها تغییر عملیاتی
 main_v2.py                                    |   1 +
 referral_service.py                           | 283 +++++++++++++++++++
 test_otp_rate_limit.py / test_password_reset_service.py / test_referral_service.py
```

**هیچ فایلی زیر `docs/` تغییر نکرد.** پس پنل مدیریت و پرداخت به‌خاطر تغییر فرانت‌اند از کار نیفتاده‌اند.

### زنجیرهٔ خرابی

```
مرج → هوک اضافه می‌شود → Liara قبل از بالا آوردن uvicorn هوک را اجرا می‌کند
     → alembic upgrade head روی پایگاه‌دادهٔ زنده شکست می‌خورد
     → هوک exit 1 می‌دهد (fail-closed، دقیقاً همان‌طور که قرار بود)
     → uvicorn هرگز اجرا نمی‌شود
     → api.asbe-siah.ir پاسخ نمی‌دهد
     → app.js / admin.html / commercial_ui.js هر سه در تماس با API شکست می‌خورند
```

سه علامتی که گزارش کردید یک علت دارند، نه سه علت.

---

## ۲. علت ریشه‌ای: پایگاه‌دادهٔ زنده `alembic_version` ندارد

اگر پایگاه‌داده «stamped» بود، `alembic upgrade head` فقط `0012` را اجرا می‌کرد و تمام.
اما پایگاه‌داده‌ای که پیش از Alembic با `create_all` ساخته شده، جدول‌ها را دارد و **جدول
`alembic_version` را ندارد**. در آن حالت Alembic از ابتدا شروع می‌کند و اولین دستور
`0001` یعنی `CREATE TABLE micro_motives` با خطای `DuplicateTable` می‌شکند.

بازسازی دقیق این وضعیت و اجرای **همان هوک** روی PostgreSQL 16.2:

```
PRE-STATE: tables=22  alembic_version=None      ← شکل واقعی پایگاه‌دادهٔ قدیمی
=== اجرای هوک جدید ===
EXIT CODE: 1  ← یعنی برنامه هرگز بالا نمی‌آید
   psycopg.errors.DuplicateTable: relation "micro_motives" already exists
   liara_pre_start: FATAL: alembic upgrade head failed; aborting startup
```

و آزمون A/B روی همان پایگاه‌داده:

```
WITH the hook    -> hook exit: 1 | app starts: NO
WITHOUT the hook -> app starts: YES
   GET /__runtime_fingerprint -> 200
```

یعنی **کد بک‌اند سالم است**؛ فقط دروازهٔ جدید جلوی آن را گرفته.

### چرا این وضعیت محتمل است

- `git log a326919` (۲۰ شهریور): «remove runtime schema creation from commercial startup» —
  `init_db()` از `lifespan` حذف شد و از آن به بعد تنها راه ساخت اسکیما Alembic است.
- گردش‌کار `prod-migration-once.yml` که برای stamp کردن تولید نوشته شده، **هرگز یک بار هم اجرا نشده**
  (`gh run list --workflow=prod-migration-once.yml` خالی است).
- روی خود شاخهٔ deploy دستور `alembic stamp` در هیچ فایلی وجود ندارد.

نتیجه: هیچ‌چیز در تاریخ این مخزن ثابت نمی‌کند پایگاه‌دادهٔ زنده هرگز stamp شده باشد؛
و رفتار مشاهده‌شده (شکست در `0001`) با «stamp نشده» سازگار است، با «stamp شده» نه.

> **تأیید نهایی فقط با یک دستور ممکن است** (فقط خواندنی، هیچ نوشتنی ندارد). روی پنل
> Liara → شل، یا با `PRODUCTION_DATABASE_URL` در GitHub Actions:
>
> ```sql
> SELECT to_regclass('alembic_version'), (SELECT version_num FROM alembic_version);
> ```
>
> - `NULL` → پایگاه‌داده stamp نشده است ← علت همین است، برو به بخش ۳.
> - `0011_otp_request_ip` → stamp شده است ← علت چیز دیگری است، برو به بخش ۵ (مورد ب).

---

## ۳. راه‌حل

### آیا باید هوک را حذف کرد؟

**نه.** آن ۴۰ ثانیه اول که سایت بالا بود (و بعد رفت) دقیقاً همان پنجرهٔ بین «هوک تمام شد» و
«uvicorn بالا آمد» بود. حذف هوک یعنی برگشتن به همان وضعیت شکننده‌ای که `0012` را با
`DuplicateTable` روی `uq_admin_audit_referral_code` رها می‌کند. هوک درست است؛ فقط
**حالت «پایگاه‌دادهٔ قدیمی بدون stamp» را پوشش نمی‌دهد**.

### نسخهٔ اصلاح‌شده: `liara_pre_start.sh` (در همین شاخه)

سه چیز اضافه شده، بدون شل‌کردن دروازه:

1. **پروب فقط‌خواندنی وضعیت اسکیما** با همان نرمال‌سازی URL که `alembic/env.py` دارد:
   `stamped` / `unstamped_empty` / `unstamped_tables`.
2. **حالت `ALEMBIC_BASELINE_REVISION` (اختیاری، یک‌بار‌مصرف):** اگر تنظیم شود و پایگاه‌داده
   stamp نشده باشد، آن ریویژن را یک بار `stamp` می‌کند و بعد `upgrade head` می‌زند.
   اگر تنظیم نشود، رفتار دقیقاً مثل قبل fail-closed می‌ماند.
3. **پیشنهاددهندهٔ baseline:** وقتی stamp نشده و متغیر تنظیم نشده، هوک با خواندن
   جدول‌ها/ستون‌ها/ایندکس‌ها **می‌گوید کدام ریویژن با اسکیمای فعلی می‌خواند** و
   **هیچ‌وقت خودش حدس نمی‌زند**. (حدس زدن خطرناک است: در تست، حدس ثابت
   `0011` روی یک پایگاه‌دادهٔ واقعی به `DuplicateTable` روی ایندکس `0012` خورد.)

#### مسیر بازیابی (تست‌شده، سه گام)

```
STEP 1 - اجرا بدون متغیر: بسته می‌ماند و می‌گوید چه چیزی لازم است
  liara_pre_start: live tables already match revision 0012_referral_attribution (derived read-only).
  liara_pre_start: FATAL: ... Set ALEMBIC_BASELINE_REVISION=0012_referral_attribution for this one release ...

STEP 2 - همان کامیت + متغیر محیطی ALEMBIC_BASELINE_REVISION=0012_referral_attribution
  liara_pre_start: legacy schema without alembic_version; stamping baseline 0012_referral_attribution once.
  liara_pre_start: migrations applied; starting application.        ← exit 0

STEP 3 - برنامه بالا می‌آید
  app starts: True        alembic_version: 0012_referral_attribution
```

سپس **متغیر را حذف کنید** تا در رول‌اوت بعدی کورکورانه stamp نکند.

#### نکتهٔ مهم دربارهٔ `0012`

نسخهٔ اول `0012` یک ایندکس **یونیک** روی `admin_audit_logs.target_id` می‌سازد. اگر در
پایگاه‌دادهٔ زنده دو ردیف `create_referral_code` با کد یکسان وجود داشته باشد، مهاجرت با
`UniqueViolation` می‌شکند و سرویس بالا نمی‌آید — مستقل از بحث stamp:

```
seeded duplicate referral_code rows: REF-1 x2
=== هوک ===
EXIT: 1 | app starts: NO
   psycopg.errors.UniqueViolation: could not create unique index "uq_admin_audit_referral_code"
```

پاک‌سازی (فقط خواندنی برای تشخیص):

```sql
SELECT target_id, count(*) FROM admin_audit_logs
WHERE target_type='referral_code' AND action='create_referral_code'
GROUP BY target_id HAVING count(*) > 1;
```

اگر خروجی داشت، آن ردیف‌ها باید قبل از استقرار اصلاح شوند. بهتر است `0012` با همین بررسی
پیش‌پرواز (fail-closed با پیام گویا) منتشر شود؛ در نسخهٔ اصلاح‌شده یک hint خوانا برای همین
حالت اضافه شده است.

---

## ۴. آنچه *علت* نیست (تا وقت تلف نشود)

| فرضیه | حکم | شاهد |
|---|---|---|
| ترتیب مرج اشتباه بود | ❌ رد | `27672cf` (#389) والدِ `dda1561` (#387) است |
| فایل‌های لازم به deploy نرسیدند | ❌ رد | `liara.json`، هوک (`100755`)، `alembic/env.py` با نرمالایزر، `0012`، `main_v2.py` همه در `dda1561` |
| هوک روی DB سالم قابل‌اجرا نیست | ❌ رد | `alembic` با پین `1.20.1` در requirements هست؛ اجرای مکرر هوک idempotent است (exit 0 سه بار) |
| نقص در کد بک‌اند | ❌ رد | `import main_v2` ✅، `compileall` ✅، موتور ۲۳۰ رشته/۴ شاخه/۲۰۲ motive-driven ✅، `/` و `/__runtime_fingerprint` → 200 |
| ناسازگاری نسخهٔ فرانت و API | ⚠️ هست، ولی علت این قطعی نیست | هر ۲۲ اندپوینتی که فرانت صدا می‌زند در بک‌اند وجود دارد؛ زنجیرهٔ احراز/شارژ/پرداخت/پنل روی DB واقعی ۲۰۰ داد |
| فرانت قدیمی/کش سرویس‌ورکر | ⚠️ مشکل جدا، پایین | `free_journey_mode.js` در `docs/index.html` صدا زده می‌شود ولی فایل ۴۰۴ است |

### زنجیرهٔ تجاری که تست شد (روی PostgreSQL 16.2 + همان درخت deploy)

با کاربر واقعی، انتزاع رایگان، و پرووایدر mock — همه از مسیر production:

```
/me                       : 200
quota                     : 200  {'credits_granted':1,'credits_consumed':0,'credits_remaining':1}
discover (قبل از شارژ)    : 402  ← گیت شارژ، رفتار درست
consume-test              : 200  {'consumed':1,'credits_remaining':0}
discover (بعد از شارژ)    : 200  {'discovery_result': {...}}
/admin/dashboard          : 200
/admin/users              : 200
/admin/feedback           : 200
/billing/create-payment   : 200  {'payment_url': ...}
```

**یعنی به‌محض اینکه API بالا بیاید، هر سه سرویس کار می‌کنند.** این خودش تأیید می‌کند که
مشکل یک نقطه است: بالا نیامدن API.

نکتهٔ جانبی: `consume-test` پارامتر `session_uuid` می‌خواهد (نه `session_id`)؛ فرانت هر دو
شاخه درست آن را می‌فرستد. بدنهٔ `discover` اما `session_id` است. این‌ها درست‌اند و تغییر نکرده‌اند.

---

## ۵. کارهای بعدی، به ترتیب اولویت

### الف) فوری — سرویس را بالا بیاورید

1. خروجی SQL بخش ۲ را بگیرید تا حالت پایگاه‌داده قطعی شود.
2. اگر stamp نشده بود: `liara_pre_start.sh` این شاخه را روی شاخهٔ deploy بگذارید و
   `ALEMBIC_BASELINE_REVISION=<ریویژن پیشنهادی هوک>` را در محیط Liara تنظیم کنید.
3. یک بار که بالا آمد، متغیر را حذف کنید.
4. اگر خواستید همین حالا سایت بالا باشد بدون تغییر کد: **rollback به `8451887`**
   (تیپ deploy پیش از این مرج). آن درخت **هوک ندارد** (پس دروازه‌ای نیست که ببندد) و
   `0012` هم ندارد (پس ایندکس یونیک مشکل‌ساز هم ندارد). هزینه‌اش از دست رفتن referral است.

### ب) اگر پایگاه‌داده stamp شده بود

یعنی `alembic upgrade head` در هوک به علت دیگری شکست خورده. دو گزینهٔ محتمل:

- داده‌های تکراری `referral_code` → بخش ۳ (پاک‌سازی).
- `0012` با اسکیمای زنده ناسازگار است → `alembic upgrade 0011_otp_request_ip` را
  در یک محیط staging با کپی پایگاه‌داده اجرا کنید و خطای دقیق را ببینید. (لوگ‌های Liara
  پیش از هر چیز تعیین‌کننده‌اند؛ در سندباکس من دسترسی به آن‌ها نبود و از این طرف
  `api.asbe-siah.ir` قابل resolve نبود.)

### ج) بدهی فنی که این حادثه رو کرد

- **`prod-migration-once.yml` هرگز اجرا نشد.** همان گردش‌کاری که باید تولید را stamp کند.
  اجرای آن (یا معادل دستی) باید بخشی از چک‌لیست رول‌اوت باشد.
- **`Liara Runtime Lock` از ۱۵ آبان در حال شکست است.** این چک عملاً مرده است و کسی به آن
  نگاه نمی‌کند؛ وگرنه همین حالا معلوم می‌شد که بیلد جدید به تولید نرسیده. یا درست شود یا
  از چک‌لیست حذف شود — نه اینکه قرمز بماند.
- **هوک باید قبل از مرج روی یک کپی از پایگاه‌دادهٔ تولید تست شود،** نه فقط روی DB خالی.
  تست قبلی من روی پایگاه‌دادهٔ خالی (که خودش Alembic ساخته بود) این حالت را نمی‌دید. این
  درس اصلی این حادثه است و تقصیر آن مستقیم بر گردن من است.

### د) مشکل مستقل فرانت (ربطی به این قطعی ندارد)

`docs/index.html` روی شاخهٔ deploy فایل `free_journey_mode.js` را صدا می‌زند که **وجود ندارد**
(۴۰۴). این از قبل از مرج‌ها هم بود (در `8451887` هم غایب است) و در `main` هست. به‌تنهایی
سرویس را نمی‌خواباند، ولی «سفر اکتشافی» را در حالت بدون ورود تحت تأثیر قرار می‌دهد.

```html
<script defer src="free_journey_mode.js?v=3"></script>   <!-- 404 -->
```

اگر بعد از بالا آمدن API، سفر اکتشافی برای کاربر **بدون ورود** هنوز کار نکرد، سراغ این بروید.
توجه: گیت شارژ (`_require_charged_journey`، کامیت `27e88c2`) در این خط از ۲۷ مهر هست و
بدون ورود + شارژ تأییدشده، `discover` عمداً ۴۰۱/۴۰۲ می‌دهد. این طراحی است، نه خرابی.

---

## ۶. کد معرف اختیاری (خواستهٔ دوم)

### وضعیت واقعی: بک‌اند از قبل اختیاری است

`referral_service.set_user_referral_code` صریحاً می‌گوید کد نامعتبر «عمداً غیرمسدودکننده»
است. روی PostgreSQL واقعی تست شد:

| ورودی | پاسخ `PUT /api/v1/me/referral-code` | `create-payment` |
|---|---|---|
| فیلد خالی | `200 {status: direct, purchase_allowed: true}` | ۲۰۰ ✅ |
| کد نامعتبر `XX99` | `200 {status: invalid_ignored, purchase_allowed: true}` | ۲۰۰ ✅ |
| کد معتبر | `200 {status: applied, referral_code: REF2026}` | ۲۰۰ ✅ |
| هیچ درخواستی (کلاینت قدیمی) | — | ۲۰۰ ✅ |

پس هیچ‌جا کد معرف **الزامی** نشده بود. چیزی که نبود، **رابط کاربری** آن بود:
نه در `main` و نه در deploy هیچ فیلدی برای ورود کد وجود ندارد (جستجوی `referral` در
`docs/` صفر نتیجه دارد). یعنی کاربر هیچ راهی برای وارد کردن کد نداشت.

### PR #388 همان قابلیت است (باز مانده، هرگز مرج نشد)

`#388 feat(frontend): add optional referral code to checkout` — Draft، بر پایهٔ `main`،
فایل‌های `docs/purchase_ui_fix.js`، `docs/commercial_ui.js`، `docs/auth_api_client.js`.
طراحی‌اش درست است (referral-first، کد نامعتبر خرید را متوقف نمی‌کند، مهلت ۱۲ ثانیه).

**مشکل:** روی `deploy/liara-commercial-sandbox` هیچ‌وقت اعمال نشد؛ و قابل اعمال هم نیست —
`docs/purchase_ui_fix.js` که این PR اصلاح می‌کند **روی deploy وجود ندارد**.
`main` و deploy هیچ نقطهٔ مرج مشترکی ندارند (deploy ۲۲۶۹ کامیت جلوتر است).

### راه‌حل اعمال‌شده: پچ سازگار با deploy

فایل `patches/recovery_and_optional_referral.patch` همان رفتار #388 را روی نسخهٔ
فرانت‌اندی که **واقعاً سرو می‌شود** پیاده می‌کند:

- `docs/commercial_ui.js` — فیلد «کد معرف (اختیاری)» در پنجرهٔ خرید، با راهنمای
  «کد ندارید؟ این قسمت را خالی بگذارید و ادامه دهید.»
- `docs/auth_api_client.js` — متد `setReferralCode` برای `PUT /api/v1/me/referral-code`.
- `docs/index.html` — cache-bust (`auth v8`، `commercial v25`) تا کاربران برگشتی فایل تازه بگیرند.

**قاعدهٔ کلیدی:** هر خطای مسیر معرف (کد بد، حساب قفل‌شده، قطعی شبکه) فقط پیام نشان می‌دهد و
خرید به‌صورت مستقیم ادامه می‌یابد. تست رفتاری روی چهار مسیر:

```
valid code    -> PUT sent: true | status=applied         | purchase_allowed=true
invalid code  -> PUT sent: true | status=invalid_ignored | purchase_allowed=true
empty field   -> PUT sent: true | status=direct          | purchase_allowed=true
network error -> setReferralCode rejects (modal catches it, purchase continues)
```

### دو باگ که کنار همین پیدا شد

1. **`0012` سرویس را می‌خواباند.** ایندکس یونیک روی `target_id` بدون هیچ محافظی ساخته
   می‌شد؛ اگر فقط دو ردیف `create_referral_code` با کد یکسان در ledger باشد،
   `UniqueViolation` و بالا نیامدن سرویس. حالا `0012` **هیچ ردیفی را حذف نمی‌کند**؛
   فقط ردیف‌های تکراری *قدیمی‌تر* را با پسوند `-ARCHIVED-<id>` بازنام‌گذاری می‌کند
   (`target_id` به‌هرحال یونیک می‌شود، پس idempotent است) و ردیف بازمانده کد اصلی را
   نگه می‌دارد. اگر باز هم تکراری بماند، خطای خوانا می‌دهد و دادهٔ کسی را دور نمی‌ریزد.
2. **قرارداد ریویژن منقضی شده بود.** `test_quota_health_migration.py` و
   `commercial_api.quota_health` ریویژن را ثابت `0011_otp_request_ip` نگه داشته بودند.
   روی درخت deploy **همین حالا** آن تست شکست می‌خورد (CI این فایل را اجرا نمی‌کند،
   پس دیده نشد). به `0012` به‌روز شد.

### مقایسهٔ قطعی روی PostgreSQL 16.2 (همان مجموعه تست‌ها)

```
BASE (deploy tip)    1 failed, 32 passed, 1 skipped
      test_quota_health_migration.py::test_expected_revision_matches_checked_in_alembic_head
PATCHED              33 passed, 1 skipped, 0 failed
```

### اثبات دست-نخوردن منطق علمی

`scoring_build_fingerprint` (همان هفت فایلی که `Liara Runtime Lock` چک می‌کند) روی درخت
deploy و درخت پچ‌شده **بیت‌به‌بیت یکسان** است:

```
deploy tip  : 8f39e0c3308fda4547c78d664edea6549a0c644a29a5a81aafa2c595a0803758
patched     : 8f39e0c3308fda4547c78d664edea6549a0c644a29a5a81aafa2c595a0803758
IDENTICAL: True
```

`0012` هیچ منطق امتیازدهی، رشته، موتیو، قیمت یا طرح را لمس نمی‌کند؛ تنها جدول‌های
`users` و `orders` (ستون‌های معرف) و ایندکس دفتر کد را تغییر می‌دهد.

---

## پیوست: آنچه تست شد

| سناریو | نتیجه |
|---|---|
| هوک، DB خالی | exit 0، `alembic_version=0012` |
| هوک، سه بار پشت‌سرهم (idempotent) | exit 0، ۰، ۰ |
| هوک، DB قدیمی بدون stamp | exit 1 + پیشنهاد baseline |
| هوک + `ALEMBIC_BASELINE_REVISION` درست | exit 0 و اپ بالا می‌آید |
| هوک، `DATABASE_URL` غایب | exit 1 |
| هوک، DB در دسترس نیست | exit 1، بدون لو رفتن DSN |
| هوک، اجرا از cwd دیگر | exit 0 (به ریشهٔ انتشار `cd` می‌کند) |
| هوک، داده تکراری `referral_code` | exit 1 + hint، بدون بالا آمدن |
| `main_v2` import / compileall | ✅ |
| پنل مدیریت / پرداخت / شارژ / discover | همه ۲۰۰ روی DB واقعی |
