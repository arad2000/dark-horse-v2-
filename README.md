# Dark Horse V2

**سیستم هوشمند کشف فردیت برای هدایت تحصیلی و انتخاب رشته**

Dark Horse یک موتور توصیه‌گر مبتنی بر روان‌شناسی فردیت است. با سه لایهٔ شخصیت — خرده‌انگیزه‌ها، راهبردهای شخصی و ارزش‌های بنیادین — به دانش‌آموز و داوطلب کنکور کمک می‌کند مسیر تحصیلی مناسب خودش را پیدا کند.

## الان کجاست

| لایه | آدرس | وضعیت |
|---|---|---|
| اپ | [arad2000.github.io/dark-horse-v2-](https://arad2000.github.io/dark-horse-v2-/) | زنده روی GitHub Pages |
| API امتیازدهی | [asbe-siah.liara.run](https://asbe-siah.liara.run) | زنده؛ منبع امتیازدهی JSON است |
| مهاجرت PostgreSQL | شاخه `feature/postgresql-hybrid` | فقط staging — **سوییچ پروداکشن خاموش است** |

منبع حقیقت روان‌سنجی و امتیازدهی، فایل‌های JSON داخل گیت است. PostgreSQL برای دادهٔ عملیاتی (نشست، اعتبار، پرداخت) آماده می‌شود و تا تأیید جداگانه وارد موتور زنده نمی‌شود.

## امتیازدهی (تغییر نکرده)

- انتخاب رشته دانشگاهی: `Total = 0.55 × M + 0.30 × V + 0.15 × S`
- هدایت تحصیلی پایه نهم: `Total = 0.60 × M + 0.20 × S + 0.20 × V`

خروجی شامل کهن‌الگو، منبع رضایت، مسیر جایگزین و توضیح شخصی‌سازی‌شده است.

## منبع داده

یک کپی از هر دیتاست مرجع کافی است:

| فایل | نقش |
|---|---|
| `docs/data/micro_motives.json` | خرده‌انگیزه‌ها (موتور + فرانت) |
| `docs/data/trait_map_v3.json` | نقشهٔ راهبرد SJT |
| `docs/data/questions_v2.json` | متن سؤال‌های فرانت |
| `majors_database_v2.json` | ۱۶۰ رشته |
| `school_branches_v2.json` | چهار شاخه دبیرستان |
| `value_poles_v2.json` | قطب‌های ارزشی Q1A..Q15B |

کپی ریشهٔ `micro_motives.json` و snapshotهای `*_v22.json` حذف شدند تا دو نسخه از یک حقیقت باقی نماند.

## ساختار

```
dark-horse-v2-/
├── main_v2.py                 API زنده (FastAPI، JSON-backed)
├── dark_horse_engine_v2.py    موتور M / V / S
├── majors_database_v2.json
├── school_branches_v2.json
├── value_poles_v2.json
├── requirements.txt
├── liara.json
└── docs/                      فرانت GitHub Pages
    ├── index.html
    ├── app.js
    └── data/
        ├── micro_motives.json
        ├── questions_v2.json
        └── trait_map_v3.json
```

## اجرای محلی

```bash
git clone https://github.com/arad2000/dark-horse-v2-.git
cd dark-horse-v2-
pip install -r requirements.txt
python main_v2.py
```

API روی همان پورتی که `PORT` می‌گوید بالا می‌آید (پیش‌فرض ۸۰۰۰).

## API

```
GET  /
POST /api/v2/darkhorse/discover
POST /api/v2/darkhorse/branch-discovery
```

بدنهٔ هر دو POST:

```json
{
  "micro_motives": ["MED-001"],
  "sjt_answers": { "sjt_1": "A" },
  "conjoint_choices": { "conj_1": "Q1A" }
}
```

لایهٔ حساب / اعتبار / پرداخت روی شاخهٔ hybrid است و هنوز به `main` نیامده.

## تکنولوژی

- Backend: FastAPI + Uvicorn + Pydantic
- موتور: Python خالص
- Frontend: HTML + Vanilla JS + PWA
- داده: JSON در گیت

## نسخه

- موتور: `DarkHorseEngineV2`
- Trait Map: v3 — Value Poles: v2 — API: 2.0
- PostgreSQL runtime cutover: **OFF**
