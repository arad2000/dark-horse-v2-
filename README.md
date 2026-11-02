# Dark Horse V2

**سیستم هوشمند کشف فردیت برای هدایت تحصیلی و انتخاب رشته**

Dark Horse یک موتور توصیه‌گر مبتنی بر روان‌شناسی فردیت است که با تحلیل سه لایهٔ اصلی شخصیت (خرده‌انگیزه‌ها، راهبردهای شخصی و ارزش‌های بنیادین) به دانش‌آموزان و داوطلبان کنکور کمک می‌کند مسیر تحصیلی و شغلی مناسب خود را پیدا کنند.

---

## ویژگی‌ها

- **انتخاب رشته دانشگاهی**  
  فرمول امتیازدهی:  
  `Total = 0.55 × M + 0.30 × V + 0.15 × S`

- **هدایت تحصیلی پایه نهم (شاخه‌های دبیرستان)**  
  فرمول امتیازدهی:  
  `Total = 0.60 × M + 0.20 × S + 0.20 × V`

- استخراج کهن‌الگو (Archetype) و منبع رضایت از دیتابیس
- ارائه مسیرهای جایگزین (Alternative Paths)
- تولید توضیحات شخصی‌سازی‌شده بر اساس ۸ سناریوی مختلف
- پشتیبانی کامل از زبان فارسی

---

## ساختار پروژه

```
dark-horse-v2-/
├── main_v2.py                  # API اصلی (FastAPI)
├── dark_horse_engine_v2.py     # موتور اصلی Dark Horse
├── majors_database_v2.json     # دیتابیس رشته‌های دانشگاهی
├── school_branches_v2.json     # دیتابیس شاخه‌های دبیرستان
├── trait_map_v3.json           # نقشه ویژگی‌های رفتاری
├── value_poles_v2.json         # قطب‌های ارزشی
├── requirements.txt
└── docs/                       # فرانت‌اند (GitHub Pages)
    ├── index.html
    ├── app.js
    ├── data.js
    ├── feedback.html
    └── data/
        └── micro_motives.json  # لیست میکروموتیوها
```

---

## نقش شاخه‌ها و نصب backend

