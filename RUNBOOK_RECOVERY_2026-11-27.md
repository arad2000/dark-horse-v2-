# راهنمای اجرا: بالا آوردن سایت + کد معرف اختیاری

شاخه: `arena/dd8fedc9-dark-horse-v2` · هدف: `deploy/liara-commercial-sandbox`

---

## چه چیزی در این شاخه آماده است

| فایل | نقش |
|---|---|
| `patches/recovery_and_optional_referral.patch` | پچ کامل (۶ فایل) که روی `dda1561` **تمیز اعمال می‌شود** |
| `liara_pre_start.sh` | نسخهٔ مقاوم هوک (همان چیزی که پچ می‌گذارد) |
| `OUTAGE_DIAGNOSIS_2026-11-27.md` | گزارش عیب‌یابی و شواهد |

پچ شامل:

1. `alembic/versions/0012_referral_attribution.py` — دیگر سرویس را نمی‌خواباند
2. `liara_pre_start.sh` — حالت «پایگاه‌دادهٔ قدیمی بدون stamp»
3. `commercial_api.py` + `test_quota_health_migration.py` — قرارداد ریویژن `0012`
4. `docs/commercial_ui.js` + `docs/auth_api_client.js` + `docs/index.html` — کد معرف اختیاری

---

## گام ۰ — یک کوئری، قبل از هر کاری

بدون این جواب، حدس زدن اتلاف وقت است. در پنل Liara → شل، یا با
`PRODUCTION_DATABASE_URL`:

```sql
SELECT to_regclass('alembic_version') AS version_table,
       (SELECT version_num FROM alembic_version) AS revision;
```

| نتیجه | معنی | برو به |
|---|---|---|
| `version_table = NULL` | پایگاه‌داده stamp نشده ← علت اصلی | گام ۲ با `ALEMBIC_BASELINE_REVISION` |
| `revision = 0011_otp_request_ip` | stamp شده، شکست جای دیگری است | گام ۲ بدون متغیر baseline |
| `revision = 0012_referral_attribution` | مهاجرت قبلاً انجام شده | فقط گام ۱ و ۳ |

---

## گام ۱ — پچ را روی شاخهٔ deploy بگذارید

```bash
git checkout deploy/liara-commercial-sandbox
git pull

git apply --check patches/recovery_and_optional_referral.patch   # باید بی‌صدا بگذرد
git apply         patches/recovery_and_optional_referral.patch
```

اگر `--check` خطا داد، شاخهٔ deploy از `dda1561` جلوتر رفته است؛ پچ را دستی اعمال کنید
(۶ فایل، همه در گزارش توضیح داده شده‌اند) یا از من بخواهید بازتولیدش کنم.

سپس **قبل از push** این دو را اجرا کنید:

```bash
python -m compileall -q .            # باید بی‌صدا بگذرد
python -m pytest -q test_quota_health_migration.py \
                    test_referral_service.py \
                    test_commercial_api.py \
                    test_main_api_contract.py
# انتظار: همه پاس (روی PostgreSQL واقعی ۳۳ پاس / ۰ شکست)
node tests/test_security_contracts.js
node tests/test_public_javascript_syntax.js
```

> تست‌هایی که `DATABASE_URL` می‌خواهند، بدون آن skip می‌شوند و اشکالی ندارد؛
> ولی برای اطمینان، یک `DATABASE_URL` روی پایگاه‌دادهٔ تست بدهید.

---

## گام ۲ — استقرار، با یا بدون baseline

### حالت الف: پایگاه‌داده stamp نشده است (محتمل‌ترین)

هوک اگر تنها باشد **باز هم بسته می‌ماند** ولی این بار دلیلش را می‌گوید:

```
liara_pre_start: live tables already match revision 0012_referral_attribution (derived read-only).
liara_pre_start: FATAL: ... Set ALEMBIC_BASELINE_REVISION=0012_referral_attribution ...
```

۱. در Liara → تنظیمات → متغیرهای محیطی، اضافه کنید:

```
ALEMBIC_BASELINE_REVISION=0012_referral_attribution
```

۲. دپلوی کنید. در لاگ باید ببینید:

```
liara_pre_start: legacy schema without alembic_version; stamping baseline 0012_referral_attribution once.
liara_pre_start: migrations applied; starting application.
```

۳. **متغیر را حذف کنید** و یک بار دیگر دپلوی کنید تا مطمئن شوید بدون آن هم بالا می‌آید.

