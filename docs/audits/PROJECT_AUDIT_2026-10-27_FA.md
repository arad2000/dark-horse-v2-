# ممیزی سراسری پروژهٔ اسب سیاه — ۲۰۲۶-۱۰-۲۷

**نوع ممیزی: معماری و بررسی ایستای چندلایه با شواهد فعلی GitHub؛ نه penetration test، نه تأیید علمی/حقوقی و نه مجوز انتشار.**

## خلاصهٔ اجرایی
وضعیت دادهٔ فعال deploy از نظر شکل/عضویت/pool مطلوب‌تر از main است، اما سه شکست CI فعلی، قرارداد canonical حل‌نشده، نبود backend کامل در main و ضعف کنترل login مانع اعلام آمادگی انتشار هستند. هیچ P0 اثبات‌شده یا نفوذ بالفعل در این ممیزی گزارش نمی‌شود. ۱۸ یافته: ۵ مورد P1، ۱۱ مورد P2 و ۲ مورد P3. P1 یعنی اصلاح/تعیین تکلیف قبل از اتکای عملیاتی، نه اثبات خرابی سراسری سرویس.

## ۱. دامنه و هویت مبنا
- شاخهٔ نشست: `arena/9da65698-dark-horse-v2`؛ HEAD محلی: `a1cdab9cd875bf9e9e01c19debf1e1237f58302b`؛ Working Tree هنگام شروع پاک بود.
- main واقعی خوانده‌شده از GitHub: `fbdee3e01e95a37468de680eeded63f13cad9c8b`؛ ۱۲۶ blob.
- deploy واقعی خوانده‌شده از GitHub: `8c87cb5d879e166a6052ea90a8d63b22d2118aa3`؛ ۳۴۵ blob.
- SHAهای راه‌دور در شروع ممیزی pinned شدند؛ جابه‌جایی بعدی refs نتیجه را برای commit جدید خودکار معتبر نمی‌کند.
- tree کامل main/deploy و ۴۰ فایل منتخب deploy شامل API، auth، quota/payment، موتور، داده‌های اصلی و workflowها خوانده شد. محتوای GET با Git blob SHA1 کنترل شد. فایل‌های main که همسانی‌شان با checkout بررسی شد: main_v2، requirements، engine، sw، auth client و privacy.
- تمام ادعاهای deploy به source همین SHA مربوط‌اند؛ نه اثبات اینکه همین SHA روی Liara در حال سرویس است. live endpoint یا fingerprint زنده فراخوانی نشد.
- خواندن داده‌های JSON و تحلیل مجموعه‌ای انجام شد. هیچ import کد پروژه، startup API، DB، migration، آزمون integration، scoring experiment یا AI request اجرا نشد.

## ۲. معماری
Frontend: docs/، HTML/CSS/Vanilla JS و PWA/service worker؛ auth/quota و persistence محلی. Backend deploy: FastAPI، router تجاری/مدیریت/feedback/admission، SQLAlchemy/PostgreSQL برای عملیات و JSON versioned برای psychometrics. Engine M/S/V جدا از billing است؛ counsel از سرویس Cloudflare استفاده می‌کند. عملیات استقرار/Pages و بررسی DB در GitHub Actions تعریف شده‌اند.
گلوگاه ساختاری: main عملاً front-heavy با backend ناقص است ولی deploy مجموعهٔ عملیاتی بزرگ‌تری دارد؛ همزمان guard، main را canonical تمام داده‌های مرجع می‌خواند. تصمیم منشأ حقیقت باید پیش از sync و توسعهٔ علمی بعدی ثبت شود.

