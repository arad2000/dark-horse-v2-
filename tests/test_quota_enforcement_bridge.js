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
    fetch: async () => {
      consumeCalls += 1;
      return responses[0];
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
  assert.match(indexSource, /quota_runtime\.js\?v=1/);
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

  // A discovery response must not replace the persisted billing identity.
  localStorage.setItem('darkhorse_session_v2', JSON.stringify({ sessionId: 'journey-uuid-1' }));
  context.DHQuotaEnforcement.ensureJourneySession();
  assert.strictEqual(localStorage.getItem('darkhorse_session_v2'), JSON.stringify({ sessionId: 'journey-uuid-1' }));

  console.log('quota_runtime consolidation regression: PASS');
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
