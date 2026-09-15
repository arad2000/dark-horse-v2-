/* commercial_ui_bridge_v2.js — resilient frontend bridge for billing + admin entry */
(function (global) {
  'use strict';

  var BUSY = false;

  function byId(id) { return document.getElementById(id); }

  function isAdminRole(user) {
    var role = user && user.role;
    return role === 'admin' || role === 'support';
  }

  async function showAdminEntry() {
    var entry = byId('dh-admin-entry');
    if (!entry) return;

    var user = null;
    try {
      if (global.DHAuth && typeof global.DHAuth.getUser === 'function') {
        user = global.DHAuth.getUser();
      }
      if ((!user || !isAdminRole(user)) && global.DHAuth && global.DHAuth.isLoggedIn && global.DHAuth.isLoggedIn() && typeof global.DHAuth.refreshMe === 'function') {
        user = await global.DHAuth.refreshMe();
      }
    } catch (_) {}

    entry.style.display = isAdminRole(user) ? 'inline-block' : 'none';
  }

  async function startPayment() {
    if (BUSY) return;
    BUSY = true;
    try {
      if (!global.DHAuth || !global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) {
        if (typeof global.DHCommercialUI?.showLogin === 'function') {
          global.DHCommercialUI.showLogin();
        }
        return;
      }

      if (!global.DHAuth.createPayment) throw new Error('سرویس پرداخت در دسترس نیست.');
      var payment = await global.DHAuth.createPayment();
      if (!payment || !payment.payment_url) throw new Error('آدرس پرداخت از سرور دریافت نشد.');
      window.location.assign(payment.payment_url);
    } catch (e) {
      alert((e && e.message) ? e.message : 'خطا در ایجاد درخواست پرداخت');
    } finally {
      BUSY = false;
    }
  }

  function installPurchaseBridge() {
    document.addEventListener('click', function (event) {
      var target = event.target && typeof event.target.closest === 'function'
        ? event.target.closest('#dh-p-prem')
        : null;
      if (!target) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      startPayment();
    }, true);
  }

  function normalizePurchaseLabel() {
    var btn = byId('dh-p-prem');
    if (btn && !btn.disabled) btn.textContent = 'خرید بسته ۳ تست';
  }

  function boot() {
    installPurchaseBridge();
    normalizePurchaseLabel();
    showAdminEntry();

    var observer = new MutationObserver(function () {
      normalizePurchaseLabel();
      showAdminEntry();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(window);
