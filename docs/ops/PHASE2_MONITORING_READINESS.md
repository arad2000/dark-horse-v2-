# فاز ۲ — نقشهٔ پایش و readiness پایلوت

**خلاصه: طرح و probe محلی آماده؛ پایش مستقر روی Liara/staging هنوز BLOCKED از نظر دسترسی است. endpoint یا middleware محصول تغییر نکرد.** مرجع: [SLO پایلوت](CAPACITY_PILOT_SLO_v1.md).

## وضعیت و شواهد

| مورد | وضعیت | شاهد / حد اعتبار |
|---|---|---|
| منبع API | ثبت‌شده | `deploy/liara-commercial-sandbox@dd0947492a27dd88fb3fb496c7cf2223d43a5a50` از Git fetch شد؛ نه Python قدیمی main |
| منبع فرانت | ثبت‌شده | main مبنای جلسه `05d58ee832d0be8e2a74590e77df3731e6f8a37f` |
| نقشهٔ metrics/alerts | آمادهٔ تصویب | جدول زیر؛ نه ادعای نصب dashboard |
| پایش واقعی staging/نزدیک تولید | **BLOCKED** | connector لیارا unsupported؛ بدون دسترسی مستقیم پنل/API لیارا یا میزبان staging؛ منابع، worker، proxy و اتصال DB واقعی نامعلوم |
| CPU/RAM لیارا | **BLOCKED برای قرائت فعلی** | ناظر باید نمودار مصرف و زمان نمونه را از پنل app API و Static ثبت کند؛ plan limit با مصرف واقعی فرق دارد |
| liveness فعلی | موجود، ناکافی برای readiness | `main_v2.py:399–401`: root پاسخ ثابت online؛ startup در نبود تنظیم DB می‌تواند فقط log کند (`247–257`) |
| readiness دقیق release | معیار پیشنهادی، probe محلی PASS | DB سالم/خراب، head نامنطبق و engine unavailable در observer خارجی بررسی شدند؛ endpoint تولیدی اضافه نشد |
| quota-health به‌عنوان readiness | **FAIL** | روی DB سالمِ restore شده، HTTP=200 ولی migration_ok=false؛ انتظار کد 0010 و revision واقعی 0011 است |
| استقلال readiness از AI | طراحی‌شده؛ محلی تأیید در حد probe | probe به AI وصل نمی‌شود؛ وضعیت سبز DB/engine به AI وابسته نیست؛ اشباع منابع AI آزمایش نشده |

## A) حداقل پایش پیشنهادی

بدون خرید ابزار گران: شمارنده و histogram تجمیعی در لاگ ساختاریافته یا ابزار موجود پنل + probe خواندنی، با پایش جدا برای API و Static. ابزار واقعی پس از دسترسی ناظر انتخاب شود؛ در این موج collector نصب نشده است.

| مسیر/سیگنال | اندازه‌گیری لازم | هدف اولیه/هشدار پیشنهادی |
|---|---|---|
| POST `/api/v1/auth/login` | count، duration، p95، 5xx، timeout، 429 | p95≤۲s طبق SLO؛ خطای 5xx بیش از ۱٪ در دو پنجرهٔ ۵دقیقه‌ای با حداقل ۱۰۰ درخواست در هر پنجره → رسیدگی؛ نمونهٔ کم = شاهد ناکافی |
| POST `/api/v1/me/save-result` و `/me/consume-test` | جداگانه latency، 5xx، 409، retry/no-op شمارشی | p95≤۱s؛ هر double-charge یا نقض مالکیت → توقف افزایش جذب و incident، مستقل از درصد خطا |
| POST `/api/v2/darkhorse/discover` و `/branch-discovery` | زمان کامل request و شمار نتیجه/خطا بدون متن نتیجه | p95≤۳s؛ همان شرط پنجره/حجم نمونه؛ health سبز جای latency را نمی‌گیرد |
| billing create-payment / callback در صورت فعال‌بودن | 5xx، خطای verification، latency و grant تکراری به‌صورت عدد | callback 303 موفق را 5xx نشماریم؛ duplicate grant باید صفر باشد؛ probe نباید پرداخت واقعی ایجاد کند |
| اتصال DB | SELECT 1، latency اتصال/query، migration head؛ محدودیت pool در صورت دسترسی | هر ۶۰s، connect timeout حدود ۲s و statement timeout حدود ۱s؛ سه شکست متوالی → هشدار؛ مبنای پیشنهادی نه تنظیم انجام‌شده |
| API process / فرانت | root و GET فایل کوچک عمومی؛ status و timeout | از probe خارج فرایند با فاصلهٔ کنترل‌شده؛ root فقط liveness است |
| CPU/RAM/DB pool | مصرف واقعی، OOM/restart، اشباع connection | قرائت پنل با زمان؛ حدود هشدار پس از شناخت baseline، نه حدس از اندازهٔ plan |
| AI | timeout/502/504، مدت و هزینهٔ تجمیعی | وضعیت degraded مستقل از readiness اصلی؛ پایش هزینه بدون prompt |

۵xx تنها کل خطای SLO نیست: network/timeout و 429 روی بار عادی نیز طبق سند SLO جدا گزارش شوند. numerator و denominator هر route مشخص باشد؛ failureهای سرویس ثالث از گزارش ناپدید نشوند. p95 محلی restore در این گزارش معیار SLO ترافیک نیست.

