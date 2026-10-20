const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('docs/quota_runtime.js', 'utf8');

function storage() {
  const data = new Map();
  return {
    getItem(key) { return data.has(key) ? data.get(key) : null; },
    setItem(key, value) { data.set(key, String(value)); },
    removeItem(key) { data.delete(key); }
  };
}

async function run() {
  const localStorage = storage();
  let consumeCalls = 0;
  const fetchCalls = [];

  const responses = [
    {
      ok: true,
      json: async () => ({
        consumed: 1,
        already_consumed: false,
        credits_granted: 1,
        credits_consumed: 1,
        credits_remaining: 0
      })
    }
  ];

  class Storage {
    constructor() { this._storage = localStorage; }
    getItem(key) { return this._storage.getItem(key); }
    setItem(key, value) { return this._storage.setItem(key, value); }
    removeItem(key) { return this._storage.removeItem(key); }
  }

  const context = {
    console,
    localStorage,
    Storage,
    document: {
      readyState: 'complete',
      addEventListener() {}
    },
    crypto: { randomUUID: () => 'journey-uuid-1' },
    API_BASE: 'https://staging.example',
    Headers,
    fetch: async (url, init = {}) => {
      const urlText = String(url);
      fetchCalls.push({ url: urlText, init });
      if (urlText.includes('/api/v1/me/consume-test')) {
        consumeCalls += 1;
        return responses[0];
      }
      const data = { session_id: 'journey-uuid-1' };
      return {
        ok: true,
        json: async () => data,
        clone() { return { json: async () => data }; }
      };
    },
    Date,
    Promise,
    setInterval,
    clearInterval,
    Object,
    Number,
    String,
    JSON,
    Error
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(source, context);

  const indexSource = fs.readFileSync('docs/index.html', 'utf8');
const commercialSource = fs.readFileSync('docs/commercial_ui.js', 'utf8');
const shellSource = fs.readFileSync('docs/shell.js', 'utf8');
const postAuthSource = fs.readFileSync('docs/post_auth_flow_policy.js', 'utf8');
  assert.match(indexSource, /quota_runtime\.js\?v=4/);
  assert.doesNotMatch(indexSource, /journey_session_boot\.js/);
  assert.doesNotMatch(indexSource, /quota_enforcement_bridge\.js/);
  assert.doesNotMatch(indexSource, /quota_charge_failure_ui\.js/);
  assert.doesNotMatch(indexSource, /quota_consume_session_adapter\.js/);
  assert.match(source, /global\.DHJourneySessionBoot/);
  assert.match(source, /global\.DHQuotaEnforcement/);
  assert.match(source, /dh-quota-charge-error/);
  assert.match(source, /dhQuotaConsumeSessionAdapterWrapped/);

  localStorage.setItem('dh_auth_v1', JSON.stringify({ token: 'test-token', user: { public_id: 'u1' } }));

  const first = await context.DHQuotaEnforcement.consumeForJourney('journey-uuid-1');
  const second = await context.DHQuotaEnforcement.consumeForJourney('journey-uuid-1');

  assert.strictEqual(first.consumed, 1);
  assert.strictEqual(second.local_guard, true);
  assert.strictEqual(consumeCalls, 1);
  assert.strictEqual(localStorage.getItem('dh_quota_charged_session_v1'), 'journey-uuid-1');

  // Discovery and counsel must carry the authenticated, already-charged journey identity.
  localStorage.setItem('darkhorse_session_v2', JSON.stringify({ sessionId: 'journey-uuid-1', stage: 'choice' }));
  await context.fetch('https://api.asbe-siah.ir/api/v2/darkhorse/discover', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ micro_motives: [], sjt_answers: {}, conjoint_choices: {} })
  });
  await context.fetch('https://api.asbe-siah.ir/api/v2/darkhorse/counsel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile: {}, top_results: [] })
  });
  for (const path of ['/api/v2/darkhorse/discover', '/api/v2/darkhorse/counsel']) {
    const request = fetchCalls.find(call => call.url.includes(path));
    assert.ok(request, 'expected protected journey request ' + path);
    assert.strictEqual(request.init.headers.get('Authorization'), 'Bearer test-token');
    assert.strictEqual(JSON.parse(request.init.body).session_id, 'journey-uuid-1');
  }
  assert.strictEqual(consumeCalls, 1, 'discovery/counsel must not consume a second credit');

  const continueMatch = commercialSource.match(/async function continueAfterAuth\(\)\s*\{[\s\S]*?\n  \}/);
  assert.ok(continueMatch, 'commercial continuation gate not found');
  assert.ok(continueMatch[0].includes('consumeForJourney(sessionId)'));
  assert.ok(continueMatch[0].indexOf('consumeForJourney(sessionId)') < continueMatch[0].indexOf('DHShell.startJourney()'),
    'server charge must succeed before the journey begins');
  assert.match(commercialSource, /dh_pending_journey_session_id/);
  assert.match(shellSource, /dh_pending_journey_session_id/);
  assert.match(indexSource, /window\.DHCommercialUI\.startServerAuthorizedJourney\(\)/);
  assert.match(postAuthSource, /#dh-startup-start/);

  console.log('quota runtime + authenticated journey contract regression: PASS');
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
