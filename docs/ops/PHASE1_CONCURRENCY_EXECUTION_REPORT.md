# فاز ۱ — گزارش اجرای صحت هم‌زمانی پایلوت

مرجع: [CAPACITY_PILOT_SLO_v1](CAPACITY_PILOT_SLO_v1.md)، Merge #364. **نتیجه: هفت مورد در دامنهٔ محدود و شبیه‌سازی‌شدهٔ توضیح‌داده‌شده PASS؛ نه اثبات ظرفیت ۲۰۰۰ کاربر/روز، نه پذیرش کامل تولید.**

## محیط واقعی اجرا و پیش‌نیازها

- Backend قفل‌شده: `dd0947492a27dd88fb3fb496c7cf2223d43a5a50`؛ HEAD شاخهٔ تجاری با remote تأیید شد. archive خارج repo، بدون تغییر source.
- Frontend: `4755716824b6e2529892009b7428b97ec87d791f` از main؛ برای شبیه‌سازی مرز release، app/index نسخهٔ #361 در `0fb035357fa55a1aa02a086bbd7dd0b3b27a6061` نیز خوانده شد.
- **PostgreSQL واقعی 16.2** با بستهٔ محلی `pgserver==0.1.4`، خوشهٔ تازهٔ خارج مخزن و Unix socket، بدون listener شبکه و بدون اتصال لیارا/تولید. SQLite استفاده نشد. CPU قابل مشاهده ۲ منطقی؛ منابع تضمین‌شدهٔ معادل تولید ادعا نمی‌شود.
- `alembic upgrade head` روی DB خالی موفق؛ revision=`0011_otp_request_ip`، isolation=`read committed`؛ SQLAlchemy pool_size=10. schema با migration ساخته شد، نه جایگزینی bootstrap به‌جای migration.
- requirements/constraints تجاری در venv جدا نصب شدند. seed مرجع با ابزار موجود از JSON بدون تغییر همان SHA فقط به DB ایزوله وارد شد؛ weights، فایل‌های مرجع و Cutover تغییر نکردند.
- دادهٔ تست: دو کاربر مصنوعی محلی و سفرهای مصنوعی؛ برای ۱۰ تکرار C01..C03 کاربران/ledger محلی بازنشانی شدند. هر entitlement اولیه یک اعتبار داشت. این fixture است، نه تغییر سهمیهٔ محصول یا حساب واقعی.
- HTTP درون‌پردازشی با FastAPI TestClient، احراز واقعی session و DB connection/session مستقل هر درخواست؛ شروع جفت درخواست‌ها با Barrier و دو thread. هیچ auth، قفل، تابع مصرف، ذخیره یا gateway verification واقعی برای PASS دور زده نشد. جفت شروع نزدیک الزاماً تمام زمان‌بندی‌های ممکن scheduler را پوشش نمی‌دهد.
- APP_ENV=test، BILLING_PROVIDER=mock، BILLING_FREE_MODE=false صرفاً برای **process محلی harness**؛ env لیارا و production بدون تغییر. callback به شبکهٔ درگاه یا پرداخت واقعی وصل نشد. فقط مرز AI با fault injection شبیه‌سازی شد.
- logging برنامه در harness غیرفعال و خروجی به status/count/assertion محدود شد؛ tokenها فقط در حافظه و هدر TestClient استفاده شدند، چاپ/ضمیمه نشدند. هیچ دادهٔ دانش‌آموز واقعی استفاده نشد. پس از اتمام، PostgreSQL و process نگهدارنده متوقف شدند.

## جدول هفت مورد اجباری

