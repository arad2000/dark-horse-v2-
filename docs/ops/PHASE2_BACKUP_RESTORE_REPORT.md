# فاز ۲ — گزارش backup / restore واقعی ایزوله

**حکم: dump→restore منطقی محلی PASS؛ وضعیت و قابلیت بازیابی backup واقعی لیارا/تولید BLOCKED از نظر دسترسی است.** نتیجهٔ محلی، تضمین RPO/RTO یا بازیابی نسخهٔ پشتیبان تولید نیست. مرجع [SLO پایلوت](CAPACITY_PILOT_SLO_v1.md) و [پایش/readiness](PHASE2_MONITORING_READINESS.md).

## C) جدول مورد | وضعیت | شاهد

| مورد | وضعیت | شاهد |
|---|---|---|
| روشن/خاموش بودن backup لیارا/DB فعلی | **BLOCKED / نامعلوم** | connector لیارا unsupported؛ دسترسی پنل/DB واقعی موجود نیست؛ فرض روشن‌بودن یا خاموش‌بودن نداریم |
| بازه، retention، آخرین موفقیت و PITR لیارا | **BLOCKED / نامعلوم** | نیازمند قرائت ناظر؛ هیچ screenshot یا خروجی جدید ارائه نشده |
| backup واقعی DB محلی مصنوعی | **PASS** | pg_dump 16.2، format custom، exit=0؛ ۲۱۸٬۹۶۱ بایت، حدود ۰٫۱۵۴ ثانیه |
| restore در DB تازهٔ ایزوله | **PASS** | pg_restore 16.2 با exit-on-error، exit=0؛ حدود ۰٫۴۵۱ ثانیه؛ مقصد تازه، بدون clean/drop روی DB منبع |
| تطبیق داده | **PASS** | همهٔ ۲۳ جدول public: count و SHA-256 دادهٔ canonical هر جدول برابر؛ ۲۰ sequence با last_value برابر |
| اپ روی DB بازیابی‌شده | **PASS در smoke محلی** | startup حدود ۲٫۲۷۶ ثانیه؛ root/me/quota/retry-consume/discover/save-result همگی 200 |
| عدم debit مجدد پس از restore | **PASS** | consumed retry=۰؛ موجودی همان کاربر=۱؛ ledger اولیه بازیابی شد |
| migration و query سبک | **PASS** | SELECT 1 موفق؛ revision=`0011_otp_request_ip` مطابق head همان source |
| quota-health موجود | **FAIL به‌عنوان معیار readiness** | HTTP=200 ولی migration_ok=false به‌دلیل انتظار قدیمی 0010؛ جزئیات در سند پایش |
| restore backup واقعی Liara یا زمان بازیابی تولید | **BLOCKED** | فایل/دسترسی backup واقعی موجود نیست؛ هیچ اتصال به DB کاربر یا restore مخرب انجام نشد |

## محیط و روش دقیق اجرا

Backend از `deploy/liara-commercial-sandbox@dd0947492a27dd88fb3fb496c7cf2223d43a5a50` خارج repo archive شد. venv با requirements و constraints همان source و `pgserver==0.1.4` ساخته شد. ابزارهای pg_dump/pg_restore همراه PostgreSQL بسته، نسخهٔ 16.2 بودند. خوشهٔ تازهٔ `/home/user/phase2-pgdata` روی Unix socket بدون listener شبکه اجرا شد؛ هیچ DSN از تنظیمات لیارا خوانده نشد.

دو DB تازهٔ محلی در همان خوشه ساخته شدند: `audit_source` و `audit_restored`. این جداسازی منطقی واقعی است، **نه** تمرین خرابی کامل ماشین/دیسک/منطقه. `alembic upgrade head` روی source خالی اجرا شد؛ مقصد بدون اجرای migration اضافی از dump restore شد. schema با نسخهٔ محصول دستکاری نشد. seed مرجع موجود از JSON همان Git فقط وارد DB ایزوله شد؛ scoring همچنان JSON-backed و Cutover بدون تغییر ماند.

