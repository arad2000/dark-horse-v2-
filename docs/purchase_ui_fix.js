/* purchase_ui_fix.js v12 — referral-first checkout + explicit payment readiness */
(function (global) {
  'use strict';

  var PREPARE_TIMEOUT_MS = 12000;
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

  function setReferralNotice(kind, message) {
    var notice = byId('dh-buy-referral-message');
    if (!notice) return;
    notice.textContent = message || '';
    notice.hidden = !message;
    notice.style.color = kind === 'success' ? '#80d49a' : '#f0c040';
  }

  function paymentErrorText(error, existingPaymentRequest) {
    var message = text(error && error.message ? error.message : error);
    if (/timeout/i.test(message)) {
      return existingPaymentRequest
        ? 'پاسخ ساخت پرداخت بیش از ۱۲ ثانیه طول کشید؛ برای جلوگیری از سفارش تکراری، همان درخواست قبلی بررسی می‌شود.'
        : 'آماده‌سازی پرداخت بیش از ۱۲ ثانیه طول کشید. برای ادامه، «تلاش دوباره» را بزنید.';
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
    try { if (overlay) overlay.remove(); } catch (_) {}
    try {
      global.__dhInJourney = false;
      global.__dhJourneyStarting = false;
      global.__dhPaymentHandoff = true;
    } catch (_) {}
    // Android: open the same-origin site hop first so ZarinPal receives the site's referrer.
    var chromeHop = chromeHopUrl(target);
    try {
      global.location.href = chromeIntent(chromeHop, chromeHop);
      return true;
    } catch (_) {}
    try {
      global.location.href = chromeHop;
      return true;
    } catch (_) {}
    return false;
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
    var referralInput = byId('dh-buy-referral-code');
    if (status) status.hidden = true;
    setError('');
    setReferralNotice('', '');
    setButton(button, 'ادامه به پرداخت', false);

    var localSerial = 0;
    var readyUrl = null;
    var referralLocked = false;
    // Reuse a payment-creation request after timeout; never POST a second order for this modal.
    var paymentRequestPromise = null;
    var paymentRequestTimedOut = false;

    function showFailure(errorValue, expectedSerial) {
      var serial = typeof expectedSerial === 'number' ? expectedSerial : localSerial;
      if (serial !== patchSerial || !byId('dh-commercial-overlay')) return;
      readyUrl = null;
      if (referralInput && !referralLocked) referralInput.disabled = !!paymentRequestPromise;
      setStatus('error', 'آماده‌سازی پرداخت ناموفق بود.');
      setError(paymentErrorText(errorValue, paymentRequestTimedOut));
      setButton(button, paymentRequestTimedOut ? 'بررسی نتیجه' : 'تلاش دوباره', false);
      button.onclick = function (event) {
        if (event) { event.preventDefault(); event.stopPropagation(); }
        if (button.disabled) return;
        startPreparation();
      };
    }

    function showReady(url) {
      if (localSerial !== patchSerial || !byId('dh-commercial-overlay')) return;
      readyUrl = url;
      if (referralInput) referralInput.disabled = true;
      setError('');
      setStatus('ready', '✓ لینک پرداخت آماده شد. برای ورود به درگاه «پرداخت» را بزنید.');
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

    async function prepareReferralAndPayment(serial) {
      // A timed-out POST may still complete on the server. Reattach to the same promise.
      if (paymentRequestPromise) return paymentRequestPromise;
      if (!global.DHAuth || typeof global.DHAuth.createPayment !== 'function') {
        throw new Error('کلاینت پرداخت در دسترس نیست.');
      }

      var code = referralInput ? String(referralInput.value || '').trim() : '';
      if (typeof global.DHAuth.setReferralCode === 'function') {
        try {
          var result = await global.DHAuth.setReferralCode(code);
          if (serial !== patchSerial) throw new Error('payment_prepare_stale');
          var state = result && String(result.status || '');
          if (state === 'invalid_ignored') {
            setReferralNotice('warning', 'کد معرف معتبر نیست؛ خرید بدون کد معرف ادامه پیدا می‌کند.');
          } else if (state === 'applied') {
            setReferralNotice('success', 'کد معرف ثبت شد.');
          } else if (state === 'direct') {
            setReferralNotice('success', 'خرید بدون کد معرف ادامه پیدا می‌کند.');
          } else if (result && result.purchase_allowed === false) {
            throw new Error('ثبت کد معرف مجاز نیست.');
          } else {
            setReferralNotice('', '');
          }
        } catch (errorValue) {
          if (serial !== patchSerial) throw errorValue;
          if (Number(errorValue && errorValue.status) === 409) {
            referralLocked = true;
            if (referralInput) referralInput.disabled = true;
            setReferralNotice(
              'warning',
              'کد معرف پس از نخستین پرداخت موفق قفل شده است؛ تغییر جدید اعمال نشد و خرید با ثبت قبلی ادامه می‌یابد.'
            );
          } else {
            setReferralNotice(
              'warning',
              'ثبت کد معرف انجام نشد؛ خرید با وضعیت قبلی حساب ادامه می‌یابد.'
            );
          }
        }
      } else {
        setReferralNotice(
          'warning',
          'ثبت کد معرف در این نسخه در دسترس نیست؛ خرید با وضعیت قبلی حساب ادامه می‌یابد.'
        );
      }

      if (serial !== patchSerial) throw new Error('payment_prepare_stale');
      var createdPayment = global.DHAuth.createPayment();
      paymentRequestPromise = Promise.resolve(createdPayment);
      var trackedPaymentRequest = paymentRequestPromise;
      trackedPaymentRequest.then(null, function () {
        // Retry only after a pre-timeout, definitive rejection. Once timed out, outcome is unknown.
        if (!paymentRequestTimedOut && paymentRequestPromise === trackedPaymentRequest) {
          paymentRequestPromise = null;
        }
      });
      return trackedPaymentRequest;
    }

    function startPreparation() {
      var nowSerial = ++patchSerial;
      localSerial = nowSerial;
      readyUrl = null;
      setError('');
      if (referralInput && !referralLocked) referralInput.disabled = true;
      setStatus('loading', 'در حال بررسی کد معرف و آماده‌سازی لینک پرداخت…');
      setButton(button, 'در حال آماده‌سازی…', true);

      var request;
      try {
        request = prepareReferralAndPayment(nowSerial);
      } catch (errorValue) {
        showFailure(errorValue, nowSerial);
        return;
      }
      waitForPayment(request, nowSerial).then(showReady).catch(function (errorValue) {
        if (/payment_prepare_stale/.test(text(errorValue && errorValue.message ? errorValue.message : errorValue))) return;
        if (/payment_prepare_timeout/.test(text(errorValue && errorValue.message ? errorValue.message : errorValue))) {
          // Invalidate a slow referral request; if the payment POST was already sent, keep its promise locked.
          if (paymentRequestPromise) paymentRequestTimedOut = true;
          var failedSerial = ++patchSerial;
          localSerial = failedSerial;
          showFailure(errorValue, failedSerial);
          return;
        }
        showFailure(errorValue, nowSerial);
      });
    }

    button.onclick = function (event) {
      if (event) { event.preventDefault(); event.stopPropagation(); }
      if (!button.disabled) startPreparation();
    };

    var close = byId('dh-buy-close');
    if (close) {
      close.onclick = function (event) {
        if (event) { event.preventDefault(); event.stopPropagation(); }
        patchSerial += 1;
        try { overlay.remove(); } catch (_) {}
      };
    }
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
