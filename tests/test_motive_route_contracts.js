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
  dataSource + '\nthis.__testData = { REALMS, SUB_REALMS, NARROW_PATHS };',
  sandbox,
  { filename: 'docs/data.js' }
);
const routeData = sandbox.__testData;
const realms = routeData && routeData.REALMS;
const subRealms = routeData && routeData.SUB_REALMS;
const narrowPaths = routeData && routeData.NARROW_PATHS;
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

assert.ok(Array.isArray(realms), 'REALMS must load from docs/data.js');
assert.ok(subRealms && typeof subRealms === 'object', 'SUB_REALMS must load from docs/data.js');
const realmIds = new Set(realms.map((realm) => realm.id));
const reachableRoutes = [];
const unreachableSubRealms = [];
for (const realm of realms) {
  const subRealmItems = subRealms[realm.id] || [];
  assert.ok(Array.isArray(subRealmItems), `SUB_REALMS[${realm.id}] must be an array`);
  for (const subRealm of subRealmItems) {
    const paths = narrowPaths[subRealm.id];
    if (!Array.isArray(paths)) {
      unreachableSubRealms.push({ realm: realm.id, subRealm: subRealm.id });
      continue;
    }
    for (const path of paths) reachableRoutes.push({ realm: realm.id, subRealm: subRealm.id, path });
  }
}
assert.deepEqual(unreachableSubRealms, [], 'every SUB_REALMS node must expose its NARROW_PATHS routes');
const orphanRealmGroups = Object.keys(subRealms).filter((realmId) => !realmIds.has(realmId));
assert.deepEqual(orphanRealmGroups, [], 'SUB_REALMS keys must resolve to REALMS');

const missingMajorRoutes = [];
for (const major of majors) {
  if (major.motive_driven !== true) continue;
  const codes = Array.isArray(major.micro_motive_codes) ? major.micro_motive_codes : [];
  const hasDiscoverableRoute = reachableRoutes.some(({ path }) =>
    (path.majorCodes || []).some((prefix) =>
      typeof prefix === 'string' && codes.some((code) =>
        typeof code === 'string' && code.startsWith(prefix)
      )
    )
  );
  if (!hasDiscoverableRoute) {
    missingMajorRoutes.push({ id: major.id, name: major.name, reason: 'no REALMS -> SUB_REALMS -> NARROW_PATHS prefix match' });
  }
}
assert.deepEqual(
  missingMajorRoutes,
  [],
  'every motive_driven=true major must be discoverable through REALMS -> SUB_REALMS -> NARROW_PATHS'
);

console.log(`R2 motive-route contract: PASS (${prefixes.length} route-prefix occurrences, ${new Set(prefixes.map((item) => item.prefix)).size} unique prefixes, ${reachableRoutes.length} reachable routes, all active-major codes and routes resolved)`);
