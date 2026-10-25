# هم‌ترازی پیشنهادی pool کد با high_school_branch — فقط ۱۷۲، ۲۱۹، ۲۲۰

**وضعیت: Draft فقط سند. هیچ کد یا JSON عملیاتی تغییر نکرده است.** قبل/بعد زیر دو آبجکت در حافظه‌اند، نه وضعیت deploy پس از اصلاح. این مرحله هیچ میانگین S/V، موتور یا آزمون امتیازدهی اجرا نکرد. Merge یا فعال‌سازی انجام نشده است.

## ۱. مبنای قطعی و محدوده
- تاریخ 2026-10-25؛ HEAD deploy: **`dd76083836c80732caf33c38b3d59b837f88c284`**، پس از #303. ابتدا با remote کنترل شد. منابع این گزارش از `git show` همان SHA هستند، نه working tree main.
- عضویت مقصد فقط `high_school_branch` معتبر major فعال است؛ ۲۰۲/۲۰۲ معتبر و خالی ۰. **از overlap برای تعیین/بازنویسی عضویت استفاده نشده**؛ overlap فقط برای تشخیص جای فعلی کدها و گزارش پوشش است.
- نام‌های دقیق موجود: `branch-1 / علوم تجربی`، `branch-2 / ریاضی فیزیک`، `branch-3 / علوم انسانی`، `branch-4 / فنی و حرفه‌ای`. هیچ شاخه‌ای ساخته یا نام‌گذاری مجدد نشد.
- scope بالقوه نسخه داده‌ای فقط `school_branches_v2.json[*].micro_motive_codes` برای همان ۲۱ کد است. **تمام** فیلدهای دیگر branch، از جمله S/V، denominator، name/id/group، version و source_majors_count، و تمام majors/micro/engine/gates باید ثابت بمانند.

## ۲. فیلد قطعی در برابر محل واقعی کدها
|id|نام|high_school_branch فعلی|pool فعلی دارای کدها|پوشش در مقصد فعلی|اقدام پیشنهادی|
|---:|---|---|---|---:|---|
|172|معماری داخلی|ریاضی فیزیک|فنی و حرفه‌ای: ۷/۷؛ سه pool دیگر: ۰/۷|۰/۷|حذف ۷ کد از فنی و حرفه‌ای؛ افزودن همان ۷ به ریاضی فیزیک|
|219|مهندسی فضای سبز|علوم تجربی|ریاضی فیزیک: ۷/۷؛ سه pool دیگر: ۰/۷|۰/۷|حذف ۷ کد از ریاضی فیزیک؛ افزودن همان ۷ به علوم تجربی|
|220|مهندسی مکانیزاسیون کشاورزی|علوم تجربی|ریاضی فیزیک: ۷/۷؛ سه pool دیگر: ۰/۷|۰/۷|حذف ۷ کد از ریاضی فیزیک؛ افزودن همان ۷ به علوم تجربی|

### کدهای دقیق جابه‌جایی
|id|کدها با ترتیب اصلی major|مقصد یکتا در پیشنهاد|
|---:|---|---|
|172|`INTARCH-001, INTARCH-002, INTARCH-003, INTARCH-004, INTARCH-005, INTARCH-006, INTARCH-007`|ریاضی فیزیک|
|219|`LAND-001, LAND-002, LAND-003, LAND-004, LAND-005, LAND-006, LAND-007`|علوم تجربی|
|220|`AGMECH-001, AGMECH-002, AGMECH-003, AGMECH-004, AGMECH-005, AGMECH-006, AGMECH-007`|علوم تجربی|