- **`main/docs` منبع انتشار frontend است.** وجود چند فایل Python در main به معنی کامل‌بودن backend آن نیست؛ checkout فعلی main برای اجرای مستقل backend کافی نیست.
- **منبع ساخت backend، commit بازبینی‌شدهٔ `deploy/liara-commercial-sandbox` است.** همهٔ deploy را به main کپی نکنید. اختلاف داده‌های مرجع یا گیت قرمز را با sync خودکار برطرف نکنید.
- قرارداد حاکم: [main/deploy](https://github.com/arad2000/dark-horse-v2-/blob/4b918261f3f7996439e6f9c98fe83f81f7df3c8d/docs/audits/MAIN_DEPLOY_CONTRACT.md). این راهنما نقش فعلی شاخه‌ها را توضیح می‌دهد، نه ممنوعیت دائمیِ backend در main.

### ۱. تعیین SHA و ساخت artifact تمیز

محیط مرجع CI، Python 3.12 است؛ چک محلی این اصلاح با Python 3.11 نیز اجرا شده است. دستورات زیر برای shell سازگار با Bash و ابزارهای git/tar هستند.

```bash
git clone --branch deploy/liara-commercial-sandbox --single-branch \
  https://github.com/arad2000/dark-horse-v2-.git
cd dark-horse-v2-
SOURCE_SHA=$(git rev-parse HEAD)
printf 'Backend source: %s\n' "$SOURCE_SHA"
# پیش از استفادهٔ عملیاتی، همین SHA باید بازبینی و تأیید شده باشد.
# برای تکرار ساخت، SOURCE_SHA را از رسید همان ساخت بردارید؛ نه از tip جدید شاخه.
ARTIFACT="../dark-horse-build-$SOURCE_SHA"
mkdir "$ARTIFACT"
git archive "$SOURCE_SHA" | tar -x -C "$ARTIFACT"
cd "$ARTIFACT"
```

`git archive` فقط فایل‌های commit را وارد artifact می‌کند، نه فایل untracked یا تغییر محلی. ثبت SHA، هویت منبع را مشخص می‌کند؛ به‌تنهایی نسخهٔ نصب وابستگی‌ها یا سلامت سرویس زنده را تضمین نمی‌کند. اسکریپت smoke زیر باید در همان نسخهٔ انتخاب‌شده موجود باشد؛ برای commit قدیمیِ فاقد آن، نتیجهٔ تست نسخهٔ جدید را به آن تعمیم ندهید.

### ۲. نصب در محیط مجزا و بررسی offline

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python scripts/backend_build_smoke.py
```

خروجی موفق شامل `APP_IMPORT=PASS`، `SCORING_REFERENCES=PASS`، `SHARED_ENGINE=PASS` و `LIFESPAN=PASS` است. این چک import و startup/shutdown موتور را در subprocess جدا و با محیط allowlistشده اجرا می‌کند؛ تنظیمات DB/AI/پرداخت والد به آن منتقل نمی‌شوند و مسیرهای معمول اتصال socket مسدودند. listener، درخواست HTTP، migration یا اتصال DB ایجاد نمی‌کند.

**این smoke test، readiness عملیاتی نیست.** `EXTERNAL_SERVICES=NOT_TESTED` عمدی است؛ عبور آن سلامت auth/DB/پرداخت/AI، گیت canonical یا اعتبار علمی را ثابت نمی‌کند. وابستگی‌های فعلی بازه‌ای‌اند؛ تا قفل مستقل نسخه‌ها، نصب مجدد الزاماً بایت‌به‌بایت یکسان نیست.

### ۳. اجرای دستی، فقط در محیط محلیِ مجاز

پس از پیکربندی مستقل محیط محلی و بدون استفاده از credential عملیاتی:

```bash
python -m uvicorn main_v2:app --host 0.0.0.0 --port 8000
```

`0.0.0.0` آدرس bind است، نه آدرس سایت عمومی. ریشهٔ API جای readiness تمام وابستگی‌ها نیست. برای آزمون صرفاً offline، همان smoke بالا کافی است و نیازی به اجرای سرور نیست.

مسیرهای نتیجهٔ deploy به Bearer معتبر و session_id سفر متعلق به کاربر با charge تأییدشده نیاز دارند؛ نمونهٔ بدنهٔ زیر به‌تنهایی درخواست اجرایی کامل نیست. با نبود DB/احراز هویت، محدودیت را با خاموش‌کردن guard دور نزنید. چرخهٔ schema عملیاتی Alembic-only است؛ این دستورات هیچ migration یا استقرار Liara را مجاز نمی‌کنند.

---

## API Endpoints

### انتخاب رشته دانشگاهی

```
POST /api/v2/darkhorse/discover
```

**بدنه درخواست:**
```json
{
  "micro_motives": ["code1", "code2", ...],
  "sjt_answers": {
    "sjt_1": "A",
    "sjt_2": "C",
    ...
  },
  "conjoint_choices": {
    "conj_1": "Q1A",
    "conj_2": "Q2B",
    ...
  }
}
```

### هدایت تحصیلی (شاخه‌های دبیرستان)

```
POST /api/v2/darkhorse/branch-discovery
```

بدنه درخواست دقیقاً مشابه endpoint بالا است.

---

## اجزای امتیازدهی

| مؤلفه | توضیح | وزن در انتخاب رشته | وزن در هدایت تحصیلی |
|-------|-------|---------------------|----------------------|
| **M (Motive)** | میزان همخوانی خرده‌انگیزه‌های کاربر با رشته/شاخه | 55٪ | 60٪ |
| **V (Value)** | همراستایی ارزش‌های بنیادین | 30٪ | 20٪ |
| **S (Strategy)** | همخوانی راهبردهای شخصی (SJT) | 15٪ | 20٪ |

---

## فرانت‌اند

فرانت‌اند پروژه به صورت Static در پوشه `docs/` قرار دارد و برای استفاده با **GitHub Pages** آماده است.

پس از فعال کردن GitHub Pages روی branch `main` و پوشه `/docs`، سایت از این آدرس در دسترس خواهد بود:

```
https://arad2000.github.io/dark-horse-v2-/
```

---

## تکنولوژی‌ها

- **Backend:** FastAPI + Uvicorn + Pydantic
- **موتور هوشمند:** Python خالص (بدون وابستگی به مدل‌های زبانی)
- **Frontend:** HTML + Vanilla JavaScript
- **داده:** JSON-driven architecture

---

## نسخه فعلی

- موتور: `DarkHorseEngineV2` (نسخه نهایی)
- Trait Map: v3
- Value Poles: v2
- API Version: 2.0

---

## توسعه‌دهنده

ساخته‌شده با تمرکز بر کشف فردیت واقعی کاربران  
**Dark Horse Philosophy** — پیدا کردن مسیرهایی که دیگران کمتر می‌بینند.
