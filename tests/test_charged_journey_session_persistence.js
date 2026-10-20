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
  const persistence = extractBetween(appSource, 'function durableJourneySessionIdForSave()', '\nfunction clearSession()');
  const requestBuilder = extractBetween(appSource, 'function buildJourneyAnalysisRequest(', '\nfunction journeyAnalysisErrorHTML(');
  const localStorage = storage({
    dh_auth_v1: JSON.stringify({ token: 'commercial-token-test' }),
    dh_pending_journey_session_id: 'journey-uuid-charge-123',
    dh_quota_charged_session_v1: 'journey-uuid-charge-123',
    darkhorse_session_v2: JSON.stringify({ sessionId: 'stale-before-charge', stage: 'splash' })
  });
  const sandbox = { localStorage, state: makeState('stale-before-charge', 'splash'), progressHTML: () => '<progress></progress>' };
  vm.createContext(sandbox);
  vm.runInContext(persistence + '\n' + requestBuilder, sandbox);

  // Confirmed charge: exact charged UUID supersedes stale in-memory and stored state.
  sandbox.saveSession();
  let saved = JSON.parse(localStorage.getItem('darkhorse_session_v2'));
  assert.equal(sandbox.state.sessionId, 'journey-uuid-charge-123');
  assert.equal(saved.sessionId, 'journey-uuid-charge-123');
  assert.equal(localStorage.getItem('dh_pending_journey_session_id'), 'journey-uuid-charge-123');

  // Each journey step and save must preserve the same UUID.
  for (const stage of ['realm', 'subRealm', 'narrowPath', 'swipe', 'strategies', 'values', 'choice']) {
    sandbox.state.stage = stage;
    sandbox.saveSession();
    saved = JSON.parse(localStorage.getItem('darkhorse_session_v2'));
    assert.equal(saved.sessionId, 'journey-uuid-charge-123', 'session lost while saving stage ' + stage);
  }

  // Reload: fresh JS state must recover the charged UUID from the durable session.
  sandbox.state = makeState(null, 'splash');
  assert.equal(sandbox.loadSession(), true);
  assert.equal(sandbox.state.sessionId, 'journey-uuid-charge-123');
  assert.equal(JSON.parse(localStorage.getItem('darkhorse_session_v2')).sessionId, 'journey-uuid-charge-123');

  // Results request after reload uses the same UUID and the authenticated commercial bearer.
  const request = sandbox.buildJourneyAnalysisRequest({ micro_motives: ['MOTIVE-TEST'] });
  assert.equal(request.headers.Authorization, 'Bearer commercial-token-test');
  assert.equal(JSON.parse(request.body).session_id, 'journey-uuid-charge-123');

  // A stale UUID without its matching confirmed-charge marker must not be sent.
  localStorage.removeItem('dh_pending_journey_session_id');
  localStorage.setItem('darkhorse_session_v2', JSON.stringify({ sessionId: 'uncharged-or-stale-id', stage: 'choice' }));
  sandbox.state.sessionId = 'uncharged-or-stale-id';
  let rejected = null;
  try { sandbox.buildJourneyAnalysisRequest({}); } catch (error) { rejected = error; }
  assert.equal(rejected && rejected.code, 'JOURNEY_SESSION_REQUIRED');

  // Prevent a regression where a logged-in button directly bypasses commercial charge.
  assert.equal((commercialSource.match(/global\.DHShell\.startJourney\(\)/g) || []).length, 1,
    'commercial module may invoke shell directly only after charging');
  assert.match(commercialSource, /persistChargedJourneySession\(sessionId\)/);
  assert.match(commercialSource, /await global\.DHShell\.startJourney\(\)/);
  assert.match(shellSource, /authorizedCommercialJourneySessionId/);
  assert.match(shellSource, /dh_quota_charged_session_v1/);
  assert.match(quotaSource, /pending && pending === String\(charged\)/);

  console.log('Charged journey session persistence: PASS (charge → stages → reload → Bearer + same session_id)');
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
