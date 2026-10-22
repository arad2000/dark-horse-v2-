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
  /src="data\.js\?v=motives-1393-catalog-230-v1&narrow-fix=1&wood-fix=1&copy=grade9-v1"/,
  'docs/index.html must load clean cache-busted src for data.js'
);
assert.ok(
  !indexSource.includes('v1data.js'),
  'docs/index.html must not contain duplicated data.js?v= substrings inside src attribute'
);

const sandbox = {};
vm.runInNewContext(
  dataSource + '\nthis.__testRealms = REALMS;\nthis.__testSubRealms = SUB_REALMS;\nthis.__testNarrowPaths = NARROW_PATHS;',
  sandbox,
  { filename: 'docs/data.js' }
);
const realms = sandbox.__testRealms;
const subRealms = sandbox.__testSubRealms;
const narrowPaths = sandbox.__testNarrowPaths;
assert.ok(Array.isArray(realms), 'REALMS must load from docs/data.js');
assert.ok(subRealms && typeof subRealms === 'object', 'SUB_REALMS must load from docs/data.js');
assert.ok(narrowPaths && typeof narrowPaths === 'object', 'NARROW_PATHS must load from docs/data.js');

// S1 structural lock: 6 REALMS, 32 SUB_REALMS, 105 NARROW_PATHS
assert.equal(realms.length, 6, 'S1 lock requires exactly 6 REALMS');
const totalSubRealms = Object.values(subRealms).reduce((acc, arr) => acc + arr.length, 0);
const totalNarrowPaths = Object.values(narrowPaths).reduce((acc, arr) => acc + arr.length, 0);
assert.equal(totalSubRealms, 32, 'S1 lock requires exactly 32 SUB_REALMS');
assert.equal(totalNarrowPaths, 105, 'S1 lock requires exactly 105 NARROW_PATHS');

// Copy quality, titleless & emoji-free contract across all 143 cards
const emojiRegex = /\p{Extended_Pictographic}/u;
const copyViolations = [];
function validateCard(level, card) {
  if (card.icon !== '') copyViolations.push({ level, id: card.id, reason: 'non-empty icon' });
  if (card.name !== '') copyViolations.push({ level, id: card.id, reason: 'non-empty name/title' });
  if (typeof card.motto !== 'string' || card.motto.trim().length < 10) {
    copyViolations.push({ level, id: card.id, reason: 'missing or too-short motto' });
  }
  if (typeof card.description !== 'string' || card.description.trim().length < 40) {
    copyViolations.push({ level, id: card.id, reason: 'missing or too-short description' });
  }
  if (emojiRegex.test(card.motto || '') || emojiRegex.test(card.description || '')) {
    copyViolations.push({ level, id: card.id, reason: 'emoji detected in copy' });
  }
}
for (const r of realms) validateCard('REALM', r);

const subRealmPrefixes = [];
const subRealmMap = new Map();
for (const [realmId, items] of Object.entries(subRealms)) {
  assert.ok(Array.isArray(items), `SUB_REALMS[${realmId}] must be an array`);
  for (const item of items) {
    validateCard('SUB_REALM', item);
    subRealmMap.set(item.id, new Set(item.majorCodes || []));
    for (const prefix of item.majorCodes || []) {
      subRealmPrefixes.push({ realmId, subRealmId: item.id, prefix });
    }
  }
}

const prefixes = [];
const narrowPathList = [];
const narrowPathMap = new Map();
for (const [pathId, items] of Object.entries(narrowPaths)) {
  assert.ok(Array.isArray(items), `NARROW_PATHS[${pathId}] must be an array`);
  const unionSet = new Set();
  for (const item of items) {
    validateCard('NARROW_PATH', item);
    narrowPathList.push({ subId: pathId, id: item.id, majorCodes: item.majorCodes || [] });
    for (const prefix of item.majorCodes || []) {
      unionSet.add(prefix);
      prefixes.push({ pathId, itemId: item.id, prefix });
    }
  }
  narrowPathMap.set(pathId, unionSet);
}
assert.deepEqual(copyViolations, [], 'all REALMS, SUB_REALMS, and NARROW_PATHS must have valid Grade-9 motto+description with empty name/icon and zero emojis');
assert.ok(prefixes.length > 0, 'NARROW_PATHS must declare at least one majorCodes prefix');