> اگر هوک ریویژن دیگری پیشنهاد داد (مثلاً `0011_otp_request_ip`)، همان را بگذارید —
> پیشنهاد از روی جدول‌ها/ستون‌های واقعی محاسبه می‌شود، نه حدس.

### حالت ب: پایگاه‌داده stamp شده است

بدون هیچ متغیری دپلوی کنید. اگر باز شکست خورد، لاگ Liara را ببینید:

| خطا | معنی | کار |
|---|---|---|
| `relation "..." already exists` | اسکیما جلوتر از ریویژن ثبت‌شده است | گام ۰ را دوباره بگیرید؛ با من هماهنگ کنید |
| `UniqueViolation ... referral_code` | نسخهٔ قدیمی `0012` | پچ این را حل می‌کند |
| `cannot inspect the target schema` | URL/شبکهٔ پایگاه‌داده | `DATABASE_URL` و دسترسی Liara را چک کنید |
| `DATABASE_URL is not set` | متغیر در هوک در دسترس نیست | فرض بنیادی هوک؛ به من بگویید |

### راه فرار فوری (اگر نمی‌خواهید منتظر بمانید)

```bash
git revert -m 1 dda1561     # یا reset به 8451887
```

`8451887` نه هوک دارد نه `0012`، پس بالا می‌آید؛ هزینه‌اش از دست رفتن referral و
مهاجرت `0012` است. دادهٔ کاربران دست نمی‌خورد.

---

## گام ۳ — تأیید بالا آمدن

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://api.asbe-siah.ir/
curl -s https://api.asbe-siah.ir/__runtime_fingerprint | head -c 300
curl -s https://api.asbe-siah.ir/api/v1/runtime/quota-health
```

`quota-health` باید بدهد:

```json
"expected_migration_revision": "0012_referral_attribution",
"alembic_revisions": ["0012_referral_attribution"],
"migration_ok": true
```

سپس در مرورگر، سه چیز را ببینید:

1. **سفر اکتشافی** — باز می‌شود (برای نتیجهٔ نهایی، ورود + شارژ لازم است؛ این طراحی است)
2. **پنل مدیریت** — `asbe-siah.ir/admin.html` با حساب admin
3. **پرداخت** — پنجرهٔ خرید باز می‌شود و فیلد «کد معرف (اختیاری)» دیده می‌شود

---

## گام ۴ — کد معرف: آنچه باید ببینید

در پنجرهٔ خرید، **بدون وارد کردن هیچ کدی** باید بتوانید «ادامه به درگاه» را بزنید.

| کاری که می‌کنید | نتیجهٔ مورد انتظار |
|---|---|
| فیلد را خالی می‌گذارید | خرید مستقیم، بدون هیچ پیام خطا |
| کد معتبر می‌زنید | پیام سبز «کد معرف ثبت شد.» |
| کد اشتباه می‌زنید | پیام زرد «این کد معتبر نبود؛ خرید به‌صورت مستقیم ادامه می‌یابد.» و خرید ادامه دارد |
| بعد از اولین خرید موفق کد می‌زنید | حساب قفل است (۴۰۹)؛ پیام اطلاع‌رسانی، خرید ادامه دارد |

ساخت کد توسط ادمین: `POST /api/v1/admin/referrals/codes` با `{"code": "REF2026", "label": "..."}`
(کد باید ۴ تا ۳۲ نویسهٔ ASCII حرف/رقم باشد).

---

## نکتهٔ کش مرورگر

`docs/index.html` نسخه‌ها را بالا برده (`auth v8`، `commercial v25`). اگر کاربری نسخهٔ قدیم
را دید، یک بار hard-refresh کافی است. سرویس‌ورکر روی این نسخهٔ فرانت وجود ندارد
(`sw.js` در `index.html` صدا زده نمی‌شود)، پس مشکل کش پایدار نیست.

---

## چیزهایی که این پچ **نمی‌کند**

- منطق امتیازدهی، رشته‌ها، موتیوها، مشاوره و آزمون ورودی: **صفر تغییر**
  (fingerprint یکسان — بخش ۶ گزارش)
- قیمت، تعداد اعتبار، طرح‌ها، درگاه پرداخت: **صفر تغییر**
- دادهٔ کاربران: هیچ ردیفی حذف یا بازنویسی نمی‌شود
- مرج `main` به deploy: انجام نمی‌شود (هیچ نقطهٔ مرج مشترکی ندارند)
