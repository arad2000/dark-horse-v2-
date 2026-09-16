/* P0 guard for the profile tab: prevent the legacy shell boot timers from
 * re-rendering the home page immediately after a profile tap.  The profile
 * view itself remains shell-owned; this guard only short-circuits the tabbar
 * event and marks the UI as stable while the existing delayed boot checks run.
 */
(function () {
  'use strict';

  function onReady() {
    if (window.__dhProfileTabGuardInstalled) return;
    window.__dhProfileTabGuardInstalled = true;

    document.addEventListener('click', function (event) {
      var target = event.target;
      var button = target && target.closest ? target.closest('#dh-tabbar button[data-tab="profile"]') : null;
      if (!button || !window.DHShell || typeof window.DHShell.renderProfile !== 'function') return;

      event.preventDefault();
      if (event.stopImmediatePropagation) event.stopImmediatePropagation();
      else event.stopPropagation();

      window.__dhInJourney = true;
      try {
        window.DHShell.renderProfile();
      } catch (e) {
        console.error('Profile tab render failed', e);
      }
      // The shell's delayed boot checks test this flag before rendering home.
      window.__dhInJourney = true;
    }, true);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', onReady);
  else onReady();
})();
