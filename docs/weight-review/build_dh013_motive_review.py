#!/usr/bin/env python3
"""Build review-only DH013 artifacts from pinned git blobs; never modify runtime JSON."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = 'a1cdab9cd875bf9e9e01c19debf1e1237f58302b'
DIR = ROOT / 'docs/weight-review'
DRAFT = DIR / 'DH013_BATCH1_161_165_MOTIVE_DRAFT.md'
REPORT = DIR / 'DH013_BATCH1_161_165_MOTIVE_REVIEW.md'
PACKET = DIR / 'DH013_BATCH1_161_165_REVIEW_PACKET.json'
# Content-selected peers, not statistical nearest neighbours. Shared motives are legitimate.
PEERS = {
 'SPORT-001': ('WATER-002', 'تبدیل دادهٔ اندازه‌گیری به تصمیم؛ زمینه متفاوت است، نه لزوماً کشش مستقل.'),
 'SPORT-002': ('SPORT-004', 'دیدن بازخورد تغییر منفرد در برابر آزمودن روش تازه؛ استقلال هنوز احراز نشده.'),
 'SPORT-003': ('PHYSIO-004', 'هر دو کشف اختلال حرکت‌اند؛ درمان/ورزش به‌تنهایی تمایز انگیزشی نیست.'),
 'SPORT-004': ('SPORT-002', 'اشتراک آزمون و نتیجه مشروع است؛ تفاوت شکل آزمون برای استقلال کافی نیست.'),
 'SPORT-005': ('PHYSIO-002', 'تنظیم اختصاصی برای فرد مشترک است؛ پیشگیری و توانبخشی زمینه‌های متفاوت‌اند.'),
 'SPORT-006': ('ARAB-007', 'انتقال نکته و دیدن یادگیری؛ اجرای حرکت با فهم قاعده تفاوت فعالیت دارد.'),
 'SPORT-007': ('PHYSIO-007', 'دیدن تغییر در زمان مشترک است؛ تیم/فرد به‌تنهایی استقلال نمی‌سازد.'),
 'ARCH-001': ('ARCH-004', 'حل قیود پلان و سازگاری اجزای بنا نزدیک‌اند؛ هستهٔ مستقل نیازمند بررسی است.'),
 'ARCH-002': ('ARCHA-002', 'از ترسیم تا تحقق؛ نقشهٔ اجرایی و دیوار واقعی دو مرحلهٔ یک زنجیره‌اند.'),
 'ARCH-003': ('ARCHA-004', 'کاوش نور/حرکت با مدل در برابر حس حجم فیزیکی؛ اشتراک ماکت پذیرفتنی است.'),
 'ARCH-004': ('INTARCH-002', 'سازگاری مصالح و اثر فضایی مشترک؛ اقلیم و سازه قیود اضافه‌اند، نه اثبات استقلال.'),
 'ARCH-005': ('INTARCH-006', 'کشف مشکل استفاده در برابر اصلاح ارگونومی؛ دو مرحلهٔ نزدیک از طراحی انسان‌محور.'),
 'ARCH-006': ('ARCHA-006', 'اصلاح تناسب و بازکاری مشترک؛ از این متن پایداری چندساله استنتاج نمی‌شود.'),
 'ARCH-007': ('INTARCH-007', 'تقریباً همان تحقق منطق طراحی در تجربهٔ واقعی؛ هم‌پوشانی بین‌رشته‌ای را حفظ و بررسی کن.'),
 'TOURISM-001': ('TOURISM-006', 'حل قیود زمان/هزینه در برابر ساخت تجربهٔ تازه؛ یکی لزوماً دیگری را ایجاب نمی‌کند.'),
 'TOURISM-002': ('TOURISM-003', 'کشف ترجیح در گفت‌وگو در برابر تبدیل شناخت مقصد به پیشنهاد؛ ترتیب فرایند متفاوت است.'),
 'TOURISM-003': ('TOUR-001', 'پیشنهاد مقصد و طراحی تور نزدیک‌اند؛ شناخت فرهنگ زمینه است، نه تیپ شخصیتی.'),
 'TOURISM-004': ('TOUR-002', 'حل اختلال فوری اجرایی مشترک؛ تصمیم مستقل بدون کمک در هیچ‌کدام تضمین نشده.'),
 'TOURISM-005': ('TOUR-003', 'مذاکره و توافق هم‌پوشانی قوی دارند؛ تمایز مصنوعی اضافه نشود.'),
 'TOURISM-006': ('TOUR-001', 'تازگی تجربه و تم منحصربه‌فرد نزدیک‌اند؛ تازه‌بودن مقصد مساوی خطرپذیری نیست.'),
 'TOURISM-007': ('TOUR-001', 'رضایت مسافر در هر دو صریح است؛ تکرار بین‌رشته‌ای ممکن است مشروع باشد.'),
 'QURAN-001': ('FIQH-005', 'مقایسهٔ استدلال با حل تعارض نزدیک است؛ کشف تفاوت الزاماً حل تعارض نیست.'),
 'QURAN-002': ('QURAN-004', 'اعتبارسنجی روایت در برابر ساخت پاسخ؛ ارزیابی ورودی و ترکیب نتیجه متمایزند.'),
 'QURAN-003': ('ARAB-001', 'فهم عبارت عربی با تحلیل بلاغت نزدیک است؛ یکی فهم مستقیم معنا و دیگری تحلیل صورت بیان است.'),
 'QURAN-004': ('RELIG-004', 'ترکیب چند منبع مشترک؛ پاسخ به شبهه و پژوهش تطبیقی خروجی‌های متفاوت‌اند.'),
 'QURAN-005': ('QURAN-004', 'سامان‌دادن موضوع در برابر ساخت استدلال؛ دسته‌بندی الزاماً پاسخ‌دادن نیست.'),
 'QURAN-006': ('FIQH-002', 'متن قدیمی و مسئلهٔ تازه مشترک؛ تفسیر و استنباط حکم را یکسان فرض نکن.'),
 'QURAN-007': ('QURAN-001', 'فهم عمیق متن در برابر مقایسهٔ مفسران؛ مکث طولانی شاهد مستقل انزوا نیست.'),
 'WATER-001': ('WW-002', 'مدل فشار شبکه مشترک؛ پیدا کردن اختلال منبع کشش مشخص‌تر است، نه الزاماً مستقل.'),
 'WATER-002': ('SPORT-001', 'داده به تصمیم مشترک؛ اندازه‌گیری محل با آزمون بدنی تفاوت زمینه دارد.'),
 'WATER-003': ('LAND-003', 'طراحی آب/خاک/زهکشی مشترک؛ اشتراک معتبر حفظ شود.'),
 'WATER-004': ('WATER-005', 'کاوش سناریوی مدل در برابر مقایسهٔ آزمایش با پیش‌بینی؛ پرسش و شاهد متفاوت‌اند.'),
 'WATER-005': ('WATER-004', 'آزمایش فیزیکی در برابر سناریوی مدل؛ هر دو می‌توانند کشش آزمون فرضیه داشته باشند.'),
 'WATER-006': ('WW-001', 'کاهش اتلاف و کارکرد شبکه مشترک‌اند؛ پیوستگی رساندن آب با جلوگیری از رسوب هم‌پوشانی مشروع دارد.'),
 'WATER-007': ('WW-006', 'دسترسی واقعی مردم به آب تقریباً مشترک است؛ تمایز ساختگی لازم نیست.'),
}


def blob(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def build():
    paths = ['majors_database_v2.json', 'docs/data/micro_motives.json',
             'docs/data/questions_v2.json', 'value_poles_v2.json',
             'docs/protocols/DH013_MAJOR_WEIGHTING_PROTOCOL.md']
    raw = {p: blob(p) for p in paths}
    majors = json.loads(raw[paths[0]])
    catalog = {m['code']: m['description_fa'] for m in json.loads(raw[paths[1]])}
    layers = json.loads(raw[paths[2]])['layers']
    sq, vq = layers['strategies']['questions'], layers['values']['questions']
    assert len(sq) == 25 and all(len(q['options']) == 5 for q in sq)
    assert len(vq) == 15 and all(len(q['options']) == 2 for q in vq)
    assert {o['code'] for q in vq for o in q['options']} == set(json.loads(raw[paths[3]]))
    selected = [m for m in majors if 161 <= m['id'] <= 165]
    expected = [c for m in selected for c in m['micro_motive_codes']]
    assert len(selected) == 5 and len(expected) == len(set(expected)) == 35
    rows = {}
    for line in DRAFT.read_text().splitlines():
        if not line.startswith('| '):
            continue
        cells = [x.strip() for x in line.strip('|').split('|')]
        if cells[0] not in expected:
            continue
        code, old, new = cells
        assert code not in rows and old == catalog[code] and new
        peer, rationale = PEERS[code]
        rows[code] = {'code': code, 'previous': old, 'proposed': new,
                      'peer_code': peer, 'peer_baseline_text': catalog[peer],
                      'comparison': rationale, 'status': 'DRAFT_NOT_APPROVED'}
    assert set(rows) == set(expected) == set(PEERS)
    owners = {c: [{'id': m['id'], 'name': m['name']} for m in majors
                  if c in m.get('micro_motive_codes', [])] for c in catalog}
    for r in rows.values():
        r['peer_proposed_text'] = rows.get(r['peer_code'], {}).get('proposed')
        r['peer_owners'] = owners[r['peer_code']]
    packet = {'status': 'REVIEW_ONLY_NOT_RUNTIME', 'base_commit': BASE,
              'source_sha256': {p: hashlib.sha256(b).hexdigest() for p, b in raw.items()},
              'draft_sha256': hashlib.sha256(DRAFT.read_bytes()).hexdigest(),
              'independent_reviews_completed': 0,
              'majors': [{'id': m['id'], 'name': m['name'],
                          'motives': [rows[c] for c in m['micro_motive_codes']]} for m in selected],
              'strategy_questions': sq, 'value_questions': vq,
              'value_poles': json.loads(raw[paths[3]])}
    lines = ['# DH013 — بازبینی محتوایی دستهٔ ۱۶۱ تا ۱۶۵', '',
             '**وضعیت: خودبازبینی نویسنده؛ تعداد بازبینی مستقل انجام‌شده: صفر.**', '',
             'این گزارش نزدیکان را بر اساس اشتراک تجربه/فعالیت انتخاب می‌کند، نه فاصلهٔ عددی. '
             'متن کامل نزدیکان و مالکیت کد در بستهٔ JSON همراه ثبت شده است. '
             'هم‌پوشانی بین رشته‌های مرتبط لزوماً ایراد نیست؛ استقلال هفت کارت داخل هر رشته هنوز تأیید نشده است.', '',
             '## اصلاحات این دور', '',
             '- حذف شرط‌های بی‌شاهد دربارهٔ پذیرفتن نتیجهٔ نامطلوب در SPORT-004 و WATER-005.',
             '- بازگرداندن اتصال داده به برنامه در SPORT-001، بدون ساختن کشش تازه برای رابطهٔ پنهان.',
             '- حذف ادعای برتری متن اصلی بر ترجمه در QURAN-003؛ هستهٔ پیشنهادی، لحظهٔ فهم مستقیم عبارت است.',
             '- حذف الزام اختلاف در مذاکره، و حذف شنیدن تعریف مسافر به‌عنوان شرط رضایت.',
             '- بازگرداندن پایداری طراحی در WATER-006 و دامنهٔ مزرعه در WATER-007.', '',
             '## مقایسهٔ محتوایی ۳۵ کارت', '',
             '| کارت | نزدیک محتوایی منتخب | مقایسه و محدودیت |', '|---|---|---|']
    for c in expected:
        r = rows[c]
        lines.append(f"| {c} | {r['peer_code']} | {r['comparison']} |")
    lines += ['', '## تصمیم مرحله‌ای', '',
              '- همهٔ کارت‌ها Draft هستند؛ مقایسهٔ حاضر اثبات روایی یا تأیید مستقل نیست.',
              '- QURAN-003 به لحظهٔ فهم عبارت اصلی و WATER-006 به پیوستگی رساندن آب مشخص شدند؛ تأیید میدانی انجام نشده. '
              'SPORT-002/004 و ARCH-001/004 برای استقلال هسته‌های انگیزشی باز می‌مانند.',
              '- متن‌ها برای عبور از آستانهٔ EQUAL یا کاهش شباهت وزنی تغییر نمی‌کنند.',
              '- هیچ عدد S/V در این مرحله تولید نمی‌شود. پرسش‌نامهٔ کامل زیر فقط بستهٔ آمادهٔ نگاشت شواهد است؛ '
              'وجود آن به معنی تکمیل تصمیم برای ۱۲۵ ردیف راهبردی و ۱۵۰ کلید ارزشی نیست.', '',
              '## پرسش‌های کامل برای مرحلهٔ بعد', '',
              'منبع هر دو لایه: `docs/data/questions_v2.json` در commit مبنا؛ '
              '`value_poles_v2.json` فقط نام قطب‌هاست، نه متن کامل سؤال.', '']
    for group, questions in [('راهبردی', sq), ('ارزشی', vq)]:
        lines += [f'### لایهٔ {group}', '']
        for q in questions:
            lines += [f"#### {q['id']} — {q['question']}", '']
            lines += [f"- {o.get('code', o['index'])}: {o['text']}" for o in q['options']]
            lines.append('')
    return {REPORT: '\n'.join(lines) + '\n',
            PACKET: json.dumps(packet, ensure_ascii=False, indent=2) + '\n'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify artifacts without writing')
    args = parser.parse_args()
    for path, content in build().items():
        if args.check:
            assert path.read_text() == content, f'Stale artifact: {path}'
        else:
            path.write_text(content)
        print(('Verified ' if args.check else 'Wrote ') + str(path.relative_to(ROOT)))
    print('PASS: 5 majors, 35 unique existing codes, 25×5 S options, 15×2 V options; no runtime writes.')