## ۳. یافته‌ها به ترتیب اولویت
|ID|شدت|موضوع|قطعیت|
|---|---|---|---|
|A01|P1|main بک‌اند مستقلِ قابل ساخت ندارد|قطعی در source؛ اجرای startup انجام نشد|
|A02|P1|قرارداد canonical با وضع واقعی main/deploy ناسازگار است|قطعی از blobها و گام CI|
|A03|P1|مسیر login محدودکنندهٔ تلاش ندارد|قطعی در فایل‌های برنامهٔ خوانده‌شده؛ وضعیت WAF نامعلوم|
|A04|P1|بارگذاری داده و schema موتور fail-open است|قطعی در source؛ خرابی داده تزریق و اجرا نشد|
|A05|P1|HEAD فعلی deploy گیت سبز کامل و شاهد runtime موفق ندارد|قطعی از GitHub check/job metadata؛ علت ریشه‌ای کامل نامعلوم|
|A06|P2|schema ورودی counsel ضعیف و باعث 500 قابل‌پیش‌بینی می‌شود|قطعی در تحلیل مسیر؛ HTTP اجرا نشد|
|A07|P2|مشاوره بر نتایج ادعایی client تکیه می‌کند|قطعی در data flow؛ سوءاستفادهٔ مدل آزمایش نشد|
|A08|P2|محدودکنندهٔ process-local و ترتیب زمانی شکننده است|قطعی در source؛ اثر همزمانی عملاً بازتولید نشد|
|A09|P2|اعتبار یک journey به پاسخ‌های ثابت bind نشده است|قرارداد فعلی قطعی؛ «نقض محصول» نیازمند تصمیم مالک|
|A10|P2|توکن در localStorage و تناقض سند CSP|ذخیرهٔ JS-readable قطعی؛ header واقعی مرورگر بررسی نشد|
|A11|P2|root و diagnostics جایگزین readiness نیستند|قطعی در routeها|
|A12|P2|build وابستگی‌ها بازتولیدپذیر نیست|قطعی در requirements/workflow|
|A13|P2|سیاست حریم خصوصی با جریان واقعی AI جزئیات کافی ندارد|قطعی در policy main و data flow؛ نظر حقوقی نیست|
|A14|P2|موانع CI داخل PR مستقل از خود کد PR نیستند|قطعی در workflow؛ تنظیمات محیط GitHub اثبات‌نشده|
|A15|P2|بخشی از تست P0 به ref متحرک دیگری متصل است|قطعی در workflow|
|A16|P3|fallback سرویس‌ورکر نوع پاسخ را حفظ نمی‌کند|قطعی در source main؛ مرورگر اجرا نشد|
|A17|P2|callback پرداخت به Host مشتق‌شده fallback می‌کند|قطعی در source؛ قابلیت سوءاستفاده به proxy بستگی دارد|
|A18|P3|محدودیت byte به‌تنهایی سقف زمان/تعداد chunk نیست|قطعی در loop؛ امکان حملهٔ عملی اثبات‌نشده|

### A01 — P1: main بک‌اند مستقلِ قابل ساخت ندارد
- **وضعیت:** قطعی در source؛ اجرای startup انجام نشد
- **شاهد:** main_v2.py:15–19 در main ماژول‌های admin_router، commercial_api و feedback_api را import می‌کند، اما این فایل‌ها در tree فعلی main نیستند. auth_service، database و trait_map_v3.json ریشه نیز غایب‌اند. main_v2.py و requirements فعلی main بایت‌معادل checkout بررسی‌شده‌اند. requirements main تنها FastAPI/Uvicorn/Pydantic دارد؛ httpx مورد نیاز ai_counsel_service نیز تصریح نشده است. راهنمای اجرای README با این tree سازگار نیست.
- **اثر:** کلون تازهٔ main مسیر مستندشدهٔ backend را در محیط استاندارد با شکست import روبه‌رو می‌کند. این عیب main است، نه اثبات خرابی backend deploy.
- **اصلاح پیشنهادی:** قرارداد branchها را روشن کنید: main فقط frontend است یا باید backend هم بسازد؟ CI smoke import/build بدون DB، بسته‌بندی مستقل و README دقیق لازم است. انتقال خودکار تمام deploy به main مجاز نیست.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/fbdee3e01e95a37468de680eeded63f13cad9c8b/main_v2.py#L15

### A02 — P1: قرارداد canonical با وضع واقعی main/deploy ناسازگار است
- **وضعیت:** قطعی از blobها و گام CI
- **شاهد:** از شش فایل مرجع، micro_motives، majors و school_branches با main متفاوت‌اند؛ guard برابری دقیق blob با main می‌طلبد. آخرین job postgres-staging-audit در همین گام شکست دارد.
- **اثر:** آمادگی cutover یا سازگاری مرجع قابل تأیید نیست؛ توسعهٔ علمی عملاً روی منبع دیگری از main ادامه یافته است.
- **اصلاح پیشنهادی:** مالک باید مسیر پذیرش تغییرهای مرجع، منشأ هر اختلاف و ترتیب PRهای محدود را تعیین کند. expected یا guard را برای سبزشدن تغییر ندهید و sync کلی نکنید.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/reference_data_sync_audit.py#L13

### A03 — P1: مسیر login محدودکنندهٔ تلاش ندارد
- **وضعیت:** قطعی در فایل‌های برنامهٔ خوانده‌شده؛ وضعیت WAF نامعلوم
- **شاهد:** commercial_api.py:217–241 مستقیماً authenticate_user را اجرا می‌کند؛ main فقط body cap این مسیر را دارد و limiter آن برای discovery/counsel است. auth_service.py:120 به ازای هر تلاش معتبرنام PBKDF2 اجرا می‌کند. در این مسیر شمارش تلاش/lockout مشاهده نشد.
- **اثر:** credential stuffing و بار CPU با PBKDF2 گران ممکن است. از نبود کنترل app، نبود WAF واقعی نتیجه نمی‌شود.
- **اصلاح پیشنهادی:** محدودیت ترکیبی حساب/IP، backoff و پاسخ غیرقابل‌شناسایی حساب، با مخزن مشترک برای چند replica و بررسی مستقل edge. تست امنیتی باید در محیط مجاز انجام شود.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/commercial_api.py#L217

