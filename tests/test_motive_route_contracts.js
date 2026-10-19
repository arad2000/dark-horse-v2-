'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const dataSource = fs.readFileSync(path.join(root, 'docs/data.js'), 'utf8');
const majors = JSON.parse(fs.readFileSync(path.join(root, 'majors_database_v2.json'), 'utf8'));
const motives = JSON.parse(fs.readFileSync(path.join(root, 'micro_motives.json'), 'utf8'));
const motiveCodes = new Set(motives.map((item) => item.code));

const sandbox = {};
vm.runInNewContext(
  dataSource + '\nthis.__testNarrowPaths = NARROW_PATHS;',
  sandbox,
  { filename: 'docs/data.js' }
);
const narrowPaths = sandbox.__testNarrowPaths;
assert.ok(narrowPaths && typeof narrowPaths === 'object', 'NARROW_PATHS must load from docs/data.js');

const prefixes = [];
for (const [pathId, items] of Object.entries(narrowPaths)) {
  assert.ok(Array.isArray(items), `NARROW_PATHS[${pathId}] must be an array`);
  for (const item of items) {
    for (const prefix of item.majorCodes || []) prefixes.push({ pathId, prefix });
  }
}
assert.ok(prefixes.length > 0, 'at least one NARROW_PATHS majorCodes prefix must be checked');

const unresolvedPrefixes = prefixes.filter(
  ({ prefix }) => !motives.some((motive) => typeof motive.code === 'string' && motive.code.startsWith(prefix))
);
assert.deepEqual(
  unresolvedPrefixes,
  [],
  'each NARROW_PATHS majorCodes prefix must resolve to at least one micro-motive'
);

const invalidActiveMajors = [];
for (const major of majors) {
  if (major.motive_driven !== true) continue;
  const codes = major.micro_motive_codes;
  if (!Array.isArray(codes) || codes.length === 0) {
    invalidActiveMajors.push({ id: major.id, reason: 'missing micro_motive_codes' });
    continue;
  }
  for (const code of codes) {
    if (!motiveCodes.has(code)) invalidActiveMajors.push({ id: major.id, code, reason: 'code absent from micro_motives.json' });
  }
}
assert.deepEqual(
  invalidActiveMajors,
  [],
  'every motive_driven=true major must reference existing micro-motive codes'
);

console.log(`R2 motive-route contract: PASS (${prefixes.length} route-prefix occurrences, ${new Set(prefixes.map((item) => item.prefix)).size} unique prefixes, all active-major codes resolved)`);
