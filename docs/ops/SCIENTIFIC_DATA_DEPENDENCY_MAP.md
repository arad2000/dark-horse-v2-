# نقشهٔ وابستگی دادهٔ علمی به `docs/`

**هدف:** جلوگیری از یک اشتباه مشخص و پرهزینه — حذف یا جابه‌جایی `docs/` بدون آگاهی از اینکه موتور علمی به آن وابسته است.

**دامنه:** فقط اسناد. هیچ کد، داده، مسیر، وزن، موتور یا workflow تغییر نمی‌کند.

**مکمل، نه جایگزین:** این سند به [`docs/audits/MAIN_DEPLOY_CONTRACT.md`](docs/audits/MAIN_DEPLOY_CONTRACT.md) و [`docs/ops/LIARA_FRONTEND_AUTO_DEPLOY.md`](docs/ops/LIARA_FRONTEND_AUTO_DEPLOY.md) اضافه می‌شود. قرارداد رسمی شاخه‌ها همان سند اول است؛ اینجا فقط **وابستگی فنی داده** ثبت می‌شود.

تاریخ: ۲۰۲۶-۱۱-۲۷ · مبنای بررسی: `main` = `41c5acf` · `deploy/liara-commercial-sandbox` = `ec30e92`

---

## ۱. خلاصه — در یک پاراگراف

در شاخهٔ `deploy`، پوشهٔ `docs/` **هم فرانت‌اند مرده است و هم محل نگهداری دادهٔ علمی زنده**. موتور انتخاب رشته ۱۵ فایل JSON را از `docs/data/` می‌خواند. حذف `docs/` — حتی به قصد «پاک کردن فرانت‌اند تکراری» — **انتخاب رشته را از کار می‌اندازد**. این سند آن وابستگی را فهرست می‌کند تا هیچ‌کس دوباره به این تله نیفتد.

---

## ۲. شواهد (قابل بازتولید)

### ۲.۱ با `docs/` سر جایش

```
capacity rows: 5
sanjesh engine: imported OK
```

### ۲.۲ با `docs/` برداشته‌شده

```
/api/v1/admission/chance  (منبع: capacity)
   → DEAD: FileNotFoundError

/api/v1/admission/chance  (منبع: record / سوابق تحصیلی)
   → DEAD: FileNotFoundError
```

خروجی مشخص: `FileNotFoundError: .../docs/data/sanjesh_riazi_1405_programs.json`

**تفسیر:** مسیرها با `ROOT / "docs" / "data" / ...` ساخته می‌شوند، پس خطا در **زمان درخواست** رخ می‌دهد نه در startup. یعنی سرویس بالا می‌آید و سالم به نظر می‌رسد، ولی هر درخواست انتخاب رشته ۵۰۰ می‌دهد. این خطرناک‌ترین نوع شکست است.

---

## ۳. فهرست کامل وابستگی‌ها

هر فایل زیر **از داخل `docs/`** خوانده می‌شود. ستون «کد مصرف‌کننده» دقیق است و قابل جست‌وجو.

| فایل | کد مصرف‌کننده | نقش | حجم تقریبی |
|---|---|---|---|
| `docs/data/sanjesh_record_capacity_full.json` | `admission_capacity_record.py` | ظرفیت سوابق تحصیلی | ۶.۲ مگ |
| `docs/data/sanjesh_tajrobi_1405_programs.json` | `admission_capacity_record.py`, `admission_exam_capacity.py` | ظرفیت تجربی | ۴.۸ مگ |
| `docs/data/sanjesh_riazi_1405_programs.json` | `admission_capacity_record.py`, `admission_exam_capacity.py` | ظرفیت ریاضی | ۴.۰ مگ |
| `docs/data/sanjesh_ensani_1405_programs.json` | `admission_capacity_record.py`, `admission_exam_capacity.py` | ظرفیت انسانی | ۳.۷ مگ |
| `docs/data/sanjesh_honar_1405_programs.json` | `admission_capacity_record.py`, `admission_exam_capacity.py` | ظرفیت هنر | ۳.۳ مگ |
| `docs/data/sanjesh_zaban_1405_programs.json` | `admission_capacity_record.py`, `admission_exam_capacity.py` | ظرفیت زبان | ۳.۲ مگ |
| `docs/data/micro_motives.json` | `audit_hybrid_integrity.py`, `reference_contract_audit.py` + اثر انگشت | ۱٬۳۹۳ انگیزه | ۳۱۲ کیلو |
| `docs/data/questions_v2.json` | `reference_contract_audit.py` + اثر انگشت | سؤالات | ۳۶ کیلو |
| `docs/data/trait_map_v3.json` | `audit_hybrid_integrity.py`, `reference_contract_audit.py` | نقشهٔ ویژگی‌ها | ۱۲ کیلو |
| `docs/bomi_geography_v1.json` | `admission_sanjesh_engine.py` | جغرافیای بومی | ۸ کیلو |
| `docs/sanjesh_table5_major_bomi_v1.json` | `admission_sanjesh_engine.py` | جدول ۵ بومی | ۸ کیلو |

