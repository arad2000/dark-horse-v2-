# فاز ۳ — بار پله‌ای کوتاه و ایزولهٔ CAPACITY pilot

## حکم و مرز اعتبار

**PASS محدود به smoke بار محلی زیر؛ ظرفیت عملیاتی لیارا / پذیرش SLO پایلوت: BLOCKED (شاهد ناکافی).** این تست ظرفیت رسمی **۱۰۰۰ DAU را اثبات نمی‌کند**؛ ۱۰۰ VU با think time معادل ۱۰۰ POST خام هم‌زمان نیست. سناریوی برنامه‌ریزی ۲۰۰۰ DAU در سند ظرفیت نیز اثبات نشده است. مرجع: `CAPACITY_PILOT_SLO_v1.md` و گزارش‌های فازهای ۱ و ۲ روی main. شرط حداقل ۶۰ دقیقه steady سند SLO با سه پلهٔ دو دقیقه‌ای برآورده نشده است؛ PASS جدول صرفاً موفقیت سناریوی کوتاه اجراشده است، نه تأیید ظرفیت یا SLO تولید.

طبق اطلاع ناظر، **پلن فعلی DB لیارا پایه و بدون backup دستی/خودکار پنل است**. سیاست ارتقا بعد از عبور کاربران/بار از محدودهٔ پایلوت (~هزار) یا پیش از کمپین بزرگ است، نه اکنون. این PR بکاپ تولید را حل نمی‌کند و هیچ پلنی را تغییر نمی‌دهد.

## محیط و ایمنی

| مورد | وضعیت | شاهد / محدودیت |
|---|---|---|
| محل اجرا | LOCAL ISOLATED | sandbox همین جلسه؛ هیچ درخواست بار به production، staging لیارا یا کاربران واقعی ارسال نشد |
| نسخهٔ بک‌اند | pinned | `848ce07297a925bf2a3d84c209f1c95eb2f2bf55` از `deploy/liara-commercial-sandbox`، شامل Merge #367؛ فایل‌های محصول از git archive بدون تغییر اجرا شدند |
| فرانت | NOT RUN | مبنای گزارش/PR روی main پس از #366؛ مرورگر/CDN/SW در بار شرکت نداشتند |
| DB | PASS local | PostgreSQL 16.2 از pgserver 0.1.4؛ کلاستر تازه، Unix socket، Alembic upgrade head تا `0011_otp_request_ip`، نه SQLite/mock |
| سرور | مشخص | یک process/worker Uvicorn، HTTP بدون TLS روی loopback پورت 8133، بدون proxy؛ client و DB روی همان ماشین |
| pool | پیش‌فرض محصول | size=10، max_overflow=10، pool_timeout=30s، pool_pre_ping=true؛ تنظیمات برای سبزشدن تغییر نکردند |
| ماشین | محدود | Linux 6.1.158+، nproc=2؛ سهم CPU و RAM قابل اتکای معادل پلن لیارا معلوم نیست؛ cgroup v2 cpu.max/memory.max در مسیر استاندارد در دسترس نبود |
| CPU/RAM لیارا و مقایسه با near-production | BLOCKED | دسترسی پنل/محیط staging تأییدشده وجود نداشت؛ آمار منابع یا headroom حدس زده نشد |
| تنظیمات محلی | ایزوله | APP_ENV=staging، BILLING_FREE_MODE=false، BILLING_PROVIDER=mock؛ ثابت cutover دست‌نخورده و false |
| داده | مصنوعی | ۱۰۰ user/token/session مصنوعی؛ هرکدام یک entitlement رایگان با موجودی ۱ و یک discovery row مصنوعی ازپیش‌موجود برای مجازبودن save؛ یک major صرفاً fixture در DB ایزوله، نه تغییر مرجع علمی/JSON |
| خروجی حساس | محافظت‌شده | توکن‌ها فقط در حافظه؛ access log خاموش، stdout/stderr اپ دور ریخته شد؛ بدون password/OTP/پاسخ دانش‌آموز/URL دیتابیس در گزارش |
| پایان اجرا | PASS | process بار exit=0؛ finally سرور Uvicorn و کلاستر PostgreSQL را متوقف کرد؛ بررسی process بعد اجرا postgres/uvicorn زنده نشان نداد |

