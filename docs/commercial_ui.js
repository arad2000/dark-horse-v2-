/* commercial_ui.js — single auth flow + server-authoritative credit gate */
(function (global) {
  'use strict';

  var USER_KEY = 'dh_local_user_v1';
  var QUOTA_KEY = 'dh_local_quota_v1';
  var BUSY = false;

  function el(id) { return document.getElementById(id); }
  function text(v) { return String(v == null ? '' : v); }
  function digits(v) {
    return text(v).replace(/[۰-۹]/g, function (d) { return String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)); });
  }
  function escapeHtml(v) {
    return text(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function saveLocalUser(user) {
    try { localStorage.setItem(USER_KEY, JSON.stringify(user || null)); } catch (_) {}
  }
  function clearLocalState() {
    try { localStorage.removeItem('dh_auth_v1'); } catch (_) {}
    try { localStorage.removeItem(USER_KEY); } catch (_) {}
    try { localStorage.removeItem(QUOTA_KEY); } catch (_) {}
    try { localStorage.removeItem('dh_last_result_v1'); } catch (_) {}
  }
  function setLocalQuota(remaining) {
    try {
      localStorage.setItem(QUOTA_KEY, JSON.stringify({
        used: Number(remaining) > 0 ? 0 : 1,
        premium: false,
        serverRemaining: Math.max(0, Number(remaining) || 0)
      }));
    } catch (_) {}
  }
  function currentJourneySessionId() {
    try {
      var journey = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null');
      return journey && journey.sessionId ? String(journey.sessionId) : null;
    } catch (_) { return null; }
  }

  function addStyles() {
    if (el('dh-commercial-styles')) return;
    var s = document.createElement('style');
    s.id = 'dh-commercial-styles';
    s.textContent =
      '.dh-commercial-overlay{position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:18px;backdrop-filter:blur(7px)}' +
      '.dh-commercial-modal{width:100%;max-width:430px;background:#161622;border:1px solid rgba(212,175,55,.45);border-radius:18px;padding:20px;box-shadow:0 20px 60px rgba(0,0,0,.55);color:#eee}' +
      '.dh-commercial-title{color:#f0c040;text-align:center;margin:0 0 8px;font-size:1.35rem}' +
      '.dh-commercial-sub{color:#b0a080;text-align:center;font-size:.86rem;line-height:1.8;margin-bottom:14px}' +
      '.dh-commercial-input{width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#0f0f18;color:#fff;font:inherit;margin:6px 0;box-sizing:border-box}' +
      '.dh-commercial-actions{display:flex;gap:8px;margin-top:12px}' +
      '.dh-commercial-actions .btn{flex:1;margin:0}' +
      '.dh-commercial-error{color:#ff7b7b;min-height:1.4em;font-size:.82rem;margin-top:6px}' +
      '.dh-commercial-note{color:#8f845f;font-size:.76rem;line-height:1.7;margin-top:10px;text-align:center}' +
      '.dh-commercial-price{font-size:2rem;color:#f0c040;font-weight:800;text-align:center;margin:8px 0}' +
      '.dh-commercial-pack{background:#10101a;border:1px solid rgba(212,175,55,.22);border-radius:12px;padding:12px;margin:12px 0;color:#cbb98a;line-height:2;text-align:center}' +
      '.dh-commercial-link{background:none;border:0;color:#d4af37;text-decoration:underline;cursor:pointer;font:inherit;padding:4px}' +
      '.dh-otp-box{display:flex;gap:8px;justify-content:center;direction:ltr;margin:14px 0}' +
      '.dh-otp-box input{width:44px;height:52px;text-align:center;font-size:1.25rem;font-weight:800}' +
      '.dh-commercial-status{color:#cbb98a;text-align:center;margin:10px 0}';
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
    ov.addEventListener('click', function (e) {
      if (e.target === ov && !BUSY) closeModal();
    });
    document.body.appendChild(ov);
    return ov;
  }

  function showOtpModal(reg) {
    var fields = '';
    for (var i = 1; i <= 6; i += 1) {
      fields += '<input id="dh-otp-' + i + '" class="dh-commercial-input" inputmode="numeric" maxlength="1" autocomplete="one-time-code">';
    }
    var ov = showModal(
      '<h2 class="dh-commercial-title">تأیید شماره موبایل</h2>' +
      '<p class="dh-commercial-sub">کد ۶ رقمی ارسال‌شده به <strong dir="ltr">' + escapeHtml(reg.phone) + '</strong> را وارد کنید.</p>' +
      '<div class="dh-otp-box">' + fields + '</div>' +
      '<div id="dh-otp-err" class="dh-commercial-error"></div>' +
      '<div id="dh-otp-timer" class="dh-commercial-status">اعتبار کد: ۵:۰۰</div>' +
      '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-otp-submit">تأیید و ساخت حساب</button><button type="button" class="btn" id="dh-otp-cancel">انصراف</button></div>' +
      '<p class="dh-commercial-note">کد یک‌بارمصرف ۵ دقیقه معتبر است و تلاش‌های ناموفق محدود هستند.</p>'
    );
    var fieldsList = [];
    for (var j = 1; j <= 6; j += 1) fieldsList.push(el('dh-otp-' + j));
    fieldsList.forEach(function (field, idx) {
      field.addEventListener('input', function () {
        field.value = digits(field.value).replace(/\D/g, '').slice(0, 1);
        if (field.value && fieldsList[idx + 1]) fieldsList[idx + 1].focus();
      });
      field.addEventListener('keydown', function (e) {
        if (e.key === 'Backspace' && !field.value && fieldsList[idx - 1]) fieldsList[idx - 1].focus();
      });
    });
    fieldsList[0].focus();
    var left = Number(reg.expires_in || 300);
    var timer = el('dh-otp-timer');
    var timerId = setInterval(function () {
      left -= 1;
      if (left <= 0) {
        clearInterval(timerId);
        if (timer) timer.textContent = 'کد منقضی شده است.';
      } else if (timer) {
        timer.textContent = 'اعتبار کد: ' + Math.floor(left / 60) + ':' + String(left % 60).padStart(2, '0');
      }
    }, 1000);
    el('dh-otp-cancel').onclick = function () { clearInterval(timerId); closeModal(); };
    el('dh-otp-submit').onclick = async function () {
      if (BUSY) return;
      BUSY = true;
      var err = el('dh-otp-err');
      if (err) err.textContent = '';
      var code = fieldsList.map(function (f) { return f.value; }).join('');
      if (code.length !== 6) {
        if (err) err.textContent = 'کد ۶ رقمی را کامل وارد کنید.';
        BUSY = false;
        return;
      }
      try {
        var data = await global.DHAuth.verifyRegistration(reg.challenge_id, code);
        if (data && data.user) saveLocalUser(data.user);
        if (data && typeof data.quota === 'number') setLocalQuota(data.quota);
        clearInterval(timerId);
        closeModal();
        await continueAfterAuth();
      } catch (e) {
        if (err) err.textContent = text(e && e.message ? e.message : e) || 'تأیید کد ناموفق بود.';
        BUSY = false;
      }
    };
    return ov;
  }

  function showAuthModal(initialMode) {
    var mode = initialMode === 'login' ? 'login' : 'register';
    var ov = showModal('');

    function paint() {
      var title = mode === 'login' ? 'ورود به حساب' : 'ساخت حساب';
      var action = mode === 'login' ? 'ورود' : 'ارسال کد ثبت‌نام';
      ov.querySelector('.dh-commercial-modal').innerHTML =
        '<h2 class="dh-commercial-title">' + title + '</h2>' +
        '<p class="dh-commercial-sub">' + (mode === 'login' ? 'با شماره موبایل و رمز عبور وارد حساب خود شوید.' : 'نام، موبایل و رمز را وارد کنید؛ سپس کد پیامکی کاوه‌نگار را تأیید کنید.') + '</p>' +
        (mode === 'register' ? '<input id="dh-c-name" class="dh-commercial-input" placeholder="نام و نام خانوادگی" autocomplete="name">' : '') +
        '<input id="dh-c-phone" class="dh-commercial-input" inputmode="numeric" dir="ltr" placeholder="09xxxxxxxxx" autocomplete="tel">' +
        '<input id="dh-c-pass" class="dh-commercial-input" type="password" placeholder="رمز عبور (حداقل ۸ کاراکتر)" autocomplete="current-password">' +
        '<div id="dh-c-err" class="dh-commercial-error"></div>' +
        '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-c-submit">' + action + '</button><button type="button" class="btn" id="dh-c-close">انصراف</button></div>' +
        '<p class="dh-commercial-note">احراز هویت، OTP و اعتبارها در سمت سرور کنترل می‌شوند.</p>' +
        '<div style="text-align:center;margin-top:8px"><button type="button" class="dh-commercial-link" id="dh-c-switch">' + (mode === 'login' ? 'ساخت حساب جدید' : 'حساب دارم؛ ورود') + '</button></div>';

      el('dh-c-close').onclick = closeModal;
      el('dh-c-switch').onclick = function () {
        if (BUSY) return;
        mode = mode === 'login' ? 'register' : 'login';
        paint();
        if (mode === 'login' && typeof global.__dhInstallForgotLink === 'function') global.__dhInstallForgotLink();
      };
      el('dh-c-submit').onclick = async function () {
        if (BUSY) return;
        BUSY = true;
        var err = el('dh-c-err');
        if (err) err.textContent = '';
        var phone = digits(el('dh-c-phone').value).replace(/\s+/g, '');
        var pass = el('dh-c-pass').value;
        var name = mode === 'register' ? el('dh-c-name').value.trim() : '';
        if (mode === 'register' && name.length < 2) { if (err) err.textContent = 'نام را کامل وارد کنید.'; BUSY = false; return; }
        if (!/^09\d{9}$/.test(phone)) { if (err) err.textContent = 'شماره موبایل را به‌صورت 09xxxxxxxxx وارد کنید.'; BUSY = false; return; }
        if (pass.length < 8) { if (err) err.textContent = 'رمز عبور باید حداقل ۸ کاراکتر باشد.'; BUSY = false; return; }
        try {
          if (mode === 'login') {
            var logged = await global.DHAuth.login(phone, pass);
            if (logged && logged.user) saveLocalUser(logged.user);
            if (logged && typeof logged.quota === 'number') setLocalQuota(logged.quota);
            closeModal();
            await continueAfterAuth();
          } else {
            var registration = await global.DHAuth.register(name, phone, pass);
            if (!registration || !registration.challenge_id) throw new Error('پاسخ OTP ثبت‌نام معتبر نیست.');
            closeModal();
            showOtpModal({ phone: phone, challenge_id: registration.challenge_id, expires_in: registration.expires_in });
          }
        } catch (e) {
          if (err) err.textContent = text(e && e.message ? e.message : e) || 'خطا در ارتباط با سرور.';
        } finally {
          BUSY = false;
        }
      };
    }
    paint();
    if (mode === 'login' && typeof global.__dhInstallForgotLink === 'function') global.__dhInstallForgotLink();
  }

  function openExternalPay(url) {
    if (!url) return false;
    var target = String(url);
    try {
      if (global.AndroidBridge && typeof global.AndroidBridge.openExternalUrl === 'function') {
        global.AndroidBridge.openExternalUrl(target);
        return true;
      }
    } catch (_) {}
    try { window.location.assign(target); return true; } catch (_) {}
    return false;
  }

  function openPurchaseModal() {
    if (!global.DHAuth || typeof global.DHAuth.isLoggedIn !== 'function' || !global.DHAuth.isLoggedIn()) {
      showAuthModal('login');
      return;
    }
    showModal(
      '<h2 class="dh-commercial-title">خرید بسته ۳ تست</h2>' +
      '<div class="dh-commercial-pack"><div class="dh-commercial-price">۲۴۹٬۰۰۰ تومان</div><div>۳ تست · بدون تاریخ انقضا</div></div>' +
      '<p class="dh-commercial-sub">مبلغ و تعداد اعتبار فقط از سمت سرور تعیین می‌شود.</p>' +
      '<div id="dh-buy-err" class="dh-commercial-error"></div>' +
      '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-buy-now">ادامه به درگاه</button><button type="button" class="btn" id="dh-buy-close">انصراف</button></div>' +
      '<p class="dh-commercial-note">تا زمان فعال‌شدن Merchant، خرید تجاری ممکن است موقتاً غیرفعال باشد.</p>'
    );
    el('dh-buy-close').onclick = closeModal;
    el('dh-buy-now').onclick = async function () {
      if (BUSY) return;
      BUSY = true;
      var err = el('dh-buy-err');
      if (err) err.textContent = '';
      try {
        var payment = await global.DHAuth.createPayment();
        if (!payment || !payment.payment_url) throw new Error('آدرس درگاه از سرور دریافت نشد.');
        closeModal();
        openExternalPay(payment.payment_url);
      } catch (e) {
        if (err) err.textContent = text(e && e.message ? e.message : e) || 'ایجاد درخواست پرداخت ناموفق بود.';
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
      setLocalQuota(remaining);
      if (remaining <= 0) {
        openPurchaseModal();
        return;
      }
      await global.DHAuth.consumeTest();
      setLocalQuota(remaining - 1);
      closeModal();
      if (global.DHShell && typeof global.DHShell.startJourney === 'function') global.DHShell.startJourney();
    } catch (e) {
      var msg = text(e && e.message ? e.message : e);
      if (/401|authentication/i.test(msg)) {
        doLogout(false);
        showAuthModal('login');
        return;
      }
      showModal('<h2 class="dh-commercial-title">خطا</h2><p class="dh-commercial-sub">' + escapeHtml(msg) + '</p><div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-error-close">باشه</button></div>');
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
        summary.result = type === 'branches'
          ? { branch_discovery_result: data.branch_discovery_result || data }
          : { discovery_result: data.discovery_result || data };
      }
      await global.DHAuth.saveResult(summary);
    } catch (e) {
      console.warn('Final result summary persistence skipped:', e);
    }
  }

  function doLogout(reload) {
    try { if (global.DHAuth && typeof global.DHAuth.logout === 'function') global.DHAuth.logout(); } catch (_) {}
    clearLocalState();
    try {
      global.dispatchEvent(new CustomEvent('dh-auth-changed', { detail: { loggedIn: false } }));
    } catch (_) {}
    if (reload !== false) {
      try { global.location.reload(); } catch (_) {}
    }
  }

  function bindButton(id, handler) {
    var button = el(id);
    if (!button || button.__dhCommercialBound) return;
    button.__dhCommercialBound = true;
    button.onclick = function (event) {
      if (event) event.preventDefault();
      handler(event);
    };
  }

  function installButtonHooks() {
    bindButton('dh-start-journey', continueAfterAuth);
    bindButton('dh-continue-journey', continueAfterAuth);
    bindButton('dh-p-journey', continueAfterAuth);
    bindButton('dh-p-buy', openPurchaseModal);
    bindButton('dh-p-out', function () { doLogout(true); });
  }

  function syncQuota(done) {
    if (!global.DHAuth || !global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) {
      if (done) done(null);
      return;
    }
    global.DHAuth.quota().then(function (data) {
      var remaining = Math.max(0, Number(data && data.credits_remaining) || 0);
      setLocalQuota(remaining);
      if (done) done(remaining);
    }).catch(function () { if (done) done(null); });
  }

  function boot() {
    global.DHCommercialUI = {
      showAuth: showAuthModal,
      showPurchase: openPurchaseModal,
      startServerAuthorizedJourney: continueAfterAuth,
      persistFinalResultSummary: persistFinalResultSummary,
      logout: doLogout,
      syncQuota: syncQuota,
      closeModal: closeModal
    };
    installButtonHooks();
    installDiscoverySessionBridge();
    if (document.body && typeof MutationObserver !== 'undefined') {
      var observer = new MutationObserver(function () { installButtonHooks(); });
      observer.observe(document.body, { childList: true, subtree: true });
    }
    syncQuota(function () {});
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
          var body = await response.clone().json();
          if (body && body.session_id) {
            var journey = null;
            try { journey = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null'); } catch (_) {}
            journey = journey && typeof journey === 'object' ? journey : {};
            journey.sessionId = String(body.session_id);
            try { localStorage.setItem('darkhorse_session_v2', JSON.stringify(journey)); } catch (_) {}
            if (global.DHCommercialUI && typeof global.DHCommercialUI.persistFinalResultSummary === 'function') {
              try { await global.DHCommercialUI.persistFinalResultSummary(body, /branch-discovery/.test(url) ? 'branches' : 'majors'); } catch (_) {}
            }
          }
        } catch (_) {}
      }
      return response;
    };
  }

  global.DHCommercialUI = {
    showAuth: showAuthModal,
    showPurchase: openPurchaseModal,
    startServerAuthorizedJourney: continueAfterAuth,
    persistFinalResultSummary: persistFinalResultSummary,
    logout: doLogout,
    syncQuota: syncQuota,
    closeModal: closeModal
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})(window);