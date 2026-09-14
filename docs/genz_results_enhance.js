/* Dark Horse — Gen-Z Results Enhancement v1
 * Presentation-only. Adds CSS hooks after result rendering; no data or behavior is changed.
 */
(function () {
  'use strict';

  function tagResults() {
    var app = document.getElementById('app');
    if (!app) return;

    app.querySelectorAll('.card').forEach(function (card) {
      if (card.classList.contains('dh-result-card')) return;
      var text = card.textContent || '';
      var inline = card.getAttribute('style') || '';
      if (/جرقه‌های این رشته/.test(text) && /linear-gradient\(145deg,#1a1a2e,#0a0a12\)/.test(inline)) {
        card.classList.add('dh-result-card');
        card.setAttribute('data-result-card', 'true');

        var badge = card.querySelector('div[style*="background:#d4af37"]');
        if (badge) badge.classList.add('dh-result-score-badge');
      }
    });
  }

  function install() {
    tagResults();
    var app = document.getElementById('app');
    if (!app || app.__dhGenZResultObserver) return;
    var observer = new MutationObserver(function () { tagResults(); });
    observer.observe(app, { childList: true, subtree: true });
    app.__dhGenZResultObserver = observer;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  } else {
    install();
  }
})();
