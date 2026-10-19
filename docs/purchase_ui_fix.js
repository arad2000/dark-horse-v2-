/* purchase_ui_fix.js v10 — explicit payment readiness + APK hop contract */
(function (global) {
  'use strict';

  var PREPARE_TIMEOUT_MS = 2000;
  var DIRECT_GATEWAY_TIMEOUT_MS = 2200;
  var CHROME_INTENT_TIMEOUT_MS = 1800;
  var patchSerial = 0;

  function byId(id) { return document.getElementById(id); }
  function text(v) { return String(v == null ? '' : v); }

  function setButton(button, label, disabled) {
    if (!button) return;
    button.disabled = !!disabled;
    button.textContent = label;
    button.style.opacity = disabled ? '.72' : '';
    button.style.cursor = disabled ? 'wait' : '';
  }

  function ensureStatus() {
    var status = byId('dh-buy-status');
    if (status) return status;
    var error = byId('dh-buy-err');
    if (!error || !error.parentNode) return null;
    status = document.createElement('div');
    status.id = 'dh-buy-status';
    status.className = 'dh-commercial-status';
    status.innerHTML = '<span class="dh-commercial-spinner" id="dh-buy-spin"></span><span id="dh-buy-status-text">در حال دریافت لینک پرداخت…</span>';
    error.parentNode.insertBefore(status, error.nextSibling);
    return status;
  }

  function setStatus(kind, message) {
    var status = ensureStatus();
    if (!status) return;
    var spin = byId('dh-buy-spin');
    var label = byId('dh-buy-status-text');
    if (kind === 'loading') {
      status.hidden = false;
      status.style.color = '#9f957f';
      if (spin) spin.hidden = false;
    } else if (kind === 'ready') {
      status.hidden = false;
      status.style.color = '#80d49a';
      if (spin) spin.hidden = true;
    } else {
      status.hidden = false;
      status.style.color = '#ff8787';
      if (spin) spin.hidden = true;
    }
    if (label) label.textContent = message;
  }

  function setError(message, warning) {
    var error = byId('dh-buy-err');
    if (!error) return;
    error.textContent = message || '';
    error.style.color = warning ? '#f0c040' : '';
  }

  function paymentErrorText(error) {
    var message = text(error && error.message ? error.message : error);
    if (/timeout/i.test(message)) {
      return 'آماده‌سازی درگاه بیش از ۲ ثانیه طول کشید. برای ادامه، «تلاش دوباره» را بزنید.';
    }
    if (/merchant|not configured|credential|authority/i.test(message)) {
      return 'درگاه هنوز آماده تراکنش نیست؛ وضعیت Merchant ID و فعال‌سازی زرین‌پال را بررسی کنید.';
    }
    if (/network|failed to fetch|abort/i.test(message)) {
      return 'ارتباط با درگاه برقرار نشد؛ اتصال شبکه یا وضعیت سرویس زرین‌پال را بررسی کنید.';
    }
    return message || 'ایجاد درخواست پرداخت ناموفق بود. برای ادامه، «تلاش دوباره» را بزنید.';
  }

  function isEmbeddedAndroid() {
    var ua = String(global.navigator && global.navigator.userAgent || '');
    if (!/Android/i.test(ua)) return false;
    var standalone = false;
    try {
      standalone = !!(global.matchMedia && global.matchMedia('(display-mode: standalone)').matches);
    } catch (_) {}
    if (global.navigator && global.navigator.standalone) standalone = true;
    return standalone || /; wv\)/i.test(ua) || /WebView/i.test(ua) || /Version\/4\.0 Chrome/i.test(ua);
  }

  function siteHopPayUrl(paymentUrl) {
    return 'https://asbe-siah.ir/?dh_pay=' + encodeURIComponent(String(paymentUrl));
  }

  function chromeHopUrl(paymentUrl) {
    return siteHopPayUrl(paymentUrl) + '&dh_chrome=1';
  }

  function chromeIntent(url, fallbackUrl) {
    var target = String(url);
    var fallback = String(fallbackUrl || target);
    var hostpath = target.replace(/^https?:\/\//, '');
    return 'intent://' + hostpath +
      '#Intent;scheme=https;action=android.intent.action.VIEW;' +
      'category=android.intent.category.BROWSABLE;package=com.android.chrome;' +
      'S.browser_fallback_url=' + encodeURIComponent(fallback) + ';end';
  }

  function openPayment(url) {
    if (!url) return false;
    var target = String(url);
    if (!isEmbeddedAndroid()) {
      try { global.location.replace(target); return true; } catch (_) {}
      return false;
    }

    var overlay = byId('dh-commercial-overlay');
    var hop = chromeHopUrl(target);
    try {
      global.__dhInJourney = false;
      global.__dhJourneyStarting = false;
      global.__dhPaymentHandoff = true;
    } catch (_) {}
    setStatus('loading', 'در حال اتصال به درگاه امن…');

    var stopped = false;
    var stage = 'raw';
    var timer = null;

    function clearTimer() {
      if (timer === null) return;
      try { global.clearTimeout(timer); } catch (_) {}
      timer = null;
    }
    function cleanup() {
      if (stopped) return;
      stopped = true;
      clearTimer();
      try { global.removeEventListener('pagehide', onPageHide); } catch (_) {}
      try { document.removeEventListener('visibilitychange', onVisibilityChange); } catch (_) {}
    }
    function onPageHide() { cleanup(); }
    function onVisibilityChange() {
      try { if (document.visibilityState === 'hidden') cleanup(); } catch (_) {}
    }
    function schedule(fn, delay) {
      if (stopped) return;
      clearTimer();
      try {
        timer = global.setTimeout(function () {
          timer = null;
          if (!stopped) fn();
        }, delay);
      } catch (_) {}
    }
    function goToSiteHop() {
      if (stopped) return false;
      stage = 'hop';
      clearTimer();
      try { global.location.replace(hop); return true; } catch (_) {}
      try { global.location.href = hop; return true; } catch (_) {}
      setStatus('error', 'اتصال به درگاه انجام نشد؛ دوباره تلاش کنید.');
      return false;
    }
    function goToChrome() {
      if (stopped || stage !== 'raw') return false;
      stage = 'chrome';
      clearTimer();
      try {
        global.location.href = chromeIntent(target, hop);
        schedule(goToSiteHop, CHROME_INTENT_TIMEOUT_MS);
        return true;
      } catch (_) {}
      return goToSiteHop();
    }

    try {
      global.addEventListener('pagehide', onPageHide);
      document.addEventListener('visibilitychange', onVisibilityChange);
    } catch (_) {}
    try {
      // Preferred path: let Android WebView/PWA navigate to Zarinpal in-place.
      global.location.replace(target);
      schedule(goToChrome, DIRECT_GATEWAY_TIMEOUT_MS);
      return true;
    } catch (_) {
      // Only invoke Chrome immediately when direct navigation actually throws.
      return goToChrome();
    }
  }

  function waitForPayment(payload, serial) {
    var timeout = new Promise(function (_, reject) {
      setTimeout(function () { reject(new Error('payment_prepare_timeout')); }, PREPARE_TIMEOUT_MS);
    });
    return Promise.race([Promise.resolve(payload), timeout]).then(function (payment) {
      if (serial !== patchSerial) throw new Error('payment_prepare_stale');
      var url = payment && (payment.payment_url || payment.paymentUrl || payment.url);
      if (!url) throw new Error('آدرس درگاه از سرور نیامد.');
      return String(url);
    });
  }

  function patchModal() {
    var overlay = byId('dh-commercial-overlay');
    var button = byId('dh-buy-now');
    var error = byId('dh-buy-err');
    if (!overlay || !button || !error || overlay.dataset.dhPurchaseReadyUx === '1') return;
    overlay.dataset.dhPurchaseReadyUx = '1';

    var status = ensureStatus();
    if (status) status.hidden = false;
    setError('');
    setStatus('loading', 'در حال آماده‌سازی لینک پرداخت…');
    setButton(button, 'در حال آماده‌سازی…', true);

    var localSerial = ++patchSerial;
    var readyUrl = null;

    function showFailure(errorValue) {
      if (localSerial !== patchSerial || !byId('dh-commercial-overlay')) return;
      readyUrl = null;
      setStatus('error', 'آماده‌سازی پرداخت ناموفق بود.');
      setError(paymentErrorText(errorValue));
      setButton(button, 'تلاش دوباره', false);
      button.onclick = function (event) {
        if (event) { event.preventDefault(); event.stopPropagation(); }
        if (button.disabled) return;
        startPreparation();
      };
    }

    function showReady(url) {
      if (localSerial !== patchSerial || !byId('dh-commercial-overlay')) return;
      readyUrl = url;
      setError('');
      setStatus('ready', '✓ آماده پرداخت — برای ورود به درگاه «پرداخت» را بزنید.');
      setButton(button, 'پرداخت', false);
      button.onclick = function (event) {
        if (event) { event.preventDefault(); event.stopPropagation(); }
        if (!readyUrl || button.disabled) return;
        setButton(button, 'در حال انتقال…', true);
        if (!openPayment(readyUrl)) {
          setError('در باز کردن درگاه مشکلی پیش آمد؛ «تلاش دوباره» را بزنید.');
          setButton(button, 'تلاش دوباره', false);
          readyUrl = null;
          setStatus('error', 'انتقال به درگاه انجام نشد.');
          button.onclick = function (ev) {
            if (ev) { ev.preventDefault(); ev.stopPropagation(); }
            startPreparation();
          };
        }
      };
    }

    function startPreparation() {
      var nowSerial = ++patchSerial;
      localSerial = nowSerial;
      readyUrl = null;
      setError('');
      setStatus('loading', 'در حال آماده‌سازی لینک پرداخت…');
      setButton(button, 'در حال آماده‌سازی…', true);
      if (!global.DHAuth || typeof global.DHAuth.createPayment !== 'function') {
        showFailure(new Error('کلاینت پرداخت در دسترس نیست.'));
        return;
      }
      var request;
      try { request = global.DHAuth.createPayment(); } catch (errorValue) { showFailure(errorValue); return; }
      waitForPayment(request, localSerial).then(showReady).catch(function (errorValue) {
        if (/payment_prepare_stale/.test(text(errorValue && errorValue.message ? errorValue.message : errorValue))) return;
        showFailure(errorValue);
      });
    }

    var close = byId('dh-buy-close');
    if (close) {
      close.onclick = function (event) {
        if (event) { event.preventDefault(); event.stopPropagation(); }
        patchSerial += 1;
        try { overlay.remove(); } catch (_) {}
      };
    }

    startPreparation();
  }

  function scan() {
    try { patchModal(); } catch (error) { if (global.console) console.error('Purchase UI patch failed:', error); }
  }

  if (document.body && typeof MutationObserver !== 'undefined') {
    new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scan);
  } else {
    setTimeout(scan, 0);
  }
})(window);
