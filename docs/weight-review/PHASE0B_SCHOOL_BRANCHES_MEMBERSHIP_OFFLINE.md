# PHASE0b — عضویت پیشنهادی و آزمایش آفلاین S/V شاخه‌ها

**وضعیت: آزمایش آفلاین انجام شد؛ حکم فعلی No-Go برای PR اجرایی داده‌ای تا تصویب عضویت و پذیرش اثر مشاهده‌شده.** هیچ فایل school_branches، موتور، majors، میکروها یا گیت تغییر نکرد. این سند به معنای بهتر بودن مدل میانگین‌شده، مجوز write، Merge یا deploy نیست.

## ۱. تثبیت منبع و تفکیک دو سناریو
- تاریخ: 2026-10-25. منبع baseline و هر دو سناریو: deploy HEAD **`03cbc16697c111514dccdc70fa1e980f90bb0cce`**؛ هنگام آغاز با `git ls-remote` کنترل شد و با فاز صفر یکسان بود.
- موتور بدون تغییر از همان commit با `compile/exec` خوانده شد. برای جلوگیری از خواندن فایل‌های قدیمی main، instance با `__new__` و deepcopy داده‌های pinned ساخته شد، سپس validator و precompute اصلی اجرا شدند؛ هیچ متد امتیازدهی override نشد. کلاس و defaultها از working tree استفاده نشدند.
- ورودی micro_motives همان مسیر عملیاتی `docs/data/micro_motives.json` است؛ root/mirror در HEAD مبنا byte-identical. تمام ۲۳۰ major بارگذاری شدند؛ فقط ۲۰۲ فعال برای عضویت/میانگین واجدشرایط بودند، ۲۸ غیرفعال وارد میانگین نشدند و فعال هم نشدند.
- **E = explicit-only:** فقط major فعال با `high_school_branch` پر و برابر نام دقیق یکی از چهار branch. ۱۷۶ عضو؛ ۲۶ null از میانگین حذف می‌شوند، نه از دیتابیس. این سناریو تشخیصی است، نه سیاست مناسب حذف داده.
- **I = explicit + inferred:** همان اعضای E، به‌علاوه پیشنهاد جدول ۲۶ null بر اساس overlap کامل و یکتا. ۲۰۲ عضو. این عضویت هنوز مصوب ناظر نیست؛ candidate آزمایشگاهی است، نه reference نهایی.
- در هر دو فقط `strategy_weights` و `value_weights` در deepcopy شاخه‌ها جایگزین شدند. micro_motive_codes، denom_limit، id/name/group، نسخه و metadata دقیقاً حفظ شدند. پس E عمداً Mِ مخزن کامل را با S/V میانگین ۱۷۶ عضو مقایسه می‌کند؛ بازسازی codes متناسب با E یا حذف کدهای ۲۶ مورد انجام نشده است.
- baseline فاز صفر بازتولید شد؛ fixtureهای A/B/C1/C2 از JSON داخل سند PHASE0 خوانده و با fixture اسکریپت equality شدند. گزارش فاز صفر یک snapshot تاریخی پیش از محاسبه candidate است؛ این سند مرحله مجاز جدیدِ آزمایش را ثبت می‌کند.

|شاخه|baseline عضویت کدی|E: فیلد پر|I: پر + پیشنهاد|افزوده از nullها|
|---|---:|---:|---:|---:|
|علوم تجربی|54|54|54|0|
|ریاضی فیزیک|62|55|62|7|
|علوم انسانی|59|51|59|8|
|فنی و حرفه‌ای|27|16|27|11|