| مورد | روش و تعداد | نتیجه | شاهد کوتاه و مرز |
|---|---|---|---|
| C01 — Double-submit یک سفر | ۱۰ تکرار، در هرکدام دو POST موازی `/api/v1/me/consume-test` با همان کاربر و journey؛ اعتبار اولیه ۱ | **PASS** | ۱۰/۱۰؛ پاسخ‌ها 200/200، consumed مجموع=۱، یکی already_consumed=false و دیگری true؛ موجودی نهایی=۰ و ledger=۱ |
| C02 — دو سفر، یک اعتبار | ۱۰ تکرار، دو POST موازی از همان کاربر با journey متفاوت | **PASS** | ۱۰/۱۰؛ 200/409، consumed مجموع=۱، موجودی=۰ و ledger=۱؛ در مسیرهای مشاهده‌شده double-spend یا موجودی منفی رخ نداد |
| C03 — callback تکراری | ۱۰ payment مصنوعی؛ برای هرکدام دو GET callback موازی با همان order/authority و سپس یک retry؛ MockPaymentProvider واقعی پروژه | **PASS** | ۱۰/۱۰؛ 303/303/303 بدون دنبال‌کردن redirect؛ دقیقاً یک entitlement برای order با ۳ اعتبار و یک PaymentEvent؛ موجودی اولیه از grant پرداخت جدا شمرده شد |
| C04 — ذخیرهٔ موازی | یک سفر متعلق به A با نتیجهٔ واقعی engine که در DB ایزوله persist شد؛ ۱۰ جفت save-result با دو summary مصنوعی متفاوت | **PASS در صحت اتمیک مشاهده‌شده** | ۱۰/۱۰؛ 200/200؛ یک UserSession، همان مالک، completed=true؛ JSON نهایی یکی از دو summary کامل، نه ترکیب آن‌ها. سیاست عملی کد در بخش بعد؛ lost-update detection وجود ندارد |
| C05 — جداسازی A/B | تلاش دوطرفه روی consume/save/discover/counsel با شناسهٔ سفر دیگری؛ همچنین GET admin/users با نقش عادی | **PASS در routeهای آزموده‌شده** | برای هر جهت 403/403/402/402/403؛ تمام bodyهای ردشده فقط detail داشتند؛ مالکیت و summary سفرها بدون تغییر؛ اعتبار و ledger هر کاربر همان ۰ و ۱ باقی ماند |
| C06 — سفر باز و فرانت تازه | VM با app قدیمی #361: دو پاسخ S و سفر ناقص ذخیره شد؛ mount فرانت main با index cache-busted؛ جداگانه client جدید روی API/DB همان سفر باز را ادامه داد | **PASS برای شبیه‌سازی مجاز** | VM پاسخ/cursor/sessionId/seed/selectedRealms را حفظ و payload ادامه را canonical ساخت. API retry مصرف=۰ و discovery=200؛ debit اضافی رخ نداد. Deploy/CDN/SW واقعی آزموده نشد |
| C07 — خطای AI | تزریق HTTP 504 و 502 در مرز generate_counseling؛ برای هر خطا سپس discover، save-result و retry consume از مسیر واقعی API/DB اجرا شد | **PASS برای fault-path** | AI به‌ترتیب 504/502، main=200، save=200، consumed retry=۰؛ mock واقعاً فراخوانی شد. شبیه‌سازی upstream کند، اشباع worker یا outage طولانی اجرا نشد |

**FAIL یا BLOCKED در محدودهٔ اجراهای جدول ثبت نشد.** به همین علت PR اصلاح محصول پیشنهاد اجرایی ندارد. PASSها محدود به روش‌های بالا هستند؛ بخش‌های بدون اجرا از PASS عمومی استنتاج نشوند.

### C04 — سیاست تعارض دقیقاً چیست؟

`deploy:operational_store.py:201–241` به‌ویژه `225–239`، سشن را بر اساس UUID می‌خواند، مالک و وجود تحلیل persisted را کنترل و `row.result_summary = result_summary` را یکجا UPDATE می‌کند. مسیر API در `commercial_api.py:402–433` است.

**رفتار فعلی: جایگزینی کل JSON؛ آخرین UPDATE در ترتیب اعمال DB برنده است.** version field، compare-and-swap یا conflict response وجود ندارد؛ پس «آخرین ویرایش مورد نظر کاربر» یا جلوگیری از overwrite تغییرات تب دیگر تضمین نمی‌شود. PASS این تست فقط نبود JSON مخلوط/نیمه‌کاره و حفظ مالکیت است، نه تأیید سیاست حل تعارض به‌عنوان نیاز محصول. اگر ناظر حفظ همهٔ ویرایش‌ها یا optimistic locking بخواهد، PR کوچک جدا برای قرارداد ذخیره لازم است؛ فعلاً کد تغییر نکرده است.

### C05 — مرز خواندن نتیجه

