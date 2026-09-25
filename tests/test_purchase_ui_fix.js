const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
// P0 frontend cache recovery: keep the existing payment contract regression active.
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

function commercialHop(query, userAgent) {
  const calls = { href: [], replace: [] };
  const location = {
    search: query,
    _href: 'https://asbe-siah.ir/',
    replace(value) { calls.replace.push(value); }
  };
  Object.defineProperty(location, 'href', {
    get() { return this._href; },
    set(value) { this._href = value; calls.href.push(value); }
  });
  const context = {
    console,
    URL,
    URLSearchParams,
    encodeURIComponent,
    setTimeout() {},
    navigator: { userAgent: userAgent || '', standalone: false },
    matchMedia() { return { matches: false }; },
    document: {
      readyState: 'complete',
      body: {},
      getElementById() { return null; },
      querySelectorAll() { return []; },
      addEventListener() {}
    },
    location,
    MutationObserver: class { observe() {} },
    addEventListener() {}
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(commercialSource, context);
  return calls;
}

async function runPurchase({ delay, userAgent = '' }) {
  const overlay = makeElement('dh-commercial-overlay');
  const button = makeElement('dh-buy-now');
  const error = makeElement('dh-buy-err');
  const status = makeElement('dh-buy-status');
  const spin = makeElement('dh-buy-spin');
  const statusText = makeElement('dh-buy-status-text');
  const close = makeElement('dh-buy-close');
  const elements = [overlay, button, error, status, spin, statusText, close];
  const map = Object.fromEntries(elements.map((element) => [element.id, element]));
  const location = { href: '', replace(value) { this.href = value; }, assign(value) { this.href = value; } };
  let observerCallback = null;
  const bridgeCalls = [];

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
    navigator: { userAgent, standalone: false },
    matchMedia() { return { matches: false }; },
    AndroidBridge: { openExternalUrl(value) { bridgeCalls.push(value); } },
    DHAuth: {
      isLoggedIn() { return true; },
      createPayment() {
        return new Promise((resolve) => setTimeout(
          () => resolve({ payment_url: 'https://sandbox.zarinpal.com/pg/StartPay/ABC123' }),
          delay
        ));
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
  return { button, error, status, spin, statusText, location, bridgeCalls };
}

(async () => {
  const paymentUrl = 'https://sandbox.zarinpal.com/pg/StartPay/ABC123';
  const expectedHop = 'https://asbe-siah.ir/?dh_pay=https%3A%2F%2Fsandbox.zarinpal.com%2Fpg%2FStartPay%2FABC123';
  const expectedChromeHop = expectedHop + '&dh_chrome=1';
  const expectedFallback = encodeURIComponent(expectedChromeHop);
  const expectedIntent =
    'intent://asbe-siah.ir/?dh_pay=https%3A%2F%2Fsandbox.zarinpal.com%2Fpg%2FStartPay%2FABC123&dh_chrome=1' +
    '#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=' + expectedFallback + ';end';

  const desktop = await runPurchase({ delay: 50 });
  assert.strictEqual(desktop.button.disabled, false);
  assert.strictEqual(desktop.button.textContent, 'پرداخت');
  desktop.button.onclick({ preventDefault() {}, stopPropagation() {} });
  assert.strictEqual(desktop.location.href, paymentUrl);
  assert.deepStrictEqual(desktop.bridgeCalls, []);

  const webView = await runPurchase({
    delay: 50,
    userAgent: 'Mozilla/5.0 (Linux; Android 12; wv) AppleWebKit/537.36 Version/4.0 Chrome/120.0 Mobile Safari/537.36'
  });
  webView.button.onclick({ preventDefault() {}, stopPropagation() {} });
  assert.strictEqual(webView.location.href, expectedIntent);
  assert.deepStrictEqual(webView.bridgeCalls, []);

  const chrome = commercialHop(
    '?dh_pay=' + encodeURIComponent(paymentUrl),
    'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/140.0 Mobile Safari/537.36'
  );
  assert.deepStrictEqual(chrome.href, []);
  assert.deepStrictEqual(chrome.replace, [paymentUrl]);

  const embeddedNoFlag = commercialHop(
    '?dh_pay=' + encodeURIComponent(paymentUrl),
    'Mozilla/5.0 (Linux; Android 12; wv) AppleWebKit/537.36 Version/4.0 Chrome/120.0 Mobile Safari/537.36'
  );
  assert.deepStrictEqual(embeddedNoFlag.href, [expectedIntent]);
  assert.deepStrictEqual(embeddedNoFlag.replace, []);

  const embeddedFlag = commercialHop(
    '?dh_pay=' + encodeURIComponent(paymentUrl) + '&dh_chrome=1',
    'Mozilla/5.0 (Linux; Android 12; wv) AppleWebKit/537.36 Version/4.0 Chrome/120.0 Mobile Safari/537.36'
  );
  assert.deepStrictEqual(embeddedFlag.href, []);
  assert.deepStrictEqual(embeddedFlag.replace, [paymentUrl]);

  const extraOfficialHost = commercialHop(
    '?dh_pay=' + encodeURIComponent('https://payment.zarinpal.com/pg/StartPay/XYZ789') + '&dh_chrome=1',
    'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/140.0 Mobile Safari/537.36'
  );
  assert.deepStrictEqual(extraOfficialHost.href, []);
  assert.deepStrictEqual(extraOfficialHost.replace, ['https://payment.zarinpal.com/pg/StartPay/XYZ789']);

  const evil = commercialHop(
    '?dh_pay=' + encodeURIComponent('https://evil.example/pay') + '&dh_chrome=1',
    'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/140.0 Mobile Safari/537.36'
  );
  assert.deepStrictEqual(evil.href, []);
  assert.deepStrictEqual(evil.replace, []);

  const timeout = await runPurchase({ delay: 2500 });
  assert.strictEqual(timeout.button.disabled, false);
  assert.strictEqual(timeout.button.textContent, 'تلاش دوباره');
  assert.strictEqual(timeout.status.hidden, false);
  assert.strictEqual(timeout.spin.hidden, true);
  assert.match(timeout.error.textContent, /بیش از ۲ ثانیه/);

  const purchaseFunction = (source.match(/function openPayment\([\s\S]*?\n  }\n\n  function waitForPayment/) || [])[0];
  const commercialFunction = (commercialSource.match(/function openExternalPay\([\s\S]*?\n  }\n  function showPayFallback/) || [])[0];
  const hopFunction = (commercialSource.match(/function handlePaymentHop\([\s\S]*?\n  }\n  function chromeIntent/) || [])[0];
  assert.ok(purchaseFunction, 'purchase payment function not found');
  assert.ok(commercialFunction, 'commercial payment function not found');
  assert.ok(hopFunction, 'payment hop function not found');

  assert.doesNotMatch(purchaseFunction, /AndroidBridge\.openExternalUrl/);
  assert.doesNotMatch(commercialFunction, /AndroidBridge\.openExternalUrl/);
  assert.match(purchaseFunction, /!isEmbeddedAndroid\(\)/);
  assert.match(purchaseFunction, /location\.replace\(target\)/);
  assert.match(commercialFunction, /!isEmbeddedAndroid\(\)/);
  assert.match(commercialFunction, /location\.replace\(raw\)/);
  assert.match(commercialFunction, /chromeHopUrl\(raw\)/);
  assert.match(hopFunction, /dh_chrome.*===.*['"]1['"]/);
  assert.match(hopFunction, /window\.location\.replace\(decoded\)/);
  assert.match(commercialSource, /payment\.zarinpal\.com/);
  assert.match(commercialSource, /www\.payment\.zarinpal\.com/);
  assert.match(commercialSource, /encodeURIComponent\(fallback\)/);
  assert.match(indexSource, /commercial_ui\.js\?v=40/);
  assert.match(indexSource, /purchase_ui_fix\.js\?v=5/);
  assert.doesNotMatch(commercialSource, /AndroidBridge\.openExternalUrl/);
  assert.doesNotMatch(source, /AndroidBridge\.openExternalUrl/);

  console.log('payment P0 no-blink/no-loop regression: PASS');
})();