## ۲. جدول ۲۶ عضویت پیشنهادی — بدون write در JSON
معیار پیشنهاد: تطبیق strip/lower کدهای major با `_active_branch_code_set` واقعی هر branch؛ هر ۲۶ مورد **۷/۷ در یک branch و ۰ در سه branch دیگر** دارند. این اتصال، جاگذاری کنونی کدها در c030bf8 را بازتولید می‌کند؛ شاهد مستقل وزارت آموزش‌وپرورش یا قضاوت جدید از عنوان رشته نیست.
**تعریف اطمینان:** برای بازیابی نگاشت کدی فعلی بالا، اما برای تصویب عضویت موضوعی/آموزشی **متوسط**؛ چون دادهٔ استنباط و مخزن مقصد از یک نگاشت میراثی‌اند. بنابراین تمام ردیف‌ها «متوسط» و نیازمند تأیید ناظرند؛ این یکنواختی عمدی است، نه رتبه‌بندی ساختگی بین رشته‌ها. هیچ high_school_branch پر نشده است.
|major_id|name|branch پیشنهادی از overlap|اطمینان|نیاز تأیید ناظر؟|
|---:|---|---|---|---|
|177|کارگردانی|فنی و حرفه‌ای — 7/7|متوسط|بله|
|178|کارگردانی تلویزیون|فنی و حرفه‌ای — 7/7|متوسط|بله|
|180|نوازندگی موسیقی ایرانی|فنی و حرفه‌ای — 7/7|متوسط|بله|
|181|نوازندگی موسیقی جهانی|فنی و حرفه‌ای — 7/7|متوسط|بله|
|182|آهنگسازی|فنی و حرفه‌ای — 7/7|متوسط|بله|
|183|طراحی پارچه|فنی و حرفه‌ای — 7/7|متوسط|بله|
|184|طراحی و چاپ پارچه|فنی و حرفه‌ای — 7/7|متوسط|بله|
|185|نمایش عروسکی|فنی و حرفه‌ای — 7/7|متوسط|بله|
|186|کتاب‌آرایی|فنی و حرفه‌ای — 7/7|متوسط|بله|
|187|طراحی و ساخت طلا و جواهر|فنی و حرفه‌ای — 7/7|متوسط|بله|
|189|چاپ|فنی و حرفه‌ای — 7/7|متوسط|بله|
|199|مهندسی هوانوردی و مراقبت پرواز|ریاضی فیزیک — 7/7|متوسط|بله|
|201|خلبانی بالگرد|ریاضی فیزیک — 7/7|متوسط|بله|
|202|خلبانی پهپاد|ریاضی فیزیک — 7/7|متوسط|بله|
|203|هوانوردی خلبانی|ریاضی فیزیک — 7/7|متوسط|بله|
|204|مهندسی نگهداری و تعمیر بالگرد|ریاضی فیزیک — 7/7|متوسط|بله|
|205|زبان روسی|علوم انسانی — 7/7|متوسط|بله|
|208|علوم قضایی|علوم انسانی — 7/7|متوسط|بله|
|209|زبان و ادبیات آلمانی|علوم انسانی — 7/7|متوسط|بله|
|210|زبان و ادبیات اسپانیایی|علوم انسانی — 7/7|متوسط|بله|
|211|زبان و ادبیات ترکی استانبولی|علوم انسانی — 7/7|متوسط|بله|
|212|زبان و ادبیات ایتالیایی|علوم انسانی — 7/7|متوسط|بله|
|213|زبان و ادبیات ژاپنی|علوم انسانی — 7/7|متوسط|بله|
|214|زبان و ادبیات کردی|علوم انسانی — 7/7|متوسط|بله|
|219|مهندسی فضای سبز|ریاضی فیزیک — 7/7|متوسط|بله|
|220|مهندسی مکانیزاسیون کشاورزی|ریاضی فیزیک — 7/7|متوسط|بله|

### manifest دقیقِ ورودی هر سناریو
|شاخه|اعضای E|اعضای افزوده برای I|
|---|---|---|
|علوم تجربی|`1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 99, 152, 153, 156, 169`|``|
|ریاضی فیزیک|`40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 84, 85, 96, 97, 98, 100, 151, 154, 155, 157, 162, 165`|`199, 201, 202, 203, 204, 219, 220`|
|علوم انسانی|`101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 146, 147, 148, 149, 150, 159, 160, 161, 163, 164, 166, 171, 173, 174, 175, 176`|`205, 208, 209, 210, 211, 212, 213, 214`|
|فنی و حرفه‌ای|`77, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 158, 167, 168, 170, 172`|`177, 178, 180, 181, 182, 183, 184, 185, 186, 187, 189`|

## ۳. روش میانگین و کنترل داده
- همان تعریف طراحی‌شده در PHASE0: هر major عضو یک وزن برابر؛ نه وزن‌دهی با تعداد کد/نام/مقدار M/جدید بودن. S هر خانه میانگین، سپس تقسیم بر جمع همان ردیف و round چهاررقمی؛ residual به بزرگ‌ترین mean خام همان ردیف، در tie به اندیس اول. V هر یک از ۳۰ قطب مستقل میانگین و round چهاررقمی؛ هیچ pair normalization انجام نشد.
- محاسبه با Decimal از str ورودی، precision=50 و `ROUND_HALF_EVEN`؛ خروجی float فقط در مرز ورود به موتور. بیشینه خطای جمع S ورودی ۲۰۲ major: **0.0001**، زیر حد پیش‌پرواز ۰٫۰۰۱؛ هیچ major ورودی اصلاح نشد. ردیف خروجی در Decimal دقیقاً جمع ۱ و 25×5؛ V دقیقاً ۳۰ کلید Q1A..Q15B، همه متناهی و در [۰،۱].
- کاندیدها فقط Python object بودند. هیچ فایل candidate JSON، patch وزن یا تغییر school_branches روی دیسک ساخته نشد. hash زیر serialization کانونیِ درحافظه‌ایِ کل فهرست چهار branch است، نه اثر انگشت یک فایل deploy.
|سناریو|SHA-256 آبجکت candidate (canonical JSON in memory)|
|---|---|
|E|`5185d4d8455a3ccbe1e731d63dab392ad2ba4d22f369556f29cdcbeddaa26e24`|
|I|`a63a02d0b42d9a14135d26e989e27724914c40bcaa773487d76c3180ef8be42d`|

