# فاز صفر — ممیزی ترتیب محله‌ها و گزینه‌های پاسخ

**وضعیت: ممیزی و سند تکمیل شد؛ هیچ shuffle پیاده‌سازی نشده است.**

مرجع فرانت: `main` در `6a57882ec25a2ea850e54c3df4c33d4c13f2a904`؛ موتور و قرارداد API از `deploy/liara-commercial-sandbox` در `dd0947492a27dd88fb3fb496c7cf2223d43a5a50` خوانده شد، نه Python قدیمی main. نتیجه دربارهٔ source است؛ نصب همین بایت‌ها روی Live یا رفتار نسخهٔ آینده ادعا نمی‌شود.

## حکم کوتاه

| مورد | منبع ترتیب فعلی | کلید پایدار انتخاب | GO shuffle نمایش؟ |
|---|---|---|---|
| محله‌ها | آرایهٔ ثابت `REALMS` در `docs/data.js:2`؛ `renderRealm` آن را مستقیم پیمایش می‌کند | `r.id` مانند `healer`؛ نه index کارت | **بله**؛ فقط کپی آرایهٔ نمایش، بدون تغییر ترتیب انتخاب کاربر |
| گزینه‌های راهبرد S | آرایهٔ `options` هر سؤال در JSON؛ پیمایش مستقیم در `renderStrategy` | فیلد اصلی `o.index` برابر ۰..۴، معادل کد A..E؛ نه index جدید نمایش | **بله، مشروط به حفظ index اصلی هر گزینه**؛ بازشماری بعد از shuffle **NO-GO** |
| گزینه‌های ارزش V | دو عضو `q.options`، نمایش فعلی در جایگاه‌های ۰ و ۱ در `renderValue` | `o.code` مانند `Q1A` و `Q1B` | **بله، مشروط به جابه‌جایی کل شیء گزینه همراه text/code/title** |

**حکم کلی گزینه‌ها: GO برای ترتیب نمایشی، نه جابه‌جایی نگاشت پاسخ به معنا/وزن.** وجود فیلد با نام index در S به معنی اتصال به جایگاه DOM نیست؛ در کد فعلی همین فیلد شناسهٔ معنایی و قرارداد وزن است. shuffle متن به‌تنهایی یا ساخت index جدید از محل نمایش امن نیست.

## الف) محله‌ها: مسیر، ترتیب و انتخاب

- ورود و ناوبری مرحله‌ها در `docs/app.js`، stage=`realm` به `renderRealm()` می‌رسد (`1243`). `shell.js` برای مراحل متن راهنما دارد؛ منبع ترتیب اصلی نیست.
- `docs/data.js:2–52`، `REALMS` را با ترتیب ثابت `healer, builder, explorer, thinker, artist, speaker` تعریف می‌کند. این مسیر از API یا Object.keys ترتیب نمی‌گیرد.
- `renderRealm` (`app.js:1792–1837`) با `REALMS.forEach((r, idx) => ...)` کارت‌ها را می‌سازد؛ handler برابر `toggleRealm('${r.id}')` است. `idx` به style/تأخیر نمایش می‌رود، نه هویت انتخاب.
- `toggleRealm(id)` (`1840–1849`) رشتهٔ id را در `state.selectedRealms` اضافه/حذف می‌کند. `indexOf` در اینجا پیدا کردن id در انتخاب‌هاست، نه خواندن محله از جایگاه کارت.
- `saveSession` و `loadSession` (`557–578`, `632–638`) همین selectedRealms را ذخیره/بازیابی می‌کنند. `SUB_REALMS[rid]` و pruning در `1056–1057` با id کار می‌کنند.
- selectedRealms ترتیب انتخاب کاربر را نیز نگه می‌دارد؛ `selectedRealms[0]` در `1558` مصرف می‌شود و badge «انتخاب ۱/۲/۳» از همان آرایه می‌آید. پس **نباید selectedRealms را shuffle کرد** یا آن را از ترتیب تازهٔ کارت‌ها بازسازی کرد.
- `buildPayload` (`2930–2960`) محله یا index کارت نمی‌فرستد؛ `micro_motives` از `state.likedCodes` می‌آید. محله‌ها مسیر رسیدن به انتخاب انگیزه را هدایت می‌کنند، نه ورودی مستقیم وزن API.

**نتیجه: shuffle فقط کپی نمایشی REALMS امن است.** دادهٔ پایه، idها، SUB_REALMS و انتخاب‌های ذخیره‌شده نباید mutate شوند. امن‌بودن نگاشت به معنی تضمین ثابت ماندن رفتار انسانی نیست؛ تغییر ترتیب می‌تواند انتخاب کاربر را تغییر دهد.

## ب) سؤال‌ها و پاسخ‌ها

### بارگذاری و ثبات سؤال

