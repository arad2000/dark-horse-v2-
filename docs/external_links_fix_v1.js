/* External links v4 — preserve native external navigation. */
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

  function directNavigate(anchor, url) {
    if (!anchor) return;
    // Preserve native external-link behavior. This avoids trapping Eitaa/Sanjesh
    // inside the Android WebView and lets the platform/browser choose the
    // appropriate external handler.
    anchor.setAttribute('href', url);
    anchor.setAttribute('target', '_blank');
    anchor.setAttribute('rel', 'noopener noreferrer');
    anchor.onclick = null;
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
