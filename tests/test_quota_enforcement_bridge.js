const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('docs/quota_enforcement_bridge.js', 'utf8');

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

  const context = {
    console,
    localStorage,
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
    Object,
    Number,
    String,
    JSON,
    Error
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(source, context);

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

  console.log('quota_enforcement_bridge regression: PASS');
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
