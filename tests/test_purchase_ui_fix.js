const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('docs/purchase_ui_fix.js', 'utf8');

function makeElement(id) {
  return {
    id,
    dataset: {},
    style: {},
    hidden: false,
    disabled: false,
    textContent: '',
    parentNode: null,
    onclick: null,
    nextSibling: null,
    remove() { this.removed = true; }
  };
}

async function run({ delay, userAgent }) {
  const overlay = makeElement('dh-commercial-overlay');
  const button = makeElement('dh-buy-now');
  const error = makeElement('dh-buy-err');
  const status = makeElement('dh-buy-status');
  const spin = makeElement('dh-buy-spin');
  const statusText = makeElement('dh-buy-status-text');
  const close = makeElement('dh-buy-close');
  const elements = [overlay, button, error, status, spin, statusText, close];
  const map = Object.fromEntries(elements.map((element) => [element.id, element]));
  const location = { href: '', assign(value) { this.href = value; } };
  let observerCallback = null;

  const document = {
    readyState: 'complete',
    body: {},
    getElementById(id) { return map[id] || null; },
    createElement() { throw new Error('Unexpected createElement path'); },
    addEventListener() {}
  };

  const context = {
    console,
    document,
    setTimeout,
    Promise,
    navigator: { userAgent },
    location,
    open() { return {}; },
    AndroidBridge: null,
    DHAuth: {
      isLoggedIn() { return true; },
      createPayment() {
        return new Promise((resolve) => setTimeout(() => resolve({ payment_url: 'https://example.com/pay' }), delay));
      }
    },
    MutationObserver: class {
      constructor(callback) { observerCallback = callback; }
      observe() {}
    }
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(source, context);
  observerCallback();
  await new Promise((resolve) => setTimeout(resolve, delay >= 2000 ? 2100 : 100));

  return { button, error, status, spin, statusText, location };
}

(async () => {
  const success = await run({ delay: 50, userAgent: 'Mozilla/5.0' });
  assert.strictEqual(success.button.disabled, false);
  assert.strictEqual(success.button.textContent, 'پرداخت');
  assert.strictEqual(success.status.hidden, false);
  assert.strictEqual(success.spin.hidden, true);
  assert.match(success.statusText.textContent, /آماده پرداخت/);
  assert.strictEqual(success.error.textContent, '');

  const timeout = await run({ delay: 2500, userAgent: 'Mozilla/5.0' });
  assert.strictEqual(timeout.button.disabled, false);
  assert.strictEqual(timeout.button.textContent, 'تلاش دوباره');
  assert.strictEqual(timeout.status.hidden, false);
  assert.strictEqual(timeout.spin.hidden, true);
  assert.match(timeout.error.textContent, /بیش از ۲ ثانیه/);

  const android = await run({ delay: 50, userAgent: 'Mozilla/5.0 (Linux; Android 12)' });
  android.button.onclick({ preventDefault() {}, stopPropagation() {} });
  assert.match(android.location.href, /^intent:\/\//);

  console.log('purchase_ui_fix regression: PASS');
})();
