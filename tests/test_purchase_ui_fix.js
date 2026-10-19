const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
// P0 frontend cache recovery: keep the existing payment contract regression active.
const source = fs.readFileSync('docs/purchase_ui_fix.js', 'utf8');
const commercialSource = fs.readFileSync('docs/commercial_ui.js', 'utf8');
const indexSource = fs.readFileSync('docs/index.html', 'utf8');
const hopBootSource = fs.readFileSync('docs/payment_hop_boot.js', 'utf8');
const externalLinksSource = fs.readFileSync('docs/external_links_fix_v1.js', 'utf8');

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

function commercialHop(query, userAgent, replaceThrows = false) {
  const calls = { href: [], replace: [] };
  const location = {
    search: query,
    _href: 'https://asbe-siah.ir/',
    replace(value) { if (replaceThrows) throw new Error('navigation blocked'); calls.replace.push(value); }
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
    addEventListener() {},
    removeEventListener() {},
    visibilityState: 'visible'
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(commercialSource, context);
  return calls;
}

async function runPurchase({ delay, userAgent = '', journeyCalls = [], replaceThrows = false }) {
  const overlay = makeElement('dh-commercial-overlay');
  const button = makeElement('dh-buy-now');
  const error = makeElement('dh-buy-err');
  const status = makeElement('dh-buy-status');
  const spin = makeElement('dh-buy-spin');
  const statusText = makeElement('dh-buy-status-text');
  const close = makeElement('dh-buy-close');
  const elements = [overlay, button, error, status, spin, statusText, close];
  const map = Object.fromEntries(elements.map((element) => [element.id, element]));
  const listeners = {};
  const location = { href: '', replacements: [], replace(value) { if (replaceThrows) throw new Error('navigation blocked'); this.replacements.push(value); this.href = value; }, assign(value) { this.href = value; } };
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
    addEventListener(name, callback) { listeners[name] = callback; },
    removeEventListener(name) { delete listeners[name]; },
    clearTimeout,
    navigator: { userAgent, standalone: false },
    matchMedia() { return { matches: false }; },
    AndroidBridge: { openExternalUrl(value) { bridgeCalls.push(value); } },
    DHShell: { startJourney() { journeyCalls.push('startJourney'); } },
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
  return { button, error, status, spin, statusText, location, bridgeCalls, journeyCalls, listeners };
}

(async () => {
  const paymentUrl = 'https://sandbox.zarinpal.com/pg/StartPay/ABC123';
  const expectedHop = 'https://asbe-siah.ir/?dh_pay=https%3A%2F%2Fsandbox.zarinpal.com%2Fpg%2FStartPay%2FABC123';
  const expectedChromeHop = expectedHop + '&dh_chrome=1';
  const expectedFallback = encodeURIComponent(expectedChromeHop);
  const expectedIntent =
    'intent://sandbox.zarinpal.com/pg/StartPay/ABC123' +
    '#Intent;scheme=https;action=android.intent.action.VIEW;category=android.intent.category.BROWSABLE;package=com.android.chrome;S.browser_fallback_url=' + expectedFallback + ';end';
  const expectedLegacyIntent =
    'intent://asbe-siah.ir/?dh_pay=https%3A%2F%2Fsandbox.zarinpal.com%2Fpg%2FStartPay%2FABC123&dh_chrome=1' +
    '#Intent;scheme=https;action=android.intent.action.VIEW;category=android.intent.category.BROWSABLE;package=com.android.chrome;S.browser_fallback_url=' + expectedFallback + ';end';

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
  assert.strictEqual(webView.location.href, paymentUrl, 'embedded Android should try raw Zarinpal URL in-place first');
  assert.deepStrictEqual(webView.location.replacements, [paymentUrl]);
  assert.deepStrictEqual(webView.bridgeCalls, []);
  if (webView.listeners.pagehide) webView.listeners.pagehide();

  const webViewDirectFailure = await runPurchase({
    delay: 50,
    replaceThrows: true,
    userAgent: 'Mozilla/5.0 (Linux; Android 12; wv) AppleWebKit/537.36 Version/4.0 Chrome/120.0 Mobile Safari/537.36'
  });
  webViewDirectFailure.button.onclick({ preventDefault() {}, stopPropagation() {} });
  assert.strictEqual(webViewDirectFailure.location.href, expectedIntent, 'Chrome intent should only be used after direct navigation throws');
  if (webViewDirectFailure.listeners.pagehide) webViewDirectFailure.listeners.pagehide();

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
  assert.deepStrictEqual(embeddedNoFlag.href, []);
  assert.deepStrictEqual(embeddedNoFlag.replace, [paymentUrl], 'site payment hop must try the raw gateway URL before Chrome');

  const embeddedFlag = commercialHop(
    '?dh_pay=' + encodeURIComponent(paymentUrl) + '&dh_chrome=1',
    'Mozilla/5.0 (Linux; Android 12; wv) AppleWebKit/537.36 Version/4.0 Chrome/120.0 Mobile Safari/537.36'
  );
  assert.deepStrictEqual(embeddedFlag.href, []);
  assert.deepStrictEqual(embeddedFlag.replace, [paymentUrl]);

  const embeddedDirectFailure = commercialHop(
    '?dh_pay=' + encodeURIComponent(paymentUrl),
    'Mozilla/5.0 (Linux; Android 12; wv) AppleWebKit/537.36 Version/4.0 Chrome/120.0 Mobile Safari/537.36',
    true
  );
  assert.deepStrictEqual(embeddedDirectFailure.replace, []);
  assert.deepStrictEqual(embeddedDirectFailure.href, [expectedIntent], 'Chrome intent is permitted after a synchronous in-WebView navigation failure');


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
  assert.match(hopFunction, /dh_chrome.*(?:===|!==).*['"]1['"]/);
  assert.match(hopFunction, /window\.location\.replace\(decoded\)/);
  assert.match(commercialSource, /payment\.zarinpal\.com/);
  assert.match(commercialSource, /www\.payment\.zarinpal\.com/);
  assert.match(commercialSource, /encodeURIComponent\(fallback\)/);
  assert.match(hopBootSource, /dh_pay/);
  assert.match(hopBootSource, /action=android\.intent\.action\.VIEW/);
  assert.match(hopBootSource, /category=android\.intent\.category\.BROWSABLE/);
  assert.match(hopBootSource, /package=com\.android\.chrome/);
  assert.match(hopBootSource, /window\.location\.replace\(decoded\)/);
  assert.match(hopBootSource, /dh_chrome.*===.*['\"]1['\"]/);
  assert.match(indexSource, /payment_hop_boot\\.js\\?v=4/);
  assert.match(indexSource, /external_links_fix_v1\.js\?v=6/);
  assert.match(externalLinksSource, /function openExternal\(url\)/);
  assert.match(externalLinksSource, /AndroidBridge &&[\s\S]*openExternalUrl/);
  assert.match(externalLinksSource, /action=android\.intent\.action\.VIEW/);
  assert.match(externalLinksSource, /category=android\.intent\.category\.BROWSABLE/);
  assert.match(externalLinksSource, /package=com\.android\.chrome/);
  assert.match(externalLinksSource, /location\.assign\(target\)/);
  assert.match(source, /function openPayment\(url\)[\s\S]*?location\.replace\(target\)[\s\S]*?chromeIntent\(target, hop\)/, 'purchase patch must use direct gateway navigation before Chrome');
  assert.match(source, /schedule\(goToChrome, DIRECT_GATEWAY_TIMEOUT_MS\)/, 'Chrome must be a delayed fallback when direct navigation does not leave the page');
  assert.match(source, /در حال اتصال به درگاه امن/);
  assert.doesNotMatch(source, /AndroidBridge\.openExternalUrl\(chromeHopUrl/);
  assert.match(commercialSource, /function openExternalPay\(url\)[\s\S]*?location\.replace\(raw\)[\s\S]*?chromeIntent\(raw,hop\)/, 'commercial UI must use direct gateway navigation before Chrome');
  assert.match(commercialSource, /در حال اتصال به درگاه امن/);
  assert.match(commercialSource, /function handlePaymentHop\(\)[\s\S]*?__dhPaymentHopBootHandled/);
  assert.match(hopBootSource, /window\.location\.replace\(decoded\)[\s\S]*?schedule\(launchChrome, 2200\)/, 'pre-SPA hop must try direct navigation before Chrome');
  assert.match(hopBootSource, /dh_chrome=1 is a terminal/);
  assert.match(indexSource, /commercial_ui\.js\?v=44/);
  assert.match(indexSource, /purchase_ui_fix\.js\?v=11/);
  assert.match(indexSource, /payment_hop_boot\.js\?v=4/);
  const paymentHopPosition = indexSource.indexOf('payment_hop_boot.js?v=4');
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
