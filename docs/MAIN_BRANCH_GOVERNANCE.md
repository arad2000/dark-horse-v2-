# حاکمیت شاخه‌ها و مرز منبع حقیقت (`main` در برابر `deploy`)

این سند مرز رسمی «منبع حقیقت» بین انتشار عمومی فرانت‌اند و runtime بک‌اند را ثبت می‌کند تا همگام‌سازی‌های بعدی هرگز با کپی کور باعث بازگشت Split-Brain یا افشای داده‌های سروری نشوند.

---

## ۱. منبع حقیقت فرانت‌اند عمومی (GitHub Pages)

- **شاخهٔ مرجع:** `main`
- **محدودهٔ معتبر روی `main`:** درخت `docs/`، تست‌های قرارداد رابط کاربری در `tests/`، و ورک‌فلوهای بررسی/انتشار فرانت‌اند (`.github/workflows/publish-frontend-from-deploy.yml` و `.github/workflows/purchase-ui-regression.yml`).

## ۲. منبع حقیقت بک‌اند، پایگاه داده و ظرفیت زندهٔ سنجش

- **شاخهٔ مرجع:** `deploy/liara-commercial-sandbox`
- **محدودهٔ معتبر روی `deploy`:** runtime سرور لیارا (`main_v2.py`، `requirements.txt` زنده)، مدل‌ها و مهاجرت‌های `alembic/`، سرویس‌های احراز هویت و پرداخت/اعتبار، موتور و loaderهای پذیرش سنجش، و فایل‌های ظرفیت زنده (**۱۴۰۵** و سوابق تحصیلی).

## ۳. همگام‌سازی‌های ممنوع (خط قرمز کپی کور)

- **از `main` به `deploy/liara-commercial-sandbox` ممنوع:** کپی کور فایل‌های پایتون بک‌اند یا `requirements.txt` از `main` به `deploy` مطلقاً ممنوع است (نسخه‌های پایتون ریشهٔ `main` قدیمی‌اند و باعث شکست سرویس زنده می‌شوند).
- **از `deploy/liara-commercial-sandbox` به `main` ممنوع:** کپی کور درخت `docs/` فرانت‌اند یا هرگونه فایل JSON ظرفیت/دفترچهٔ سنجش از `deploy` به `main` (انتشار عمومی Pages) مطلقاً ممنوع است.

## ۴. سیاست داده‌های ظرفیت سنجش و گارد خودکار CI

- انتشار هرگونه فایل خام دفترچه یا ظرفیت سنجش (`docs/data/sanjesh_*.json`، `docs/**/sanjesh_*_programs.json`، `docs/**/sanjesh_record_capacity_full.json`) در GitHub Pages عمومی مجاز نیست؛ این داده‌ها صرفاً روی سرور / شاخهٔ `deploy/liara-commercial-sandbox` نگهداری می‌شوند.
- گارد خودکار `scripts/ci/check_no_public_sanjesh_dumps.sh` در `.github/workflows/publish-frontend-from-deploy.yml` (هر دو مرحلهٔ `verify` و `publish` پیش از آپلود آرتیفکت؛ مستقر در گام‌های ۱ و ۲) هر PR یا انتشاری را که حاوی این الگوها باشد مسدود می‌کند.

## ۵. حاکمیت تغییرات موتور، وزن‌ها و Hybrid و حفاظت `main`

- هرگونه تغییر در موتور امتیازدهی (`dark_horse_engine_v2.py`)، وزن‌ها/کالیبراسیون علمی، یا لایهٔ `Hybrid / Cutover` صرفاً با دستور صریح ناظر و در PR مجزا مجاز است.
- شاخهٔ `main` نیازمند Pull Request، عبور چک‌های الزامی (`Publish frontend from main / verify` و `Purchase UI regression`) و ممنوعیت `force-push` است.

## ۶. بازیابی فایل‌های حذف‌شدهٔ ۱۴۰۴ از تاریخچهٔ Git

پنج فایل حذف‌شدهٔ دفترچهٔ ۱۴۰۴ از `docs/data/` روی `main` (حذف‌شده در merge commit به شناسهٔ `984b90bf154e9bddabe96ae3f836f7bc3d65e2b3`) در تاریخچهٔ Git روی commit مرجع **`bb7da0d907671dc8393f4f333d3e8779a5e2e5e9`** (پیش از `984b90bf`) دست‌نخورده باقی مانده‌اند و در صورت نیاز با دستور زیر قابل بازیابی‌اند:

```bash
git checkout bb7da0d907671dc8393f4f333d3e8779a5e2e5e9 -- \
  docs/data/sanjesh_riazi_1404_programs.json \
  docs/data/sanjesh_tajrobi_1404_programs.json \
  docs/data/sanjesh_ensani_1404_programs.json \
  docs/data/sanjesh_honar_1404_programs.json \
  docs/data/sanjesh_zaban_1404_programs.json
```

---

## مراجع مرتبط

- گام ۱ (حذف ۵ فایل خام ۱۴۰۴ از انتشار عمومی GitHub Pages): [PR #274](https://github.com/arad2000/dark-horse-v2-/pull/274) (`984b90bf154e9bddabe96ae3f836f7bc3d65e2b3`)
- گام ۲ (گارد خودکار CI ضدِ بازگشت فایل‌های ظرفیت سنجش به `docs/`): [PR #275](https://github.com/arad2000/dark-horse-v2-/pull/275) (`36b3c95fef9aed4642c02129ef104115b9fedb2f`)
