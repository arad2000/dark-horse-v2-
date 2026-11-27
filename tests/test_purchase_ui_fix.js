const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
// P0 frontend cache recovery: keep the existing payment contract regression active.
const source = fs.readFileSync('docs/purchase_ui_fix.js', 'utf8');
const commercialSource = fs.readFileSync('docs/commercial_ui.js', 'utf8');
const indexSource = fs.readFileSync('docs/index.html', 'utf8');
const hopBootSource = fs.readFileSync('docs/payment_hop_boot.js', 'utf8');
const externalLinksSource = fs.readFileSync('docs/external_links_fix_v1.js', 'utf8');
const authApiSource = fs.readFileSync('docs/auth_api_client.js', 'utf8');

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

async function runPurchase({ delay, userAgent = '', journeyCalls = [] }) {
  const overlay = makeElement('dh-commercial-overlay');
  const button = makeElement('dh-buy-now');
  const error = makeElement('dh-buy-err');
  const status = makeElement('dh-buy-status');
  const spin = makeElement('dh-buy-spin');
  const statusText = makeElement('dh-buy-status-text');
  const referralInput = makeElement('dh-buy-referral-code');
  referralInput.value = String(arguments[0] && arguments[0].referralCode || '');
  const referralMessage = makeElement('dh-buy-referral-message');
  referralMessage.hidden = true;
  const close = makeElement('dh-buy-close');
  const elements = [overlay, button, error, status, spin, statusText, referralInput, referralMessage, close];
  const map = Object.fromEntries(elements.map((element) => [element.id, element]));
  const location = { href: '', replace(value) { this.href = value; }, assign(value) { this.href = value; } };
  let observerCallback = null;
  const bridgeCalls = [];
  const referralCalls = [];
  let createPaymentCalls = 0;
  const options = arguments[0] || {};

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
    DHShell: { startJourney() { journeyCalls.push('startJourney'); } },
    DHAuth: {
      isLoggedIn() { return true; },
      setReferralCode(code) {
        referralCalls.push(code);
        if (options.referralError) return Promise.reject(options.referralError);
        return Promise.resolve(options.referralResult || { status: code ? 'applied' : 'direct', purchase_allowed: true });
      },
      createPayment() {
        createPaymentCalls += 1;
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
  await new Promise((resolve) => setTimeout(resolve, 0));
  if (options.start !== false && typeof button.onclick === 'function') {
    button.onclick({ preventDefault() {}, stopPropagation() {} });
    await new Promise((resolve) => setTimeout(resolve, delay >= 2000 ? 2100 : 100));
  }
  return { button, error, status, spin, statusText, referralInput, referralMessage, referralCalls, createPaymentCalls, location, bridgeCalls, journeyCalls };
}

(async () => {
  const paymentUrl = 'https://sandbox.zarinpal.com/pg/StartPay/ABC123';
  const expectedHop = 'https://asbe-siah.ir/?dh_pay=https%3A%2F%2Fsandbox.zarinpal.com%2Fpg%2FStartPay%2FABC123';
  const expectedChromeHop = expectedHop + '&dh_chrome=1';
  const expectedFallback = encodeURIComponent(expectedChromeHop);
  const expectedIntent =
    'intent://asbe-siah.ir/?dh_pay=https%3A%2F%2Fsandbox.zarinpal.com%2Fpg%2FStartPay%2FABC123&dh_chrome=1' +
    '#Intent;scheme=https;action=android.intent.action.VIEW;category=android.intent.category.BROWSABLE;package=com.android.chrome;S.browser_fallback_url=' + expectedFallback + ';end';
  const expectedLegacyIntent = expectedIntent;

  const notStarted = await runPurchase({ delay: 50, start: false });
  assert.strictEqual(notStarted.button.disabled, false);
  assert.strictEqual(notStarted.button.textContent, 'ادامه به پرداخت');
  assert.strictEqual(notStarted.createPaymentCalls, 0, 'opening the purchase modal must not create an order');
  assert.deepStrictEqual(notStarted.referralCalls, [], 'referral code must not be submitted before user confirmation');

  const invalidReferral = await runPurchase({
    delay: 50,
    referralCode: 'BAD!',
    referralResult: { status: 'invalid_ignored', applied: false, purchase_allowed: true }
  });
  assert.deepStrictEqual(invalidReferral.referralCalls, ['BAD!']);
  assert.strictEqual(invalidReferral.createPaymentCalls, 1, 'invalid referral must not block payment creation');
  assert.strictEqual(invalidReferral.referralMessage.hidden, false);
  assert.match(invalidReferral.referralMessage.textContent, /کد معرف معتبر نیست/);
  invalidReferral.button.onclick({ preventDefault() {}, stopPropagation() {} });
  assert.strictEqual(invalidReferral.location.href, paymentUrl);

  const directReferral = await runPurchase({ delay: 50, referralCode: '' });
  assert.deepStrictEqual(directReferral.referralCalls, ['']);
  assert.strictEqual(directReferral.createPaymentCalls, 1);
  assert.match(directReferral.referralMessage.textContent, /بدون کد معرف/);

  const lockedError = new Error('referral attribution is locked after the first successful payment');
  lockedError.status = 409;
  const lockedReferral = await runPurchase({ delay: 50, referralCode: 'NEWCODE', referralError: lockedError });
  assert.strictEqual(lockedReferral.createPaymentCalls, 1, 'locked referral must not block a later purchase');
  assert.strictEqual(lockedReferral.referralInput.disabled, true);
  assert.match(lockedReferral.referralMessage.textContent, /قفل شده است/);

  const journeyCalls = [];
  const desktop = await runPurchase({ delay: 50, journeyCalls });
  assert.strictEqual(desktop.button.disabled, false);
  assert.strictEqual(desktop.button.textContent, 'پرداخت');
  desktop.button.onclick({ preventDefault() {}, stopPropagation() {} });
  assert.strictEqual(desktop.location.href, paymentUrl);
  assert.deepStrictEqual(desktop.bridgeCalls, []);
  assert.deepStrictEqual(desktop.journeyCalls, []);

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
  assert.deepStrictEqual(embeddedNoFlag.href, [expectedLegacyIntent]);
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
  const commercialFunction = (commercialSource.match(/function openExternalPay\([\s\S]*?\n  }\s*\n\s*function showPayFallback/) || [])[0];
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
  assert.match(commercialSource, /کد معرف \(اختیاری\)/);
  assert.match(commercialSource, /dh-buy-referral-code/);
  assert.match(commercialSource, /dh-buy-referral-message/);
  assert.match(authApiSource, /async setReferralCode\(code\)/);
  assert.match(authApiSource, /\/api\/v1\/me\/referral-code/);
  assert.match(authApiSource, /method: 'PUT'/);
  const referralPrepareFunction = (source.match(/async function prepareReferralAndPayment\([\s\S]*?\n    }\n\n    function startPreparation/) || [])[0];
  assert.ok(referralPrepareFunction, 'referral-first checkout function not found');
  assert.ok(referralPrepareFunction.indexOf('await global.DHAuth.setReferralCode') < referralPrepareFunction.indexOf('global.DHAuth.createPayment'), 'referral must be set before payment order creation');
  assert.match(source, /کد معرف معتبر نیست؛ خرید بدون کد معرف ادامه پیدا می‌کند/);
  assert.match(source, /کد معرف پس از نخستین پرداخت موفق قفل شده است/);
  assert.match(commercialSource, /www\.payment\.zarinpal\.com/);
  assert.match(commercialSource, /encodeURIComponent\(fallback\)/);
  assert.match(hopBootSource, /dh_pay/);
  assert.match(hopBootSource, /action=android\.intent\.action\.VIEW/);
  assert.match(hopBootSource, /category=android\.intent\.category\.BROWSABLE/);
  assert.match(hopBootSource, /package=com\.android\.chrome/);
  assert.match(hopBootSource, /window\.location\.replace\(decoded\)/);
  assert.match(hopBootSource, /dh_chrome.*===.*['\"]1['\"]/);
  assert.match(indexSource, /payment_hop_boot.js\?v=3/);
  assert.match(indexSource, /external_links_fix_v1\.js\?v=6/);
  assert.match(externalLinksSource, /function openExternal\(url\)/);
  assert.match(externalLinksSource, /AndroidBridge &&[\s\S]*openExternalUrl/);
  assert.match(externalLinksSource, /action=android\.intent\.action\.VIEW/);
  assert.match(externalLinksSource, /category=android\.intent\.category\.BROWSABLE/);
  assert.match(externalLinksSource, /package=com\.android\.chrome/);
  assert.match(externalLinksSource, /location\.assign\(target\)/);
  assert.match(source, /function openPayment\(url\)[\s\S]*?chromeIntent\(chromeHop, chromeHop\)/);
  assert.match(source, /function openPayment\(url\)[\s\S]*?location\.href = chromeHop/);
  assert.match(source, /chromeIntent\(chromeHop, chromeHop\)/);
  assert.doesNotMatch(source, /AndroidBridge\.openExternalUrl\(chromeHopUrl/);
  assert.match(commercialSource, /function openExternalPay\(url\)[\s\S]*?chromeIntent\(fallback,\s*fallback\)/);
  assert.match(commercialSource, /function openExternalPay\(url\)[\s\S]*?window\.location\.href=fallback/);
  assert.match(indexSource, /commercial_ui\.js\?v=47/);
  assert.match(indexSource, /purchase_ui_fix.js\?v=11/);
  const paymentHopPosition = indexSource.indexOf('payment_hop_boot.js?v=3');
  const appScriptPosition = indexSource.indexOf('app.js?v=');
  assert.ok(paymentHopPosition >= 0 && appScriptPosition > paymentHopPosition, 'payment hop boot must execute before app.js');
  assert.match(hopBootSource, /pageshow/);
  assert.match(hopBootSource, /visibility = ''/);
  assert.match(externalLinksSource, /target', '_blank'/);
  assert.match(externalLinksSource, /package=com\.android\.chrome/);
  assert.match(source, /var overlay = byId\('dh-commercial-overlay'\)/);
  assert.match(source, /global\.__dhInJourney = false/);
  assert.doesNotMatch(commercialSource, /AndroidBridge\.openExternalUrl/);
  assert.doesNotMatch(source, /AndroidBridge\.openExternalUrl/);

  console.log('payment P0 no-blink/no-loop regression: PASS');
})();
