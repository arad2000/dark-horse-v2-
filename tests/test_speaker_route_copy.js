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
const copy = JSON.parse(fs.readFileSync('prototypes/speaker-copy/copy.json','utf8'));
const approved = new Map([['speaker',copy]]);
for (const g of copy.groups) { approved.set(g.id,g); for (const p of g.paths) approved.set(p.id,p); }
assert.equal(copy.groups.length,2);
assert.equal(approved.size,7);
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
assert.equal(changed,7);
assert.equal(crypto.createHash('sha256').update(JSON.stringify(normalized)).digest('hex'), '9fb4b1dfbb75db1ae22fd7c1f78bdb4eadebacc68433a5b215c238e49aa4de4c');

assert(fs.readFileSync('docs/index.html','utf8').includes('data.js?v=motives-1393-catalog-230-v1&narrow-fix=1&wood-fix=1&copy=speaker-grade9-v7'));
console.log('PASS: approved speaker copy matches preview; 7 entries; every other field, route order and other neighborhood unchanged; data cache key updated.');
// Rendering lists must not add choices, leak HTML, or change other realms/completed cards.
const app = fs.readFileSync('docs/app.js','utf8');
const renderer = app.slice(app.indexOf('function renderRouteCardHTML('),app.indexOf('\nfunction renderRealm()'));
const ctx={escapeHtml:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),dhGetWorldTheme:()=>({soft:'',border:'',color:'',svg:'',title:''}),dhWorldStyleVars:()=>'',dhFaNum:String};
vm.createContext(ctx);vm.runInContext(renderer,ctx);
const opts={realmId:'speaker',description:'<img src=x>\nsecond\nthird',motto:'Test'};
let html=ctx.renderRouteCardHTML(opts);
assert.equal((html.match(/<li>/g)||[]).length,3);
assert(html.includes('&lt;img'));assert(!html.includes('<img'));
assert.equal((html.match(/role="button"/g)||[]).length,1);
html=ctx.renderRouteCardHTML({...opts,realmId:'builder'});assert(!html.includes('<ul'));
html=ctx.renderRouteCardHTML({...opts,isComplete:true,doneDescription:'Completed'});
assert(!html.includes('<ul'));assert(html.includes('Completed'));assert(html.includes('tabindex="-1"'));
console.log('PASS speaker examples: escaped list, one route choice, legacy and completed behavior preserved');
// The review fixture itself must not drift from production structure.
copy.groups.forEach((group, i) => {
  assert.equal(group.id, actual.SUB_REALMS.speaker[i].id);
  assert.deepStrictEqual(group.majorCodes, actual.SUB_REALMS.speaker[i].majorCodes);
  assert.equal(group.paths.length, actual.NARROW_PATHS[group.id].length);
  group.paths.forEach((path, j) => {
    assert.equal(path.id, actual.NARROW_PATHS[group.id][j].id);
    assert.deepStrictEqual(path.majorCodes, actual.NARROW_PATHS[group.id][j].majorCodes);
    assert.equal(path.examples.length, 3);
  });
});
console.log('PASS speaker fixture: group/path IDs, order, mappings and three examples per path');
assert.equal(copy.groups.flatMap(g => g.paths).length, 4);
for (const id of ['bridge-translator', 'bridge-teacher']) {
  assert(approved.get(id).title.includes('انگلیسی'));
}
assert(approved.get('word-literature').title.includes('عربی'));
console.log('PASS speaker scope: four paths; English explicit in translation/teaching; Arabic translation retained');
