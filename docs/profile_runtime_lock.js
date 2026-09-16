/* Dark Horse profile runtime lock.
 * Prevents late app.js renders from replacing the Profile view while the
 * asynchronous bootstrap finishes. The lock is released only by explicit
 * navigation away from Profile.
 */
(function () {
  'use strict';
  if (window.__dhProfileRuntimeLockInstalled) return;
  window.__dhProfileRuntimeLockInstalled = true;

  function install() {
    if (!window.DHShell || typeof window.DHShell.renderProfile !== 'function') {
      return false;
    }

    if (!window.__dhProfileRenderOriginal) {
      window.__dhProfileRenderOriginal = window.DHShell.renderProfile;
      window.DHShell.renderProfile = function () {
        window.__dhProfileVisible = true;
        window.__dhInJourney = true;
        return window.__dhProfileRenderOriginal.apply(this, arguments);
      };
    }

    if (typeof window.render === 'function' && !window.__dhProfileRenderWrapped) {
      window.__dhProfileRenderWrapped = true;
      window.__dhProfileAppRenderOriginal = window.render;
      window.render = function () {
        if (window.__dhProfileVisible) return;
        return window.__dhProfileAppRenderOriginal.apply(this, arguments);
      };
    }

    if (!window.__dhProfileHomeWrapped && typeof window.DHShell.renderHome === 'function') {
      window.__dhProfileHomeWrapped = true;
      window.__dhProfileHomeOriginal = window.DHShell.renderHome;
      window.DHShell.renderHome = function () {
        window.__dhProfileVisible = false;
        window.__dhInJourney = false;
        return window.__dhProfileHomeOriginal.apply(this, arguments);
      };
    }

    if (!window.__dhProfileJourneyWrapped && typeof window.DHShell.startJourney === 'function') {
      window.__dhProfileJourneyWrapped = true;
      window.__dhProfileJourneyOriginal = window.DHShell.startJourney;
      window.DHShell.startJourney = function () {
        window.__dhProfileVisible = false;
        window.__dhInJourney = true;
        return window.__dhProfileJourneyOriginal.apply(this, arguments);
      };
    }
    return true;
  }

  document.addEventListener('click', function (e) {
    var btn = e.target && e.target.closest ? e.target.closest('#dh-tabbar button[data-tab]') : null;
    if (!btn) return;
    var tab = btn.getAttribute('data-tab');
    if (tab === 'profile') {
      window.__dhProfileVisible = true;
      window.__dhInJourney = true;
    } else if (tab === 'home' || tab === 'journey') {
      window.__dhProfileVisible = false;
    }
  }, true);

  if (install()) return;
  var tries = 0;
  var timer = window.setInterval(function () {
    tries += 1;
    if (install() || tries >= 50) {
      window.clearInterval(timer);
    }
  }, 20);
})();
