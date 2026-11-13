# #361 — بررسی مسیر انتشار shuffle و cache-bust

## منبع تغییر

Merge #361: `0fb035357fa55a1aa02a086bbd7dd0b3b27a6061`.
فهرست واقعی diff از `gh pr view 361 --json files` (نه نمایش root commit در clone shallow):

- `docs/app.js`: +42 / -3
- `docs/ops/PHASE0_SHUFFLE_NEIGHBORHOODS_OPTIONS.md`: +113
- `tests/test_display_shuffle_contract.js`: +140
- `tests/test_value_poles_contract.js`: +2

فایل `app.js` در ریشهٔ مخزن وجود ندارد. workflow `.github/workflows/publish-frontend-from-deploy.yml` با نام «Publish frontend from main»، `path: docs` را به `actions/upload-pages-artifact@v3` می‌دهد؛ بنابراین `docs/app.js` به `/app.js` و `docs/index.html` به `/index.html` نگاشت می‌شوند. `/docs/app.js` در سایت مسیر مورد انتظار نیست و 404 آن نشانهٔ اشتباه بودن محل source نیست.

## شاهد واقعی انتشار قبلی

اجرای [43420906323](https://github.com/arad2000/dark-horse-v2-/actions/runs/43420906323) روی SHA Merge:

- verify: **SUCCESS**
- Upload docs/ as site root: **SUCCESS**
- Deploy GitHub Pages و job publish: **FAILURE**
- annotation ثبت‌شدهٔ GitHub: `No artifacts named "github-pages" were found for this workflow run` و خطای fetching artifact metadata؛ پیشنهاد rerun در annotation آمده است.
- در عین حال API متادیتای Actions آرتیفکت `github-pages` با ID `14033642069` و head SHA همان Merge را نشان داد. این تناقض متادیتا/دریافت، علت ریشه‌ای قطعی نیست؛ تغییر workflow یا حدس ناسازگاری actionها از آن نتیجه نمی‌شود.

دانلود آرتیفکت و log از میزبان‌های redirectشده با EOF ناموفق بود؛ بنابراین **بایت‌های آرتیفکت واقعی Actions مستقلاً باز نشده‌اند**. اعلام موفقیت آپلود با اعلام موفقیت deploy فرق دارد. نبود نسخهٔ shuffle روی Live با شکست deploy سازگار است؛ هیچ GET یا مرورگر مستقل Live در این موج اجرا نشده است. شمارش صفر و query قدیمی از گزارش ناظر است.

## بررسی محتوای بسته‌بندی

بسته‌بندی محلی با همان ریشهٔ `docs/` بازتولید شد. `app.js` داخل tar محلی بایت‌به‌بایت با `0fb0353:docs/app.js` برابر است:

```text
SHA-256: 3f070dea0071366cce28c71573a1c77192fbfa24d950021a252562e8161ce0d9
dhDisplayOrder occurrences: 4
displayShuffleSeed occurrences: 11
```

این شاهد، تأیید **source و بسته‌بندی محلی مطابق مسیر workflow** است؛ نه جایگزین دانلود artifact واقعی یا اثبات نصب روی دامنه. منطق #361 از قبل روی فایل درست موجود است و دوباره پیاده‌سازی نشد.

## تغییر کوچک این PR

به URL اسکریپت app در `docs/index.html` پارامتر `&shuffle-v1=1` اضافه شد؛ queryهای قبلی حفظ شدند. SW برای assetهای نسخه‌دار cache را با URL درخواست می‌خواند؛ query تازه cache key تازه می‌دهد. خود SW، سهمیه و bootstrap خرید دست‌نخورده‌اند. HTML cache-first فعلی ممکن است نخست پوستهٔ قبلی را نشان دهد؛ دریافت پوستهٔ تازه و reload برای پذیرش مرورگر لازم است. cache-bust جای deploy موفق را نمی‌گیرد و `/app.js` بدون query را نیز در سرور عوض نمی‌کند.

تست shuffle توسعه یافت تا یک script app، مسیر `/app.js`، query تازه، نگاشت workflow و وجود منطق shuffle در source منتشرشونده را بررسی کند. regex تست motive-route با حفظ همهٔ queryهای قبلی، query تازه را نیز الزامی می‌کند؛ assertion حذف یا ضعیف نشد.

اعتبارسنجی: هر ۱۹ فایل `tests/test_*.js` موفق، `node --check docs/app.js` موفق و بسته‌بندی محلی بایت‌برابر. این تست‌ها browser/live acceptance نیستند.

## معیار پذیرش پس از مجوز Merge

1. اجرای جدید «Publish frontend from main» روی SHA Merge جدید: **verify و publish هر دو SUCCESS**. اگر خطای metadata تکرار شد، علت با شواهد تازه بررسی شود؛ از cache-bust موفقیت deploy استنتاج نشود.
2. ناظر `/index.html` تازه را با script حاوی `shuffle-v1=1` بررسی کند.
3. ناظر `/app.js` و URL نسخه‌دارش را دریافت کند: وجود `dhDisplayOrder` و `displayShuffleSeed` و ترجیحاً hash کامل مورد انتظار بررسی شود. شمارش marker صرفاً شاهد نصب اولیه است، نه آزمون کامل رفتار.
4. بررسی نشست تازه و ثبات ترتیب در reload/resume؛ index اصلی S و code اصلی V حفظ شوند.

این موارد هنوز پذیرش آینده‌اند. هیچ Merge، rerun workflow، deploy دستی لیارا یا تغییر engine، majors، weights، questions JSON، Hybrid یا سهمیه در این موج انجام نشد. مرجع قرارداد: [PHASE0](PHASE0_SHUFFLE_NEIGHBORHOODS_OPTIONS.md).
