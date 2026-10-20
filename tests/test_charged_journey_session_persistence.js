'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const appSource = fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8');
const shellSource = fs.readFileSync(path.join(root, 'docs/shell.js'), 'utf8');
const commercialSource = fs.readFileSync(path.join(root, 'docs/commercial_ui.js'), 'utf8');
const quotaSource = fs.readFileSync(path.join(root, 'docs/quota_runtime.js'), 'utf8');

function extractBetween(source, startText, endText) {
  const start = source.indexOf(startText);
  if (start < 0) throw new Error('Start marker not found: ' + startText);
  const end = source.indexOf(endText, start);
  if (end < 0) throw new Error('End marker not found: ' + endText);
  return source.slice(start, end).trim();
}

function storage(seed = {}) {
  const values = new Map(Object.entries(seed));
  return {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
    removeItem(key) { values.delete(key); }
  };
}

function makeState(sessionId, stage) {
  return {
    sessionId: sessionId || null, selectedRealms: [], selectedSubRealms: [],
    selectedNarrowPaths: [], likedCodes: [], strategyAnswers: [], valueAnswers: [],
    currentQuestion: 0, currentValueQuestion: 0, stage: stage || 'splash',
    history: [], swipeIndex: 0, totalSwipes: 0,
    completedPaths: new Set(), completedSubRealms: new Set(), journeyFinished: false
  };
}