نسخه‌های محیط اجرا: Python 3.11، SQLAlchemy 2.1.6، psycopg 3.3.6، FastAPI 0.162.0، Uvicorn 0.54.0، httpx 0.28.1. این محیط نصب‌شده از requirements است؛ معادل byte-for-byte image لیارا ادعا نمی‌شود.

## مدل بار و توقف

- closed-loop، هر VU حداکثر یک درخواست درحال‌انتظار؛ یک VU به یک user/session مستقل متصل بود. چهار مسیر به ترتیب تکرار شدند: health → token_me → quota → save. سهم هر مسیر تقریباً ۲۵٪ است، **نه مدل اندازه‌گیری‌شدهٔ ترافیک واقعی**.
- آغاز VUها طی یک ثانیه پخش شد؛ پس از هر درخواست think time تصادفی یکنواخت ۰٫۷۵–۱٫۲۵ ثانیه با seed ثابت به ازای VU؛ هر پله پنجرهٔ ارسال ۱۲۰ ثانیه، سپس drain؛ بین پله‌ها ۵ ثانیه مکث و بررسی integrity/error. یک preflight health و یک save خارج از شمارش پیش از بار اجرا شد.
- health: `GET /api/v1/runtime/quota-health`؛ HTTP 200 **و migration_ok=true** بررسی شد؛ این endpoint به‌تنهایی readiness کامل نیست.
- token_me: `GET /api/v1/me` با session صادرشده از تابع واقعی issue_session؛ تست مسیر احراز توکن است، **نه تست hash/password login یا OTP**.
- quota: `GET /api/v1/me/quota`؛ save: `POST /api/v1/me/save-result` با summary کوچک ثابت `{synthetic: true}` روی session خود VU؛ HTTP 200 و saved=true بررسی شد. این تکرار ذخیرهٔ نتیجهٔ ازپیش‌موجود است، نه شروع/محاسبهٔ سفر کامل یا read-result UI.
- زمان‌سنج client monotonic از قبل ارسال تا دریافت کامل پاسخ؛ صف انتظار client/server داخل latency است. timeout=10s؛ شکست/timeout از denominator حذف نمی‌شود، در صورت وقوع مدت تا شکست در samples می‌ماند. nearest-rank برای p50/p95/p99؛ بدون حذف outlier.
- توقف خودکار همان پله: پس از حداقل ۱۰۰ درخواست، نرخ تجمعی هر پاسخ غیر200/transport/timeout/semantic بالاتر از ۱٪. توقف افزایش پله: همان خطا یا هر integrity=false. هیچکدام رخ نداد. توقف integrity در پایان پله بررسی شد، نه پایش پیوستهٔ همهٔ invariants؛ این محدودیت روی production قابل قبول فرض نشده است.
- p95 هر مسیر و هدف آن بین پله‌ها بررسی شد؛ quota و save بسیار پایین‌تر از ۱ ثانیه بودند. آزمون دو پنجرهٔ پنج‌دقیقه‌ای سند در این اجرای کوتاه ممکن نبود. closed-loop ممکن است افت throughput را پشت think time پنهان کند؛ open-loop/saturation/burst آزمایش نشد.

## جدول پله‌ها

p95ها به ترتیب health / token_me / quota / save و همگی **میلی‌ثانیه** هستند. مدت شامل drain است؛ RPS روی مجموع مدت client محاسبه شده است.

