# ضمیمهٔ بازتولید فاز ۱ — فقط ممیزی، نه runtime

**خطر عملیاتی: harness کاربران جدول users را با CASCADE در DB مقصد پاک می‌کند. فقط PostgreSQL تازهٔ محلی ایزوله مجاز است؛ به production/staging مشترک اشاره نکند.** هیچ URL یا credential واقعی در این فایل نیست. fixtureها مصنوعی‌اند. قبل از اجرا مقصد را با اپراتور بررسی کنید؛ صرف نام فایل URI محافظ کافی در برابر تنظیم اشتباه نیست.

روش اجراشده: Git archive از SHA تجاری در `/home/user/concurrency-audit`؛ venv در `/home/user/concurrency-venv` با requirements/constraints همان source، pytest و pgserver==0.1.4. با pgserver.get_server یک cluster تازه در `/home/user/concurrency-pgdata` ساخته شد؛ URI آن در فایل محلی mode=0600 به نام `/home/user/concurrency-db-uri` نوشته شد و هیچ‌وقت چاپ نشد. parent process تا پایان اجرا فعال ماند. PostgreSQL فقط Unix socket داشت. `alembic upgrade head` با dialect `postgresql+psycopg` روی همان URI قبل از harness اجرا شد؛ schema یا Cutover تغییر نکرد. اجرای script از داخل archive لازم است.

برای اجرای واقعی اسکریپت زیر را در فایل خارج repo ذخیره کنید. خطاها را با traceback شامل params چاپ نکنید؛ wrapper استفاده‌شده فقط نام نوع exception و نام تابع/شمارهٔ خط harness را چاپ کرد. execution نهایی موفق بود؛ همهٔ خروجی ثبت‌شده پایین همین سند aggregate است. stdout/stderr عمومی برنامه غیرفعال و SQL echo روشن نشده است. هیچ env dump، رمز، token یا متن پاسخ کاربر به report منتقل نشده است.

در پایان، pg_ctl با mode=fast خوشهٔ ایزوله را متوقف کرد و process نگهدارنده بسته شد؛ هیچ سرویس تولیدی stop نشد. این محیط ephemeral است؛ برای تکرار، نصب ابزار و ایجاد DB تازه لازم است، نه اتکا به موجودماندن مسیرها. ابزار نصب‌شدهٔ PostgreSQL محلی زیرساخت تجاری خریداری‌شده نیست.

## Harness backend اجراشده

SHA-256: `0326ed4c84f31081277ffc5074ea74904a5a7fe283986ba98039b9ec254e0684`

