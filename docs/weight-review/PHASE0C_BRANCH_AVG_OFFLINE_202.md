# PHASE0C — آزمایش آفلاین میانگین شاخه از ۲۰۲ عضویت قطعی

**حکم: No-Go برای PR اجرایی بعدی با همین candidate به شکل S/V-only.** آزمایش‌های canonical و عدم تغییر خروجی majorها پاس‌اند؛ اما حذف کارت در پاسخ ناقص V بازتولید شد و مخزن M برای سه major هنوز با عضویت مصوب هم‌راستا نیست. هیچ JSON عملیاتی، engine یا gate نوشته/تغییر داده نشد؛ candidate فقط در حافظه است. این سند مجوز Merge/deploy یا شروع دسته وزن/activation نیست.

## ۱. مبنا و عضویت قطعی
- تاریخ: 2026-10-25. مبنای ثابت، HEAD deploy پس از #303: **`dd76083836c80732caf33c38b3d59b837f88c284`**؛ با remote کنترل شد. داده و موتور از git show همین SHA خوانده شدند، نه working tree قدیمی main.
- **تأیید یک‌خطی: تعداد فعال با high_school_branch معتبر = ۲۰۲؛ خالی = ۰؛ فهرست باقی‌مانده `[]`.** هر مقدار دقیقاً یکی از nameهای واقعی فایل school_branches است؛ ۲۸ غیرفعال وارد عضویت یا میانگین نشدند.
- تنها تعریف عضویت: `motive_driven is True and high_school_branch == branch.name`. هیچ overlap کد، group، exam_group، عنوان، alias موضوعی یا استنباط میراثی در انتخاب اعضا استفاده نشد.
|گروه|id واقعی|name واقعی / کلید dict موتور|تعداد عضو قطعی|source_majors_count فعلی فایل|
|---|---|---|---:|---:|
|ریاضی|`branch-2`|`ریاضی فیزیک`|61|62|
|تجربی|`branch-1`|`علوم تجربی`|56|54|
|انسانی|`branch-3`|`علوم انسانی`|59|59|
|فنی و حرفه‌ای|`branch-4`|`فنی و حرفه‌ای`|26|27|

ستون source_majors_count میراثی عمداً تغییر نکرد؛ آن عدد، ورودی این میانگین نیست. شاخه مستقل هنر یا زبان در فایل وجود ندارد. نام فارسی دقیق با نیم‌فاصلهٔ موجود استفاده شد.

## ۲. baseline و candidate دو آبجکت جدا
- **baseline:** چهار پروفایل دقیق `school_branches_v2.json` فعلی؛ بدون دست‌کاری.
- **candidate:** deepcopy همان فهرست؛ فقط strategy_weights و value_weights با میانگین اعضای قطعی جایگزین شد. equality تمام فیلدهای دیگر (شامل micro_motive_codes، مخرج M، metadata/version/id/name/group) assert شد. هیچ فایل JSON یا patch عددی تولید/ذخیره نشد؛ serialization برای checksum فقط در حافظه است.
- وزن هر major عضو برابر است؛ تعداد کد، عنوان، تازگی DH-013 یا تعداد اعضای شاخه وزن اضافه نمی‌دهد. دادهٔ موجود ۱۶۰ historical نیز مصرف شده، اما مجدداً ممیزی علمی نشده است؛ این آزمایش اعتبارسنجی میدانی نیست.
### روش محاسبه و گردکردن دقیق
برای هر خانه q=1..25 و j=1..5، `meanS[q,j] = sum(S_major[q,j])/N_branch`. اگر جمع ردیف به علت گردکردن ورودی دقیقاً ۱ نباشد، meanS بر جمع همان ردیف تقسیم می‌شود؛ نتیجه تا چهار رقم اعشار گرد می‌شود و residual جمع به بزرگ‌ترین mean خام اضافه می‌شود (tie: اندیس اول). ردیف نهایی در Decimal دقیقاً جمع ۱ دارد.
برای هر یک از ۳۰ کلید Q1A..Q15B، `candidateV[key] = round(sum(V_major[key])/N_branch,4)`؛ قطب‌ها مستقل‌اند و pair-normalization انجام نمی‌شود. Decimal از str ورودی، precision=50 و ROUND_HALF_EVEN؛ تبدیل به float فقط برای ورود به موتور.
بیشینه خطای جمع ردیف S ورودی **0.0001** است (حد پیش‌پرواز ۰٫۰۰۱). هر major: S=25×5 و V=30 قطب کامل/متناهی/[۰،۱]. نقص با default یا صفر پر نشد؛ هیچ major اصلاح نشد.
|آبجکت چهار branch، canonical JSON در حافظه|SHA-256|
|---|---|
|baseline|`0215f638f638af68eb715c5385a3ae1030875ca09371ec3780541dba3f1d6173`|
|candidate|`defc03e877275976efe1ecdc5b8d0ed218a3d45ac848ea8a945e50a3ca591bc7`|

## ۳. اجرای موتور و فرمول بدون pool_scale
- همان کلاس بدون تغییر از SHA مبنا compile/exec شد؛ برای جلوگیری از خواندن فایل‌های main، instance با __new__ و deepcopy ورودی pinned ساخته و validator/precompute اصلی اجرا شد. هیچ متد، epsilon، threshold یا فرمولی override نشد.
- مسیر عملیاتی main_v2.py:256–264: میکروها از `docs/data/micro_motives.json`، majors و school_branches از root، trait_map_v3 و value_poles_v2. root/mirror میکروها در مبنا byte-identical هستند. instance major/branch مشترک در API با تست تعامل cache پوشش داده شد؛ سرور یا live فراخوانی نشد.
- `M = min(1, |unique U ∩ active branch pool| / min(30,max(15,|unique U|)))`؛ هیچ pool_scale/mean_pool مصنوعی در مسیر فعلی وجود ندارد. filter مخزن همان تابع فعلی catalog-intersection با fallback است، نه فیلتر motive_driven؛ در این snapshot خروجی‌های آن غیرتهی‌اند.
- Total بدون تغییر `0.60M + 0.20S + 0.20V` و گردکردن API یک‌رقمی است. V با range-normalization و epsilon=0.02؛ S نسبت گزینه انتخاب‌شده به بیشینه هر ردیف. UI مخزن: نتیجه rankable و سپس M≥15 و Total≥30. predicate فقط در حافظه بازتولید شد، نه browser یا endpoint integration.
- raw M **و evidence** برای ۳۴۰×۴ مقایسه یکسان‌اند. چون codes/motive map/limit ثابت‌اند، اختلاف component M صفر است؛ تغییر رتبه از S/V است، نه بازگشت pool bias.