// Strict zero-duplicate prefix/code across all NARROW_PATHS
const seenPrefixToPaths = new Map();
for (const { itemId, prefix } of prefixes) {
  if (!seenPrefixToPaths.has(prefix)) seenPrefixToPaths.set(prefix, []);
  seenPrefixToPaths.get(prefix).push(itemId);
}
const duplicatePrefixes = [...seenPrefixToPaths.entries()].filter(([, list]) => list.length > 1);
assert.deepEqual(
  duplicatePrefixes,
  [],
  'no majorCodes prefix/slice may appear in more than one NARROW_PATH'
);

// Every single micro-motive in micro_motives.json must match at most 1 (and in fact exactly 1) NARROW_PATH
const multiRoutedMotives = [];
for (const motive of motives) {
  const matching = narrowPathList.filter((p) =>
    p.majorCodes.some((pref) => motive.code.startsWith(pref))
  );
  if (matching.length !== 1) {
    multiRoutedMotives.push({ code: motive.code, count: matching.length, paths: matching.map((x) => x.id) });
  }
}
assert.deepEqual(
  multiRoutedMotives,
  [],
  'every micro-motive code in micro_motives.json must map to exactly 1 NARROW_PATH'
);

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
const unexpectedMultiPathMajors = [];
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
  const matchedPaths = narrowPathList.filter((p) =>
    codes.some((code) => p.majorCodes.some((pref) => code.startsWith(pref)))
  );
  if (!hasSubRealm) unreachableSubRealmMajors.push({ id: major.id, name: major.name, codes });
  if (matchedPaths.length === 0) unreachableNarrowPathMajors.push({ id: major.id, name: major.name, codes });
  if (matchedPaths.length > 1) {
    // Sole documented catalog-level cross-prefix hybrid: major #100 (IT-001..003 + DS-001,002,005,006)
    const pathIds = matchedPaths.map((x) => x.id).sort();
    if (!(major.id === 100 && pathIds.length === 2 && pathIds[0] === 'digital-logic' && pathIds[1] === 'logic-data')) {
      unexpectedMultiPathMajors.push({ id: major.id, name: major.name, paths: pathIds });
    }
  }
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
assert.deepEqual(
  unexpectedMultiPathMajors,
  [],
  'every active major except documented hybrid major #100 (IT-/DS-) must map to exactly 1 NARROW_PATH'
);

// Phase 2 Gen-Z UI & Mobile-First Route Card Contracts
const shellCssSource = fs.readFileSync(path.join(root, 'docs', 'shell.css'), 'utf8');
const journeyCssSource = fs.readFileSync(path.join(root, 'docs', 'journey_experience.css'), 'utf8');
const appSource = fs.readFileSync(path.join(root, 'docs', 'app.js'), 'utf8');

