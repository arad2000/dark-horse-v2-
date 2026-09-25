const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('docs/purchase_ui_fix.js', 'utf8');
const commercialSource = fs.readFileSync('docs/commercial_ui.js', 'utf8');
const indexSource = fs.readFileSync('docs/index.html', 'utf8');

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

function assertPaymentHop(query, expectedReplace){
  const calls = [];
  const context = {
    console,
    URL,
    URLSearchParams,
    setTimeout() {},
    document: {
      readyState: 'complete',
      body: {},
      getElementById() { return null; },
      querySelectorAll() { return []; },
      addEventListener() {}
    },
    location: {
      href: 'https://asbe-siah.ir/',
      search: query,
      replace(value) { calls.push(value); }
    },
    MutationObserver: class { observe() {} },
    addEventListener() {}
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(commercialSource, context);
  assert.deepStrictEqual(calls, expectedReplace);
}

async function run({ delay }) {
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
    location,
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
  const success = await run({ delay: 50 });
  assert.strictEqual(success.button.disabled, false);
  assert.strictEqual(success.button.textContent, 'پرداخت');
  assert.strictEqual(success.status.hidden, false);
  assert.strictEqual(success.spin.hidden, true);
  assert.match(success.statusText.textContent, /آماده پرداخت/);
  assert.strictEqual(success.error.textContent, '');

  assertPaymentHop(
    '?dh_pay=https%3A%2F%2Fsandbox.zarinpal.com%2Fpg%2FStartPay%2FABC123',
    ['https://sandbox.zarinpal.com/pg/StartPay/ABC123']
  );
  assertPaymentHop(
    '?dh_pay=https%3A%2F%2Fevil.example%2Fpay',
    []
  );

  const timeout = await run({ delay: 2500 });
  assert.strictEqual(timeout.button.disabled, false);
  assert.strictEqual(timeout.button.textContent, 'تلاش دوباره');
  assert.strictEqual(timeout.status.hidden, false);
  assert.strictEqual(timeout.spin.hidden, true);
  assert.match(timeout.error.textContent, /بیش از ۲ ثانیه/);

  const direct = await run({ delay: 50 });
  direct.button.onclick({ preventDefault() {}, stopPropagation() {} });
  assert.strictEqual(direct.location.href, 'https://example.com/pay');

  assert.match(commercialSource, /function siteHopPayUrl\(paymentUrl\)[\s\S]*?https:\/\/asbe-siah\.ir\/\?dh_pay=/);
  assert.match(commercialSource, /function isZarinpalPaymentUrl\(url\)[\s\S]*?sandbox\.zarinpal\.com/);
  assert.match(commercialSource, /var u=isZarinpalPaymentUrl\(raw\)\?siteHopPayUrl\(raw\):raw/);
  assert.match(commercialSource, /AndroidBridge\.openExternalUrl\(u\)/);
  assert.match(commercialSource, /function handlePaymentHop\(\)[\s\S]*?isZarinpalPaymentUrl\(decoded\)/);
  assert.match(commercialSource, /window\.location\.replace\(decoded\)/);
  assert.match(commercialSource, /از همین صفحه به درگاه امن می‌روید/);
  assert.doesNotMatch(commercialSource, /window\.open\(u/);
  assert.doesNotMatch(commercialSource, /dh-pay-intent/);
  assert.doesNotMatch(commercialSource, /dh-pay-chrome/);
  assert.match(indexSource, /commercial_ui\.js\?v=37/);

  console.log('purchase/payment referer-hop regression: PASS');
})();
