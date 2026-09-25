/* payment_hop_boot.js v2 — handle gateway hop before SPA + recover on bfcache Back */
(function () {
  'use strict';

  function hasPaymentHop() {
    try { return !!new URLSearchParams(window.location.search || '').get('dh_pay'); }
    catch (_) { return false; }
  }

  function restoreAppAfterExternalReturn() {
    if (hasPaymentHop()) return;
    try { document.documentElement.style.visibility = ''; } catch (_) {}
    try { document.documentElement.style.removeProperty('visibility'); } catch (_) {}
    try {
      if (window.__dhCommercialOverlay && window.__dhCommercialOverlay.parentNode) {
        window.__dhCommercialOverlay.parentNode.removeChild(window.__dhCommercialOverlay);
      }
    } catch (_) {}
    try { var o = document.getElementById('dh-commercial-overlay'); if (o) o.remove(); } catch (_) {}
    try { window.__dhInJourney = false; window.__dhJourneyStarting = false; } catch (_) {}
    try { window.__dhPaymentHandoff = false; } catch (_) {}
  }

  try {
    window.addEventListener('pageshow', function () { restoreAppAfterExternalReturn(); });
    window.addEventListener('pagehide', function () { try { document.documentElement.style.visibility = ''; } catch (_) {} });
  } catch (_) {}

  function isEmbeddedAndroid() {
    var ua = String(navigator.userAgent || '');
    if (!/Android/i.test(ua)) return false;
    var standalone = false;
    try {
      standalone = !!(window.matchMedia &&
        window.matchMedia('(display-mode: standalone)').matches);
    } catch (_) {}
    if (navigator.standalone) standalone = true;
    return standalone || /; wv\)/i.test(ua) ||
      /WebView/i.test(ua) || /Version\/4\.0 Chrome/i.test(ua);
  }

  function isZarinpalPaymentUrl(url) {
    try {
      var parsed = new URL(String(url), window.location.href);
      var host = String(parsed.hostname || '').toLowerCase();
      return parsed.protocol === 'https:' && (
        host === 'zarinpal.com' ||
        host === 'www.zarinpal.com' ||
        host === 'sandbox.zarinpal.com' ||
        host === 'payment.zarinpal.com' ||
        host === 'www.payment.zarinpal.com'
      );
    } catch (_) {
      return false;
    }
  }

  function chromeIntent(url, fallbackUrl) {
    var target = String(url);
    var fallback = String(fallbackUrl || target);
    var hostpath = target.replace(/^https?:\/\//, '');
    return 'intent://' + hostpath +
      '#Intent;scheme=https;package=com.android.chrome;' +
      'S.browser_fallback_url=' + encodeURIComponent(fallback) + ';end';
  }

  try {
    var params = new URLSearchParams(window.location.search || '');
    var raw = params.get('dh_pay');
    if (!raw) return;

    var decoded;
    try {
      decoded = decodeURIComponent(raw);
    } catch (_) {
      return;
    }
    if (!isZarinpalPaymentUrl(decoded)) return;

    try { document.documentElement.style.visibility = 'hidden'; } catch (_) {}

    var dhChrome = params.get('dh_chrome') === '1';

    // This script runs before app.js/shell.js. Therefore a payment hop
    // cannot render the SPA splash/Journey UI before redirecting away.
    if (isEmbeddedAndroid() && !dhChrome) {
      window.location.replace(
        chromeIntent(
          'https://asbe-siah.ir/?dh_pay=' +
            encodeURIComponent(decoded) + '&dh_chrome=1',
          'https://asbe-siah.ir/?dh_pay=' +
            encodeURIComponent(decoded) + '&dh_chrome=1'
        )
      );
      return;
    }

    window.location.replace(decoded);
  } catch (_) {}
})();