لاگ مجاز: route template بدون query، method، status، duration_ms، release SHA و correlation ID تصادفی مستقل از کاربر. **رمز، Bearer/token، OTP، cookie، Authorization، شماره، متن پاسخ/نتیجه، prompt AI، raw callback، URL اتصال DB و dump env ممنوع‌اند.** exception/SQL params و query string باید پیش از ارسال به ابزار پایش redact شوند؛ ثبت request/response body فعال نشود. retention و دسترسی اپراتور پیش از نصب تعیین شود.

## B) قرارداد پیشنهادی readiness جدا از liveness

«آمادهٔ ترافیک پایلوت» یعنی: (۱) engine فعلی پس از startup موجود است، بدون تغییر scoring؛ (۲) اتصال و SELECT 1 با timeout موفق؛ (۳) مجموعهٔ revisionهای alembic دقیقاً با headهای **همان release** برابر؛ (۴) schema/جدول‌های حیاتی حساب، session و ledger موجود و قابل خواندن با نقش runtime. dependency اجباری دیگری اگر در مسیر اصلی وجود دارد باید با شاهد به فهرست افزوده شود؛ پرداخت غیرفعال یا AI اختیاری نباید readiness مسیر اصلی را قرمز کند. readiness نباید احراز را دور بزند، رکورد بنویسد، موتور را دوباره بسازد یا به درگاه وصل شود.

پیشنهاد HTTP آینده: `/health/live` فقط liveness؛ `/health/ready` برابر 200 برای آماده و 503 برای ناآماده، body عمومی حداقلی. revision/diagnostics/جزئیات DB در سطح اپراتور محدود بمانند. این routeها **در این PR وجود ندارند**. observer کوتاه محلی فقط DB+head+flag engine را بررسی کرد؛ schema permission role و جمع همهٔ وابستگی‌ها را تضمین نمی‌کند.

### probe محلی اجراشده

PostgreSQL واقعی 16.2 و migration head=`0011_otp_request_ip`؛ انتظار از `ScriptDirectory.from_config(Config('alembic.ini')).get_heads()` همان source، نه رشتهٔ ثابت کپی‌شده. نتایج:

- DB سالم + head برابر + flag engine_ready=true → ready=true.
- head مورد انتظار ساختگیِ نامنطبق، بدون تغییر DB → ready=false، migration_mismatch.
- flag engine_ready=false تزریق‌شده → ready=false، engine_unavailable؛ این تست خرابی واقعی فایل موتور نیست.
- بعد از stop واقعی خوشهٔ محلی → ready=false، db_unavailable.

startup و discovery موتور واقعی در smoke restore جدا PASS شدند. هیچ probe به AI متصل نشد. این observer ابزار آزمایش خارج مخزن بود؛ readiness عملیاتی staging هنوز پیاده/فعال نشده است.

### نقص مشاهده‌شدهٔ health فعلی

`deploy:commercial_api.py:284–305` مقدار expected_revision=`0010_journey_credit_consumptions` دارد ولی Alembic head تجاری `0011_otp_request_ip` است. روی restore سالم خروجی migration_ok=false و HTTP=200 بود. این **نقص diagnostic/readiness** است، نه شاهد خرابی DB بازیابی‌شده. اگر observer فعلی فقط HTTP را می‌سنجد false-positive خواهد داشت؛ اگر migration_ok را می‌سنجد روی release جاری false-negative دارد.

پیشنهاد اصلاح جدا و کوچک در شاخهٔ تجاری: قرارداد health و expected head release را مشخص و تست 200/503 برای DB down، migration mismatch و حالت سالم اضافه کنید؛ همراه با حفظ جدایی AI. در این جلسه شاخهٔ ثابت مبتنی بر main است؛ backend به main کپی یا اصلاح نشد. هیچ گیت برای سبزشدن تضعیف نشده است.

## D) rollback — فقط دستورالعمل، اجرا نشد

- **فرانت:** ناظر در app تأییدشدهٔ `asbe-siah-web-test` یک release قبلیِ سالم با SHA و hash مشخص را بازگرداند، اگر پنل قابلیت rollback دارد. fallback با مجوز: همان خروجی allowlist‌شدهٔ SHA قبلی دوباره deploy شود؛ نیازی به reset/force-push main نیست. منبع `main` است و CI push بعدی دوباره نسخهٔ main را منتشر می‌کند؛ incident باید با انتشارهای بعدی هماهنگ شود. HTML و asset URL/SW با release سازگار بررسی شوند؛ پاک‌کردن localStorage/token/quota روش rollback نیست.
- **API:** نام app و release قبلی سالم را ناظر تأیید کند؛ backend فقط از شاخهٔ تجاری. rollback کد با rollback DB یکی نیست. پیش از برگشت، سازگاری schema/env با نسخهٔ قبلی ارزیابی شود؛ migration downgrade و restore تولید خودکار انجام نشود. cutoff و مجوز برگشت را مسئول incident مشخص کند.
- smoke پس از برگشت: readiness واقعی، ورود، نتیجه، ذخیره و retry بدون debit دوباره. rollback فعلی production/staging اجرا نشده است.

**گیت پایان عملیاتی باز است:** ناظر باید پایش staging، مصرف پنل، سیاست هشدار و readiness قابل استفاده را تأیید کند. نتیجهٔ restore محلی و دستورالعمل backup در [گزارش بازیابی](PHASE2_BACKUP_RESTORE_REPORT.md) است. بدون فاز۳/بار، بدون Redis اجباری، بدون تغییر موتور/وزن/majors/Hybrid/shuffle/خرید؛ Merge فقط با تأیید ناظر.
