/* password_reset_ui.js — OTP-based forgot-password flow */
(function (global) {
  'use strict';
  var installed = false;
  var challengeId = null;
  function el(id) { return document.getElementById(id); }
  function safe(v) { return String(v == null ? '' : v); }

  function renderStepOne() {
    var modal = document.querySelector('.dh-commercial-modal');
    if (!modal) return;
    modal.innerHTML = '<h2 class="dh-commercial-title">بازیابی رمز عبور</h2>' +
      '<p class="dh-commercial-sub">شماره موبایل حساب را وارد کنید. در صورت وجود حساب، کد تأیید برای شما پیامک می‌شود.</p>' +
      '<input id="dh-reset-phone" class="dh-commercial-input" inputmode="tel" autocomplete="tel" placeholder="شماره موبایل">' +
      '<div id="dh-reset-err" class="dh-commercial-error"></div>' +
      '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-reset-request">ارسال کد</button><button type="button" class="btn" id="dh-reset-back">بازگشت</button></div>' +
      '<p class="dh-commercial-note">برای امنیت، وجود یا عدم وجود حساب از پیام پاسخ قابل تشخیص نیست.</p>';
    el('dh-reset-request').onclick = async function () {
      var phone = safe(el('dh-reset-phone').value).trim();
      var err = el('dh-reset-err');
      if (!/^09\d{9}$/.test(phone)) { err.textContent = 'شماره موبایل را درست وارد کنید.'; return; }
      try {
        var result = await global.DHAuth.requestPasswordReset(phone);
        if (!result || !result.challenge_id) { err.textContent = 'اگر حسابی با این شماره وجود داشته باشد، کد بازیابی ارسال می‌شود.'; return; }
        challengeId = result.challenge_id;
        renderStepTwo();
      } catch (e) { err.textContent = safe(e && e.message ? e.message : e); }
    };
    el('dh-reset-back').onclick = function () { global.DHCommercialUI.showAuth('login'); };
  }

  function renderStepTwo() {
    var modal = document.querySelector('.dh-commercial-modal');
    if (!modal) return;
    modal.innerHTML = '<h2 class="dh-commercial-title">تعیین رمز جدید</h2>' +
      '<p class="dh-commercial-sub">کد پیامک‌شده و رمز جدید را وارد کنید.</p>' +
      '<input id="dh-reset-code" class="dh-commercial-input" inputmode="numeric" autocomplete="one-time-code" placeholder="کد ۶ رقمی">' +
      '<input id="dh-reset-pass" class="dh-commercial-input" type="password" autocomplete="new-password" placeholder="رمز جدید (حداقل ۸ کاراکتر)">' +
      '<input id="dh-reset-pass2" class="dh-commercial-input" type="password" autocomplete="new-password" placeholder="تکرار رمز جدید">' +
      '<div id="dh-reset-err" class="dh-commercial-error"></div>' +
      '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-reset-submit">ذخیره رمز جدید</button><button type="button" class="btn" id="dh-reset-cancel">انصراف</button></div>';
    el('dh-reset-submit').onclick = async function () {
      var code = safe(el('dh-reset-code').value).trim();
      var pass = safe(el('dh-reset-pass').value);
      var pass2 = safe(el('dh-reset-pass2').value);
      var err = el('dh-reset-err');
      if (!/^\d{6}$/.test(code)) { err.textContent = 'کد تأیید باید ۶ رقمی باشد.'; return; }
      if (pass.length < 8) { err.textContent = 'رمز جدید باید حداقل ۸ کاراکتر باشد.'; return; }
      if (pass !== pass2) { err.textContent = 'تکرار رمز با رمز جدید یکسان نیست.'; return; }
      try {
        var result = await global.DHAuth.verifyPasswordReset(challengeId, code, pass);
        if (!result || !result.token) throw new Error('بازیابی رمز کامل نشد.');
        challengeId = null;
        global.DHCommercialUI.startServerAuthorizedJourney();
      } catch (e) { err.textContent = safe(e && e.message ? e.message : e); }
    };
    el('dh-reset-cancel').onclick = function () { challengeId = null; global.DHCommercialUI.showAuth('login'); };
  }

  function ensureForgotLink() {
    var modal = document.querySelector('.dh-commercial-modal');
    if (!modal || el('dh-c-forgot') || !el('dh-c-submit')) return;
    var switchEl = el('dh-c-switch');
    var host = switchEl && switchEl.parentNode ? switchEl.parentNode : modal;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'dh-c-forgot';
    btn.className = 'dh-commercial-link';
    btn.textContent = 'رمز عبور را فراموش کرده‌ام';
    btn.onclick = renderStepOne;
    host.appendChild(btn);
  }

  function boot() {
    if (installed) return;
    installed = true;
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(ensureForgotLink).observe(document.body, { childList: true, subtree: true });
    }
    ensureForgotLink();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true }); else boot();
})(window);
