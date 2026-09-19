/* admin_feedback_ui_v1.js — admin grant + feedback tools independent of commercial_ui boot */
(function (global) {
  'use strict';

  var INSTALLED = false;
  var REFRESH_TIMER = null;

  function el(id) { return document.getElementById(id); }
  function text(v) { return String(v == null ? '' : v); }

  function isAdminUser() {
    try {
      if (global.DHAuth && typeof global.DHAuth.isAdmin === 'function' && global.DHAuth.isAdmin()) return true;
      var u = global.DHAuth && typeof global.DHAuth.getUser === 'function' ? global.DHAuth.getUser() : null;
      return !!(u && (u.role === 'admin' || u.role === 'support' || u.is_admin === true));
    } catch (_) {
      return false;
    }
  }

  function mount() {
    if (!isAdminUser()) return;
    if (el('dh-admin-feedback')) return;

    var adminPanel = el('dh-admin-panel');
    if (!adminPanel || !adminPanel.parentNode) return;

    var box = document.createElement('section');
    box.id = 'dh-admin-feedback';
    box.setAttribute('dir', 'rtl');
    box.style.cssText =
      'margin:14px 0 0;padding:14px;border-radius:14px;' +
      'border:1px solid rgba(212,175,55,.3);background:#12121c;text-align:right;';

    box.innerHTML =
      '<h4 style="color:#f0c040;font-weight:800;margin:0 0 12px;">پنل ادمین · بازخورد و اعتبار</h4>' +
      '<div style="padding:12px;border:1px solid rgba(212,175,55,.24);border-radius:12px;background:#0f0f18;margin-bottom:12px;">' +
        '<div style="color:#f0c040;font-weight:800;margin-bottom:8px;">اعطای اعتبار</div>' +
        '<label for="dh-admin-grant-user-id" style="display:block;color:#cbb98a;font-size:.8rem;margin:7px 2px 4px;">شناسه عددی کاربر</label>' +
        '<input id="dh-admin-grant-user-id" type="number" min="1" step="1" inputmode="numeric" autocomplete="off" placeholder="مثلاً 123" style="width:100%;box-sizing:border-box;padding:11px 12px;border-radius:10px;border:1px solid #333;background:#0b0b12;color:#eee;font:inherit;">' +
        '<label for="dh-admin-grant-plan" style="display:block;color:#cbb98a;font-size:.8rem;margin:9px 2px 4px;">plan_code</label>' +
        '<input id="dh-admin-grant-plan" value="pack_3_tests" maxlength="64" autocomplete="off" style="width:100%;box-sizing:border-box;padding:11px 12px;border-radius:10px;border:1px solid #333;background:#0b0b12;color:#eee;font:inherit;direction:ltr;text-align:left;">' +
        '<label for="dh-admin-grant-reason" style="display:block;color:#cbb98a;font-size:.8rem;margin:9px 2px 4px;">دلیل</label>' +
        '<input id="dh-admin-grant-reason" value="هدیه مالک" maxlength="1000" autocomplete="off" style="width:100%;box-sizing:border-box;padding:11px 12px;border-radius:10px;border:1px solid #333;background:#0b0b12;color:#eee;font:inherit;">' +
        '<div id="dh-admin-grant-msg" style="min-height:1.5em;margin-top:8px;font-size:.82rem;line-height:1.7;"></div>' +
        '<button type="button" class="btn btn-primary" id="dh-admin-grant" style="width:100%;margin-top:8px;">اعطا</button>' +
      '</div>' +
      '<div id="dh-admin-feedback-dash" style="color:#b7ad98;font-size:.84rem;line-height:1.8;margin-bottom:8px;">در حال بارگذاری…</div>' +
      '<div id="dh-admin-feedback-list" style="max-height:320px;overflow:auto;font-size:.8rem;color:#d7caa9;line-height:1.7;"></div>' +
      '<button type="button" class="btn" id="dh-admin-refresh" style="width:100%;margin-top:10px;">بروزرسانی بازخوردها</button>';

    adminPanel.parentNode.insertBefore(box, adminPanel.nextSibling);

    var grant = el('dh-admin-grant');
    if (grant) {
      grant.onclick = async function () {
        if (global.__dh_admin_grant_loading) return;

        var userInput = el('dh-admin-grant-user-id');
        var planInput = el('dh-admin-grant-plan');
        var reasonInput = el('dh-admin-grant-reason');
        var msg = el('dh-admin-grant-msg');
        var userId = Number((userInput && userInput.value) || 0);
        var plan = text((planInput && planInput.value) || '').trim() || 'pack_3_tests';
        var reason = text((reasonInput && reasonInput.value) || '').trim() || 'هدیه مالک';

        if (!Number.isInteger(userId) || userId <= 0) {
          if (msg) { msg.style.color = '#ff8787'; msg.textContent = 'شناسه کاربر باید یک عدد صحیح مثبت باشد.'; }
          if (userInput) userInput.focus();
          return;
        }

        global.__dh_admin_grant_loading = true;
        if (msg) { msg.style.color = '#b7ad98'; msg.textContent = ''; }
        grant.disabled = true;
        grant.textContent = 'در حال اعطا…';

        try {
          if (!global.DHAuth || typeof global.DHAuth.adminGrantCredits !== 'function') {
            throw new Error('کلاینت اعطای اعتبار آماده نیست.');
          }
          var result = await global.DHAuth.adminGrantCredits(userId, plan, reason);
          var granted = Number(result && result.credits_granted || 0);
          var target = Number(result && result.user_id || userId);
          if (msg) {
            msg.style.color = '#9fe3a2';
            msg.textContent = granted > 0
              ? granted + ' اعتبار به کاربر ' + target + ' اضافه شد.'
              : 'اعطای اعتبار با موفقیت ثبت شد.';
          }
          await loadFeedback();
        } catch (e) {
          if (msg) {
            msg.style.color = '#ff8787';
            msg.textContent = text(e && e.message ? e.message : e) || 'اعطای اعتبار ناموفق بود.';
          }
        } finally {
          global.__dh_admin_grant_loading = false;
          grant.disabled = false;
          grant.textContent = 'اعطا';
        }
      };
    }

    var refresh = el('dh-admin-refresh');
    if (refresh) refresh.onclick = function () { loadFeedback(); };
    loadFeedback();
  }

  async function loadFeedback() {
    if (!isAdminUser()) return;
    if (!global.DHAuth || typeof global.DHAuth.adminDashboard !== 'function' ||
        typeof global.DHAuth.adminFeedback !== 'function') {
      var dashMissing = el('dh-admin-feedback-dash');
      if (dashMissing) dashMissing.textContent = 'کلاینت ادمین آماده نیست.';
      return;
    }

    var dash = el('dh-admin-feedback-dash');
    var list = el('dh-admin-feedback-list');

    try {
      var d = await global.DHAuth.adminDashboard();
      if (dash) {
        dash.textContent =
          'کاربران: ' + (d && d.users_total || 0) +
          ' · بازخورد: ' + (d && d.feedback_total || 0) +
          ' · پرداخت موفق: ' + (d && d.payments_verified != null ? d.payments_verified : '—') +
          ' · اعتبارها: ' + (d && d.entitlements_total || 0);
      }

      var rows = await global.DHAuth.adminFeedback(40);
      if (!list) return;

      if (!Array.isArray(rows) || !rows.length) {
        list.textContent = 'هنوز بازخوردی ثبت نشده است.';
        return;
      }

      list.innerHTML = rows.map(function (r) {
        var title = r && (r.suggested_major || r.exam_code || ('#' + r.id)) || 'بازخورد';
        var scores =
          'رضایت: ' + (r && r.satisfaction_score != null ? r.satisfaction_score : '—') +
          ' · دقت: ' + (r && r.accuracy_rating != null ? r.accuracy_rating : '—') +
          ' · توصیه: ' + (r && r.would_recommend ? 'بله' : 'خیر');
        var comment = text(r && r.comments || '').replace(/\s*\|?\s*payload=.*$/, '').trim();
        var when = text(r && r.created_at || '').slice(0, 19).replace('T', ' ');
        return '<div style="border-top:1px solid rgba(255,255,255,.08);padding:9px 0;">' +
          '<div style="color:#f0c040;font-weight:700;">' + text(title).replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>' +
          '<div>' + text(scores).replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>' +
          '<div style="color:#8f845f;font-size:.74rem;">' + text(when).replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>' +
          (comment ? '<div style="margin-top:4px;color:#cbb98a;">' + text(comment.slice(0, 220)).replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>' : '') +
          '</div>';
      }).join('');
    } catch (e) {
      if (dash) dash.textContent = text(e && e.message ? e.message : e) || 'خطا در بارگذاری پنل ادمین.';
      if (list) list.textContent = '';
    }
  }

  function boot() {
    if (INSTALLED) return;
    INSTALLED = true;

    var attempts = 0;
    function tick() {
      mount();
      attempts += 1;
      if (attempts < 30) REFRESH_TIMER = setTimeout(tick, 250);
      else REFRESH_TIMER = null;
    }
    tick();

    if (typeof MutationObserver !== 'undefined' && document.body) {
      new MutationObserver(function () {
        if (!el('dh-admin-feedback')) mount();
      }).observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})(window);