```python
"""Isolated audit harness; emits aggregate assertions only. Not production code."""
import os, logging, warnings, json, time, threading, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from datetime import datetime, timezone
os.environ['DATABASE_URL']=Path('/home/user/concurrency-db-uri').read_text().replace('postgresql://','postgresql+psycopg://')
os.environ['APP_ENV']='test'
os.environ['BILLING_PROVIDER']='mock'
os.environ['BILLING_FREE_MODE']='false'
os.environ['POSTGRES_RUNTIME_CUTOVER_APPROVED']='false'
logging.disable(logging.CRITICAL)
warnings.filterwarnings('ignore')
from fastapi.testclient import TestClient
from sqlalchemy import select, text, func
from database import SessionLocal, engine
from billing_models import User, PremiumPlan, Entitlement, JourneyCreditConsumption, Payment, PaymentEvent
from models import UserSession, DiscoveryResult
from auth_service import issue_session
from billing_credit_service import initiate_payment
from payment_providers import MockPaymentProvider
from operational_store import OperationalStore
from seed_reference_data import seed_reference_data
from main_v2 import app
from unittest.mock import patch
from fastapi import HTTPException

results={}
def record(case, **data):
    results[case]=data
    Path('/home/user/phase1-results.json').write_text(json.dumps(results,indent=2))
    print(case,json.dumps(data),flush=True)
def parallel(tasks):
    barrier=threading.Barrier(len(tasks))
    def call(f):
        barrier.wait(timeout=10)
        return f()
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        return list(pool.map(call,tasks))

def setup(credits=1):
    with SessionLocal() as db:
        db.execute(text('TRUNCATE users RESTART IDENTITY CASCADE'))
        users=[];headers=[]
        plan=db.scalar(select(PremiumPlan).where(PremiumPlan.code=='pack_3_tests'))
        for i in range(2):
            u=User(public_id=str(uuid4()),name='Synthetic audit',phone='local-audit-'+str(i),role='user',status='active')
            db.add(u);db.flush()
            token,_=issue_session(db,u)
            db.add(Entitlement(user_id=u.id,plan_id=plan.id,source='payment',credits_granted=credits,credits_remaining=credits,starts_at=datetime.now(timezone.utc),status='active'))
            users.append(u.id);headers.append({'Authorization':'Bearer '+token})
        db.commit()
    return users,headers

def stats(user):
    with SessionLocal() as db:
        return (db.scalar(select(func.sum(Entitlement.credits_remaining)).where(Entitlement.user_id==user)),
                db.scalar(select(func.count()).select_from(JourneyCreditConsumption).where(JourneyCreditConsumption.user_id==user)))

def post(client,path,head,body):
    return client.post(path,headers=head,json=body)

with engine.connect() as db:
    record('environment', postgres=db.scalar(text('SHOW server_version')), isolation=db.scalar(text('SHOW transaction_isolation')), migration=db.scalar(text('SELECT version_num FROM alembic_version')), pool_size=engine.pool.size())
with SessionLocal() as db:
    seed_reference_data(db,Path.cwd())
record('reference_seed',status='PASS',source='unchanged commercial Git JSON into isolated database')

with TestClient(app,raise_server_exceptions=False) as client:
    # C01/C02: independent DB sessions behind the real authenticated endpoints.
    for case,same in [('C01',True),('C02',False)]:
        trials=[]
        for _ in range(10):
            users,heads=setup();ids=[str(uuid4()),str(uuid4())]
            if same: ids[1]=ids[0]
            rs=parallel([lambda sid=sid: post(client,'/api/v1/me/consume-test',heads[0],{'session_uuid':sid}) for sid in ids])
            counts=stats(users[0]); codes=sorted(r.status_code for r in rs)
            consumed=sum(r.json().get('consumed',0) for r in rs if r.status_code==200)
            ok=counts==(0,1) and consumed==1 and codes==([200,200] if same else [200,409])
            if same: ok=ok and sorted(r.json()['already_consumed'] for r in rs)==[False,True]
            trials.append(ok)
        record(case,status='PASS' if all(trials) else 'FAIL',trials=len(trials),passed=sum(trials),last_statuses=codes,remaining=counts[0],ledger=counts[1])

    # C03: true HTTP callback, synthetic gateway only, no outbound payment call.
    trials=[]
    for _ in range(10):
        users,heads=setup()
        with SessionLocal() as db:
            provider=MockPaymentProvider()
            order,pay,req=initiate_payment(db,users[0],provider,'https://example.test/callback')
            public_id=order.public_id;authority=req['authority'];order_id=order.id
            db.commit()
        def cb():
            return client.get('/api/v1/billing/callback',params={'order_id':public_id,'Authority':authority,'Status':'OK'},follow_redirects=False)
        rs=parallel([cb,cb]);retry=cb()
        with SessionLocal() as db:
            ents=list(db.scalars(select(Entitlement).where(Entitlement.order_id==order_id)))
            events=db.scalar(select(func.count()).select_from(PaymentEvent))
            ok=len(ents)==1 and ents[0].credits_granted==3 and all(r.status_code==303 for r in rs+[retry])
            trials.append(ok)
    record('C03',status='PASS' if all(trials) else 'FAIL',trials=10,passed=sum(trials),last_statuses=[r.status_code for r in rs+[retry]],grants=len(ents),granted_credits=ents[0].credits_granted if ents else None,events=events)

    # C04: test the existing whole-summary UPDATE, no optimistic version contract.
    users,heads=setup();sid=str(uuid4())
    charge=post(client,'/api/v1/me/consume-test',heads[0],{'session_uuid':sid});assert charge.status_code==200
    with SessionLocal() as db:
        row=db.scalar(select(UserSession).where(UserSession.session_uuid==sid));row_id=row.id
    # Use actual unchanged engine recommendations, not fabricated scientific weights.
    payload={'session_id':sid,'micro_motives':[f'MED-{i:03d}' for i in range(1,8)],'sjt_answers':{f'sjt_{i}':'A' for i in range(1,26)},'conjoint_choices':{f'conj_{i}':f'Q{i}A' for i in range(1,16)}}
    discovery=app.state.engine.discover_individuality(payload['micro_motives'],payload['sjt_answers'],payload['conjoint_choices'])
    OperationalStore().store_discovery_results(row_id,discovery['discovered_majors'])
    summaries=[{'audit_fixture':x,'pair':[x,x]} for x in ['left','right']]
    trials=[]
    for _ in range(10):
        rs=parallel([lambda summary=summary: post(client,'/api/v1/me/save-result',heads[0],{'session_uuid':sid,'result_summary':summary}) for summary in summaries])
        with SessionLocal() as db:
            rows=list(db.scalars(select(UserSession).where(UserSession.session_uuid==sid)))
            final=dict(rows[0].result_summary);final.pop('session_uuid',None)
            ok=all(r.status_code==200 for r in rs) and len(rows)==1 and rows[0].user_id==users[0] and rows[0].is_completed and final in summaries
            trials.append(ok)
    record('C04',status='PASS' if all(trials) else 'FAIL',trials=10,passed=sum(trials),last_statuses=[r.status_code for r in rs],rows=1,policy='whole JSON replacement; last database UPDATE wins; no version/conflict rejection; no guarantee of user-intended latest edit')

    # C05: bidirectional attempts on all relevant user write/compute routes; no user GET-result route exists.
    sid_b=str(uuid4());assert post(client,'/api/v1/me/consume-test',heads[1],{'session_uuid':sid_b}).status_code==200
    codes=[]; safe_error_bodies=[]
    with SessionLocal() as db:
        before=[(r.session_uuid,r.user_id,r.result_summary) for r in db.scalars(select(UserSession).order_by(UserSession.id))]
    for attacker,victim_sid in [(heads[1],sid),(heads[0],sid_b)]:
        for path,body in [('/api/v1/me/consume-test',{'session_uuid':victim_sid}),('/api/v1/me/save-result',{'session_uuid':victim_sid,'result_summary':{'audit_fixture':'attempt'}}),('/api/v2/darkhorse/discover',dict(payload,session_id=victim_sid)),('/api/v2/darkhorse/counsel',{'session_id':victim_sid,'profile':{},'top_results':[]})]:
            denied=post(client,path,attacker,body)
            codes.append(denied.status_code)
            safe_error_bodies.append(set(denied.json())=={'detail'})
        denied=client.get('/api/v1/admin/users',headers=attacker)
        codes.append(denied.status_code)
        safe_error_bodies.append(set(denied.json())=={'detail'})
    with SessionLocal() as db:
        after=[(r.session_uuid,r.user_id,r.result_summary) for r in db.scalars(select(UserSession).order_by(UserSession.id))]
    record('C05',status='PASS' if all(code in (401,402,403) for code in codes) and all(safe_error_bodies) and before==after and stats(users[0])==(0,1) and stats(users[1])==(0,1) else 'FAIL',statuses=codes,server_state_unchanged=before==after,error_bodies_detail_only=all(safe_error_bodies),scope='bidirectional consume/save/discover/counsel + admin user read; no normal GET result endpoint; 402 must not disclose data')

    # C06: simulate old tab/new tab clients on same unchanged API + persisted database.
    users,heads=setup();sid=str(uuid4())
    assert post(client,'/api/v1/me/consume-test',heads[0],{'session_uuid':sid}).status_code==200
    payload=dict(payload,session_id=sid)
    with SessionLocal() as db:
        row=db.scalar(select(UserSession).where(UserSession.session_uuid==sid))
        assert row.is_completed is False and row.sjt_answers=={}
        resumed_row_id=row.id
    resumed=TestClient(app,raise_server_exceptions=False)
    before_credits=stats(users[0])
    response=post(resumed,'/api/v1/me/consume-test',heads[0],{'session_uuid':sid})
    result=post(resumed,'/api/v2/darkhorse/discover',heads[0],payload)
    record('C06_backend',status='PASS' if response.status_code==200 and response.json().get('consumed')==0 and result.status_code==200 and stats(users[0])==before_credits else 'FAIL',statuses=[response.status_code,result.status_code],consumed_on_retry=response.json().get('consumed'),scope='client remount and resume same API/DB; paired frontend VM reload evidence required; no real CDN/SW deployment simulated here')

    OperationalStore().store_discovery_results(resumed_row_id,discovery['discovered_majors'])

    # C07: inject failure at AI external boundary only; main engine/DB remain real.
    cases=[]
    for fault in [504,502]:
        async def fail_ai(**kwargs):raise HTTPException(fault,detail='synthetic upstream fault')
        with patch('main_v2.generate_counseling',side_effect=fail_ai) as mocked:
            ai=post(client,'/api/v2/darkhorse/counsel',heads[0],{'session_id':sid,'profile':{},'top_results':[{'name':'synthetic'}]})
            main=post(client,'/api/v2/darkhorse/discover',heads[0],payload)
            save=post(client,'/api/v1/me/save-result',heads[0],{'session_uuid':sid,'result_summary':summaries[0]})
            repeat=post(client,'/api/v1/me/consume-test',heads[0],{'session_uuid':sid})
            cases.append({'ai':ai.status_code,'main':main.status_code,'save':save.status_code,'repeat_consumed':repeat.json().get('consumed'),'injected':mocked.called})
    record('C07',status='PASS' if all(c=={'ai':fault,'main':200,'save':200,'repeat_consumed':0,'injected':True} for c,fault in zip(cases,[504,502])) else 'FAIL',cases=cases,scope='HTTP fault injection at AI call boundary; not slow upstream resource saturation')
print('AUDIT_FINISHED',flush=True)
```

