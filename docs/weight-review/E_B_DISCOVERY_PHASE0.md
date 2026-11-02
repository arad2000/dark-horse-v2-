# فاز صفر کشف e_b / نمایش جرقه — فقط گزارش

**SHA مبنا:** `8d239a11c09cb3e178fe777fca2b5ebca3650e67`، شاخهٔ `deploy/liara-commercial-sandbox`، شامل Merge #343. ممیزی snapshot کد است، نه تأیید کد بارگذاری‌شده در Liara، سایت main یا cache مرورگر. هیچ کد، فرمول، داده، UI، تست یا گیتی تغییر نکرده است.

## جمع‌بندی: S1، با تفکیک روشن نام از نقش

**ضریب اجرایی به نام e_b/eb یا boost/bias/rarity/exposure که به M یا Total شاخه/رشته اضافه یا در آن ضرب شود، در کد جاریِ بررسی‌شده یافت نشد.** اشاره‌های e_b/Dirichlet در docs صرفاً «خارج از دامنه» هستند. اما تبدیل شمارش و ترتیب/خلاصه‌سازیِ صرفاً نمایشی وجود دارد؛ بنابراین برای دامنهٔ وسیع «یا نقش مشابه در UI»، سناریو **S1** انتخاب می‌شود، نه ادعای وجود یک متغیر محصولی به نام e_b و نه S2.

برای **payload ثابت**، عامل نمایشی کشف‌شده نمرهٔ عددی API را تغییر نمی‌دهد. ترتیب و دامنهٔ کارت‌های سفر ممکن است انتخاب‌های بعدی انسان را عوض کند؛ آن اثر رفتاری اندازه‌گیری نشده و با «ضریب مستقیم نمره» یکی نیست.

## جدول یافته‌ها — خطوط همگی در SHA مبنا

