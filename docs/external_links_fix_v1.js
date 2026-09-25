/* External links v6 — shared native/intent/browser external navigation contract. */
(function (global) {
  'use strict';

  var SANJESH_URL = 'https://www.sanjesh.org';
  var ENAMAD_URL = 'https://trustseal.enamad.ir/?id=7638931&Code=B04E6IpO9ivFnOcTrDySvqdKmiG011AS';
  var EITAA_URL = 'https://eitaa.com/asbe_siah';
  var OBSERVER_INSTALLED = false;

  function text(value) { return String(value == null ? '' : value); }

  function armReturnEntry() {
    try {
      var marker = '__dh_external_return_v1__';
      if (global.history && global.history.state && global.history.state[marker]) return;
      if (global.history && typeof global.history.pushState === 'function') {
        var state = {};
        state[marker] = true;
        state.url = global.location.href;
        global.history.pushState(state, '', global.location.href);
      }
    } catch (_) {}
  }

  function isAndroidWebViewOrPwa() {
    var ua = text(global.navigator && global.navigator.userAgent);
    if (!/Android/i.test(ua)) return false;
    var standalone = false;
    try {
      standalone = !!(global.matchMedia &&
        global.matchMedia('(display-mode: standalone)').matches);
    } catch (_) {}
    if (global.navigator && global.navigator.standalone) standalone = true;
    return standalone || /; wv\)/i.test(ua) ||
      /WebView/i.test(ua) || /Version\/4\.0 Chrome/i.test(ua);
  }

  function chromeIntent(url) {
    var target = String(url);
    var hostpath = target.replace(/^https?:\/\//, '');
    return 'intent://' + hostpath +
      '#Intent;scheme=https;action=android.intent.action.VIEW;' +
      'category=android.intent.category.BROWSABLE;package=com.android.chrome;' +
      'S.browser_fallback_url=' + encodeURIComponent(target) + ';end';
  }

  function openExternal(url) {
    var target = String(url || '');
    if (!/^https:\/\//i.test(target)) return false;

    // 1) Native APK bridge gets first refusal.
    try {
      if (global.AndroidBridge &&
          typeof global.AndroidBridge.openExternalUrl === 'function') {
        global.AndroidBridge.openExternalUrl(target);
        return true;
      }
    } catch (_) {}

    // 2) Android WebView/PWA leaves the app through Chrome.
    if (isAndroidWebViewOrPwa()) {
      try {
        global.location.href = chromeIntent(target);
        return true;
      } catch (_) {}
      return false;
    }

    // 3) Normal browser navigation.
    try {
      global.location.assign(target);
      return true;
    } catch (_) {
      try {
        global.location.href = target;
        return true;
      } catch (_) {}
    }
    return false;
  }

  function directNavigate(anchor, url) {
    if (!anchor) return;
    anchor.setAttribute('href', url);
    anchor.setAttribute('target', '_blank');
    anchor.setAttribute('rel', 'noopener noreferrer');
    anchor.onclick = function (event) {
      try {
        if (event) {
          event.preventDefault();
          if (typeof event.stopImmediatePropagation === 'function') event.stopImmediatePropagation();
          if (typeof event.stopPropagation === 'function') event.stopPropagation();
        }
      } catch (_) {}
      openExternal(url);
      return false;
    };
  }

  function repair() {
    var sanjesh = document.querySelector('.dh-sanjesh-link');
    if (sanjesh && text(sanjesh.textContent).indexOf('ورود به پرتال سازمان سنجش') >= 0) {
      directNavigate(sanjesh, SANJESH_URL);
    }

    var enamad = document.querySelector('#enamad-seal a[href*="trustseal.enamad.ir"]');
    if (enamad) directNavigate(enamad, ENAMAD_URL);

    var eitaa = document.querySelector('a[href*="eitaa.com"]');
    if (eitaa && text(eitaa.textContent).indexOf('عضویت در کانال ایتا') >= 0) {
      directNavigate(eitaa, EITAA_URL);
    }
  }

  function boot() {
    repair();
    if (OBSERVER_INSTALLED || !document.body || typeof MutationObserver === 'undefined') return;
    OBSERVER_INSTALLED = true;
    var observer = new MutationObserver(function () {
      try { repair(); } catch (_) {}
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})(window);