## ۴. نتیجه M/V/S/Total برای A، B، C1، C2
تمام اعداد درصد/امتیاز مدل در بازه ۰..۱۰۰ و گردکردن API به یک رقم‌اند؛ فرمول بدون تغییر `0.60M + 0.20S + 0.20V`. Total از componentهای گردنشده محاسبه شده، پس جمع componentهای یک‌رقمی الزاماً عین Total نیست.
در هر ۱۶ مقایسهٔ هر candidate با baseline، **M و evidence متناظر دقیقاً ثابت** بود؛ equality با تابع M قبل از گردکردن هم بررسی شد. کدها/مخرج/آستانه‌ها تغییری نکردند. SJT همه C و conjoint فرد A / زوج B، همان fixtureهای PHASE0.
### ۴-الف. baseline فاز صفر
|پروفایل|شاخه|M|V|S|Total|visible|
|---|---|---:|---:|---:|---:|---|
|A|علوم تجربی|0.0|74.1|72.2|29.3|خیر|
|A|ریاضی فیزیک|66.7|71.3|59.1|66.1|بله|
|A|علوم انسانی|0.0|61.1|82.0|28.6|خیر|
|A|فنی و حرفه‌ای|0.0|69.9|61.4|26.3|خیر|
|B|علوم تجربی|0.0|74.1|72.2|29.3|خیر|
|B|ریاضی فیزیک|0.0|71.3|59.1|26.1|خیر|
|B|علوم انسانی|0.0|61.1|82.0|28.6|خیر|
|B|فنی و حرفه‌ای|66.7|69.9|61.4|66.3|بله|
|C1|علوم تجربی|0.0|74.1|72.2|29.3|خیر|
|C1|ریاضی فیزیک|33.3|71.3|59.1|46.1|بله|
|C1|علوم انسانی|0.0|61.1|82.0|28.6|خیر|
|C1|فنی و حرفه‌ای|33.3|69.9|61.4|46.3|بله|
|C2|علوم تجربی|20.0|74.1|72.2|41.3|بله|
|C2|ریاضی فیزیک|20.0|71.3|59.1|38.1|بله|
|C2|علوم انسانی|20.0|61.1|82.0|40.6|بله|
|C2|فنی و حرفه‌ای|20.0|69.9|61.4|38.3|بله|

### ۴-ب. E — فقط فیلدهای پر
|پروفایل|شاخه|M|V|S|Total|ΔTotal نسبت به baseline|visible|
|---|---|---:|---:|---:|---:|---:|---|
|A|علوم تجربی|0.0|74.2|71.9|29.2|-0.1|خیر|
|A|ریاضی فیزیک|66.7|71.5|59.6|66.2|+0.1|بله|
|A|علوم انسانی|0.0|62.2|82.7|29.0|+0.4|خیر|
|A|فنی و حرفه‌ای|0.0|71.4|63.7|27.0|+0.7|خیر|
|B|علوم تجربی|0.0|74.2|71.9|29.2|-0.1|خیر|
|B|ریاضی فیزیک|0.0|71.5|59.6|26.2|+0.1|خیر|
|B|علوم انسانی|0.0|62.2|82.7|29.0|+0.4|خیر|
|B|فنی و حرفه‌ای|66.7|71.4|63.7|67.0|+0.7|بله|
|C1|علوم تجربی|0.0|74.2|71.9|29.2|-0.1|خیر|
|C1|ریاضی فیزیک|33.3|71.5|59.6|46.2|+0.1|بله|
|C1|علوم انسانی|0.0|62.2|82.7|29.0|+0.4|خیر|
|C1|فنی و حرفه‌ای|33.3|71.4|63.7|47.0|+0.7|بله|
|C2|علوم تجربی|20.0|74.2|71.9|41.2|-0.1|بله|
|C2|ریاضی فیزیک|20.0|71.5|59.6|38.2|+0.1|بله|
|C2|علوم انسانی|20.0|62.2|82.7|41.0|+0.4|بله|
|C2|فنی و حرفه‌ای|20.0|71.4|63.7|39.0|+0.7|بله|

### ۴-ج. I — فیلدهای پر + پیشنهاد ۲۶ null
|پروفایل|شاخه|M|V|S|Total|ΔTotal نسبت به baseline|visible|
|---|---|---:|---:|---:|---:|---:|---|
|A|علوم تجربی|0.0|74.2|71.9|29.2|-0.1|خیر|
|A|ریاضی فیزیک|66.7|72.6|61.5|66.8|+0.7|بله|
|A|علوم انسانی|0.0|64.6|82.0|29.3|+0.7|خیر|
|A|فنی و حرفه‌ای|0.0|81.2|68.1|29.9|+3.6|خیر|
|B|علوم تجربی|0.0|74.2|71.9|29.2|-0.1|خیر|
|B|ریاضی فیزیک|0.0|72.6|61.5|26.8|+0.7|خیر|
|B|علوم انسانی|0.0|64.6|82.0|29.3|+0.7|خیر|
|B|فنی و حرفه‌ای|66.7|81.2|68.1|69.9|+3.6|بله|
|C1|علوم تجربی|0.0|74.2|71.9|29.2|-0.1|خیر|
|C1|ریاضی فیزیک|33.3|72.6|61.5|46.8|+0.7|بله|
|C1|علوم انسانی|0.0|64.6|82.0|29.3|+0.7|خیر|
|C1|فنی و حرفه‌ای|33.3|81.2|68.1|49.9|+3.6|بله|
|C2|علوم تجربی|20.0|74.2|71.9|41.2|-0.1|بله|
|C2|ریاضی فیزیک|20.0|72.6|61.5|38.8|+0.7|بله|
|C2|علوم انسانی|20.0|64.6|82.0|41.3|+0.7|بله|
|C2|فنی و حرفه‌ای|20.0|81.2|68.1|41.9|+3.6|بله|