## Harness frontend اجراشده

از ریشهٔ source فعلی اجرا شد؛ Git object #361 در صورت نبودن با fetch همان SHA دریافت شد. harness موجود S فقط برای ساخت VM خوانده می‌شود و فایل تست تغییر نکرده است.

SHA-256: `cad40d6710185cba9fc64850ca1e0aeb0c8e9b839a5238d9201ef8a573762af3`

```javascript
const fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process'),assert=require('node:assert/strict');
const root='/home/user/dark-horse-v2-';
const test=fs.readFileSync(root+'/tests/test_strategy_ui_complete_gate.js','utf8');
let prefix=test.slice(0,test.indexOf('const contract = (async () => {'));
prefix=prefix.replace("const source = fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8');",'const source = overrideSource;');
function mount(source,store){
 const context={require,console,AbortController,__dirname:root+'/tests',overrideSource:source,store};
 vm.runInNewContext(prefix+'\nglobalThis.mounted = harness(store);',context);
 return context.mounted;
}
const old=cp.execFileSync('git',['show','0fb035357fa55a1aa02a086bbd7dd0b3b27a6061:docs/app.js'],{cwd:root,encoding:'utf8'});
const fresh=fs.readFileSync(root+'/docs/app.js','utf8');
const before=mount(old);
before.c.state.sessionId='audit-synthetic-open-session';
before.c.state.stage='strategies';
before.c.state.strategyAnswers=[4,2];
before.c.state.currentQuestion=2;
before.c.state.valueAnswers=[];
before.c.state.selectedRealms=['speaker','healer'];
before.c.saveSession();
const snapshot=before.values.get('darkhorse_session_v2');
const after=mount(fresh,before.values);
assert.equal(after.c.loadSession(),true);
assert.equal(after.c.state.sessionId,before.c.state.sessionId);
assert.equal(JSON.stringify(after.c.state.strategyAnswers),'[4,2]');
assert.equal(after.c.state.currentQuestion,2);
assert.equal(JSON.stringify(after.c.state.selectedRealms),'["speaker","healer"]');
assert.equal(after.c.state.displayShuffleSeed,before.c.state.displayShuffleSeed);
for(let i=2;i<25;i++)after.c.answerStrategy(i%5);
assert.equal(after.c.buildPayload().sjt_answers.sjt_1,'E');
assert.equal(after.c.buildPayload().sjt_answers.sjt_2,'C');
const indexOld=cp.execFileSync('git',['show','0fb035357fa55a1aa02a086bbd7dd0b3b27a6061:docs/index.html'],{cwd:root,encoding:'utf8'});
const indexNew=fs.readFileSync(root+'/docs/index.html','utf8');
assert.ok(!indexOld.includes('shuffle-v1=1')&&indexNew.includes('shuffle-v1=1'));
console.log('C06 frontend PASS: open synthetic journey from #361 to current cache-busted frontend; partial answers, cursor, seed, selection and session ID retained; completion payload canonical. VM only, no actual SW/browser deploy.');
```