| شناسه/نام در کد | فایل:خط | ورودی‌ها | خروجی | ضرب/جمع در نمرهٔ شاخه/رشته؟ | فقط ترتیب/استایل UI؟ | تست خودکار موجود؟ |
|---|---|---|---|---|---|---|
| e_b / eb / branch_boost / spark_bias / motive_boost / exposure / rarity | جست‌وجوی کد، تست و JSON؛ اشارهٔ docs مثل `docs/weight-review/BRANCH_M_WAVE_B_CONTRACT.md:49` | — | هیچ نماد/عامل اجرایی منطبق یافت نشد | **یافت نشد** | نماد مستقلی یافت نشد | تست اختصاصی e_b یافت نشد؛ نبود آن ادعای اعتبار علمی نیست |
| `_compute_branch_m_score` و Total | `dark_horse_engine_v2.py:312–333,1046–1078,1096–1101`؛ رشته `:892–919,989` | کدهای معتبر یکتا، S/V | `k/N`؛ درصد گردِ Total و sort؛ گیت M برای best | فقط فرمول‌های شناخته‌شدهٔ M/S/V/Total؛ عامل اضافه یافت نشد | خیر؛ کنترل موتور، نه e_b | `test_engine_psychometrics.py`، `test_v_range_norm.py`، AST/مرزهای قبلی |
| `m_score_denom_limit` و getter خصوصی | `dark_horse_engine_v2.py:185–199,260–263`؛ `school_branches_v2.json` | metadata تاریخی ۳۰ | اعتبارسنجی/خواندن مرجع؛ نه مخرج محاسبات M | خیر؛ مسیر M از `len(user_set)` استفاده می‌کند؛ کلید گمراه‌کنندهٔ method پس از #343 حذف است | خیر؛ دادهٔ مرجع تاریخی | تست startup رد مقدار۲۹ و fingerprint؛ بدون تغییر |
| `discover_v2` / `branch_discovery_v2` | `main_v2.py:557–582,640–670` | درخواست → خروجی موتور | `fit_score=score/average_score`، عبور components/evidence، sort | **هیچ boost اضافه‌ای یافت نشد**؛ فیلتر rankable موجود است | خیر؛ adapter، نه بازوزن‌دهی | `test_main_api_contract.py` و `test_v_consumer_contract.py` |
| `orderedPrefixes` / `loadSwipeCards` | `docs/app.js:759–800`؛ نگاشت `docs/data.js:320` به بعد | مسیرهای باریک انتخاب‌شده، majorCodes، کاتالوگ، likedCodesSet | فیلتر prefix، حذف قبلاً‌لایک‌شده، ترتیب انتخاب مسیر و سپس code عددی | خیر؛ پیش از درخواست و گردآوری انتخاب است | بله، ارائهٔ گزینه‌ها؛ نه تصادفی در این مسیر | تست نگاشت `test_phase3_city_paths.py` هست؛ تست اختصاصی ترتیب در جست‌وجو یافت نشد |
| `likeCard` → `buildPayload` | `docs/app.js:955–966,1197–1201` | انتخاب کاربر، سقف UI=۸۰ | ارسال همان likedCodes در micro_motives | ورودی معمول M را می‌سازد؛ ضریب تازه نیست | صرفاً استایل نیست؛ جمع‌آوری ورودی است، نه boost نمره | تست‌های موتور برای ورودی؛ تست اختصاصی ترتیب/اثر رفتاری یافت نشد |
| `fromPct` / `motiveMatched` / `motiveDenom` | **`docs/app.js:1435–1454`**؛ تابع مشترک رشته/شاخه | M درصدی و طول micro_motives_matched | `max(evidence.length, round(7*M_pct/100))` سپس clamp به ۰..۷؛ متن «جرقه‌های این رشته: x از 7» | **خیر؛ score جدا از r.fit_score خوانده می‌شود** | **بله، شمارش/برچسب نمایشی؛ برای شاخه هم اجرا می‌شود** | render به‌طور غیرمستقیم در `tests/test_v_null_consumer.js`؛ assert اختصاصی این تبدیل یافت نشد؛ probe محلی زیر اجرا شد |
| `microMatch.slice(0,3)` و highlights | `docs/app.js:1456–1459`؛ موتور `:1081–1085,325–332` | لیست شواهد/هایلایت‌ها | سه متن اول؛ شاهد M در ترتیب ورودی کاربر | خیر؛ افزایش امتیاز یا وزن rarity نیست | بله، محدودکردن متن؛ «اول» لزوماً «بیشترین وزن» نیست | تست render/null موجود، نه تست اختصاصی اهمیت سه متن |
| `sampleDiverse` / `TARGET_CARDS=6` | `docs/spark_game.js:12,145–180,321–327` | کاتالوگ گروه‌بندی‌شده برحسب prefix | shuffle prefix؛ تا حد امکان یک کارت از هر prefix، سپس تکمیل نمونه | خیر؛ score سفر محاسبه نمی‌کند | بله، نمونهٔ آزمایشگاه مستقل؛ ادعای برابری مواجههٔ چهار شاخه نیست | تست اختصاصی این نمونه‌گیری در مخزن یافت نشد |
| `aggregateHits` / pathScore/subScore/realmScore | `docs/spark_game.js:193–221,281–292,322–365` | liked محلی آزمایشگاه و تمام hitهای نگاشت prefix→مسیر/محله | برای هر hit، +۱؛ sort تعداد و top مسیر۵/گذر۳/محله۳ | **نه در score API**؛ این اعداد فقط رتبهٔ محلی آزمایشگاه‌اند، نه rank شاخه | بله؛ شمارش hit نگاشت، نه الزاماً کد یکتای هر دسته | تست اختصاصی یافت نشد؛ فقط خواندن کد، بدون ادعای پوشش کامل |
| `displayResults` filter/sort و patch ظاهری | `docs/app.js:1346–1357`؛ `docs/ux_v2_patch.js:137–202`؛ `docs/genz_results_enhance.js:7–29` | fit_score، M درصدی و DOM | فیلتر۳۰/۱۵ و sort همان score؛ افزودن «همخوانی»، توضیح و CSS | خیر؛ فیلتر موجود است، نه جمع/ضرب boost | بله؛ فیلتر بر کارت‌های قابل‌نمایش اثر دارد، نه عدد API | تست مرز/null Node و `test_genz_results_layer.py`؛ تست جامع مرورگر نیست |
| `_hybrid_profile_distance` / alternative_paths | `dark_horse_engine_v2.py:586–596,672–708,1088–1090` | وزن‌های مرجع S/Vِ دو پروفایل؛ **نه k/N کاربر** | `sqrt(.60*RMS(V)^2+.40*RMS(S)^2)` و sort فاصلهٔ مسیر جایگزین | نه در M/Total/رتبهٔ recommended_branches؛ خروجی distance جداست | صرفاً استایل نیست: محاسبهٔ واقعیِ پیشنهاد جایگزین، **خارج از S2 نمرهٔ اصلی** | `test_alternative_cache_equivalence.py` و تست‌های فاصلهٔ موتور |
| persistence / shadow | `operational_store.py:185–193`؛ `api_shadow_bridge.py:31–49` | امتیاز و ترتیب آمادهٔ API | ذخیرهٔ همان اعداد/rank؛ shadow کپی پاسخ را برمی‌گرداند | boost یافت نشد؛ رتبهٔ ذخیره از enumerate است، نه امتیاز جدید | خیر؛ ذخیره‌سازی، نه عامل نمایش | `test_operational_store.py` و `test_api_shadow_bridge.py`؛ در این فاز اجرا نشدند |

## دو مرز مهم خواندن کد

