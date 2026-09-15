/* commercial_ui_bridge_v3.js — profile-scoped admin entry + stable purchase bridge */
(function (global) {
  'use strict';
  var purchaseBound = false;
  var adminBound = false;

  function authSession() {
    try { return JSON.parse(localStorage.getItem('dh_auth_v1') || 'null'); } catch (_) { return null; }
  }
  function isStaff(user) {
    return !!user && (user.role === 'admin' || user.role === 'support');
  }
  function getAdminButton() {
    return document.getElementById('dh-profile-admin');
  }
  function ensureAdminInProfile() {
    var top = document.getElementById('dh-admin-entry');
    if (top) top.style.display = 'none';

    var purchase = document.getElementById('dh-p-prem');
    if (!purchase || !purchase.parentNode) return;

    var session = authSession();
    var user = session && session.user;
    var existing = getAdminButton();

    if (!isStaff(user)) {
      if (existing) existing.remove();
      return;
    }
    if (existing) return;

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'dh-profile-admin';
    btn.className = purchase.className || 'btn';
    btn.style.cssText = 'width:100%;margin-top:8px;border:1px solid rgba(212,175,55,.45);color:#f0c040;background:rgba(212,175,55,.08);';
    btn.textContent = 'پنل مدیریت';
    btn.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      window.location.assign('admin.html');
    });
    purchase.parentNode.insertBefore(btn, purchase.nextSibling);
  }

  async function startPurchase() {
    if (!global.DHAuth || typeof global.DHAuth.isLoggedIn !== 'function') {
      alert('سرویس حساب کاربری در دسترس نیست.');
      return;
    }
    if (!global.DHAuth.isLoggedIn()) {
      if (global.DHCommercialUI && typeof global.DHCommercialUI.showLogin === 'function') {
        global.DHCommercialUI.showLogin();
      } else {
        alert('ابتدا وارد حساب کاربری شوید.');
      }
      return;
    }
    if (typeof global.DHAuth.createPayment !== 'function') {
      alert('سرویس پرداخت در دسترس نیست.');
      return;
    }
    try {
      var payment = await global.DHAuth.createPayment();
      if (!payment || !payment.payment_url) throw new Error('آدرس پرداخت از سرور دریافت نشد.');
      window.location.assign(payment.payment_url);
    } catch (e) {
      alert((e && e.message) || 'ایجاد درخواست پرداخت ناموفق بود.');
    }
  }

  function bindPurchase() {
    if (purchaseBound) return;
    var btn = document.getElementById('dh-p-prem');
    if (!btn) return;
    purchaseBound = true;
    btn.textContent = 'خرید بسته ۳ تست';
    btn.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();
      startPurchase();
    }, true);
  }

  function bind() {
    bindPurchase();
    ensureAdminInProfile();
  }

  function boot() {
    bind();
    var observer = new MutationObserver(function () {
      bindPurchase();
      ensureAdminInProfile();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener('storage', function (e) {
      if (e.key === 'dh_auth_v1') ensureAdminInProfile();
    });
    window.addEventListener('dh-auth-changed', ensureAdminInProfile);
    setTimeout(bind, 250);
    setTimeout(bind, 1000);
    setTimeout(bind, 2500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})(window);
