/* commercial_ui_bridge_v2.js — single commercial purchase CTA + profile admin entry */
(function (global) {
  'use strict';

  var BUSY = false;
  var INSTALLED = false;
  var SYNC_SCHEDULED = false;

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
      if ((!user || !isAdminRole(user)) && global.DHAuth && typeof global.DHAuth.isLoggedIn === 'function' && global.DHAuth.isLoggedIn() && typeof global.DHAuth.refreshMe === 'function') {
        user = await global.DHAuth.refreshMe();
      }
    } catch (_) {}
    return user;
  }

  async function startPayment() {
    if (BUSY) return;
    BUSY = true;
    try {
      if (!global.DHAuth || typeof global.DHAuth.isLoggedIn !== 'function' || !global.DHAuth.isLoggedIn()) {
        if (global.DHCommercialUI && typeof global.DHCommercialUI.showAuth === 'function') {
          global.DHCommercialUI.showAuth('login');
        } else if (global.DHCommercialUI && typeof global.DHCommercialUI.showLogin === 'function') {
          global.DHCommercialUI.showLogin();
        } else {
          alert('ابتدا وارد حساب کاربری شوید.');
        }
        return;
      }
      if (typeof global.DHAuth.createPayment !== 'function') {
        throw new Error('سرویس پرداخت در دسترس نیست.');
      }
      var payment = await global.DHAuth.createPayment();
      if (!payment || !payment.payment_url) {
        throw new Error('آدرس پرداخت از سرور دریافت نشد.');
      }
      window.location.assign(payment.payment_url);
    } catch (e) {
      alert((e && e.message) ? e.message : 'خطا در ایجاد درخواست پرداخت');
    } finally {
      BUSY = false;
    }
  }

  function ensureSinglePurchaseButton() {
    var legacy = byId('dh-p-prem');
    var purchases = document.querySelectorAll('#dh-p-buy');
    var purchase = purchases.length ? purchases[0] : null;

    /* Convert the legacy DOM node instead of hiding it: the final DOM has one purchase CTA. */
    if (!purchase && legacy) {
      legacy.id = 'dh-p-buy';
      legacy.removeAttribute('data-legacy-purchase');
      purchase = legacy;
    } else if (legacy && legacy !== purchase) {
      legacy.remove();
    }

    for (var i = 1; i < purchases.length; i += 1) {
      purchases[i].remove();
    }

    if (!purchase) return null;
    purchase.textContent = 'خرید بسته ۳ تست';
    purchase.setAttribute('data-testid', 'purchase-pack-3');
    return purchase;
  }

  async function ensureAdminEntry() {
    var purchase = ensureSinglePurchaseButton();
    if (!purchase || !purchase.parentNode) return;

    var fixedEntry = byId('dh-admin-entry');
    if (fixedEntry) fixedEntry.remove();

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
    SYNC_SCHEDULED = false;
    ensureSinglePurchaseButton();
    ensureAdminEntry();
  }

  function scheduleSync() {
    if (SYNC_SCHEDULED) return;
    SYNC_SCHEDULED = true;
    Promise.resolve().then(sync);
  }

  function installPurchaseDelegation() {
    document.addEventListener('click', function (event) {
      var target = event.target && typeof event.target.closest === 'function'
        ? event.target.closest('#dh-p-buy')
        : null;
      if (!target) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      startPayment();
    }, true);
  }

  function boot() {
    if (INSTALLED) return;
    INSTALLED = true;
    installPurchaseDelegation();
    sync();

    if (typeof MutationObserver !== 'undefined') {
      var root = byId('app') || document.body;
      var observer = new MutationObserver(function () {
        scheduleSync();
      });
      observer.observe(root, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})(window);