## ۴. مقایسه عددی canonical A/B/C1/C2
همان fixtureهای فاز صفر/۰ب: A ده جرقه ریاضی، B ده فنی، C1 پنج اول از هرکدام، C2 سه از هر چهار شاخه. SJT همه C؛ V در سؤال فرد A و زوج B. ترتیب tupleها **M / S / V / Total** و همه مقادیر درصد/امتیاز ۰..۱۰۰ هستند. Δ اختلاف مقادیر یک‌رقمی API است؛ Total با raw component محاسبه می‌شود، نه جمع componentهای گرد‌شده.
|پروفایل|branch|baseline M/S/V/Total|candidate M/S/V/Total|Δ M/S/V/Total|تغییر رتبه اول پروفایل؟|
|---|---|---|---|---|---|
|A|علوم تجربی|0.0 / 72.2 / 74.1 / 29.3|0.0 / 71.9 / 74.4 / 29.3|+0.0 / -0.3 / +0.3 / +0.0|خیر|
|A|ریاضی فیزیک|66.7 / 59.1 / 71.3 / 66.1|66.7 / 61.0 / 72.4 / 66.7|+0.0 / +1.9 / +1.1 / +0.6|خیر|
|A|علوم انسانی|0.0 / 82.0 / 61.1 / 28.6|0.0 / 82.0 / 64.6 / 29.3|+0.0 / +0.0 / +3.5 / +0.7|خیر|
|A|فنی و حرفه‌ای|0.0 / 61.4 / 69.9 / 26.3|0.0 / 68.2 / 81.1 / 29.9|+0.0 / +6.8 / +11.2 / +3.6|خیر|
|B|علوم تجربی|0.0 / 72.2 / 74.1 / 29.3|0.0 / 71.9 / 74.4 / 29.3|+0.0 / -0.3 / +0.3 / +0.0|خیر|
|B|ریاضی فیزیک|0.0 / 59.1 / 71.3 / 26.1|0.0 / 61.0 / 72.4 / 26.7|+0.0 / +1.9 / +1.1 / +0.6|خیر|
|B|علوم انسانی|0.0 / 82.0 / 61.1 / 28.6|0.0 / 82.0 / 64.6 / 29.3|+0.0 / +0.0 / +3.5 / +0.7|خیر|
|B|فنی و حرفه‌ای|66.7 / 61.4 / 69.9 / 66.3|66.7 / 68.2 / 81.1 / 69.9|+0.0 / +6.8 / +11.2 / +3.6|خیر|
|C1|علوم تجربی|0.0 / 72.2 / 74.1 / 29.3|0.0 / 71.9 / 74.4 / 29.3|+0.0 / -0.3 / +0.3 / +0.0|خیر|
|C1|ریاضی فیزیک|33.3 / 59.1 / 71.3 / 46.1|33.3 / 61.0 / 72.4 / 46.7|+0.0 / +1.9 / +1.1 / +0.6|خیر|
|C1|علوم انسانی|0.0 / 82.0 / 61.1 / 28.6|0.0 / 82.0 / 64.6 / 29.3|+0.0 / +0.0 / +3.5 / +0.7|خیر|
|C1|فنی و حرفه‌ای|33.3 / 61.4 / 69.9 / 46.3|33.3 / 68.2 / 81.1 / 49.9|+0.0 / +6.8 / +11.2 / +3.6|خیر|
|C2|علوم تجربی|20.0 / 72.2 / 74.1 / 41.3|20.0 / 71.9 / 74.4 / 41.3|+0.0 / -0.3 / +0.3 / +0.0|بله|
|C2|ریاضی فیزیک|20.0 / 59.1 / 71.3 / 38.1|20.0 / 61.0 / 72.4 / 38.7|+0.0 / +1.9 / +1.1 / +0.6|بله|
|C2|علوم انسانی|20.0 / 82.0 / 61.1 / 40.6|20.0 / 82.0 / 64.6 / 41.3|+0.0 / +0.0 / +3.5 / +0.7|بله|
|C2|فنی و حرفه‌ای|20.0 / 61.4 / 69.9 / 38.3|20.0 / 68.2 / 81.1 / 41.9|+0.0 / +6.8 / +11.2 / +3.6|بله|

|پروفایل|best baseline|best candidate|کارت‌های visible baseline → candidate|
|---|---|---|---|
|A|ریاضی فیزیک|ریاضی فیزیک|ریاضی فیزیک → ریاضی فیزیک|
|B|فنی و حرفه‌ای|فنی و حرفه‌ای|فنی و حرفه‌ای → فنی و حرفه‌ای|
|C1|فنی و حرفه‌ای|فنی و حرفه‌ای|ریاضی فیزیک، فنی و حرفه‌ای → ریاضی فیزیک، فنی و حرفه‌ای|
|C2|علوم تجربی|فنی و حرفه‌ای|ریاضی فیزیک، علوم انسانی، علوم تجربی، فنی و حرفه‌ای → ریاضی فیزیک، علوم انسانی، علوم تجربی، فنی و حرفه‌ای|

- A ریاضی‌اول و B فنی‌اول باقی است؛ M خالص هر دو ۶۶٫۷. C1 هر دو کارت M=33.3 را حفظ می‌کند. C2 هر چهار M=20 و هر چهار کارت را حفظ می‌کند. حذف/اضافه کارت نسبت به فیلتر ۱۵٪ و predicate کامل UI در این چهار fixture **صفر** است.
- C1: فنی ۴۶٫۳→۴۹٫۹، ریاضی ۴۶٫۱→۴۶٫۷؛ فاصله نمایشی ۰٫۲→۳٫۲. C2: تجربی‌اول→فنی‌اول با فنی ۳۸٫۳→۴۱٫۹. این جابه‌جایی واقعاً دیده شد، اما به تنهایی «غیرقابل‌قبول» یا «تورم مصنوعی» نیست؛ برای تحمیل ریاضی‌اول، وزن/آستانه تغییر نکرد.
## ۵. مجموعه دقیق ۳۴۰ ورودی و diff majorها
۴ fixture + ۲۰۲ مجموعه کد فعال + ۲۸ مجموعه کد غیرفعال + ۱۰۰ پروفایل synthetic با seed=20261023 + ۶ edge case (خالی، no-S، no-V، partial-S، duplicates/case/whitespace، unknown). ورود کدِ غیرفعال به تست، آن major را فعال نمی‌کند. داده/ترتیب این مجموعه دقیقاً با PHASE0b یکسان است:
`f1b76560bec62a96748b09f2e5730786dd48846b0a6a16fa3484275f9048916f`.
|آزمون|نتیجه اجراشده|
|---|---|
|ورودی discover_individuality|340|
|score برگشتی major که مقایسه شد|637|
|بیشینه اختلاف score major|0.0|
|خروجی کلی متفاوت|0|
|فهرست/order، raw_components، evidence، descriptions، traits، status، alternative_paths، method/summary موجود|equality کامل خروجی PASS؛ نه فقط score/order|
|raw M/evidence متفاوت branch|0 در ۱۳۶۰ مقایسه|
|ورودی با تغییر کارت بعد از M≥15|0|
|ورودی با حذف/اضافه کارت در predicate کامل M≥15 و Total≥30|0|
|ورودی با تغییر best_branch|2: C2 و random-69|
- cache گرم: precompute اصلی، ۲۳۰ cache major و ۴ cache branch assert شد. cache سرد: A/B/C1/C2 روی هر دو instance، discover قبل و بعد branch call برابر golden؛ ۱۶ فراخوانی discover و ۸ branch call، همگی PASS. deepcopy ورودی‌ها مانع alias/mutation مشترک شد؛ majors و snapshot داده پس از آزمون equality شدند.
- ۶۳۷ فقط scoreهای واقعاً برگشتی است، نه ۲۰۲×۳۴۰ score ادعایی؛ ورودی بدون match یا با پاسخ ناقص نیز با equality تمام خروجی سنجیده شد. بدون تست میدانی یا fingerprint، این PASSها ادعای live نیستند.
### فراوانی رتبه اول در ۱۰۰ پروفایل synthetic ثابت
|حالت|تجربی|ریاضی|انسانی|فنی|
|---|---:|---:|---:|---:|
|baseline|29|34|29|8|
|candidate|29|35|28|8|

