/* commercial_ui.js — server-authoritative auth + credit gate + payment UI */
(function (global) {
  'use strict';

  var USER_KEY = 'dh_local_user_v1';
  var QUOTA_KEY = 'dh_local_quota_v1';
  var BUSY = false;

  function el(id) { return document.getElementById(id); }
  function safeText(v) { return String(v == null ? '' : v); }
  function escapeHtml(v) {
    return safeText(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function saveLocalUser(user) {
    try { localStorage.setItem(USER_KEY, JSON.stringify(user || null)); } catch (_) {}
  }
  function clearLocalUser() {
    try { localStorage.removeItem(USER_KEY); } catch (_) {}
  }
  function setLocalQuota(q) {
    try { localStorage.setItem(QUOTA_KEY, JSON.stringify(q || { used: 0, premium: false })); } catch (_) {}
  }

  function setBusyButton(button, busyText, normalText, busy) {
    if (!button) return;
    button.disabled = !!busy;
    button.setAttribute('aria-busy', busy ? 'true' : 'false');
    button.style.opacity = busy ? '0.72' : '';
    button.textContent = busy ? busyText : normalText;
  }

  function addStyles() {
    if (el('dh-commercial-styles')) return;
    var s = document.createElement('style');
    s.id = 'dh-commercial-styles';
    s.textContent = `
      .dh-commercial-overlay{position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.76);display:flex;align-items:center;justify-content:center;padding:16px;backdrop-filter:blur(8px)}
      .dh-commercial-modal{width:100%;max-width:440px;background:#161622;border:1px solid rgba(212,175,55,.45);border-radius:20px;padding:20px;box-shadow:0 22px 70px rgba(0,0,0,.6);color:#eee;max-height:92vh;overflow:auto}
      .dh-commercial-title{color:#f0c040;text-align:center;margin:0 0 8px;font-size:1.38rem;font-weight:800}
      .dh-commercial-sub{color:#b7ad98;text-align:center;font-size:.88rem;line-height:1.9;margin:0 0 14px}
      .dh-commercial-label{display:block;color:#d7caa9;font-size:.82rem;margin:9px 2px 5px;text-align:right}
      .dh-commercial-field{position:relative}
      .dh-commercial-input{width:100%;box-sizing:border-box;padding:13px 14px;border-radius:12px;border:1px solid #353545;background:#0f0f18;color:#fff;font:inherit;margin:0;outline:none;transition:border-color .2s,box-shadow .2s}
      .dh-commercial-input:focus{border-color:rgba(240,192,64,.75);box-shadow:0 0 0 3px rgba(240,192,64,.1)}
      .dh-commercial-input.has-toggle{padding-left:48px}
      .dh-commercial-toggle{position:absolute;left:8px;top:50%;transform:translateY(-50%);width:34px;height:34px;border:0;border-radius:9px;background:transparent;color:#b8ad94;cursor:pointer;font-size:1rem}
      .dh-commercial-toggle:hover{background:rgba(255,255,255,.06);color:#f0c040}
      .dh-commercial-actions{display:flex;gap:9px;margin-top:15px}
      .dh-commercial-actions .btn{flex:1;margin:0;min-height:48px}
      .dh-commercial-error{color:#ff8787;min-height:1.45em;font-size:.83rem;line-height:1.7;margin-top:8px;text-align:right}
      .dh-commercial-success{color:#7fe2aa;font-size:.82rem;line-height:1.7;margin-top:8px;text-align:center}
      .dh-commercial-note{color:#8f845f;font-size:.77rem;line-height:1.8;margin-top:11px;text-align:center}
      .dh-commercial-price{font-size:2rem;color:#f0c040;font-weight:850;text-align:center;margin:6px 0}
      .dh-commercial-pack{background:#10101a;border:1px solid rgba(212,175,55,.22);border-radius:14px;padding:14px;margin:12px 0;color:#cbb98a;line-height:2.05;text-align:center}
      .dh-commercial-pack .badge{display:inline-block;padding:4px 10px;border-radius:999px;background:rgba(240,192,64,.1);border:1px solid rgba(240,192,64,.22);font-size:.72rem;color:#e0c876;margin-bottom:5px}
      .dh-commercial-link{background:none;border:0;color:#d4af37;text-decoration:underline;cursor:pointer;font:inherit;padding:6px}
      .dh-commercial-divider{height:1px;background:rgba(255,255,255,.07);margin:13px 0 10px}
      .dh-commercial-status{display:flex;align-items:center;justify-content:center;gap:8px;font-size:.8rem;color:#9f957f;margin-top:10px}
      .dh-commercial-spinner{width:14px;height:14px;border:2px solid rgba(240,192,64,.2);border-top-color:#f0c040;border-radius:50%;animation:dhspin .8s linear infinite}
      @keyframes dhspin{to{transform:rotate(360deg)}}
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
    ov.addEventListener('click', function (e) { if (e.target === ov && !BUSY) closeModal(); });
    document.body.appendChild(ov);
    return ov;
  }

  function addPasswordToggle(inputId, buttonId) {
    var input = el(inputId), button = el(buttonId);
    if (!input || !button) return;
    button.onclick = function () {
      var visible = input.type === 'text';
      input.type = visible ? 'password' : 'text';
      button.textContent = visible ? '◉' : '◉̸';
      button.setAttribute('aria-label', visible ? 'نمایش رمز عبور' : 'مخفی کردن رمز عبور');
      input.focus();
    };
  }

  function showAuthModal(initialMode) {
    var mode = initialMode === 'login' ? 'login' : 'register';
    var ov = showModal('');

    function paint() {
      var title = mode === 'login' ? 'ورود به حساب' : 'ساخت حساب';
      var action = mode === 'login' ? 'ورود' : 'ثبت‌نام';
      var helper = mode === 'login'
        ? 'با شماره موبایل و رمز عبور وارد حساب خود شوید.'
        : 'برای ذخیره سفر و اعتبارها، حساب شما روی سرور ساخته می‌شود.';

      ov.querySelector('.dh-commercial-modal').innerHTML =
        '<h2 class="dh-commercial-title">' + title + '</h2>' +
        '<p class="dh-commercial-sub">' + helper + '</p>' +
        (mode === 'register'
          ? '<label class="dh-commercial-label" for="dh-c-name">نام</label>' +
            '<input id="dh-c-name" class="dh-commercial-input" placeholder="نام و نام خانوادگی" autocomplete="name">'
          : '') +
        '<label class="dh-commercial-label" for="dh-c-phone">شماره موبایل</label>' +
        '<input id="dh-c-phone" class="dh-commercial-input" type="tel" inputmode="numeric" dir="ltr" placeholder="09xxxxxxxxx" autocomplete="tel">' +
        '<label class="dh-commercial-label" for="dh-c-pass">رمز عبور</label>' +
        '<div class="dh-commercial-field">' +
          '<input id="dh-c-pass" class="dh-commercial-input has-toggle" type="password" placeholder="حداقل ۸ کاراکتر" autocomplete="current-password">' +
          '<button type="button" class="dh-commercial-toggle" id="dh-c-pass-toggle" aria-label="نمایش رمز عبور">◉</button>' +
        '</div>' +
        '<div id="dh-c-err" class="dh-commercial-error"></div>' +
        '<div class="dh-commercial-actions">' +
          '<button type="button" class="btn btn-primary" id="dh-c-submit">' + action + '</button>' +
          '<button type="button" class="btn" id="dh-c-close">انصراف</button>' +
        '</div>' +
        '<p class="dh-commercial-note">رمز عبور هرگز روی کلاینت اعتبارسنجی مالی نمی‌شود؛ احراز هویت توسط سرور انجام می‌شود.</p>' +
        '<div style="text-align:center;margin-top:4px">' +
          (mode === 'login'
            ? '<button type="button" class="dh-commercial-link" id="dh-c-switch">ساخت حساب جدید</button>'
            : '<button type="button" class="dh-commercial-link" id="dh-c-switch">حساب دارم؛ ورود</button>') +
        '</div>';

      addPasswordToggle('dh-c-pass', 'dh-c-pass-toggle');
      el('dh-c-close').onclick = function () { if (!BUSY) closeModal(); };
      el('dh-c-switch').onclick = function () { if (!BUSY) { mode = mode === 'login' ? 'register' : 'login'; paint(); } };
      el('dh-c-submit').onclick = async function () {
        if (BUSY) return;
        BUSY = true;
        var submit = el('dh-c-submit');
        var err = el('dh-c-err');
        if (err) err.textContent = '';
        setBusyButton(submit, mode === 'login' ? 'در حال ورود…' : 'در حال ثبت‌نام…', action, true);
        var phone = safeText(el('dh-c-phone').value).trim().replace(/[۰-۹]/g, function (d) { return String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)); });
        var pass = safeText(el('dh-c-pass').value);
        var name = mode === 'register' ? safeText(el('dh-c-name').value).trim() : '';
        if (mode === 'register' && name.length < 2) { if (err) err.textContent = 'نام را کامل وارد کن.'; BUSY = false; setBusyButton(submit, '', action, false); return; }
        if (!/^09\d{9}$/.test(phone)) { if (err) err.textContent = 'شماره موبایل را به‌صورت 09xxxxxxxxx وارد کن.'; BUSY = false; setBusyButton(submit, '', action, false); return; }
        if (pass.length < 8) { if (err) err.textContent = 'رمز عبور باید حداقل ۸ کاراکتر داشته باشد.'; BUSY = false; setBusyButton(submit, '', action, false); return; }
        try {
          var data = mode === 'register'
            ? await global.DHAuth.register(name, phone, pass)
            : await global.DHAuth.login(phone, pass);
          if (data && data.user) saveLocalUser(data.user);
          if (data && typeof data.quota === 'number') setLocalQuota({ used: data.quota > 0 ? 0 : 1, premium: false });
          closeModal();
          await continueAfterAuth();
        } catch (e) {
          if (err) err.textContent = safeText(e && e.message ? e.message : e) || 'خطا در ارتباط با سرور.';
        } finally {
          BUSY = false;
          if (el('dh-c-submit')) setBusyButton(el('dh-c-submit'), '', action, false);
        }
      };
    }
    paint();
  }

  function paymentErrorText(e) {
    var msg = safeText(e && e.message ? e.message : e);
    if (/merchant|not configured|credential|authority/i.test(msg)) {
      return 'درگاه هنوز آمادهٔ تراکنش نیست. وضعیت Merchant ID و فعال‌سازی زرین‌پال را بررسی کنید.';
    }
    if (/timeout|timed out|network|failed to fetch/i.test(msg)) {
      return 'ارتباط با درگاه برقرار نشد. اتصال شبکه و وضعیت سرویس زرین‌پال را بررسی کنید.';
    }
    return msg || 'ایجاد درخواست پرداخت ناموفق بود.';
  }

  async function openPurchaseModal() {
    if (BUSY) return;
    showModal(
      '<h2 class="dh-commercial-title">خرید بسته ۳ تست</h2>' +
      '<p class="dh-commercial-sub">برای ادامه، پرداخت امن از طریق زرین‌پال انجام می‌شود.</p>' +
      '<div class="dh-commercial-pack"><span class="badge">بسته استاندارد</span><div class="dh-commercial-price">۲۴۹٬۰۰۰ تومان</div><div>۳ تست · بدون تاریخ انقضا</div></div>' +
      '<p class="dh-commercial-sub">مبلغ و تعداد اعتبار فقط از سمت سرور تعیین می‌شود.</p>' +
      '<div id="dh-buy-err" class="dh-commercial-error"></div>' +
      '<div id="dh-buy-status" class="dh-commercial-status" hidden><span class="dh-commercial-spinner"></span><span>در حال اتصال به درگاه…</span></div>' +
      '<div class="dh-commercial-actions">' +
        '<button type="button" class="btn btn-primary" id="dh-buy-now">ادامه به درگاه</button>' +
        '<button type="button" class="btn" id="dh-buy-close">انصراف</button>' +
      '</div>' +
      '<div class="dh-commercial-divider"></div>' +
      '<p class="dh-commercial-note">پس از پرداخت، تراکنش توسط سرور Verify می‌شود و اعتبار به حساب شما اضافه خواهد شد.</p>'
    );

    el('dh-buy-close').onclick = function () { if (!BUSY) closeModal(); };
    el('dh-buy-now').onclick = async function () {
      if (BUSY) return;
      BUSY = true;
      var button = el('dh-buy-now');
      var close = el('dh-buy-close');
      var err = el('dh-buy-err');
      var status = el('dh-buy-status');
      if (err) err.textContent = '';
      if (status) status.hidden = false;
      setBusyButton(button, 'در حال اتصال…', 'ادامه به درگاه', true);
      if (close) close.disabled = true;
      try {
        if (!global.DHAuth || !global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) {
          BUSY = false;
          closeModal();
          showAuthModal('login');
          return;
        }
        var payment = await global.DHAuth.createPayment();
        if (!payment || !payment.payment_url) throw new Error('سرور آدرس درگاه را برنگرداند.');
        if (status) status.querySelector('span:last-child').textContent = 'در حال انتقال به زرین‌پال…';
        window.location.assign(payment.payment_url);
      } catch (e) {
        if (status) status.hidden = true;
        if (err) err.textContent = paymentErrorText(e);
        if (close) close.disabled = false;
        setBusyButton(button, '', 'ادامه به درگاه', false);
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
      if (global.DHShell && typeof global.DHShell.startJourney === 'function') global.DHShell.startJourney();
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
        '<p class="dh-commercial-sub">' + escapeHtml(msg) + '</p>' +
        '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-error-close">باشه</button></div>'
      );
      el('dh-error-close').onclick = closeModal;
    }
  }

  function installButtonHooks() {
    function patchButtons() {
      document.querySelectorAll('#dh-start-journey, #dh-continue-journey, #dh-p-journey').forEach(function (btn) {
        if (btn.__dhCommercialHooked) return;
        btn.__dhCommercialHooked = true;
        btn.onclick = function (e) { if (e) e.preventDefault(); continueAfterAuth(); };
      });
      var premium = el('dh-p-prem');
      if (premium && !premium.__dhCommercialHooked) {
        premium.__dhCommercialHooked = true;
        premium.textContent = 'خرید بسته ۳ تست';
        premium.onclick = function (e) { if (e) e.preventDefault(); openPurchaseModal(); };
      }
    }
    patchButtons();
    var observer = new MutationObserver(patchButtons);
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function boot() {
    if (!global.DHAuth) return;
    installButtonHooks();
  }

  global.DHCommercialUI = {
    showAuth: showAuthModal,
    showPurchase: openPurchaseModal,
    startServerAuthorizedJourney: continueAfterAuth
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})(window);
