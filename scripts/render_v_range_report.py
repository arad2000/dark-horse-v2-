"""Render the supervisor's scientific review from the reproducible JSON audit."""
import ast
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
r = json.loads((ROOT / 'docs/V_RANGE_REGRESSION_REPORT.json').read_text())
old = subprocess.check_output(['git', 'show', r['baseline_sha'] + ':dark_horse_engine_v2.py'], text=True)
new = (ROOT / 'dark_horse_engine_v2.py').read_text()


def fn(source, name):
    node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == name)
    return node, '\n'.join(source.splitlines()[node.lineno-1:node.end_lineno])


def pct(x):
    return 'null' if x is None else f'{100*x:.2f}'


def yn(x):
    return 'بله' if x else 'خیر'


out = ['# بازبینی علمی V — برد، رگرسیون و مصرف‌کننده', '',
       '## وضعیت و مبنا', '',
       f"مبنای منبع deploy: `{r['baseline_sha']}`. نسخهٔ بعد، working tree همین شاخه است؛ هنوز مستقر نیست.",
       'منظور از «قبل» کد Git شاخهٔ استقرار است، نه مشاهدهٔ API زنده. دسترسی مستقیم زنده از این محیط غیرقابل تأیید است.',
       'Merge و redeploy مجاز نیستند. ساخت Draft صرفاً برای بازبینی است و به معنی Go انتشار نیست.', '',
       '## ۱. مرجع داده', '',
       '۲۳۰ = ۱۶۰ اولیه + ۷۰ مدخل جدید؛ ۲۰۲ فعال = ۲۳۰ − ۲۸ = ۱۶۰ + ۴۲.',
       'عبارت «۱۶۰+۴۲−۲۸» نادرست است: ۴۲ از قبل فقط فعال‌ها را می‌شمارد. چهار شاخه مستقل‌اند؛ دامنه ۲۰۶ است، نه ۲۰۲×۴.',
       'فایل hybrid غایب مبنای این ممیزی نیست؛ هیچ ادعایی دربارهٔ تطبیق با آن نداریم.', '',
       '| فایل | len | MD5 فعلی = مبنا | SHA-256 فعلی = مبنا |', '|---|---:|---|---|']
for d in r['database_identity']:
    assert d['byte_identical'] and d['sha256_current'] == d['sha256_baseline']
    out.append(f"| {d['file']} | {d['length']} | `{d['md5_current']}` | `{d['sha256_current']}` |")
out += ['', 'مقایسهٔ بایت‌به‌بایت نیز برابر است. این هویت فایل در Git است، نه اثبات فایل بارگذاری‌شده در runtime زنده.', '',
        '## ۲. استخراج عینی فرمول', '',
        'قدیم: `V_old = (1/n) Σ [w_chosen / max(wA,wB)]`؛ زوج با max=0 سهم صفر می‌گرفت و در n شمرده می‌شد.',
        'جدید: `V_new = Σ(w_chosen − min(wA,wB)) / Σ(max(wA,wB) − min(wA,wB))` روی پاسخ‌های معتبر با range≥0.02.', '']
for label, source, names in [('قبل، deploy مبنا', old, ['_pairwise_value_score', '_compute_v_score']),
                             ('بعد، کاندیدای منتشرنشده', new, ['_compute_v_result', '_compute_v_score'])]:
    for name in names:
        node, code = fn(source, name)
        out += [f'### {label}: `{name}` — dark_horse_engine_v2.py:{node.lineno}–{node.end_lineno}', '', '```python', code, '```', '']
