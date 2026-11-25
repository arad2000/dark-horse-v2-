'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const app=fs.readFileSync('docs/app.js','utf8'),css=fs.readFileSync('docs/genz_results_layer.css','utf8');
assert.equal((app.match(/class="btn dh-result-action dh-result-action-explore"/g)||[]).length,2);
assert(app.includes('class="btn btn-primary dh-result-action dh-result-action-primary"'));
assert.equal((app.match(/class="btn dh-result-action dh-result-action-back"/g)||[]).length,2);
assert(css.includes('prefers-reduced-motion'));assert(css.includes(':focus-visible'));
const source=app.slice(app.indexOf('async function loadDeepCounselItem('),app.indexOf('\nasync function loadDeepCounsel(mode)'));
async function scenario(fail){
 const box={dataset:{},style:{},setAttribute(k,v){this[k]=v;},innerHTML:''};
 const buttons=[{textContent:'توضیح',disabled:false},{textContent:'جایگزین',disabled:false}];
 let calls=0,complete;
 const pending=new Promise(resolve=>{complete=resolve;});
 const ctx={state:{lastCounselTops:[{name:'Test'}]},document:{getElementById(id){if(id==='dh-counsel-box-0')return box;if(id==='dh-counsel-actions-0')return {querySelectorAll:()=>buttons};return id==='dh-counsel-main-0'?buttons[0]:buttons[1];}},API_BASE:'',AbortController,console:{error(){}},setTimeout:()=>1,clearTimeout(){},escapeHtml:String,fetch:async()=>{calls++;await pending;if(fail)throw Error('offline');return {ok:true,json:async()=>({counseling:'Answer'})};}};
 vm.createContext(ctx);vm.runInContext(source,ctx);
 const first=ctx.loadDeepCounselItem(0,'main');
 assert(buttons.every(b=>b.disabled));assert.equal(box['aria-busy'],'true');
 await ctx.loadDeepCounselItem(0,'alternatives');assert.equal(calls,1);
 complete();await first;
 assert(buttons.every(b=>!b.disabled));assert.equal(buttons[0].textContent,'توضیح');assert.equal(box['aria-busy'],'false');assert.equal(box.dataset.pending,'false');
 assert(box.innerHTML.includes(fail?'دوباره تلاش':'Answer'));
}
(async()=>{await scenario(false);await scenario(true);console.log('PASS result actions: visual roles, reduced motion, pending guard, recovery and mock-only network');})().catch(e=>{console.error(e);process.exit(1);});
