# فاز ۱ — آماده‌سازی آرتیفکت عمومی فرانت برای لیارا

**محدودهٔ اجراشده: build محلی + allowlist + تست و سند. بدون mount، publish، DNS، قطع Pages یا تغییر runtime.**

## ۱. ref فرانت production و سطح اثبات

- منبع قفل‌شدهٔ فایل‌ها: main در `4b918261f3f7996439e6f9c98fe83f81f7df3c8d`. اسکریپت به moving ref مانند main/HEAD اعتماد نمی‌کند؛ فقط SHA کامل ثبت‌شده در allowlist پذیرفته می‌شود.
- پاسخ Pages API: source=`main:/docs`، build_type=`workflow`، cname=`asbe-siah.ir`، status=`built`.
- آخرین اجرای موفق workflow «Publish frontend from main»: [run 41283772225](https://github.com/arad2000/dark-horse-v2-/actions/runs/41283772225)، headSha همان SHA بالاست؛ jobهای verify و publish و مرحلهٔ «Deploy GitHub Pages» همگی success هستند.
- بنابراین این ref، آخرین **منبع انتشار موفق ثبت‌شدهٔ Pages** است. پاسخ HTTP فعلی سایت یا APK دانلود نشده؛ تطبیق byteهای CDN/cache/دستگاه با آن را ادعا نمی‌کنیم.
- ref مقایسهٔ backend/deploy: `9e5342351fb149b5c2a26a2a1e32ce2fd011aeb7`. main و deploy در این گزارش به معنای دو بستهٔ همسان نیستند.
- PR این آماده‌سازی به **main** است: ابزار تولید آرتیفکت از منبع فرانت production، بدون دست‌زدن به backend deploy. Merge، انتقال انتخاب‌شدهٔ فرانت به release backend و اتصال آرتیفکت به runtime مجوز جدا می‌خواهد.

## ۲. فایل‌ها و خروجی build

| فایل جدید | نقش |
|---|---|
| `scripts/frontend/public_allowlist.json` | فهرست دقیق ۶۴ asset، SHA منبع، ریشهٔ docs و شمارهٔ اجرای Pages؛ بدون wildcard |
| `scripts/frontend/build_public_artifact.py` | stdlib + git؛ استخراج از Git blobهای commit قفل‌شده؛ بدون import کد برنامه، networking یا publish |
| `tests/test_frontend_public_artifact.py` | ۱۶ تست offline برای ساخت، hash، exclusions، symlink، path و عدم overwrite |
| همین Markdown | فهرست allowlist، تفاوت‌ها، شواهد و پذیرش اجرا‌نشدهٔ لیارا |

### اجرای تکرارپذیر

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/frontend/build_public_artifact.py \
  --output /home/user/frontend-phase1-output/public
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover \
  -s tests -p test_frontend_public_artifact.py -v
```

مسیر خروجی باید **جدید و ناموجود** باشد؛ ابزار چیزی را پاک یا overwrite نمی‌کند. اگر commit منبع در clone کم‌عمق غایب باشد، ابزار fail می‌کند؛ دریافت اشیای Git باید جدا و صریح انجام شود. ابزار خودش fetch نمی‌کند.
خروجی می‌تواند `dist/<new-name>/public` یا مسیر جدید خارج repo باشد. نوشتن داخل docs یا سایر مسیرهای منبع repo ممنوع است. خروجی تولیدشده را وارد Git نکنید؛ در این اجرا تمام خروجی‌ها بیرون repo ساخته شدند.
- `public/`: فقط assetهای allowlisted با حفظ byteهای منبع.
- `public.evidence.json`: **کنار public، نه داخل ریشهٔ قابل سرو**؛ شامل commit، hash allowlist، Git blob، اندازه و SHA-256 هر فایل. این گزارش hash، fingerprint علمی را تغییر نمی‌دهد.
- ساخت از Git tree/blob است؛ dirty working tree یا فایل اضافی در docs وارد artifact نمی‌شود. تمام read/validationها پیش از ایجاد public انجام می‌شوند. در خطای نوشتن/sidecar، موفقیت اعلام نمی‌شود؛ خروجی را بدون evidence معتبر deploy نکنید.
- dependencyهای مستقیم HTML (script/link/img/srcset)، CSS url و آیکن manifest کنترل می‌شوند و فقدان فایل خطاست. URL پویا در JavaScript به‌طور کامل از تحلیل استاتیک قابل اثبات نیست؛ allowlist بازبینی‌شده و آزمون مرورگر در پذیرش الزامی است. dependencyهای خارجی fetch/بازبسته‌بندی نمی‌شوند.
- کد HTML/JS و API_BASE، SW، پرداخت یا guardها **بازنویسی نمی‌شوند**؛ این آرتیفکت معادل byteهای production است، نه ادعای آماده‌بودن API same-origin روی هر hostname.

## ۳. allowlist صریح

تنها JSONهای مجاز: `manifest.json`، `majors_catalog_ui_v1.json`، `trait_map_v3.json`، و سه فایل `data/micro_motives.json`، `data/questions_v2.json`، `data/trait_map_v3.json`. این‌ها پیش‌تر در tree عمومی main بوده‌اند و بدون تغییر byte کپی می‌شوند؛ JSON تازه یا دادهٔ ظرفیت افزوده نمی‌شود.
خانه شامل UIهای همراه والدین/روایت/یهویی و حریم خصوصی است؛ ورود/پرداخت و سنجش UI به همین فایل‌ها متصل‌اند و در بسته حفظ شده‌اند. تصاویر و iconهای navigation برای مسیرهای پویا به‌صراحت فهرست شده‌اند. فایل 31032553.txt برای نشان ثبت‌شدهٔ اعتماد و manifest/فونت برای PWA نگه داشته شدند.

| URL عمومی از root | نقش |
|---|---|
| `/31032553.txt` | فایل تأیید دامنهٔ موجود در main |
| `/admin_feedback_ui_v1.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/admission_chance_ui.css` | پوسته و استایل UI |
| `/admission_chance_ui.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/app.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/apple-touch-icon.png` | PWA / آیکن / boot |
| `/auth_api_client.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/commercial_ui.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/data.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/data/micro_motives.json` | دادهٔ عمومی سفر / کاتالوگ سنجش UI؛ نه ظرفیت یا نمرهٔ سرور |
| `/data/questions_v2.json` | دادهٔ عمومی سفر / کاتالوگ سنجش UI؛ نه ظرفیت یا نمرهٔ سرور |
| `/data/trait_map_v3.json` | دادهٔ عمومی سفر / کاتالوگ سنجش UI؛ نه ظرفیت یا نمرهٔ سرور |
| `/divider-gold.svg` | تصویر، navigation یا فونت محلی |
| `/external_links_fix_v1.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/feedback_bridge.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/fonts/Vazirmatn-Variable.woff2` | تصویر، navigation یا فونت محلی |
| `/genz_results_enhance.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/genz_results_layer.css` | پوسته و استایل UI |
| `/hero-journey.jpg` | تصویر، navigation یا فونت محلی |
| `/hero-journey@2x.jpg` | تصویر، navigation یا فونت محلی |
| `/ico-bell.svg` | تصویر، navigation یا فونت محلی |
| `/ico-bolt.svg` | تصویر، navigation یا فونت محلی |
| `/ico-book.svg` | تصویر، navigation یا فونت محلی |
| `/ico-chevron.svg` | تصویر، navigation یا فونت محلی |
| `/ico-compass.svg` | تصویر، navigation یا فونت محلی |
| `/ico-home.svg` | تصویر، navigation یا فونت محلی |
| `/ico-journey.svg` | تصویر، navigation یا فونت محلی |
| `/ico-parents.svg` | تصویر، navigation یا فونت محلی |
| `/ico-profile.svg` | تصویر، navigation یا فونت محلی |
| `/ico-quill.svg` | تصویر، navigation یا فونت محلی |
| `/icon-192.png` | PWA / آیکن / boot |
| `/icon-512.png` | PWA / آیکن / boot |
| `/index.html` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/journey_experience.css` | پوسته و استایل UI |
| `/journey_experience.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/majors_catalog_ui_v1.json` | دادهٔ عمومی سفر / کاتالوگ سنجش UI؛ نه ظرفیت یا نمرهٔ سرور |
| `/manifest.json` | PWA / آیکن / boot |
| `/mobile-pwa.css` | پوسته و استایل UI |
| `/parents-feature.jpg` | تصویر، navigation یا فونت محلی |
| `/parents.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/password_reset_ui.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/payment_hop_boot.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/payment_return_reconcile.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/poems.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/post_auth_flow_policy.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/privacy.html` | حریم خصوصی پیوندخورده از پوسته |
| `/profile_ux_v1.css` | پوسته و استایل UI |
| `/profile_ux_v1.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/purchase_ui_fix.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/pwa-boot.js` | PWA / آیکن / boot |
| `/quota_runtime.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/quota_state_reconciler.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/quotes_darkhorse.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/shell.css` | پوسته و استایل UI |
| `/shell.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/shell_runtime_fix.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/spark-feature.jpg` | تصویر، navigation یا فونت محلی |
| `/spark_game.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/stories-feature.jpg` | تصویر، navigation یا فونت محلی |
| `/stories.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/sw.js` | PWA / آیکن / boot |
| `/trait_map_v3.json` | دادهٔ عمومی سفر / کاتالوگ سنجش UI؛ نه ظرفیت یا نمرهٔ سرور |
| `/ux_v2_patch.js` | entrypoint / پوسته / سفر / سنجش UI / تعامل و پرداخت موجود |
| `/wisdom-feature.jpg` | تصویر، navigation یا فونت محلی |

### excludeهای صریح و دفاع در برابر نشت

- همهٔ `sanjesh*`، dumpهای ظرفیت/دفترچهٔ ۱۴۰۴/۱۴۰۵ و `sanjesh_record_capacity_full.json`؛ حتی اگر در allowlist دستکاری‌شده اضافه شوند build رد می‌شود.
- `program2s.json`، majors/value_poles/school_branches و هر JSON سروری یا ناشناخته: JSON فقط در مجموعهٔ شش‌تاییِ فوق مجاز است. کاتالوگ UI عمومی با majors علمیِ root فرق دارد.
- `docs/weight-review/`، `docs/audits/`، protocolها، گزارش‌ها و هر پوشه جز data و fonts؛ `.git`، dotfile، env، symlink، APK و wildcardها.
- CNAME و .nojekyll (مختص میزبانی Pages)، `admin.html`، `download.html` و legacy `feedback.html` وارد بسته نیستند. download فعلی به APK غایب `/asbe-siah-1.0.5.apk` اشاره دارد؛ این فاز hosting APK نمی‌سازد. endpointهای feedback موجود در اپ دست‌نخورده‌اند.
- `free_journey_mode.js` عمداً ممنوع است؛ وجود آن روی main مجوز احیای ارجاع حذف‌شده در deploy نیست. فایل‌های کمکیِ بارگذاری‌نشده مثل commercial_ui_bridge_v2/quota_p0_guard نیز خودکار اضافه نمی‌شوند.
- ابزار روی main یا deploy تمام docs را copy/walk نمی‌کند؛ فقط pathهای دقیق در Git commit منبع خوانده می‌شوند. فایل‌های جدید آینده خودکار عمومی نمی‌شوند.
- absent بودن فایل حساس در artifact اثبات شده؛ **HTTP 404 آن روی لیارا هنوز تست نشده** و به محدودشدن document root و عدم fallback نشت‌دهنده در mount آینده وابسته است.

## ۴. اختلاف‌های deploy با production

| موضوع | production/main | deploy فعلی | نتیجهٔ آماده‌سازی |
|---|---|---|---|
| manifest id/start_url/scope و icon | root `/` | prefix `/dark-horse-v2-/` | artifact همان manifest root تولیدشدهٔ main است |
| Service Worker | v80، سیاست cache جدیدتر | v62؛ install cacheها را پاک می‌کند | v80 بدون bump/rewrite منتقل شده؛ تغییر origin، cache/session را مهاجرت نمی‌دهد |
| PWA boot | `sw.js?v=80` | `sw.js?v=62` | app/sw/registration از یک SHA منبع‌اند |
| HTML آغازین | خانهٔ اولیه داخل index | ظرف app خالی | خانهٔ HTML در artifact موجود است؛ اثبات اجرای کامل WebView نیست |
| فایل غایب | index به free_journey_mode ارجاع ندارد | `index.html:48` فایل غایب را می‌خواهد | فایل و ارجاع قدیمی به artifact وارد نمی‌شود |
| فونت | فایل محلی Vazirmatn | CSS فونت از jsDelivr | فونت main بدون تغییر بسته‌بندی شد |
| app/shell/data و queryهای cache | نسخه‌های production و UX موجود | byteها/نسخه‌های قدیمی متفاوت | hash هر فایل از M ثبت شد؛ هیچ ادغام خودکار JS انجام نشد |
| payment hop | payment_hop_boot در index main وجود دارد | فایل روی deploy غایب است | همان فایل main همراه dependencyهایش در allowlist است؛ URL ثابت production حفظ می‌شود |
| runtime root | در Pages، index.html | در backend، `GET /` پاسخ JSON online است | در این PR تغییر نکرد؛ رفع تعارض برای mount نیاز دستور رفتاری جدا دارد |
| داده‌های داخل docs | عمومی محدود | raw data سنجش و auditها نیز وجود دارند | docs deploy مطلقاً document root مستقیم این artifact نیست |

شاهد: main/deploy:`docs/index.html`، `manifest.json`، `sw.js`، `pwa-boot.js` در دو SHA بخش ۱؛ backend deploy:`main_v2.py:306–312,320–365`. شمارهٔ خط فایل‌های دو ref قابل جایگزینی نیست.

## ۵. شواهد build محلی

- **۶۴ فایل، مجموع 1,520,788 byte**؛ مجموعهٔ فایل‌های public دقیقاً با allowlist برابر شد؛ فقط شش JSON عمومی مجاز حضور دارند.
- دو build مستقل از یک ورودی evidence یکسان تولید کردند؛ آزمون repro جزو ۱۶ تست است.
- **۱۶/۱۶ تست Python PASS**: build دقیق/hash، ref متغیر، فایل غایب، dependency غایب، manifest قدیمی، دادهٔ حساس، path traversal، symlink Git و خروجی، duplicate، عدم overwrite و عدم خواندن docs working tree.
- **۲۸ فایل JS آرتیفکت `node --check` PASS**.
- تست موجود `node tests/test_genz_native_home_v2.js` نیز PASS شد؛ آن تست source/VM است و مرورگر یا APK واقعی نیست.
- خانهٔ اولیه بدون API در HTML موجود است و در تست استاتیک assert شده؛ اجرای JS با API قطع و رفتار مرورگر/WebView هنوز تأیید نشده است.

| asset | SHA-256 byteهای public = Git source M |
|---|---|
| `index.html` | `477c40f226689ce1a4c975a671abb8abe90c7eb2f67a1c650ab7a29fb622a54b` |
| `app.js` | `534e60f479fbe2d79312c6eb90cd9787191ca185f0bfc50f9196c95314288716` |
| `shell.js` | `2d2e3fb88083be6838865ab0e4e91d0b078e3321e37f0837014d082d55eba074` |
| `manifest.json` | `a9844d2a676e9430d04079f48273e2e2cd1c6f52807408884a35a6a20f8adc17` |
| `sw.js` | `d7e7600b1f3c11fd6d55f0d1cf6c861db6cc95a032f419a7c28f3b2c82ec6cda` |

آثار اجرایی خارج Git: `/home/user/frontend-phase1-evidence/public/`، sidecar `public.evidence.json` و `home-node.log`. اسکریپت build این مسیر را publish نکرده و هیچ سرور background راه‌اندازی نشده است.

## ۶. طرح runtime بعدی — اجرا نشده

```text
HTTPS Liara origin L
  /api/* و /api            -> backend، با auth/quota/methodهای فعلی؛ پیش از static
  /__runtime_fingerprint  -> backend موجود؛ بدون بازنویسی fingerprint علمی
  /openapi.json و /docs و /redoc -> reserved backend طبق سیاست مصوب
  / و /index.html         -> index آرتیفکت public، نه JSON root فعلی
  /<allowlisted asset>    -> فایل از public/؛ نه docs/ خام deploy
  /<missing or sensitive> -> 404/deny واقعی؛ هرگز index به جای JSON/JS یا API
```

- این PR هیچ StaticFiles یا root handler اضافه نمی‌کند. mount ریشه باید بعد از routerها و با لحاظ تعارض `GET /` فعلی پیاده شود؛ `/api/not-found` و 405 نباید HTML شوند.
- document root آینده فقط public باشد؛ sidecar metadata و source repo نباید کنار آن در سطح وب قرار گیرند. mounts اضافه برای data یا scientific root ممنوع‌اند مگر دستور جدا.
- API_BASEهای فعلی و payment callback/hop به origin production وابستگی دارند. روی hostname جدید لیارا، برابری hash فایل‌ها به معنی same-origin API نیست؛ اصلاح URLهای runtime، CORS و callback در scope این PR نیست.
- شروط «فرانت هم‌خوان production» و «همان SHA release با backend» مستقل‌اند: این artifact از M است، backend فعلی D است. این فاز ادعای SHA مشترک API/فرانت ندارد. برای commit نهایی S روی deploy، انتخاب/ثبت فرانت و provenance فایل‌ها باید در PR مجاز بعدی انجام شود؛ کپی کور docs ممنوع است.
- اگر در مرحلهٔ بعد شرط باشد همهٔ فایل‌ها دقیقاً byteهای M بمانند، نمی‌توان بدون بررسی هم‌زمان وعده داد API_BASE هم عوض شده است؛ هر استثنا/تغییر frontend باید صریح ثبت و baseline جدید به تأیید ناظر برسد.
- تک‌سرویس با خاموشی کامل لیارا، فرانت را نیز قطع می‌کند. نمایش خانه هنگام unavailable بودن API با در دسترس‌ماندن خانه هنگام خاموشی کل میزبان متفاوت است. Pages در تمام این مرحله روشن می‌ماند.

## ۷. معیار پذیرش از URL لیارا — وضعیت فعلی

| معیار | وضعیت اکنون | شاهد لازم در مرحلهٔ مجاز بعدی |
|---|---|---|
| فایل‌های artifact مطابق source M | **PASS محلی** | برای HTTP مجدداً hash بگیرید؛ raw/decompressed body، نه متن فرمت‌شده |
| `L/`, `L/index.html`, `L/app.js?...`, `L/shell.js?...` | **اجرا نشده؛ publish/mount خارج scope** | 200، MIME صحیح، final origin همان L، hash دقیق جدول بالا، بدون redirect به Pages |
| assetهای وابسته و data عمومی | موجودی و dependency استاتیک PASS؛ HTTP اجرا نشده | تمام مسیرهای allowlist و query نسخه‌ها از L؛ فقدان فایل 404 واقعی؛ هیچ HTML جای JSON |
| مسیرهای حساس | absent از artifact PASS؛ HTTP اجرا نشده | URL مستقیم sanjesh/record/raw docs/audit/.git/env/root scientific/traversal، 404 یا deny؛ نه fallback HTML |
| خانه با API unavailable | خانهٔ HTML موجود؛ اجرای مرورگر اجرا نشده | مرورگر تازه و SW نصب‌شده: خانه نمایش یابد؛ عدم hang به دلیل auth/analysis؛ صفحهٔ کنترل‌شده برای بخش نیازمند API |
| PWA و cache | byteهای v80 حفظ؛ آزمون مرورگر اجرا نشده | نصب تازه، cache قدیمی، update بدون loop، root scope، MIME sw و headerهای واقعی؛ حفظ session |
| API و payment | runtime دست‌نخورده | فقط در مجوز بعدی؛ auth/quota/verification/idempotency حفظ، بدون پرداخت واقعی یا env change خودسرانه |
| یک SHA release API و فرانت | **هنوز برقرار/تأیید نشده** | release S، hashes backend و تمام static؛ metadata به‌تنهایی کافی نیست |
| Pages/DNS/موتور/وزن/JSON علمی | **بدون تغییر** | diff و وضعیت زیرساخت قبل/بعد؛ هیچ cutover از این Draft مجوز نمی‌گیرد |

جدول evidence HTTP بعدی: `URL | final URL/origin | status | MIME | Cache-Control | response SHA-256 | expected SHA-256 | source M | release S`. اجرای مرورگر با cache سرد و گرم و SW فعال جدا ثبت شود. fingerprint علمی موجود پوشش index/app/shell ندارد؛ hashes frontend به صورت شاهد مستقل ثبت شوند، نه تغییر fingerprint.

## ۸. حدود PR و تصمیم ناظر

این Draft فقط یک سند، اسکریپت build، allowlist فنی و تست‌های همان ابزار دارد. دو سند فاز صفرِ قبلیِ untracked در commit/PR وارد نمی‌شوند. هیچ workflow یا رفتار برنامه تغییر نکرده است.
**هیچ publish، تغییر DNS، قطع Pages، mount runtime، روشن‌کردن سرویس، تغییر CORS، env، موتور/وزن/majors/JSON علمی، commit دادهٔ تولیدشده یا Merge انجام نشده است.** تأیید این Draft به معنی تأیید deployment نیست؛ برای mount و آزمون origin لیارا دستور جدا لازم است.
