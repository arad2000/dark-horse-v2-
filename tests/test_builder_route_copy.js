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
const copy = JSON.parse(fs.readFileSync('prototypes/builder-copy/copy.json','utf8'));
const approved = new Map([['builder',copy]]);
for (const g of copy.groups) { approved.set(g.id,g); for (const p of g.paths) approved.set(p.id,p); }
assert.equal(copy.groups.length,7);
assert.equal(approved.size,36);
let changed=0;
// Fingerprint of the reviewed base routes, excluding ONLY approved text fields.
// This works in Actions checkout's shallow clone without fetching Git history.
const normalized = JSON.parse(JSON.stringify(actual));
for (const items of [normalized.REALMS, ...Object.values(normalized.SUB_REALMS), ...Object.values(normalized.NARROW_PATHS)]) {
  for (const item of items) if (approved.has(item.id)) {
    const text=approved.get(item.id);
    assert.equal(item.motto,text.title); assert.equal(item.description,text.description);
    assert(item.motto.endsWith('؟')); changed++;
    delete item.motto; delete item.description;
  }
}
assert.equal(changed,36);
assert.equal(crypto.createHash('sha256').update(JSON.stringify(normalized)).digest('hex'), 'ea972ba95738a61a44117a6bac91351344bd767d29a3e300d44ad742b0dff5d8');

assert(fs.readFileSync('docs/index.html','utf8').includes('data.js?v=motives-1393-catalog-230-v1&narrow-fix=1&wood-fix=1&copy=speaker-grade9-v7'));
console.log('PASS: approved builder copy matches preview; 36 entries; every other field, route order and other neighborhood unchanged; data cache key updated.');
