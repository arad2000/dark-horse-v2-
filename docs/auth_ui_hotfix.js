/* auth_ui_hotfix.js — release auth/OTP resilience and UI deduplication */
(function (global) {
  'use strict';
  var BUSY = false;

  function el(id) { return document.getElementById(id); }
  function text(v) { return String(v == null ? '' : v); }
  function modal() { return document.querySelector('.dh-commercial-modal'); }
  function error(message) {
    var node = el('dh-c-err') || el('dh-reset-err');
    if (node) node.textContent = text(message || 'عملیات انجام نشد.');
  }

  function renderRegistrationConfirm(challengeId, expiresIn) {
    var m = modal();
    if (!m) return;
    m.innerHTML =
      '<h2 class="dh-commercial-title">تأیید شماره موبایل</h2>' +
      '<p class="dh-commercial-sub">کد ۶ رقمی ارسال‌شده را وارد کنید تا حساب شما ساخته شود.</p>' +
      '<input id="dh-reg-code" class="dh-commercial-input" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="کد تأیید">' +
      '<div id="dh-reg-err" class="dh-commercial-error"></div>' +
      '<div class="dh-commercial-actions">' +
        '<button type="button" class="btn btn-primary" id="dh-reg-confirm">تأیید و ساخت حساب</button>' +
        '<button type="button" class="btn" id="dh-reg-cancel">انصراف</button>' +
      '</div>' +
      '<p class="dh-commercial-note">کد تا ' + Math.max(1, Math.ceil(Number(expiresIn || 300) / 60)) + ' دقیقه معتبر است.</p>';
    el('dh-reg-cancel').onclick = function () { if (global.DHCommercialUI && global.DHCommercialUI.showAuth) global.DHCommercialUI.showAuth('register'); };
    el('dh-reg-confirm').onclick = async function () {
      if (BUSY) return;
      BUSY = true;
      var e = el('dh-reg-err');
      if (e) e.textContent = '';
      var code = text((el('dh-reg-code') || {}).value).trim().replace(/[۰-۹]/g, function (c) { return '۰۱۲۳۴۵۶۷۸۹'.indexOf(c); });
      if (!/^\d{6}$/.test(code)) {
        if (e) e.textContent = 'کد تأیید باید ۶ رقم باشد.';
        BUSY = false;
        return;
      }
      try {
        var data = await global.DHAuth.verifyRegistration(challengeId, code);
        try { localStorage.setItem('dh_local_user_v1', JSON.stringify(data.user || null)); } catch (_) {}
        try { localStorage.setItem('dh_local_quota_v1', JSON.stringify({ used: 0, premium: false })); } catch (_) {}
        if (global.DHCommercialUI && typeof global.DHCommercialUI.closeModal === 'function') global.DHCommercialUI.closeModal();
        else {
          var ov = el('dh-commercial-overlay'); if (ov) ov.remove();
        }
        if (global.DHShell && typeof global.DHShell.startJourney === 'function') global.DHShell.startJourney();
      } catch (ex) {
        if (e) e.textContent = ex && ex.message ? ex.message : 'تأیید شماره انجام نشد.';
      } finally { BUSY = false; }
    };
  }

  async function interceptRegistration(event) {
    var button = event.target && event.target.closest ? event.target.closest('#dh-c-submit') : null;
    if (!button || !el('dh-c-name') || BUSY) return false;
    event.preventDefault();
    event.stopImmediatePropagation();
    BUSY = true;
    var err = el('dh-c-err');
    if (err) err.textContent = '';
    var name = text((el('dh-c-name') || {}).value).trim();
    var phone = text((el('dh-c-phone') || {}).value).trim();
    var pass = text((el('dh-c-pass') || {}).value);
    if (name.length < 2) { if (err) err.textContent = 'نام را وارد کنید.'; BUSY = false; return true; }
    if (!/^09\d{9}$/.test(phone)) { if (err) err.textContent = 'شماره موبایل را درست وارد کنید.'; BUSY = false; return true; }
    if (pass.length < 8) { if (err) err.textContent = 'رمز عبور باید حداقل ۸ کاراکتر باشد.'; BUSY = false; return true; }
    try {
      var data = await global.DHAuth.register(name, phone, pass);
      if (!data || !data.challenge_id) throw new Error('ماژول تأیید شماره موبایل پاسخ معتبری برنگرداند.');
      renderRegistrationConfirm(data.challenge_id, data.expires_in);
    } catch (e) {
      if (err) err.textContent = e && e.message ? e.message : 'ارسال کد ثبت‌نام انجام نشد.';
    } finally { BUSY = false; }
    return true;
  }

  function renderResetRequest() {
    var m = modal(); if (!m) return;
    m.innerHTML =
      '<h2 class="dh-commercial-title">فراموشی رمز عبور</h2>' +
      '<p class="dh-commercial-sub">شماره موبایل حساب خود را وارد کنید.</p>' +
      '<input id="dh-reset-phone" class="dh-commercial-input" inputmode="tel" autocomplete="tel" placeholder="شماره موبایل">' +
      '<div id="dh-reset-err" class="dh-commercial-error"></div>' +
      '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-reset-send">ارسال کد</button><button type="button" class="btn" id="dh-reset-back">بازگشت</button></div>';
    el('dh-reset-back').onclick = function () { if (global.DHCommercialUI && global.DHCommercialUI.showAuth) global.DHCommercialUI.showAuth('login'); };
    el('dh-reset-send').onclick = async function () {
      if (BUSY) return;
      BUSY = true; error('');
      var phone = text((el('dh-reset-phone') || {}).value).trim();
      if (!/^09\d{9}$/.test(phone)) { error('شماره موبایل را درست وارد کنید.'); BUSY = false; return; }
      try {
        var data = await global.DHAuth.requestPasswordReset(phone);
        if (data && data.challenge_id) renderResetConfirm(data.challenge_id, phone, data.expires_in);
        else {
          m.innerHTML = '<h2 class="dh-commercial-title">بازیابی رمز عبور</h2><p class="dh-commercial-sub">اگر حسابی با این شماره وجود داشته باشد، کد بازیابی ارسال می‌شود.</p><div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-reset-back">بازگشت به ورود</button></div>';
          el('dh-reset-back').onclick = function () { if (global.DHCommercialUI && global.DHCommercialUI.showAuth) global.DHCommercialUI.showAuth('login'); };
        }
      } catch (e) { error(e && e.message ? e.message : 'ارسال کد انجام نشد.'); }
      finally { BUSY = false; }
    };
  }

  function renderResetConfirm(challengeId, phone, expiresIn) {
    var m = modal(); if (!m) return;
    m.innerHTML =
      '<h2 class="dh-commercial-title">تغییر رمز عبور</h2><p class="dh-commercial-sub">کد ارسال‌شده به ' + text(phone) + ' را وارد کنید.</p>' +
      '<input id="dh-reset-code" class="dh-commercial-input" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="کد تأیید">' +
      '<input id="dh-reset-pass" class="dh-commercial-input" type="password" autocomplete="new-password" placeholder="رمز جدید (حداقل ۸ کاراکتر)">' +
      '<input id="dh-reset-pass2" class="dh-commercial-input" type="password" autocomplete="new-password" placeholder="تکرار رمز جدید">' +
      '<div id="dh-reset-err" class="dh-commercial-error"></div>' +
      '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-reset-confirm">ثبت رمز جدید</button><button type="button" class="btn" id="dh-reset-back">بازگشت</button></div>' +
      '<p class="dh-commercial-note">کد تا ' + Math.max(1, Math.ceil(Number(expiresIn || 300) / 60)) + ' دقیقه معتبر است.</p>';
    el('dh-reset-back').onclick = renderResetRequest;
    el('dh-reset-confirm').onclick = async function () {
      if (BUSY) return;
      BUSY = true; error('');
      var code = text((el('dh-reset-code') || {}).value).trim().replace(/[۰-۹]/g, function (c) { return '۰۱۲۳۴۵۶۷۸۹'.indexOf(c); });
      var pass = text((el('dh-reset-pass') || {}).value);
      var pass2 = text((el('dh-reset-pass2') || {}).value);
      if (!/^\d{6}$/.test(code)) { error('کد تأیید باید ۶ رقم باشد.'); BUSY = false; return; }
      if (pass.length < 8) { error('رمز جدید باید حداقل ۸ کاراکتر باشد.'); BUSY = false; return; }
      if (pass !== pass2) { error('تکرار رمز جدید یکسان نیست.'); BUSY = false; return; }
      try {
        await global.DHAuth.resetPassword(challengeId, code, pass);
        m.innerHTML = '<h2 class="dh-commercial-title">رمز عبور تغییر کرد</h2><p class="dh-commercial-sub">رمز جدید ثبت شد و نشست‌های قبلی بی‌اعتبار شدند.</p><div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-reset-done">ادامه</button></div>';
        el('dh-reset-done').onclick = function () { if (global.DHCommercialUI && global.DHCommercialUI.closeModal) global.DHCommercialUI.closeModal(); else { var ov=el('dh-commercial-overlay'); if(ov) ov.remove(); } };
      } catch (e) { error(e && e.message ? e.message : 'تغییر رمز انجام نشد.'); }
      finally { BUSY = false; }
    };
  }

  function installForgotLink() {
    var m = modal();
    var switchBtn = el('dh-c-switch');
    if (!m || !switchBtn || !el('dh-c-pass') || el('dh-forgot-password')) return;
    var wrap = document.createElement('div');
    wrap.id = 'dh-forgot-password-wrap';
    wrap.style.cssText = 'text-align:center;margin-top:8px';
    var b = document.createElement('button');
    b.type = 'button'; b.id = 'dh-forgot-password'; b.className = 'dh-commercial-link'; b.textContent = 'فراموشی رمز عبور';
    wrap.appendChild(b);
    switchBtn.parentNode.insertBefore(wrap, switchBtn.parentNode.firstChild);
    b.addEventListener('click', function (e) { e.preventDefault(); e.stopImmediatePropagation(); renderResetRequest(); }, true);
  }

  function dedupePurchaseButtons() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll('#dh-p-buy, #dh-p-prem, [data-testid="purchase-pack-3"]'));
    if (nodes.length <= 1) return;
    var keep = nodes.find(function (n) { return n.id === 'dh-p-buy'; }) || nodes[0];
    keep.id = 'dh-p-buy';
    keep.textContent = 'خرید بسته ۳ تست';
    keep.setAttribute('data-testid', 'purchase-pack-3');
    nodes.forEach(function (n) { if (n !== keep) n.remove(); });
  }

  function boot() {
    document.addEventListener('click', function (event) { interceptRegistration(event); }, true);
    var observer = new MutationObserver(function () {
      installForgotLink();
      dedupePurchaseButtons();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    installForgotLink();
    dedupePurchaseButtons();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})(window);
