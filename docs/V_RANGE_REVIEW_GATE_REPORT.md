# بازبینی علمی V — برد، رگرسیون و مصرف‌کننده

## وضعیت و مبنا

مبنای منبع deploy: `45e61bc5ed0f83a69ec36aff9de7a24a1ce45b90`. نسخهٔ بعد، working tree همین شاخه است؛ هنوز مستقر نیست.
منظور از «قبل» کد Git شاخهٔ استقرار است، نه مشاهدهٔ API زنده. دسترسی مستقیم زنده از این محیط غیرقابل تأیید است.
Merge و redeploy مجاز نیستند. ساخت Draft صرفاً برای بازبینی است و به معنی Go انتشار نیست.

## ۱. مرجع داده

۲۳۰ = ۱۶۰ اولیه + ۷۰ مدخل جدید؛ ۲۰۲ فعال = ۲۳۰ − ۲۸ = ۱۶۰ + ۴۲.
عبارت «۱۶۰+۴۲−۲۸» نادرست است: ۴۲ از قبل فقط فعال‌ها را می‌شمارد. چهار شاخه مستقل‌اند؛ دامنه ۲۰۶ است، نه ۲۰۲×۴.
فایل hybrid غایب مبنای این ممیزی نیست؛ هیچ ادعایی دربارهٔ تطبیق با آن نداریم.

| فایل | len | MD5 فعلی = مبنا | SHA-256 فعلی = مبنا |
|---|---:|---|---|
| majors_database_v2.json | 230 | `5c58ea511c77cab70572fd3a335ffa74` | `3ed655ecfe02984dac602fff84cea0d7cd0b1cccd25a9b492288630b14240f84` |
| school_branches_v2.json | 4 | `f86dd61da4a3858b40bac36cebee89fd` | `49821a86476dc9d5bb2d8fee68048be83121aa74bc2bd03715b9c1c73ff88412` |

مقایسهٔ بایت‌به‌بایت نیز برابر است. این هویت فایل در Git است، نه اثبات فایل بارگذاری‌شده در runtime زنده.

## ۲. استخراج عینی فرمول

قدیم: `V_old = (1/n) Σ [w_chosen / max(wA,wB)]`؛ زوج با max=0 سهم صفر می‌گرفت و در n شمرده می‌شد.
جدید: `V_new = Σ(w_chosen − min(wA,wB)) / Σ(max(wA,wB) − min(wA,wB))` روی پاسخ‌های معتبر با range≥0.02.

### قبل، deploy مبنا: `_pairwise_value_score` — dark_horse_engine_v2.py:251–262

```python
    def _pairwise_value_score(choice: str, value_weights: Dict[str, float]) -> Tuple[float, float]:
        code = choice.strip().upper()
        chosen_w = float(value_weights.get(code, 0.0) or 0.0)
        if len(code) >= 3 and code.startswith("Q") and code[-1] in ("A", "B"):
            base = code[:-1]
            pair_max = max(
                float(value_weights.get(base + "A", 0.0) or 0.0),
                float(value_weights.get(base + "B", 0.0) or 0.0),
            )
            normalized = (chosen_w / pair_max) if pair_max > 0.0 else 0.0
            return normalized, chosen_w
        return chosen_w, chosen_w
```

### قبل، deploy مبنا: `_compute_v_score` — dark_horse_engine_v2.py:264–284

```python
    def _compute_v_score(self, value_choices: List[str], value_weights: Dict[str, float]) -> Tuple[float, List[str]]:
        if not value_choices or not value_weights:
            return 0.0, []

        total = 0.0
        valid = 0
        highlights = []

        for v in value_choices:
            if not v or not v.strip():
                continue
            code = v.strip().upper()
            normalized, raw_weight = self._pairwise_value_score(code, value_weights)
            total += normalized
            valid += 1
            if raw_weight > 0.7 or (normalized >= 0.85 and raw_weight >= 0.55):
                pole = self.value_poles.get(code, v.strip())
                highlights.append(f"ارزش «{pole}»: هم‌راستایی قوی")

        score = min(1.0, total / valid) if valid > 0 else 0.0
        return score, highlights
```

### بعد، کاندیدای منتشرنشده: `_compute_v_result` — dark_horse_engine_v2.py:276–316

