# DH-013 F4 — فعال‌سازی محدود (208، 219، 220)

**وضعیت:** شاخهٔ نامزد GitHub ساخته و داده‌های فعال‌سازی فقط برای سه هدف ثبت شده است. PRها باید Draft بمانند؛ ادغام پیش از سبزشدن CI و تأیید صریح ناظر ممنوع است.

## دامنه و قفل‌ها

- تنها شناسه‌های فعال‌شده در این شاخه: **208 علوم قضایی، 219 مهندسی فضای سبز، 220 مهندسی مکانیزاسیون کشاورزی**.
- هر هدف دارای 7 Motive، 25×5 ماتریس Strategy، و 30 Value pole با شواهد کدبه‌کد در فایل evidence است.
- 162 مهندسی معماری، 163 گردشگری و 171 هتلداری تغییر داده نشده‌اند. شناسه‌های 1..160، F1–F3، 179 و 188 نیز خارج از محدوده‌اند.
- کدها: `COURT-001..007`, `LAND-001..007`, `AGMECH-001..007`. تعداد `micro_motives` پس از این موج: **1,393** (۲۱ مورد افزوده).
- موتور، scoring formula، Hybrid، Total و cutoff تغییر نکرده است.

## جدول اهداف

| ID | رشته | کدها | Archetype | Fulfillment |
|---:|---|---|---|---|
| 208 | علوم قضایی | COURT-001…007 | تحلیل‌گر-هماهنگ‌کنندهٔ فرایند دادرسی | وقتی پرونده از ثبت و کنترل شکلی تا ارجاع و جلسه، با صلاحیت درست، مهلت‌های روشن و سابقهٔ قابل‌ردگیری پیش می‌رود. |
| 219 | مهندسی فضای سبز | LAND-001…007 | طراح-سامان‌دهندهٔ زیرساخت سبز | وقتی نقشه و جزئیات فضای باز به محیطی قابل‌دسترس، کم‌مصرف در آب و سازگار با زهکشی و اکوسیستم محلی تبدیل می‌شود. |
| 220 | مهندسی مکانیزاسیون کشاورزی | AGMECH-001…007 | مهندس-هماهنگ‌کنندهٔ عملیات مکانیزهٔ مزرعه | وقتی انتخاب و تنظیم ماشین و ادوات، عملیات مزرعه را در پنجرهٔ مناسب با پوشش یکنواخت و اتلاف/مصرف کمتر اجرا می‌کند. |

## تمایزهای اجباری

1. **208 ↔ 101 حقوق:** علوم قضایی در این طرح بر گردش پرونده، صلاحیت، ابلاغ، مهلت، سوابق و سلامت آیینی تمرکز دارد؛ حقوق بر تفسیر قواعد و ساخت استدلال/دفاع حقوقی. منابع اداری بین‌المللی برای توصیف workflow پرونده‌اند، نه به‌عنوان تفسیر قانون ایران.
2. **219 ↔ 69 باغبانی:** فضای سبز طراحی سایت و فضای باز، مسیرها، آب/خاک، زهکشی، دسترسی و عملکرد اکولوژیک را یکپارچه می‌کند؛ باغبانی بر پرورش، تکثیر، سلامت گیاه و کیفیت محصول متمرکز است.
3. **220 ↔ 68/50:** مکانیزاسیون بر انتخاب، تطبیق، کالیبراسیون، زمان‌بندی، بهره‌برداری و نگهداری ماشین در عملیات مزرعه متمرکز است؛ 68 سامانهٔ کلی تولید کشاورزی را پوشش می‌دهد و 50 بر طراحی/ساخت خود ماشین تمرکز دارد.

## منشأ وزن‌ها و معیار بازتولید

- Strategy از 25 سؤال و پنج گزینهٔ ثابت در قالب F2 و `trait_map_v3.json` استفاده می‌کند. هفت کد نقش هرکدام وزن پایهٔ واحد `1.0` دارند؛ امتیاز خام گزینه، شمار کدهایی است که حداقل یک trait دقیقاً مشترک دارند، سپس امتیازها در همان سؤال نرمال می‌شوند. هر گزینه هفت ارجاع کدبه‌کد S/C دارد.
- Value از 30 pole ثابت در `value_poles_v2.json` استفاده می‌کند: شاهد مستقیم در متن Motive برابر 1، همپوشانی trait برابر 0.5، و نبود شاهد برابر 0. وزن pole برابر `0.25 + 0.70 × mean(score across seven equal-weight motives)` است. cue-keywordها، نگاشت traitها و امتیاز هر کد برای هر pole در evidence JSON ذخیره شده است.
- این وزن‌ها خروجی قاعده‌محور و قابل‌بازتولیدند، نه کالیبراسیون تجربی. چون ضریب همسایهٔ قابل‌بازتولید در rubric موجود تعریف نشده، blending عددی اعمال نشده است. بازبینی مستقل A/B هنوز امضا نشده و پیگیری باز است.

## منابع نقش

- علوم قضایی/فرایند پرونده: [U.S. Courts — Court Records](https://www.uscourts.gov/court-records)؛ [U.S. Courts — Judicial Administration](https://www.uscourts.gov/administration-policies/judicial-administration).
- فضای سبز/منظر: [ASLA — Green Infrastructure](https://www.asla.org/focus-areas/climate-biodiversity-action/resource-guides/climate-mitigation-landscape-architecture/green-infrastructure_climate_change_mitigation)؛ [ASLA — Public Practice Landscape Architecture](https://www.asla.org/resources/practitioners/professional-practice-networks-home/public-practice-service/guide-to-public-practice-landscape-architecture)؛ [Penn State Extension — Horticulture](https://extension.psu.edu/business-and-operations/starting-a-farm/introduction-to-horticulture).
- مکانیزاسیون: [FAO — Sustainable Agricultural Mechanization](https://www.fao.org/sustainable-agricultural-mechanization/overview/what-is-sustainable-mechanization/en/)؛ [USDA NAL — Agricultural Engineering](https://lod.nal.usda.gov/nalt/en/page/5316)؛ [USDA ARS — Field Machinery Operations](https://www.ars.usda.gov/research/publications/publication/?seqNo115=169182).

## وضعیت CI و ادغام

- قرارداد تست و seed برای F4 باید دقیقاً 208، 219 و 220 را فعال و آن‌ها را از لیست deferred خارج کند؛ fingerprint تاریخی 1..215 با نرمال‌سازی رکوردهای staged حفظ می‌شود.
- هنوز ادعایی مبنی بر سبزبودن CI ثبت نشده است؛ بعد از ایجاد PR واقعی باید همهٔ بررسی‌های الزامی روی head SHA نهایی بررسی شوند.
- **بدون Merge:** PRها Draft بمانند تا ناظر به‌طور صریح اجازه دهد.
