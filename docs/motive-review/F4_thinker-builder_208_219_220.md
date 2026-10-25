# DH-013 F4 — فعال‌سازی محدود (208، 219، 220)

**وضعیت:** شاخهٔ نامزد GitHub ساخته شده؛ روش وزن‌دهی با rubric موجود F1/F2 همسو شده و نسخهٔ نامزد `dh013_f4_review_v2` است. بررسی مستقل و تأیید ناظر همچنان لازم است. PRها باید Draft بمانند؛ ادغام پیش از سبزشدن CI و تأیید صریح ناظر ممنوع است.

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

## DH-013: موتور شناختی و منشأ وزن‌ها

- برای هر هدف، فایل evidence شامل امضای لذت محوری با ≥3 Motive، هفت مؤلفهٔ Cognitive Engine (`core_verb`, `operational_verb`, `dominant_object`, `dominant_reward`, `dominant_frustration`, `time_horizon`, `interaction_mode`)، و Traceability Matrix کدبه‌کد است.
- Motive tier weights طبق روش موجود F2 و به ترتیب هفت کد: `[1, 1, 0.9, 0.9, 1, 0.9, 0.7]`; هر وزن برای هر کد در evidence ذخیره می‌شود. این وزن‌ها رتبه‌بندی شواهد وظیفه‌ای‌اند، نه دادهٔ تجربی.
- Strategy: prevalence وزنیِ تطابق دقیق traitهای `trait_map_v3.json`؛ میانگین prevalence برای traitهای هر گزینه، سپس نرمال‌سازی پنج گزینه. `evidence_confidence` نسبت وزنی کدهای دارای تطابق است. زیر 0.70، وزن نامزد با میانگین گزینهٔ متناظر سه همسایهٔ مستند blend می‌شود.
- Value: از `docs/motive-review/F1_value_cue_rubric.json` (SHA `08785995aab29214e2520c454f04a1beccbfe2f0`): شاهد متنی مستقیم=1، همپوشانی trait=0.5، بدون تطابق=0؛ وزن خام `0.25 + 0.70 × weighted mean`. Confidence با سقف‌های rubric محدود می‌شود و در confidence زیر 0.70، وزن قطب با میانگین همان قطب در سه همسایه blend می‌شود.
- همسایه‌های تنظیم وزن (همه از کاتالوگ پایهٔ بدون تغییر؛ انتخاب‌ها موقت و منتظر تأیید Reviewer A):
  - 208: `101, 104, 105` — حقوق و دو رشتهٔ هم‌زیرگروه حقوقی D1.
  - 219: `69, 68, 73` — باغبانی، مهندسی کشاورزی و مهندسی محیط زیست در حوزهٔ B4.
  - 220: `50, 68, 46` — ماشین‌های کشاورزی، مهندسی کشاورزی و مهندسی مکانیک.
- روش وزن‌دهی نسخه‌دار و قابل‌بازتولید است، اما کالیبراسیون روان‌سنجی ادعا نمی‌شود. تست جداسازی سراسری و آزمون کور هویت تا امضای دو بازبین مستقل **Pending** است؛ هیچ تأیید عددی یا انسانی جعل نشده است.

## منابع نقش

- علوم قضایی/فرایند پرونده: [U.S. Courts — Court Records](https://www.uscourts.gov/court-records)؛ [U.S. Courts — Judicial Administration](https://www.uscourts.gov/administration-policies/judicial-administration).
- فضای سبز/منظر: [ASLA — Green Infrastructure](https://www.asla.org/focus-areas/climate-biodiversity-action/resource-guides/climate-mitigation-landscape-architecture/green-infrastructure_climate_change_mitigation)؛ [ASLA — Public Practice Landscape Architecture](https://www.asla.org/resources/practitioners/professional-practice-networks-home/public-practice-service/guide-to-public-practice-landscape-architecture)؛ [Penn State Extension — Horticulture](https://extension.psu.edu/business-and-operations/starting-a-farm/introduction-to-horticulture).
- مکانیزاسیون: [FAO — Sustainable Agricultural Mechanization](https://www.fao.org/sustainable-agricultural-mechanization/overview/what-is-sustainable-mechanization/en/)؛ [USDA NAL — Agricultural Engineering](https://lod.nal.usda.gov/nalt/en/page/5316)؛ [USDA ARS — Field Machinery Operations](https://www.ars.usda.gov/research/publications/publication/?seqNo115=169182).

## وضعیت CI و ادغام

- قرارداد تست و seed برای F4 باید دقیقاً 208، 219 و 220 را فعال و آن‌ها را از لیست deferred خارج کند؛ fingerprint تاریخی 1..215 با نرمال‌سازی رکوردهای staged حفظ می‌شود.
- هنوز ادعایی مبنی بر سبزبودن CI ثبت نشده است؛ بعد از ایجاد PR واقعی باید همهٔ بررسی‌های الزامی روی head SHA نهایی بررسی شوند.
- **بدون Merge:** PRها Draft بمانند تا ناظر به‌طور صریح اجازه دهد.