async function run() {
  const chargedId = 'journey-uuid-charge-123';
  const localStorage = storage({
    dh_auth_v1: JSON.stringify({ token: 'commercial-token-test', user: { public_id: 'user-test' } }),
    dh_pending_journey_session_id: chargedId,
    darkhorse_session_v2: JSON.stringify({ sessionId: 'stale-before-charge', stage: 'splash' })
  });
  let consumeCalls = 0;

  class Storage {
    constructor() {}
    getItem(key) { return localStorage.getItem(key); }
    setItem(key, value) { localStorage.setItem(key, value); }
    removeItem(key) { localStorage.removeItem(key); }
  }

  const quotaContext = {
    console, localStorage, Storage, Headers, Date, Promise, Object, Number, String, JSON, Error,
    API_BASE: 'https://api.asbe-siah.ir',
    document: { readyState: 'complete', addEventListener() {} },
    crypto: { randomUUID: () => 'should-not-replace-charged-id' },
    setInterval: () => 1,
    clearInterval() {},
    setTimeout: () => 1,
    clearTimeout() {},
    fetch: async (url, init = {}) => {
      const target = String(url);
      if (target.includes('/api/v1/me/consume-test')) {
        consumeCalls += 1;
        assert.equal(JSON.parse(init.body).session_uuid, chargedId);
        return {
          ok: true, status: 200,
          json: async () => ({
            consumed: 1, already_consumed: false, credits_granted: 14,
            credits_consumed: 1, credits_remaining: 13
          }),
          clone() { return { json: async () => ({ consumed: 1 }) }; }
        };
      }
      if (target.includes('/api/v1/me/quota')) {
        return {
          ok: true, status: 200,
          json: async () => ({ credits_granted: 14, credits_consumed: 1, credits_remaining: 13 }),
          clone() { return { json: async () => ({ credits_remaining: 13 }) }; }
        };
      }
      return {
        ok: true, status: 200,
        json: async () => ({ session_id: chargedId }),
        clone() { return { json: async () => ({ session_id: chargedId }) }; }
      };
    }
  };
  quotaContext.window = quotaContext;
  vm.createContext(quotaContext);
  vm.runInContext(quotaSource, quotaContext);

  // Run the actual quota bridge against a mocked successful server consume response.
  const charge = await quotaContext.DHQuotaEnforcement.consumeForJourney(chargedId);
  assert.equal(charge.consumed, 1);
  assert.equal(consumeCalls, 1, 'one successful commercial charge should call consume-test once');
  assert.equal(localStorage.getItem('dh_quota_charged_session_v1'), chargedId);
  assert.equal(JSON.parse(localStorage.getItem('darkhorse_session_v2')).sessionId, chargedId,
    'quota bridge must persist the exact UUID after confirmed charge');

  const persistence = extractBetween(appSource, 'function durableJourneySessionIdForSave()', '\nfunction clearSession()');
  const requestBuilder = extractBetween(appSource, 'function buildJourneyAnalysisRequest(', '\nfunction journeyAnalysisErrorHTML(');
  const sandbox = {
    localStorage,
    state: makeState('stale-before-charge', 'splash'),
    progressHTML: () => '<progress></progress>'
  };
  vm.createContext(sandbox);
  vm.runInContext(persistence + '\n' + requestBuilder, sandbox);

  // Confirmed charge: saveSession must adopt that exact charged UUID, not stale state.
  sandbox.saveSession();
  let saved = JSON.parse(localStorage.getItem('darkhorse_session_v2'));
  assert.equal(sandbox.state.sessionId, chargedId);
  assert.equal(saved.sessionId, chargedId);
  assert.equal(localStorage.getItem('dh_pending_journey_session_id'), chargedId,
    'pending marker must remain until shell start is confirmed');

  // Simulate a reload before start confirmation: the pending charged UUID must survive.
  sandbox.state = makeState(null, 'splash');
  assert.equal(sandbox.loadSession(), true);
  assert.equal(sandbox.state.sessionId, chargedId);
  assert.equal(localStorage.getItem('dh_pending_journey_session_id'), chargedId);

  // Simulate successful shell start; only now may pending be cleared.
  sandbox.state.stage = 'realm';
  sandbox.saveSession();
  localStorage.removeItem('dh_pending_journey_session_id');

  // Each intermediate stage and save must preserve the same UUID after pending clears.
  for (const stage of ['realm', 'subRealm', 'narrowPath', 'swipe', 'strategies', 'values', 'choice']) {
    sandbox.state.stage = stage;
    sandbox.saveSession();
    saved = JSON.parse(localStorage.getItem('darkhorse_session_v2'));
    assert.equal(saved.sessionId, chargedId, 'session lost while saving stage ' + stage);
  }

  // Reload with pending already cleared: state restores from darkhorse_session_v2.
  sandbox.state = makeState(null, 'splash');
  assert.equal(sandbox.loadSession(), true);
  assert.equal(sandbox.state.sessionId, chargedId);
  assert.equal(JSON.parse(localStorage.getItem('darkhorse_session_v2')).sessionId, chargedId);

  // Result request after reload carries the commercial Bearer and the same session UUID.
  const request = sandbox.buildJourneyAnalysisRequest({ micro_motives: ['MOTIVE-TEST'] });
  assert.equal(request.headers.Authorization, 'Bearer commercial-token-test');
  assert.equal(JSON.parse(request.body).session_id, chargedId);
  assert.equal(consumeCalls, 1, 'result request must not consume another credit');

  // A stale UUID without its matching confirmed-charge marker must not be sent.
  localStorage.setItem('darkhorse_session_v2', JSON.stringify({ sessionId: 'uncharged-or-stale-id', stage: 'choice' }));
  sandbox.state.sessionId = 'uncharged-or-stale-id';
  let rejected = null;
  try { sandbox.buildJourneyAnalysisRequest({}); } catch (error) { rejected = error; }
  assert.equal(rejected && rejected.code, 'JOURNEY_SESSION_REQUIRED');

  // Prevent a regression where a logged-in button bypasses commercial charge.
  assert.equal((commercialSource.match(/global\.DHShell\.startJourney\(\)/g) || []).length, 1,
    'commercial module may invoke shell directly only after charging');
  assert.match(commercialSource, /persistChargedJourneySession\(sessionId\)/);
  assert.match(commercialSource, /await global\.DHShell\.startJourney\(\)/);
  assert.match(shellSource, /authorizedCommercialJourneySessionId/);
  assert.match(shellSource, /dh_quota_charged_session_v1/);
  assert.match(quotaSource, /pending && pending === String\(charged\)/);

  console.log('Charged journey session persistence: PASS (server-confirmed charge → stages → reload → Bearer + same session_id)');
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