### A04 — P1: بارگذاری داده و schema موتور fail-open است
- **وضعیت:** قطعی در source؛ خرابی داده تزریق و اجرا نشد
- **شاهد:** dark_horse_engine_v2.py:39–79 خطاهای خواندن را گرفته و map خالی می‌گذارد؛ _validate_schema_consistency:94–129 برای کلید/شکل S نامعتبر warning می‌دهد نه توقف. main تنها در صورت exception واقعی engine=None می‌کند.
- **اثر:** فایل مفقود یا آسیب‌دیده می‌تواند به موتور ظاهراً آماده با دادهٔ ناقص و خروجی خالی/ناقص منجر شود؛ نبود فایل trait در main نمونهٔ ملموس همین ریسک است.
- **اصلاح پیشنهادی:** اعتبارسنجی قطعی قبل از ready شدن: schema، یکتایی ID/code، شکل/دامنه/مجموع، کلید سؤال، عضویت و hash manifest؛ startup یا readiness در نقص reference باید fail closed شود.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/dark_horse_engine_v2.py#L39

### A05 — P1: HEAD فعلی deploy گیت سبز کامل و شاهد runtime موفق ندارد
- **وضعیت:** قطعی از GitHub check/job metadata؛ علت ریشه‌ای کامل نامعلوم
- **شاهد:** روی SHA فعلی، backend در Reference-data integrity، hybrid در canonical sync و runtime-lock در Verify live Liara root is online شکست دارند. لاگ کامل و probing زنده در این ممیزی اجرا نشد.
- **اثر:** اعلام «live سبز» یا release-ready مجاز نیست. شکست root به‌تنهایی ثابت نمی‌کند downtime سراسری رخ داده؛ می‌تواند از شبکه/timeout نیز باشد. علت fingerprint را از گزارش قبلی به SHA جدید تعمیم نمی‌دهیم.
- **اصلاح پیشنهادی:** لاگ همان runها و شاهد مستقیم همان SHA را بررسی کنید؛ incident review و رفع محدود در PR مستقل. از rerun کور یا تغییر expected پرهیز شود.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/.github/workflows/liara-runtime-lock.yml#L19

### A06 — P2: schema ورودی counsel ضعیف و باعث 500 قابل‌پیش‌بینی می‌شود
- **وضعیت:** قطعی در تحلیل مسیر؛ HTTP اجرا نشد
- **شاهد:** main_v2.py:675 بدنه را dict می‌گیرد؛ profile=request.get("profile") or {}. برای profile غیرخالیِ list/string، خط 698 profile.get و خط 714 unpack بدون اعتبارسنجی نوع انجام می‌شود. وقتی journey_type داده شده باشد برخی مسیرها دیرتر fail می‌کنند.
- **اثر:** کاربر دارای journey مجاز می‌تواند 500 ایجاد کند و نوع خطا به جای 422 کنترل‌شده نامشخص است.
- **اصلاح پیشنهادی:** مدل Pydantic برای profile/results/mode با نوع‌ها، طول رشته‌ها و enumهای محدود؛ ورودی‌های object/list/string/null/عدد را با تست آفلاین بررسی کنید.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/main_v2.py#L674

### A07 — P2: مشاوره بر نتایج ادعایی client تکیه می‌کند
- **وضعیت:** قطعی در data flow؛ سوءاستفادهٔ مدل آزمایش نشد
- **شاهد:** counsel پس از بررسی charged journey، top_results و evidence را از بدنهٔ client می‌گیرد و به AI می‌فرستد؛ آن‌ها از نتیجهٔ ذخیره‌شدهٔ سرور بازسازی نمی‌شوند. _clean در ai_counsel_service sanitizer متنی است نه اثبات منشأ علمی.
- **اثر:** توضیح علمی می‌تواند برای نمره/شواهد ساختگی ساخته شود و prompt injection با فیلتر regex قابل تضمین نیست. این به معنی تغییر نمرهٔ خود موتور نیست.
- **اصلاح پیشنهادی:** نتایج و شواهد را با journey مالک از سرور استخراج کنید؛ ورودی client فقط انتخاب مورد/حالت باشد. محتوای مدل دادهٔ غیرقابل‌اعتماد بماند.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/main_v2.py#L696

### A08 — P2: محدودکنندهٔ process-local و ترتیب زمانی شکننده است
- **وضعیت:** قطعی در source؛ اثر همزمانی عملاً بازتولید نشد
- **شاهد:** ai_rate_limit.py:41 clock را قبل از lock می‌خواند؛ threadها می‌توانند timestampها را خلاف ترتیب append کنند و فرض مرتب‌بودن deque را بشکنند. هر worker map مستقل دارد، restart پاک می‌کند، eviction هویت‌ها را حذف می‌کند؛ client.host به تنظیم trusted proxy وابسته است.
- **اثر:** محدودیت سراسری هزینه/بار تضمین نمی‌شود؛ NAT می‌تواند کاربران مستقل را یکی کند و replicaهای متعدد سقف مؤثر را افزایش دهند.
- **اصلاح پیشنهادی:** clock داخل critical section؛ تست clock/همزمانی مستقل؛ سیاست identity و proxy مستند؛ سقف per-account و بودجهٔ مشترک/edge برای scale-out. وجود localhost یا نام staging اثبات امنیت نیست.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/ai_rate_limit.py#L38

