/* profile_auth_cleanup.js — remove legacy profile controls without creating new UI */
(function (global) {
  'use strict';

  var INSTALLED = false;

  function el(id) { return document.getElementById(id); }

  function removeLegacyGuestFields() {
    var save = el('dh-p-save');
    if (!save) return;
    var node = save.previousElementSibling;
    while (node) {
      if (node.tagName === 'DIV') break;
      var previous = node.previousElementSibling;
      node.remove();
      node = previous;
    }
    save.remove();
  }

  function normalizePurchaseButton() {
    var buy = el('dh-p-buy');
    var legacy = el('dh-p-prem');
    var testButtons = document.querySelectorAll('[data-testid="purchase-pack-3"]');

    if (!buy && legacy) {
      legacy.id = 'dh-p-buy';
      buy = legacy;
    }
    if (buy) {
      buy.textContent = 'خرید بسته ۳ تست';
      buy.setAttribute('data-testid', 'purchase-pack-3');
    }
    if (legacy && legacy !== buy) legacy.remove();
    for (var i = 0; i < testButtons.length; i += 1) {
      if (testButtons[i] !== buy) testButtons[i].remove();
    }
  }

  function bindExisting(id, handler) {
    var button = el(id);
    if (!button || button.__dhAuthCleanupBound) return;
    button.__dhAuthCleanupBound = true;
    button.onclick = function (event) {
      if (event) event.preventDefault();
      handler();
    };
  }

  function normalizeProfile() {
    removeLegacyGuestFields();
    normalizePurchaseButton();

    var ui = global.DHCommercialUI;
    if (!ui) return;

    bindExisting('dh-p-register', function () {
      if (typeof ui.showAuth === 'function') ui.showAuth('register');
    });
    bindExisting('dh-p-login', function () {
      if (typeof ui.showAuth === 'function') ui.showAuth('login');
    });
    bindExisting('dh-p-buy', function () {
      if (typeof ui.showPurchase === 'function') ui.showPurchase();
    });
    bindExisting('dh-p-out', function () {
      if (typeof ui.logout === 'function') ui.logout(true);
    });
  }

  function boot() {
    if (INSTALLED) return;
    INSTALLED = true;
    normalizeProfile();
    if (typeof MutationObserver !== 'undefined' && document.body) {
      var observer = new MutationObserver(function () { normalizeProfile(); });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})(window);
