# نقشهٔ فیلدها، مصرف‌کنندگان و دامنهٔ حاکمیت — Dark Horse V2

**نسخه:** 1.0-draft  
**تاریخ ممیزی:** 2026-10-30  
**Base:** `deploy/liara-commercial-sandbox` در `a743ab8ddd335c49e579299f062778bd4f8e6e85`  
**وضعیت:** نقشهٔ خواندنی برای بازبینی؛ هیچ projection، fingerprint، expected یا gate اجرایی را تغییر نمی‌دهد.

---

## 1. هدف و روش

این سند خروجی مرحلهٔ field mapping از معماری چهاردامنه‌ای است. هر فیلد با سه پرسش بررسی می‌شود:

1. کدام کد/مصرف‌کننده آن را می‌خواند یا ذخیره می‌کند؟
2. تغییر آن چه اثری بر scoring، membership/guidance، evidence content یا interpretation/presentation دارد؟
3. آیا این اثر در fingerprint و mutation test فعلی پوشش داده شده است؟

**مرز شواهد:** این ممیزی روی call-siteهای اصلی زیر در snapshot مشخص انجام شده است: `dark_horse_engine_v2.py`، `admission_sanjesh_engine.py`، `docs/app.js`، `seed_reference_data.py`، `models.py` و `reference_fingerprints.py`، به‌علاوهٔ قراردادهای اعتبارسنجی مرتبط. نبودن یک فیلد در این فایل‌های بررسی‌شده، اثبات نبود مصرف آن در کل repository نیست؛ چنین مواردی صریحاً «مصرف اثبات‌نشده/نیازمند scan تکمیلی» علامت خورده‌اند.

## 2. نسخه‌های دقیق کد و دادهٔ مبنا

| منبع | Blob در snapshot |
|---|---|
| `dark_horse_engine_v2.py` | `9ce233695ff50ca7492b9944e87b823a48d0e6ed` |
| `admission_sanjesh_engine.py` | `722e8099c9fff3cc54cca8b54f472fcb3a2d6bc4` |
| `docs/app.js` | `c0fe4029f1a5bfabcc01ac7420c5d6951baca73d` |
| `seed_reference_data.py` | `0909396920cef5127835dbb8a203f5a4b11de01d` |
| `models.py` | `c6c28bc047981f30826764a89df279f8d520b5d7` |
| `reference_fingerprints.py` | `bffdf430f6602e2c498eff3bead1192830541045` |
| `majors_database_v2.json` | `abce609d8a8683f0168d251718e3f743b03dd2b7` |
| `micro_motives.json` در ریشه | `c59ab2a5d82283d2c4a5f503c42190e1740af780` |
| `docs/data/micro_motives.json` | `c59ab2a5d82283d2c4a5f503c42190e1740af780` |
| `school_branches_v2.json` | `abb7b08a6686a570f997a872fd13b3b0683a67a8` |
| `docs/data/questions_v2.json` | `17f0d764538657e1f8b4b5efe2dad8a6bf368bb3` |
| `trait_map_v3.json` | `466280fe517b7e6ba68e54dbe8535de7444c7f4a` |
| `value_poles_v2.json` | `251d435d57b90e325ff671a4f8c69c530de61494` |

خطوط ذکرشده در ادامه نسبت به همین blobهای دقیق هستند و با تغییر commit باید دوباره resolve شوند.

## 3. نگاشت مصرف‌کننده به دامنه

### 3.1 رشته‌ها — `majors_database_v2.json`