out += ['### زوج برابر، نزدیک و مخرج صفر', '',
        '- قبل: زوج مثبت برابر حتی با انتخاب دلخواه ۱ می‌داد؛ برای max=0 سهم صفر بود؛ ε وجود نداشت.',
        '- بعد: `V_EPSILON=0.02`؛ اختلاف به ۱۲ رقم اعشار گرد و سپس مقایسه می‌شود. کمتر از ۰٫۰۲ حذف؛ دقیقاً ۰٫۰۲ حفظ.',
        '- زوج برابر از صورت و مخرج حذف می‌شود. اگر هیچ زوج واجد تمایزی باقی نماند score=null است؛ نه صفر.',
        '- هر زوج پذیرفته‌شده حداقل ۰٫۰۲ به مخرج می‌دهد؛ بنابراین مخرج مثبتِ خیلی کوچک‌تر از ε نداریم.',
        '- EPSILON سیاست حذف تمایز ضعیف است، نه آستانهٔ اثبات‌شدهٔ روان‌سنجی. score در [0,1] محدود می‌شود.',
        '- با دادهٔ معتبر، مخرج مثبت: کمینه=۰، بیشینه=۱ و امید انتخاب مستقل ۵۰/۵۰ برابر ۰٫۵؛ واریانس رشته‌ها لزوماً برابر نیست.',
        '- پاسخ خالی/نامعتبر حذف، تکراری یک‌بار، و انتخاب متناقض A/B یک دوراهی باطل می‌شود. پوشش در امتیاز ضرب نمی‌شود.', '',
        '### همان مثال zahra_synthetic', '',
        '`seed=3`؛ طراحی گرافیک #140: V قدیم 66.99% و جدید 10.87%؛ Total از 43.4 به 26.6.',
        '۱۴ زوج متمایز: سه انتخاب بیشینه (Q3B,Q6B,Q13A) و یازده کمینه؛ Q5=(0.55,0.55) دقیقاً برابر است.',
        'صورت = 0.15+0.05+0.30 = 0.50؛ مخرج = 4.60؛ V=0.50/4.60. null یا حذف زوج نزدیک علت خروج نیست.',
        'در این مثال خاموش‌کردن ε هم امتیاز جدید را عوض نمی‌کند؛ افت فقط از 0.30×ΔV است.', '',
        '## ۳. جدول چندپروفایلی', '',
        'همهٔ پروفایل‌ها مصنوعی‌اند. جدول زیر یک رشتهٔ کانونی از هر پروفایل است؛ هر پروفایل روی **تمام ۲۰۲ رشته** اجرا شده است.',
        'جدول کامل ۱۸×۲۰۲=۳۶۳۶ ردیف در `V_RANGE_MULTIPROFILE_ROWS.csv` و JSON موجود است؛ ورودی دقیق و seed هر پروفایل ثبت شده‌اند.',
        'متعادل یعنی الگوی پاسخ A/B متناوب (۸/۷)، نه تضمین امتیاز برابر برای رشته‌ها. قوی روی قطب یعنی همه A یا همه B، نه الزاماً V=۱.',
        'اعداد M/S/V درصد و Total با گردکردن یک‌رقمی فعلی موتور است. عبور از ۳۰ جدا از شرط M≥۱۵ گزارش می‌شود.', '',
        '| پروفایل / seed | major_id | name | M قبل→بعد | S قبل→بعد | V قبل→بعد | Total قبل→بعد | ≥30→<30 | null |',
        '|---|---:|---|---:|---:|---:|---:|---|---|']
for f in r['fixtures']:
    row = next(x for x in f['all_major_rows'] if x['id'] == f['focus_major_id'])
    out.append(f"| {f['label']} / {f['seed']} | {row['id']} | {row['name']} | {pct(row['m_before'])}→{pct(row['m_after'])} | {pct(row['s_before'])}→{pct(row['s_after'])} | {pct(row['v_before'])}→{pct(row['v_after'])} | {row['before']}→{row['after'] if row['after'] is not None else 'null'} | {yn(row['cross_down'])} | {yn(row['null'])} |")
out += ['', '### جمع آماری روی تمام رشته‌ها، به تفکیک پروفایل', '',
        '| پروفایل | تعداد رشته با abs(ΔV)>20 نقطه | ≥30→<30 بدون شرط M | <30→≥30 بدون شرط M | ≥30→<30 با M≥15 | معکوس با M≥15 | null |',
        '|---|---:|---:|---:|---:|---:|---:|']
for f in r['fixtures']:
    c=f['counts']
    out.append(f"| {f['label']} | {c['delta_v_gt20']} | {c['cross_down']} | {c['cross_up']} | {c['eligible_cross_down']} | {c['eligible_cross_up']} | {c['null']} |")
