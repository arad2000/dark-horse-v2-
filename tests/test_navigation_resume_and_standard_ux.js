'use strict';

/**
 * End-to-End Frontend UX, Seamless Multi-Stage Navigation, Anytime Home/Exact-Resume
 * & Standard Palette/Copy Contract Test
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');

function makeStorage(seed = {}) {
  const map = new Map(Object.entries(seed));
  return {
    getItem(k) { return map.has(k) ? map.get(k) : null; },
    setItem(k, v) { map.set(k, String(v)); },
    removeItem(k) { map.delete(k); },
    clear() { map.clear(); }
  };
}

function makeEl(id, map) {
  const el = {
    id: id || '',
    innerHTML: '',
    outerHTML: '',
    textContent: '',
    value: '',
    hidden: false,
    disabled: false,
    open: false,
    scrollTop: 0,
    children: [],
    style: { cssText: '', width: '', display: '', opacity: '', border: '', setProperty() {}, removeProperty() {} },
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); },
      remove(c) { this._s.delete(c); },
      toggle(c) { if (this._s.has(c)) this._s.delete(c); else this._s.add(c); },
      contains(c) { return this._s.has(c); }
    },
    hasAttribute() { return false; },
    setAttribute() {},
    getAttribute() { return null; },
    addEventListener() {},
    removeEventListener() {},
    appendChild(child) {
      if (child && child.id && map) map.set(child.id, child);
      return child;
    },
    insertBefore(child) { return child; },
    remove() { if (el.id && map) map.delete(el.id); },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    scrollTo() {},
    scrollIntoView() {}
  };
  return el;
}

async function run() {
  const motivesRaw = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/micro_motives.json'), 'utf8'));
  const questionsRaw = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/questions_v2.json'), 'utf8'));
  const traitMapRaw = JSON.parse(fs.readFileSync(path.join(root, 'docs/trait_map_v3.json'), 'utf8'));

  const localStorage = makeStorage({
    dh_auth_v1: JSON.stringify({ token: 'tok-ux-e2e', user: { id: 7, public_id: 'u-7' } })
  });
  const elements = new Map();
  const getEl = (id) => {
    if (!elements.has(id)) elements.set(id, makeEl(id, elements));
    return elements.get(id);
  };

  let currentScrollY = 0;
  let lastScrolledToY = 0;
  const alerts = [];

  const doc = {
    readyState: 'complete',
    documentElement: makeEl('html', elements),
    scrollingElement: makeEl('scrolling', elements),
    head: makeEl('head', elements),
    body: makeEl('body', elements),
    getElementById: (id) => getEl(id),
    createElement: (tag) => makeEl(tag, elements),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
    removeEventListener() {}
  };

  const sandbox = {
    console,
    localStorage,
    sessionStorage: makeStorage(),
    Date,
    Promise,
    Object,
    Array,
    Set,
    Map,
    Number,
    String,
    Boolean,
    Math,
    RegExp,
    JSON,
    Error,
    TypeError,
    Headers,
    AbortController,
    parseInt,
    parseFloat,
    isNaN,
    isFinite,
    encodeURIComponent,
    decodeURIComponent,
    get scrollY() { return currentScrollY; },
    get pageYOffset() { return currentScrollY; },
    scrollTo(xOrOpt, y) {
      if (typeof xOrOpt === 'object' && xOrOpt) lastScrolledToY = Number(xOrOpt.top || 0);
      else lastScrolledToY = Number(y || 0);
      currentScrollY = lastScrolledToY;
    },
    requestAnimationFrame: (fn) => { if (typeof fn === 'function') fn(); return 1; },
    setTimeout: (fn) => { if (typeof fn === 'function') fn(); return 1; },
    clearTimeout() {},
    setInterval: () => 1,
    clearInterval() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() { return true; },
    confirm: () => true,
    alert: (m) => alerts.push(String(m)),
    location: { href: 'http://localhost:8000/', pathname: '/', search: '', hash: '', origin: 'http://localhost:8000', reload() {} },
    history: { replaceState() {}, pushState() {} },
    navigator: { userAgent: 'node-e2e', clipboard: { writeText: async () => {} } },
    crypto: { randomUUID: () => '11111111-2222-4333-8444-555555555555' },
    document: doc,
    app: getEl('app'),
    fetch: async (url) => {
      const u = String(url);
      if (u.includes('micro_motives.json')) {
        return { ok: true, status: 200, json: async () => motivesRaw };
      }
      if (u.includes('questions_v2.json')) {
        return { ok: true, status: 200, json: async () => questionsRaw };
      }
      if (u.includes('trait_map_v3.json')) {
        return { ok: true, status: 200, json: async () => traitMapRaw };
      }
      return { ok: true, status: 200, json: async () => ({}) };
    }
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);

  for (const rel of [
    'docs/data.js',
    'docs/app.js',
    'docs/journey_experience.js',
    'docs/ux_v2_patch.js',
    'docs/shell.js',
    'docs/stories.js',
    'docs/parents.js',
    'docs/poems.js',
    'docs/genz_results_enhance.js'
  ]) {
    vm.runInContext(fs.readFileSync(path.join(root, rel), 'utf8'), sandbox, { filename: rel });
  }
  vm.runInContext('globalThis.REALMS = REALMS; globalThis.SUB_REALMS = SUB_REALMS; globalThis.NARROW_PATHS = NARROW_PATHS;', sandbox);

  await sandbox.loadQuestions();
  await sandbox.loadMicroMotivesMap();
  await sandbox.loadTraitMap();

  // 1. Verify ux_v2_patch.js preserves .dh-spark-bar progress bar inside sparkChipHTML()
  const chipHtml = sandbox.sparkChipHTML();
  assert.ok(chipHtml.includes('dh-spark-bar') && chipHtml.includes('dh-spark-fill'),
    'ux_v2_patch.js must keep .dh-spark-bar inside sparkChipHTML');

  // 2. Start journey -> select 2 realms, 2 sub-realms, 2 narrow-paths
  sandbox.startNewJourney();
  assert.equal(sandbox.state.stage, 'realm');
  assert.ok(getEl('app').innerHTML.includes('dh-home-chip'), 'Sticky header must include صفحه اول button');
  assert.ok(getEl('app').innerHTML.includes('dh-stage-nav'), 'Sticky header must include interactive stage pills');

  const r1 = sandbox.REALMS[0].id;
  const r2 = sandbox.REALMS[1].id;
  sandbox.toggleRealm(r1);
  sandbox.toggleRealm(r2);
  assert.ok(getEl('app').innerHTML.includes('dh-world-card'), 'Realm cards must have distinct world aura theme');
  assert.ok(getEl('app').innerHTML.includes('dh-synergy-card'), 'Selecting 2 realms must render Live Synergy Banner');
  sandbox.goTo('subRealm');
  assert.ok(getEl('app').innerHTML.includes('dh-district-group'), 'SubRealms must group passages under parent world headers');

  const s1 = sandbox.SUB_REALMS[r1][0].id;
  const s2 = sandbox.SUB_REALMS[r2][0].id;
  sandbox.toggleSub(s1, 6);
  sandbox.toggleSub(s2, 6);
  sandbox.goTo('narrowPath');

  const p1 = sandbox.NARROW_PATHS[s1][0].id;
  const p2 = sandbox.NARROW_PATHS[s2][0].id;
  sandbox.togglePath(p1);
  sandbox.togglePath(p2);

  // 3. NON-DESTRUCTIVE NAVIGATION: step back narrowPath -> subRealm -> realm WITHOUT losing selections!
  sandbox.goBack();
  assert.equal(sandbox.state.stage, 'subRealm');
  assert.deepEqual(Array.from(sandbox.state.selectedNarrowPaths), [p1, p2],
    'Stepping back to subRealm MUST NOT wipe selectedNarrowPaths');

  sandbox.goBack();
  assert.equal(sandbox.state.stage, 'realm');
  assert.deepEqual(Array.from(sandbox.state.selectedSubRealms), [s1, s2],
    'Stepping back to realm MUST NOT wipe selectedSubRealms');
  assert.deepEqual(Array.from(sandbox.state.selectedNarrowPaths), [p1, p2],
    'Stepping back to realm MUST NOT wipe selectedNarrowPaths');

  // Deselecting ONLY r2 prunes ONLY s2/p2 while keeping s1/p1 intact!
  sandbox.toggleRealm(r2);
  assert.deepEqual(Array.from(sandbox.state.selectedSubRealms), [s1]);
  assert.deepEqual(Array.from(sandbox.state.selectedNarrowPaths), [p1]);

  // 4. Direct jump to narrowPath -> Home clean layout (NO active-page banner) -> standard resume via DHShell.startJourney()!
  await sandbox.dhJumpToStage('narrowPath');
  assert.equal(sandbox.state.stage, 'narrowPath');
  currentScrollY = 340;
  sandbox.dhGoHomeKeepPlace();
  assert.ok(!getEl('app').innerHTML.includes('dh-active-place-banner'),
    'Home must NEVER render dh-active-place-banner (removed per UX simplification)');
  assert.strictEqual(typeof sandbox.dhReturnToActivePage, 'undefined',
    'dhReturnToActivePage must be completely removed');
  assert.strictEqual(typeof sandbox.dhGetActivePlaceSummary, 'undefined',
    'dhGetActivePlaceSummary must be completely removed');

  await sandbox.DHShell.startJourney();
  assert.equal(sandbox.state.stage, 'narrowPath');
  assert.deepEqual(Array.from(sandbox.state.selectedNarrowPaths), [p1]);

  // 5. Load Swipe cards -> advance to card #4 -> simulate hard reload (swipeCards = []) -> Home & back via DHShell.startJourney()!
  await sandbox.loadSwipeCards();
  assert.equal(sandbox.state.stage, 'swipe');
  assert.ok(!getEl('app').innerHTML.includes('قلمروها'), 'Swipe UI must not contain legacy قلمروها term');
  assert.ok(getEl('app').innerHTML.includes('dh-swipe-stage') && getEl('app').innerHTML.includes('dh-swipe-stamp--like'),
    'Swipe deck must render 3D layered stack + live drag stamps');
  sandbox.likeCard(true);
  sandbox.likeCard(false);
  sandbox.likeCard(true);
  assert.equal(sandbox.state.swipeIndex, 3); // Card #4 (0-based 3)
  const expectedCardCode = sandbox.state.swipeCards[3].code;

  // Simulate cold reload wiping in-memory arrays before resuming
  sandbox.state.swipeCards = [];
  sandbox.dhGoHomeKeepPlace();
  assert.ok(!getEl('app').innerHTML.includes('dh-active-place-banner'), 'Home must stay free of active-page banner');
  await sandbox.DHShell.startJourney();
  assert.equal(sandbox.state.stage, 'swipe');
  assert.equal(sandbox.state.swipeIndex, 3, 'Must resume on exact card index 3');
  assert.equal(sandbox.state.swipeCards[3].code, expectedCardCode, 'Exact swipe deck order must be restored');

  // 6. Populate 22 sparks -> enter Strategies -> jump to Question #9 -> visit Home + Stories -> return to Q#9!
  for (let i = 0; i < 22 && i < motivesRaw.length; i++) {
    const code = motivesRaw[i].code;
    if (!sandbox.state.likedCodesSet.has(code)) {
      sandbox.state.likedCodes.push(code);
      sandbox.state.likedCodesSet.add(code);
    }
  }
  const liveChipAfterSparks = sandbox.sparkChipHTML();
  assert.ok(liveChipAfterSparks.includes('۲۲ جرقه'),
    'sparkChipHTML must reflect live state.likedCodes count (window.state exposed properly)');
  sandbox.finishSwipe();
  sandbox.goTo('strategies');
  sandbox.answerStrategy(1);
  sandbox.answerStrategy(2);
  sandbox.jumpStrategyQ(8); // Question #9 (0-based 8)
  assert.equal(sandbox.state.currentQuestion, 8);
  assert.ok(getEl('app').innerHTML.includes('dh-progress-wrap'), 'Strategies must render sticky stage nav header');
  assert.ok(getEl('app').innerHTML.includes('dh-q-jumper'), 'Strategies must render interactive question jumper');

  sandbox.dhGoHomeKeepPlace();
  assert.ok(!getEl('app').innerHTML.includes('dh-active-place-banner'),
    'Home must omit active-page resume banner completely');
  assert.ok(!getEl('app').innerHTML.includes('dh-mk2-progress'),
    'Home must completely omit legacy dh-mk2-progress / آخرین فعالیت block from DOM');
  sandbox.DHStories.open();
  assert.ok(!getEl('app').innerHTML.includes('→Excellence'), 'BiDi defect in stories.js must be fixed');
  assert.ok(!getEl('app').innerHTML.includes('dh-st-resume-place'), 'Secondary pages must omit active-place return button');

  await sandbox.DHShell.startJourney();
  assert.equal(sandbox.state.stage, 'strategies');
  assert.equal(sandbox.state.currentQuestion, 8, 'Must return straight to Question #9');

  // Even when history is cleared (as after reload), goBack() walks canonically without resetting answers!
  sandbox.state.history = [];
  sandbox.goBack();
  assert.equal(sandbox.state.stage, 'introStrategies');
  assert.equal(sandbox.state.strategyAnswers[0], 1, 'Answers must stay intact on goBack');

  // 7. Complete Values -> verify VS Split Duel Arena + Live Strategy Mirror -> Results Story Card!
  for (let i = 0; i < 8; i++) sandbox.state.strategyAnswers[i] = i % 4;
  sandbox.jumpStrategyQ(8);
  assert.ok(getEl('app').innerHTML.includes('dh-chapter-bar') && getEl('app').innerHTML.includes('dh-opt-letter'),
    'Strategies must render 5-chapter bar and letter badges');
  assert.ok(getEl('app').innerHTML.includes('dh-live-mirror'),
    'Strategies must render live thinking-style mirror checkpoint');

  for (let i = 0; i < 25; i++) sandbox.state.strategyAnswers[i] = i % 4;
  sandbox.goTo('values');
  assert.ok(getEl('app').innerHTML.includes('dh-duel-arena') && getEl('app').innerHTML.includes('dh-duel-vs'),
    'Values must render dramatic VS Split Duel Cards');
  assert.ok(getEl('app').innerHTML.includes('عمق‌تأثیر') && getEl('app').innerHTML.includes('گستره‌تأثیر'),
    'Value duel cards must display canonical pole badges');

  for (let i = 0; i < 15; i++) sandbox.state.valueAnswers[i] = `Q${i + 1}A`;
  sandbox.goTo('choice');
  assert.ok(getEl('app').innerHTML.includes('btn btn-primary dh-choice-mode-card'), 'Choice page buttons must be bold primary brand buttons');
  assert.ok(
    getEl('app').innerHTML.includes('تحلیل شاخه') &&
    getEl('app').innerHTML.includes('تحلیل دانشگاه') &&
    getEl('app').innerHTML.includes('#f0c040'),
    'Choice page must render bold golden primary buttons for both Branch Analysis and University Analysis'
  );
  sandbox.state.choiceDisabled = true;
  sandbox.render();
  assert.ok(
    getEl('app').innerHTML.includes('disabled aria-disabled="true"') &&
    getEl('app').innerHTML.includes('#222634'),
    'Choice buttons must render distinct disabled state when disabled'
  );
  sandbox.state.choiceDisabled = false;
  sandbox.render();

  sandbox.state.majorsResult = {
    discovered_majors: [
      {
        major_name_fa: 'مهندسی کامپیوتر',
        fit_score: 88,
        raw_components: { m_score: 90, s_score: 84, v_score: 86 },
        personalized_description: 'همخوانی بالا با حل مسئله و ساخت سیستم.',
        evidence: { micro_motives_matched: [{ description: 'طراحی الگوریتم' }] }
      }
    ]
  };
  sandbox.displayResults(sandbox.state.majorsResult, 'majors');
  assert.ok(getEl('app').innerHTML.includes('dh-result-card'), 'Result items must have .dh-result-card');
  assert.ok(getEl('app').innerHTML.includes('dh-story-id-card'), 'Results must render Shareable Gen-Z Story Identity Card');

  sandbox.dhGoHomeKeepPlace();
  assert.ok(!getEl('app').innerHTML.includes('dh-active-place-banner'),
    'Home must omit active-page banner even after viewing Results');
  assert.ok(!getEl('app').innerHTML.includes('مشاهدهٔ دوبارهٔ نتیجه'),
    'Home must not display extra active-page result button');

  console.log('Frontend seamless stage navigation, Home exact-return & standard UX E2E contract: PASS');
}

run().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