| پله | هم‌زمانی هدف | مدت | p95 تقریبی | نرخ خطا | PASS/FAIL/BLOCKED | یادداشت |
|---|---:|---:|---|---|---|---|
| پایه | ۲۰ VU | ۱۲۱٫۱۸s | 7.96 / 8.10 / 9.05 / 13.15 | 0/2387 = 0% | PASS محلی محدود | حدود 19.70 req/s؛ تکمیل save برای ۲۰ session |
| متوسط | ۵۰ VU | ۱۲۱٫۰۹s | 8.13 / 7.85 / 9.23 / 13.30 | 0/5978 = 0% | PASS محلی محدود | حدود 49.37 req/s؛ تکمیل تجمعی ۵۰ session |
| سقف کوتاه پیشنهادی | ۱۰۰ VU | ۱۲۱٫۱۹s | 11.78 / 11.00 / 12.62 / 19.42 | 0/11914 = 0% | PASS محلی محدود | حدود 98.31 req/s؛ تکمیل تجمعی ۱۰۰ session |
| پذیرش ظرفیت واقعی/SLO | — | steady ۶۰ دقیقه اجرا نشد | — | نامعلوم | BLOCKED | محیط معادل لیارا، منابع و مسیر کامل نتیجه/ورود اندازه‌گیری نشده‌اند |

### جزئیات هر مسیر

تمام نمونه‌های جدول HTTP 200 بودند؛ برای **هر ردیف**: 5xx=0، timeout=0، transport=0، 429=0، سایر status غیرمنتظره=0، semantic failure=0. latencyها میلی‌ثانیه‌اند.

| VU | مسیر | n | p50 | p95 | p99 |
|---:|---|---:|---:|---:|---:|
|20|health|603|5.02|7.96|10.59|
|20|token_me|599|4.92|8.10|12.22|
|20|quota|595|5.72|9.05|11.28|
|20|save|590|8.31|13.15|18.18|
|50|health|1514|4.40|8.13|11.38|
|50|token_me|1501|4.31|7.85|12.54|
|50|quota|1486|5.15|9.23|13.40|
|50|save|1477|7.65|13.30|16.64|
|100|health|3018|4.69|11.78|18.58|
|100|token_me|2990|4.73|11.00|17.37|
|100|quota|2963|5.78|12.62|19.18|
|100|save|2943|8.99|19.42|28.87|

## مقایسه با SLO و صحت

| مورد | وضعیت | شاهد |
|---|---|---|
| quota/save ≤۱s و خطای ≤۱٪ | PASS فقط پنجرهٔ محلی | بدترین p95 برابر 19.42ms، صفر خطا؛ نه پذیرش شرط steady سند |
| health/token_me | PASS عملکرد محلی؛ SLO عددی مستقل ندارد | migration_ok=true و HTTP 200؛ token_me معادل login ≤۲s نیست |
| موجودی اعتبار منفی/تغییر ناخواسته | PASS محدود | پس از هر پله، هر ۱۰۰ entitlement موجودی دقیقاً ۱، هیچ موجودی منفی و ledger count=0 |
| double-consume تحت بار | NOT RUN | consume/callback در این workload نیست؛ صفر ledger شاهد عدم مصرف ناخواسته است نه اثبات idempotency تحت بار. نتیجهٔ فاز ۱ جای اجرای بار این دور را نمی‌گیرد |
| ذخیره/صحت داده | PASS محدود | saved=true و شمار completed تجمعی ۲۰/۵۰/۱۰۰؛ بررسی جامع تمام summaryها، مالکیت cross-user یا race همان session در این دور انجام نشد |
| login رمزعبوری ≤۲s | NOT RUN | مسیر توکن انتخاب شد؛ بدون SMS و بدون انبوه OTP؛ CPU هزینهٔ password hash اندازه‌گیری نشد |
| شروع سفر، محاسبه و تحویل نتیجه ≤۳s | NOT RUN | fixture تحلیل ازپیش‌موجود بود؛ discover/branch-discovery و read-result/UI تحت بار نبودند؛ science اجرا یا تغییر داده نشد |
| خانهٔ مرورگر ≤۵s | NOT RUN | مرورگر/شبکهٔ کاربر وجود نداشت |
| پرداخت / SMS / AI | EXCLUDED | هیچ فراخوانی به زرین‌پال، SMS یا Model API خارجی، Coarena یا provider جدید نشد |
| near-production و فشار DB پایهٔ لیارا | BLOCKED | آزمون فقط محلی است؛ هیچ نتیجه‌ای دربارهٔ سلامت کاربران زنده یا منابع لیارا استخراج نمی‌شود |

