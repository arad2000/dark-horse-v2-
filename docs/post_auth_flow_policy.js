/* post_auth_flow_policy.js v4
 * Authentication must not trigger a purchase or consume a test automatically.
 * After successful login/OTP the user remains on Profile with the server-granted
 * free credit. Journey consumption starts only after an explicit Journey click.
 */
(function (global) {
  'use strict';

  var QUOTA_KEY = 'dh_local_quota_v1';
  var justAuthenticated = false;
  var explicitJourneyRequested = false;
  var flagTimer = null;

  function getUserKey() {
    try {
      var u = global.DHAuth && typeof global.DHAuth.getUser === 'function'
        ? (global.DHAuth.getUser() || {}) : {};
      return String(u.id || u.user_id || u.public_id || u.phone || u.mobile || u.username || '');
    } catch (_) { return ''; }
  }

  function readQuotaCache() {
    try {
      var raw = JSON.parse(localStorage.getItem(QUOTA_KEY) || 'null');
      return raw && typeof raw === 'object' ? raw : null;
    } catch (_) { return null; }
  }

  function writeQuotaSnapshot(data) {
    var current = readQuotaCache() || {};
    var userKey = getUserKey();
    var sameUser = !!userKey && String(current.userKey || '') === userKey;
    var remaining = Number(data && data.credits_remaining);
    var consumed = Number(data && data.credits_consumed);
    var granted = Number(data && data.credits_granted);
    if (!isFinite(remaining) || remaining < 0) remaining = sameUser && isFinite(Number(current.serverRemaining)) ? Number(current.serverRemaining) : 0;
    if (!isFinite(consumed) || consumed < 0) consumed = sameUser && isFinite(Number(current.used)) ? Number(current.used) : 0;
    if (!isFinite(granted) || granted < 0) granted = sameUser && isFinite(Number(current.serverGranted)) ? Number(current.serverGranted) : 0;
    try {
      localStorage.setItem(QUOTA_KEY, JSON.stringify({
        userKey: userKey,
        used: consumed,
        premium: sameUser ? !!current.premium : false,
        serverRemaining: remaining,
        remaining: remaining,
        serverGranted: granted,
        syncedAt: new Date().toISOString()
      }));
    } catch (_) {}
  }

  function markAuthenticated() {
    justAuthenticated = true;
    explicitJourneyRequested = false;
    if (flagTimer) clearTimeout(flagTimer);
    flagTimer = setTimeout(function () {
      justAuthenticated = false;
      explicitJourneyRequested = false;
    }, 5000);
  }

  function consumeAuthFlag() {
    justAuthenticated = false;
    explicitJourneyRequested = false;
    if (flagTimer) clearTimeout(flagTimer);
    flagTimer = null;
  }

  function renderProfile() {
    try {
      if (global.DHShell && typeof global.DHShell.renderProfile === 'function') {
        global.DHShell.renderProfile();
        return;
      }
    } catch (_) {}
    try {
      var btn = document.querySelector('#dh-tabbar button[data-tab="profile"]');
      if (btn) btn.click();
    } catch (_) {}
  }

  function syncGrantedQuotaThenProfile() {
    try {
      if (!global.DHAuth || typeof global.DHAuth.quota !== 'function') {
        renderProfile();
        return;
      }
      global.DHAuth.quota().then(function (data) {
        writeQuotaSnapshot(data);
        renderProfile();
      }).catch(function () { renderProfile(); });
    } catch (_) { renderProfile(); }
  }

  function wrapAuthMethod(name) {
    if (!global.DHAuth || typeof global.DHAuth[name] !== 'function') return;
    var original = global.DHAuth[name];
    if (original.__dhPostAuthWrapped) return;
    var wrapped = async function () {
      var result = await original.apply(this, arguments);
      if (result && (result.user || result.token)) markAuthenticated();
      return result;
    };
    wrapped.__dhPostAuthWrapped = true;
    global.DHAuth[name] = wrapped;
  }

  function installJourneyClickGuard() {
    document.addEventListener('click', function (event) {
      try {
        var btn = event.target && event.target.closest && event.target.closest('#dh-start-journey,#dh-continue-journey,#dh-p-journey');
        if (btn) {
          explicitJourneyRequested = true;
          justAuthenticated = false;
          return;
        }
      } catch (_) {}
    }, true);
  }

  function installAuthWrappers() {
    wrapAuthMethod('login');
    wrapAuthMethod('verifyRegistration');
  }

  function installConsumeGuard() {
    if (!global.DHAuth || typeof global.DHAuth.consumeTest !== 'function') return;
    var original = global.DHAuth.consumeTest;
    if (original.__dhPostAuthWrapped) return;
    var wrapped = async function () {
      if (justAuthenticated && !explicitJourneyRequested) {
        var data = null;
        try { data = await global.DHAuth.quota(); } catch (_) {}
        if (data) writeQuotaSnapshot(data);
        var q = data && Number(data.credits_remaining);
        return {
          consumed: 0,
          credits_remaining: isFinite(q) && q >= 0 ? q : 0,
          automatic: true
        };
      }
      return original.apply(this, arguments);
    };
    wrapped.__dhPostAuthWrapped = true;
    global.DHAuth.consumeTest = wrapped;
  }

  function installJourneyGuard() {
    if (!global.DHShell || typeof global.DHShell.startJourney !== 'function') return;
    var original = global.DHShell.startJourney;
    if (original.__dhPostAuthWrapped) return;
    var wrapped = function () {
      if (justAuthenticated && !explicitJourneyRequested) {
        consumeAuthFlag();
        syncGrantedQuotaThenProfile();
        return;
      }
      return original.apply(this, arguments);
    };
    wrapped.__dhPostAuthWrapped = true;
    global.DHShell.startJourney = wrapped;
  }

  function watchForAutoPurchase() {
    if (!document.body || typeof MutationObserver === 'undefined') return;
    new MutationObserver(function () {
      if (!justAuthenticated || explicitJourneyRequested) return;
      var overlay = document.getElementById('dh-commercial-overlay');
      if (!overlay) return;
      var modalText = String(overlay.textContent || '');
      if (modalText.indexOf('خرید بسته ۳ تست') < 0) return;
      try { overlay.remove(); } catch (_) {}
      consumeAuthFlag();
      syncGrantedQuotaThenProfile();
    }).observe(document.body, { childList: true, subtree: true });
  }

  function boot() {
    installAuthWrappers();
    installConsumeGuard();
    installJourneyClickGuard();
    installJourneyGuard();
    watchForAutoPurchase();
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      installAuthWrappers();
      installConsumeGuard();
      installJourneyGuard();
      if (tries >= 20) clearInterval(timer);
    }, 100);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})(window);
