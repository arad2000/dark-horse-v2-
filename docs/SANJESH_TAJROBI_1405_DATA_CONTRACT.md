# قرارداد داده و Audit — دفترچه تجربی ۱۴۰۵

## دامنه
- سال: ۱۴۰۵
- گروه: tajrobi
- فایل ورودی: docs/data/sanjesh_tajrobi_1405_programs.json
- این سند فقط قرارداد و ممیزی فاز ۰ است.
- در این فاز هیچ Loader، CAPACITY_PATHS، API، UI، scoring، ranking، engine، Hybrid یا majors_database تغییر نمی‌کند.

## ساختار ردیف
فیلدهای الزامی:
- sanjesh_code
- major_name
- campus
- province
- period
- capacity
- admission_type
- note
- page
- year
- group

JSON فعلی علاوه بر این‌ها فیلد gender نیز دارد؛ در فاز ۰ حذف یا بازتعریف نمی‌شود.

## baseline ممیزی
- کل ردیف: ۱۳٬۳۸۵
- کد یکتا: ۱۳٬۳۸۵
- با آزمون: ۴٬۳۳۰
- صرفاً سوابق: ۹٬۰۵۵
- کد خالی: ۰
- کد تکراری: ۰
- period=نامشخص: ۹٬۰۹۶
- استان خالی: ۳۰۷
- محدوده صفحات: ۴۷ تا ۶۵۷
- تعداد صفحات متمایز: ۴۲۹
- سال مشاهده‌شده: ۱۴۰۵
- گروه مشاهده‌شده: tajrobi

## Overlap با ۱۴۰۴
- کد سنجش مشترک: ۱۱٬۶۷۹
- امضای دقیق رشته‌محل مشترک بر اساس major_name + campus + province + period + admission_type: ۷
- ۱۴۰۵ دارای ۹٬۰۳۲ امضای رشته‌محل جدید نسبت به همین کلید در ۱۴۰۴ است.

## Overlap با ظرفیت سوابق
فایل اختیاری موجود: docs/data/sanjesh_record_capacity_full.json
- کل ردیف ظرفیت سوابق: ۸٬۳۵۰
- کد یکتا: ۸٬۳۵۰
- کد مشترک با تجربی ۱۴۰۵: ۸٬۰۱۷
- امضای رشته‌محل مشترک بر اساس major_name + campus + province + period: ۲۲

## قواعد audit
اسکریپت scripts/audit_tajrobi_1405_programs.py:
- ورودی ۱۴۰۵ را از مسیر محلی می‌خواند.
- ۱۴۰۴ و ظرفیت سوابق را در صورت وجود برای overlap می‌خواند.
- کدهای خالی و تکراری، admission_type، period، استان، صفحات، year و group را audit می‌کند.
- وجود فیلدهای قرارداد و چند نوع داده پایه را بررسی می‌کند.
- هیچ JSON را بازسازی یا اصلاح نمی‌کند.
- خروجی audit را در tajrobi_1405_audit_report.json می‌نویسد.

این PR عمداً Loader را به داده ۱۴۰۵ سوییچ نمی‌کند.