### تغییر componentها در این چهار fixture
چون SJT و conjoint در A/B/C1/C2 یکسان‌اند، ΔS و ΔV هر branch بین چهار fixture ثابت است؛ M و ΔTotal به مجموعه جرقه مربوط‌اند. جدول زیر اختلاف componentهای یک‌رقمی نسبت به baseline است، نه تغییر وزن‌ها.
|شاخه|ΔM در E/I|ΔS در E|ΔV در E|ΔS در I|ΔV در I|
|---|---:|---:|---:|---:|---:|
|علوم تجربی|0.0 / 0.0|-0.3|+0.1|-0.3|+0.1|
|ریاضی فیزیک|0.0 / 0.0|+0.5|+0.2|+2.4|+1.3|
|علوم انسانی|0.0 / 0.0|+0.7|+1.1|+0.0|+3.5|
|فنی و حرفه‌ای|0.0 / 0.0|+2.3|+1.5|+6.7|+11.3|

## ۵. رتبه اول، نمایش و V evidence
|پروفایل|best baseline|best E|best I|کارت visible baseline / E / I|
|---|---|---|---|---|
|A|ریاضی فیزیک|ریاضی فیزیک|ریاضی فیزیک|1 / 1 / 1|
|B|فنی و حرفه‌ای|فنی و حرفه‌ای|فنی و حرفه‌ای|1 / 1 / 1|
|C1|فنی و حرفه‌ای|فنی و حرفه‌ای|فنی و حرفه‌ای|2 / 2 / 2|
|C2|علوم تجربی|علوم تجربی|فنی و حرفه‌ای|4 / 4 / 4|

- **A ریاضی اول و B فنی اول در هر دو سناریو باقی ماند.** C1 در هر سه حالت هم ریاضی و هم فنی را نمایش می‌دهد؛ C2 هر چهار کارت را حفظ می‌کند. gateهای عددی چهار fixture در هر دو candidate PASS است؛ browser/API integration یا ادعای live از آن نتیجه نمی‌شود.
- **اثر قابل توجه I:** Total فنی در C1 از ۴۶٫۳ به ۴۹٫۹ و ریاضی از ۴۶٫۱ به ۴۶٫۸؛ فاصله نمایشی ۰٫۲→۳٫۱. V فنی ۶۹٫۹→۸۱٫۲ (+۱۱٫۳) و S فنی ۶۱٫۴→۶۸٫۱ (+۶٫۷). در C2 رتبه اول از تجربی به فنی می‌رود (فنی ۳۸٫۳→۴۱٫۹). این تغییر را نباید مخفی، «بهبود قطعی» یا pool-scale inflation نامید؛ از عوض شدن S/V است، نه M. وزن‌ها برای برگرداندن رتبه ریاضی تنظیم نشده‌اند.
- E اثر کمتر دارد اما ۲۶ عضو فاقد field را از شاهد S/V حذف می‌کند؛ این حذف محتوایی به‌خصوص در فنی ۱۱/۲۷ عضو و در ریاضی ۷/۶۲ عضو است. بهتر ماندن رتبه تجربی در E دلیل ترجیح این سناریو نیست.
### جفت‌های informative با epsilon ثابت ۰٫۰۲
|شاخه|baseline|E|I|
|---|---:|---:|---:|
|علوم تجربی|15|15|15|
|ریاضی فیزیک|15|15|15|
|علوم انسانی|15|15|13|
|فنی و حرفه‌ای|13|15|14|

برای هر چهار fixture همه ۱۵ سؤال V پاسخ داده شده‌اند و status هر branch در هر سه حالت complete است؛ complete به تعداد پاسخ اشاره دارد، نه الزام ۱۵ جفت informative. هیچ V=None یا incomplete card ساخته نشد. با این حال افت evidence انسانی ۱۵→۱۳ در I واقعی است و باید مصوب شود؛ epsilon برای نگه‌داشتن شواهد تغییر نکرد.
|سناریو|شاخه|جفت‌هایی که از informative خارج شدند (span قبل→بعد)|جفت‌هایی که informative شدند (span قبل→بعد)|
|---|---|---|---|
|E|فنی و حرفه‌ای|—|Q5: 0.0166→0.0712، Q13: 0.0075→0.0269|
|I|علوم انسانی|Q1: 0.0550→0.0150، Q11: 0.0772→0.0167|—|
|I|فنی و حرفه‌ای|Q12: 0.0292→0.0129|Q5: 0.0166→0.1504، Q13: 0.0075→0.0615|

### حساسیت تکمیلی، ۱۰۰ پروفایل مصنوعی ثابت
همان ۱۰۰ پروفایل تصادفی آزمون majors: seed=20261023، چهار major فعال انتخاب و چهار کد اول از هر کدام، پاسخ‌های SJT و V تصادفی. این نمونه به نسبت تعداد majorها حساس است، داده میدانی/ترجیح واقعی نیست و سهم رتبه اول هدف بهینه‌سازی ندارد.
|حالت|تجربی اول|ریاضی اول|انسانی اول|فنی اول|UI بدون کارت|با incomplete branch|
|---|---:|---:|---:|---:|---:|---:|
|baseline|29|34|29|8|0|0|
|E|29|34|29|8|0|0|
|I|29|35|28|8|0|0|

در این نمونهٔ مصنوعی، تعداد رتبه‌اول فنی در هر سه حالت ۸/۱۰۰ است؛ تغییر خالص I نسبت به baseline، ریاضی +۱ و انسانی −۱ است. این مشاهده محدود، اثبات برابری فرصت یا اعتبار علمی نیست، اما جهش C2 را هم نباید به «انحصار عمومی فنی» تعمیم داد.

