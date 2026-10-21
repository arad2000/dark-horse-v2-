const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const dataSource = fs.readFileSync(path.join(root, 'docs', 'data.js'), 'utf8');
const indexSource = fs.readFileSync(path.join(root, 'docs', 'index.html'), 'utf8');
const majors = JSON.parse(fs.readFileSync(path.join(root, 'majors_database_v2.json'), 'utf8'));
const motives = JSON.parse(fs.readFileSync(path.join(root, 'docs', 'data', 'micro_motives.json'), 'utf8'));
assert.ok(Array.isArray(majors), 'majors_database_v2.json must be an array');
assert.ok(Array.isArray(motives), 'docs/data/micro_motives.json must be an array');
const motiveCodes = new Set(motives.map((item) => item.code));

assert.match(
  indexSource,
  /src="data\.js\?v=motives-1393-catalog-230-v1&narrow-fix=1&wood-fix=1"/,
  'docs/index.html must load clean single src for data.js without duplicate data.js?v= concatenation'
);
assert.ok(
  !indexSource.includes('v1data.js'),
  'docs/index.html must not contain duplicated data.js?v= substrings inside src attribute'
);

const sandbox = {};
vm.runInNewContext(
  dataSource + '\nthis.__testSubRealms = SUB_REALMS;\nthis.__testNarrowPaths = NARROW_PATHS;',
  sandbox,
  { filename: 'docs/data.js' }
);
const subRealms = sandbox.__testSubRealms;
const narrowPaths = sandbox.__testNarrowPaths;
assert.ok(subRealms && typeof subRealms === 'object', 'SUB_REALMS must load from docs/data.js');
assert.ok(narrowPaths && typeof narrowPaths === 'object', 'NARROW_PATHS must load from docs/data.js');

const subRealmPrefixes = [];
const subRealmMap = new Map();
for (const [realmId, items] of Object.entries(subRealms)) {
  assert.ok(Array.isArray(items), `SUB_REALMS[${realmId}] must be an array`);
  for (const item of items) {
    subRealmMap.set(item.id, new Set(item.majorCodes || []));
    for (const prefix of item.majorCodes || []) {
      subRealmPrefixes.push({ realmId, subRealmId: item.id, prefix });
    }
  }
}

const prefixes = [];
const narrowPathMap = new Map();
for (const [pathId, items] of Object.entries(narrowPaths)) {
  assert.ok(Array.isArray(items), `NARROW_PATHS[${pathId}] must be an array`);
  const unionSet = new Set();
  for (const item of items) {
    for (const prefix of item.majorCodes || []) {
      unionSet.add(prefix);
      prefixes.push({ pathId, itemId: item.id, prefix });
    }
  }
  narrowPathMap.set(pathId, unionSet);
}
assert.ok(prefixes.length > 0, 'NARROW_PATHS must declare at least one majorCodes prefix');

// Bidirectional sync check: SUB_REALMS[subId].majorCodes <-> NARROW_PATHS[subId] union
const bidirectionalMismatches = [];
for (const [subId, subSet] of subRealmMap.entries()) {
  const narrowSet = narrowPathMap.get(subId) || new Set();
  const missingInNarrow = [...subSet].filter((p) => !narrowSet.has(p));
  const missingInSub = [...narrowSet].filter((p) => !subSet.has(p));
  if (missingInNarrow.length || missingInSub.length) {
    bidirectionalMismatches.push({ subId, missingInNarrow, missingInSub });
  }
}
assert.deepEqual(
  bidirectionalMismatches,
  [],
  'SUB_REALMS and NARROW_PATHS majorCodes must be bidirectionally synchronized for every sub-realm'
);

// Explicit WOOD- (Wood Engineering, major 76) vs WW- (Water Engineering, major 56) separation check
const uniquePrefixSet = new Set(prefixes.map((item) => item.prefix));
assert.ok(uniquePrefixSet.has('WOOD-'), 'WOOD- prefix must exist in NARROW_PATHS');
assert.ok(uniquePrefixSet.has('WW-'), 'WW- prefix must remain distinct in NARROW_PATHS');
assert.ok(subRealmMap.get('builder-transform').has('WOOD-'), 'builder-transform must include WOOD-');
assert.ok(!subRealmMap.get('builder-transform').has('WW-'), 'builder-transform must not conflate WW- with WOOD-');
assert.ok(subRealmMap.get('builder-structure').has('WW-'), 'builder-structure must retain WW-');

const unmatchedPrefixes = prefixes.filter(
  ({ prefix }) => !motives.some((motive) => typeof motive.code === 'string' && motive.code.startsWith(prefix))
);
assert.deepEqual(
  unmatchedPrefixes,
  [],
  'every NARROW_PATHS majorCodes prefix must match at least one code in micro_motives.json'
);

const invalidActiveMajors = [];
const unreachableSubRealmMajors = [];
const unreachableNarrowPathMajors = [];
let activeCount = 0;
for (const major of majors) {
  if (major.motive_driven !== true) continue;
  activeCount++;
  const codes = major.micro_motive_codes;
  if (!Array.isArray(codes) || codes.length === 0) {
    invalidActiveMajors.push({ id: major.id, reason: 'empty micro_motive_codes' });
    continue;
  }
  for (const code of codes) {
    if (!motiveCodes.has(code)) invalidActiveMajors.push({ id: major.id, code, reason: 'code absent from micro_motives.json' });
  }
  const hasSubRealm = codes.some((code) => subRealmPrefixes.some(({ prefix }) => code.startsWith(prefix)));
  const hasNarrowPath = codes.some((code) => prefixes.some(({ prefix }) => code.startsWith(prefix)));
  if (!hasSubRealm) unreachableSubRealmMajors.push({ id: major.id, name: major.name, codes });
  if (!hasNarrowPath) unreachableNarrowPathMajors.push({ id: major.id, name: major.name, codes });
}
assert.equal(activeCount, 202, 'catalog must contain 202 motive_driven=true active majors');
assert.deepEqual(
  invalidActiveMajors,
  [],
  'every motive_driven=true major must reference existing micro-motive codes'
);
assert.deepEqual(
  unreachableSubRealmMajors,
  [],
  'every motive_driven=true major must be reachable from at least one SUB_REALMS majorCodes prefix'
);
assert.deepEqual(
  unreachableNarrowPathMajors,
  [],
  'every motive_driven=true major must be reachable from at least one NARROW_PATHS majorCodes prefix'
);

console.log(`R2 motive-route contract: PASS (${prefixes.length} route-prefix occurrences, ${uniquePrefixSet.size} unique prefixes, bidirectional SUB_REALMS<->NARROW_PATHS sync, WOOD-/WW- distinct, all 202 active majors reachable)`);
