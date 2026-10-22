/* Dark Horse — Gen Z Results Enhancement Layer v3 */
(function () {
  function enhanceResultsDOM() {
    var root = document.getElementById('app');
    if (!root) return;

    var cards = root.querySelectorAll('.card');
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      var text = card.textContent || '';
      if (card.hasAttribute('data-dh-result-item') ||
          /جرقه‌های (مشترک|این رشته)|تطابق کلی|همخوانی کلی/.test(text)) {
        card.classList.add('dh-result-card');
      }
    }

    var allDivs = root.querySelectorAll('.card div, .card p');
    for (var j = 0; j < allDivs.length; j++) {
      var el = allDivs[j];
      if (el.children.length === 0 && /توضیح تحلیلی:|چرا این رشته:/i.test(el.textContent || '')) {
        el.classList.add('dh-result-why');
      }
    }
  }

  function install() {
    if (window.__dhGenZResultsInstalled) return;
    if (typeof window.displayResults !== 'function') return;
    window.__dhGenZResultsInstalled = true;
    var orig = window.displayResults;
    window.displayResults = function () {
      var out = orig.apply(this, arguments);
      try { enhanceResultsDOM(); } catch (e) {}
      return out;
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install);
  } else {
    install();
  }
})();
