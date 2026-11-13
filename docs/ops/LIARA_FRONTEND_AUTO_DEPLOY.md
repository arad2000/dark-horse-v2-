# انتشار خودکار فرانت لیارا

app تأییدشدهٔ ناظر: **asbe-siah-web-test**؛ دامنهٔ عمومی: https://asbe-siah.ir/ . روش قبلی ZIP دستی بود؛ workflow پیشنهادی جایگزین آن است، نه تغییر API.

`.github/workflows/liara-frontend-static.yml`: PR به main فقط تست و build؛ push به main پس از موفقیت همان تست/build، خروجی عمومی را با CLI پین‌شدهٔ `@liara/cli@9.6.7` به همان Static app می‌فرستد. بدون ساخت شاخهٔ آینه یا تغییر source API.

ناظر باید قبل از Merge، secret مخزن **LIARA_API_TOKEN** را در Settings → Secrets and variables → Actions تنظیم کند؛ مقدار در گفتگو یا Git ثبت نشود. از کمترین دسترسی ممکن برای همان app استفاده شود. نبود secret باعث FAIL صریح می‌شود، نه انتشار موفق ساختگی. اگر app متعلق به team خاصی است که token به‌تنهایی آن را resolve نمی‌کند، قبل از اجرا نیاز به تنظیم تیم و تأیید جدا دارد؛ شناسه حدس زده نمی‌شود.

خروجی از Git blobهای SHA همان run و allowlist عمومی ساخته می‌شود؛ source فایل‌ها docs است ولی تمام docs با اسناد داخلی آپلود نمی‌شود. `index.html` و `app.js` در ریشه‌اند. CLI از خروجی جدا در RUNNER_TEMP اجرا می‌شود؛ `liara.json` پایتون ریشه یا backend وارد بسته نمی‌شود. CLI بدون detach اجرا می‌شود؛ خطای آن workflow را FAIL می‌کند. SHA در پیام release و hash index/app در log ثبت می‌شوند. این‌ها جای probe دامنه را نمی‌گیرند.

تست محلی workflow نمی‌تواند اتصال واقعی، token، تنظیمات app یا ظرفیت لیارا را اثبات کند. معیار نهایی بعد از Merge مجاز: deploy موفق روی app تعیین‌شده، index زنده دارای shuffle-v1، app.js دارای dhDisplayOrder/displayShuffleSeed و smoke ورود/resume. cache/SW مطابق رفتار فعلی می‌ماند؛ reload پس از دریافت HTML تازه ممکن است لازم شود. دادهٔ سفر و quota برای cache پاک نشوند.

بدون تغییر engine، وزن، majors، questions، منطق shuffle، سهمیه یا backend. GitHub Pages workflow دست‌نخورده باقی می‌ماند؛ موفقیت آن معیار انتشار لیارا نیست. Draft تا دستور Merge ناظر؛ در آماده‌سازی این طرح هیچ Deploy اجرا نشده است.