مجموع دادهٔ علمی داخل `docs/`: حدود **۴۴ مگابایت** (از ۶۹ مگ کل پوشه).

### ۳.۱ فایل‌های ۱۴۰۴

پوشهٔ `docs/data/` فایل‌های ۱۴۰۴ را هم دارد (`sanjesh_*_1404_programs.json`). این‌ها را **فقط اسکریپت‌های `scripts/audit_*`** می‌خوانند، نه مسیر درخواست زنده. حذفشان سرویس را نمی‌شکند، ولی ابزارهای بازبینی داده را می‌شکند.

### ۳.۲ اثر انگشت علمی

`main_v2.py` این فهرست را هش می‌کند:

```python
_SCORING_FINGERPRINT_FILES = (
    "dark_horse_engine_v2.py",
    "docs/data/micro_motives.json",     # ← داخل docs
    "docs/data/questions_v2.json",      # ← داخل docs
    "majors_database_v2.json",
    "trait_map_v3.json",
    "value_poles_v2.json",
    "school_branches_v2.json",
)
```

**پیامد مستقیم:** هر جابه‌جایی `docs/data/micro_motives.json` یا `docs/data/questions_v2.json`، **اثر انگشت علمی را عوض می‌کند** — حتی اگر بایت‌ها دست‌نخورده باشند. اگر روزی این فایل‌ها منتقل شوند، اثر انگشت باید بازتولید و مستند شود، وگرنه گیت یکپارچگی علمی به‌درستی هشدار می‌دهد.

---

## ۴. تفکیک «چه چیزی مرده است»

در `deploy`:

| مسیر | وضعیت | دست بزنید؟ |
|---|---|---|
| `deploy/docs/data/` | **زنده** — موتور می‌خواند | ❌ هرگز |
| `deploy/docs/*.json` (ریشه) | **زنده** — موتور می‌خواند | ❌ هرگز |
| `deploy/docs/*.js` | **مرده** — از هیچ‌جا سرو نمی‌شود | ⚠️ با احتیاط |
| `deploy/docs/*.css` | مرده | ⚠️ با احتیاط |
| `deploy/docs/*.html` | مرده | ⚠️ با احتیاط |

**هشدار دربارهٔ فایل‌های مرده:** بعضی تست‌ها به آن‌ها وابسته‌اند. مثلاً `test_frontend_billing_admin_sandbox_contract.py` و `test_release_hotfix_contract.py` محتوای `docs/commercial_ui.js` و `docs/index.html` را می‌خوانند. جدول بالا «سرو نمی‌شود» می‌گوید، نه «بی‌مصرف است».

---

## ۵. ریسک اصلی و قاعدهٔ عملی

### چرا خطرناک است

شکست در **زمان درخواست** رخ می‌دهد، نه در startup:

- سرویس بالا می‌آید ✅
- `/` جواب می‌دهد ✅
- health ظاهراً سالم است ✅
- **هر درخواست انتخاب رشته ۵۰۰ می‌دهد** ❌

یعنی این شکست در هیچ بررسی سادهٔ استقرار دیده نمی‌شود.

### قاعدهٔ عملی

> **`docs/data/` و JSONهای ریشهٔ `docs/` دادهٔ عملیاتی‌اند، نه دارایی فرانت‌اند.**

هر کسی که می‌خواهد `docs/` را در `deploy` پاک کند، باید اول این جمله را در PR خود نقل کند و ثابت کند `build_exam_capacity_results` و `build_record_capacity_results` هنوز کار می‌کنند.

### آزمون پذیرش برای هر تغییر آینده

