/* payment_return_reconcile.js v1
 * Reliable post-ZarinPal reconciliation for the web/PWA shell.
 * - Never grants credits on the client.
 * - Forwards gateway callback params to the server callback when needed.
 * - Refreshes server-authoritative quota after return.
 * - Safe to run again: server payment verification remains idempotent.
 */
(function (global) {
  'use strict';

  var API = (global.API_BASE || 'https://api.asbe-siah.ir').replace(/\/$/, '');
  var DONE_KEY = 'dh_payment_return_reconciled_v1';
  var QUOTA_KEY = 'dh_local_quota_v1';

  function query() {
    try { return new URLSearchParams(global.location.search || ''); }
    catch (_) { return null; }
  }

  function saveQuota(q) {
    try {
      var old = {};
      try { old = JSON.parse(localStorage.getItem(QUOTA_KEY) || '{}') || {}; } catch (_) {}
      var r = Number(q);
      if (!isFinite(r) || r < 0) r = 0;
      localStorage.setItem(QUOTA_KEY, JSON.stringify({
        used: Number(old.used) || 0,
        premium: !!old.premium,
        serverRemaining: r,
        remaining: r
      }));
    } catch (_) {}
  }

  async function refreshQuota() {
    if (!global.DHAuth || !global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) return null;
    try {
      var d = await global.DHAuth.quota();
      var r = Number(d && d.credits_remaining);
      if (!isFinite(r) || r < 0) r = 0;
      saveQuota(r);
      try { global.dispatchEvent(new CustomEvent('dh-quota-updated', { detail: { credits_remaining: r } })); } catch (_) {}
      return r;
    } catch (_) {
      return null;
    }
  }

  async function forwardGatewayCallback(params) {
    if (!params) return false;
    var authority = params.get('Authority');
    var status = params.get('Status');
    if (!authority || !status) return false;

    var orderId = params.get('order_id');
    var qs = new URLSearchParams();
    if (orderId) qs.set('order_id', orderId);
    qs.set('Authority', authority);
    qs.set('Status', status);

    try {
      await fetch(API + '/api/v1/billing/callback?' + qs.toString(), {
        method: 'GET',
        cache: 'no-store',
        redirect: 'manual'
      });
    } catch (_) {
      // The callback may have committed server-side before returning a redirect.
    }
    return true;
  }

  function cleanUrl() {
    try {
      var u = new URL(global.location.href);
      u.searchParams.delete('Authority');
      u.searchParams.delete('Status');
      u.searchParams.delete('order_id');
      u.searchParams.delete('credits_added');
      u.searchParams.delete('payment');
      global.history.replaceState({}, document.title, u.pathname + (u.hash || ''));
    } catch (_) {}
  }

  async function reconcile() {
    var p = query();
    if (!p) return;
    var payment = (p.get('payment') || '').toLowerCase();
    var hasGatewayParams = !!(p.get('Authority') && p.get('Status'));
    if (!hasGatewayParams && payment !== 'success') return;

    var signature = [
      payment,
      p.get('order_id') || '',
      p.get('Authority') || '',
      p.get('Status') || ''
    ].join('|');
    try {
      if (sessionStorage.getItem(DONE_KEY) === signature && !hasGatewayParams) {
        await refreshQuota();
        return;
      }
      await forwardGatewayCallback(p);
      // Give the server transaction a moment to finish before reading quota.
      await new Promise(function (resolve) { setTimeout(resolve, 350); });
      var r = await refreshQuota();
      if (r != null) {
        try { sessionStorage.setItem(DONE_KEY, signature); } catch (_) {}
      }
      try {
        if (global.DHShell && typeof global.DHShell.renderProfile === 'function' &&
            document.querySelector('#dh-tabbar button.active[data-tab="profile"]')) {
          global.DHShell.renderProfile();
        }
      } catch (_) {}
      cleanUrl();
    } catch (_) {}
  }

  function boot() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { reconcile(); }, { once: true });
    } else {
      reconcile();
    }
  }
  boot();
})(window);