```python
    def _compute_v_result(self, value_choices, value_weights):
        # Repeated identical answers count once; conflicting answers invalidate
        # the question rather than making the result depend on input order.
        answers = {}
        for value in value_choices or []:
            code = self._valid_value_code(value)
            if code:
                answers.setdefault(code[:-1], set()).add(code)
        answered = sum(len(codes) == 1 for codes in answers.values())
        numerator = denominator = 0.0
        informative = 0
        highlights = []
        for base, codes in answers.items():
            if len(codes) != 1:
                continue
            code = next(iter(codes))
            try:
                a, b = (float(value_weights[base + side]) for side in "AB")
            except (KeyError, TypeError, ValueError):
                continue
            if not all(isfinite(x) and 0 <= x <= 1 for x in (a, b)):
                continue
            span = round(abs(a - b), 12)
            if span < self.V_EPSILON:
                continue
            chosen = a if code[-1] == "A" else b
            numerator += chosen - min(a, b)
            denominator += span
            informative += 1
            if chosen > min(a, b):
                pole = self.value_poles.get(code, code)
                highlights.append(f"ارزش «{pole}»: هم‌راستایی قوی")
        score = min(1.0, max(0.0, numerator / denominator)) if denominator else None
        return {
            "score": score,
            "status": ("complete" if answered == 15 else "partial") if score is not None
                      else ("no_discriminative_evidence" if answered else "incomplete"),
            "coverage": {"answered": answered, "total": 15,
                         "discriminative_answered": informative},
            "highlights": highlights,
        }
```

### بعد، کاندیدای منتشرنشده: `_compute_v_score` — dark_horse_engine_v2.py:318–320

```python
    def _compute_v_score(self, value_choices, value_weights):
        result = self._compute_v_result(value_choices, value_weights)
        return result["score"], result["highlights"]
```

### زوج برابر، نزدیک و مخرج صفر

- قبل: زوج مثبت برابر حتی با انتخاب دلخواه ۱ می‌داد؛ برای max=0 سهم صفر بود؛ ε وجود نداشت.
- بعد: `V_EPSILON=0.02`؛ اختلاف به ۱۲ رقم اعشار گرد و سپس مقایسه می‌شود. کمتر از ۰٫۰۲ حذف؛ دقیقاً ۰٫۰۲ حفظ.
- زوج برابر از صورت و مخرج حذف می‌شود. اگر هیچ زوج واجد تمایزی باقی نماند score=null است؛ نه صفر.
- هر زوج پذیرفته‌شده حداقل ۰٫۰۲ به مخرج می‌دهد؛ بنابراین مخرج مثبتِ خیلی کوچک‌تر از ε نداریم.
- EPSILON سیاست حذف تمایز ضعیف است، نه آستانهٔ اثبات‌شدهٔ روان‌سنجی. score در [0,1] محدود می‌شود.
- با دادهٔ معتبر، مخرج مثبت: کمینه=۰، بیشینه=۱ و امید انتخاب مستقل ۵۰/۵۰ برابر ۰٫۵؛ واریانس رشته‌ها لزوماً برابر نیست.
- پاسخ خالی/نامعتبر حذف، تکراری یک‌بار، و انتخاب متناقض A/B یک دوراهی باطل می‌شود. پوشش در امتیاز ضرب نمی‌شود.

### همان مثال zahra_synthetic

`seed=3`؛ طراحی گرافیک #140: V قدیم 66.99% و جدید 10.87%؛ Total از 43.4 به 26.6.
۱۴ زوج متمایز: سه انتخاب بیشینه (Q3B,Q6B,Q13A) و یازده کمینه؛ Q5=(0.55,0.55) دقیقاً برابر است.
صورت = 0.15+0.05+0.30 = 0.50؛ مخرج = 4.60؛ V=0.50/4.60. null یا حذف زوج نزدیک علت خروج نیست.
در این مثال خاموش‌کردن ε هم امتیاز جدید را عوض نمی‌کند؛ افت فقط از 0.30×ΔV است.

## ۳. جدول چندپروفایلی

همهٔ پروفایل‌ها مصنوعی‌اند. جدول زیر یک رشتهٔ کانونی از هر پروفایل است؛ هر پروفایل روی **تمام ۲۰۲ رشته** اجرا شده است.
جدول کامل ۱۸×۲۰۲=۳۶۳۶ ردیف در `V_RANGE_MULTIPROFILE_ROWS.csv` و JSON موجود است؛ ورودی دقیق و seed هر پروفایل ثبت شده‌اند.
متعادل یعنی الگوی پاسخ A/B متناوب (۸/۷)، نه تضمین امتیاز برابر برای رشته‌ها. قوی روی قطب یعنی همه A یا همه B، نه الزاماً V=۱.
اعداد M/S/V درصد و Total با گردکردن یک‌رقمی فعلی موتور است. عبور از ۳۰ جدا از شرط M≥۱۵ گزارش می‌شود.

