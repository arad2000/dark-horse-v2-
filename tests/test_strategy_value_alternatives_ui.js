'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const app=fs.readFileSync('docs/app.js','utf8');
const start=app.indexOf('function renderStrategyValueAlternativesHTML(');
const end=app.indexOf('// ==================== توضیح مشاوره‌ای',start);
const ctx={escapeHtml:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),dhFaNum:String};
vm.createContext(ctx);vm.runInContext(app.slice(start,end),ctx);
const render=ctx.renderStrategyValueAlternativesHTML;
assert(render(null).includes('محاسبهٔ تازه لازم است'));
assert(!render({method:'old',items:[{major_name:'OLD_NUMERIC'}]}).includes('OLD_NUMERIC'));
const base={method:'user_strategy_or_value_gt70_v1',status:'ready',coverage:{incomplete:true}};
const dim=(score,qualifies)=>({status:'evaluated',score,qualifies});
for(const basis of ['strategy','value','both']){
 const html=render({...base,items:[{major_name:'<img src=x>',basis,strategy:dim(.82,basis!=='value'),value:basis==='strategy'?{status:'unknown',score:null}:dim(.91,true),evidence:{uniform_strategy_rows:1}}]});
 assert(html.includes('&lt;img'));assert(!html.includes('<img'));
 assert(html.includes('۸۲')||html.includes('82'));
 assert(html.includes('پوشش داده‌ها'));assert(html.includes('تمایز قوی نیست'));
 if(basis==='strategy')assert(html.includes('اطلاعات کافی برای بررسی موجود نیست'));
}
assert(render({...base,status:'insufficient_data',items:[]}).includes('اطلاعات کافی برای بررسی سازگاری'));
assert(render({...base,status:'no_matches_in_evaluated_dimensions',items:[]}).includes('پیدا نشد'));
assert(app.includes('!isBranch ? renderStrategyValueAlternativesHTML(r.strategy_value_alternatives)'));
assert(app.includes('alternative_paths: isBranch ?'));
assert(fs.readFileSync('docs/index.html','utf8').includes('&r=282&next-step='));
console.log('PASS S/V results: reasons, scores, unknown/empty/legacy, escaping, coverage, branch isolation');