## ۳. چرا حذف از pool قبلی در این پیشنهاد موجه است؟
- هر ۲۱ کد در catalog واقعی میکروها وجود دارد. مالکیت در **تمام ۲۳۰ major** بررسی شد: هر کد فقط متعلق به همان id هدف است؛ هیچ major دیگرِ فعال یا غیرفعال برای نگه داشتن آن در pool قبلی شاهد مشترک ایجاد نمی‌کند.
- در snapshot فعلی، هر دستهٔ هفت‌تایی فقط در یک pool قدیمی است؛ هیچ عضویت چندشاخه‌ای موجود یا partial coverage برای این سه مورد نیست. هیچ کد مشترک با idهای دیگر یا کد بی‌catalog منتقل/حذف نمی‌شود.
- تاریخچه شناخته‌شده c030bf8، نگاشت قدیمی هنر به فنی و مهندسی کشاورزی به ریاضی را توضیح می‌دهد؛ #303 فیلدهای مقصد را صریحاً مصوب کرد: ۱۷۲ ریاضی، ۲۱۹/۲۲۰ تجربی. برای دو مورد کشاورزی، high_school_branch قبل از #303 null بود؛ «عضویت قدیمی» در اینجا جاگذاری کدهاست، نه ادعای وجود فیلد قدیمی ریاضی.
- این شواهد برای پیشنهاد هم‌ترازی با دستور عضویتِ یکتا کافی است؛ از آن نتیجه نمی‌گیریم که پذیرش دانشگاهی یا واقعیت آموزشی تک‌مسیره است. اگر ناظر قصد pool چندمسیرهٔ مستقل از membership را دارد، باید این سیاست را جدا مصوب کند؛ این گزارش چنین معنایی اختراع نمی‌کند.

## ۴. پوشش کد per branch قبل/بعد
«معتبر» در جدول همان semantics واقعی `_active_branch_code_set` است: strip/lower، اشتراک با catalog در صورت غیرتهی بودن، وگرنه fallback به raw. تابع موتور فقط خوانده شد؛ در اسکریپت همین set logic تکرار شده و هیچ کلاس engine اجرا نشده. همه مخزن‌های این snapshot اشتراک غیرتهی دارند.
|branch|raw قبل→بعد|unique قبل→بعد|catalog-filtered قبل→بعد|کد افزوده|کد حذف‌شده|Δ خالص|
|---|---:|---:|---:|---:|---:|---:|
|علوم تجربی|378→392|378→392|371→385|14|0|+14|
|ریاضی فیزیک|420→413|420→413|420→413|7|14|-7|
|علوم انسانی|413→413|413→413|413→413|0|0|+0|
|فنی و حرفه‌ای|189→182|189→182|189→182|0|7|-7|

### پوشش اعضای قطعیِ همان branch، نه هر major حاضر در pool
|branch|اعضای قطعی|کدهای اعضای قطعی|کد عضو پوشیده قبل→بعد|عضو با پوشش کامل قبل→بعد|کد نامنطبق با عضویت در pool قبل→بعد|
|---|---:|---:|---:|---|---:|
|علوم تجربی|56|385|371→385|54/56→56/56|0→0|
|ریاضی فیزیک|61|413|406→413|60/61→61/61|14→0|
|علوم انسانی|59|413|413→413|59/59→59/59|0→0|
|فنی و حرفه‌ای|26|182|182→182|26/26→26/26|7→0|

- پوشش کامل اعضای قطعی در pool مقصد: **قبل ۱۹۹/۲۰۲؛ پس از پیشنهاد ۲۰۲/۲۰۲**. کد متعلق به عضو مصوب ولی بیرون pool خودش: **۲۱→۰**. فهرست عضوِ باقی‌ماندهٔ ناقص در پیشنهاد: `[]`.
- تعداد کل raw: **۱۴۰۰→۱۴۰۰**؛ اجتماع catalog-filtered: **۱۳۹۳→۱۳۹۳**؛ overlap دو‌به‌دوی poolهای معتبر: **۰→۰**. هیچ کد در کل مخزن گم نمی‌شود؛ فقط **۲۱ حذف از مبدأ + ۲۱ افزودن به مقصد** داریم، نه ۴۲ کد یکتای تازه.
- ۷ کد BIOTM-001..007 در raw تجربی موجود ولی خارج catalogند و همچنان فیلتر می‌شوند. raw تجربی پس از پیشنهاد ۳۹۲ و معتبر ۳۸۵ است؛ آن ۷ مورد پاکسازی نشده‌اند. این موضوع خارج scope سه major است.
- `source_majors_count` در هر دو حالت **۵۴/۶۲/۵۹/۲۷** باقی می‌ماند؛ تعداد قطعی اعضا **۵۶/۶۱/۵۹/۲۶** است. metadata میراثی نه ورودی این پیشنهاد است و نه خودکار اصلاح می‌شود. اگر ناظر تغییر metadata را خواست، scope آن باید جدا تأیید شود. API count مشتق از raw codes است، پس در اجرای آینده countهای نمایش‌داده‌شده ممکن است ۳۷۸→۳۹۲، ۴۲۰→۴۱۳، ۴۱۳→۴۱۳ و ۱۸۹→۱۸۲ شوند؛ این‌ها تعداد major نیستند.

