/* commercial_ui.js — server-authoritative auth + credit gate + payment UI */
(function (global) {
  'use strict';

  var USER_KEY = 'dh_local_user_v1';
  var QUOTA_KEY = 'dh_local_quota_v1';
  var BUSY = false;

  function el(id) { return document.getElementById(id); }
  function safeText(v) { return String(v == null ? '' : v); }

  function saveLocalUser(user) {
    try { localStorage.setItem(USER_KEY, JSON.stringify(user || null)); } catch (_) {}
  }

  function clearLocalUser() {
    try { localStorage.removeItem(USER_KEY); } catch (_) {}
  }

  function setLocalQuota(q) {
    try { localStorage.setItem(QUOTA_KEY, JSON.stringify(q || { used: 0, premium: false })); } catch (_) {}
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
        window.location.assign(payment.payment_url);
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

  function installButtonHooks() {
    function patchButtons() {
      var journeyButtons = document.querySelectorAll('#dh-start-journey, #dh-continue-journey, #dh-p-journey');
      journeyButtons.forEach(function (btn) {
        if (btn.__dhCommercialHooked) return;
        btn.__dhCommercialHooked = true;
        btn.onclick = function (e) {
          if (e) e.preventDefault();
          continueAfterAuth();
        };
      });

      var premium = el('dh-p-prem');
      if (premium && !premium.__dhCommercialHooked) {
        premium.__dhCommercialHooked = true;
        premium.textContent = 'خرید بسته ۳ تست';
        premium.onclick = function (e) {
          if (e) e.preventDefault();
          openPurchaseModal();
        };
      }
    }

    patchButtons();
    var observer = new MutationObserver(patchButtons);
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function patchLegacyProfileCopy() {
    var btn = el('dh-p-prem');
    if (btn) btn.textContent = 'خرید بسته ۳ تست';
  }

  function boot() {
    if (!global.DHAuth) return;
    installButtonHooks();
    patchLegacyProfileCopy();
  }

  global.DHCommercialUI = {
    showAuth: showAuthModal,
    showPurchase: openPurchaseModal,
    startServerAuthorizedJourney: continueAfterAuth
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})(window);
