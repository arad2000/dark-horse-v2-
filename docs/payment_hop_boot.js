/* payment_hop_boot.js v3 — handle gateway hop before SPA + recover on bfcache Back */
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
      '#Intent;scheme=https;action=android.intent.action.VIEW;' +
      'category=android.intent.category.BROWSABLE;package=com.android.chrome;' +
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

    // Prevent commercial_ui.js from starting a second, concurrent handoff.
    window.__dhPaymentHopBootHandled = true;
    var dhChrome = params.get('dh_chrome') === '1';
    var embedded = isEmbeddedAndroid();
    var hop = 'https://asbe-siah.ir/?dh_pay=' +
      encodeURIComponent(decoded) + '&dh_chrome=1';
    var stopped = false;
    var stage = 'raw';
    var timer = null;

    function clearTimer() {
      if (timer === null) return;
      try { window.clearTimeout(timer); } catch (_) {}
      timer = null;
    }
    function restorePage() {
      try { document.documentElement.style.visibility = ''; } catch (_) {}
      try { document.documentElement.style.removeProperty('visibility'); } catch (_) {}
      cleanup();
    }
    function cleanup() {
      if (stopped) return;
      stopped = true;
      clearTimer();
      try { window.removeEventListener('pagehide', onPageHide); } catch (_) {}
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
        timer = window.setTimeout(function () {
          timer = null;
          if (!stopped) fn();
        }, delay);
      } catch (_) {}
    }
    function finalSiteHop() {
      if (stopped) return;
      stage = 'hop';
      clearTimer();
      try { window.location.replace(hop); return; } catch (_) {}
      try { window.location.href = hop; return; } catch (_) {}
      restorePage();
    }
    function launchChrome() {
      if (stopped || stage !== 'raw') return;
      stage = 'chrome';
      clearTimer();
      try {
        window.location.href = chromeIntent(decoded, hop);
        schedule(finalSiteHop, 1800);
      } catch (_) {
        finalSiteHop();
      }
    }

    try {
      window.addEventListener('pagehide', onPageHide);
      document.addEventListener('visibilitychange', onVisibilityChange);
    } catch (_) {}

    // Keep the hop page quiet while the first, in-place gateway navigation starts.
    try { document.documentElement.style.visibility = 'hidden'; } catch (_) {}
    try {
      // First attempt is always the raw Zarinpal URL. dh_chrome=1 is a terminal
      // fallback marker: attempt raw once, but never recursively launch Chrome again.
      window.location.replace(decoded);
      if (embedded && !dhChrome) {
        schedule(launchChrome, 2200);
      } else {
        // Never leave a stuck blank page if a WebView/browser silently blocks navigation.
        schedule(restorePage, 2200);
      }
    } catch (_) {
      if (embedded && !dhChrome) {
        restorePage();
        launchChrome();
      } else {
        clearTimer();
        restorePage();
      }
    }
  } catch (_) {
    try { document.documentElement.style.visibility = ''; } catch (_) {}
  }
})();