fixture: دو کاربر مصنوعی، یک auth session، دو entitlement هرکدام ۲ اعتبار، یک journey و یک ledger مصرف؛ نتیجه با موتور واقعیِ همان release محاسبه و persist و یک summary مصنوعی ذخیره شد. بعد از مصرف اولیه، کاربر آزمون یک اعتبار داشت. این fixture محلی است، نه تغییر سهمیهٔ تولید. نه پول واقعی و نه سرویس خارجی AI/پیامک/درگاه فراخوانی شد.

ترتیب عملیات:

1. گرفتن snapshot منطقی از تمام جدول‌های public در DB ساکن آزمایش: row_to_json هر ردیف، canonical JSON با کلیدهای مرتب، مرتب‌سازی ردیف‌ها، count و SHA-256؛ همچنین نام/last_value sequenceها. rowها فقط در حافظه مقایسه شدند، در report یا log چاپ نشدند.
2. `pg_dump --format=custom --no-owner --no-acl` از source به فایل محلی؛ سپس `pg_restore --exit-on-error --no-owner --no-acl` به DB تازه. هیچ `--clean` روی source یا DB تولید اجرا نشد.
3. همان snapshot روی target؛ برابری کامل ۲۳ جدول و ۲۰ sequence قبل از smoke که می‌تواند داده بنویسد تأیید شد. این تمرین roles/ACL/ownerهای production را پوشش نمی‌دهد چون صریحاً از dump/restore حذف شدند.
4. process تازهٔ اپ با DATABASE_URL فقط target و APP_ENV=test/BILLING_PROVIDER=mock/BILLING_FREE_MODE=false شروع شد. startup موتور واقعی و مسیرهای زیر روی target بررسی شدند؛ auth با session بازیابی‌شده بود، نه درخواست login با رمز.
5. پس از اتمام، PostgreSQL و process نگهدارنده متوقف شدند. dump مصنوعی خارج Git ماند. هیچ restore، restart یا redeploy لیارا انجام نشد.

| probe اپ بازیابی‌شده | نتیجه |
|---|---|
| GET `/` | 200؛ فقط liveness |
| GET `/api/v1/me` با session مصنوعی بازیابی‌شده | 200 |
| GET `/api/v1/me/quota` | 200 |
| POST `/api/v1/me/consume-test` برای همان journey | 200؛ consumed=۰، remaining=۱ |
| POST `/api/v2/darkhorse/discover` با همان journey | 200؛ engine و guard DB واقعی |
| POST `/api/v1/me/save-result` | 200؛ همان DB target |

زمان‌های بالا مربوط به **DB کوچک مصنوعی** هستند؛ زمان دانلود backup، شبکه، provisioning، نقش‌ها، extensions، WAL، object storage یا دیتاست واقعی در آن‌ها نیست. از جمع این زمان‌ها RTO production استخراج نمی‌شود. مقدار RPO/RTO و برنامهٔ backup باید با ناظر تصویب و با دادهٔ هم‌اندازه تمرین شود.

## شواهد بدون دادهٔ حساس

```text
source SHA: dd0947492a27dd88fb3fb496c7cf2223d43a5a50
logical table/sequence comparison: equal
users=2; auth_sessions=1; user_sessions=1; entitlements=2
journey_credit_consumptions=1; discovery_results=1
dump SHA-256: 661a494edcfa5fa538ff9e7273064b074f4e0a75cb9cfe6b40bfba131770575d
```

مسیرهای آزمایش خارج repo: `/home/user/phase2-source/restore_audit.py`، `/home/user/phase2-source/readiness_probe.py`، `/home/user/phase2-restore-result.json`. فایل backup و fixture هیچ‌کدام وارد Git یا آرتیفکت عمومی نشدند. این مسیرها evidence محلی‌اند، نه آرشیو دائمی؛ مراحل بالا برای بازتولید مستقل ثبت شده‌اند. برای IPC آزمون auth، fixture مصنوعی موقت mode=0600 استفاده و پس از smoke حذف شد؛ توکن در report/لاگ چاپ نشد. log اپ غیرفعال و subprocess output حساس منتشر نشد.

## حداقل اقدام ناظر برای Liara — بدون restore روی production