## ۵. روش و کنترل‌های اجراشده در حافظه
1. خواندن snapshot pinned و ساخت deepcopy branchها. برای هر id هدف، مقصد فقط از high_school_branch؛ remove فقط کدهای همان major از branchهای غیرمقصد، append فقط missingها به مقصد با ترتیب اصلی major.
2. ترتیب تمام کدهای دیگر در هر آرایه حفظ می‌شود. در هیچ branch کد تکراری ایجاد نمی‌شود. normalized case/whitespace برای تشخیص برابری استفاده می‌شود، نه بازنویسی خود رشته‌های کد.
3. assert دقیق: همه فیلدها جز micro_motive_codes در هر چهار branch برابر؛ همه عناصر codes خارج ۲۱ مورد در ترتیب اصلی برابر؛ هر دسته هفت‌تایی در دقیقاً یک branch و فقط مقصد مصوب است.
4. assert کل catalog partition، عدم overlap، عدم orphan جدید، پوشش کامل همه ۲۰۲ عضو و عدم تغییر majors/baseline در حافظه. hash فایل‌های runtime محلی قبل/بعد ثابت (مسیر غایب باید غایب بماند).
5. این‌ها آزمون مجموعه/metadata هستند؛ هیچ اجرای engine، discover، score، میانگین Strategy/Value، یا تست مرورگر/CI در این مرحله انجام نشده. از کنترل‌های مجموعه‌ای ادعای ثبات score شاخه نمی‌کنیم: در اجرای واقعی M جرقه‌های جابه‌جاشده باید به مقصد جدید منتقل شود.
- checksum آبجکت پیشنهادیِ کامل در حافظه (canonical JSON؛ نه فایل تولیدشده): `e2b996b3a449ca20007e059c6e7282ea40695e328fdfe3a03066c5289906975c`.

## ۶. حکم و مرحله بعد
**Go برای تأیید ناظر روی این طرح محدود؛ No-Go برای write/Merge خودکار.** خروجی انتخاب‌شدهٔ این نوبت فقط سند است. برای هر سه major، پیشنهاد انتقال هفت کد به مقصد مصوب، با مالکیت انحصاری و بدون حذف پوشش کل، کنترل‌های مجموعه‌ای را پاس کرد.
- اگر ناظر اعمال را مجاز کرد، PR اجرایی جدا روی deploy با تنها تغییر runtime `school_branches_v2.json` و فقط آرایهٔ micro_motive_codes این ۲۱ کد؛ هیچ S/V، metadata/count/version، majors، micro، engine یا gate نباید همراهش تغییر کند. قبل از write، HEAD تازه pin و همین بررسی بازپخش شود؛ اگر ownership/pool عوض شد، توقف و گزارش delta.
- پذیرش PR اجرایی آینده: مجموعهٔ کدهای diff دقیقاً همین ۲۱ کد، ۲۱ حذف و ۲۱ افزودن، انتقال ۱۷۲ فنی→ریاضی و ۲۱۹/۲۲۰ ریاضی→تجربی، کامل‌شدن پوشش مقصد همه ۲۰۲ عضو و hash برابری تمام فیلدهای ممنوع. آزمون M و قرارداد نمایش آن نسخه باید با مجوز اجرای مربوط گزارش شود؛ گیت قرمز دور زده نشود.
- rollback آینده: restore فقط آرایه‌های codes از blob مبنای همان PR و reload instance/cache طبق روال مصوب؛ S/V و majors/engine revert نشوند.
- این طرح فقط مانع pool/membership گزارش PHASE0C را در **پیشنهاد حافظه‌ای** برطرف می‌کند؛ مشکل informative V و کارت‌های partial-V همان گزارش را حل نمی‌کند و حکم No-Go آن candidate میانگین را خودکار به Go تبدیل نمی‌کند. هیچ آزمایش میانگین مجدد یا اجرای وزن جدید آغاز نشد.
- هیچ Merge/deploy/live-green ادعا نمی‌شود؛ وضعیت واقعی فایل deploy همچنان همان before است.

