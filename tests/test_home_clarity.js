'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('docs/shell.js', 'utf8');
function harness(auth) {
  const nodes = {};
  const node = () => ({innerHTML:'', style:{}, classList:{add(){},remove(){},toggle(){}}, querySelectorAll(){return [];},querySelector(){return null;},setAttribute(){},appendChild(){}});
  const values = new Map([
    ['dh_local_user_v1', JSON.stringify({name:'LOCAL_FAKE',phone:'LOCAL_PHONE',is_premium:true})],
    ['dh_local_quota_v1', JSON.stringify({used:1,serverRemaining:3,premium:true,other:'preserve'})]
  ]);
  const storage = {getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};
  const document = {readyState:'loading',getElementById(id){return nodes[id]||(nodes[id]=node());},querySelectorAll(){return [];},addEventListener(){},body:node(),documentElement:node()};
  const context = {document,localStorage:storage,console,Date,setTimeout(){},navigator:{},location:{},window:null};
  context.window=context;context.addEventListener=()=>{};context.scrollTo=()=>{};context.DHAuth=auth;
  context.dhHasCommercialRuntime=()=>true;
  vm.createContext(context);
  vm.runInContext(source.replace('  window.DHShell = {','  window.__test = {homeSavedJourney,isResumableJourneyData};\n  window.DHShell = {'),context);
  return {context,nodes,values};
}
function authorize(h,id,pending=id) {
  h.context.__dhCommercialJourneyAuthorizedSessionId=id;
  h.values.set('dh_pending_journey_session_id',pending);
}
function saveJourney(h,data) { h.values.set('darkhorse_session_v2',JSON.stringify(data)); }

const resumableStages=['splash','realm','subRealm','narrowPath','introSwipe','swipe','introStrategies','strategies','introValues','values','choice'];
for (const stage of resumableStages) {
  const h=harness();authorize(h,'keep');
  saveJourney(h,{stage,journeyFinished:false,sessionId:'keep'});
  const before=h.values.get('darkhorse_session_v2');
  h.context.DHShell.renderHome();
  const html=h.nodes.app.innerHTML;
  assert(html.includes('ادامهٔ سفر'));
  assert(html.includes(h.context.__test.homeSavedJourney().label));
  assert(html.includes('dh-restart-journey'));
  assert(!html.includes('این ذخیرهٔ محلی، ذخیره در حساب نیست'));
  assert.strictEqual(h.values.get('darkhorse_session_v2'),before);
  let started=0,loaded=0;
  h.context.loadSession=()=>{loaded++;return true;};
  h.context.isPreResultsInProgress=()=>true;
  h.context.startNewJourney=()=>started++;
  h.nodes['dh-restart-journey'].onclick();
  assert.strictEqual(started,1);assert.strictEqual(loaded,1);
}

// A stale/different UUID is not resumable; rendering Home must not erase the saved selections.
const mismatch=harness();authorize(mismatch,'authorized-id');
saveJourney(mismatch,{stage:'swipe',journeyFinished:false,sessionId:'old-id',likedCodes:['S-keep']});
const mismatchBefore=mismatch.values.get('darkhorse_session_v2');
mismatch.context.DHShell.renderHome();
assert(mismatch.nodes.app.innerHTML.includes('شروع سفر'));
assert(!mismatch.nodes.app.innerHTML.includes('ادامهٔ سفر'));
assert(!mismatch.nodes.app.innerHTML.includes('dh-restart-journey'));
assert.strictEqual(mismatch.values.get('darkhorse_session_v2'),mismatchBefore);

// The in-memory authorization must itself match the pending UUID.
const pendingMismatch=harness();authorize(pendingMismatch,'authorized-id','different-pending-id');
saveJourney(pendingMismatch,{stage:'swipe',journeyFinished:false,sessionId:'authorized-id'});
const pendingBefore=pendingMismatch.values.get('darkhorse_session_v2');
pendingMismatch.context.DHShell.renderHome();
assert(pendingMismatch.nodes.app.innerHTML.includes('شروع سفر'));
assert(!pendingMismatch.nodes.app.innerHTML.includes('ادامهٔ سفر'));
assert.strictEqual(pendingMismatch.values.get('darkhorse_session_v2'),pendingBefore);

// Keep the existing startJourneyFromShell predicate: a legacy save without sessionId is eligible only after the commercial ID is authorized.
const legacy=harness();authorize(legacy,'authorized-id');
saveJourney(legacy,{stage:'swipe',journeyFinished:false,likedCodes:['legacy-selection']});
legacy.context.DHShell.renderHome();
assert(legacy.nodes.app.innerHTML.includes('ادامهٔ سفر'));
assert(legacy.nodes.app.innerHTML.includes('legacy-selection')===false); // saved choices are not rendered as HTML or rewritten
assert.strictEqual(legacy.values.get('darkhorse_session_v2'),JSON.stringify({stage:'swipe',journeyFinished:false,likedCodes:['legacy-selection']}));