## ۶. discover_individuality — تفاضل واقعاً اجراشده
مجموعه ثابت **۳۴۰ ورودی**: ۴ fixture + ۲۰۲ مجموعه کد major فعال + ۲۸ مجموعه کد major غیرفعال + ۱۰۰ پروفایل fixed-seed + ۶ edge case (خالی، بدون S، بدون V، S ناقص، duplicate/case/whitespace، کد ناشناخته). ورودی غیرفعال فقط تست است؛ موتور همچنان آن major را غیرفعال می‌بیند. برای دو سناریو، موتور مستقل با deepcopy majors/micro/trait/value map یکسان و فقط branch متفاوت ساخته شد.
|مقایسه با baseline|ورودی|مقایسه scoreهای major برگشتی|تعداد score متفاوت|بیشینه Δscore|full result متفاوت|
|---|---:|---:|---:|---:|---:|
|E|340|637|0|0.0|0|
|I|340|637|0|0.0|0|

- **PASS واقعی: diff امتیاز major = ۰ در هر دو سناریو.** مقایسه `actual == baseline` کل خروجی نیز اجرا و پاس شد، نه فقط score یا order؛ تمام evidence/traits/descriptions/alternative_paths/summary/status حاضر در خروجی یکسان‌اند. مقایسه score شامل ۶۳۷ score برگشتی برای هر سناریو است؛ ورودی‌های بدون match یا پاسخ کامل نیز با equality کل خروجی پوشش داده شده‌اند، نه score جعلی صفر.
- cache گرم: precompute اصلی اجرا و تعداد cacheها ۲۳۰ major و ۴ branch assert شد. cache سرد: چهار fixture برای هر سه instance، قبل و بعد فراخوانی recommend_school_branch، دوباره با golden discover مقایسه شد؛ ۲۴ فراخوانی cold discover به‌علاوه ۱۲ branch call، همگی PASS. خروجی branch نیز در cold برابر نتیجه warm خودش بود. cache یا instance زنده production دست‌کاری نشد.
- SHA-256 ورودی‌های ۳۴۰تایی (canonical JSON، شامل label/codes/S/V): `f1b76560bec62a96748b09f2e5730786dd48846b0a6a16fa3484275f9048916f`.
- hash همه ۱۰ مسیر محلی قبل/بعد آزمایش برابر بود (مسیر غایب در main باید غایب می‌ماند)؛ snapshot داده pinned و majors هر سه instance نیز پس از اجرا byte-equivalent در serialization/ساختار ماندند. فقط حافظهٔ branch candidate متفاوت است.

## ۷. حکم Go / No-Go برای PR اجرایی بعدی
**حکم فعلی: No-Go برای PR اجرایی نهایی school_branches؛ Go فقط برای review همین خروجی آفلاین.** دلیل، شکست تست M یا آسیب majors نیست: همه آزمون‌های تعریف‌شده و انجام‌شدهٔ بالا پاس شده‌اند. مانع فعلی این است که عضویت ۲۶ مورد هنوز تأیید نشده و اثر محتواییِ مشخص I (به‌ویژه V فنی، C2 و افت evidence انسانی) هنوز پذیرش ناظر ندارد. رتبه اول فنی به خودی خود خطا یا دلیل رد نیست؛ تحمیل سهم برابر/ریاضی‌اول مجاز نیست.
- **E: No-Go به عنوان نسخه اجرایی**؛ حذف silentِ ۲۶ عضو از میانگین، سیاست عضویت معناداری برای کل branch نیست. صرفاً شاهد حساسیت به fieldهای ناقص است.
- **I: گزینه قابل بررسی برای PR بعدی فقط پس از مجوز جدا**: تصویب تک‌تک پیشنهادها/manifest و وزن برابر majors، پذیرش روشن deltaهای بالا و از‌دست‌رفتن جفت‌های informative، و حفظ منشأ «میانگین مدل از داده‌های موجود» نه «اعتبارسنجی میدانی». ۱۶۰ major تاریخی دوباره ممیزی نشده‌اند؛ این محاسبه تأیید علمی تازه برای آن‌ها نیست.
- بعد از آن، اگر ناظر PR اجرایی را خواست، تنها فایل runtime مجاز `school_branches_v2.json` و فقط S/V مصوب؛ docs/tests مرتبط ممکن، اما engine/majors/micro/root+mirror/UI/گیت/activation ممنوع. codes و denominator و metadata در این طرح ثابت‌اند. برای نسخه جدید نباید high_school_branchهای majors را در همان PR پر کرد. اگر تصمیم metadata جدید لازم دارد، scope آن قبل از اجرا جدا تأیید شود.
- قبل از PR بعدی، HEAD تازه deploy دوباره pin و همین آزمایش تکرار شود؛ hash candidate باید مطابق snapshot و روش گردکردن باشد. تغییر ورودی نیازمند نتیجه جدید است، نه استفاده از عددهای این سند برای فایل تازه. Gateهای قرارداد API/UI و CI/fingerprint در PHASE0 همچنان برقرارند؛ در این فاز مرورگر، live یا آزمون integration endpoint اجرا نشد.
- rollbackِ نسخه آینده: بازگرداندن دقیق branch از blob مبنا در PR بازگشت با تأیید ناظر، reload instance/cache و replay golden tests؛ نه revert موتور یا DH-013. CI قرمز موجود با این سند درمان/تضعیف نشده و هیچ Merge/deploy/live-green ادعا نمی‌شود.