در ۱۰۰تایی، فنی ۸/۱۰۰ در هر دو حالت است؛ فقط random-69 انسانی→ریاضی شد. این نمونه بر اساس انتخاب major است و نماینده جامعه/گروه‌های برابر نیست؛ سهم رتبه اول هدف بهینه‌سازی یا اثبات نبود bias نیست. در canonicalها فنی بیشتر اول شد، اما «انحصار مصنوعی» از این داده احراز نمی‌شود.

## ۶. پوشش M صرفاً برای گزارش؛ نه انتخاب عضویت یا تغییر codes
پس از تصمیم #303 برای ۱۷۲/۲۱۹/۲۲۰، fieldهای membership با جاگذاری کد در فایل میراثی یکسان نیستند. دستور حفظ codes رعایت شد؛ این ناسازگاری از metadata merge وجود داشت و candidate آن را اصلاح نکرده است.
|branch|کدهای اعضای قطعی|pool معتبر فعلی|کد عضو که در pool خودش نیست|majorهای مربوط|
|---|---:|---:|---:|---|
|علوم تجربی|385|371|14|219, 220|
|ریاضی فیزیک|413|420|7|172|
|علوم انسانی|413|413|0|—|
|فنی و حرفه‌ای|182|189|0|—|

- ۱۷۲ عضو قطعی ریاضی است ولی ۷ کد INTARCH هنوز در pool فنی است. ۲۱۹/۲۲۰ عضو تجربی‌اند ولی LAND و AGMECH (۱۴ کد) هنوز در pool ریاضی‌اند. این‌ها کد بی‌پوشش در کل سیستم نیستند؛ **پوشش در شاخهٔ مصوب خودشان** ندارند. از این کدها برای حدس مجدد membership استفاده نشد.
- source_majors_count قدیمی و هفت BIOTM خامِ catalog-absent در تجربی نیز دست‌نخورده‌اند. پاکسازی، انتقال کد یا تغییر metadata در این فاز انجام نشد. PR صرفاً S/V یک معنای membership برای میانگین و معنای قدیمی برای M را همزمان نگه می‌دارد؛ تصمیم درباره هم‌راستاسازی codes نیازمند مجوز جداست.

## ۷. شواهد V و آزمایش تکمیلی پاسخ ناقص
epsilon=0.02 در موتور ثابت ماند؛ informative بودن با round(span,12) همان موتور سنجیده شد. هر چهار fixture کامل، status=complete و V غیرnull دارند؛ complete از ۱۵ پاسخ می‌آید، نه الزام ۱۵ جفت متمایز.
|branch|informative baseline|candidate|از دست رفته، span قبل→بعد|جدید، span قبل→بعد|
|---|---:|---:|---|---|
|علوم تجربی|15|15|—|—|
|ریاضی فیزیک|15|15|—|—|
|علوم انسانی|15|13|Q1: 0.0550→0.0150، Q11: 0.0772→0.0167|—|
|فنی و حرفه‌ای|13|14|Q12: 0.0292→0.0134|Q5: 0.0166→0.1415، Q13: 0.0075→0.0658|

برای آشکار کردن پیامد افت span، **۶ ورودی تکمیلی خارج از ۳۴۰تایی** اجرا شد: کدهای کامل major120 (حسابداری، انسانی) با فقط Q1A/B یا Q11A/B، و major167 (فرش، فنی) با فقط Q12A/B؛ SJT همه C. این تست‌ها رفتار پاسخ ناقصِ پشتیبانی‌شده در موتور را می‌سنجند، نه امکان عبور از فرم واقعی UI. مجموعه ثابت تاریخی تغییر نکرد.
|تست تکمیلی|شاخه|M ثابت|Total baseline|candidate|کارت قبل→بعد|
|---|---|---:|---:|---|---|
|major-120-Q1A|علوم انسانی|46.7|44.4|null / no_discriminative_evidence|علوم انسانی → هیچ کارت|
|major-120-Q1B|علوم انسانی|46.7|64.4|null / no_discriminative_evidence|علوم انسانی → هیچ کارت|
|major-120-Q11A|علوم انسانی|46.7|44.4|null / no_discriminative_evidence|علوم انسانی → هیچ کارت|
|major-120-Q11B|علوم انسانی|46.7|64.4|null / no_discriminative_evidence|علوم انسانی → هیچ کارت|
|major-167-Q12A|فنی و حرفه‌ای|46.7|40.3|null / no_discriminative_evidence|فنی و حرفه‌ای → هیچ کارت|
|major-167-Q12B|فنی و حرفه‌ای|46.7|60.3|null / no_discriminative_evidence|فنی و حرفه‌ای → هیچ کارت|

هر شش مورد baseline یک کارت visible دارد ولی candidate آن را به‌علت V بدون evidence متمایز به incomplete می‌برد. این **عبور به زیر M=15 نیست** (M=46.7 ثابت است)، بلکه حذف پیش از رتبه‌بندی از مسیر V=None است؛ پس با «۰ کارت حذف‌شده در ۳۴۰تایی» تناقض ندارد. discover_individuality در همین ۶ مورد نیز equality کامل قبل/بعد داشت.

