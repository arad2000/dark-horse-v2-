'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const {execFileSync} = require('child_process');
function load(source) {
  const ctx = {}; vm.createContext(ctx);
  vm.runInContext(source + ';this.routes={REALMS,SUB_REALMS,NARROW_PATHS};', ctx);
  return JSON.parse(JSON.stringify(ctx.routes));
}
const baseline = load(execFileSync('git',['show','f6a984f627a8b01dc4a2ef31f3ab32062b2a4cd9:docs/data.js'],{encoding:'utf8'}));
const actual = load(fs.readFileSync('docs/data.js','utf8'));
const copy = JSON.parse(fs.readFileSync('prototypes/health-copy/copy.json','utf8'));
const approved = new Map([['healer',copy]]);
for (const g of copy.groups) { approved.set(g.id,g); for (const p of g.paths) approved.set(p.id,p); }
assert.equal(copy.groups.length,6);
assert.equal(approved.size,30);
let changed=0;
function check(oldItems,newItems) {
  assert.equal(oldItems.length,newItems.length);
  oldItems.forEach((old,i)=>{
    const current=newItems[i]; assert.equal(old.id,current.id);
    const expected=JSON.parse(JSON.stringify(old));
    if(approved.has(old.id)) {
      const text=approved.get(old.id);
      expected.motto=text.title; expected.description=text.description;
      assert(current.motto.endsWith('؟')); changed++;
    }
    assert.deepStrictEqual(current,expected,'Only approved copy may change: '+old.id);
  });
}
check(baseline.REALMS,actual.REALMS);
for(const key of ['SUB_REALMS','NARROW_PATHS']) {
  assert.deepStrictEqual(Object.keys(actual[key]),Object.keys(baseline[key]));
  for(const id of Object.keys(baseline[key])) check(baseline[key][id],actual[key][id]);
}
assert.equal(changed,30);
assert(fs.readFileSync('docs/index.html','utf8').includes('data.js?v=motives-1393-catalog-230-v1&narrow-fix=1&wood-fix=1&copy=health-grade9-v2'));
console.log('PASS: approved health copy matches preview; 30 entries; every other field, route order and other neighborhood unchanged; data cache key updated.');