## ۸. اثر انگشت منابع و بازتولید
|مسیر در SHA مبنا|SHA-256|
|---|---|
|`dark_horse_engine_v2.py`|`8ce3ef7220c008bd910d85069c2627b44eceebbaf596eea7c0f76bb2481c7168`|
|`main_v2.py`|`6d3ebcf4606e5d7831b8298be83b64871bbe36d85f2ae13c2b6caeb7ad995557`|
|`school_branches_v2.json`|`49821a86476dc9d5bb2d8fee68048be83121aa74bc2bd03715b9c1c73ff88412`|
|`majors_database_v2.json`|`2cbdfb59f8e3ec60a6c7be226800baffc6361083127773a9d8e1eea91fb88010`|
|`docs/data/micro_motives.json`|`34f04251e4d6a7b09e18c117c6af9e5670464dd60047fff5407d89a1fa63edde`|
|`micro_motives.json`|`34f04251e4d6a7b09e18c117c6af9e5670464dd60047fff5407d89a1fa63edde`|
|`trait_map_v3.json`|`6d11d19b8ac565f84a6e44a6cc8e91832891a557cce694650852b02bfc6a4bc1`|
|`value_poles_v2.json`|`84390b1d3c00b08f86492e48c8b301d3d3fc61a1f24a5d6727f0f08bbc68c82b`|
|`test_engine_psychometrics.py`|`3d1bae31a007f7d86547752d52782cd392349d61663b46847a617e8251500ba9`|
|`docs/app.js`|`c55843d01e818ff3953f84d4c248c3dbe6cee43e98626bcc86412909acef18b0`|

