/* Dark Horse Home v25 — presentation-only adapter.
 * Reads existing rendered Home elements; does not alter Journey state,
 * scoring, sampling, navigation, session persistence, Strategy or Value.
 */
(function () {
  'use strict';

  function applyHomeV25() {
    var root = document.querySelector('.dh-home-v24');
    if (!root || root.getAttribute('data-dh-home-v25') === '1') return;

    root.setAttribute('data-dh-home-v25', '1');

    // Exact requested copy: singular "پیام امروز" and a clean subtitle hierarchy.
    var identity = root.querySelector('.dh-identity-title');
    if (identity) {
      identity.textContent = 'سامانه هدایت تحصیلی و انتخاب رشته دانشگاهی';
      var oldSubtitle = root.querySelector('.dh-home-subtitle');
      if (!oldSubtitle) {
        oldSubtitle = document.createElement('p');
        oldSubtitle.className = 'dh-home-subtitle';
        oldSubtitle.textContent = 'بر اساس فردیت';
        identity.insertAdjacentElement('afterend', oldSubtitle);
      }
    }

    var msg = root.querySelector('.dh-messages-label');
    if (msg) msg.textContent = '✦ پیام امروز';

    // Keep the existing semantic IDs and handlers; only upgrade the icon artwork.
    var iconSvgs = {
      '⚡': '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13 2 5 14h6l-1 8 8-12h-6z"/></svg>',
      '📖': '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5.5A3.5 3.5 0 0 1 7.5 2H20v17H7.5A3.5 3.5 0 0 0 4 22z"/><path d="M4 5.5v16.5"/><path d="M8 6h8"/></svg>',
      '🪶': '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 4c-7 0-13 4-13 10 0 3 2 6 5 6 5 0 9-7 8-16Z"/><path d="M4 21c3-5 7-8 13-11"/></svg>',
      '🤝': '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8" cy="7" r="3"/><circle cx="17" cy="8" r="2.5"/><path d="M2.5 20c.6-4.2 2.5-6.5 5.5-6.5S12.9 15.8 13.5 20"/><path d="M13 14.5c1-.7 2.2-1 3.5-1 2.5 0 4.2 2 5 5.5"/></svg>'
    };

    root.querySelectorAll('.dh-f-ico').forEach(function (el) {
      var key = (el.textContent || '').trim();
      if (iconSvgs[key]) el.innerHTML = iconSvgs[key];
    });
  }

  function watch() {
    applyHomeV25();
    var app = document.getElementById('app');
    if (!app || !window.MutationObserver) return;
    var observer = new MutationObserver(function () {
      applyHomeV25();
    });
    observer.observe(app, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watch, { once: true });
  } else {
    watch();
  }
})();