a=r['aggregate_counts']
out += ['', f"مجموع رخدادهای رشته–پروفایل: abs(ΔV)>20: **{a['delta_v_gt20']}**؛ عبور نزولی عددی: **{a['cross_down']}**؛ صعودی: **{a['cross_up']}**.",
        f"تعداد رشتهٔ یکتا با abs(ΔV)>20 در حداقل یک پروفایل: **{r['unique_majors_delta_v_gt20']}**.",
        f"عبور واقعی با شرط M≥15: نزولی **{a['eligible_cross_down']}**، صعودی **{a['eligible_cross_up']}**.",
        f"null: **{a['null']}**، همگی در پروفایل کنترلِ بدون پاسخ V؛ در ۱۷ پروفایل دارای پاسخ کامل هیچ رشته‌ای null نشد.",
        'در کنترل بدون پاسخ، V قدیم صفر بود؛ Total جدید null است و عبور عددی محسوب نمی‌شود.',
        'بیشتر عبورهای عددیِ بدون شرط M مربوط به رشته‌هایی است که از قبل واجد شرط نمایش نبودند؛ این دو شمارش نباید خلط شوند.', '',
        f"M و S قبل/بعد دقیقاً برابر: `{r['ms_parity']}`؛ SHA-256 مشترک `{r['ms_after_sha256']}`.",
        'AST توابع `_compute_branch_m_score` و `_compute_s_score` نسبت به مبنا بدون تغییر است؛ pool_scale و فیلتر شاخه تغییر نکرده‌اند.', '',
        '## ۴. قرارداد null و دروازهٔ مصرف‌کننده', '',
        '- API: نتایج null جدا از sort و persistence عددی؛ best_branch نباید به مدخل محاسبه‌ناپذیر اشاره کند.',
        '- API: وضعیت، value_assessment، coverage و method.version در پاسخ حفظ می‌شوند.',
        '- UI: مدخل محاسبه‌ناپذیر خارج از رتبه‌بندی، با «فاقد شواهد تمایزبخش» جدا از «اطلاعات ناکافی برای محاسبهٔ امتیاز».',
        '- UI: null به صفر یا درصد تبدیل نمی‌شود؛ صفر واقعی همچنان یک امتیاز معتبر است. پیام شکست آستانه جای وضعیت ناقص نمایش داده نمی‌شود.',
        '- تست Node تابع واقعی displayResults را با DOM sink شبیه‌سازی‌شده اجرا می‌کند؛ آزمون مرورگر واقعی یا layout نیست.',
        '- تست API آداپتور واقعی با موتور مصنوعی و موتور واقعی محلی است؛ DB و authentication در تست mock می‌شوند. وضعیت live اثبات نمی‌شود.', '',
        '## ۵. پیشنهاد محصول — A مشروط، بدون تغییر کد', '',
        'پیشنهاد: آستانهٔ ۳۰٪ در این بسته ثابت بماند (A)، ولی Go انتشار منوط به بازبینی ناظر باشد.',
        'در ۱۷ پروفایل کامل، فقط یک خروج واجد شرط M رخ داد؛ آن مورد یازده انتخاب کمینه و V=10.87% دارد.',
        'این نمونهٔ کوچک مصنوعی پشتوانهٔ انتخاب عدد تازه برای آستانه نیست؛ بنابراین عدد جایگزین بدون دادهٔ واقعی پیشنهاد نمی‌شود.',
        'گزینه C توصیه نمی‌شود: زیر آستانه یک امتیاز محاسبه‌شده است، نه فقدان شواهد؛ تبدیل آن به null قرارداد علمی را مخدوش می‌کند.',
        'تصمیم نهایی محصول و استقرار فقط با ناظر؛ هیچ آستانه‌ای در کد تغییر نکرده است.', '',
        '## ۶. بازتولید و گیت نهایی', '', '```bash',
        'python scripts/audit_v_range_norm.py > docs/V_RANGE_REGRESSION_REPORT.json',
        'python scripts/render_v_range_report.py',
        'python -m unittest test_v_range_norm test_engine_psychometrics test_p0_s_score test_v_consumer_contract test_main_api_contract -q',
        'node tests/test_v_null_consumer.js', '```', '',
        '**No-Go برای Merge/استقرار** تا CI کامل Backend و تست‌های V موفق و Go ناظر ثبت شوند.',
        'Draft بازبینی، مجوز Merge یا redeploy نیست. گزارش CI باید به SHA مشخص متصل شود؛ سبز بودن تست محلی جای CI را نمی‌گیرد.']
(ROOT/'docs/V_RANGE_REVIEW_GATE_REPORT.md').write_text('\n'.join(out)+'\n')
fields=['profile','seed','major_id','name','m_before','m_after','s_before','s_after','v_before','v_after','total_before','total_after','cross_down','cross_up','null']
with (ROOT/'docs/V_RANGE_MULTIPROFILE_ROWS.csv').open('w',newline='') as file:
    w=csv.DictWriter(file,fieldnames=fields);w.writeheader()
    for f in r['fixtures']:
        for x in f['all_major_rows']:
            w.writerow({'profile':f['label'],'seed':f['seed'],'major_id':x['id'],'name':x['name'],
                **{k:pct(x[k]) for k in ['m_before','m_after','s_before','s_after','v_before','v_after']},
                'total_before':x['before'],'total_after':x['after'],
                **{k:x[k] for k in ['cross_down','cross_up','null']}})