- مسیر عدد اصلی: `buildPayload` → API `branch-discovery` → `_compute_branch_m_score` → `Total=.60M+.20V+.20S` → درصد گرد → API fit_score → UI. در مسیر رشته ضرایب شناخته‌شدهٔ `.55M+.30V+.15S` است؛ هیچ ضریب کنار این‌ها یافت نشد. S2 احراز نشد؛ ادعای دوباره‌شماری k/N در موتور نداریم.
- آزمایشگاه متغیر **state محلی** در `startSession` دارد و در کلید `dh_spark_lab_v1` می‌نویسد، نه `darkhorse_session_v2` سفر (`spark_game.js:9–30,288–292,322–327` و `app.js:222–226`). fetch آن فقط کاتالوگ است (`:65–80`)، نه API نمره. عددهای pathScore نام مشابه score دارند ولی هیچ call به discover/branch یا افزودن به likedCodes سفر در این فایل یافت نشد.
- `index.html:38–40,49,58` واقعاً app، patch، آزمایشگاه و لایهٔ ظاهری را بارگذاری می‌کند. patch پس از render فقط DOM را تزیین/توضیح می‌دهد؛ شمارش ۷تایی را اصلاح نمی‌کند. `ux_v2_patch.js:29–32` صریحاً می‌گوید «Do not shuffle, reseed, or otherwise reorder»؛ این نقل‌قول به‌تنهایی اثبات نیست، بدنهٔ patch هم خوانده شد.

## probe نمایشی، بدون تغییر یا دادهٔ واقعی کاربر

تابع واقعی `displayResults` در VM/DOM-stub از همین snapshot اجرا شد. payload ساختگی M=50، S=80، V=90 و fit_score=64 با Total شناخته‌شده سازگار است؛ وزن جدید ساخته نشد. با ۲۰ شاهد در evidence، متن **۷ از ۷** شد؛ با evidence خالی، fallback متن **۴ از ۷** ساخت. در هر دو حالت **۶۴٪** باقی ماند و `JSON.stringify(payload)` قبل/بعد عیناً برابر بود. این نمونهٔ رفتار نمایش است، نه شیوع کاربران، نه اجرای مرورگر/patchهای کامل و نه آزمون API زنده.

برای شاخه، نمایش «از۷/کامل» را نباید با k/N یا تعداد شاهد واقعی یکی دانست؛ همین تفاوت، یافتهٔ UI است، نه ضریب e_b در نمره. در این فاز هیچ اصلاحی انجام نشد و هیچ فرمول e_b پیشنهاد نمی‌شود.

## دامنه، جست‌وجو و کنترل

جست‌وجوی نام‌ها/الگوها در کد و تست و docs/weight-review و JSON، همراه خواندن مسیر عدد، UI، نگاشت و callerهای `discover_individuality`/`recommend_school_branch` انجام شد. `pool_scale` در متن گزارش‌های تاریخی و generator اسناد یافت می‌شود؛ در محاسبهٔ جاری M شاخه فعال نیست. نتیجهٔ منفی به همین SHA و مسیرهای ممیزی‌شده محدود است؛ کد خارجی/نسخهٔ live یا هر سوگیری تجربیِ ناشی از رفتار کاربران را نفی نمی‌کند.

```sh
git grep -n -I -i -E '\be_b\b|\beb\b|branch_boost|spark_bias|motive_boost|exposure|rarity|display_order' 8d239a11c09cb3e178fe777fca2b5ebca3650e67 -- '*.py' '*.js' '*.md' '*.json'
git grep -n -I -E 'pool_scale|branch_score|m_branch|k_b|fromPct|motiveMatched|sampleDiverse|aggregateHits|recommend_school_branch\(|discover_individuality\(' 8d239a11c09cb3e178fe777fca2b5ebca3650e67 -- '*.py' '*.js'
```

تست‌های موجودِ فقط‌خواندنی اجراشده: `python -m unittest test_genz_results_layer test_genz_visual_layer test_engine_psychometrics test_alternative_cache_equivalence -q` → **۲۹ PASS**. probe VM بیرون مخزن بود و هیچ تست/کد اجرایی به PR اضافه نشد. برای ردیف‌های «تست موجود» الزاماً اجرای همهٔ آن‌ها ادعا نشده است. هیچ تست اختصاصی تازه برای e_b ساخته نشد؛ گیت تاریخی CI بدون تغییر است. این PR تنها همین یک Markdown را اضافه می‌کند؛ نتیجهٔ چک‌های طبیعی PR در خود PR ثبت می‌شود، نه ادعای all-green یا سلامت runtime.

**توصیهٔ یک‌خطی برای ناظر: «موج UI جدا» — صرفاً برای تصمیم دربارهٔ شمارش/برچسب جرقهٔ شاخه؛ این گزارش نه پیشنهاد پیاده‌سازی e_b است و نه مجوز تغییر فرمول یا ترتیب.** Draft؛ بدون Merge تا دستور ناظر.