`loadQuestions` در `docs/app.js:933–952` فایل `DATA_BASE + 'questions_v2.json'` را می‌خواند و آرایه‌های `layers.strategies.questions` و `layers.values.questions` را در state می‌گذارد. ترتیب فعلی سؤال و گزینه، ترتیب JSON است. در این موج ترتیب **خود سؤال‌ها ثابت بماند**: ذخیرهٔ پاسخ‌ها بر اساس موقعیت سؤال است و `analyzeStrategyStyle` نیز S01..S25 را از همان موقعیت می‌سازد.

### S: index اصلی، یک شناسهٔ معنایی عددی

- در `docs/data/questions_v2.json` سؤال `S01` پنج شیء گزینه دارد، هرکدام با `index` اصلی ۰..۴ و `text`؛ option id جداگانه‌ای وجود ندارد.
- `renderStrategy` (`app.js:2602–2651`) برای هر شیء `o`، handler=`answerStrategy(o.index)` می‌سازد. `idx` حلقه فقط برچسب نمایشی «الف، ب، ...» است. selected بودن نیز با `o.index` سنجیده می‌شود.
- `answerStrategy` (`2653–2664`) با `dhStrategyLetter` پاسخ را به حرف canonical تبدیل و دوباره به عدد اصلی ۰..۴ در `state.strategyAnswers[currentQuestion]` ذخیره می‌کند.
- `dhBuildSjtAnswers` (`140–153`) id سؤال S01..S25 را به `sjt_1..sjt_25` و پاسخ canonical را به A..E تبدیل می‌کند. `analyzeStrategyStyle` (`3704–3716`) همین عدد اصلی را برای traitMap مصرف می‌کند.
- در موتور تجاری `_parse_s_strategy_answers` (`dark_horse_engine_v2.py:337–393`) حرف را با `ord(answer)-ord('A')` به index وزن تبدیل می‌کند؛ `_s_item_score` و `_compute_s_result` (`395–435`) `row[idx]` و traitMap همان index را می‌خوانند. موتور جایگاه نمایش گزینه در DOM را دریافت نمی‌کند.

بنابراین اگر کل شیء گزینه جابه‌جا شود و `o.index` ثابت بماند، انتخاب همان پاسخ معنایی همان payload و نمره را می‌دهد. اگر گزینهٔ اصلی E به اول لیست منتقل و با عدد ۰ ارسال شود، پاسخ A و وزن دیگری ثبت می‌شود: **ممنوع**. برچسب ظاهری جایگاه باید از هویت canonical تفکیک بماند.

### V: code پایدار و دو کارت نمایشی

- همان JSON برای `V01` گزینه‌های `{index:0, code:'Q1A', text:...}` و `{index:1, code:'Q1B', text:...}` دارد.
- `renderValue` (`app.js:2783–2848`) اکنون دو کارت صریح با `opts[0]` و `opts[1]` می‌سازد. متن، عنوان قطب از `DH_VALUE_POLE_TITLES[code]`، handler و selected همگی از code همان شیء گرفته می‌شوند.
- `answerValue(code)` (`2851` به بعد) code را در `state.valueAnswers[currentValueQuestion]` نگه می‌دارد؛ `buildPayload` آن را با id سؤال V01 به `conj_1` وصل می‌کند (`2939–2950`). نام کلاس‌های نمایشی `--a/--b` نباید به code علمی A/B تبدیل شوند.
- موتور `_compute_v_result` (`dark_horse_engine_v2.py:489–518`) پاسخ‌ها را با code و پایهٔ Qn گروه‌بندی و وزن انتخاب‌شده را از پسوند A/B می‌گیرد. جایگاه کارت در UI ورودی نمره نیست.

**نتیجهٔ V: GO** برای کپی نمایشیِ دو گزینه، همراه تمام metadata همان شیء. مرجع canonical سؤال و نگاشت QnA/QnB دست‌نخورده بماند.

### نمونهٔ واقعی موجود در تست، نه payload ساختگی

در `tests/test_strategy_ui_complete_gate.js:108–118` این مسیر موجود است:

```js
for (let i = 0; i < 25; i++) c.answerStrategy(i % 5);
const payload = c.buildPayload();
// تست ۲۵ کلید canonical و پاسخ‌های A..E را بررسی می‌کند.
c.state.strategyAnswers[0] = ' e ';
assert.equal(c.buildPayload().sjt_answers.sjt_1, 'E');
```

این نمونه شاهد پاسخ canonical است، نه ادعای وجود shuffle امروز. در `tests/test_value_poles_contract.js:136–148` نمونهٔ state و بازیابی موجود است:

```js
sandbox.state.valueAnswers = ['Q1A', 'Q3A'];
sandbox.state.currentValueQuestion = 2;
sandbox.saveSession();
// پس از loadSession:
assert.deepEqual(Array.from(sandbox.state.valueAnswers), ['Q1A', 'Q3A']);
```

