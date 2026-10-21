const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const authSource = fs.readFileSync(path.join(root, 'docs', 'auth_api_client.js'), 'utf8');
const indexSource = fs.readFileSync(path.join(root, 'docs', 'index.html'), 'utf8');
const hopSource = fs.readFileSync(path.join(root, 'docs', 'payment_hop_boot.js'), 'utf8');
const mainApiSource = fs.readFileSync(path.join(root, 'main_v2.py'), 'utf8');

function createStorage() {
  const map = new Map();
  return {
    getItem(k) { return map.has(k) ? map.get(k) : null; },
    setItem(k, v) { map.set(k, String(v)); },
    removeItem(k) { map.delete(k); },
    dump() { return Object.fromEntries(map.entries()); }
  };
}

function createAuthHarness(fetchImpl) {
  const storage = createStorage();
  let nextTimerId = 1;
  const activeTimers = new Map();

  const context = {
    window: null,
    localStorage: storage,
    AbortController,
    fetch: fetchImpl,
    setTimeout(fn, delay) {
      const id = nextTimerId++;
      activeTimers.set(id, { fn, delay });
      return id;
    },
    clearTimeout(id) {
      activeTimers.delete(id);
    },
    JSON,
    Object,
    Number,
    String,
    Date,
    Error
  };
  context.window = context;
  vm.runInNewContext(authSource, context, { filename: 'auth_api_client.js' });
  return { DHAuth: context.DHAuth, storage, activeTimers };
}

function runPaymentHop(search) {
  let replacedWith = null;
  const context = {
    URL,
    URLSearchParams,
    decodeURIComponent,
    encodeURIComponent,
    String,
    navigator: { userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X)', standalone: false },
    document: {
      documentElement: { style: { visibility: '', removeProperty() {} } },
      getElementById() { return null; }
    },
    window: null
  };
  context.window = {
    location: {
      href: 'https://asbe-siah.ir/' + search,
      search,
      replace(target) { replacedWith = target; }
    },
    addEventListener() {},
    matchMedia() { return { matches: false }; },
    document: context.document,
    navigator: context.navigator
  };
  vm.runInNewContext(hopSource, context, { filename: 'payment_hop_boot.js' });
  return replacedWith;
}

(async () => {
  // 1. Static contract checks on auth_api_client.js
  assert.match(authSource, /const\s+REQUEST_TIMEOUT_MS\s*=\s*15000\s*;/);
  assert.match(authSource, /new\s+AbortController\(\)/);
  assert.match(authSource, /clearTimeout\(timer\)/);

  // 2. Runtime check: stalled DHAuth request aborts cleanly at 15000ms with TIMEOUT code & zero leaked timers
  {
    let capturedSignal = null;
    const { DHAuth, activeTimers } = createAuthHarness((_url, opts) => {
      capturedSignal = opts && opts.signal;
      return new Promise((_resolve, reject) => {
        capturedSignal.addEventListener('abort', () => {
          const abortErr = new Error('The operation was aborted.');
          abortErr.name = 'AbortError';
          reject(abortErr);
        });
      });
    });

    const pending = DHAuth.quota();
    assert.equal(activeTimers.size, 1, 'Expected one active timeout timer during in-flight request');
    const [timerEntry] = activeTimers.values();
    assert.equal(timerEntry.delay, 15000, 'Timeout delay must be exactly 15000ms');
    assert.ok(capturedSignal && capturedSignal.aborted === false);

    timerEntry.fn();
    await assert.rejects(
      pending,
      (err) => err && err.code === 'TIMEOUT' && /زمان پاسخ سرور تمام شد/.test(err.message)
    );
    assert.equal(activeTimers.size, 0, 'Timeout timer must be cleared in finally after abort');
  }

  // 3. Runtime check: normal response succeeds, clears timer, and never stores raw password in localStorage
  {
    const { DHAuth, storage, activeTimers } = createAuthHarness(async (_url, opts) => {
      assert.ok(opts && opts.signal, 'Fetch request should carry AbortSignal');
      return {
        ok: true,
        status: 200,
        async json() {
          return {
            token: 'tok-live-1',
            user: { id: 7, phone: '09120000000' },
            credits_remaining: 1,
            credits_consumed: 0,
            credits_granted: 1
          };
        }
      };
    });

    const secretPassword = 'MySuperSecretPassword!99';
    await DHAuth.login('09120000000', secretPassword);
    assert.equal(activeTimers.size, 0, 'Timeout timer must be cleared after normal response');
    const serialized = JSON.stringify(storage.dump());
    assert.doesNotMatch(serialized, new RegExp(secretPassword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }

  // 4. Security & cache-bust contracts on docs/index.html + payment_hop_boot.js + main_v2.py
  assert.match(indexSource, /src="auth_api_client\.js\?v=10&timeout-fix=1"/);
  assert.match(indexSource, /target\.protocol\s*===\s*'https:'\s*&&\s*validHost/);
  for (const host of ['zarinpal.com', 'www.zarinpal.com', 'sandbox.zarinpal.com', 'payment.zarinpal.com', 'www.payment.zarinpal.com']) {
    assert.ok(indexSource.includes(`host === '${host}'`), `Missing Zarinpal host allowlist entry in index.html: ${host}`);
  }
  assert.equal(runPaymentHop('?dh_pay=' + encodeURIComponent('https://evil.example.com/?zarinpal.com')), null);
  assert.equal(runPaymentHop('?dh_pay=' + encodeURIComponent('http://payment.zarinpal.com/pg/StartPay/A001')), null);
  assert.equal(
    runPaymentHop('?dh_pay=' + encodeURIComponent('https://payment.zarinpal.com/pg/StartPay/A001')),
    'https://payment.zarinpal.com/pg/StartPay/A001'
  );
  assert.doesNotMatch(mainApiSource, /allow_origins\s*=\s*\[\s*["']\*["']\s*\][\s\S]{0,160}allow_credentials\s*=\s*True/);

  console.log('Security & DHAuth timeout contracts: PASS');
})();
