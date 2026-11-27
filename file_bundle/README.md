# بستهٔ فایل‌های اصلاحی

این پوشه فقط برای انتقال فایل به گوشی است. **کد برنامه نیست** و روی سرویس اثری ندارد.

## چطور استفاده شود

۱. آدرس را در مرورگر باز کنید:
   `https://arad2000.github.io/dark-horse-v2-/file_bundle/`

۲. دکمهٔ پایین صفحه: **«دانلود بستهٔ کامل (ZIP)»**

۳. فایل `referral-files.zip` را در GitHub باز کنید و محتوایش را بریزید روی شاخهٔ
   `deploy/liara-commercial-sandbox`.

## فایل داخل ZIP

```
admin_router.py
billing_credit_service.py
billing_models.py
commercial_api.py
phone_verification_service.py
referral_commission_service.py
referral_service.py
test_commercial_api.py
test_quota_health_migration.py
alembic/versions/0012_referral_attribution.py
alembic/versions/0013_referral_ownership.py
alembic/versions/0014_signup_attribution.py
alembic/versions/0015_self_service_codes.py
docs/admin_referrals.html
docs/auth_api_client.js
docs/commercial_ui.js
docs/index.html
```

## چرا این روش

GitHub Pages از شاخهٔ `main` منتشر می‌شود و `deploy` فرانت‌اند قدیمی‌تری دارد.
این پوشه در `main` است، پس صفحه در دسترس است؛ ولی محتوایش چیزی را روی سرویس
عوض نمی‌کند.
