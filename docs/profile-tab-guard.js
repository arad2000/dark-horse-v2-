/* Dark Horse Profile v2 — isolated tab renderer.
 * The Profile tab must not call the legacy shell renderer because that path
 * rewrites the tabbar/app root synchronously and can collide with async boot.
 * This handler owns only the Profile click and renders a small, deterministic
 * view directly into #app. Navigation away returns control to the shell.
 */
(function () {
  'use strict';

  if (window.__dhProfileIsolatedV2) return;
  window.__dhProfileIsolatedV2 = true;

  var USER_KEY = 'dh_local_user_v1';
  var QUOTA_KEY = 'dh_local_quota_v1';
  var RESULT_KEY = 'dh_last_result_v1';

  function $(id) { return document.getElementById(id); }
  function readJson(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback)); }
    catch (e) { return fallback; }
  }
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function user() {
    try {
      if (window.DHAuth && typeof DHAuth.isLoggedIn === 'function' && DHAuth.isLoggedIn()) {
        return DHAuth.getUser() || null;
      }
    } catch (e) {}
    return readJson(USER_KEY, null);
  }
  function quota() {
    var q = readJson(QUOTA_KEY, { used: 0, premium: false });
    return q && typeof q === 'object' ? q : { used: 0, premium: false };
  }
  function lastResult() {
    var r = readJson(RESULT_KEY, null);
    return r && typeof r === 'object' ? r : null;
  }
  function setProfileState(on) {
    window.__dhProfileVisible = !!on;
    window.__dhInJourney = !!on;
  }
  function restoreHome() {
    setProfileState(false);
    try {
      if (window.DHShell && typeof window.DHShell.renderHome === 'function') {
        window.DHShell.renderHome();
        return;
      }
    } catch (e) {}
    if (typeof window.render === 'function') {
      try { window.render(); } catch (e2) {}
    }
  }
  function startJourney() {
    setProfileState(false);
    try {
      if (window.DHShell && typeof window.DHShell.startJourney === 'function') {
        window.DHShell.startJourney();
        return;
      }
    } catch (e) {}
    restoreHome();
  }
  function renderProfile() {
    var root = $('app');
    if (!root) return;
    setProfileState(true);

    var u = user();
    var q = quota();
    var last = lastResult();
    var premium = !!(u && u.is_premium) || !!q.premium;
    var remain = premium ? '∞' : ((q.used || 0) < 1 ? '1' : '0');
    var name = (u && u.name ? String(u.name).trim() : 'مسافر');
    var phone = u && u.phone ? String(u.phone) : '';
    var initial = esc(name.charAt(0) || '؟');

    var lastHtml = '<div class="dh-last-card dh-last-empty">' +
      '<div class="dh-last-title">هنوز سفری تمام نشده</div>' +
      '<p style="margin:8px 0 0;color:#8a7a55;font-size:.88rem;line-height:1.7;">یک‌بار سفر اکتشافی را تا نتیجه برو؛ خلاصه اینجا می‌ماند.</p>' +
      '</div>';
    if (last && Array.isArray(last.tops) && last.tops.length) {
      var rows = last.tops.slice(0, 5).map(function (t, i) {
        var score = Number(t && t.score || 0);
        if (score <= 1) score = Math.round(score * 1000) / 10;
        else score = Math.round(score * 10) / 10;
        return '<div class="dh-last-row"><span class="dh-last-rank">' + (i + 1) + '</span>' +
          '<span class="dh-last-name">' + esc(t && t.name || '—') + '</span>' +
          '<span class="dh-last-score">' + esc(String(score)) + '٪</span></div>';
      }).join('');
      lastHtml = '<div class="dh-last-card"><div class="dh-last-title">آخرین کشف تو</div>' + rows + '</div>';
    }

    root.innerHTML =
      '<div class="dh-home-wrap">' +
        '<div class="card" style="text-align:right;margin-top:4px;padding-bottom:18px;">' +
          '<div class="dh-profile-avatar">' + initial + '</div>' +
          '<h2 class="dh-prof-display-name">' + esc(name) + '</h2>' +
          (phone ? '<p style="text-align:center;color:#8a7a55;margin:6px 0 0;font-size:.9rem;">' + esc(phone) + '</p>' : '') +
          '<div class="dh-stat-grid">' +
            '<div class="dh-stat"><div class="n">' + esc(String(remain)) + '</div><div class="l">اکتشاف باقی</div></div>' +
            '<div class="dh-stat"><div class="n">' + (premium ? '✓' : String(q.used || 0)) + '</div><div class="l">' + (premium ? 'اشتراک' : 'مصرف‌شده') + '</div></div>' +
          '</div>' +
          lastHtml +
          '<button type="button" class="btn btn-primary" style="width:100%;margin-top:14px;" id="dh-p-journey-v2">' +
            (last && last.tops && last.tops.length ? 'سفر دوباره' : 'شروع اولین سفر') + '</button>' +
          '<button type="button" class="btn" style="width:100%;margin-top:8px;" id="dh-p-home-v2">خانه</button>' +
        '</div>' +
      '</div>';

    var j = $('dh-p-journey-v2'); if (j) j.onclick = startJourney;
    var h = $('dh-p-home-v2'); if (h) h.onclick = restoreHome;
  }

  document.addEventListener('click', function (event) {
    var target = event.target;
    var button = target && target.closest ? target.closest('#dh-tabbar button[data-tab="profile"]') : null;
    if (!button) return;

    event.preventDefault();
    if (event.stopImmediatePropagation) event.stopImmediatePropagation();
    else if (event.stopPropagation) event.stopPropagation();

    renderProfile();
  }, true);

  document.addEventListener('click', function (event) {
    var target = event.target;
    var button = target && target.closest ? target.closest('#dh-tabbar button[data-tab="home"], #dh-tabbar button[data-tab="journey"]') : null;
    if (button) {
      setProfileState(false);
    }
  }, true);
})();