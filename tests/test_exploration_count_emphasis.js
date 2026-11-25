'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const app=fs.readFileSync('docs/app.js','utf8');
const start=app.indexOf('// In-memory only: each exploration stage gets');
const end=app.indexOf('function renderRealm() {',start);
const helper=app.slice(start,end);
function session(preference=true, available=true){
  let nodes=[],queries=0;
  const ctx={app:{querySelectorAll(selector){assert.equal(selector,'.dh-card-subcount');queries++;return nodes;}},window:available?{matchMedia(query){assert.equal(query,'(prefers-reduced-motion: no-preference)');return {matches:preference};}}:{}};
  vm.createContext(ctx);vm.runInContext(helper,ctx);
  return {ctx,render(stage,count=3){nodes=Array.from({length:count},()=>({added:[],classList:{add(name){this.owner.added.push(name);}}}));nodes.forEach(n=>n.classList.owner=n);ctx.dhEmphasizeExplorationCounts(stage);return nodes;},queries:()=>queries};
}
const s=session();
for(const stage of ['realm','subRealm','narrowPath']){
 assert(s.render(stage).every(n=>n.added.length===1));
 assert(s.render(stage).every(n=>n.added.length===0),'selection rerender and revisit must not replay');
}
assert(s.render('profile').every(n=>n.added.length===0));
assert(s.render('results').every(n=>n.added.length===0));
assert(session().render('realm').every(n=>n.added.length===1),'fresh in-memory session can emphasize');
const reduced=session(false);assert(reduced.render('realm').every(n=>!n.added.length));
reduced.ctx.window.matchMedia=()=>({matches:true});assert(reduced.render('realm').every(n=>!n.added.length),'do not replay after reduced-motion entry');
assert(session(true,false).render('realm').every(n=>!n.added.length));
const empty=session();empty.render('realm',0);assert(empty.render('realm').every(n=>n.added.length===1));
assert(!/localStorage|sessionStorage|setTimeout|setInterval|fetch\(/.test(helper));
const css=fs.readFileSync('docs/journey_experience.css','utf8');
assert(css.includes('animation: dh-count-enter-once 360ms ease-out 1;'));
assert(css.includes('@media (prefers-reduced-motion: reduce)'));
assert(css.includes('animation: none !important; transform: none !important;'));
assert(!helper.includes('innerHTML'));
// Lock every other app byte, including count labels, card renderer, scoring,
// alternatives, profile, quota and all selection handlers, to main 4064c0dd.
let normalized=app.slice(0,start)+app.slice(end);
for(const stage of ['realm','subRealm','narrowPath']){
 const call="\n"+(stage==='realm'?'    ':'  ')+"dhEmphasizeExplorationCounts('"+stage+"');";
 assert.equal(normalized.split(call).length-1,1);normalized=normalized.replace(call,'');
}
assert.equal(crypto.createHash('sha256').update(normalized).digest('hex'),'5d8aa623122685c29dcb8195cb368630c7c15575deabe268c8054729a42f26c7');
const html=fs.readFileSync('docs/index.html','utf8');
assert(html.includes('journey_experience.css?v=3'));assert(html.includes('&r=283&next-step='));
console.log('PASS count emphasis: once/stage/app-load, no replay, reduced motion, safe fallback, no persistence; all other app bytes unchanged');
