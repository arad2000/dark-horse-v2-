/* commercial_ui.js — server-authoritative auth + credit gate + payment UI */
(function (global) {
  'use strict';

  var USER_KEY = 'dh_local_user_v1';
  var QUOTA_KEY = 'dh_local_quota_v1';
  var BUSY = false;

  function el(id) { return document.getElementById(id); }
  function safeText(v) { return String(v == null ? '' : v); }
  function apiBase() { return global.API_BASE || 'https://api.asbe-siah.ir'; }

  function saveLocalUser(user) {
    try { localStorage.setItem(USER_KEY, JSON.stringify(user || null)); } catch (_) {}
  }

  function clearLocalUser() {
    try { localStorage.removeItem(USER_KEY); } catch (_) {}
  }

  function setLocalQuota(q) {
    try { localStorage.setItem(QUOTA_KEY, JSON.stringify(q || { used: 0, premium: false })); } catch (_) {}
  }

  function currentJourneySessionId() {
    try {
      var journey = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null');
      return journey && journey.sessionId ? String(journey.sessionId) : null;
    } catch (_) {
      return null;
    }
  }

  function installDiscoverySessionBridge() {
    if (global.__dhDiscoverySessionBridgeInstalled || typeof global.fetch !== 'function') return;
    global.__dhDiscoverySessionBridgeInstalled = true;
    var nativeFetch = global.fetch.bind(global);
    global.fetch = async function (input, init) {
      var url = '';
      try { url = typeof input === 'string' ? input : String(input && input.url || ''); } catch (_) {}
      var isDiscovery = /\/api\/v2\/darkhorse\/(discover|branch-discovery)(?:\?|$)/.test(url);
      var nextInit = init;

      if (isDiscovery && init && typeof init.body === 'string') {
        try {
          var payload = JSON.parse(init.body);
          var sessionId = currentJourneySessionId();
          if (sessionId && !payload.session_id) {
            payload.session_id = sessionId;
            nextInit = Object.assign({}, init, { body: JSON.stringify(payload) });
          }
        } catch (_) {}
      }

      var response = await nativeFetch(input, nextInit);
      if (isDiscovery && response && response.ok) {
        try {
          var clone = response.clone();
          var body = await clone.json();
          if (body && body.session_id) {
            var journey = null;
            try { journey = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null'); } catch (_) {}
            journey = journey && typeof journey === 'object' ? journey : {};
            journey.sessionId = String(body.session_id);
            try { localStorage.setItem('darkhorse_session_v2', JSON.stringify(journey)); } catch (_) {}
            if (typeof global.DHCommercialUI?.persistFinalResultSummary === 'function') {
              try { await global.DHCommercialUI.persistFinalResultSummary(body, /branch-discovery/.test(url) ? 'branches' : 'majors'); } catch (_) {}
            }
          }
        } catch (_) {}
      }
      return response;
    };
  }

  function addStyles() {
    if (el('dh-commercial-styles')) return;
    var s = document.createElement('style');
    s.id = 'dh-commercial-styles';
    s.textContent = `
      .dh-commercial-overlay{position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:18px;backdrop-filter:blur(7px)}
      .dh-commercial-modal{width:100%;max-width:430px;background:#161622;border:1px solid rgba(212,175,55,.45);border-radius:18px;padding:20px;box-shadow:0 20px 60px rgba(0,0,0,.55);color:#eee}
      .dh-commercial-title{color:#f0c040;text-align:center;margin:0 0 8px;font-size:1.35rem}
      .dh-commercial-sub{color:#b0a080;text-align:center;font-size:.86rem;line-height:1.8;margin-bottom:14px}
      .dh-commercial-input{width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#0f0f18;color:#fff;font:inherit;margin:6px 0}
      .dh-commercial-actions{display:flex;gap:8px;margin-top:12px}
      .dh-commercial-actions .btn{flex:1;margin:0}
      .dh-commercial-error{color:#ff7b7b;min-height:1.4em;font-size:.82rem;margin-top:6px}
      .dh-commercial-note{color:#8f845f;font-size:.76rem;line-height:1.7;margin-top:10px;text-align:center}
      .dh-commercial-price{font-size:2rem;color:#f0c040;font-weight:800;text-align:center;margin:8px 0}
      .dh-commercial-pack{background:#10101a;border:1px solid rgba(212,175,55,.22);border-radius:12px;padding:12px;margin:12px 0;color:#cbb98a;line-height:2;text-align:center}
      .dh-commercial-link{background:none;border:0;color:#d4af37;text-decoration:underline;cursor:pointer;font:inherit;padding:4px}
      .dh-sandbox-badge{display:inline-block;padding:4px 9px;border-radius:999px;background:rgba(155,140,255,.12);border:1px solid rgba(155,140,255,.28);color:#b9afff;font-size:.74rem;margin-bottom:8px}
      .dh-admin-link{display:block;width:100%;margin:8px 0 0;padding:11px 14px;border-radius:12px;border:1px solid rgba(155,140,255,.28);background:rgba(155,140,255,.07);color:#cfc8ff;text-align:center;text-decoration:none;font:inherit;cursor:pointer}
    `;
    document.head.appendChild(s);
  }

  function closeModal() {
    var old = el('dh-commercial-overlay');
    if (old) old.remove();
  }

  function showModal(html) {
    addStyles();
    closeModal();
    var ov = document.createElement('div');
    ov.id = 'dh-commercial-overlay';
    ov.className = 'dh-commercial-overlay';
    ov.innerHTML = '<div class="dh-commercial-modal">' + html + '</div>';
    ov.addEventListener('click', function (e) { if (e.target === ov) closeModal(); });
    document.body.appendChild(ov);
    return ov;
  }

  async function handleSandboxPaymentQuery() {
    try {
      var params = new URLSearchParams(global.location.search || '');
      var sandbox = params.get('payment_sandbox');
      var orderId = params.get('order_id');
      var authority = params.get('authority');
      if (sandbox !== '1' || !orderId || !authority) return;

      if (history.replaceState) {
        history.replaceState({}, document.title, global.location.pathname || '/');
      }

      var ov = showModal(
        '<div style="text-align:center"><span class="dh-sandbox-badge">محیط سندباکس</span></div>' +
        '<h2 class="dh-commercial-title">درگاه پرداخت آزمایشی</h2>' +
        '<p class="dh-commercial-sub">این تراکنش آزمایشی است و هیچ برداشت واقعی انجام نمی‌شود.</p>' +
        '<div class="dh-commercial-pack"><div>سفارش</div><div style="font-size:.78rem;word-break:break-all;color:#8f845f">' + safeText(orderId) + '</div><div style="margin-top:8px">Authority: ' + safeText(authority) + '</div></div>' +
        '<div id="dh-sandbox-err" class="dh-commercial-error"></div>' +
        '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-sandbox-ok">پرداخت موفق</button><button type="button" class="btn" id="dh-sandbox-cancel">لغو پرداخت</button></div>' +
        '<p class="dh-commercial-note">پس از انتخاب، callback سرور اجرا و اعتبارها ثبت می‌شوند.</p>'
      );

      function callback(status) {
        var target = apiBase() + '/api/v1/billing/callback?' +
          new URLSearchParams({ order_id: orderId, Authority: authority, Status: status }).toString();
        global.location.assign(target);
      }

      el('dh-sandbox-ok').onclick = function () { callback('OK'); };
      el('dh-sandbox-cancel').onclick = function () { callback('NOK'); };
      return ov;
    } catch (e) {
      console.warn('Sandbox payment query handling skipped:', e);
    }
  }

  function showAuthModal(initialMode) {
    var mode = initialMode === 'login' ? 'login' : 'register';
    var ov = showModal('');

    function paint() {
      var title = mode === 'login' ? 'ورود به حساب' : 'ساخت حساب';
      var action = mode === 'login' ? 'ورود' : 'ثبت‌نام';
      ov.querySelector('.dh-commercial-modal').innerHTML =
        '<h2 class="dh-commercial-title">' + title + '</h2>' +
        '<p class="dh-commercial-sub">برای ذخیرهٔ سفر و اعتبارها، حساب شما روی سرور ثبت می‌شود.</p>' +
        (mode === 'register' ? '<input id="dh-c-name" class="dh-commercial-input" placeholder="نام" autocomplete="name">' : '') +
        '<input id="dh-c-phone" class="dh-commercial-input" inputmode="tel" placeholder="شماره موبایل" autocomplete="tel">' +
        '<input id="dh-c-pass" class="dh-commercial-input" type="password" placeholder="رمز عبور (حداقل ۸ کاراکتر)" autocomplete="current-password">' +
        '<div id="dh-c-err" class="dh-commercial-error"></div>' +
        '<div class="dh-commercial-actions">' +
          '<button type="button" class="btn btn-primary" id="dh-c-submit">' + action + '</button>' +
          '<button type="button" class="btn" id="dh-c-close">انصراف</button>' +
        '</div>' +
        '<p class="dh-commercial-note">احراز هویت با سرور انجام می‌شود و منطق اعتبار در اختیار کلاینت نیست.</p>' +
        '<div style="text-align:center;margin-top:8px">' +
          (mode === 'login'
            ? '<button type="button" class="dh-commercial-link" id="dh-c-switch">ساخت حساب جدید</button>'
            : '<button type="button" class="dh-commercial-link" id="dh-c-switch">حساب دارم؛ ورود</button>') +
        '</div>';

      el('dh-c-close').onclick = closeModal;
      el('dh-c-switch').onclick = function () { mode = mode === 'login' ? 'register' : 'login'; paint(); };
      el('dh-c-submit').onclick = async function () {
        if (BUSY) return;
        BUSY = true;
        var err = el('dh-c-err');
        if (err) err.textContent = '';
        var phone = safeText(el('dh-c-phone').value).trim();
        var pass = safeText(el('dh-c-pass').value);
        var name = mode === 'register' ? safeText(el('dh-c-name').value).trim() : '';
        if (mode === 'register' && name.length < 2) { if (err) err.textContent = 'نام را وارد کن.'; BUSY = false; return; }
        if (!/^09\d{9}$/.test(phone)) { if (err) err.textContent = 'شماره موبایل را درست وارد کن.'; BUSY = false; return; }
        if (pass.length < 8) { if (err) err.textContent = 'رمز عبور باید حداقل ۸ کاراکتر باشد.'; BUSY = false; return; }
        try {
          var data = mode === 'register'
            ? await global.DHAuth.register(name, phone, pass)
            : await global.DHAuth.login(phone, pass);
          if (data && data.user) saveLocalUser(data.user);
          if (data && typeof data.quota === 'number') setLocalQuota({ used: data.quota > 0 ? 0 : 1, premium: false });
          closeModal();
          await continueAfterAuth();
        } catch (e) {
          if (err) err.textContent = safeText(e && e.message ? e.message : e);
        } finally {
          BUSY = false;
        }
      };
    }
    paint();
  }

  async function openPurchaseModal() {
    if (BUSY) return;
    showModal(
      '<h2 class="dh-commercial-title">خرید اعتبار آزمون</h2>' +
      '<div class="dh-commercial-pack"><div>بسته استاندارد</div><div class="dh-commercial-price">۲۴۹٬۰۰۰ تومان</div><div>۳ تست · بدون تاریخ انقضا</div></div>' +
      '<p class="dh-commercial-sub">مبلغ و تعداد اعتبار از سمت سرور تعیین می‌شود.</p>' +
      '<div id="dh-buy-err" class="dh-commercial-error"></div>' +
      '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-buy-now">ادامه به درگاه</button><button type="button" class="btn" id="dh-buy-close">انصراف</button></div>' +
      '<p class="dh-commercial-note">برای تراکنش واقعی، درگاه از تنظیمات امن سرور استفاده می‌کند.</p>'
    );
    el('dh-buy-close').onclick = closeModal;
    el('dh-buy-now').onclick = async function () {
      if (BUSY) return;
      BUSY = true;
      var err = el('dh-buy-err');
      if (err) err.textContent = '';
      try {
        if (!global.DHAuth || !global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) {
          closeModal();
          showAuthModal('login');
          return;
        }
        var payment = await global.DHAuth.createPayment();
        if (!payment || !payment.payment_url) throw new Error('آدرس درگاه از سرور دریافت نشد.');
        global.location.assign(payment.payment_url);
      } catch (e) {
        if (err) err.textContent = safeText(e && e.message ? e.message : e);
      } finally {
        BUSY = false;
      }
    };
  }

  async function continueAfterAuth() {
    if (!global.DHAuth || !global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) {
      showAuthModal('login');
      return;
    }
    try {
      var quota = await global.DHAuth.quota();
      var remaining = Number(quota && quota.credits_remaining || 0);
      if (remaining <= 0) {
        await openPurchaseModal();
        return;
      }

      await global.DHAuth.consumeTest();
      setLocalQuota({ used: 0, premium: false });
      closeModal();
      if (global.DHShell && typeof global.DHShell.startJourney === 'function') {
        global.DHShell.startJourney();
      }
    } catch (e) {
      var msg = safeText(e && e.message ? e.message : e);
      if (/401|authentication/i.test(msg) && global.DHAuth.logout) {
        global.DHAuth.logout();
        clearLocalUser();
        showAuthModal('login');
        return;
      }
      showModal(
        '<h2 class="dh-commercial-title">خطا</h2>' +
        '<p class="dh-commercial-sub">' + msg.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</p>' +
        '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-error-close">باشه</button></div>'
      );
      el('dh-error-close').onclick = closeModal;
    }
  }

  async function persistFinalResultSummary(data, type) {
    if (!data || !global.DHAuth || !global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) return;
    var sessionId = currentJourneySessionId();
    if (!sessionId || typeof global.DHAuth.saveResult !== 'function') return;

    var summary = {
      type: type === 'branches' ? 'branches' : 'majors',
      session_id: sessionId,
      saved_at: new Date().toISOString(),
      result: data
    };

    try {
      var encoded = JSON.stringify(summary);
      if (new TextEncoder().encode(encoded).length > 100000) {
        summary = {
          type: summary.type,
          session_id: sessionId,
          saved_at: summary.saved_at,
          result: type === 'branches'
            ? { branch_discovery_result: data.branch_discovery_result || data }
            : { discovery_result: data.discovery_result || data }
        };
      }
      await global.DHAuth.saveResult(summary);
    } catch (e) {
      console.warn('Final result summary persistence skipped:', e);
    }
  }

  function installCaptureGuards() {
    document.addEventListener('click', function (e) {
      var journey = e.target && typeof e.target.closest === 'function'
        ? e.target.closest('#dh-start-journey, #dh-continue-journey, #dh-p-journey') : null;
      if (journey) {
        e.preventDefault();
        e.stopImmediatePropagation();
        continueAfterAuth();
        return;
      }

      var premium = e.target && typeof e.target.closest === 'function'
        ? e.target.closest('#dh-p-prem') : null;
      if (premium) {
        e.preventDefault();
        e.stopImmediatePropagation();
        openPurchaseModal();
      }
    }, true);
  }

  function patchLegacyProfileCopy() {
    var btn = el('dh-p-prem');
    if (btn) btn.textContent = 'خرید بسته ۳ تست';
  }

  function patchAdminLink() {
    var u = null;
    try { u = global.DHAuth && global.DHAuth.getUser ? global.DHAuth.getUser() : null; } catch (_) {}
    var isAdmin = !!(u && (u.role === 'admin' || u.role === 'support'));
    var prem = el('dh-p-prem');
    if (!prem || !isAdmin) return;
    if (el('dh-admin-link')) return;
    var a = document.createElement('a');
    a.id = 'dh-admin-link';
    a.className = 'dh-admin-link';
    a.href = 'admin.html';
    a.textContent = 'پنل مدیریت';
    prem.parentNode.insertBefore(a, prem.nextSibling);
  }

  function observeShell() {
    var observer = new MutationObserver(function () { patchLegacyProfileCopy(); patchAdminLink(); });
    observer.observe(document.body, { childList: true, subtree: true });
    patchLegacyProfileCopy();
    patchAdminLink();
  }

  async function boot() {
    if (!global.DHAuth) return;
    installDiscoverySessionBridge();
    installCaptureGuards();
    observeShell();
    await handleSandboxPaymentQuery();
  }

  global.DHCommercialUI = {
    showAuth: showAuthModal,
    showPurchase: openPurchaseModal,
    startServerAuthorizedJourney: continueAfterAuth,
    persistFinalResultSummary: persistFinalResultSummary
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})(window);
