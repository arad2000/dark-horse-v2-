'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const majors = JSON.parse(fs.readFileSync(path.join(root, 'majors_database_v2.json'), 'utf8'));
const motives = JSON.parse(fs.readFileSync(path.join(root, 'micro_motives.json'), 'utf8'));

assert.equal(majors.length, 230, 'major catalog must contain exactly 230 entries');
assert.deepEqual(
  majors.map((major) => major.id),
  Array.from({ length: 230 }, (_, index) => index + 1),
  'major IDs must be contiguous from 1 through 230'
);

const motiveCodes = motives.map((motive) => motive.code);
assert.equal(motives.length, 1393, 'approved micro-motive count must remain 1,393');
assert.equal(new Set(motiveCodes).size, 1393, 'micro-motive codes must be unique');

const knownCodes = new Set(motiveCodes);
const orphaned = [];
for (const major of majors) {
  for (const code of major.micro_motive_codes || []) {
    if (!knownCodes.has(code)) orphaned.push({ majorId: major.id, code });
  }
}
assert.deepEqual(orphaned, [], 'catalog must not reference absent micro-motives');

console.log('R1 catalog contract: PASS (230 majors, IDs 1..230, 1,393 unique motives, no orphan codes)');