در routerهای کاربر بررسی‌شده، GET عمومی نتیجه/سفر با id وجود ندارد؛ برای یک URL فرضی 404 نگرفتیم و آن را اثبات امنیت حساب نکردیم. route خواندن admin/users با دو نقش عادی رد شد؛ discover/counsel مربوط به سفر دیگری نیز قبل از تحویل نتیجه رد شدند. 402 برای guard سفر شارژشده است، نه 401/403؛ پاسخ فقط detail و بدون payload قربانی بود. بررسی همهٔ routeها، proxy یا تست نفوذ کامل ادعا نمی‌شود.

### C06 و C07 — حدود ادعای عدم وابستگی

مرز frontend واقعاً از source #361 به main و cache-bust index بررسی شد؛ چون app در #362 بازنویسی نشده، این یک مهاجرت schema عمده را مدل نمی‌کند. VM با مرورگر واقعی و SW مساوی نیست. آزمون backend C06 با یک journey شارژشده اما incomplete شروع شد؛ client جدید نتیجه گرفت و ledger تغییری نکرد.

در C07 شکست AI در همان مرز فراخوانی به پاسخ خطا تبدیل شد و مسیرهای بعدی غیر-AI موفق ماندند. این شاهد **جدایی عملکردی مسیر خطا** است، نه اثبات جدایی منابع یا حفظ latency هنگام صف طولانی/اشباع AI. ظرفیت/صف/Redis در این موج طراحی یا اضافه نشد.

## تطبیق source و شواهد

بایت‌های پنج فایل در archive تست با blobهای SHA تجاری مقایسه شدند و برابر بودند؛ نمونه‌ها:

| فایل | SHA-256 |
|---|---|
| main_v2.py | `9d547a3409a014c377c4ba13ef1863e834c31423467cea7cc752dd35e5475965` |
| commercial_api.py | `6c40e54edc8f66d695f4abb8c581fa640126a04d5690a4fa9e1ddcde73cb8995` |
| billing_credit_service.py | `39159ce425880936eb260639598f0f2e456914191101ae6ca5dabcf11c09b8f5` |
| operational_store.py | `abe05e7467b9900bb7798114462b3d0917e8dc5ecd07e42df09e40829f94dab4` |
| dark_horse_engine_v2.py | `09f77e211d9632603b3fe9cdbc780ec22ce7d5db40d6357f410e69333d2c8ed1` |

منبع assertionها و خروجی aggregate بدون دادهٔ حساس در [ضمیمهٔ بازتولید](PHASE1_CONCURRENCY_REPRODUCTION.md) ثبت شده‌اند. اسکریپت‌ها در این PR به runtime/tests اضافه نشده‌اند؛ متن ممیزی‌اند و اجرای مجددشان فقط روی DB تازهٔ ایزوله مجاز است. آزمون موجود `node tests/test_display_shuffle_contract.js` نیز جدا اجرا و PASS شد.

### خطاهای آماده‌سازی، نه پنهان‌کردن شکست محصول

نخستین اجرای harness محلی به starts_at خالی fixture entitlement برخورد کرد (SQLSTATE 23502)؛ starts_at مصنوعی به fixture اضافه شد، نه مدل یا محصول. نخستین اجرای VM به object قدیمی Gitِ موجودنبودن و سپس نبود AbortController در outer sandbox برخورد کرد؛ SHA fetch و dependency خود harness اضافه شدند. هیچ assertion صحت برای سبزکردن حذف نشد. جدول بالا مربوط به اجرای نهایی کامل است؛ شمار تکرارهای ناقص قبلی به‌عنوان PASS حساب نشده‌اند.

## نتیجه و عدم اقدام

برای این فشار کنترل‌شده، نقض صحت اعتبار/مالکیت در مسیرهای آزموده‌شده مشاهده نشد. این نتیجه مجوز افزایش جذب، تأیید SLO، اجرای production load یا اعلام آمادگی ملی نیست. پیشنهاد قدم بعد فقط با دستور ناظر: تعیین پذیرش last-write، سپس برنامهٔ بار با think time و محیط نزدیک تولید؛ آزمایش مرورگر/SW واقعی و fault کند AI جدا باقی‌اند.

در این موج تنها گزارش و ضمیمهٔ Markdown وارد Draft می‌شوند؛ بدون تغییر source محصول، تست‌های موجود، موتور، وزن، majors، Hybrid، Total، shuffle، منطق سهمیه/خرید، CI، env لیارا، DNS یا Deploy. هیچ خرید infra و الزام Redis وجود ندارد. Merge فقط با دستور جداگانهٔ ناظر.