| فیلد | مصرف‌کنندهٔ احرازشده | اثر تغییر | دامنهٔ پیشنهادی | وضعیت در fingerprint فعلی |
|---|---|---|---|---|
| `id` | `DarkHorseEngineV2._load_json(..., key_field="id")`؛ کلید اصلی lookup و `major_id` خروجی (engine lines 45–48, 830–832) | اتصال پروفایل و نتیجه به رشتهٔ درست را حفظ می‌کند؛ تغییر شناسه می‌تواند اتصال را جابه‌جا کند. | هویت ثابت مشترک برای A و B؛ شناسه نباید با نام نمایشی جایگزین شود. | در scientific و membership projection وجود دارد. |
| `motive_driven` | فیلتر رشته‌های فعال در load/discovery و عبور از ردیف‌های catalog-only (engine lines 48–53, 195–204, 766–780) | eligibility ورود به امتیازدهی فردیت را تغییر می‌دهد. | A — Scientific/scoring | در scientific projection وجود دارد. |
| `micro_motive_codes` | `_compute_m_score`، ساخت مجموعهٔ کد و مخرج M رشته (engine lines 245–274) | صورت/مخرج و هم‌پوشانی M را تغییر می‌دهد. | A — Scientific/scoring | در scientific projection وجود دارد. |
| `strategy_weights` | اعتبارسنجی 25×5 (engine lines 205–238) و `_compute_s_score` (engine lines 335–360) | امتیاز S، highlightها و فاصلهٔ پروفایل جایگزین را تغییر می‌دهد. | A — Scientific/scoring | در scientific projection وجود دارد. |
| `value_weights` | `_compute_v_result` و `_pairwise_value_score` (engine lines 370–430)، فاصلهٔ پروفایل (engine lines 520–550) | امتیاز V و فاصلهٔ مسیرهای جایگزین را تغییر می‌دهد. | A — Scientific/scoring | در scientific projection وجود دارد. |
| `weights_version` | در seed ذخیره می‌شود (seed lines 864–867) و در scoring projection ثبت می‌شود (fingerprints lines 145–183)؛ به‌عنوان ضریب محاسبه در engine مصرف مستقیم مشاهده نشد. | نسخه/منشأ پروفایل را قابل ممیزی می‌کند، اما به‌تنهایی مقدار عددی S/V را تغییر نمی‌دهد. | metadata نسخهٔ پروفایل متصل به A؛ نه ورودی عددی مستقل | در scientific projection هست؛ این عضویت برای provenance است، نه ادعای اثر عددی. |
| `name` | متن personalized description، نام نتیجه و نام مسیر جایگزین (engine lines 805–832, 535–552؛ app.js lines 1320–1330) | بر هویت نمایشی/متن خروجی اثر می‌گذارد؛ در موتور به‌جای id کلید اصلی امتیاز نیست. | D — Interpretation/presentation؛ id ثابت در A/B باقی بماند. | در membership projection فعلی هست؛ این امر نمایش را با membership مخلوط می‌کند و نیازمند تصمیم/مهاجرت نسخه‌دار است. |
| `group` | `realm_fa` در خروجی و فیلد مسیر جایگزین (engine lines 535–552, 830–832) | بر دسته‌بندی و نمایش/توضیح مسیر جایگزین اثر دارد؛ مصرف مستقیم در Total مشاهده نشد. | D — Interpretation/presentation | در membership projection فعلی هست؛ call-site مشاهده‌شده بیشتر نمایشی است. |
| `exam_group` | `_major_target_group` و `_record_target_group` برای استنتاج گروه هدف سنجش/ضرایب پذیرش (admission_sanjesh_engine lines 456–464, 784–801) | گروه سنجش مورد استفاده در مسیر پذیرش را تغییر می‌دهد. | B — Membership/guidance | در membership projection فعلی هست. |
| `high_school_branch` | در seed از JSON به `Major.high_school_branch` منتقل می‌شود (seed lines 845–867؛ مدل lines 97–105). در سه فایل engine/admission_sanjesh_engine/app.jsِ بررسی‌شده، مصرف مستقیم runtime آن احراز نشد. | از نظر معنا رابطهٔ رشته↔شاخهٔ هدایت تحصیلی است؛ تغییر آن باید مستقل ردیابی شود، حتی اگر این call-site scan مصرف بعدی آن را نشان نداده باشد. | B — Membership/guidance؛ call-site downstream هنوز OPEN | در membership projection فعلی هست؛ گیت عضویت طبق GOV-05 باید blocking باشد. |
| `cluster` و `subgroup` | از JSON به مدل `Major` ذخیره می‌شوند (seed lines 855–860؛ models lines 97–100). مصرف مستقیم در فایل‌های موتور/سنجش/فرانت‌اندِ اسکن‌شده پیدا نشد. | طبقه‌بندی/گروه‌بندی محتمل؛ اثر دقیق بر UX یا مسیر پذیرش هنوز ثابت نشده است. | نامزد B یا D؛ فعلاً طبقه‌بندی قطعی ممنوع | در membership projection فعلی هست؛ تا تکمیل scan مصرف‌کننده، دامنهٔ آن تأیید نهایی نیست. |
| `archetype` و `fulfillment_source` | موتور آن‌ها را به نتیجه منتقل می‌کند (engine lines 812–850) و UI آن‌ها را نمایش می‌دهد (app.js lines 1314–1328, 1515–1531). | محتوای هویتی/تفسیری نتیجه را تغییر می‌دهد، نه فرمول عددی Total در call-site مشاهده‌شده. | D — Interpretation/presentation | در scientific و membership projection فعلی نیستند. |
| `prestige_level` | به `market_demand_level` در پاسخ نتیجه نگاشت می‌شود (engine lines 837–841). همان کد تصریح می‌کند این فیلد در snapshot دیتابیس فعلی وجود ندارد و مقدار null برمی‌گردد. | در صورت افزودن، اطلاعات نمایشی/تقاضای بازار را تغییر می‌دهد؛ score نیست. | D — Interpretation/presentation | در fingerprintهای فعلی دیده نمی‌شود؛ فعلاً در JSON حاضر نیست. |
| `handcrafted` | در seed validation برای waveهای مشخص کنترل می‌شود (seed lines 503–542, 565–582, 639–738)؛ در `verify_hybrid_staging.py` هم در parity JSON↔DB مقایسه می‌شود (lines 115–146). مصرف عددی در engine مشاهده نشد. | provenance/وضعیت دستی‌سازی و کنترل ورود wave؛ نه مؤلفهٔ Total. | metadata/provenance؛ تا consumer اجرایی دیگری اثبات نشده وارد A/B/D نشود. | در scoring و membership projection فعلی نیست؛ باید در change/evidence record پوشش داشته باشد. |