### A09 — P2: اعتبار یک journey به پاسخ‌های ثابت bind نشده است
- **وضعیت:** قرارداد فعلی قطعی؛ «نقض محصول» نیازمند تصمیم مالک
- **شاهد:** _require_charged_journey فقط user_id/session_uuid ledger را کنترل می‌کند؛ discover پاسخ‌های تازهٔ بدنه را score می‌کند. counsel نیز روی همان UUID می‌تواند بارها متن تولید کند. محدودیت تعداد AI call بر journey در این مسیر دیده نشد.
- **اثر:** اگر یک اعتبار باید یک ارزیابی immutable باشد، استفادهٔ مجدد UUID نتایج متعدد و هزینهٔ AI ایجاد می‌کند؛ اگر retry/reassessment عمدی باشد نقص قطعی محصول محسوب نمی‌شود.
- **اصلاح پیشنهادی:** سیاست retry در برابر تغییر پاسخ را تصویب کنید؛ در صورت نیاز input digest/result version و سقف AI per-journey اضافه شود، با حفظ idempotency و retry مشروع.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/main_v2.py#L400

### A10 — P2: توکن در localStorage و تناقض سند CSP
- **وضعیت:** ذخیرهٔ JS-readable قطعی؛ header واقعی مرورگر بررسی نشد
- **شاهد:** docs/auth_api_client.js:4–12 توکن session را در dh_auth_v1 می‌نویسد؛ XSS هم‌مبدأ امکان خواندن دارد. SECURITY_AUTH_HARDENING_PLAN مدعی CSP inline-script-free است، اما index checkout inline script و onload/onerror دارد و meta CSP در آن مشاهده نشد. CSP ارسال‌شده توسط CDN اثبات نشده است.
- **اثر:** ریسک theft در صورت XSS؛ وجود innerHTML به‌تنهایی اثبات XSS نیست. مسیر نمایش counseling در app.js:3198 escapeHtml دارد و نباید بی‌دلیل آسیب‌پذیر اعلام شود.
- **اصلاح پیشنهادی:** برنامهٔ migration cookie HttpOnly/Secure/SameSite به همراه CSRF و CORS درست؛ CSP ابتدا report-only و سپس nonce/hash، حذف handlerهای inline؛ بررسی header واقعی با مجوز جدا.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/docs/auth_api_client.js#L4

### A11 — P2: root و diagnostics جایگزین readiness نیستند
- **وضعیت:** قطعی در routeها
- **شاهد:** GET / همواره status=online برمی‌گرداند؛ startup خطاهای engine/DB را log می‌کند و ادامه می‌دهد. __runtime_fingerprint جزئیات module path/routeها را بدون auth منتشر می‌کند و تطابق hash هم سلامت DB/AI یا صحت علمی را ثابت نمی‌کند.
- **اثر:** مانیتور ممکن است حالت خراب را سالم بداند؛ diagnostics عمومی سطح اطلاعات داخلی را بیشتر می‌کند.
- **اصلاح پیشنهادی:** liveness/readiness/build-info را تفکیک کنید؛ readiness بر engine/reference و وابستگی ضروری اتکا کند؛ اطلاعات debug را محدود کنید و probeها را از مهاجرت DB جدا نگه دارید.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/main_v2.py#L307

### A12 — P2: build وابستگی‌ها بازتولیدپذیر نیست
- **وضعیت:** قطعی در requirements/workflow
- **شاهد:** در deploy dependencyها range هستند، در main سه dependency بدون سقف دقیق؛ lock/hash manifest در مسیر نصب خوانده‌شده نیست. workflowها pip را upgrade می‌کنند و actions عمدتاً tag v4/v5 هستند نه commit SHA immutable؛ postgres:16 نیز tag متحرک است.
- **اثر:** تغییر dependency/runner/image بدون تغییر source می‌تواند نتیجه را عوض کند. وجود CVE مشخص از این ممیزی ادعا نمی‌شود؛ اسکن advisory و dependency resolution انجام نشد.
- **اصلاح پیشنهادی:** lock تولیدشده در محیط معتبر، hashes/SBOM، pin actions/image و برنامهٔ آپدیت مستقل؛ بعد از lock تست سازگاری و security review لازم است.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/requirements.txt#L1

### A13 — P2: سیاست حریم خصوصی با جریان واقعی AI جزئیات کافی ندارد
- **وضعیت:** قطعی در policy main و data flow؛ نظر حقوقی نیست
- **شاهد:** privacy.html فقط توضیح کلی آزمون/حساب/پرداخت/فروش‌نرفتن داده دارد؛ AI counseling دادهٔ پروفایل و شواهد را به Cloudflare می‌فرستد. policy موجود دربارهٔ این پردازشگر، دورهٔ نگهداری، مبنای پردازش و مخاطب کم‌سن صریح نیست. policy روی دامنهٔ واقعی بررسی نشد.
- **اثر:** شفافیت و رضایت/حذف داده قابل ارزیابی نیست؛ محل کاربر به‌تنهایی قانون لازم‌الاجرا را تعیین نمی‌کند.
- **اصلاح پیشنهادی:** data map و minimization، processor/retention و مسیر حذف/دسترسی را مستند کنید؛ بازبینی حقوقی متناسب با حوزهٔ فعالیت و سن کاربران، بدون ادعای قطعی نقض قانون.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/ai_counsel_service.py#L1