| پروفایل / seed | major_id | name | M قبل→بعد | S قبل→بعد | V قبل→بعد | Total قبل→بعد | ≥30→<30 | null |
|---|---:|---|---:|---:|---:|---:|---|---|
| sara_synthetic / 0 | 1 | پزشکی | 100.00→100.00 | 47.69→47.69 | 71.62→51.07 | 83.6→77.5 | خیر | خیر |
| ali_synthetic / 1 | 38 | مدیریت توانبخشی | 100.00→100.00 | 52.84→52.84 | 82.34→58.26 | 87.6→80.4 | خیر | خیر |
| hossein_synthetic / 2 | 75 | مهندسی بیوسیستم | 100.00→100.00 | 70.00→70.00 | 87.88→73.21 | 91.9→87.5 | خیر | خیر |
| zahra_synthetic / 3 | 140 | طراحی گرافیک | 28.57→28.57 | 50.68→50.68 | 66.99→10.87 | 43.4→26.6 | بله | خیر |
| random_1 / 4 | 149 | زبان و ادبیات عربی | 100.00→100.00 | 75.14→75.14 | 76.75→56.28 | 89.3→83.2 | خیر | خیر |
| random_2 / 5 | 187 | طراحی و ساخت طلا و جواهر | 100.00→100.00 | 67.24→67.24 | 91.79→60.23 | 92.6→83.2 | خیر | خیر |
| pole_a_biotech / 101 | 34 | بیوتکنولوژی (پزشکی) | 100.00→100.00 | 36.17→36.17 | 77.63→56.78 | 83.7→77.5 | خیر | خیر |
| pole_b_biotech / 102 | 93 | بیوتکنولوژی (علوم پایه) | 100.00→100.00 | 57.78→57.78 | 72.60→42.43 | 85.4→76.4 | خیر | خیر |
| pole_a_computer / 103 | 42 | مهندسی کامپیوتر | 100.00→100.00 | 56.91→56.91 | 86.53→66.88 | 89.5→83.6 | خیر | خیر |
| pole_b_software / 104 | 44 | مهندسی نرم‌افزار | 100.00→100.00 | 54.45→54.45 | 75.91→38.36 | 85.9→74.7 | خیر | خیر |
| balanced_it / 105 | 43 | مهندسی فناوری اطلاعات | 100.00→100.00 | 33.25→33.25 | 74.19→41.33 | 82.2→72.4 | خیر | خیر |
| balanced_computer_science / 106 | 45 | علوم کامپیوتر | 100.00→100.00 | 27.37→27.37 | 82.11→65.50 | 83.7→78.8 | خیر | خیر |
| balanced_biotech / 107 | 169 | زیست‌فناوری | 100.00→100.00 | 45.72→45.72 | 79.55→66.67 | 85.7→81.9 | خیر | خیر |
| balanced_graphic / 108 | 140 | طراحی گرافیک | 100.00→100.00 | 49.41→49.41 | 85.53→64.13 | 88.1→81.7 | خیر | خیر |
| sensitive_biotech / 109 | 34 | بیوتکنولوژی (پزشکی) | 100.00→100.00 | 48.70→48.70 | 81.75→63.72 | 86.8→81.4 | خیر | خیر |
| sensitive_software / 110 | 44 | مهندسی نرم‌افزار | 100.00→100.00 | 42.01→42.01 | 72.14→27.04 | 82.9→69.4 | خیر | خیر |
| sensitive_it / 111 | 43 | مهندسی فناوری اطلاعات | 100.00→100.00 | 35.21→35.21 | 88.19→75.24 | 86.7→82.9 | خیر | خیر |
| unanswered_v / 112 | 140 | طراحی گرافیک | 100.00→100.00 | 65.45→65.45 | 0.00→null | 64.8→null | خیر | بله |

### جمع آماری روی تمام رشته‌ها، به تفکیک پروفایل

| پروفایل | تعداد رشته با abs(ΔV)>20 نقطه | ≥30→<30 بدون شرط M | <30→≥30 بدون شرط M | ≥30→<30 با M≥15 | معکوس با M≥15 | null |
|---|---:|---:|---:|---:|---:|---:|
| sara_synthetic | 164 | 151 | 0 | 0 | 0 | 0 |
| ali_synthetic | 119 | 156 | 0 | 0 | 0 | 0 |
| hossein_synthetic | 67 | 123 | 0 | 0 | 0 | 0 |
| zahra_synthetic | 142 | 148 | 0 | 1 | 0 | 0 |
| random_1 | 177 | 129 | 0 | 0 | 0 | 0 |
| random_2 | 184 | 132 | 0 | 0 | 0 | 0 |
| pole_a_biotech | 173 | 98 | 0 | 0 | 0 | 0 |
| pole_b_biotech | 137 | 147 | 0 | 0 | 0 | 0 |
| pole_a_computer | 173 | 119 | 0 | 0 | 0 | 0 |
| pole_b_software | 137 | 148 | 0 | 0 | 0 | 0 |
| balanced_it | 191 | 84 | 0 | 0 | 0 | 0 |
| balanced_computer_science | 94 | 111 | 0 | 0 | 0 | 0 |
| balanced_biotech | 191 | 80 | 0 | 0 | 0 | 0 |
| balanced_graphic | 94 | 136 | 0 | 0 | 0 | 0 |
| sensitive_biotech | 154 | 137 | 0 | 0 | 0 | 0 |
| sensitive_software | 167 | 125 | 0 | 0 | 0 | 0 |
| sensitive_it | 110 | 104 | 0 | 0 | 0 | 0 |
| unanswered_v | 0 | 0 | 0 | 0 | 0 | 202 |

