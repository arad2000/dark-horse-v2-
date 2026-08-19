/**
 * shell.js — پوسته اپ (خانه / سفر / پروفایل) + جمله روز
 * بعد از app.js لود شود. نسخه پایدار در برابر کش و race با init
 */
(function () {
  'use strict';

  const TAB_KEY = 'dh_shell_tab';
  const LOCAL_USER_KEY = 'dh_local_user_v1';
  const LOCAL_QUOTA_KEY = 'dh_local_quota_v1';

  window.__dhInJourney = false;

  function $(id) { return document.getElementById(id); }

  function localUser() {
    try { return JSON.parse(localStorage.getItem(LOCAL_USER_KEY) || 'null'); } catch (e) { return null; }
  }
  function saveLocalUser(u) { localStorage.setItem(LOCAL_USER_KEY, JSON.stringify(u)); }
  function localQuota() {
    try { return JSON.parse(localStorage.getItem(LOCAL_QUOTA_KEY) || '{"used":0,"premium":false}'); }
    catch (e) { return { used: 0, premium: false }; }
  }
  function saveQuota(q) { localStorage.setItem(LOCAL_QUOTA_KEY, JSON.stringify(q)); }

  function getDisplayUser() {
    try {
      if (window.DHAuth && DHAuth.isLoggedIn && DHAuth.isLoggedIn()) return DHAuth.getUser();
    } catch (e) {}
    return localUser();
  }

  function canRunTest() {
    const u = getDisplayUser();
    if (u && u.is_premium) return true;
    if (u && typeof u.tests_remaining === 'number') return u.tests_remaining > 0;
    const q = localQuota();
    if (q.premium) return true;
    return (q.used || 0) < 1;
  }

  function escape(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function ensureTabbar() {
    if ($('dh-tabbar')) return;
    const nav = document.createElement('nav');
    nav.id = 'dh-tabbar';
    nav.innerHTML =
      '<button type="button" data-tab="home"><span class="ico">🏠</span><span>خانه</span></button>' +
      '<button type="button" data-tab="journey"><span class="ico">🗺️</span><span>سفر</span></button>' +
      '<button type="button" data-tab="profile"><span class="ico">👤</span><span>پروفایل</span></button>';
    nav.addEventListener('click', function (e) {
      const btn = e.target.closest('button[data-tab]');
      if (!btn) return;
      switchTab(btn.getAttribute('data-tab'));
    });
    document.body.appendChild(nav);
  }

  function setActiveTab(tab) {
    document.querySelectorAll('#dh-tabbar button').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-tab') === tab);
    });
    try { localStorage.setItem(TAB_KEY, tab); } catch (e) {}
  }

  function renderHome() {
    ensureTabbar();
    setActiveTab('home');
    window.__dhInJourney = false;

    var bundle = [];
    try {
      if (window.DHQuote && DHQuote.todayBundle) bundle = DHQuote.todayBundle();
    } catch (e) {}
    if (!bundle.length && window.DH_QUOTES && DH_QUOTES.length) {
      bundle = [DH_QUOTES[0], DH_QUOTES[1] || DH_QUOTES[0], DH_QUOTES[2] || DH_QUOTES[0]];
    }

    var lines = bundle.map(function (q) {
      return '<p class="line">' + escape(q.t) + '</p>';
    }).join('');
    var tags = bundle.map(function (q) {
      return '<span class="dh-chip">' + escape(q.tag) + '</span>';
    }).join('');

    var u = getDisplayUser();
    var q = localQuota();
    var quotaText = (u && u.is_premium) || q.premium
      ? 'اشتراک فعال'
      : (canRunTest() ? '۱ تست رایگان باقی است' : 'سهمیه رایگان تمام شده');
    var name = (u && u.name) ? u.name : 'مسافر';

    var root = $('app');
    if (!root) return;
    root.innerHTML =
      '<div class="dh-home-wrap">' +
        '<div class="dh-home-header">' +
          '<div><h1>اسب سیاه</h1><p class="dh-home-sub">سلام ' + escape(name) + '</p></div>' +
          '<span class="dh-chip">' + escape(quotaText) + '</span>' +
        '</div>' +
        '<div class="dh-quote-card">' +
          '<div class="label">✦ جملهٔ امروز — با الهام از روح کتاب اسب سیاه</div>' +
          lines +
          '<div class="foot">بازنویسی آزاد برای اپ · تاد رز و اگی اوگاس · پروژه هاروارد</div>' +
          '<div class="dh-chip-row">' + tags + '</div>' +
        '</div>' +
        '<div class="dh-action-card">' +
          '<p style="margin:0 0 12px;color:#cbb98a;line-height:1.8;font-size:0.95rem;">آماده‌ای جرقه‌های واقعی خودت را پیدا کنی؟</p>' +
          '<button class="btn btn-primary" style="width:100%;" id="dh-start-journey">شروع / ادامه سفر اکتشافی</button>' +
          '<button class="btn" style="width:100%;margin-top:8px;" id="dh-to-profile">پروفایل و اشتراک</button>' +
          '<button class="btn" style="width:100%;margin-top:8px;border-color:#d4af37;color:#f0c040;" id="dh-install-home">⬇ نصب اپ روی گوشی</button>' +
        '</div>' +
      '</div>';

    var b1 = $('dh-start-journey');
    var b2 = $('dh-to-profile');
    if (b1) b1.onclick = function () { startJourneyFromShell(); };
    if (b2) b2.onclick = function () { switchTab('profile'); };
    var b3 = $('dh-install-home');
    if (b3) b3.onclick = function () {
      if (window.DHInstall) DHInstall.show();
      else alert('از منوی مرورگر گزینه Install / افزودن به صفحه اصلی را بزن');
    };
  }

  function startJourneyFromShell() {
    if (!canRunTest()) {
      switchTab('profile');
      setTimeout(function () {
        alert('سهمیه رایگان تمام شده. از پروفایل اشتراک را فعال کن.');
      }, 150);
      return;
    }
    window.__dhInJourney = true;
    setActiveTab('journey');
    try {
      if (typeof state !== 'undefined') {
        if (window.__dhHasSavedSession && !window.__dhJourneyFinished) {
          state.stage = 'splash';
        } else {
          state.stage = 'manifesto';
        }
        state.history = [];
      }
      if (typeof render === 'function') render();
    } catch (e) {
      console.error(e);
      alert('خطا در شروع سفر');
    }
  }

  function renderProfile() {
    ensureTabbar();
    setActiveTab('profile');
    window.__dhInJourney = false;
    var root = $('app');
    if (!root) return;
    var u = getDisplayUser();
    var q = localQuota();

    if (!u) {
      root.innerHTML =
        '<div class="card" style="text-align:right;margin-top:8px;">' +
        '<h2 style="text-align:center;color:#f0c040;">پروفایل</h2>' +
        '<p style="color:#b0a080;line-height:1.9;">برای مدیریت تست رایگان، نام و موبایل را وارد کن.</p>' +
        '<label style="display:block;margin:8px 0 4px;">نام</label>' +
        '<input id="dh-p-name" placeholder="مثلاً سارا" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">' +
        '<label style="display:block;margin:8px 0 4px;">موبایل</label>' +
        '<input id="dh-p-phone" inputmode="numeric" placeholder="09xxxxxxxxx" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">' +
        '<p id="dh-p-err" style="color:#f66;min-height:1.2em;font-size:0.85rem;"></p>' +
        '<button class="btn btn-primary" style="width:100%;" id="dh-p-save">ثبت و ورود</button>' +
        '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">بازگشت خانه</button>' +
        '</div>';
      $('dh-p-home').onclick = function () { switchTab('home'); };
      $('dh-p-save').onclick = function () {
        var name = (($('dh-p-name') || {}).value || '').trim();
        var phone = (($('dh-p-phone') || {}).value || '').trim();
        var err = $('dh-p-err');
        if (err) err.textContent = '';
        if (name.length < 2) { if (err) err.textContent = 'نام را وارد کن'; return; }
        if (!/^09\d{9}$/.test(phone)) { if (err) err.textContent = 'موبایل را درست وارد کن'; return; }
        saveLocalUser({ name: name, phone: phone, is_premium: false });
        renderProfile();
      };
      return;
    }

    var initial = (u.name || '؟').trim().charAt(0);
    var premium = !!(u.is_premium || q.premium);
    var remain = premium ? '∞' : (canRunTest() ? '1' : '0');

    root.innerHTML =
      '<div class="card" style="text-align:right;margin-top:8px;">' +
      '<div class="dh-profile-avatar">' + escape(initial) + '</div>' +
      '<h2 style="text-align:center;margin:0;color:#f0c040;">' + escape(u.name) + '</h2>' +
      '<p style="text-align:center;color:#8a7a55;margin:6px 0 0;">' + escape(u.phone || '') + '</p>' +
      '<div class="dh-stat-grid">' +
        '<div class="dh-stat"><div class="n">' + escape(String(remain)) + '</div><div class="l">تست باقی‌مانده</div></div>' +
        '<div class="dh-stat"><div class="n">' + (premium ? '✓' : '—') + '</div><div class="l">اشتراک</div></div>' +
      '</div>' +
      '<button class="btn btn-primary" style="width:100%;" id="dh-p-prem">' + (premium ? 'اشتراک فعال است' : 'فعال‌سازی اشتراک (تستی)') + '</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-journey">رفتن به سفر</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-out">خروج</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">خانه</button>' +
      '</div>';

    $('dh-p-home').onclick = function () { switchTab('home'); };
    $('dh-p-journey').onclick = function () { startJourneyFromShell(); };
    $('dh-p-out').onclick = function () {
      try { if (window.DHAuth && DHAuth.logout) DHAuth.logout(); } catch (e) {}
      localStorage.removeItem(LOCAL_USER_KEY);
      renderProfile();
    };
    $('dh-p-prem').onclick = function () {
      if (premium) return;
      var qq = localQuota();
      qq.premium = true;
      saveQuota(qq);
      var lu = localUser();
      if (lu) { lu.is_premium = true; saveLocalUser(lu); }
      alert('اشتراک تستی فعال شد');
      renderProfile();
    };
  }

  function switchTab(tab) {
    if (tab === 'home') renderHome();
    else if (tab === 'profile') renderProfile();
    else if (tab === 'journey') startJourneyFromShell();
  }

  function patchRender() {
    if (typeof window.render !== 'function' || window.__dhShellRenderPatched) return;
    var _render = window.render;
    window.render = function () {
      // اگر کاربر عمداً در سفر نیست و مرحله اول است → خانه
      if (!window.__dhInJourney && typeof state !== 'undefined') {
        var st = state.stage;
        if (!st || st === 'manifesto' || st === 'guide') {
          renderHome();
          return;
        }
      }
      _render();
    };
    window.__dhShellRenderPatched = true;
  }

  function patchConsumeOnResults() {
    if (typeof window.displayResults !== 'function' || window.__dh_shell_quota_patched) return;
    var orig = window.displayResults;
    window.displayResults = function (data, type) {
      orig(data, type);
      try {
        var q = localQuota();
        if (!q.premium && (q.used || 0) < 1) {
          q.used = (q.used || 0) + 1;
          saveQuota(q);
        }
      } catch (e) {}
    };
    window.__dh_shell_quota_patched = true;
  }

  function boot() {
    ensureTabbar();
    patchRender();
    patchConsumeOnResults();
    renderHome();
    // چند بار تکرار تا init دیرهنگام manifesto را نیاورد
    setTimeout(function () {
      if (!window.__dhInJourney) renderHome();
    }, 100);
    setTimeout(function () {
      if (!window.__dhInJourney) renderHome();
    }, 400);
    setTimeout(function () {
      if (!window.__dhInJourney) renderHome();
    }, 1200);
  }

  window.DHShell = {
    switchTab: switchTab,
    renderHome: renderHome,
    renderProfile: renderProfile,
    startJourney: startJourneyFromShell
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  // اگر اسکریپت بعد از DOM لود شد
  setTimeout(boot, 0);
})();