## ۸. حکم اجرایی صریح
**No-Go برای PR اجرایی بعدی که همین candidate را فقط به شکل S/V-only بنویسد.** این حکم به معنای شکست ۳۴۰تایی، نقص عضویت قطعی یا اجبار به تغییر برنده C2 نیست. دلایل مشخص:
1. **regression بازتولیدشده در قرارداد پاسخ ناقص V:** شش تست بالا کارت واجد M/Total قبلی را به صفر کارت می‌رسانند؛ candidate میانگین چند جفت را زیر epsilon می‌برد. تا ناظر درباره پذیرش این افت evidence و قرارداد پاسخ ناقص تصمیم نگیرد، جایگزینی مستقیم توصیه نمی‌شود. راه حل، تغییر epsilon/threshold/صفرسازی V یا تیزکردن مصنوعی وزن برای عبور نیست.
2. **دوگانگی عضو S/V و pool M برای ۳ عضو قطعی:** S/V از عضویت ۲۰۲تایی مصوب می‌آید ولی M هنوز سه مورد را در pool قبلی نگه می‌دارد. اصلاح codes در این آزمایش ممنوع بود و انجام نشد؛ PR S/V-only این مسئله را حل نمی‌کند. هر طرح هم‌راستاسازی codes/metadata باید جدا مجوز و acceptance بگیرد، نه اضافه‌شدن پنهانی به PR آینده.
3. **اثر قابل توجه و نیازمند پذیرش مدل:** C1 فاصله فنی/ریاضی را ۰٫۲→۳٫۲ و C2 برنده را عوض می‌کند. در ۱۰۰تایی رشد سهم فنی نداریم؛ بنابراین این مورد را به‌تنهایی تورم مصنوعی یا علت کافی رد نمی‌نامیم. مدل میانگین برابر و ۱۶۰ ورودی میراثی نیز صرفاً به خاطر تازه‌بودن میانگین، اعتبار علمی تازه نمی‌گیرند.
**Go فقط برای review این سند و تعیین تکلیف دو مسئله بالا؛ نه write یا Merge.** هیچ candidate جایگزین، انتقال کد، تغییر مقدار major یا دستهٔ وزن جدید تولید نشده است. اگر ناظر بعداً اجرای همین یا طرح دیگری را مجاز کرد، منبع تازه باید pin و آزمون replay شود. دامنهٔ احتمالی باید صریحاً همان فایل/فیلدهای مصوب باشد؛ rollback نسخهٔ بعدی، restore blob کامل school_branches از SHA مبنای همان PR و reload cache خواهد بود، نه revert majors/engine.
CI موجود deploy پس از #303 سبز نبود: backend/reference-data integrity، postgres/reference-vs-main و runtime-lock/Liara-root شکست داشتند و fingerprint skip بود. این اطلاعات تاریخی با آزمایش محلی حاضر مخلوط نشده؛ CI جدید این Draft و live جدا هستند. گیت‌ها تغییر نکردند و ادعای live نداریم.

## ۹. اثر انگشت ورودی‌های pinned
|مسیر|SHA-256|
|---|---|
|`school_branches_v2.json`|`49821a86476dc9d5bb2d8fee68048be83121aa74bc2bd03715b9c1c73ff88412`|
|`majors_database_v2.json`|`0f416e69e817666ed0b4a37d28b63ec5afa5f448d794aedbe4edf466fa4b01c8`|
|`docs/data/micro_motives.json`|`34f04251e4d6a7b09e18c117c6af9e5670464dd60047fff5407d89a1fa63edde`|
|`micro_motives.json`|`34f04251e4d6a7b09e18c117c6af9e5670464dd60047fff5407d89a1fa63edde`|
|`trait_map_v3.json`|`6d11d19b8ac565f84a6e44a6cc8e91832891a557cce694650852b02bfc6a4bc1`|
|`value_poles_v2.json`|`84390b1d3c00b08f86492e48c8b301d3d3fc61a1f24a5d6727f0f08bbc68c82b`|
|`dark_horse_engine_v2.py`|`8ce3ef7220c008bd910d85069c2627b44eceebbaf596eea7c0f76bb2481c7168`|
|`main_v2.py`|`6d3ebcf4606e5d7831b8298be83b64871bbe36d85f2ae13c2b6caeb7ad995557`|
|`docs/app.js`|`c55843d01e818ff3953f84d4c248c3dbe6cee43e98626bcc86412909acef18b0`|
|`test_engine_psychometrics.py`|`3d1bae31a007f7d86547752d52782cd392349d61663b46847a617e8251500ba9`|

## ۱۰. manifest قطعی برای بازپخش
|name شاخه|id اعضای فعال از high_school_branch|
|---|---|
|علوم تجربی|`1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 99, 152, 153, 156, 169, 219, 220`|
|ریاضی فیزیک|`40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 84, 85, 96, 97, 98, 100, 151, 154, 155, 157, 162, 165, 172, 199, 201, 202, 203, 204`|
|علوم انسانی|`101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 146, 147, 148, 149, 150, 159, 160, 161, 163, 164, 166, 171, 173, 174, 175, 176, 205, 208, 209, 210, 211, 212, 213, 214`|
|فنی و حرفه‌ای|`77, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 158, 167, 168, 170, 177, 178, 180, 181, 182, 183, 184, 185, 186, 187, 189`|

