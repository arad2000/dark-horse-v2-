/*
 * shell_runtime_fix.js v1
 * Narrow lifecycle protection for the canonical shell/Profile path.
 * Does not render Profile and does not change scoring/data semantics.
 */
(function () {
  'use strict';

  var nativeSetTimeout = window.setTimeout.bind(window);
  var nativeClearTimeout = window.clearTimeout.bind(window);
  var timerGuardActive = true;
  var profileActive = false;
  var renderPatched = false;

  function isShellRaceTimer(fn, delay) {
    if (typeof fn !== 'function') return false;
    var d = Number(delay);
    if (d !== 0 && d !== 200 && d !== 700) return false;
    try {
      var src = Function.prototype.toString.call(fn);
      if (d === 0 && /^\s*function\s+boot\s*\(/.test(src)) return true;
      if ((d === 200 || d === 700) && /renderHome\s*\(/.test(src)) return true;
    } catch (e) {}
    return false;
  }

  window.setTimeout = function (fn, delay) {
    if (timerGuardActive && isShellRaceTimer(fn, delay)) return 0;
    return nativeSetTimeout.apply(window, arguments);
  };
  window.clearTimeout = function (id) {
    return nativeClearTimeout(id);
  };

  function installProfileRenderProtection() {
    if (renderPatched || typeof window.render !== 'function') return;
    var originalRender = window.render;
    if (originalRender.__dhProfileLifecycleWrapped) {
      renderPatched = true;
      return;
    }
    function guardedRender() {
      if (profileActive) return;
      return originalRender.apply(this, arguments);
    }
    guardedRender.__dhProfileLifecycleWrapped = true;
    window.render = guardedRender;
    renderPatched = true;
  }

  document.addEventListener('click', function (event) {
    try {
      var target = event.target;
      var tabBtn = target && target.closest && target.closest('#dh-tabbar button[data-tab]');
      if (tabBtn) {
        var tab = tabBtn.getAttribute('data-tab');
        if (tab === 'profile') profileActive = true;
        else if (tab === 'home' || tab === 'journey') profileActive = false;
        return;
      }

      var profileJourney = target && target.closest && target.closest('#dh-p-journey');
      var profileHome = target && target.closest && target.closest('#dh-p-home');
      if (profileJourney || profileHome) profileActive = false;
    } catch (e) {}
  }, true);

  document.addEventListener('DOMContentLoaded', function () {
    nativeSetTimeout(function () {
      timerGuardActive = false;
      installProfileRenderProtection();
    }, 100);
  }, false);

  nativeSetTimeout(function () {
    timerGuardActive = false;
    installProfileRenderProtection();
  }, 500);
})();