### اسکریپت دقیق آزمایش
از ریشه repository که commit مبنا را دارد، بلوک زیر را با Python 3.11 اجرا کنید. فقط stdlib؛ خواندن داده با git show. این اسکریپت هیچ `open(..., "w")` یا write برای candidate/JSON ندارد و فقط stdout گزارش می‌دهد؛ برای کپی آن به فایل موقت از مسیری خارج repository استفاده شود. canonical JSON برای checksum در حافظه است. این کد بخشی از سند است، نه تغییر engine یا pipeline.
```python
# Read-only pinned-source experiment. Candidates exist only as Python objects.
import copy, hashlib, json, math, random, subprocess
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from pathlib import Path

SHA = '03cbc16697c111514dccdc70fa1e980f90bb0cce'
PATHS = ['dark_horse_engine_v2.py', 'main_v2.py', 'school_branches_v2.json',
         'majors_database_v2.json', 'docs/data/micro_motives.json', 'micro_motives.json',
         'trait_map_v3.json', 'value_poles_v2.json', 'test_engine_psychometrics.py', 'docs/app.js']
def local_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None
local_before = {p: local_hash(p) for p in PATHS}
raw = {p: subprocess.check_output(['git', 'show', SHA + ':' + p]) for p in PATHS}
assert raw['micro_motives.json'] == raw['docs/data/micro_motives.json']
data = {p: json.loads(v) for p, v in raw.items() if p.endswith('.json')}
input_hashes = {p: hashlib.sha256(v).hexdigest() for p, v in raw.items()}
def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
def digest(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()
input_snapshot = digest(data)
ns = {'__name__': 'phase0b_pinned_engine', '__file__': 'pinned/dark_horse_engine_v2.py'}
exec(compile(raw['dark_horse_engine_v2.py'], ns['__file__'], 'exec'), ns)
Engine = ns['DarkHorseEngineV2']

def engine(branches, warm=True):
    e = Engine.__new__(Engine)  # bypass filesystem loader, NOT the scoring methods
    e.motives_map = {m['code']: m['description_fa'] for m in copy.deepcopy(data['docs/data/micro_motives.json'])}
    e.majors_db = {m['id']: m for m in copy.deepcopy(data['majors_database_v2.json'])}
    e.trait_map = {q: {int(k): v for k, v in opts.items()} for q, opts in copy.deepcopy(data['trait_map_v3.json']).items()}
    e.value_poles = copy.deepcopy(data['value_poles_v2.json'])
    e.school_branches = {b['name']: copy.deepcopy(b) for b in branches}
    e._alt_paths_cache = {}; e._branch_alt_paths_cache = {}
    e._validate_schema_consistency()
    if warm:
        e._precompute_alternative_paths()
        assert len(e._alt_paths_cache) == len(e.majors_db)
        assert len(e._branch_alt_paths_cache) == 4
    return e

baseline = data['school_branches_v2.json']
active = [m for m in data['majors_database_v2.json'] if m['motive_driven'] is True]
nulls = [m for m in active if not m.get('high_school_branch')]
assert len(active) == 202 and len(nulls) == 26 and all(161 <= m['id'] <= 230 for m in nulls)
probe = engine(baseline, warm=False)
def norm(codes):
    return {str(c).strip().lower() for c in codes if c and str(c).strip()}
pools = {b['name']: probe._active_branch_code_set(b['micro_motive_codes']) for b in baseline}
explicit = {b['name']: [] for b in baseline}
extended = copy.deepcopy(explicit)
proposals = []
for m in active:
    cs = norm(m['micro_motive_codes'])
    overlaps = {name: len(cs & codes) for name, codes in pools.items()}
    hits = [name for name, count in overlaps.items() if count > 0]
    assert len(hits) == 1 and overlaps[hits[0]] == len(cs), m['id']
    given = m.get('high_school_branch')
    if given:
        assert given == hits[0] and given in explicit
        explicit[given].append(m['id'])
    else:
        proposals.append(dict(id=m['id'], name=m['name'], branch=hits[0],
                              overlap=overlaps[hits[0]], total=len(cs), other_overlap=0))
    extended[hits[0]].append(m['id'])
assert [len(explicit[b['name']]) for b in baseline] == [54,55,51,16]
assert [len(extended[b['name']]) for b in baseline] == [54,62,59,27]

Q = Decimal('0.0001')
major_by_id = {m['id']: m for m in active}
input_max_sum_error = Decimal(0)
for m in active:
    sw, vw = m['strategy_weights'], m['value_weights']
    assert len(sw) == 25 and all(len(row) == 5 for row in sw)
    assert set(vw) == {f'Q{i}{side}' for i in range(1,16) for side in 'AB'}
    for row in sw:
        assert all(math.isfinite(x) and 0 <= x <= 1 for x in row)
        err = abs(sum(map(lambda x: Decimal(str(x)), row)) - 1)
        input_max_sum_error = max(input_max_sum_error, err)
        assert err <= Decimal('0.001')
    assert all(math.isfinite(x) and 0 <= x <= 1 for x in vw.values())

def candidate(membership):
    out = copy.deepcopy(baseline)
    with localcontext() as ctx:
        ctx.prec = 50
        for b in out:
            members = [major_by_id[i] for i in membership[b['name']]]
            assert members
            n = Decimal(len(members)); sw = []
            for q in range(25):
                means = [sum(Decimal(str(m['strategy_weights'][q][j])) for m in members) / n for j in range(5)]
                total = sum(means); assert total > 0
                row = [(x/total).quantize(Q, rounding=ROUND_HALF_EVEN) for x in means]
                idx = max(range(5), key=lambda j: means[j])  # first index on tie
                row[idx] += Decimal(1) - sum(row)
                assert sum(row) == 1 and all(0 <= v <= 1 for v in row)
                sw.append([float(x) for x in row])
            b['strategy_weights'] = sw
            b['value_weights'] = {
                key: float((sum(Decimal(str(m['value_weights'][key])) for m in members)/n).quantize(Q, rounding=ROUND_HALF_EVEN))
                for key in b['value_weights']}
    for before, after in zip(baseline, out):
        assert {k:v for k,v in before.items() if k not in ('strategy_weights','value_weights')} == {
            k:v for k,v in after.items() if k not in ('strategy_weights','value_weights')}
    return out

candidates = {'E': candidate(explicit), 'I': candidate(extended)}
engines = {'baseline': engine(baseline), **{key: engine(value) for key,value in candidates.items()}}
a = ['AERO-001','AERO-002','AERO-003','AERO-005','AERO-006','AERO-007','AERO-008','AGM-001','AGM-002','AGM-003']
b = ['ARCHA-001','ARCHA-002','ARCHA-003','ARCHA-004','ARCHA-005','ARCHA-006','ARCHA-007','FAS-001','FAS-002','FAS-003']
profiles = {'A': a, 'B': b, 'C1': a[:5]+b[:5], 'C2': ['ANB-001','ANB-002','ANB-003','AERO-001','AERO-002','AERO-003','ACC-001','ACC-002','ACC-003','ARCHA-001','ARCHA-002','ARCHA-003']}
sjt = {f'sjt_{i}':'C' for i in range(1,26)}
conj = {f'conj_{i}': f'Q{i}'+('A' if i%2 else 'B') for i in range(1,16)}
branch_results = {key: {p: e.recommend_school_branch(codes, sjt, conj) for p,codes in profiles.items()} for key,e in engines.items()}
old = json.loads(Path('docs/weight-review/PHASE0_SCHOOL_BRANCHES_REBUILD.md').read_text().split('```json\n')[1].split('```')[0])
assert profiles == old
for key in candidates:
    for p in profiles:
        base_rows = {r['branch_name']:r for r in branch_results['baseline'][p]['recommended_branches']}
        rows = {r['branch_name']:r for r in branch_results[key][p]['recommended_branches']}
        assert base_rows.keys() == rows.keys()
        for name,row in rows.items():
            assert row['avg_components']['m_score'] == base_rows[name]['avg_components']['m_score']
            # Also compare unrounded M, not only its API rendering.
            assert engines[key]._compute_branch_m_score(profiles[p],engines[key].school_branches[name]) == engines['baseline']._compute_branch_m_score(profiles[p],engines['baseline'].school_branches[name])
        assert branch_results[key][p]['best_branch'] is not None

def visible(result):
    return [r['branch_name'] for r in result['recommended_branches'] if r['average_score'] >= 30 and r['avg_components']['m_score'] >= 15]
branch_gates = {}
for key in engines:
    r = branch_results[key]
    branch_gates[key] = dict(A=r['A']['best_branch']=='ریاضی فیزیک', B=r['B']['best_branch']=='فنی و حرفه‌ای',
        C1=set(visible(r['C1']))=={'ریاضی فیزیک','فنی و حرفه‌ای'}, C2=len(visible(r['C2']))==4)
    assert all(branch_gates[key].values())

# Fixed 340 cases, deterministic content. Full results compared, not just score.
cases = [(p, codes, sjt, conj) for p,codes in profiles.items()]
cases += [(f'active-{m["id"]}',m['micro_motive_codes'],sjt,conj) for m in active]
inactive = [m for m in data['majors_database_v2.json'] if m['motive_driven'] is False]
assert len(inactive)==28
cases += [(f'inactive-{m["id"]}',m['micro_motive_codes'],sjt,conj) for m in inactive]
rng = random.Random(20261023)
for i in range(100):
    chosen = rng.sample(active, k=4)
    codes = [c for m in chosen for c in m['micro_motive_codes'][:4]]
    ss = {f'sjt_{j}':rng.choice('ABCDE') for j in range(1,26)}
    vv = {f'conj_{j}':f'Q{j}'+rng.choice('AB') for j in range(1,16)}
    cases.append((f'random-{i}',codes,ss,vv))
cases += [('empty',[],{},{}), ('no-S',a,{},conj), ('no-V',a,sjt,{}),
          ('partial-S',a,{'sjt_1':'C'},conj), ('duplicates',[a[0],a[0].lower(),' '+a[0]+' '],sjt,conj),
          ('unknown',a+['NOT-A-CODE'],sjt,conj)]
assert len(cases)==340
regression = {key:dict(cases=0,score_comparisons=0,max_score_delta=0.0,score_differences=0,full_result_differences=0) for key in candidates}
golden = {}
for label,codes,ss,vv in cases:
    base = engines['baseline'].discover_individuality(codes,ss,vv)
    if label in profiles: golden[label] = base
    for key in candidates:
        actual = engines[key].discover_individuality(codes,ss,vv)
        assert actual == base, (key,label,'full result mismatch')
        br = {m['major_id']:m['individuality_fit']['score'] for m in base['discovered_majors']}
        ar = {m['major_id']:m['individuality_fit']['score'] for m in actual['discovered_majors']}
        assert ar == br
        deltas = [abs(ar[mid]-v) for mid,v in br.items()]
        r = regression[key]; r['cases'] += 1; r['score_comparisons'] += len(deltas)
        r['max_score_delta'] = max([r['max_score_delta']]+deltas)
# Clear caches for four canonical cases per instance, before/after branch call.
for key,e in engines.items():
    for label,codes in profiles.items():
        e._alt_paths_cache = {}; e._branch_alt_paths_cache = {}
        assert e.discover_individuality(codes,sjt,conj) == golden[label]
        assert e.recommend_school_branch(codes,sjt,conj) == branch_results[key][label]
        assert e.discover_individuality(codes,sjt,conj) == golden[label]

# Supplementary branch sensitivity on the same 100 fixed-seed cases.
random_branch_stats = {}
for key,e in engines.items():
    best_counts = {b['name']:0 for b in baseline}
    empty_visible = incomplete = 0
    for label,codes,ss,vv in cases:
        if not label.startswith('random-'): continue
        r = e.recommend_school_branch(codes,ss,vv)
        if r['best_branch'] in best_counts: best_counts[r['best_branch']] += 1
        empty_visible += not bool(visible(r))
        incomplete += bool(r['incomplete_assessments'])
    random_branch_stats[key] = dict(best=best_counts,empty_visible=empty_visible,incomplete=incomplete)
pair_changes = {}
for key,e in engines.items():
    pair_changes[key] = {}
    for name,b in e.school_branches.items():
        old_v = engines['baseline'].school_branches[name]['value_weights']
        vw = b['value_weights']
        lost = []; gained = []
        for i in range(1,16):
            before = round(abs(old_v[f'Q{i}A']-old_v[f'Q{i}B']),12)
            after = round(abs(vw[f'Q{i}A']-vw[f'Q{i}B']),12)
            if before >= e.V_EPSILON > after: lost.append((i,before,after))
            if before < e.V_EPSILON <= after: gained.append((i,before,after))
        pair_changes[key][name] = dict(lost=lost,gained=gained)

v_pairs = {key: {name:sum(round(abs(b['value_weights'][f'Q{i}A']-b['value_weights'][f'Q{i}B']),12)>=e.V_EPSILON for i in range(1,16)) for name,b in e.school_branches.items()} for key,e in engines.items()}
assert input_snapshot == digest(data)
for e in engines.values():
    assert list(e.majors_db.values()) == data['majors_database_v2.json']
assert local_before == {p:local_hash(p) for p in PATHS}
summary = dict(source=SHA, memberships={'E':explicit,'I':extended}, proposals=proposals,
    candidate_hashes={key:digest(value) for key,value in candidates.items()},
    case_set_sha256=digest(cases), regression=regression, branch_gates=branch_gates,
    informative_pairs=v_pairs, pair_changes=pair_changes, random_branch_stats=random_branch_stats, input_max_S_sum_error=str(input_max_sum_error),
    input_hashes=input_hashes, cold_cache_canonical_cases_per_instance=4,
    source_data_mutation=False, runtime_file_mutation=False)
if __name__ == '__main__':
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    for key,prs in branch_results.items():
        for p,r in prs.items():
            print(key,p,'best=',r['best_branch'],'visible=',visible(r))
            for row in r['recommended_branches']:
                print(' ',row['branch_name'],row['avg_components'],'Total',row['average_score'])
```
