/* password_reset_ui.js — phone OTP password recovery */
(function (global) {
  'use strict';

  var BUSY = false;
  var originalShowAuth = null;

  function el(id) { return document.getElementById(id); }
  function text(v) { return String(v == null ? '' : v); }
  function closeOverlay() {
    var ov = el('dh-commercial-overlay');
    if (ov) ov.remove();
  }

  function showResetError(message) {
    var node = el('dh-reset-err');
    if (node) node.textContent = text(message || 'خطا در بازیابی رمز عبور.');
  }

  function renderResetRequest() {
    var modal = document.querySelector('.dh-commercial-modal');
    if (!modal) return;
    modal.innerHTML =
      '<h2 class="dh-commercial-title">فراموشی رمز عبور</h2>' +
      '<p class="dh-commercial-sub">شماره موبایل حساب خود را وارد کنید. در صورت وجود حساب، کد بازیابی پیامک می‌شود.</p>' +
      '<input id="dh-reset-phone" class="dh-commercial-input" inputmode="tel" autocomplete="tel" placeholder="شماره موبایل">' +
      '<div id="dh-reset-err" class="dh-commercial-error"></div>' +
      '<div class="dh-commercial-actions">' +
        '<button type="button" class="btn btn-primary" id="dh-reset-send">ارسال کد</button>' +
        '<button type="button" class="btn" id="dh-reset-back">بازگشت</button>' +
      '</div>' +
      '<p class="dh-commercial-note">به دلایل امنیتی، وجود یا نبود حساب با شماره موبایل افشا نمی‌شود.</p>';

    el('dh-reset-back').onclick = function () { originalShowAuth('login'); };
    el('dh-reset-send').onclick = async function () {
      if (BUSY) return;
      BUSY = true;
      showResetError('');
      var phone = text((el('dh-reset-phone') || {}).value).trim();
      if (!/^09\d{9}$/.test(phone)) {
        showResetError('شماره موبایل را درست وارد کنید.');
        BUSY = false;
        return;
      }
      try {
        var data = await global.DHAuth.requestPasswordReset(phone);
        if (data && data.challenge_id) {
          renderResetConfirm(phone, data.challenge_id, Number(data.expires_in || 300));
        } else {
          renderResetGenericDone(data && data.message);
        }
      } catch (e) {
        showResetError(e && e.message ? e.message : 'ارسال کد انجام نشد.');
      } finally {
        BUSY = false;
      }
    };
  }

  function renderResetGenericDone(message) {
    var modal = document.querySelector('.dh-commercial-modal');
    if (!modal) return;
    modal.innerHTML =
      '<h2 class="dh-commercial-title">بازیابی رمز عبور</h2>' +
      '<p class="dh-commercial-sub">' + text(message || 'اگر حسابی با این شماره وجود داشته باشد، کد بازیابی ارسال می‌شود.') + '</p>' +
      '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-reset-back">بازگشت به ورود</button></div>';
    el('dh-reset-back').onclick = function () { originalShowAuth('login'); };
  }

  function renderResetConfirm(phone, challengeId, expiresIn) {
    var modal = document.querySelector('.dh-commercial-modal');
    if (!modal) return;
    modal.innerHTML =
      '<h2 class="dh-commercial-title">تغییر رمز عبور</h2>' +
      '<p class="dh-commercial-sub">کد ۶ رقمی ارسال‌شده به ' + text(phone) + ' را وارد کنید و رمز جدید بسازید.</p>' +
      '<input id="dh-reset-code" class="dh-commercial-input" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="کد تأیید">' +
      '<input id="dh-reset-pass" class="dh-commercial-input" type="password" autocomplete="new-password" placeholder="رمز جدید (حداقل ۸ کاراکتر)">' +
      '<input id="dh-reset-pass2" class="dh-commercial-input" type="password" autocomplete="new-password" placeholder="تکرار رمز جدید">' +
      '<div id="dh-reset-err" class="dh-commercial-error"></div>' +
      '<div class="dh-commercial-actions">' +
        '<button type="button" class="btn btn-primary" id="dh-reset-confirm">ثبت رمز جدید</button>' +
        '<button type="button" class="btn" id="dh-reset-back">بازگشت</button>' +
      '</div>' +
      '<p class="dh-commercial-note">کد تا ' + Math.max(1, Math.ceil(expiresIn / 60)) + ' دقیقه معتبر است و پس از استفاده یک‌بار مصرف خواهد بود.</p>';

    el('dh-reset-back').onclick = renderResetRequest;
    el('dh-reset-confirm').onclick = async function () {
      if (BUSY) return;
      BUSY = true;
      showResetError('');
      var code = text((el('dh-reset-code') || {}).value).trim();
      var pass = text((el('dh-reset-pass') || {}).value);
      var pass2 = text((el('dh-reset-pass2') || {}).value);
      if (!/^\d{6}$/.test(code)) {
        showResetError('کد تأیید باید ۶ رقم باشد.');
        BUSY = false;
        return;
      }
      if (pass.length < 8) {
        showResetError('رمز جدید باید حداقل ۸ کاراکتر باشد.');
        BUSY = false;
        return;
      }
      if (pass !== pass2) {
        showResetError('تکرار رمز جدید یکسان نیست.');
        BUSY = false;
        return;
      }
      try {
        await global.DHAuth.resetPassword(challengeId, code, pass);
        renderResetSuccess();
      } catch (e) {
        showResetError(e && e.message ? e.message : 'تغییر رمز انجام نشد.');
      } finally {
        BUSY = false;
      }
    };
  }

  function renderResetSuccess() {
    var modal = document.querySelector('.dh-commercial-modal');
    if (!modal) return;
    modal.innerHTML =
      '<h2 class="dh-commercial-title">رمز عبور تغییر کرد</h2>' +
      '<p class="dh-commercial-sub">رمز عبور شما با موفقیت تغییر کرد و نشست‌های قبلی از اعتبار افتادند.</p>' +
      '<div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-reset-done">ادامه</button></div>';
    el('dh-reset-done').onclick = closeOverlay;
  }

  function injectForgotLink() {
    var modal = document.querySelector('.dh-commercial-modal');
    var switchBtn = el('dh-c-switch');
    if (!modal || !switchBtn || el('dh-forgot-password')) return;
    var wrap = document.createElement('div');
    wrap.id = 'dh-forgot-password-wrap';
    wrap.style.textAlign = 'center';
    wrap.style.marginTop = '8px';
    wrap.innerHTML = '<button type="button" class="dh-commercial-link" id="dh-forgot-password">فراموشی رمز عبور</button>';
    switchBtn.parentNode.insertBefore(wrap, switchBtn.parentNode.firstChild);
    el('dh-forgot-password').onclick = renderResetRequest;
  }

  function install() {
    if (!global.DHCommercialUI || typeof global.DHCommercialUI.showAuth !== 'function') return;
    if (global.DHCommercialUI.__passwordResetInstalled) return;
    originalShowAuth = global.DHCommercialUI.showAuth;
    global.DHCommercialUI.showAuth = function (mode) {
      var result = originalShowAuth(mode);
      if (mode === 'login') {
        Promise.resolve().then(injectForgotLink);
      }
      return result;
    };
    global.DHCommercialUI.__passwordResetInstalled = true;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  } else {
    install();
  }
})(window);
