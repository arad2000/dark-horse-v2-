'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const crypto = require('crypto');
function load(source) {
  const ctx = {}; vm.createContext(ctx);
  vm.runInContext(source + ';this.routes={REALMS,SUB_REALMS,NARROW_PATHS};', ctx);
  return JSON.parse(JSON.stringify(ctx.routes));
}

const actual = load(fs.readFileSync('docs/data.js','utf8'));
const copy = JSON.parse(fs.readFileSync('prototypes/explorer-copy/copy.json','utf8'));
const approved = new Map([['explorer',copy]]);
for (const g of copy.groups) { approved.set(g.id,g); for (const p of g.paths) approved.set(p.id,p); }
assert.equal(copy.groups.length,5);
assert.equal(approved.size,20);
let changed=0;
// Fingerprint of the reviewed base routes, excluding ONLY approved text fields.
// This works in Actions checkout's shallow clone without fetching Git history.
const normalized = JSON.parse(JSON.stringify(actual));
for (const items of [normalized.REALMS, ...Object.values(normalized.SUB_REALMS), ...Object.values(normalized.NARROW_PATHS)]) {
  for (const item of items) if (approved.has(item.id)) {
    const text=approved.get(item.id);
    assert.equal(item.motto,text.title); assert.equal(item.description,text.description || text.examples.join("\n"));
    assert(item.motto.endsWith('؟')); changed++;
    delete item.motto; delete item.description;
  }
}
assert.equal(changed,20);
assert.equal(crypto.createHash('sha256').update(JSON.stringify(normalized)).digest('hex'), 'af7e15bb622c682be7b4feb1cb6f074a3b3d4624e727638bae9ae39854b3a317');

assert(fs.readFileSync('docs/index.html','utf8').includes('data.js?v=motives-1393-catalog-230-v1&narrow-fix=1&wood-fix=1&copy=speaker-grade9-v7'));
console.log('PASS: approved explorer copy matches preview; 20 entries; every other field, route order and other neighborhood unchanged; data cache key updated.');
// Rendering lists must not add choices, leak HTML, or change other realms/completed cards.
const app = fs.readFileSync('docs/app.js','utf8');
const renderer = app.slice(app.indexOf('function renderRouteCardHTML('),app.indexOf('\nfunction renderRealm()'));
const ctx={escapeHtml:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),dhGetWorldTheme:()=>({soft:'',border:'',color:'',svg:'',title:''}),dhWorldStyleVars:()=>'',dhFaNum:String};
vm.createContext(ctx);vm.runInContext(renderer,ctx);
const opts={realmId:'explorer',description:'<img src=x>\nsecond\nthird',motto:'Test'};
let html=ctx.renderRouteCardHTML(opts);
assert.equal((html.match(/<li>/g)||[]).length,3);
assert(html.includes('&lt;img'));assert(!html.includes('<img'));
assert.equal((html.match(/role="button"/g)||[]).length,1);
html=ctx.renderRouteCardHTML({...opts,realmId:'builder'});assert(!html.includes('<ul'));
html=ctx.renderRouteCardHTML({...opts,isComplete:true,doneDescription:'Completed'});
assert(!html.includes('<ul'));assert(html.includes('Completed'));assert(html.includes('tabindex="-1"'));
console.log('PASS explorer examples: escaped list, one route choice, legacy and completed behavior preserved');