### 3.2 شاخه‌ها — `school_branches_v2.json`

| فیلد | مصرف‌کنندهٔ احرازشده | اثر تغییر | دامنهٔ پیشنهادی | وضعیت در fingerprint فعلی |
|---|---|---|---|---|
| `name` | موتور شاخه‌ها را با نام در `self.school_branches` key می‌کند و `recommend_school_branch` روی همان نام iterate می‌کند (engine lines 95–125, 900–935). | کلید lookup فعلی و نام خروجی است؛ rename بدون مهاجرت می‌تواند lookup را بشکند. | B — membership/identity؛ نمایش نام نیز در D ردیابی شود. | در scientific و membership projection هست. |
| `micro_motive_codes` | `_compute_branch_m_score` و فیلتر کدهای فعال (engine lines 276–322؛ توصیه شاخه lines 900–935) | مخرج/صورت M شاخه و شواهد جرقه‌های matched را تغییر می‌دهد. | A — Scientific/scoring؛ اتصال کدها باید با membership contract نیز تطبیق داده شود، اما عدد M در A است. | در scientific projection هست. |
| `m_score_denom_limit` | مخرج M شاخه در `_compute_branch_m_score` (engine lines 294–306) | مقدار M شاخه را تغییر می‌دهد. | A — Scientific/scoring | در scientific projection هست. |
| `strategy_weights` و `value_weights` | مستقیم در `recommend_school_branch` برای S/V شاخه و در alternative path distance (engine lines 900–935, 560–590) | score شاخه و فاصلهٔ مسیر جایگزین را تغییر می‌دهد. | A — Scientific/scoring | در scientific projection هست. |
| `group` | در engine call-site مستقیمی مشاهده نشد؛ در مدل `SchoolBranch` ذخیره است (models lines 117–132). | احتمالاً metadata/طبقه‌بندی نمایشی؛ اثر مصرف‌کننده هنوز ثابت نشده. | D یا B پس از scan تکمیلی؛ فعلاً OPEN | در membership projection فعلی هست. |
| `source_majors_count` | از JSON در seed به `SchoolBranch.source_majors_count` منتقل می‌شود (seed lines 880–889؛ models lines 117–128) و در `dual_run_audit.py` برای materialize کردن snapshot DB بازخوانی می‌شود (lines 70–82). مصرف مستقیم در موتور توصیهٔ شاخه یا فرمول امتیاز احراز نشد. | شمارنده/منشأ تعداد رشته‌های مبنای شاخه و parity داده؛ نه مؤلفهٔ M/S/V. | B — integrity/provenance metadata؛ فقط پس از تعریف دقیق اینکه شمارش از چه مجموعه/وضعیتی مشتق می‌شود. | در membership projection فعلی وارد نشده؛ باید mutation test شمارش و قرارداد مشتق‌سازی داشته باشد. |
| `weights_version` | در مدل ذخیره و در scientific projection وارد می‌شود؛ مصرف عددی مستقیم در engine مشاهده نشد. | نسخهٔ ماتریس شاخه برای provenance است. | metadata نسخهٔ پروفایل متصل به A | در scientific projection فعلی هست. |