assert.match(
  indexSource,
  /href="shell\.css\?v=70&ux=phase4-live-v2" media="print"/,
  'docs/index.html must cache-bust shell.css for visual polish'
);
assert.match(
  indexSource,
  /src="app\.js\?v=72&poles-fix=1&quota-fix=4&copy=grade9-v1&genz=phase2-v1&ux=phase4-live-v2&r=265"/,
  'docs/index.html must cache-bust app.js for visual & navigation UX polish'
);
assert.match(shellCssSource, /#app \.option\.dh-route-card \.dh-route-motto[\s\S]*?font-size:\s*1\.05rem/, 'Route motto must use teen-readable 1.05rem typography');
assert.match(shellCssSource, /#app \.option\.dh-route-card \.dh-route-desc[\s\S]*?font-size:\s*0\.935rem/, 'Route description must use readable 0.935rem typography');
assert.match(journeyCssSource, /\.dh-sigil-box\s*\{[\s\S]*?width:\s*28px;[\s\S]*?height:\s*28px;/, 'Realm sigil container must be compact 28x28px');
assert.match(journeyCssSource, /\.dh-sigil-box svg\s*\{[\s\S]*?width:\s*18px;[\s\S]*?height:\s*18px;/, 'Realm sigil SVG must be compact 18x18px');
for (const selector of [
  '.dh-route-grid',
  '.dh-route-card',
  '.dh-route-motto',
  '.dh-route-desc',
  '.dh-route-check',
  '.dh-selection-pill',
  '.dh-stage-actions'
]) {
  assert.ok(shellCssSource.includes(selector), `docs/shell.css must define ${selector}`);
}

const appEl = { innerHTML: '', style: {} };
const uiSandbox = {
  console: { log() {}, warn() {}, error() {} },
  setTimeout: () => 0,
  clearTimeout: () => {},
  requestAnimationFrame: () => 0,
  addEventListener: () => {},
  removeEventListener: () => {},
  alert: () => {},
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {}, clear: () => {} },
  sessionStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {}, clear: () => {} },
  location: { search: '', pathname: '/', href: 'https://asbe-siah.ir/', reload: () => {} },
  history: { pushState: () => {}, replaceState: () => {} },
  navigator: { userAgent: 'Mozilla/5.0' },
  document: {
    getElementById: (id) => (id === 'app' ? appEl : { style: {}, innerHTML: '', classList: { add() {}, remove() {} }, addEventListener() {} }),
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: () => ({ style: {}, classList: { add() {}, remove() {} }, appendChild() {}, setAttribute() {} }),
    head: { appendChild() {} },
    body: { appendChild() {}, classList: { add() {}, remove() {} } },
    addEventListener: () => {},
    readyState: 'complete'
  },
  fetch: async () => ({ ok: true, json: async () => [] })
};
uiSandbox.window = uiSandbox;
uiSandbox.globalThis = uiSandbox;
vm.createContext(uiSandbox);
vm.runInContext(dataSource, uiSandbox);
vm.runInContext(
  appSource + '\nglobalThis.__ui = { state, renderSplash, renderRealm, toggleRealm, renderSubRealm, toggleSub, renderNarrowPath, togglePath };',
  uiSandbox
);

uiSandbox.__ui.renderSplash();
assert.ok(
  appEl.innerHTML.includes('به شهر رؤیاها خوش آمدی') && appEl.innerHTML.includes('دروازه‌های شهر رؤیاها'),
  'Splash must display concise warm invitation to City of Dreams'
);

uiSandbox.__ui.toggleRealm('explorer');
assert.ok(appEl.innerHTML.includes('dh-route-grid') && appEl.innerHTML.includes('dh-route-card selected'), 'Realm stage must render selected Gen-Z route card');
assert.ok(appEl.innerHTML.includes('قدم به شهر رؤیاها بگذار'), 'Realm stage must display warm invitation header before districts');
const strokeMatches = [...appEl.innerHTML.matchAll(/<svg width="18" height="18"[^>]*stroke="(#[0-9a-fA-F]{6})"/g)].map((m) => m[1].toLowerCase());
assert.equal(strokeMatches.length, 6, 'All 6 realm cards must render compact 18x18 SVGs');
assert.equal(new Set(strokeMatches).size, 6, 'All 6 realm cards must have distinct per-realm SVG colors');
assert.deepEqual(
  new Set(strokeMatches),
  new Set(['#34d399', '#38bdf8', '#a78bfa', '#fbbf24', '#fb7185', '#2dd4bf']),
  '6 realm SVG colors must match healer/builder/explorer/thinker/artist/speaker palette'
);
assert.ok(appEl.innerHTML.includes('width:28px;height:28px'), 'Realm sigil boxes must enforce compact 28x28 container dimensions');
assert.ok(appEl.innerHTML.includes('aria-pressed="true"'), 'Selected realm card must set aria-pressed="true"');
assert.ok(!appEl.innerHTML.includes('option-icon') && !emojiRegex.test(appEl.innerHTML), 'Realm stage must contain zero emojis and zero option-icon');

uiSandbox.__ui.state.completedSubRealms.add('explorer-cosmos');
uiSandbox.__ui.toggleSub('explorer-life', 3);
assert.ok(appEl.innerHTML.includes('dh-route-card selected') && appEl.innerHTML.includes('disabled dh-path-done'), 'SubRealm stage must render both selected and completed states uniformly');
assert.ok(!appEl.innerHTML.includes('option-icon') && !emojiRegex.test(appEl.innerHTML), 'SubRealm stage must contain zero emojis and zero option-icon');

uiSandbox.__ui.state.completedPaths = new Set(['life-nature']);
uiSandbox.__ui.togglePath('life-bioinfo');
assert.ok(appEl.innerHTML.includes('dh-route-card dh-path-card selected') && appEl.innerHTML.includes('dh-route-badge'), 'NarrowPath stage must render selected and completed badge states cleanly');
assert.ok(!appEl.innerHTML.includes('option-icon') && !emojiRegex.test(appEl.innerHTML), 'NarrowPath stage must contain zero emojis and zero option-icon');

console.log(`R2 motive-route & Phase2 Gen-Z UI contract: PASS (S1 6-32-105, ${prefixes.length} unique route entries, 0 duplicates, 1393/1393 1-to-1 motives, 202/202 active majors reachable, mobile-first cards & states verified)`);