### A14 — P2: موانع CI داخل PR مستقل از خود کد PR نیستند
- **وضعیت:** قطعی در workflow؛ تنظیمات محیط GitHub اثبات‌نشده
- **شاهد:** Hybrid کد head PR و requirements همان PR را اجرا می‌کند؛ service DB و mock تنظیم می‌کند اما این‌ها به‌تنهایی مهار مستقل خروج شبکه/credentials نیستند. prod-migration-once از PRODUCTION_DATABASE_URL و environment production-migration استفاده می‌کند؛ وجود reviewerهای مستقل آن از source قابل احراز نیست.
- **اثر:** تست PR می‌تواند guard داخل همان PR را عوض کند؛ نام sandbox و APP_ENV مرز اعتماد مستقلی نیست. وقوع دسترسی غیرمجاز یا نبود approval واقعی ادعا نمی‌شود.
- **اصلاح پیشنهادی:** اثبات organization/environment protections، least-privilege و جداسازی credentials/network خارج کنترل PR؛ تفکیک job عملیاتی از job untrusted و ثبت policy reviewer؛ هیچ gate حذف نشود.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/.github/workflows/hybrid-migration-audit.yml#L52

### A15 — P2: بخشی از تست P0 به ref متحرک دیگری متصل است
- **وضعیت:** قطعی در workflow
- **شاهد:** p0-contracts.yml:20–38 source_ref هر matrix را deploy تعیین و checkout همان ref را اجرا می‌کند، نه لزوماً SHA همان commit/PR مورد ممیزی. این workflow روی p0/** یا dispatch فعال است؛ در main نیز CI عمدتاً JS/frontend است و smoke backend ندارد.
- **اثر:** سبزشدن تست می‌تواند branch دیگر را تأیید کند؛ provenance تست باید صریح باشد. سبز main ثابت نمی‌کند backend main سالم است.
- **اصلاح پیشنهادی:** subject_sha و fixture_sha را جدا و pinned ثبت کنید؛ تست تغییرات باید روی artifact همان SHA اجرا شود، نه با تغییر expectations. پوشش نبود dependency در main با smoke غیرعملیاتی اضافه شود.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/.github/workflows/p0-contracts.yml#L20

### A16 — P3: fallback سرویس‌ورکر نوع پاسخ را حفظ نمی‌کند
- **وضعیت:** قطعی در source main؛ مرورگر اجرا نشد
- **شاهد:** docs/sw.js:109–119 حتی برای JSON در offline miss می‌تواند cached index.html را برگرداند؛ comment بالای فایل JSON را network-only می‌خواند ولی کد آن را Cache Storage نیز می‌کند. cache: no-store مربوط به fetch HTTP است، نه منع Cache Storage.
- **اثر:** JSON parser با HTML خطا می‌دهد یا JSON قدیمی نمایش داده می‌شود؛ ترکیب نسخه‌های shell/data محتمل است. نمی‌توان offline-first را صرفاً از این کد تأیید کرد.
- **اصلاح پیشنهادی:** fallback نوع‌محور: JSON پاسخ JSON خطای کنترل‌شده یا cache نسخه‌دار همان قرارداد؛ HTML فقط برای navigation. سناریوی offline/upgrade و دادهٔ stale جدا تست شود.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/fbdee3e01e95a37468de680eeded63f13cad9c8b/docs/sw.js#L109

### A17 — P2: callback پرداخت به Host مشتق‌شده fallback می‌کند
- **وضعیت:** قطعی در source؛ قابلیت سوءاستفاده به proxy بستگی دارد
- **شاهد:** commercial_api.py:142 اگر BILLING_CALLBACK_URL تنظیم نباشد request.base_url را مبنا می‌گیرد. billing_api.py:28 فقط scheme http/https و netloc را کنترل می‌کند؛ allowlist host در این validator نیست.
- **اثر:** اگر Host/forwarded-host در لبه مهار نشود مقصد callback می‌تواند غیرمنتظره شود؛ این مسیر خودبه‌خود SSRF اثبات‌شده نیست و وضعیت gateway/proxy واقعی نامعلوم است.
- **اصلاح پیشنهادی:** callback ثابت HTTPS و host allowlist، fail closed در production و TrustedHost/proxy policy؛ تست Host در محیط شبیه‌سازی‌شده مجاز، نه با درگاه واقعی.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/commercial_api.py#L142

### A18 — P3: محدودیت byte به‌تنهایی سقف زمان/تعداد chunk نیست
- **وضعیت:** قطعی در loop؛ امکان حملهٔ عملی اثبات‌نشده
- **شاهد:** request_body_limit_middleware.py:56–74 هر ASGI message را تا پایان در deque نگه می‌دارد ولی فقط body bytes را جمع می‌زند؛ cap تعداد message/زمان داخل middleware نیست. chunkهای کم‌حجم می‌توانند overhead بیشتری از byte cap داشته باشند.
- **اثر:** ریسک مصرف connection/memory در slow upload؛ سطح عملی به ASGI server و reverse proxy بستگی دارد.
- **اصلاح پیشنهادی:** timeout/minimum upload rate در edge، buffering محدود و تجمیع chunk به‌جای نگهداری metadata نامحدود؛ body cap موجود حفظ شود.
- **source pinned:** https://github.com/arad2000/dark-horse-v2-/blob/8c87cb5d879e166a6052ea90a8d63b22d2118aa3/request_body_limit_middleware.py#L56

## ۴. سلامت داده — تفکیک checkout و deploy
|کنترل|checkout قدیمی|deploy فعلی pinned|
|---|---:|---:|
|کل رشته‌ها|230|۲۳۰|
|فعال motive_driven|202|202|
|عضویت شاخه معتبر|176/۲۰۲|202/۲۰۲|
|کد canonical پوشش‌داده‌شده|1393|1393|
|مجموع raw pool|1400|1393|
|overlap|0|0|
|اعضای دارای شاخهٔ معتبر ولی pool ناقص|۰|۰|

در deploy: تجربی ۵۶، ریاضی ۶۱، انسانی ۵۹، فنی ۲۶. active_S_errors=[]، active_V_errors=[]، branch_S_errors=[]؛ این فقط شکل 25×5، کلیدهای ۳۰تایی، دامنه و مجموع با tolerance 0.001 است، نه اعتبار علمی وزن‌ها. ۲۸ ردیف غیرفعال checkout S/V کامل ندارند و نباید به‌عنوان نقص وزن فعال گزارش شوند.
در checkout هفت BIOTM خارج canonical حضور دارند؛ در deploy فعلی raw=۱۳۹۳ و این مازاد وجود ندارد. بنابراین عدد تاریخی ۱۴۰۰ نباید به وضعیت فعلی تعمیم یابد. منشأ حذف آن در این ممیزی تاریخچه‌کاوی نشده است.
تعداد زوج‌های V متمایز با epsilon=0.02 در deploy: تجربی ۱۵، ریاضی ۱۵، انسانی ۱۵، فنی ۱۳. دو زوج کم‌تمایز به‌خودی‌خود bug نیستند؛ رفتار پاسخ ناقص باید قرارداد explicit داشته باشد. آزمایش ۳۴۰/۶ نوبت‌های قبل در این ممیزی دوباره اجرا نشد و PASS جدید برای آن‌ها اعلام نمی‌شود.

## ۵. اختلاف مرجع main/deploy
SHAهای جدول زیر Git blob SHA1 هستند، نه commit SHA و نه SHA256.
|فایل|main blob|deploy blob|برابر؟|
|---|---|---|---|
|docs/data/micro_motives.json|`9a5c32831ed3a1f2d1371add4f29f46f35969b29`|`c59ab2a5d82283d2c4a5f503c42190e1740af780`|خیر|
|docs/data/questions_v2.json|`17f0d764538657e1f8b4b5efe2dad8a6bf368bb3`|`17f0d764538657e1f8b4b5efe2dad8a6bf368bb3`|بله|
|docs/data/trait_map_v3.json|`466280fe517b7e6ba68e54dbe8535de7444c7f4a`|`466280fe517b7e6ba68e54dbe8535de7444c7f4a`|بله|
|majors_database_v2.json|`64d109af28359ec692bc1e4a0647d65558e4b18b`|`abce609d8a8683f0168d251718e3f743b03dd2b7`|خیر|
|school_branches_v2.json|`cac4c01388a04fee5879daeefef0c6983228d976`|`abb7b08a6686a570f997a872fd13b3b0683a67a8`|خیر|
|value_poles_v2.json|`251d435d57b90e325ff671a4f8c69c530de61494`|`251d435d57b90e325ff671a4f8c69c530de61494`|بله|

## ۶. CI موجود — فقط خواندن، نه اجرا
روی HEAD main چهار check موجود publish/verify/purchase-ui/catalog-motive-contracts موفق بودند؛ این نتیجهٔ GitHub است نه تستی که در این نشست اجرا شده باشد. روی deploy password-reset-contract، verify و quota-regression موفق، publish skipped و سه مورد زیر شکست دارند:
|job|گام شکست مستقیم|لینک|
|---|---|---|
|postgres-staging-audit|Verify canonical reference data matches main|https://github.com/arad2000/dark-horse-v2-/actions/runs/40432566861/job/121953523350|
|backend|Reference-data integrity|https://github.com/arad2000/dark-horse-v2-/actions/runs/40432566701/job/121953523120|
|runtime-lock|Verify live Liara root is online|https://github.com/arad2000/dark-horse-v2-/actions/runs/40432566693/job/121953522833|

منبع: API check-runs و actions/jobs همان SHA. لاگ کامل assertion/stacktrace و actual fingerprint در این نوبت دریافت نشد. نام گام «Reference-data integrity» مکان assertion را ثابت نمی‌کند؛ نسبت‌دادن line240 گزارش قدیمی به این SHA بدون لاگ فعلی مجاز نیست. شکست migration/concurrency روی parent فعلی: **اثبات‌نشده**. موفقیت یا شکست run روی SHA دیگر، شاهد مستقیم این SHA محسوب نمی‌شود.

### مسیرهای اثرگذار workflow
- Hybrid PR به main/deploy و push deploy: service PostgreSQL، نصب کد/requirements head PR، canonical guard، Alembic و تست‌های DB.
- Commercial Backend CI و quota regression شامل Alembic هستند؛ صرف ساخت Draft PR به معنی بی‌اثر بودن نیست.
- Evaluator Closeout Rehearsal روی PR مقصد deploy شامل DB rehearsal و Seeder است.
- Liara Runtime Lock روی push deploy یا dispatch به API زنده درخواست خواندنی می‌زند؛ در این نشست اجرا نشد.
- Production DB Migration Once دستی، محدود به ref deploy و عبارت تأیید و environment production-migration است و Secret با نام PRODUCTION_DATABASE_URL مصرف می‌کند. policy approval این environment خارج source اثبات‌نشده است.
- frontend publish در push main می‌تواند Pages را منتشر کند؛ بنابراین push سند نیز ممکن است اثر انتشار داشته باشد. هیچ push انجام نشد.

## ۷. پرداخت، احراز هویت و نقاط مثبت مشاهده‌شده
- PBKDF2-SHA256 با ۶۰۰هزار iteration و salt تصادفی؛ bearer token با SHA256 ذخیره و با انقضا/ابطال session کنترل می‌شود. این ساختار مثبت است، ولی جایگزین rate limit login نیست.
- مسیرهای discovery/counsel در deploy نیازمند session احراز‌شده و ledger اعتبار همان user/journey هستند؛ خطای lookup fail closed است.
- مصرف اعتبار با قفل User و ledger session_uuid unique و payment verify با قفل PostgreSQL و idempotency بررسی می‌شوند. مبلغ و بسته از برنامهٔ سرور می‌آیند؛ صرف status callback به معنی موفقیت پذیرفته نمی‌شود.
- پرداخت production guard صریح و حالت free-only دارد. env واقعی و فعال‌بودن guard روی live بررسی نشد؛ APP_ENV به‌تنهایی اثبات هویت عملیاتی نیست.
- محدودیت body پیش از JSON parse در deploy وجود دارد؛ CORS deploy محدود به origin مصوب مشاهده شد. CORS ابزار احراز هویت یا مانع curl نیست.
- خروجی متن AI در مسیر frontend خوانده‌شده escapeHtml می‌شود؛ از وجود innerHTML ادعای XSS قطعی نمی‌شود.
- admission در API deploy به‌صراحت capacity/cutoff تاریخی را از «احتمال قبولی عددی» جدا و disclaimer دارد. صحت اعداد دفترچه/سنجش ۱۴۰۵ یا رسمیت منبع در این ممیزی تأیید نشده است.

## ۸. کنترل‌های واقعاً اجراشده و اجرا‌نشده
### اجراشده
- ۳۶ فایل Python ریشهٔ checkout و نمونهٔ deploy با ast.parse بررسی شدند: صفر SyntaxError. این parsing بدون import و بدون اجرای کد هدف است.
- ۳۱ فایل JS ریشهٔ docs با node --check: exit=0 برای همه؛ این فقط syntax است نه browser/E2E.
- JSON parse و کنترل یکتایی، عضویت، pool overlap/coverage، شکل S/V و blob identity؛ نتایج در بخش داده ثبت شد.
- خواندن مستقیم refs/tree/check/job/PR metadata از GitHub؛ هیچ درخواست نوشتنی ارسال نشد.
### اجرا نشده
- unittest/pytest/Node regression suite، API startup، اجرای scorer و fixtureهای ۳۴۰/۶، browser/PWA/پرداخت end-to-end.
- DB، Alembic، Seeder، backup/restore drill، concurrency/load test، تست امنیت فعال، درخواست Cloudflare یا Liara.
- نصب dependency و اسکن CVE/secret کامل/history؛ هیچ ادعای نبود secret یا نبود CVE نداریم.
- GitHub branch protections، environment reviewer، organization policies، network egress isolation، retention واقعی، تنظیم reverse proxy/WAF، RPO/RTO و fingerprint زنده مستقلاً اثبات نشدند.

## ۹. نقشهٔ اصلاح مرحله‌ای
۱. **منبع حقیقت و build:** تصمیم رسمی دربارهٔ main/deploy و source manifest؛ smoke بدون DB و رفع missing backend packaging در main یا اصلاح رسمی قرارداد frontend-only. بدون sync عمومی.
۲. **موانع فعلی CI:** دریافت لاگ سه run همین SHA و تفکیک fingerprint تاریخی، canonical drift و عدم دسترسی runtime. عدم تغییر expected صرفاً برای سبزشدن؛ هر علت PR اتمیک مستقل.
۳. **امنیت ورودی/هزینه:** login rate limit مشترک، schema counsel، نتایج server-authoritative و سیاست journey reuse/AI budget؛ شواهد proxy/edge.
۴. **سلامت startup و عملیات:** fail-closed reference loading، readiness واقعی، release manifest و artifact immutable؛ migration و backup drill فقط با مجوز محیطی مستقل.
۵. **Frontend/حریم خصوصی:** token/cookie+CSRF migration، CSP سازگار با inline handlers، JSON offline قرارداددار، data map/retention/processor policy.
۶. **بازبینی علمی:** ادامهٔ وزن‌دهی فقط با پروتکل و شواهد مصوب، تفکیک S و V و معیار incomplete؛ نه تغییر threshold یا فرمول برای سبزکردن نتیجه.

### حد پذیرش پیشنهادی پیش از اعلام آمادگی انتشار
- commit subject و artifact source روشن؛ canonical policy در عمل برقرار و تمام شکست‌های required check تعیین تکلیف شده باشند.
- startup روی reference ناقص fail closed؛ readiness نسخه/engine/schema لازم را گزارش کند.
- login abuse و counsel schema با تست مستقل مجاز پوشش داده شوند؛ هیچ راه دورزدن quota بدون تصمیم سیاستی باقی نماند.
- بودجهٔ AI، credential/network isolation و recovery شواهد مستقل داشته باشند؛ نام محیط به‌تنهایی کافی نیست.
- هیچ حکم Go برای تغییر وزن یا Merge از این گزارش صادر نمی‌شود.

## ۱۰. وضعیت PRها و عدم تغییر
#304 در زمان خواندن CLOSED و mergedAt=null؛ #305 و #306 MERGED بودند. mergeها از قبل بیرون این نشست رخ داده‌اند. این ممیزی هیچ PR، branch، commit یا ref را تغییر نداد. هیچ gate، موتور، scientific JSON، پرداخت، Liara یا env تغییر نکرد؛ تنها سند ممیزی در checkout افزوده شد.

## ۱۱. شواهد محلی قابل بازبینی
فایل‌های شواهد زیر در /home/user/project-audit/ نگهداری شدند؛ sourceها در deploy/ هستند. این مسیر شامل source خوانده‌شده از GitHub است نه دادهٔ عملیاتی یا env زنده. هیچ مقدار Secret خوانده/نمایش داده نشد.
- remote-refs.json، main-tree.json، deploy-tree.json
- local-metrics.json، deploy-metrics.json، canonical-comparison.json
- imports.json، syntax-python.json، syntax-js.json
- checks-main.json، checks-deploy.json، failed-steps.json، pr304/305/306.json

### SHA256 اسناد شواهد
|فایل|SHA256|
|---|---|
|canonical-comparison.json|`e0a37c65f54eb30fdfe5cdfa97d72485c2d1e1cf1bc85a8c1900f1d9e469dbf6`|
|checks-deploy.json|`7f8972bd9d88fe90bd4a1b5f87cf3c19fee9147102f06c1e33db3d12a1a0c6f5`|
|checks-main.json|`3810945a2b66af289122e257dd74db378821fd49d851c236f332b9073dc1dbbd`|
|deploy-metrics.json|`fd2bfa8fbbb67bb1e7d02c1f6562f3874ed5268d1766374167e3c9bf8b9a71da`|
|deploy-tree.json|`53ccf973571d9679057ea2fab2c7b47da7684723f1b07260bbb4dda724cb2589`|
|failed-steps.json|`20cc77efc34aa2b272e11844b600a701652a8a76fc5df60f8d79350a92ce30c6`|
|imports.json|`0ce0c390b30a6c32680b6a1717131aa9ce1d06657a7f583359641c349011b1bc`|
|local-metrics.json|`ba3b94968c8cda148b9013062e364deec16f37ea4a5325bd7930854d9be38373`|
|main-tree.json|`71a7815feb563364fbfe486b9d908a18d6f2f2979137e4e2818451f81f1df494`|
|pr304.json|`ed4a52928d2862eae16a310d4397358c66a8b63c8c0a408c64ce52af5406b132`|
|pr305.json|`1404117d6187747b7f99be42f4217fdc402016362c03940a66087ef730ce54b7`|
|pr306.json|`486167d1bca5081e8df7507ba60b4574da48ac39ae0076c9fa73549bf0f69c24`|
|remote-refs.json|`59bf0b09a001b5304e835bfda496e04ce0e861b60f4fcfaab36cbfdadcef86f0`|
|syntax-js.json|`a62383cfb659df10cf11306c08c2c97f879f3b9dadf05acc78b3f1888bc76327`|
|syntax-python.json|`9d3e4e095c9c25ebb4324f24ff93313adff985bcbb53d47c8cb6ea1a44c13467`|