for(const saved of [null,'broken','null','{}',JSON.stringify({stage:'results'}),JSON.stringify({stage:'swipe',journeyFinished:true,sessionId:'keep'}),JSON.stringify({stage:'<script>',sessionId:'keep'})]) {
  const h=harness();authorize(h,'keep');if(saved)h.values.set('darkhorse_session_v2',saved);
  h.context.DHShell.renderHome();
  assert(!h.nodes.app.innerHTML.includes('dh-restart-journey'));
  assert(h.nodes.app.innerHTML.includes('شروع سفر'));
}

const restart=harness();authorize(restart,'restart-id');
saveJourney(restart,{stage:'splash',sessionId:'restart-id'});
restart.context.DHShell.renderHome();
let starts=0;restart.context.loadSession=()=>true;restart.context.isPreResultsInProgress=()=>false;
restart.context.startNewJourney=()=>starts++;restart.context.confirm=()=>false;
restart.nodes['dh-restart-journey'].onclick();assert.strictEqual(starts,0);
restart.context.confirm=()=>true;restart.nodes['dh-restart-journey'].onclick();assert.strictEqual(starts,1);
for(const text of [
  'برای دانش‌آموزان در آستانهٔ انتخاب شاخهٔ دبیرستان یا رشتهٔ دانشگاهی.',
  'در پایان، پیشنهاد مسیرهای تحصیلی متناسب با علاقه‌ها، راهبردها و ارزش‌هایت می‌گیری؛ نه حکم قطعی.',
  'می‌توانی وسط راه توقف کنی و بعد در همین مرورگر و دستگاه ادامه بدهی؛ این ذخیرهٔ محلی، ذخیره در حساب نیست.',
  'جرقه‌ها: فعالیت‌هایی که دوست داری',
  'آینه: انتخاب در موقعیت واقعی',
  'دوراهی: ارزش شخصی',
  'موفقیت شخصی یعنی'
]) assert(!restart.nodes.app.innerHTML.includes(text));
assert(!restart.nodes.app.innerHTML.includes('dh-fardiyat-ticker'));
assert(restart.nodes.app.innerHTML.includes('سفر اکتشافی'));
assert(restart.nodes.app.innerHTML.includes('انتخاب رشته با منطق سنجش'));
console.log('PASS home clarity: UUID resume/restart preserved; homepage explanatory copy, glossary and ticker removed; core actions retained');

// First paint and hydrated shell use the same stage + authorization + UUID rule.
const index=fs.readFileSync('docs/index.html','utf8');
const startup=index.match(/<script>\s*\/\/ First paint[\s\S]*?<\/script>/)[0].replace(/^<script>|<\/script>$/g,'');
function runStartup(saved,authorizedId,pendingId) {
  const store=new Map();
  if(saved!==null)store.set('darkhorse_session_v2',JSON.stringify(saved));
  if(pendingId!==null)store.set('dh_pending_journey_session_id',pendingId);
  const button={textContent:'شروع سفر',parentNode:{note:null,appendChild(note){this.note=note;}}};
  const ctx={localStorage:{getItem:k=>store.get(k)||null},document:{getElementById:id=>id==='dh-startup-start'?button:null,createElement:()=>({})}};
  ctx.window=ctx;ctx.__dhCommercialJourneyAuthorizedSessionId=authorizedId||'';ctx.dhHasCommercialRuntime=()=>true;
  vm.runInNewContext(startup,ctx);
  return {button,store};
}
const startupLabels={splash:'آغاز سفر',realm:'انتخاب محله‌ها',subRealm:'انتخاب گذرها',narrowPath:'انتخاب مسیرها',introSwipe:'آشنایی با جرقه‌ها',swipe:'جرقه‌ها؛ فعالیت‌هایی که دوست داری',introStrategies:'آشنایی با آینه',strategies:'آینه؛ انتخاب در موقعیت واقعی',introValues:'آشنایی با دوراهی',values:'دوراهی؛ ارزش شخصی',choice:'انتخاب نوع نتیجه'};
for (const stage of resumableStages) {
  const result=runStartup({stage,sessionId:'first-paint-id'},'first-paint-id','first-paint-id');
  assert.strictEqual(result.button.textContent,'ادامهٔ سفر');
  assert(result.button.parentNode.note.textContent.includes(startupLabels[stage]));
}
const firstMismatch=runStartup({stage:'swipe',sessionId:'saved-old-id'},'authorized-new-id','authorized-new-id');
assert.strictEqual(firstMismatch.button.textContent,'شروع سفر');
assert.strictEqual(firstMismatch.button.parentNode.note,null);
assert.strictEqual(firstMismatch.store.get('darkhorse_session_v2'),JSON.stringify({stage:'swipe',sessionId:'saved-old-id'}));
const firstUntrusted=runStartup({stage:'swipe',sessionId:'same-id'},'same-id','different-pending-id');
assert.strictEqual(firstUntrusted.button.textContent,'شروع سفر');
const firstNoAuthorization=runStartup({stage:'swipe',sessionId:'saved-id'},'','');
assert.strictEqual(firstNoAuthorization.button.textContent,'شروع سفر');
console.log('PASS first paint: equal UUID continues; stale, untrusted or unauthorised saves keep Start and remain intact');