## ۱۱. فهرست کامل نتیجه ۳۴۰ ورودی
این جدول خلاصهٔ هر ورودی است؛ componentهای canonical در بخش ۴ و تمام raw results در حافظهٔ اسکریپت results قابل بازپخش‌اند. ستون Δ بیشینه قدرمطلق تفاوت Total نمایش‌داده‌شده بین شاخه‌های rankable مشترک است؛ عدد ۰ برای ورودی بدون branch رتبه‌پذیر، فقط «هیچ مقایسه Total» است، نه Total جعلی صفر. diff کامل major برای تمام ردیف‌ها ۰ است. هیچ حذف/اضافه کارت M۱۵ یا predicate کامل در این ۳۴۰ ردیف وجود ندارد.
|ورودی|best baseline|best candidate|max abs ΔTotal|
|---|---|---|---:|
|A|ریاضی فیزیک|ریاضی فیزیک|3.6|
|B|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|C1|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|C2|علوم تجربی|فنی و حرفه‌ای|3.6|
|active-1|علوم تجربی|علوم تجربی|3.6|
|active-2|علوم تجربی|علوم تجربی|3.6|
|active-3|علوم تجربی|علوم تجربی|3.6|
|active-4|علوم تجربی|علوم تجربی|3.6|
|active-5|علوم تجربی|علوم تجربی|3.6|
|active-6|علوم تجربی|علوم تجربی|3.6|
|active-7|علوم تجربی|علوم تجربی|3.6|
|active-8|علوم تجربی|علوم تجربی|3.6|
|active-9|علوم تجربی|علوم تجربی|3.6|
|active-10|علوم تجربی|علوم تجربی|3.6|
|active-11|علوم تجربی|علوم تجربی|3.6|
|active-12|علوم تجربی|علوم تجربی|3.6|
|active-13|علوم تجربی|علوم تجربی|3.6|
|active-14|علوم تجربی|علوم تجربی|3.6|
|active-15|علوم تجربی|علوم تجربی|3.6|
|active-16|علوم تجربی|علوم تجربی|3.6|
|active-17|علوم تجربی|علوم تجربی|3.6|
|active-18|علوم تجربی|علوم تجربی|3.6|
|active-19|علوم تجربی|علوم تجربی|3.6|
|active-20|علوم تجربی|علوم تجربی|3.6|
|active-21|علوم تجربی|علوم تجربی|3.6|
|active-22|علوم تجربی|علوم تجربی|3.6|
|active-23|علوم تجربی|علوم تجربی|3.6|
|active-24|علوم تجربی|علوم تجربی|3.6|
|active-25|علوم تجربی|علوم تجربی|3.6|
|active-26|علوم تجربی|علوم تجربی|3.6|
|active-27|علوم تجربی|علوم تجربی|3.6|
|active-28|علوم تجربی|علوم تجربی|3.6|
|active-29|علوم تجربی|علوم تجربی|3.6|
|active-30|علوم تجربی|علوم تجربی|3.6|
|active-31|علوم تجربی|علوم تجربی|3.6|
|active-32|علوم تجربی|علوم تجربی|3.6|
|active-33|علوم تجربی|علوم تجربی|3.6|
|active-34|علوم تجربی|علوم تجربی|3.6|
|active-35|علوم تجربی|علوم تجربی|3.6|
|active-36|علوم تجربی|علوم تجربی|3.6|
|active-37|علوم تجربی|علوم تجربی|3.6|
|active-38|علوم تجربی|علوم تجربی|3.6|
|active-39|علوم تجربی|علوم تجربی|3.6|
|active-40|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-41|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-42|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-43|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-44|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-45|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-46|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-47|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-48|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-49|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-50|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-51|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-52|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-53|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-54|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-55|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-56|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-57|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-58|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-59|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-60|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-61|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-62|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-63|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-64|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-65|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-66|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-67|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-68|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-69|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-70|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-71|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-72|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-73|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-74|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-75|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-76|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-77|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-78|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-79|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-80|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-81|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-82|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-83|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-84|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-85|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-86|علوم تجربی|علوم تجربی|3.6|
|active-87|علوم تجربی|علوم تجربی|3.6|
|active-88|علوم تجربی|علوم تجربی|3.6|
|active-89|علوم تجربی|علوم تجربی|3.6|
|active-90|علوم تجربی|علوم تجربی|3.6|
|active-91|علوم تجربی|علوم تجربی|3.6|
|active-92|علوم تجربی|علوم تجربی|3.6|
|active-93|علوم تجربی|علوم تجربی|3.6|
|active-94|علوم تجربی|علوم تجربی|3.6|
|active-95|علوم تجربی|علوم تجربی|3.6|
|active-96|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-97|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-98|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-99|علوم تجربی|علوم تجربی|3.6|
|active-100|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-101|علوم انسانی|علوم انسانی|3.6|
|active-102|علوم انسانی|علوم انسانی|3.6|
|active-103|علوم انسانی|علوم انسانی|3.6|
|active-104|علوم انسانی|علوم انسانی|3.6|
|active-105|علوم انسانی|علوم انسانی|3.6|
|active-106|علوم انسانی|علوم انسانی|3.6|
|active-107|علوم انسانی|علوم انسانی|3.6|
|active-108|علوم انسانی|علوم انسانی|3.6|
|active-109|علوم انسانی|علوم انسانی|3.6|
|active-110|علوم انسانی|علوم انسانی|3.6|
|active-111|علوم انسانی|علوم انسانی|3.6|
|active-112|علوم انسانی|علوم انسانی|3.6|
|active-113|علوم انسانی|علوم انسانی|3.6|
|active-114|علوم انسانی|علوم انسانی|3.6|
|active-115|علوم انسانی|علوم انسانی|3.6|
|active-116|علوم انسانی|علوم انسانی|3.6|
|active-117|علوم انسانی|علوم انسانی|3.6|
|active-118|علوم انسانی|علوم انسانی|3.6|
|active-119|علوم انسانی|علوم انسانی|3.6|
|active-120|علوم انسانی|علوم انسانی|3.6|
|active-121|علوم انسانی|علوم انسانی|3.6|
|active-122|علوم انسانی|علوم انسانی|3.6|
|active-123|علوم انسانی|علوم انسانی|3.6|
|active-124|علوم انسانی|علوم انسانی|3.6|
|active-125|علوم انسانی|علوم انسانی|3.6|
|active-126|علوم انسانی|علوم انسانی|3.6|
|active-127|علوم انسانی|علوم انسانی|3.6|
|active-128|علوم انسانی|علوم انسانی|3.6|
|active-129|علوم انسانی|علوم انسانی|3.6|
|active-130|علوم انسانی|علوم انسانی|3.6|
|active-131|علوم انسانی|علوم انسانی|3.6|
|active-132|علوم انسانی|علوم انسانی|3.6|
|active-133|علوم انسانی|علوم انسانی|3.6|
|active-134|علوم انسانی|علوم انسانی|3.6|
|active-135|علوم انسانی|علوم انسانی|3.6|
|active-136|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-137|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-138|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-139|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-140|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-141|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-142|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-143|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-144|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-145|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-146|علوم انسانی|علوم انسانی|3.6|
|active-147|علوم انسانی|علوم انسانی|3.6|
|active-148|علوم انسانی|علوم انسانی|3.6|
|active-149|علوم انسانی|علوم انسانی|3.6|
|active-150|علوم انسانی|علوم انسانی|3.6|
|active-151|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-152|علوم تجربی|علوم تجربی|3.6|
|active-153|علوم تجربی|علوم تجربی|3.6|
|active-154|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-155|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-156|علوم تجربی|علوم تجربی|3.6|
|active-157|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-158|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-159|علوم انسانی|علوم انسانی|3.6|
|active-160|علوم انسانی|علوم انسانی|3.6|
|active-161|علوم انسانی|علوم انسانی|3.6|
|active-162|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-163|علوم انسانی|علوم انسانی|3.6|
|active-164|علوم انسانی|علوم انسانی|3.6|
|active-165|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-166|علوم انسانی|علوم انسانی|3.6|
|active-167|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-168|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-169|علوم تجربی|علوم تجربی|3.6|
|active-170|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-171|علوم انسانی|علوم انسانی|3.6|
|active-172|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-173|علوم انسانی|علوم انسانی|3.6|
|active-174|علوم انسانی|علوم انسانی|3.6|
|active-175|علوم انسانی|علوم انسانی|3.6|
|active-176|علوم انسانی|علوم انسانی|3.6|
|active-177|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-178|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-180|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-181|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-182|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-183|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-184|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-185|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-186|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-187|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-189|فنی و حرفه‌ای|فنی و حرفه‌ای|3.6|
|active-199|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-201|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-202|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-203|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-204|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-205|علوم انسانی|علوم انسانی|3.6|
|active-208|علوم انسانی|علوم انسانی|3.6|
|active-209|علوم انسانی|علوم انسانی|3.6|
|active-210|علوم انسانی|علوم انسانی|3.6|
|active-211|علوم انسانی|علوم انسانی|3.6|
|active-212|علوم انسانی|علوم انسانی|3.6|
|active-213|علوم انسانی|علوم انسانی|3.6|
|active-214|علوم انسانی|علوم انسانی|3.6|
|active-219|ریاضی فیزیک|ریاضی فیزیک|3.6|
|active-220|ریاضی فیزیک|ریاضی فیزیک|3.6|
|inactive-179|—|—|3.6|
|inactive-188|—|—|3.6|
|inactive-190|—|—|3.6|
|inactive-191|—|—|3.6|
|inactive-192|—|—|3.6|
|inactive-193|—|—|3.6|
|inactive-194|—|—|3.6|
|inactive-195|—|—|3.6|
|inactive-196|—|—|3.6|
|inactive-197|—|—|3.6|
|inactive-198|—|—|3.6|
|inactive-200|—|—|3.6|
|inactive-206|—|—|3.6|
|inactive-207|—|—|3.6|
|inactive-215|—|—|3.6|
|inactive-216|—|—|3.6|
|inactive-217|—|—|3.6|
|inactive-218|—|—|3.6|
|inactive-221|—|—|3.6|
|inactive-222|—|—|3.6|
|inactive-223|—|—|3.6|
|inactive-224|—|—|3.6|
|inactive-225|—|—|3.6|
|inactive-226|—|—|3.6|
|inactive-227|—|—|3.6|
|inactive-228|—|—|3.6|
|inactive-229|—|—|3.6|
|inactive-230|—|—|3.6|
|random-0|ریاضی فیزیک|ریاضی فیزیک|3.6|
|random-1|ریاضی فیزیک|ریاضی فیزیک|0.4|
|random-2|علوم تجربی|علوم تجربی|0.6|
|random-3|علوم تجربی|علوم تجربی|1.0|
|random-4|علوم انسانی|علوم انسانی|1.7|
|random-5|علوم انسانی|علوم انسانی|2.1|
|random-6|ریاضی فیزیک|ریاضی فیزیک|1.5|
|random-7|ریاضی فیزیک|ریاضی فیزیک|1.0|
|random-8|ریاضی فیزیک|ریاضی فیزیک|4.0|
|random-9|ریاضی فیزیک|ریاضی فیزیک|1.8|
|random-10|علوم تجربی|علوم تجربی|1.7|
|random-11|ریاضی فیزیک|ریاضی فیزیک|2.9|
|random-12|علوم تجربی|علوم تجربی|0.6|
|random-13|علوم تجربی|علوم تجربی|4.1|
|random-14|علوم انسانی|علوم انسانی|2.9|
|random-15|علوم انسانی|علوم انسانی|0.4|
|random-16|علوم تجربی|علوم تجربی|1.0|
|random-17|علوم انسانی|علوم انسانی|0.8|
|random-18|فنی و حرفه‌ای|فنی و حرفه‌ای|0.6|
|random-19|ریاضی فیزیک|ریاضی فیزیک|3.1|
|random-20|علوم تجربی|علوم تجربی|1.3|
|random-21|ریاضی فیزیک|ریاضی فیزیک|0.8|
|random-22|علوم تجربی|علوم تجربی|3.4|
|random-23|علوم تجربی|علوم تجربی|0.7|
|random-24|فنی و حرفه‌ای|فنی و حرفه‌ای|1.7|
|random-25|ریاضی فیزیک|ریاضی فیزیک|1.0|
|random-26|ریاضی فیزیک|ریاضی فیزیک|2.0|
|random-27|علوم تجربی|علوم تجربی|0.4|
|random-28|علوم انسانی|علوم انسانی|0.5|
|random-29|فنی و حرفه‌ای|فنی و حرفه‌ای|0.2|
|random-30|علوم انسانی|علوم انسانی|0.2|
|random-31|ریاضی فیزیک|ریاضی فیزیک|4.7|
|random-32|ریاضی فیزیک|ریاضی فیزیک|0.6|
|random-33|علوم انسانی|علوم انسانی|0.8|
|random-34|ریاضی فیزیک|ریاضی فیزیک|1.4|
|random-35|علوم تجربی|علوم تجربی|1.8|
|random-36|علوم تجربی|علوم تجربی|1.5|
|random-37|علوم تجربی|علوم تجربی|3.4|
|random-38|علوم انسانی|علوم انسانی|0.9|
|random-39|ریاضی فیزیک|ریاضی فیزیک|1.4|
|random-40|علوم تجربی|علوم تجربی|0.9|
|random-41|علوم تجربی|علوم تجربی|1.7|
|random-42|علوم انسانی|علوم انسانی|0.3|
|random-43|علوم انسانی|علوم انسانی|1.8|
|random-44|علوم تجربی|علوم تجربی|1.2|
|random-45|علوم انسانی|علوم انسانی|2.1|
|random-46|ریاضی فیزیک|ریاضی فیزیک|3.0|
|random-47|علوم تجربی|علوم تجربی|1.7|
|random-48|علوم تجربی|علوم تجربی|3.4|
|random-49|علوم انسانی|علوم انسانی|0.7|
|random-50|علوم انسانی|علوم انسانی|1.0|
|random-51|ریاضی فیزیک|ریاضی فیزیک|0.3|
|random-52|ریاضی فیزیک|ریاضی فیزیک|1.7|
|random-53|علوم تجربی|علوم تجربی|1.2|
|random-54|علوم انسانی|علوم انسانی|0.9|
|random-55|علوم انسانی|علوم انسانی|1.0|
|random-56|علوم تجربی|علوم تجربی|0.3|
|random-57|فنی و حرفه‌ای|فنی و حرفه‌ای|1.1|
|random-58|ریاضی فیزیک|ریاضی فیزیک|0.5|
|random-59|ریاضی فیزیک|ریاضی فیزیک|0.9|
|random-60|علوم انسانی|علوم انسانی|0.5|
|random-61|ریاضی فیزیک|ریاضی فیزیک|0.6|
|random-62|ریاضی فیزیک|ریاضی فیزیک|2.0|
|random-63|ریاضی فیزیک|ریاضی فیزیک|0.2|
|random-64|علوم انسانی|علوم انسانی|2.2|
|random-65|علوم انسانی|علوم انسانی|3.0|
|random-66|ریاضی فیزیک|ریاضی فیزیک|2.1|
|random-67|علوم انسانی|علوم انسانی|0.8|
|random-68|علوم تجربی|علوم تجربی|1.2|
|random-69|علوم انسانی|ریاضی فیزیک|1.7|
|random-70|علوم انسانی|علوم انسانی|1.0|
|random-71|فنی و حرفه‌ای|فنی و حرفه‌ای|2.2|
|random-72|ریاضی فیزیک|ریاضی فیزیک|3.5|
|random-73|فنی و حرفه‌ای|فنی و حرفه‌ای|1.9|
|random-74|علوم انسانی|علوم انسانی|2.9|
|random-75|فنی و حرفه‌ای|فنی و حرفه‌ای|3.2|
|random-76|ریاضی فیزیک|ریاضی فیزیک|0.6|
|random-77|علوم تجربی|علوم تجربی|1.9|
|random-78|ریاضی فیزیک|ریاضی فیزیک|3.6|
|random-79|ریاضی فیزیک|ریاضی فیزیک|1.5|
|random-80|علوم تجربی|علوم تجربی|0.7|
|random-81|علوم انسانی|علوم انسانی|0.2|
|random-82|ریاضی فیزیک|ریاضی فیزیک|0.5|
|random-83|علوم تجربی|علوم تجربی|1.1|
|random-84|علوم تجربی|علوم تجربی|0.5|
|random-85|علوم انسانی|علوم انسانی|2.7|
|random-86|ریاضی فیزیک|ریاضی فیزیک|1.7|
|random-87|علوم انسانی|علوم انسانی|2.1|
|random-88|علوم تجربی|علوم تجربی|3.0|
|random-89|ریاضی فیزیک|ریاضی فیزیک|2.1|
|random-90|علوم انسانی|علوم انسانی|2.2|
|random-91|ریاضی فیزیک|ریاضی فیزیک|1.2|
|random-92|علوم تجربی|علوم تجربی|1.3|
|random-93|علوم تجربی|علوم تجربی|0.3|
|random-94|ریاضی فیزیک|ریاضی فیزیک|0.2|
|random-95|علوم انسانی|علوم انسانی|3.1|
|random-96|ریاضی فیزیک|ریاضی فیزیک|3.1|
|random-97|علوم تجربی|علوم تجربی|0.4|
|random-98|فنی و حرفه‌ای|فنی و حرفه‌ای|4.3|
|random-99|علوم انسانی|علوم انسانی|0.4|
|empty|—|—|0.0|
|no-S|—|—|0.0|
|no-V|—|—|0.0|
|partial-S|ریاضی فیزیک|ریاضی فیزیک|2.3|
|duplicates|—|—|3.6|
|unknown|ریاضی فیزیک|ریاضی فیزیک|3.6|