### 3.3 خرده‌انگیزه — `micro_motives.json`

| فیلد | مصرف‌کنندهٔ احرازشده | اثر تغییر | دامنهٔ پیشنهادی | وضعیت در fingerprint فعلی |
|---|---|---|---|---|
| `code` | کلید `motives_map` در engine (engine lines 40–46)؛ تطبیق کدهای رشته و شاخه در M (lines 245–322)؛ کنترل ref در `reference_contract_audit.py` و `test_p0_data_contract.py` | تغییر کد می‌تواند referenceهای رشته/شاخه و M را بشکند. | A — Scientific/scoring و referential integrity | مجموعهٔ کدها در scientific projection هست. |
| `description_fa` | engine مقدار متن را برای matched evidence می‌سازد (engine lines 265–274)؛ UI آن را در swipe card نمایش می‌دهد (app.js lines 342–346, 884–895)؛ مدل MicroMotive آن را ذخیره می‌کند (models lines 44–55, seed lines 796–800). | متن شاهد/محتوای علمیِ پشت وزن را عوض می‌کند و همان متن در تجربهٔ کاربر نیز دیده می‌شود؛ تغییر با وزن ثابت هم باید بازبینی متن و وزن‌های وابسته را فعال کند. | C — Evidence-content؛ مصرف نمایشی به‌عنوان اثر ثانویه در گزارش ثبت شود. | **در fingerprint علمی فعلی نیست**؛ فقط code set hash می‌شود. شکاف high priority است. |
| `category` و `intensity_level` | category در مدل/seed ذخیره می‌شود؛ در engine scoring call-site مشاهده نشد. | طبقه‌بندی/ویژگی محتوایی محتمل؛ مصرف‌کنندهٔ فعال در مسیر scoring بررسی‌شده احراز نشد. | C یا D پس از scan تکمیلی | در fingerprint فعلی وارد نمی‌شود. |

### 3.5 مصرف‌کنندگان تکمیلیِ کشف‌شده در اسکن سراسری

اسکن تکمیلی مسیرهای runtime، persistence، مشاوره، seed، migration و تست‌ها نشان داد برخی داده‌ها پس از خروجی engine به مصرف‌کننده‌های دیگری می‌رسند:

| فیلد/داده | مصرف‌کنندهٔ اضافه و محل استفاده | طبقه‌بندی دقیق |
|---|---|---|
| `archetype`، `dominant_values`، `dominant_traits` و `fulfillment_source` | `ai_counsel_service.py::_arch_bits` این داده‌ها را از نتیجه می‌خواند و برای narrative مشاوره به مؤلفه‌های متنی تبدیل می‌کند (lines 155–183). `operational_store.py` نیز `archetype_info` و `personalized_description` را در نتیجه ذخیره می‌کند (lines 125–150). | D — Interpretation/presentation با مصرف downstream در AI counsel و persistence؛ نه score input. |
| داده‌های رشته/شاخه در DB | `dual_run_audit.py::materialize_engine_from_db`، فیلدهای name/group/cluster/subgroup/exam_group/high_school_branch، پروفایل‌های S/V، متن motive، archetype/fulfillment/prestige و handcrafted را به snapshot موتور بازمی‌سازد (lines 35–90). | این تابع خودِ scoring را تعیین نمی‌کند؛ مصرف آن parity/materialization برای مقایسهٔ JSON و DB است. فیلدهای serializeشده را نباید به‌خاطر حضور در این تابع، مصرف مستقیم الگوریتم تلقی کرد. |
| `high_school_branch` | در `seed_reference_data.py` به `Major.high_school_branch` منتقل می‌شود (lines 845–867)، در ORM و migration ستون دارد، در `reference_fingerprints.py` membership projection را تغییر می‌دهد و در staging parity نیز مقایسه می‌شود؛ مصرف مستقیم downstream در engine و admission consumerهای بررسی‌شده پیدا نشد. | B طبق سیاست مصوب، زیرا معنای رشته↔شاخه دارد و تغییر آن باید blocking باشد؛ وضعیت consumer runtime هنوز OPEN و نباید بیش از شواهد ادعا شود. |
| `exam_group` | `admission_sanjesh_engine.py::_major_target_group` آن را به گروه هدف سنجش نگاشت می‌کند (lines 456–464, 784–801). | B — اثر واقعی guidance/admission. یادداشت: `admission_capacity_record.py` صریحاً می‌گوید گروه منبع ظرفیت با catalog `exam_group` یکی نیست؛ نباید آن دو را یکی فرض کرد. |
| `source_majors_count` | در seed و مدل ذخیره، و در dual-run audit دوباره materialize می‌شود؛ در موتور scoring استفاده نشد. | B — metadata کنترل شمارش/provenance، نه score. |
| `handcrafted` | seed validator و تست‌های مرجع وضعیت تدوین آن را کنترل می‌کنند؛ staging verifier هم parity آن را بررسی می‌کند. | Provenance/review metadata؛ نه A، تا زمانی که اثر algorithmic ثابت نشده باشد. |

**نتیجه:** وجود یک فیلد در ORM، seed یا dual-run materializer به‌تنهایی نشانهٔ اثر بر scoring نیست. در نقشهٔ نهایی، `direct consumer`، `persistence/parity consumer` و `review/provenance consumer` از هم جدا گزارش می‌شوند.

### 3.4 سؤال‌ها، نگاشت صفات و قطب‌های ارزش

