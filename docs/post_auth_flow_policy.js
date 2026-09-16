/* post_auth_flow_policy.js v1
 * Authentication must not trigger a purchase or consume a test automatically.
 * After successful login/OTP the user remains on Profile with the server-granted
 * free credit. Journey consumption starts only after an explicit Journey click.
 */
(function (global) {
  'use strict';

  var justAuthenticated = false;
  var explicitJourneyRequested = false;
  var flagTimer = null;

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
        var q = 0;
        try {
          var serverQ = await global.DHAuth.quota();
          q = Number(serverQ && serverQ.credits_remaining);
        } catch (_) {}
        return { consumed: 0, credits_remaining: isFinite(q) && q >= 0 ? q : 0, automatic: true };
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
        renderProfile();
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
      renderProfile();
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
