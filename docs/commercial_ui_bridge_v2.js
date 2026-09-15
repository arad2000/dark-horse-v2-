/* commercial_ui_bridge_v2.js — single purchase button + profile admin entry */
(function (global) {
  'use strict';

  var BUSY = false;
  var INSTALLED = false;

  function byId(id) { return document.getElementById(id); }
  function isAdminRole(user) {
    var role = user && user.role;
    return role === 'admin' || role === 'support';
  }

  function currentUser() {
    try {
      if (global.DHAuth && typeof global.DHAuth.getUser === 'function') {
        return global.DHAuth.getUser();
      }
    } catch (_) {}
    return null;
  }

  async function refreshUser() {
    var user = currentUser();
    try {
      if ((!user || !isAdminRole(user)) && global.DHAuth && global.DHAuth.isLoggedIn && global.DHAuth.isLoggedIn() && typeof global.DHAuth.refreshMe === 'function') {
        user = await global.DHAuth.refreshMe();
      }
    } catch (_) {}
    return user;
  }

  async function startPayment() {
    if (BUSY) return;
    BUSY = true;
    try {
      if (!global.DHAuth || !global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) {
        if (global.DHCommercialUI && typeof global.DHCommercialUI.showLogin === 'function') {
          global.DHCommercialUI.showLogin('login');
        } else {
          alert('ابتدا وارد حساب کاربری شوید.');
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

  function ensureSinglePurchaseButton() {
    var legacy = byId('dh-p-prem');
    var purchase = byId('dh-p-buy');

    /* shell.js currently renders both. Keep only the commercial purchase action. */
    if (legacy) {
      legacy.remove();
    }
    if (!purchase) return;
    purchase.textContent = 'خرید بسته ۳ تست';

    if (!purchase.dataset.dhPurchaseBound) {
      purchase.dataset.dhPurchaseBound = '1';
      purchase.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopImmediatePropagation();
        startPayment();
      }, true);
    }
  }

  async function ensureAdminEntry() {
    var purchase = byId('dh-p-buy');
    if (!purchase) return;

    var existing = byId('dh-profile-admin-entry');
    var user = await refreshUser();
    var allowed = isAdminRole(user);

    if (!allowed) {
      if (existing) existing.remove();
      return;
    }

    if (existing) return;

    var btn = document.createElement('button');
    btn.id = 'dh-profile-admin-entry';
    btn.type = 'button';
    btn.className = 'btn';
    btn.style.width = '100%';
    btn.style.marginTop = '8px';
    btn.style.borderColor = 'rgba(212,175,55,.45)';
    btn.style.color = '#f0c040';
    btn.textContent = 'پنل مدیریت';
    btn.addEventListener('click', function () {
      window.location.assign('admin.html');
    });
    purchase.parentNode.insertBefore(btn, purchase.nextSibling);
  }

  function sync() {
    ensureSinglePurchaseButton();
    ensureAdminEntry();
  }

  function boot() {
    if (INSTALLED) return;
    INSTALLED = true;
    sync();
    var observer = new MutationObserver(function () {
      sync();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(window);