۱. نام سرویس DB واقعی را ثبت کنید؛ روشن/خاموش بودن backup، زمان‌بندی/منطقهٔ زمانی، retention، آخرین backup موفق، رمزنگاری/محل ذخیره و امکان PITR را از پنل بخوانید. اگر پنل این‌ها را ندارد یا روشن نیست، «نامعلوم/فاقد قابلیت» ثبت کنید؛ وعدهٔ feature ندهید.

۲. با دسترسی مجاز، یک backup مشخص را انتخاب و شناسه/زمان/نسخهٔ PostgreSQL/اندازه را ثبت کنید. **مقصد restore حتماً DB جدیدِ غیرتولیدی** باشد؛ app production به آن اشاره نکند. بدون تأیید هیچ DB قبلی را drop/overwrite نکنید. فایل پشتیبان واقعی محرمانه است و به گفتگو یا repo وارد نشود.

۳. اگر فرمت native پنل است، restore همان پنل فقط به مقصد ایزوله با امکانات موجود؛ اگر logical custom dump است، الگوی زیر پس از تأیید مقصد/نسخه/نقش‌ها. service profileها و pgpass را در فایل محلی با دسترسی 0600 تنظیم کنید، نه URL رمزدار در command/log. نام serviceها نمونه‌اند، credential نیستند:

```bash
# pilot_backup_source فقط منبع مجاز؛ pilot_restore_isolated فقط DB تازهٔ غیرتولیدی.
# انجام backup واقعی منبع نیز نیاز مجوز و پنجرهٔ عملیاتی مناسب دارد.
umask 077
pg_dump --dbname='service=pilot_backup_source' --format=custom \
  --no-owner --no-acl --file=pilot-private.dump
pg_restore --list pilot-private.dump > pilot-private.list
# پس از بررسی نوع dump، extensionها و نقش runtime؛ هرگز production مقصد نباشد.
pg_restore --exit-on-error --no-owner --no-acl \
  --dbname='service=pilot_restore_isolated' pilot-private.dump
```

اگر dump plain SQL یا physical/WAL است این فرمان را به‌جای فرایند مخصوص آن اجرا نکنید. `--no-owner/--no-acl` نیاز تنظیم و آزمون grants مناسب runtime در مقصد را حذف نمی‌کند؛ کم‌کردن دسترسی امنیتی برای سبزشدن مجاز نیست. زمان شروع/پایان، exit status و شمارهای تجمیعی ثبت شوند؛ از چاپ stderr حاوی دادهٔ ردیف/DSN در کانال عمومی خودداری شود.

۴. قبل از وصل‌کردن اپ آزمایشی، پیامک/ایمیل/AI/پرداخت و webhook خروجی واقعی را مسدود یا mock کنید. DB بازیابی‌شدهٔ واقعی ممکن است توکن/اطلاعات اشخاص داشته باشد؛ کنترل دسترسی و حذف/ناشناس‌سازی مطابق سیاست لازم است. با account مصنوعی از پیش مجاز smoke کنید، نه credential دانش‌آموز. reference فایل‌های Git و app version هم باید با backup سازگار باشند؛ dump DB به‌تنهایی backup کامل محصول نیست.

۵. migration head release، داده و sequenceها، مالکیت نتایج، سلامت اپ و idempotency مصرف را بررسی و PASS/FAIL/BLOCKED، زمان restore و زمان آماده‌شدن خدمت را جدا ثبت کنید. تا ارائهٔ این شاهد، «بازیابی production» همچنان BLOCKED است. حذف امن مقصد و backup طبق retention مصوب انجام شود؛ تولید دست‌نخورده بماند.

## حدود این PR

فقط دو فایل ops؛ بدون کد health یا runtime. نقص quota-health گزارش شد و برای اصلاح جدا در شاخهٔ تجاری نیاز دستور دارد؛ آن را با تغییر کد در main پنهان نکردیم. بدون rollback واقعی، تست بار فاز۳، Redis اجباری، تغییر موتور/وزن/majors/Hybrid/shuffle/منطق خرید یا Merge. پایش staging و وضعیت backup لیارا هنوز نیاز شاهد ناظر دارند؛ این فاز از نظر عملیاتی کامل بسته اعلام نمی‌شود.
