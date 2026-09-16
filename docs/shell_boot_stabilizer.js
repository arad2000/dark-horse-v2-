/* Dark Horse shell bootstrap stabilizer.
 * Installed immediately before shell.js. It suppresses only the two known
 * legacy timer paths in shell.js: the unconditional duplicate boot(0) and
 * the delayed renderHome checks at 200/700ms. All other timers pass through.
 */
(function () {
  'use strict';
  if (window.__dhShellTimerStabilizerInstalled) return;
  window.__dhShellTimerStabilizerInstalled = true;

  var nativeSetTimeout = window.setTimeout;
  var nativeClearTimeout = window.clearTimeout;
  var armed = true;

  function sourceOf(fn) {
    try { return Function.prototype.toString.call(fn); } catch (e) { return ''; }
  }

  window.setTimeout = function (fn, delay) {
    if (armed && typeof fn === 'function') {
      var src = sourceOf(fn);
      var ms = Number(delay) || 0;
      // shell.js: unconditional duplicate setTimeout(boot, 0)
      if (ms === 0 && /\bboot\s*\(\s*\)/.test(src) === false && /\bboot\b/.test(src)) {
        return 0;
      }
      // shell.js: delayed home rerenders that race Profile/other UI.
      if ((ms === 200 || ms === 700) && /renderHome\s*\(\s*\)/.test(src)) {
        return 0;
      }
    }
    return nativeSetTimeout.apply(window, arguments);
  };

  window.clearTimeout = function () {
    return nativeClearTimeout.apply(window, arguments);
  };

  // shell.js is loaded immediately after this defer script. Restore the native
  // timer APIs on the next task so no unrelated application timer is affected.
  nativeSetTimeout(function () {
    armed = false;
    window.setTimeout = nativeSetTimeout;
    window.clearTimeout = nativeClearTimeout;
  }, 0);
})();
