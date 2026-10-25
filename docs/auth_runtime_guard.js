/** Dark Horse auth runtime guard v1.
 * Blocks the legacy local-only premium activation path in the canonical UI.
 * Server-side authentication, entitlements, quota, and billing remain authoritative.
 */
(function () {
  'use strict';

  document.addEventListener('click', function (event) {
    var target = event.target;
    var premiumButton = target && target.closest ? target.closest('#dh-p-prem') : null;
    if (!premiumButton) return;
    event.preventDefault();
    event.stopPropagation();
    if (event.stopImmediatePropagation) event.stopImmediatePropagation();
    alert('فعال‌سازی اشتراک فقط از طریق حساب کاربری و پرداخت رسمی انجام می‌شود.');
  }, true);

  var style = document.createElement('style');
  style.textContent = '#dh-p-prem{display:none!important;}';
  (document.head || document.documentElement).appendChild(style);
})();
