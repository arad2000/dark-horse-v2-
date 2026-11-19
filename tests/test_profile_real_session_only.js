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
  vm.runInContext(source.replace('  window.DHShell = {','  window.__test = {getDisplayUser,canRunTest,saveQuota};\n  window.DHShell = {'),context);
  return {context,nodes,values};
}
for (const auth of [undefined,{isLoggedIn:()=>false,getUser:()=>({name:'STALE'})},{isLoggedIn(){throw Error('expired');}}]) {
  const h=harness(auth);h.context.DHShell.renderProfile();
  const html=h.nodes.app.innerHTML;
  assert(html.includes('ساخت حساب جدید (پیامک)') && html.includes('ورود به حساب'));
  for(const forbidden of ['LOCAL_FAKE','LOCAL_PHONE','dh-p-save','dh-p-name','dh-p-phone','dh-p-prem'])assert(!html.includes(forbidden));
  assert.strictEqual(h.context.__test.getDisplayUser(),null);
  assert.strictEqual(JSON.parse(h.values.get('dh_local_quota_v1')).serverRemaining,3);
}
const h=harness({isLoggedIn:()=>true,getUser:()=>({name:'REAL_SESSION',phone:'TEST',is_premium:false})});
h.context.DHShell.renderProfile();
assert(h.nodes.app.innerHTML.includes('REAL_SESSION'));
assert(!h.nodes.app.innerHTML.includes('LOCAL_FAKE'));
assert(!h.nodes.app.innerHTML.includes('dh-p-prem'));
assert(h.nodes.app.innerHTML.includes('dh-p-out') && h.nodes.app.innerHTML.includes('dh-p-buy'));
h.values.set('dh_local_quota_v1',JSON.stringify({used:1,serverRemaining:0,premium:true}));
assert.strictEqual(h.context.__test.canRunTest(),false,'legacy premium cannot grant access');
h.context.__test.saveQuota({used:1,serverRemaining:3,other:'preserve',premium:true,is_premium:true});
assert.deepStrictEqual(JSON.parse(h.values.get('dh_local_quota_v1')),{used:1,serverRemaining:3,other:'preserve'});
for(const forbidden of ['اشتراک محلی آفلاین (تست)','خاموش کردن اشتراک محلی','ثبت پروفایل محلی','اختیاری: ذخیره فقط'])assert(!source.includes(forbidden));
console.log('PASS profile: stale local identity/premium ignored; real session used; server quota retained; controls removed');
