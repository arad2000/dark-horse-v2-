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
  vm.createContext(context);
  vm.runInContext(source.replace('  window.DHShell = {','  window.__test = {homeSavedJourney};\n  window.DHShell = {'),context);
  return {context,nodes,values};
}

for (const stage of ['splash','realm','subRealm','narrowPath','introSwipe','swipe','introStrategies','strategies','introValues','values','choice']) {
  const h=harness();
  h.values.set('darkhorse_session_v2',JSON.stringify({stage,journeyFinished:false,sessionId:'keep'}));
  const before=h.values.get('darkhorse_session_v2');
  h.context.DHShell.renderHome();
  const html=h.nodes.app.innerHTML;
  assert(html.includes('ادامهٔ سفر'));
  assert(html.includes(h.context.__test.homeSavedJourney().label));
  assert(html.includes('dh-restart-journey'));
  assert(html.includes('این ذخیرهٔ محلی، ذخیره در حساب نیست'));
  assert.strictEqual(h.values.get('darkhorse_session_v2'),before);
  let started=0, loaded=0;
  h.context.loadSession=()=>{loaded++;return true;};
  h.context.isPreResultsInProgress=()=>true;
  h.context.startNewJourney=()=>started++;
  h.nodes['dh-restart-journey'].onclick();
  assert.strictEqual(started,1);assert.strictEqual(loaded,1);
}
for(const saved of [null,'broken','null','{}',JSON.stringify({stage:'results'}),JSON.stringify({stage:'swipe',journeyFinished:true}),JSON.stringify({stage:'<script>'})]) {
  const h=harness();if(saved)h.values.set('darkhorse_session_v2',saved);
  h.context.DHShell.renderHome();
  assert(!h.nodes.app.innerHTML.includes('dh-restart-journey'));
  assert(h.nodes.app.innerHTML.includes('شروع سفر'));
}
const h=harness();h.values.set('darkhorse_session_v2',JSON.stringify({stage:'splash'}));h.context.DHShell.renderHome();
let starts=0;h.context.loadSession=()=>true;h.context.isPreResultsInProgress=()=>false;
h.context.startNewJourney=()=>starts++;h.context.confirm=()=>false;
h.nodes['dh-restart-journey'].onclick();assert.strictEqual(starts,0);
h.context.confirm=()=>true;h.nodes['dh-restart-journey'].onclick();assert.strictEqual(starts,1);
for(const text of ['جرقه‌ها: فعالیت‌هایی که دوست داری','آینه: انتخاب در موقعیت واقعی','دوراهی: ارزش شخصی']) assert(h.nodes.app.innerHTML.includes(text));
console.log('PASS home clarity: local stages, malformed/finished saves, restart delegation/cancel, no storage writes');
// Initial HTML and hydrated shell must describe the same local stage.
const index = fs.readFileSync('docs/index.html','utf8');
const startup = index.match(/<script>\s*\/\/ First paint[\s\S]*?<\/script>/)[0].replace(/^<script>|<\/script>$/g,'');
for (const stage of ['splash','realm','subRealm','narrowPath','introSwipe','swipe','introStrategies','strategies','introValues','values','choice']) {
  const h=harness();h.values.set('darkhorse_session_v2',JSON.stringify({stage}));
  const button={textContent:'شروع سفر',parentNode:{appendChild(note){this.note=note;}}};
  vm.runInNewContext(startup,{localStorage:{getItem:()=>h.values.get('darkhorse_session_v2')},document:{getElementById:()=>button,createElement:()=>({})}});
  assert.strictEqual(button.textContent,'ادامهٔ سفر');
  assert(button.parentNode.note.textContent.includes(h.context.__test.homeSavedJourney().label));
}
console.log('PASS initial HTML and shell stage labels agree');
