'use strict';

/**
 * End-to-End Quota Contract Test: City of Dreams Navigation vs Full Result Completion
 *
 * Enforces the authoritative quota contract across docs/commercial_ui.js,
 * docs/shell.js, docs/quota_runtime.js, and docs/app.js:
 *  1. Registration grants 1 free credit (credits_remaining = 1); purchases are separate.
 *  2. Entering and repeatedly navigating City of Dreams (splash / realm / subRealm /
 *     narrowPath / spark swipe), switching neighborhoods multiple times, returning to
 *     Home and re-entering, or resetting an unfinished journey NEVER calls
 *     POST /api/v1/me/consume-test, NEVER sets dh_quota_charged_session_v1, and NEVER
 *     decreases credits_remaining.
 *  3. Completing the full journey and requesting results (analyzeMajors / analyzeBranches
 *     -> POST /api/v2/darkhorse/discover | branch-discovery) consumes credit ONCE
 *     (credits_remaining decrements by 1), sets markCharged(sessionId), and reuses that
 *     same charged sessionId across branch-discovery / counsel / reloads with 0 extra charges.
 *  4. Starting a fresh journey when credits_remaining === 0 opens Purchase UI immediately;
 *     after purchasing credits, navigating multiple neighborhoods keeps credits constant
 *     and completing the second journey decrements credits by exactly 1.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');

function extractBetween(source, startText, endText) {
  const start = source.indexOf(startText);
  if (start < 0) throw new Error('Start marker not found: ' + startText);
  const end = source.indexOf(endText, start);
  if (end < 0) throw new Error('End marker not found: ' + endText);
  return source.slice(start, end).trim();
}

function makeStorage(seed = {}) {
  const map = new Map(Object.entries(seed));
  return {
    getItem(k) { return map.has(k) ? map.get(k) : null; },
    setItem(k, v) { map.set(k, String(v)); },
    removeItem(k) { map.delete(k); }
  };
}

function makeElement(id, registry) {
  const elObj = {
    id: id || '',
    innerHTML: '',
    textContent: '',
    hidden: false,
    disabled: false,
    style: { cssText: '', setProperty() {}, removeProperty() {} },
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {},
    getAttribute() { return null; },
    addEventListener() {},
    removeEventListener() {},
    appendChild(child) {
      if (child && child.id && registry) registry.set(child.id, child);
      return child;
    },
    insertBefore(child) { return child; },
    remove() {
      if (elObj.id && registry) registry.delete(elObj.id);
    },
    querySelector(sel) {
      if (sel === '.dh-commercial-modal' && elObj.innerHTML.includes('dh-commercial-modal')) {
        return makeElement('dh-commercial-modal', registry);
      }
      return null;
    },
    querySelectorAll() { return []; },
    scrollIntoView() {}
  };
  return elObj;
}

async function run() {
  const dataSource = fs.readFileSync(path.join(root, 'docs/data.js'), 'utf8');
  const appSource = fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8');
  const shellSource = fs.readFileSync(path.join(root, 'docs/shell.js'), 'utf8');
  const quotaSource = fs.readFileSync(path.join(root, 'docs/quota_runtime.js'), 'utf8');
  const commercialSource = fs.readFileSync(path.join(root, 'docs/commercial_ui.js'), 'utf8');

  // Server ledger state (mirrors live FastAPI + PostgreSQL backend contract)
  let serverCreditsGranted = 1; // Registration -> 1 free credit
  let serverCreditsConsumed = 0;
  const chargedSessions = new Set();
  const networkLog = [];
  let consumeCalls = 0;
  let discoverCalls = 0;
  let branchCalls = 0;
  let counselCalls = 0;
  let uuidCounter = 0;

  function serverCreditsRemaining() {
    return Math.max(0, serverCreditsGranted - serverCreditsConsumed);
  }

  const localStorage = makeStorage({
    dh_auth_v1: JSON.stringify({
      token: 'jwt-registered-user-1',
      user: { id: 101, public_id: 'u-101', phone: '09120000001' }
    })
  });

  class Storage {
    getItem(k) { return localStorage.getItem(k); }
    setItem(k, v) { localStorage.setItem(k, v); }
    removeItem(k) { localStorage.removeItem(k); }
  }

  const elements = new Map();
  function getEl(id) {
    if (!elements.has(id)) elements.set(id, makeElement(id, elements));
    return elements.get(id);
  }

  const documentStub = {
    readyState: 'complete',
    documentElement: makeElement('html', elements),
    head: makeElement('head', elements),
    body: makeElement('body', elements),
    getElementById: (id) => getEl(id),
    createElement: (tag) => makeElement(tag, elements),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
    removeEventListener() {}
  };

  const sandbox = {
    console,
    localStorage,
    sessionStorage: makeStorage(),
    Storage,
    Headers,
    AbortController,
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
    parseInt,
    parseFloat,
    isNaN,
    isFinite,
    encodeURIComponent,
    decodeURIComponent,
    setTimeout: (fn) => { if (typeof fn === 'function') fn(); return 1; },
    clearTimeout() {},
    setInterval: () => 1,
    clearInterval() {},
    scrollTo() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() { return true; },
    confirm: () => true,
    alert() {},
    location: { href: 'https://asbe-siah.ir/', origin: 'https://asbe-siah.ir', search: '', hash: '', reload() {} },
    history: { replaceState() {}, pushState() {} },
    navigator: { userAgent: 'node-test' },
    crypto: { randomUUID: () => '00000000-0000-4000-8000-' + String(++uuidCounter).padStart(12, '0') },
    API_BASE: 'https://api.asbe-siah.ir',
    document: documentStub,
    app: getEl('app'),
    fetch: async (url, init = {}) => {
      const target = String(url);
      networkLog.push(target);

      if (target.includes('/api/v1/me/quota')) {
        const payload = {
          credits_granted: serverCreditsGranted,
          credits_consumed: serverCreditsConsumed,
          credits_remaining: serverCreditsRemaining()
        };
        return { ok: true, status: 200, json: async () => payload, clone: () => ({ json: async () => payload }) };
      }

      if (target.includes('/api/v1/billing/packs')) {
        const payload = { packs: [{ code: 'pack_3', title: 'بسته ۳ آزمون', credits: 3, amount_irr: 300000 }] };
        return { ok: true, status: 200, json: async () => payload, clone: () => ({ json: async () => payload }) };
      }

      if (target.includes('/api/v1/me/consume-test')) {
        consumeCalls += 1;
        const reqBody = JSON.parse(init.body || '{}');
        const sessionUuid = String(reqBody.session_uuid || '');
        assert.ok(sessionUuid.length > 0, 'consume-test must include session_uuid');
        if (chargedSessions.has(sessionUuid)) {
          const payload = {
            consumed: 0,
            already_consumed: true,
            credits_granted: serverCreditsGranted,
            credits_consumed: serverCreditsConsumed,
            credits_remaining: serverCreditsRemaining()
          };
          return { ok: true, status: 200, json: async () => payload, clone: () => ({ json: async () => payload }) };
        }
        if (serverCreditsRemaining() <= 0) {
          const errPayload = { detail: 'اعتبار آزمون کافی نیست.' };
          return { ok: false, status: 402, json: async () => errPayload, clone: () => ({ json: async () => errPayload }) };
        }
        chargedSessions.add(sessionUuid);
        serverCreditsConsumed += 1;
        const payload = {
          consumed: 1,
          already_consumed: false,
          credits_granted: serverCreditsGranted,
          credits_consumed: serverCreditsConsumed,
          credits_remaining: serverCreditsRemaining()
        };
        return { ok: true, status: 200, json: async () => payload, clone: () => ({ json: async () => payload }) };
      }

      if (target.includes('/api/v2/darkhorse/discover') ||
          target.includes('/api/v2/darkhorse/branch-discovery') ||
          target.includes('/api/v2/darkhorse/counsel')) {
        const reqBody = JSON.parse(init.body || '{}');
        const sid = String(reqBody.session_id || '');
        // Mirror live backend _require_charged_journey(req, session_uuid): MUST already be charged!
        if (!chargedSessions.has(sid)) {
          const unchargedPayload = { detail: 'این شناسه سفر شارژ نشده است.' };
          return { ok: false, status: 402, json: async () => unchargedPayload, clone: () => ({ json: async () => unchargedPayload }) };
        }
        if (target.includes('/branch-discovery')) branchCalls += 1;
        else if (target.includes('/counsel')) counselCalls += 1;
        else discoverCalls += 1;
        const okPayload = {
          session_id: sid,
          discovered_majors: [{ id: 1, major_title: 'مهندسی کامپیوتر', match_score: 91 }],
          branches: [{ branch_code: 'math', branch_name: 'ریاضی فیزیک', score: 89 }],
          counsel_text: 'تحلیل مشاوره‌ای آماده است.'
        };
        return { ok: true, status: 200, json: async () => okPayload, clone: () => ({ json: async () => okPayload }) };
      }

      return { ok: true, status: 200, json: async () => ({}), clone: () => ({ json: async () => ({}) }) };
    }
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);

  // Load real catalog data (REALMS, SUB_REALMS, NARROW_PATHS, MICRO_MOTIVES, SJT_QUESTIONS, VALUE_QUESTIONS)
  vm.runInContext(dataSource, sandbox);
  vm.runInContext('globalThis.REALMS = REALMS; globalThis.SUB_REALMS = SUB_REALMS; globalThis.NARROW_PATHS = NARROW_PATHS;', sandbox);
  assert.ok(Array.isArray(sandbox.REALMS) && sandbox.REALMS.length >= 4, 'expected real REALMS catalog');

  // Extract real app.js state + persistence + navigation + result analysis functions
  const appCore = [
    'var state = { stage: "splash", sessionId: null, history: [], selectedRealms: [], selectedSubRealms: [], selectedNarrowPaths: [], likedCodes: [], likedCodesSet: new Set(), strategyAnswers: [], valueAnswers: [], currentQuestion: 0, currentValueQuestion: 0, swipeIndex: 0, totalSwipes: 0, completedPaths: new Set(), completedSubRealms: new Set(), lastPayload: null, cachedMotives: null, majorsResult: null, branchesResult: null, retryCount: 0, journeyFinished: false };',
    'function goTo(st) { state.history.push(state.stage); state.stage = st; saveSession(); render(); }',
    'function render() { app.innerHTML = "<div data-stage=\\"" + state.stage + "\\"></div>"; }',
    'function progressHTML(st) { return "<div data-progress=\\"" + st + "\\"></div>"; }',
    'function loadingHTML(msg) { return "<div class=\\"loading\\">" + msg + "</div>"; }',
    extractBetween(appSource, 'const DH_S_REQUIRED_MESSAGE', '\nfunction dhIsStageUnlocked('),
    extractBetween(appSource, 'function buildPayload()', '\n\nasync function ensureJourneyChargedForResults('),
    'function displayResults(data, type) { state.stage = "results"; state.journeyFinished = true; saveSession(); app.innerHTML = "<div id=\\"results-ready\\" data-type=\\"" + type + "\\"></div>"; }',
    extractBetween(appSource, 'function durableJourneySessionIdForSave()', '\nfunction resumeJourney()'),
    extractBetween(appSource, 'async function ensureJourneyChargedForResults()', '\n// ==================== DISPLAY RESULTS')
  ].join('\n\n');
  vm.runInContext(appCore, sandbox);
  const protocolQuestions = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/questions_v2.json'), 'utf8'));
  sandbox.state.strategyQuestions = protocolQuestions.layers.strategies.questions;
  sandbox.state.valueQuestions = protocolQuestions.layers.values.questions;

  // Provide DHAuth client backed by the same server endpoints
  sandbox.DHAuth = {
    isLoggedIn: () => Boolean(localStorage.getItem('dh_auth_v1')),
    token: () => JSON.parse(localStorage.getItem('dh_auth_v1') || '{}').token || '',
    quota: async () => (await sandbox.fetch('https://api.asbe-siah.ir/api/v1/me/quota')).json(),
    packs: async () => (await sandbox.fetch('https://api.asbe-siah.ir/api/v1/billing/packs')).json(),
    logout: () => localStorage.removeItem('dh_auth_v1')
  };

  // Run REAL shell.js, quota_runtime.js, and commercial_ui.js in the same browser context
  vm.runInContext(shellSource, sandbox);
  vm.runInContext(quotaSource, sandbox);
  vm.runInContext(commercialSource, sandbox);

  // ==================== PHASE 1: REGISTRATION STATE ====================
  assert.equal(serverCreditsRemaining(), 1, 'newly registered user must start with 1 free credit');
  assert.equal(consumeCalls, 0, 'registration must not consume any credit');

  // ==================== PHASE 2: MULTI-NEIGHBORHOOD NAVIGATION ====================
  // Enter City of Dreams via the real commercial start button flow
  await sandbox.DHCommercialUI.startServerAuthorizedJourney();
  assert.equal(sandbox.__dhInJourney, true);
  assert.equal(sandbox.state.stage, 'splash');
  const firstJourneyId = sandbox.state.sessionId;
  assert.ok(firstJourneyId, 'journey entry must prepare a stable uncharged session UUID');
  assert.equal(consumeCalls, 0, 'entering City of Dreams splash MUST NOT call consume-test');
  assert.equal(localStorage.getItem('dh_quota_charged_session_v1'), null, 'markCharged MUST NOT run on entry');
  assert.equal(serverCreditsRemaining(), 1, 'free credit MUST stay 1 on entry');

  // Advance from splash into realms via real startNewJourney()
  sandbox.startNewJourney();
  assert.equal(sandbox.state.stage, 'realm');
  assert.equal(sandbox.state.sessionId, firstJourneyId, 'startNewJourney from splash must keep prepared session UUID');
  assert.equal(consumeCalls, 0);
  assert.equal(serverCreditsRemaining(), 1);

  // Visit 4 different Realms -> SubRealms -> NarrowPaths -> Spark cards WITHOUT finishing journey!
  for (let round = 0; round < 4; round++) {
    const realm = sandbox.REALMS[round % sandbox.REALMS.length];
    sandbox.state.selectedRealms = [realm.id];
    sandbox.goTo('subRealm');

    const subRealmList = Array.isArray(sandbox.SUB_REALMS)
      ? sandbox.SUB_REALMS
      : ((sandbox.SUB_REALMS && sandbox.SUB_REALMS[realm.id]) || []);
    const subRealm = subRealmList[0] || { id: 'sub-' + round };
    sandbox.state.selectedSubRealms = [subRealm.id];
    sandbox.goTo('narrowPath');

    const narrowList = Array.isArray(sandbox.NARROW_PATHS)
      ? sandbox.NARROW_PATHS
      : ((sandbox.NARROW_PATHS && sandbox.NARROW_PATHS[subRealm.id]) || []);
    const narrow = narrowList[0] || { id: 'narrow-' + round };
    sandbox.state.selectedNarrowPaths = [narrow.id];
    sandbox.goTo('introSwipe');
    sandbox.goTo('swipe');
    sandbox.state.likedCodes.push('MOTIVE-00' + (round + 1));
    sandbox.saveSession();

    // User backs out to Home tab mid-exploration and re-enters via commercial gate!
    sandbox.__dhInJourney = false;
    await sandbox.DHCommercialUI.startServerAuthorizedJourney();

    assert.equal(consumeCalls, 0, `round ${round + 1}: navigating realm/subRealm/narrowPath/spark MUST NEVER call consume-test`);
    assert.equal(localStorage.getItem('dh_quota_charged_session_v1'), null, `round ${round + 1}: markCharged MUST remain null`);
    assert.equal(serverCreditsRemaining(), 1, `round ${round + 1}: credits_remaining MUST stay 1`);
    assert.equal(sandbox.state.sessionId, firstJourneyId, `round ${round + 1}: same uncharged sessionId preserved`);
  }

  // User also resets mid-journey via startNewJourney() and picks another neighborhood!
  sandbox.startNewJourney();
  sandbox.state.likedCodes = ['SPORT-001', 'ARCHY-001'];
  sandbox.goTo('strategies');
  sandbox.goTo('values');
  sandbox.goTo('choice');
  assert.equal(consumeCalls, 0, 'all stages up to choice still MUST NOT consume credit');
  assert.equal(serverCreditsRemaining(), 1, 'credits_remaining MUST still be 1 right before requesting results');

  // ==================== PHASE 3: COMPLETE JOURNEY -> SINGLE CHARGE ON DISCOVER ====================
  // This quota-specific harness must satisfy the real S gate before discovery.
  sandbox.state.strategyAnswers = Array.from({length: 25}, (_, i) => i % 5);
  await sandbox.analyzeMajors();
  assert.equal(consumeCalls, 1, 'completing journey and requesting discover MUST consume exactly ONCE');
  assert.equal(discoverCalls, 1, 'discover endpoint reached and succeeded with HTTP 200');
  assert.equal(serverCreditsRemaining(), 0, 'credits_remaining decremented from 1 to 0 only after completed result');
  assert.equal(localStorage.getItem('dh_quota_charged_session_v1'), firstJourneyId);
  assert.equal(sandbox.state.journeyFinished, true);

  // Viewing branch-discovery and AI counsel for the SAME completed journey must NOT charge again
  await sandbox.analyzeBranches();
  const counselRes = await sandbox.fetch('https://api.asbe-siah.ir/api/v2/darkhorse/counsel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile: {}, top_results: [] })
  });
  assert.equal(counselRes.status, 200);
  assert.equal(branchCalls, 1);
  assert.equal(counselCalls, 1);
  assert.equal(consumeCalls, 1, 'branch-discovery + counsel on same completed journey MUST NOT deduct extra credits');
  assert.equal(serverCreditsRemaining(), 0);

  // ==================== PHASE 4: 0 CREDITS BLOCKS 2ND JOURNEY; PURCHASE SEPARATE ====================
  await sandbox.DHCommercialUI.startServerAuthorizedJourney();
  const modalHtmlZeroCredit = getEl('dh-commercial-overlay').innerHTML;
  assert.ok(modalHtmlZeroCredit.includes('اعتبار') || modalHtmlZeroCredit.includes('بسته'),
    'starting a new journey with 0 credits remaining must open purchase modal');
  assert.equal(consumeCalls, 1, 'zero-credit purchase prompt must not call consume-test');

  // Simulate separate credit pack purchase (+3 credits -> credits_remaining = 3)
  serverCreditsGranted += 3;
  assert.equal(serverCreditsRemaining(), 3);

  // Enter City of Dreams for Journey #2 across multiple neighborhoods -> credits stay 3!
  await sandbox.DHCommercialUI.startServerAuthorizedJourney();
  const secondJourneyId = sandbox.state.sessionId;
  assert.notEqual(secondJourneyId, firstJourneyId, 'new journey after completion must receive a fresh session UUID');
  assert.equal(localStorage.getItem('dh_quota_charged_session_v1'), null, 'previous journey charge marker cleared for fresh journey');

  sandbox.startNewJourney();
  sandbox.goTo('subRealm');
  sandbox.goTo('narrowPath');
  sandbox.goTo('swipe');
  assert.equal(serverCreditsRemaining(), 3, 'paid credits MUST stay 3 while exploring neighborhoods in Journey #2');
  assert.equal(consumeCalls, 1, 'no consume-test during Journey #2 neighborhood navigation');

  // Complete Journey #2 -> credits drop 3 -> 2 (exact -1)!
  sandbox.state.likedCodes = ['SPORT-001'];
  sandbox.goTo('choice');
  // This quota-specific harness must satisfy the real S gate before discovery.
  sandbox.state.strategyAnswers = Array.from({length: 25}, (_, i) => i % 5);
  await sandbox.analyzeMajors();
  assert.equal(consumeCalls, 2, 'Journey #2 completion deducts exactly 1 credit');
  assert.equal(discoverCalls, 2);
  assert.equal(serverCreditsRemaining(), 2, 'paid credits decremented from 3 to 2 only upon Journey #2 result');

  console.log('City of Dreams navigation quota guard E2E contract: PASS (0 consume in multi-realm navigation, single charge on completed discover, separate purchase verified)');
}

run().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