| فایل/فیلد | مصرف‌کنندهٔ احرازشده | اثر تغییر | دامنهٔ پیشنهادی | وضعیت فعلی |
|---|---|---|---|---|
| `questions_v2.layers.strategies.questions` — id/order/question/options.index/options.text | UI فهرست را بارگذاری و پاسخ‌ها را به‌صورت index/order نگهداری می‌کند (app.js lines 353–366 و build payload)؛ engine همان index را در ردیف هم‌موقعیت `strategy_weights` مصرف می‌کند (engine lines 335–360). | جابه‌جایی سؤال/گزینه یا تغییر متن آن می‌تواند معنای همان index و در نتیجه معنای S را تغییر دهد. | A و D: اثر mapping/ترتیب باید در A باشد؛ متن/نمایش نیز در D گزارش شود. | strategy questions در scientific projection فعلی هست؛ UI و backend semantic mapping همچنان نیازمند تست mutation است. |
| `questions_v2.layers.values.questions` — id/order/question/options.code/options.text | UI سؤال‌ها و گزینه‌ها را نمایش می‌دهد (app.js lines 353–366, 1119–1147) و codeهای QnA/QnB را در `buildPayload` به payload منتقل می‌کند (app.js lines 1174–1190). engine کد QnA/QnB را با `value_weights` مصرف می‌کند (engine lines 370–430). | تغییر متن prompt یا معنای گزینه بدون تغییر code می‌تواند تفسیر انتخاب کاربر را عوض کند؛ تغییر code/order می‌تواند اتصال جواب به weight را عوض کند. | متن و معنای prompt/label در D؛ code/order که اتصال به وزن را عوض کند در A نیز blocking باشد. | **در scientific projection فعلی فقط strategy questions است؛ value questions در آن نیستند.** |
| `trait_map_v3.json` | engine index پاسخ S را به label صفات برای highlights و trait profile تبدیل می‌کند (engine lines 180–194, 335–360, 613–640)؛ UI نیز `analyzeStrategyStyle` را با همین map اجرا می‌کند (app.js lines 370–390, 1650+) | متن/نگاشت traitها تفسیر و توضیح کاربر را تغییر می‌دهد، نه raw S numeric score را در call-site مشاهده‌شده. | D — Interpretation/presentation | در scoring projection فعلی نیست؛ shared-byte contract آن را با main کنترل می‌کند. |
| `value_poles_v2.json` | engine برچسب QnA/QnB را برای value highlights و dominant poles استفاده می‌کند (engine lines 95–110, 418–430, 648–680) | برچسب/معنای تفسیر V را عوض می‌کند، نه مقدار raw V وقتی code و weights ثابت‌اند. | D — Interpretation/presentation | در scoring projection فعلی نیست؛ shared-byte contract آن را با main کنترل می‌کند. |

## 4. جمع‌بندی پوشش فعلی و شکاف‌ها

| مورد | وضعیت | اولویت |
|---|---|---|
| وزن‌های S/V رشته و شاخه، active flag و کدهای مؤثر M | در scientific projection قرار دارند و engine call-site تأیید شد. | پوشش موجود؛ تست mutation گسترش یابد. |
| عضویت رشته↔شاخه و exam_group | در membership projection وجود دارد؛ exam_group در مسیر سنجش مصرف واقعی دارد؛ high_school_branch فعلاً فقط ذخیره‌شدن آن اثبات شد. | تکمیل scan مصرف‌کنندگان و enforce سیاست GOV-05 |
| متن description_fa | در scoring fingerprint نیست، ولی evidence و UI آن را می‌خوانند. | **P0: evidence-content projection و mutation test مستقل** |
| value questions و code mapping | UI و engine از code/weight استفاده می‌کنند؛ projection علمی فعلی فقط strategy questions را دارد. | **P0: تست mapping؛ تصمیم projection متن/کد** |
| name/group و متون archetype/fulfillment/prestige | در خروجی/نمایش مصرف می‌شوند؛ name و group در membership projection فعلی نیز آمده‌اند. | جداکردن identity پایدار از display label و ساخت presentation projection |
| cluster/subgroup و SchoolBranch.group/source_majors_count | در مدل/seed ذخیره می‌شوند؛ مصرف همهٔ آن‌ها در مسیرهای runtime بررسی‌شده ثابت نشد. | OPEN؛ scan repository/consumer و تصمیم مالکیت |
| handcrafted و weights_version | provenance/version هستند؛ handcrafted در fingerprintها نیست، weights_version در scientific projection هست. | قرارداد provenance و تاریخچهٔ تغییر |

## 5. قرارداد mutation tests برای چهار دامنه

تست‌ها باید روی fixture مستقل و کپی داده اجرا شوند؛ هیچ JSON تولیدی دستکاری نشود.