پیش از هر PR که به `docs/` در `deploy` دست می‌زند:

```bash
python -c "
from admission_exam_capacity import build_exam_capacity_results as b
from admission_capacity_record import build_record_capacity_results as r
print('exam  :', len(b(group='riazi', major_ids=[41], province='تهران', periods=['روزانه'], limit=5)))
print('record:', len(r(group='riazi', major_ids=[41], province='تهران', periods=['روزانه'], limit=5)))
"
```

هر دو عدد باید **بزرگ‌تر از صفر** باشند. صفر یا استثنا یعنی تغییر، موتور را شکسته است.

---

## ۶. نکتهٔ `main`

`main` منبع انتشار فرانت‌اند است (`docs/` از `main` روی `asbe-siah.ir` منتشر می‌شود) و **بک‌اند کامل ندارد**.

| ورودی اثر انگشت | روی `main` |
|---|---|
| `dark_horse_engine_v2.py` | هست، ولی **متفاوت** با deploy (۷۵۵ خط در برابر ۱٬۱۲۳) |
| `docs/data/micro_motives.json` | هست، بایت‌به‌بایت یکسان |
| `docs/data/questions_v2.json` | هست، بایت‌به‌بایت یکسان |
| `majors_database_v2.json` | هست، یکسان |
| `value_poles_v2.json` | هست، یکسان |
| `school_branches_v2.json` | هست، یکسان |
| `trait_map_v3.json` | **نیست** |

**نتیجهٔ عملی:** اثر انگشت علمی از `main` قابل بازتولید نیست — چون یک ورودی غایب است و یکی متفاوت. **`deploy` تنها منبع معتبر اثر انگشت علمی runtime است.** این با بخش ۲ سند `MAIN_DEPLOY_CONTRACT.md` هم‌خوان است و آن را تأیید می‌کند.

### داده‌های انتخاب رشته روی `main`

`docs/data/` روی `main` فقط **۳ فایل** دارد؛ روی `deploy` **۱۹ فایل**.
`sanjesh_riazi_1405_programs.json` و `sanjesh_record_capacity_full.json` روی `main` **نیستند**. پس هر تلاش برای اجرای بک‌اند از `main` در مسیر انتخاب رشته شکست می‌خورد.

---

## ۷. وضعیت فعلی: ریسک پذیرفته‌شده

**هیچ تغییری پیشنهاد نمی‌شود.** وضعیت زیر نادرست است ولی **کار می‌کند** و دست زدن به آن بدون برنامه، ریسک بالاتری از نگه‌داشتنش دارد.

| مورد | وضعیت |
|---|---|
| دادهٔ علمی داخل پوشهٔ فرانت‌اند | ❌ نادرست ولی فعال |
| `docs/` روی deploy حاوی فرانت‌اند مرده | ⚠️ منبع سردرگمی |
| شکست در زمان درخواست (نه startup) | ⚠️ خطرناک |

### چرا الان دست نمی‌زنیم

1. جداسازی درست نیازمند تغییر ۱۵ مسیر + بازتولید اثر انگشت است.
2. اثر انگشت علمی به دو فایل داخل `docs/data/` گره خورده — جابه‌جایی، گیت یکپارچگی را می‌شکند.
3. هیچ‌کدام از این‌ها用户体验 را امروز خراب نمی‌کند.
4. ریسک تغییر، از ریسک نگه‌داشتن بیشتر است.

### وقتی جداسازی منطقی شد

اگر روزی خواستید، ترتیب امن این است:

1. پوشهٔ `reference_data/` بسازید و **کپی** کنید (حذف نکنید).
2. مسیرها را یکی‌یکی عوض کنید، هر بار آزمون پذیرش بخش ۵ را اجرا کنید.
3. اثر انگشت را بازتولید و در سند ثبت کنید.
4. فقط بعد از سبز شدن همه، نسخهٔ قدیمی را حذف کنید.

**هرگز برعکس:** اول حذف، بعد تعمیر.

---

## ۸. خلاصهٔ یک‌خطی برای آینده

> در `deploy`، پوشهٔ `docs/` را به چشم «فرانت‌اند تکراری» نبینید. داخلش مغز انتخاب رشته است.

---

*این سند فقط اسناد است. هیچ داده، وزن، موتور، مسیر، workflow یا محیطی تغییر نکرد.*