## ۷. اثر انگشت منابع
|مسیر در SHA مبنا|SHA-256|
|---|---|
|`school_branches_v2.json`|`49821a86476dc9d5bb2d8fee68048be83121aa74bc2bd03715b9c1c73ff88412`|
|`majors_database_v2.json`|`0f416e69e817666ed0b4a37d28b63ec5afa5f448d794aedbe4edf466fa4b01c8`|
|`docs/data/micro_motives.json`|`34f04251e4d6a7b09e18c117c6af9e5670464dd60047fff5407d89a1fa63edde`|
|`micro_motives.json`|`34f04251e4d6a7b09e18c117c6af9e5670464dd60047fff5407d89a1fa63edde`|
|`dark_horse_engine_v2.py`|`8ce3ef7220c008bd910d85069c2627b44eceebbaf596eea7c0f76bb2481c7168`|

## ۸. اسکریپت دقیق فقط‌خواندنی
اجرا با Python stdlib از ریشه repo دارای SHA مبنا. اسکریپت فقط داده می‌خواند و summary به stdout می‌دهد؛ هیچ فایل codes یا candidate روی دیسک نمی‌نویسد، engine را import/اجرا نمی‌کند و به فایل‌های موقت مراحل قبل وابسته نیست.
```python
# Codes-only proposal in memory. No engine execution, averages, or data writes.
import copy, hashlib, json, subprocess
from pathlib import Path
BASE='dd76083836c80732caf33c38b3d59b837f88c284'
TARGETS=[172,219,220]
PATHS=['school_branches_v2.json','majors_database_v2.json','docs/data/micro_motives.json','micro_motives.json','dark_horse_engine_v2.py']
def disk_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None
local_before={p:disk_hash(p) for p in PATHS}
raw={p:subprocess.check_output(['git','show',BASE+':'+p]) for p in PATHS}
branches=json.loads(raw['school_branches_v2.json'])
majors=json.loads(raw['majors_database_v2.json'])
catalog=json.loads(raw['docs/data/micro_motives.json'])
assert raw['micro_motives.json']==raw['docs/data/micro_motives.json']
def norm(v):return str(v).strip().lower()
def codes(v):return {norm(c) for c in v if c and norm(c)}
cat={norm(m['code']) for m in catalog}
def active(b):
    s=codes(b['micro_motive_codes']);f=s&cat
    return f if f else s  # actual engine filtering semantics, no execution
by_id={m['id']:m for m in majors}
active_majors=[m for m in majors if m['motive_driven'] is True]
names=[b['name'] for b in branches]
assert len(active_majors)==202 and all(m.get('high_school_branch') in names for m in active_majors)
owners={c:[m['id'] for m in majors if c in codes(m['micro_motive_codes'])] for i in TARGETS for c in codes(by_id[i]['micro_motive_codes'])}
plan=[]
for mid in TARGETS:
    m=by_id[mid];cs=codes(m['micro_motive_codes']);target=m['high_school_branch']
    assert m['motive_driven'] and len(cs)==7 and cs<=cat
    assert all(owners[c]==[mid] for c in cs),('shared target codes',mid)
    hits={b['name']:sorted(cs & codes(b['micro_motive_codes'])) for b in branches if cs & codes(b['micro_motive_codes'])}
    assert len(hits)==1 and len(next(iter(hits.values())))==7 and target not in hits
    plan.append(dict(id=mid,name=m['name'],target=target,codes=m['micro_motive_codes'],before=hits))
# Preserve ordering of untouched codes, append in each major's existing order.
proposal=copy.deepcopy(branches)
for p in plan:
    cs=codes(p['codes'])
    for b in proposal:
        if b['name']!=p['target']:
            b['micro_motive_codes']=[c for c in b['micro_motive_codes'] if norm(c) not in cs]
        else:
            have=codes(b['micro_motive_codes'])
            b['micro_motive_codes'] += [c for c in p['codes'] if norm(c) not in have]
allowed=set().union(*(codes(p['codes']) for p in plan))
assert len(allowed)==21
for a,b in zip(branches,proposal):
    assert {k:v for k,v in a.items() if k!='micro_motive_codes'} == {k:v for k,v in b.items() if k!='micro_motive_codes'}
    assert [c for c in a['micro_motive_codes'] if norm(c) not in allowed] == [c for c in b['micro_motive_codes'] if norm(c) not in allowed]
    assert len(b['micro_motive_codes'])==len(codes(b['micro_motive_codes']))
for p in plan:
    assert [b['name'] for b in proposal if codes(p['codes']) & codes(b['micro_motive_codes'])]==[p['target']]
    assert codes(p['codes'])<=active(next(b for b in proposal if b['name']==p['target']))

def stats(bs):
    out={}
    for b in bs:
        pool=active(b);members=[m for m in active_majors if m['high_school_branch']==b['name']]
        member_codes=set().union(*(codes(m['micro_motive_codes']) for m in members))
        out[b['name']]=dict(id=b['id'],raw=len(b['micro_motive_codes']),unique=len(codes(b['micro_motive_codes'])),filtered=len(pool),
            invalid=sorted(codes(b['micro_motive_codes'])-cat),members=len(members),member_codes=len(member_codes),
            covered_member_codes=len(member_codes&pool),missing=sorted(member_codes-pool),extra=sorted(pool-member_codes),
            fully_covered_members=sum(codes(m['micro_motive_codes'])<=pool for m in members),source_majors_count=b.get('source_majors_count'))
    return out
before,after=stats(branches),stats(proposal)
assert [after[n]['raw'] for n in names]==[392,413,413,182]
assert [after[n]['filtered'] for n in names]==[385,413,413,182]
assert all(not v['missing'] and not v['extra'] and v['fully_covered_members']==v['members'] for v in after.values())
for bs in [branches,proposal]:
    pools=[active(b) for b in bs]
    assert set().union(*pools)==cat and len(cat)==1393
    assert sum(map(len,pools))==1393  # disjoint partition
    assert sum(len(b['micro_motive_codes']) for b in bs)==1400
    assert len(next(b for b in bs if b['id']=='branch-1')['micro_motive_codes'])-len(active(next(b for b in bs if b['id']=='branch-1')))==7
assert majors==json.loads(raw['majors_database_v2.json'])
assert branches==json.loads(raw['school_branches_v2.json'])
assert local_before=={p:disk_hash(p) for p in PATHS}
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
summary=dict(base=BASE,targets=TARGETS,plan=plan,before=before,after=after,transferred_codes=21,
    removals=21,additions=21,catalog=1393,raw_total=1400,proposal_sha256=digest(proposal),
    input_hashes={p:hashlib.sha256(v).hexdigest() for p,v in raw.items()},
    remaining_missing_members_after=[],other_fields_unchanged=True,local_runtime_files_unchanged=True)
if __name__=='__main__':print(json.dumps(summary,ensure_ascii=False,indent=2))
```
