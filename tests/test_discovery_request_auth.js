'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const appSource = fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8');
const indexSource = fs.readFileSync(path.join(root, 'docs/index.html'), 'utf8');

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

async function run() {
  const requestHelper = extractBetween(appSource, 'function buildJourneyAnalysisRequest(', '\nfunction journeyAnalysisErrorHTML(');
  const errorHelper = extractBetween(appSource, 'function journeyAnalysisErrorHTML(', '\n// ==================== توابع تحلیل (جدید/تغییر نام)');
  const retryHelper = extractBetween(appSource, 'async function fetchWithRetry(', '\n// ==================== DISPLAY RESULTS');
  assert.ok(appSource.includes("fetchWithRetry(API_BASE + '/api/v2/darkhorse/discover', buildJourneyAnalysisRequest(payload))"));
  assert.ok(appSource.includes("fetchWithRetry(API_BASE + '/api/v2/darkhorse/branch-discovery', buildJourneyAnalysisRequest(payload))"));
  assert.match(indexSource, /app\\.js\\?v=\\d+/);

  const localStorage = storage({
    dh_auth_v1: JSON.stringify({ token: 'commercial-token-123' }),
    dh_quota_charged_session_v1: 'charged-journey-uuid',
    darkhorse_session_v2: JSON.stringify({ sessionId: 'charged-journey-uuid', stage: 'choice' })
  });
  const sandbox = {
    localStorage,
    state: { sessionId: 'charged-journey-uuid' },
    window: {},
    progressHTML: () => '<progress></progress>',
    AbortController,
    setTimeout,
    clearTimeout,
    Promise,
    Error,
    Number,
    Object,
    JSON,
    fetch: async () => ({ ok: true, status: 200 })
  };
  vm.createContext(sandbox);
  vm.runInContext([requestHelper, errorHelper, retryHelper].join('\n\n'), sandbox);

  const request = sandbox.buildJourneyAnalysisRequest({
    micro_motives: ['MOTIVE-001'],
    sjt_answers: { S01: 'A' },
    conjoint_choices: { conj_1: 'B01Q' }
  });
  assert.equal(request.method, 'POST');
  assert.equal(request.headers.Authorization, 'Bearer commercial-token-123');
  assert.equal(request.headers['Content-Type'], 'application/json');
  const requestBody = JSON.parse(request.body);
  assert.equal(requestBody.session_id, 'charged-journey-uuid');
  assert.deepEqual(requestBody.micro_motives, ['MOTIVE-001']);
  assert.equal(requestBody.sjt_answers.S01, 'A');

  // A confirmed charge repairs a missing UUID; state and saved journey must converge.
  sandbox.state.sessionId = null;
  localStorage.setItem('darkhorse_session_v2', JSON.stringify({ stage: 'choice' }));
  const recoveredRequest = sandbox.buildJourneyAnalysisRequest({});
  assert.equal(JSON.parse(recoveredRequest.body).session_id, 'charged-journey-uuid');
  assert.equal(sandbox.state.sessionId, 'charged-journey-uuid');
  assert.equal(JSON.parse(localStorage.getItem('darkhorse_session_v2')).sessionId, 'charged-journey-uuid');

  // Never invent a UUID at result time when there is no confirmed charge marker.
  localStorage.removeItem('dh_quota_charged_session_v1');
  sandbox.state.sessionId = null;
  localStorage.setItem('darkhorse_session_v2', JSON.stringify({ stage: 'choice' }));
  let missingSessionError;
  try { sandbox.buildJourneyAnalysisRequest({}); } catch (error) { missingSessionError = error; }
  assert.equal(missingSessionError && missingSessionError.status, undefined);
  assert.equal(missingSessionError && missingSessionError.code, 'JOURNEY_SESSION_REQUIRED');
  const missingSessionHtml = sandbox.journeyAnalysisErrorHTML(missingSessionError, 'majors');
  assert.ok(missingSessionHtml.includes('شناسهٔ سفر آماده نیست'));
  assert.ok(!missingSessionHtml.includes('HTTP 403'), 'local missing session must not masquerade as an HTTP response');

  // Missing/expired commercial auth is reported as 401 before any request is sent.
  localStorage.removeItem('dh_auth_v1');
  let missingAuthError;
  try { sandbox.buildJourneyAnalysisRequest({}); } catch (error) { missingAuthError = error; }
  assert.equal(missingAuthError && missingAuthError.status, undefined);
  assert.equal(missingAuthError && missingAuthError.code, 'AUTH_REQUIRED');
  const missingAuthHtml = sandbox.journeyAnalysisErrorHTML(missingAuthError, 'majors');
  assert.ok(missingAuthHtml.includes('ورود به حساب تجاری لازم است'));
  assert.ok(!missingAuthHtml.includes('HTTP 401'), 'local missing token must not masquerade as an HTTP response');

  const unauthorizedHtml = sandbox.journeyAnalysisErrorHTML({ status: 401 }, 'majors');
  const forbiddenHtml = sandbox.journeyAnalysisErrorHTML({ status: 403 }, 'branches');
  const networkHtml = sandbox.journeyAnalysisErrorHTML({ name: 'TypeError', message: 'Failed to fetch' }, 'majors');
  const serverHtml = sandbox.journeyAnalysisErrorHTML({ status: 503 }, 'majors');
  assert.ok(unauthorizedHtml.includes('ورود دوباره لازم است'));
  assert.ok(forbiddenHtml.includes('دسترسی به سفر تأیید نشد'));
  assert.ok(networkHtml.includes('ارتباط شبکه با سرور برقرار نشد'));
  assert.ok(serverHtml.includes('سرور پاسخ خطا داد'));

  for (const status of [401, 403]) {
    let calls = 0;
    sandbox.fetch = async () => { calls++; return { ok: false, status }; };
    let thrown;
    try {
      await sandbox.fetchWithRetry('https://api.asbe-siah.ir/api/v2/darkhorse/discover', request, 3);
    } catch (error) { thrown = error; }
    assert.equal(thrown && thrown.status, status);
    assert.equal(calls, 1, 'HTTP ' + status + ' must not be retried as a network error');
  }

  console.log('Authenticated discovery request contract: PASS (Bearer, charged session_id, distinct 401/403/network/server errors)');
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
