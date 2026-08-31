/* free_journey_mode.js — temporary free-access gate for exploratory journey
 * Keeps commercial payment UI available, but does not block or consume credits
 * for entering the exploratory journey while payment/OTP rollout is completed.
 */
(function (global) {
  'use strict';

  function startFreeJourney() {
    if (global.DHShell && typeof global.DHShell.startJourney === 'function') {
      global.DHShell.startJourney();
      return true;
    }
    return false;
  }

  function patchButtons() {
    var selectors = '#dh-start-journey, #dh-continue-journey, #dh-p-journey';
    document.querySelectorAll(selectors).forEach(function (btn) {
      btn.__dhFreeJourneyMode = true;
      btn.onclick = function (e) {
        if (e) e.preventDefault();
        startFreeJourney();
      };
    });
  }

  function boot() {
    patchButtons();
    var observer = new MutationObserver(function () {
      patchButtons();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  global.DHFreeJourney = {
    enabled: true,
    start: startFreeJourney
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})(window);