هیچ اصلاح quota-health دیگری، تغییر engine/weights/majors مرجع/Hybrid/Total/سهمیه/خرید/shuffle، Redis اجباری، ارتقای پلن، deploy یا rollback انجام نشد. ادامهٔ معتبر عملیاتی نیازمند محیط staging تأییدشده و مشاهدهٔ منابع، مسیر کامل سفر با fixture معتبر، توزیع بار واقعی‌تر و steady مطابق سند است؛ این گزارش مجوز خودکار آن عملیات نیست.

## بازتولید ایزوله (غیرمحصولی)

اسکریپت دقیق اجرای این دور در پیوست زیر ثبت شده است؛ SHA256 آن `ccf895af2a55a4160077eb68d29eb16c76f00745a6f3c216e54d7b51356e31fa` است. در یک پوشهٔ scratch **جدید و غیرتولیدی**، source را با `git archive 848ce07297a925bf2a3d84c209f1c95eb2f2bf55` زیر پوشهٔ `source` باز کنید، venv تازهٔ `venv` بسازید، requirements همان source به‌علاوه pgserver==0.1.4 و httpx و uvicorn را نصب و پیوست را به نام `run.py` در کنار source ذخیره کنید. با `venv/bin/python run.py` اجرا شود. نسخه‌های بالا برای تطبیق محیط ثبت شده‌اند. script DB تازهٔ محلی خود را می‌سازد؛ **URL تولید به آن ندهید** و از پوشهٔ دادهٔ موجود استفاده نکنید. پورت 8133 باید آزاد باشد. خروجی `results.json` صرفاً aggregate است؛ pgdata و fixture و dump و venv نباید commit شوند. این پیوست ابزار خودکار production نیست.

### پیوست: harness اجراشده

