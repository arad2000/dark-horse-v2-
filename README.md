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

## نصب و راه‌اندازی

### ۱. کلون کردن پروژه

```bash
git clone https://github.com/arad2000/dark-horse-v2-.git
cd dark-horse-v2-
```

### ۲. نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

### ۳. اجرای سرور

```bash
python main_v2.py
```

سرور روی آدرس زیر بالا می‌آید:

```
http://0.0.0.0:8000
```

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
