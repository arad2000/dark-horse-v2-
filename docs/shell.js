/**
 * shell.js v2 — خانه زنده‌تر + پروفایل + تب‌ها
 */
(function () {
  'use strict';

  var LOCAL_USER_KEY = 'dh_local_user_v1';
  var LOCAL_QUOTA_KEY = 'dh_local_quota_v1';
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
    var u = getDisplayUser();
    if (u && u.is_premium) return true;
    var q = localQuota();
    if (q.premium) return true;
    return (q.used || 0) < 1;
  }

  function escape(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function greeting() {
    var h = new Date().getHours();
    if (h < 12) return 'صبح بخیر';
    if (h < 17) return 'روز بخیر';
    if (h < 21) return 'عصر بخیر';
    return 'شب خوش';
  }

  function faDate() {
    try {
      return new Date().toLocaleDateString('fa-IR', { weekday: 'long', day: 'numeric', month: 'long' });
    } catch (e) {
      return '';
    }
  }

  function ensureTabbar() {
    if ($('dh-tabbar')) return;
    var nav = document.createElement('nav');
    nav.id = 'dh-tabbar';
    nav.innerHTML =
      '<button type="button" data-tab="home"><span class="ico">🏠</span><span>خانه</span></button>' +
      '<button type="button" data-tab="journey"><span class="ico">🗺️</span><span>سفر</span></button>' +
      '<button type="button" data-tab="profile"><span class="ico">👤</span><span>پروفایل</span></button>';
    nav.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-tab]');
      if (!btn) return;
      switchTab(btn.getAttribute('data-tab'));
    });
    document.body.appendChild(nav);
  }

  function setActiveTab(tab) {
    document.querySelectorAll('#dh-tabbar button').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-tab') === tab);
    });
  }

  function getBundle() {
    var bundle = [];
    try {
      if (window.DHQuote && DHQuote.todayBundle) bundle = DHQuote.todayBundle();
    } catch (e) {}
    if (!bundle.length && window.DH_QUOTES && DH_QUOTES.length) {
      var i = new Date().getDate() % DH_QUOTES.length;
      bundle = [DH_QUOTES[i], DH_QUOTES[(i + 1) % DH_QUOTES.length], DH_QUOTES[(i + 2) % DH_QUOTES.length]];
    }
    return bundle;
  }

  function renderHome() {
    ensureTabbar();
    setActiveTab('home');
    window.__dhInJourney = false;

    var bundle = getBundle();
    var u = getDisplayUser();
    var q = localQuota();
    var name = (u && u.name) ? u.name : 'مسافر';
    var premium = !!(u && u.is_premium) || q.premium;
    var quotaText = premium ? 'اشتراک فعال' : (canRunTest() ? '۱ اکتشاف رایگان' : 'سهمیه تمام');
    var installed = (window.DHInstall && DHInstall.isStandalone && DHInstall.isStandalone()) || window.__dhIsInstalled;

    var lines = bundle.map(function (item, idx) {
      return '<div class="dh-q-line dh-fade-in" style="animation-delay:' + (idx * 0.12) + 's">' +
        '<span class="dh-q-num">' + (idx + 1) + '</span>' +
        '<p>' + escape(item.t) + '</p>' +
        '<span class="dh-q-tag">' + escape(item.tag) + '</span>' +
        '</div>';
    }).join('');

    var root = $('app');
    if (!root) return;

    root.innerHTML =
      '<div class="dh-home-wrap">' +
        '<div class="dh-home-top">' +
          '<div>' +
            '<p class="dh-greet">' + greeting() + '، <b>' + escape(name) + '</b></p>' +
            '<p class="dh-date">' + escape(faDate()) + '</p>' +
          '</div>' +
          '<span class="dh-chip">' + escape(quotaText) + '</span>' +
        '</div>' +

        '<div class="dh-quote-hero">' +
          '<div class="dh-quote-label">✦ پیام‌های امروز</div>' +
          '<div class="dh-quote-sub">با الهام از روح کتاب اسب سیاه · هر روز تازه</div>' +
          lines +
          '<div class="dh-quote-foot">تاد رز و اگی اوگاس · بازنویسی برای اپ</div>' +
        '</div>' +

        '<div class="dh-cta-card">' +
          '<p class="dh-cta-title">سفر اکتشافی</p>' +
          '<p class="dh-cta-desc">جرقه‌هایت را پیدا کن؛ مسیر را با معیار خودت ببین.</p>' +
          '<button class="btn btn-primary dh-cta-main" id="dh-start-journey">شروع سفر</button>' +
          (installed ? '' :
            '<button class="btn dh-cta-sec" id="dh-install-home"><span style="margin-left:6px">⬇️</span>نصب اپ روی گوشی</button>') +
        '</div>' +

        '<div class="dh-mini-grid">' +
          '<button type="button" class="dh-mini" id="dh-mini-quote"><span>✨</span>پیام دیگر</button>' +
          '<button type="button" class="dh-mini" id="dh-mini-install"><span>⬇️</span>نصب اپ</button>' +
        '</div>' +
      '</div>';

    $('dh-start-journey').onclick = function () { startJourneyFromShell(); };
    var inst = $('dh-install-home');
    if (inst) inst.onclick = function () {
      if (window.DHInstall) DHInstall.show();
      else alert('از منوی مرورگر Install را بزن');
    };
    $('dh-mini-quote').onclick = function () { shuffleExtraQuote(); };
    var miniInst = $('dh-mini-install');
    if (miniInst) {
      if ((window.DHInstall && DHInstall.isStandalone && DHInstall.isStandalone()) || window.__dhIsInstalled) {
        miniInst.style.display = 'none';
      } else {
        miniInst.onclick = function () {
          if (window.DHInstall) DHInstall.show();
          else alert('از منوی مرورگر گزینه Install / افزودن به صفحه اصلی را بزن.');
        };
      }
    }
  }

  function shuffleExtraQuote() {
    if (!window.DH_QUOTES || !DH_QUOTES.length) return;
    var q = DH_QUOTES[Math.floor(Math.random() * DH_QUOTES.length)];
    var hero = document.querySelector('.dh-quote-hero');
    if (!hero) return;
    var note = document.getElementById('dh-extra-q');
    if (!note) {
      note = document.createElement('div');
      note.id = 'dh-extra-q';
      note.className = 'dh-q-line dh-fade-in';
      hero.appendChild(note);
    }
    note.innerHTML = '<span class="dh-q-num">+</span><p>' + escape(q.t) + '</p><span class="dh-q-tag">' + escape(q.tag) + '</span>';
  }

  function startJourneyFromShell() {
    if (!canRunTest()) {
      switchTab('profile');
      setTimeout(function () { alert('سهمیه رایگان تمام شده. از پروفایل اشتراک تستی را فعال کن.'); }, 150);
      return;
    }
    window.__dhInJourney = true;
    setActiveTab('journey');
    try {
      if (typeof state !== 'undefined') {
        if (window.__dhHasSavedSession && !window.__dhJourneyFinished) state.stage = 'splash';
        else state.stage = 'manifesto';
        state.history = [];
      }
      if (typeof render === 'function') render();
    } catch (e) {
      console.error(e);
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
        '<h2 style="text-align:center;color:#f0c040;">ورود به حساب</h2>' +
        '<p style="color:#b0a080;line-height:1.9;">نام و موبایل برای ذخیره مسیر و سهمیه.</p>' +
        '<label style="display:block;margin:8px 0 4px;">نام</label>' +
        '<input id="dh-p-name" placeholder="مثلاً سارا" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">' +
        '<label style="display:block;margin:8px 0 4px;">موبایل</label>' +
        '<input id="dh-p-phone" inputmode="numeric" placeholder="09xxxxxxxxx" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">' +
        '<p id="dh-p-err" style="color:#f66;min-height:1.2em;font-size:0.85rem;"></p>' +
        '<button class="btn btn-primary" style="width:100%;" id="dh-p-save">ادامه</button>' +
        '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">خانه</button>' +
        '</div>';
      $('dh-p-home').onclick = function () { switchTab('home'); };
      $('dh-p-save').onclick = function () {
        var name = (($('dh-p-name') || {}).value || '').trim();
        var phone = (($('dh-p-phone') || {}).value || '').trim();
        var err = $('dh-p-err');
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
        '<div class="dh-stat"><div class="n">' + escape(String(remain)) + '</div><div class="l">اکتشاف باقی</div></div>' +
        '<div class="dh-stat"><div class="n">' + (premium ? '✓' : '—') + '</div><div class="l">اشتراک</div></div>' +
      '</div>' +
      '<button class="btn btn-primary" style="width:100%;" id="dh-p-prem">' + (premium ? 'اشتراک فعال' : 'فعال‌سازی اشتراک (تستی)') + '</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-journey">رفتن به سفر</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-out">خروج</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">خانه</button>' +
      '</div>';

    $('dh-p-home').onclick = function () { switchTab('home'); };
    $('dh-p-journey').onclick = function () { startJourneyFromShell(); };
    $('dh-p-out').onclick = function () {
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
    setTimeout(function () { if (!window.__dhInJourney) renderHome(); }, 150);
    setTimeout(function () { if (!window.__dhInJourney) renderHome(); }, 600);
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
  setTimeout(boot, 0);
})();