## خروجی aggregate اجرای نهایی

SHA-256 فایل JSON اصلی: `a0e1dd7cbd7abf506d9fea3c14b62dfc4b2b3637ae4231ef122c5a230b1f6847`

```json
{
  "environment": {
    "postgres": "16.2",
    "isolation": "read committed",
    "migration": "0011_otp_request_ip",
    "pool_size": 10
  },
  "reference_seed": {
    "status": "PASS",
    "source": "unchanged commercial Git JSON into isolated database"
  },
  "C01": {
    "status": "PASS",
    "trials": 10,
    "passed": 10,
    "last_statuses": [
      200,
      200
    ],
    "remaining": 0,
    "ledger": 1
  },
  "C02": {
    "status": "PASS",
    "trials": 10,
    "passed": 10,
    "last_statuses": [
      200,
      409
    ],
    "remaining": 0,
    "ledger": 1
  },
  "C03": {
    "status": "PASS",
    "trials": 10,
    "passed": 10,
    "last_statuses": [
      303,
      303,
      303
    ],
    "grants": 1,
    "granted_credits": 3,
    "events": 1
  },
  "C04": {
    "status": "PASS",
    "trials": 10,
    "passed": 10,
    "last_statuses": [
      200,
      200
    ],
    "rows": 1,
    "policy": "whole JSON replacement; last database UPDATE wins; no version/conflict rejection; no guarantee of user-intended latest edit"
  },
  "C05": {
    "status": "PASS",
    "statuses": [
      403,
      403,
      402,
      402,
      403,
      403,
      403,
      402,
      402,
      403
    ],
    "server_state_unchanged": true,
    "error_bodies_detail_only": true,
    "scope": "bidirectional consume/save/discover/counsel + admin user read; no normal GET result endpoint; 402 must not disclose data"
  },
  "C06_backend": {
    "status": "PASS",
    "statuses": [
      200,
      200
    ],
    "consumed_on_retry": 0,
    "scope": "client remount and resume same API/DB; paired frontend VM reload evidence required; no real CDN/SW deployment simulated here"
  },
  "C07": {
    "status": "PASS",
    "cases": [
      {
        "ai": 504,
        "main": 200,
        "save": 200,
        "repeat_consumed": 0,
        "injected": true
      },
      {
        "ai": 502,
        "main": 200,
        "save": 200,
        "repeat_consumed": 0,
        "injected": true
      }
    ],
    "scope": "HTTP fault injection at AI call boundary; not slow upstream resource saturation"
  }
}
```