| Mutation کنترل‌شده | نتیجهٔ مورد انتظار |
|---|---|
| تغییر فقط یک وزن S/V رشته یا شاخه | A تغییر کند؛ B/C/D ثابت بمانند. |
| تغییر فقط `high_school_branch` یا `exam_group` | B به‌صورت مستقل FAIL شود؛ A/C/D ثابت بمانند. |
| تغییر فقط `micro_motives[].description_fa` | C FAIL شود و فهرست رشته/وزن‌های متکی به آن برای evidence review تولید شود؛ A numeric fingerprint فقط در صورت تغییر کد/پروفایل/منطق scoring عوض شود. |
| تغییر کد یک micro-motive که به رشته/شاخه ارجاع دارد | A و referential integrity باید تغییر/FAIL را گزارش کنند؛ هیچ ارجاع شکسته‌ای پذیرفته نیست. |
| تغییر فقط `trait_map` یا `value_poles` label | D تغییر کند؛ raw score domain A ثابت بماند. |
| تغییر متن strategy question/option یا ترتیب/index آن | D تغییر کند؛ اگر معنای index-to-weight عوض می‌شود، A نیز باید تغییر کند. |
| تغییر متن value question/option با code ثابت | D تغییر کند و بازبینی معنایی لازم شود؛ تغییر code/order mapping که جواب را به weight دیگری متصل کند باید A را نیز تغییر دهد. |
| تغییر `archetype`، `fulfillment_source` یا `prestige_level` | D تغییر کند؛ raw score و B/C ثابت بمانند. |
| تغییر فقط `major.name` با id ثابت | D تغییر کند؛ membership relation و numeric profile باید ثابت بمانند. اگر runtime هنوز name را key می‌گیرد (مانند branch.name)، rename تا اصلاح lookup با ID migration ناسازگار و blocking است. |
| تغییر `cluster/subgroup` یا `SchoolBranch.group/source_majors_count` | تا تعیین consumer/owner، تست نباید از پیش domain بسازد؛ ابتدا scan و تصمیم ثبت شود، سپس mutation contract تصویب شود. |

برای هر mutation باید علاوه بر hashها، diff فیلدبه‌فیلد و پیام قابل‌فهم گزارش شود؛ صرف تفاوت digest برای ممیزی انسانی کافی نیست.

## 6. محدودیت‌ها و موارد باز

1. این دور، فهرست کامل tree در base با 366 entry و 354 blob مرور شد؛ اسکن token/call-site روی مسیرهای اصلی Python runtime، API admission، engine، AI counsel، ORM/seed، fingerprint، verifierهای staging/dual-run، frontend JS، testهای مرتبط و workflowها انجام شد. این کار، یک جست‌وجوی معناییِ اثبات‌کننده برای تمام پویایی‌های runtime نیست: importهای غیرمستقیم، reflection، queryهای خارج از repository یا consumerهای external DB ممکن است در متن literal دیده نشوند. پیش از gate اجرایی، review دوم code-owner و test coverage مصرف‌کننده‌های غیرمستقیم لازم است.
2. `high_school_branch` در مدل و seed ذخیره می‌شود؛ مصرف downstream آن در کدهای بررسی‌شده احراز نشد. تصمیم GOV-05 همچنان هر تغییر membership را blocking می‌کند، اما implementation باید تمام consumerها را کشف کند.
3. `reference_fingerprints.py` baselineهای فعلی 194/204/215 و base commit قدیمی‌تر از snapshot ممیزی دارد. این سند expected جدید تولید نمی‌کند و refresh baseline را مجاز نمی‌کند.
4. root و `docs/data/micro_motives.json` در snapshot برابرند؛ موتور پیش‌فرض root را می‌خواند و UI مسیر docs/data را. برابری دو فایل باید در هر commit داده با assertion مستقل کنترل شود.
5. تغییر متن خرده‌انگیزه شاهد را تغییر می‌دهد، حتی وقتی score عددی ثابت بماند؛ content gate باید این رویداد را آشکار کند و فهرست weights وابسته را برای بازبینی بسازد.
6. هیچ یک از جدول‌ها مجوز تغییر JSON، وزن، engine، schema DB، fingerprint module، expected یا workflow نیستند.

## 7. گام بعدی

پس از دو بازبینی مستنداتی:
1. تکمیل repository-wide consumer scan برای فیلدهای OPEN؛
2. تثبیت field map با owner و decision rule؛
3. طراحی validator/mutation contract برای چهار دامنه؛
4. PRهای اجرایی مستقل و اتمیک، فقط پس از مجوز فنی و بدون دست‌کاری baseline برای سبزکردن CI.