این fixture ناقص برای تست persistence است؛ payload کامل کاربر یا تأیید پاسخ‌های هر ۱۵ سؤال نیست. مقدار `conjoint_choices` در `buildPayload` از همین codeها ساخته می‌شود؛ هیچ دادهٔ فردی یا نتیجهٔ ساختگی برای سند تولید نشده است.

## ج) پیشنهاد موج ۱ — صرفاً محدوده، نه پیاده‌سازی

مقصد منطقی PR اجرایی بعدی طبق قرارداد **main برای فرانت** است؛ شاخهٔ همین جلسه ثابت می‌ماند. این سند مجوز ساخت شاخه، PR اجرایی یا Merge نیست.

### فایل‌های بالقوهٔ مجاز

- `docs/app.js`: helper ترتیب نمایشی، مصرف در renderRealm/renderStrategy/renderValue و در صورت نیاز ذخیره/بازیابی metadata ترتیب نشست.
- تست UI جدید مانند `tests/test_display_shuffle_contract.js` و فقط در صورت نیاز توسعهٔ تست‌های existing session/navigation و S/V.
- Markdown شرح قرارداد. `docs/data.js` و `docs/data/questions_v2.json` نیاز به تغییر ندارند؛ data و وزن‌ها در موج پیشنهادی ثابت بمانند. تغییر shell نیز برای منبع ترتیب لازم نیست.

### شروط ایمنی و پذیرش آینده

1. از آرایهٔ canonical کپی ساخته شود؛ نه shuffle درجا روی REALMS یا q.options. متن، code و index اصلی یک واحد باقی بمانند.
2. ترتیب برای هر سفر/نشست یک‌بار تعیین و در برگشت، rerender پس از انتخاب، reload و resume حفظ شود؛ نه تصادفی‌سازی در هر render. metadata ترتیب جدید از پاسخ‌ها و sessionId سهمیه جدا باشد.
3. برای نشست قدیمی فاقد metadata، ترتیب canonical یا ترتیب یک‌بار مقداردهی‌شده با پاسخ‌های قبلی سازگار باشد؛ هیچ پاسخ یا sessionId به خاطر shuffle پاک نشود.
4. در S، تمام permutationهای نمایشی باید برای انتخاب همان شیء، همان `strategyAnswers`، payload و trait mirror را بدهند؛ در V هر دو چینش باید همان code/payload را حفظ کنند.
5. برای هر محله، کلیک با id، سقف انتخاب، badge ترتیب انتخاب و مسیر زیرمحله همان رفتار قبلی را نگه دارند. selectedRealms shuffle نشود.
6. ترتیب سؤال‌ها، cursorها، gate کامل‌بودن S، V-null و schema نسخهٔ ارزش تغییر نکنند. برچسب و عنوان، focus/keyboard و aria-selected با شیء درست همراه باشند.
7. تصادفی‌سازی ممکن است در دو نشست اتفاقاً ترتیب یکسان بدهد؛ «هر بار حتماً متفاوت» نیاز سیاست اجتناب از تکرار مستقل دارد. این تصمیم با «رندم» یکی نیست و باید پیش از اجرا روشن شود.
8. تست برابری payload قبل/بعد و در موج اجرایی، parity نتیجهٔ موتور با ورودی یکسان ثبت شود. ممیزی حاضر parity پس از shuffle را اجرا نکرده چون shuffle وجود ندارد.

### آیا refactor پیش‌نیاز NO-GO لازم است؟

NO-GO بنیادی برای دو مسیر یافت نشد؛ handlerهای فعلی از قبل هویت canonical را حمل می‌کنند. کوچک‌ترین مرزبندی لازم در موج بعد، **آرایه/ترتیب نمایشی جدا از دادهٔ اصلی** است. تغییر نام پارامتر `answerStrategy(idx)` به مفهومی مثل canonicalOptionIndex می‌تواند ابهام را کم کند، ولی تغییر قرارداد ذخیره یا مهاجرت پاسخ لازم نیست. هر طرحی که فقط متن‌ها را shuffle کند یا o.index را بر اساس جایگاه تازه بسازد، تا اصلاح همین مرزبندی NO-GO است.

## د) اعتبارسنجی و کنترل تغییرات

سه تست موجود در همین ممیزی اجرا شدند و exit=0 داشتند:

- `node tests/test_strategy_ui_complete_gate.js`
- `node tests/test_value_poles_contract.js`
- `node tests/test_motive_route_contracts.js`

این‌ها baseline موجود را بررسی می‌کنند، نه قابلیت تصادفی‌سازیِ هنوز پیاده‌نشده را. بررسی موتور با `git show` از SHA تجاری انجام شد؛ backend به main کپی نشده است.

فقط همین Markdown اضافه شد. هیچ ویرایش strategy_weights، value_weights، Total، dark_horse_engine، majors_database، micro_motives، Hybrid یا Cutover انجام نشد. رفتار سهمیه/خرید، API و فایل UI تغییر نکرد. هیچ shuffle، PR اجرایی، commit، push یا Merge انجام نشد.