```python
import os,sys,time,json,asyncio,subprocess,math,random,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'source';sys.path.insert(0,str(SRC));os.chdir(SRC)
import pgserver
server=pgserver.get_server(str(ROOT/'pgdata'))
uri=server.get_uri().replace('postgresql://','postgresql+psycopg://')
os.environ.update(DATABASE_URL=uri,APP_ENV='staging',BILLING_FREE_MODE='false',BILLING_PROVIDER='mock',PYTHONDONTWRITEBYTECODE='1')
proc=None
try:
 r=subprocess.run([sys.executable.replace('python','alembic'),'upgrade','head'],capture_output=True)
 assert r.returncode==0,'migration failed (output withheld)'
 from database import SessionLocal,engine
 from billing_models import User,Entitlement,JourneyCreditConsumption
 from models import UserSession,DiscoveryResult,Major
 from auth_service import issue_session
 from billing_credit_service import ensure_free_entitlement
 from sqlalchemy import select,func
 fixtures=[]
 with SessionLocal() as db:
  major=Major(name='Synthetic load fixture only',group='synthetic',strategy_weights={},value_weights={});db.add(major);db.flush()
  for i in range(100):
   u=User(public_id=f'phase3-{i}',name='Synthetic load',phone=f'load-only-{i}',password_hash=None);db.add(u);db.flush()
   token,_=issue_session(db,u);ensure_free_entitlement(db,u.id)
   sid=f'phase3-session-{i:04d}'
   s=UserSession(user_id=u.id,session_uuid=sid,micro_motives=[],sjt_answers={},conjoint_choices={});db.add(s);db.flush()
   db.add(DiscoveryResult(session_id=s.id,major_id=major.id,m_score=0,s_score=0,v_score=0,total_score=0))
   fixtures.append((token,sid))
  db.commit()
 proc=subprocess.Popen([sys.executable,'-m','uvicorn','main_v2:app','--host','127.0.0.1','--port','8133','--no-access-log','--log-level','critical'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 import httpx
 with httpx.Client(base_url='http://127.0.0.1:8133',timeout=10) as c:
  for _ in range(60):
   try:
    if c.get('/api/v1/runtime/quota-health').json()['migration_ok']:break
   except Exception:pass
   time.sleep(.5)
  else:raise RuntimeError('startup not healthy')
  token,sid=fixtures[0]
  assert c.post('/api/v1/me/save-result',headers={'Authorization':'Bearer '+token},json={'session_uuid':sid,'result_summary':{'synthetic':True}}).status_code==200
 async def stage(n):
  samples={k:[] for k in ['health','token_me','quota','save']};codes={k:{} for k in samples};stop=asyncio.Event();start=time.monotonic()
  async with httpx.AsyncClient(base_url='http://127.0.0.1:8133',timeout=10,limits=httpx.Limits(max_connections=110,max_keepalive_connections=110)) as client:
   async def vu(i):
    rng=random.Random(1000+i);token,sid=fixtures[i];seq=0
    await asyncio.sleep(i/n)
    while time.monotonic()-start<120 and not stop.is_set():
     name=['health','token_me','quota','save'][seq%4];seq+=1
     url={'health':'/api/v1/runtime/quota-health','token_me':'/api/v1/me','quota':'/api/v1/me/quota','save':'/api/v1/me/save-result'}[name]
     t=time.monotonic();status='timeout';valid=True
     try:
      kw={'headers':{'Authorization':'Bearer '+token}}
      if name=='save':r=await client.post(url,json={'session_uuid':sid,'result_summary':{'synthetic':True}},**kw)
      else:r=await client.get(url,**kw)
      status=str(r.status_code)
      if name=='health' and r.status_code==200:valid=r.json()['migration_ok']
      if name=='save' and r.status_code==200:valid=r.json()['saved']
     except httpx.TimeoutException:pass
     except Exception:status='transport'
     if not valid:status='semantic'
     samples[name].append(time.monotonic()-t);codes[name][status]=codes[name].get(status,0)+1
     count=sum(len(v) for v in samples.values());bad=sum(v for d in codes.values() for k,v in d.items() if k!='200')
     if count>=100 and bad/count>.01:stop.set()
     await asyncio.sleep(rng.uniform(.75,1.25))
   await asyncio.gather(*(vu(i) for i in range(n)))
  stats={}
  for name,vals in samples.items():
   vals.sort();stats[name]={'n':len(vals),'p50_ms':round(vals[math.ceil(.5*len(vals))-1]*1000,2),'p95_ms':round(vals[math.ceil(.95*len(vals))-1]*1000,2),'p99_ms':round(vals[math.ceil(.99*len(vals))-1]*1000,2),'status':codes[name]}
  with SessionLocal() as db:
   negative=db.scalar(select(func.count()).select_from(Entitlement).where(Entitlement.credits_remaining<0));ledgers=db.scalar(select(func.count()).select_from(JourneyCreditConsumption));balances=list(db.execute(select(Entitlement.credits_remaining)).scalars());completed=db.scalar(select(func.count()).select_from(UserSession).where(UserSession.is_completed==True))
  integrity=not negative and ledgers==0 and balances==[1]*100
  return {'target_vu':n,'elapsed_s':round(time.monotonic()-start,2),'early_stop':stop.is_set(),'integrity':integrity,'negative':negative,'ledger_rows':ledgers,'completed':completed,'routes':stats}
 results=[]
 for n in [20,50,100]:
  result=asyncio.run(stage(n));results.append(result);(ROOT/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(result),flush=True)
  if result['early_stop'] or not result['integrity']:break
  time.sleep(5)
finally:
 if proc is not None:proc.terminate();proc.wait(timeout=15)
 server.cleanup()
```