## ۱۲. اسکریپت دقیق بازتولید — بدون write داده
Python 3.11، فقط stdlib؛ اجرا از ریشه مخزن دارای commit مبنا. کد فقط git show/خواندن فایل برای guard و stdout دارد؛ هیچ نوشتن school_branches/majors، فایل candidate، یا export وزن روی دیسک ندارد. برای آزمایش از فایل موقت خارج repository استفاده شد. guardهای آخر ثابت می‌کنند ورودی pinned، majors هر instance و تمام مسیرهای runtime محلی (از جمله غیبت مسیر روی main) تغییر نکردند. اسکریپت به JSON تولیدشده یا فایل موقت مراحل قبلی وابسته نیست.
```python
# Pinned read-only inputs; candidate branch weights exist only in memory.
import copy, hashlib, json, math, random, subprocess
from collections import Counter
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from pathlib import Path
BASE = 'dd76083836c80732caf33c38b3d59b837f88c284'
PATHS = ['school_branches_v2.json','majors_database_v2.json',
         'docs/data/micro_motives.json','micro_motives.json',
         'trait_map_v3.json','value_poles_v2.json','dark_horse_engine_v2.py',
         'main_v2.py','docs/app.js','test_engine_psychometrics.py']
def local_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None
local_before = {p:local_hash(p) for p in PATHS}
raw = {p:subprocess.check_output(['git','show',BASE+':'+p]) for p in PATHS}
data = {p:json.loads(v) for p,v in raw.items() if p.endswith('.json')}
def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()
input_digest = digest(data)
assert raw['micro_motives.json'] == raw['docs/data/micro_motives.json']
ns = {'__name__':'phase0c_pinned_engine','__file__':'pinned_engine.py'}
exec(compile(raw['dark_horse_engine_v2.py'],ns['__file__'],'exec'),ns)
Engine = ns['DarkHorseEngineV2']
branches = data['school_branches_v2.json']
majors = data['majors_database_v2.json']
active = [m for m in majors if m['motive_driven'] is True]
inactive = [m for m in majors if m['motive_driven'] is False]
names = [b['name'] for b in branches]
assert len(active)==202 and len(inactive)==28
assert all(m.get('high_school_branch') in names for m in active)
# Membership uses this field ONLY: no codes, overlap, group or exam_group.
members = {name:[m for m in active if m['high_school_branch']==name] for name in names}
assert [len(members[n]) for n in names] == [56,61,59,26]
assert sum(map(len,members.values()))==202
max_input_sum_error = Decimal(0)
for m in active:
    sw,vw = m['strategy_weights'],m['value_weights']
    assert len(sw)==25 and all(len(r)==5 for r in sw)
    assert set(vw)=={f'Q{i}{s}' for i in range(1,16) for s in 'AB'}
    for r in sw:
        assert all(math.isfinite(v) and 0<=v<=1 for v in r)
        error = abs(sum(Decimal(str(v)) for v in r)-1)
        max_input_sum_error=max(max_input_sum_error,error)
        assert error<=Decimal('0.001')
    assert all(math.isfinite(v) and 0<=v<=1 for v in vw.values())

candidate = copy.deepcopy(branches)
with localcontext() as ctx:
    ctx.prec=50
    quantum=Decimal('0.0001')
    for b in candidate:
        ms=members[b['name']];n=Decimal(len(ms));assert n>0
        rows=[]
        for q in range(25):
            mean=[sum(Decimal(str(m['strategy_weights'][q][j])) for m in ms)/n for j in range(5)]
            total=sum(mean);assert total>0
            row=[(v/total).quantize(quantum,rounding=ROUND_HALF_EVEN) for v in mean]
            row[max(range(5),key=lambda j:mean[j])] += Decimal(1)-sum(row)
            assert sum(row)==1 and all(0<=v<=1 for v in row)
            rows.append([float(v) for v in row])
        b['strategy_weights']=rows
        b['value_weights']={k:float((sum(Decimal(str(m['value_weights'][k])) for m in ms)/n).quantize(quantum,rounding=ROUND_HALF_EVEN)) for k in b['value_weights']}
for a,b in zip(branches,candidate):
    assert {k:v for k,v in a.items() if k not in ('strategy_weights','value_weights')} == {k:v for k,v in b.items() if k not in ('strategy_weights','value_weights')}

def make_engine(bs):
    e=Engine.__new__(Engine)  # inject pinned data; never load working-tree defaults
    e.motives_map={m['code']:m['description_fa'] for m in copy.deepcopy(data['docs/data/micro_motives.json'])}
    e.majors_db={m['id']:m for m in copy.deepcopy(majors)}
    e.trait_map={q:{int(k):v for k,v in opts.items()} for q,opts in copy.deepcopy(data['trait_map_v3.json']).items()}
    e.value_poles=copy.deepcopy(data['value_poles_v2.json'])
    e.school_branches={b['name']:copy.deepcopy(b) for b in bs}
    e._alt_paths_cache={};e._branch_alt_paths_cache={}
    e._validate_schema_consistency();e._precompute_alternative_paths()
    assert len(e._alt_paths_cache)==230 and len(e._branch_alt_paths_cache)==4
    return e
engines={'baseline':make_engine(branches),'candidate':make_engine(candidate)}
a=['AERO-001','AERO-002','AERO-003','AERO-005','AERO-006','AERO-007','AERO-008','AGM-001','AGM-002','AGM-003']
b=['ARCHA-001','ARCHA-002','ARCHA-003','ARCHA-004','ARCHA-005','ARCHA-006','ARCHA-007','FAS-001','FAS-002','FAS-003']
profiles={'A':a,'B':b,'C1':a[:5]+b[:5],'C2':['ANB-001','ANB-002','ANB-003','AERO-001','AERO-002','AERO-003','ACC-001','ACC-002','ACC-003','ARCHA-001','ARCHA-002','ARCHA-003']}
sjt={f'sjt_{i}':'C' for i in range(1,26)}
conj={f'conj_{i}':f'Q{i}'+('A' if i%2 else 'B') for i in range(1,16)}
cases=[(p,codes,sjt,conj) for p,codes in profiles.items()]
cases += [(f'active-{m["id"]}',m['micro_motive_codes'],sjt,conj) for m in active]
cases += [(f'inactive-{m["id"]}',m['micro_motive_codes'],sjt,conj) for m in inactive]
rng=random.Random(20261023)
for i in range(100):
    chosen=rng.sample(active,k=4)
    codes=[c for m in chosen for c in m['micro_motive_codes'][:4]]
    ss={f'sjt_{j}':rng.choice('ABCDE') for j in range(1,26)}
    vv={f'conj_{j}':f'Q{j}'+rng.choice('AB') for j in range(1,16)}
    cases.append((f'random-{i}',codes,ss,vv))
cases += [('empty',[],{},{}),('no-S',a,{},conj),('no-V',a,sjt,{}),
          ('partial-S',a,{'sjt_1':'C'},conj),('duplicates',[a[0],a[0].lower(),' '+a[0]+' '],sjt,conj),('unknown',a+['NOT-A-CODE'],sjt,conj)]
assert len(cases)==340
assert digest(cases)=='f1b76560bec62a96748b09f2e5730786dd48846b0a6a16fa3484275f9048916f'

def ranked(r):return {v['branch_name']:v for v in r['recommended_branches']}
def m_eligible(r):return {n for n,v in ranked(r).items() if v['avg_components']['m_score']>=15}
def visible(r):return {n for n,v in ranked(r).items() if v['avg_components']['m_score']>=15 and v['average_score']>=30}
results={};major_gold={};branch_cases=[];score_comparisons=0;max_score_delta=0.0
full_diffs=0;m_diffs=0
for label,codes,ss,vv in cases:
    out={k:e.recommend_school_branch(codes,ss,vv) for k,e in engines.items()}
    results[label]=out
    for n in names:
        x=engines['baseline']._compute_branch_m_score(codes,engines['baseline'].school_branches[n])
        y=engines['candidate']._compute_branch_m_score(codes,engines['candidate'].school_branches[n])
        assert x==y,(label,n,'M mismatch')
    base=engines['baseline'].discover_individuality(codes,ss,vv)
    actual=engines['candidate'].discover_individuality(codes,ss,vv)
    assert actual==base,(label,'whole discover output mismatch')
    aa={m['major_id']:m['individuality_fit']['score'] for m in base['discovered_majors']}
    bb={m['major_id']:m['individuality_fit']['score'] for m in actual['discovered_majors']}
    assert aa==bb
    score_comparisons += len(aa)
    max_score_delta=max([max_score_delta]+[abs(bb[k]-v) for k,v in aa.items()])
    if label in profiles:major_gold[label]=base
    old,new=out['baseline'],out['candidate'];oldr,newr=ranked(old),ranked(new)
    branch_cases.append(dict(label=label,best_before=old['best_branch'],best_after=new['best_branch'],
        m_removed=sorted(m_eligible(old)-m_eligible(new)),m_added=sorted(m_eligible(new)-m_eligible(old)),
        ui_removed=sorted(visible(old)-visible(new)),ui_added=sorted(visible(new)-visible(old)),
        incomplete_before=len(old['incomplete_assessments']),incomplete_after=len(new['incomplete_assessments']),
        max_total_delta=max([0]+[abs(newr[n]['average_score']-v['average_score']) for n,v in oldr.items() if n in newr])))
# Check shared-instance interaction and cold caches without changing any methods.
for key,e in engines.items():
    for label,codes in profiles.items():
        e._alt_paths_cache={};e._branch_alt_paths_cache={}
        assert e.discover_individuality(codes,sjt,conj)==major_gold[label]
        assert e.recommend_school_branch(codes,sjt,conj)==results[label][key]
        assert e.discover_individuality(codes,sjt,conj)==major_gold[label]

pair_info={}
for n in names:
    old=engines['baseline'].school_branches[n]['value_weights'];new=engines['candidate'].school_branches[n]['value_weights']
    spans=lambda v:{f'Q{i}':round(abs(v[f'Q{i}A']-v[f'Q{i}B']),12) for i in range(1,16)}
    os,cs=spans(old),spans(new)
    pair_info[n]=dict(before=sum(v>=.02 for v in os.values()),after=sum(v>=.02 for v in cs.values()),
        lost={k:[os[k],cs[k]] for k in os if os[k]>=.02>cs[k]},gained={k:[os[k],cs[k]] for k in os if os[k]<.02<=cs[k]})
# Supplementary partial-V diagnostics, kept OUTSIDE the historical 340 set.
partial_V=[]
for mid,q in [(120,1),(120,11),(167,12)]:
    major=next(m for m in active if m['id']==mid)
    for side in 'AB':
        vv={f'conj_{q}':f'Q{q}{side}'}
        rr={k:e.recommend_school_branch(major['micro_motive_codes'],sjt,vv) for k,e in engines.items()}
        assert engines['baseline'].discover_individuality(major['micro_motive_codes'],sjt,vv)==engines['candidate'].discover_individuality(major['micro_motive_codes'],sjt,vv)
        n=major['high_school_branch']
        mr=engines['baseline']._compute_branch_m_score(major['micro_motive_codes'],engines['baseline'].school_branches[n])[0]
        assert mr==engines['candidate']._compute_branch_m_score(major['micro_motive_codes'],engines['candidate'].school_branches[n])[0]
        partial_V.append(dict(label=f'major-{mid}-Q{q}{side}',branch=n,M=round(100*mr,1),
            before_visible=sorted(visible(rr['baseline'])),after_visible=sorted(visible(rr['candidate'])),
            baseline_total=ranked(rr['baseline']).get(n,{}).get('average_score'),
            candidate_total=ranked(rr['candidate']).get(n,{}).get('average_score'),
            incomplete_after=rr['candidate']['incomplete_assessments']))

# Report coverage only; this never determines membership or changes codes.
coverage={}
for n in names:
    codes={str(c).strip().lower() for m in members[n] for c in m['micro_motive_codes']}
    pool=engines['baseline']._active_branch_code_set(engines['baseline'].school_branches[n]['micro_motive_codes'])
    coverage[n]=dict(member_codes=len(codes),pool_codes=len(pool),missing_from_pool=sorted(codes-pool),
        member_ids_not_fully_covered=[m['id'] for m in members[n] if not {str(c).strip().lower() for c in m['micro_motive_codes']}<=pool])
assert digest(data)==input_digest
for e in engines.values():assert list(e.majors_db.values())==majors
assert local_before=={p:local_hash(p) for p in PATHS}
summary=dict(base=BASE,member_counts={n:len(members[n]) for n in names},remaining=[],
    input_hashes={p:hashlib.sha256(v).hexdigest() for p,v in raw.items()},
    baseline_object_sha256=digest(branches),candidate_object_sha256=digest(candidate),case_set_sha256=digest(cases),
    max_input_S_sum_error=str(max_input_sum_error),cases=len(cases),score_comparisons=score_comparisons,
    major_max_delta=max_score_delta,major_full_result_differences=full_diffs,m_differences=m_diffs,
    first_place_changes=sum(v['best_before']!=v['best_after'] for v in branch_cases),
    ui_changed_cases=sum(bool(v['ui_removed'] or v['ui_added']) for v in branch_cases),
    m15_changed_cases=sum(bool(v['m_removed'] or v['m_added']) for v in branch_cases),
    pair_info=pair_info,coverage=coverage,partial_V=partial_V)
if __name__=='__main__':
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    for p in profiles:
        for key,r in results[p].items():
            print(p,key,r['best_branch'],sorted(visible(r)))
            for row in r['recommended_branches']:print(row['branch_name'],row['avg_components'],row['average_score'])
    print('CHANGED CASES')
    for r in branch_cases:
        if r['best_before']!=r['best_after'] or r['ui_removed'] or r['ui_added']:print(r)
```