مجموع رخدادهای رشته–پروفایل: abs(ΔV)>20: **2474**؛ عبور نزولی عددی: **2128**؛ صعودی: **0**.
تعداد رشتهٔ یکتا با abs(ΔV)>20 در حداقل یک پروفایل: **202**.
عبور واقعی با شرط M≥15: نزولی **1**، صعودی **0**.
null: **202**، همگی در پروفایل کنترلِ بدون پاسخ V؛ در ۱۷ پروفایل دارای پاسخ کامل هیچ رشته‌ای null نشد.
در کنترل بدون پاسخ، V قدیم صفر بود؛ Total جدید null است و عبور عددی محسوب نمی‌شود.
بیشتر عبورهای عددیِ بدون شرط M مربوط به رشته‌هایی است که از قبل واجد شرط نمایش نبودند؛ این دو شمارش نباید خلط شوند.

M و S قبل/بعد دقیقاً برابر: `True`؛ SHA-256 مشترک `5b200172dcbf3b624fb818592dbcbf6fa85f5bb0d391cb9b8dd639185714f85b`.
AST توابع `_compute_branch_m_score` و `_compute_s_score` نسبت به مبنا بدون تغییر است؛ pool_scale و فیلتر شاخه تغییر نکرده‌اند.

## ۴. قرارداد null و دروازهٔ مصرف‌کننده

- API: نتایج null جدا از sort و persistence عددی؛ best_branch نباید به مدخل محاسبه‌ناپذیر اشاره کند.
- API: وضعیت، value_assessment، coverage و method.version در پاسخ حفظ می‌شوند.
- UI: مدخل محاسبه‌ناپذیر خارج از رتبه‌بندی، با «فاقد شواهد تمایزبخش» جدا از «اطلاعات ناکافی برای محاسبهٔ امتیاز».
- UI: null به صفر یا درصد تبدیل نمی‌شود؛ صفر واقعی همچنان یک امتیاز معتبر است. پیام شکست آستانه جای وضعیت ناقص نمایش داده نمی‌شود.
- تست Node تابع واقعی displayResults را با DOM sink شبیه‌سازی‌شده اجرا می‌کند؛ آزمون مرورگر واقعی یا layout نیست.
- تست API آداپتور واقعی با موتور مصنوعی و موتور واقعی محلی است؛ DB و authentication در تست mock می‌شوند. وضعیت live اثبات نمی‌شود.

## ۵. پیشنهاد محصول — A مشروط، بدون تغییر کد

پیشنهاد: آستانهٔ ۳۰٪ در این بسته ثابت بماند (A)، ولی Go انتشار منوط به بازبینی ناظر باشد.
در ۱۷ پروفایل کامل، فقط یک خروج واجد شرط M رخ داد؛ آن مورد یازده انتخاب کمینه و V=10.87% دارد.
این نمونهٔ کوچک مصنوعی پشتوانهٔ انتخاب عدد تازه برای آستانه نیست؛ بنابراین عدد جایگزین بدون دادهٔ واقعی پیشنهاد نمی‌شود.
گزینه C توصیه نمی‌شود: زیر آستانه یک امتیاز محاسبه‌شده است، نه فقدان شواهد؛ تبدیل آن به null قرارداد علمی را مخدوش می‌کند.
تصمیم نهایی محصول و استقرار فقط با ناظر؛ هیچ آستانه‌ای در کد تغییر نکرده است.

## ۶. بازتولید و گیت نهایی

```bash
python scripts/audit_v_range_norm.py > docs/V_RANGE_REGRESSION_REPORT.json
python scripts/render_v_range_report.py
python -m unittest test_v_range_norm test_engine_psychometrics test_p0_s_score test_v_consumer_contract test_main_api_contract -q
node tests/test_v_null_consumer.js
```

**No-Go برای Merge/استقرار** تا CI کامل Backend و تست‌های V موفق و Go ناظر ثبت شوند.
Draft بازبینی، مجوز Merge یا redeploy نیست. گزارش CI باید به SHA مشخص متصل شود؛ سبز بودن تست محلی جای CI را نمی‌گیرد.
