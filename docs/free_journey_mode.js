/* free_journey_mode.js — restore the app's original exploratory-journey handlers
 * during the temporary free-access phase. Commercial billing remains separate.
 */
(function (global) {
  'use strict';

  function journeySelectors() {
    return '#dh-start-journey, #dh-continue-journey, #dh-p-journey';
  }

  function rememberOriginal(btn) {
    if (btn.__dhOriginalJourneyOnclickSaved) return;
    btn.__dhOriginalJourneyOnclick = btn.onclick || null;
    btn.__dhOriginalJourneyOnclickSaved = true;
  }

  function restoreButtons() {
    document.querySelectorAll(journeySelectors()).forEach(function (btn) {
      rememberOriginal(btn);
      btn.onclick = btn.__dhOriginalJourneyOnclick;
      btn.__dhFreeJourneyMode = true;
    });
  }

  function restoreAfterObservers() {
    restoreButtons();
    setTimeout(restoreButtons, 0);
    setTimeout(restoreButtons, 50);
  }

  function boot() {
    restoreAfterObservers();
    var observer = new MutationObserver(function () {
      restoreAfterObservers();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  global.DHFreeJourney = {
    enabled: true,
    start: function () {
      restoreButtons();
    }
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})(window);
