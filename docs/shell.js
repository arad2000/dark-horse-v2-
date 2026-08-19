/**
 * shell.js — پوسته اپ (خانه / سفر / پروفایل) + جمله روز
 * بعد از app.js لود شود.
 */
(function () {
  'use strict';

  const TAB_KEY = 'dh_shell_tab';
  const LOCAL_USER_KEY = 'dh_local_user_v1';
  const LOCAL_QUOTA_KEY = 'dh_local_quota_v1';

  function $(id) { return document.getElementById(id); }

  function localUser() {
    try { return JSON.parse(localStorage.getItem(LOCAL_USER_KEY) || 'null'); } catch { return null; }
  }
  function saveLocalUser(u) {
    localStorage.setItem(LOCAL_USER_KEY, JSON.stringify(u));
  }
  function localQuota() {
    try {
      return JSON.parse(localStorage.getItem(LOCAL_QUOTA_KEY) || '{"used":0,"premium":false}');
    } catch { return { used: 0, premium: false }; }
  }
  function saveQuota(q) {
    localStorage.setItem(LOCAL_QUOTA_KEY, JSON.stringify(q));
  }

  function getDisplayUser() {
    if (window.DHAuth && DHAuth.isLoggedIn && DHAuth.isLoggedIn()) {
      return DHAuth.getUser();
    }
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

  function ensureTabbar() {
    if ($('dh-tabbar')) return;
    const nav = document.createElement('nav');
    nav.id = 'dh-tabbar';
    nav.innerHTML = `
      <button type="button" data-tab="home"><span class="ico">🏠</span><span>خانه</span></button>
      <button type="button" data-tab="journey"><span class="ico">🗺️</span><span>سفر</span></button>
      <button type="button" data-tab="profile"><span class="ico">👤</span><span>پروفایل</span></button>
    `;
    nav.addEventListener('click', function (e) {
      const btn = e.target.closest('button[data-tab]');
      if (!btn) return;
      switchTab(btn.getAttribute('data-tab'));
    });
    document.body.appendChild(nav);
  }

  function setActiveTab(tab) {
    document.querySelectorAll('#dh-tabbar button').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-tab') === tab);
    });
    try { localStorage.setItem(TAB_KEY, tab); } catch (_) {}
  }

  function renderHome() {
    ensureTabbar();
    setActiveTab('home');
    const bundle = (window.DHQuote && DHQuote.todayBundle) ? DHQuote.todayBundle() : [];
    const lines = bundle.map(q => `<p class="line">${escape(q.t)}</p>`).join('');
    const tags = bundle.map(q => `<span class="dh-chip">${escape(q.tag)}</span>`).join('');
    const u = getDisplayUser();
    const q = localQuota();
    const quotaText = (u && u.is_premium) || q.premium
      ? 'اشتراک فعال'
      : (canRunTest() ? '۱ تست رایگان باقی است' : 'سهمیه رایگان تمام شده');

    const name = u && u.name ? u.name : 'مسافر';

    const root = $('app');
    if (!root) return;
    root.innerHTML = `
      <div class="dh-home-wrap">
        <div class="dh-home-header">
          <div>
            <h1>اسب سیاه</h1>
            <p class="dh-home-sub">سلام ${escape(name)}</p>
          </div>
          <span class="dh-chip">${escape(quotaText)}</span>
        </div>

        <div class="dh-quote-card">
          <div class="label">✦ جملهٔ امروز — با الهام از روح کتاب اسب سیاه</div>
          ${lines}
          <div class="foot">بازنویسی آزاد برای اپ · تاد رز و اگی اوگاس · پروژه هاروارد</div>
          <div class="dh-chip-row">${tags}</div>
        </div>

        <div class="dh-action-card">
          <p style="margin:0 0 12px;color:#cbb98a;line-height:1.8;font-size:0.95rem;">
            آماده‌ای جرقه‌های واقعی خودت را پیدا کنی؟
          </p>
          <button class="btn btn-primary" style="width:100%;" id="dh-start-journey">شروع / ادامه سفر اکتشافی</button>
          <button class="btn" style="width:100%;margin-top:8px;" id="dh-to-profile">پروفایل و اشتراک</button>
        </div>

        <div class="dh-action-card" style="opacity:0.95;">
          <p style="margin:0;color:#8a7a55;font-size:0.85rem;line-height:1.7;">
            هر روز این صفحه سه پیام تازه می‌آورد. سفر را از تب «سفر» هم می‌توانی ادامه بدهی.
          </p>
        </div>
      </div>
    `;
    $('dh-start-journey').onclick = function () { startJourneyFromShell(); };
    $('dh-to-profile').onclick = function () { switchTab('profile'); };
  }

  function escape(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function startJourneyFromShell() {
    if (!canRunTest()) {
      switchTab('profile');
      setTimeout(function () {
        alert('سهمیه رایگان تمام شده. از پروفایل، اشتراک را فعال کن (فعلاً حالت تستی).');
      }, 200);
      return;
    }
    setActiveTab('journey');
    // ورود به جریان اصلی اپ
    if (typeof goTo === 'function') {
      if (window.__dhHasSavedSession && !window.__dhJourneyFinished) {
        // ادامه از اسپلش با دکمه ادامه
        if (typeof state !== 'undefined') {
          state.stage = 'splash';
          state.history = [];
        }
        if (typeof render === 'function') render();
      } else {
        if (typeof state !== 'undefined') {
          state.stage = 'manifesto';
          state.history = [];
        }
        if (typeof render === 'function') render();
      }
    }
  }

  function renderProfile() {
    ensureTabbar();
    setActiveTab('profile');
    const root = $('app');
    if (!root) return;

    const u = getDisplayUser();
    const q = localQuota();

    if (!u) {
      root.innerHTML = `
        <div class="card" style="text-align:right;margin-top:8px;">
          <h2 style="text-align:center;color:#f0c040;">پروفایل</h2>
          <p style="color:#b0a080;line-height:1.9;">برای ذخیره نتیجه و مدیریت تست رایگان، یک حساب ساده بساز.</p>
          <label style="display:block;margin:8px 0 4px;">نام</label>
          <input id="dh-p-name" placeholder="مثلاً سارا" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">
          <label style="display:block;margin:8px 0 4px;">موبایل</label>
          <input id="dh-p-phone" inputmode="numeric" placeholder="09xxxxxxxxx" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">
          <p id="dh-p-err" style="color:#f66;min-height:1.2em;font-size:0.85rem;"></p>
          <button class="btn btn-primary" style="width:100%;" id="dh-p-save">ثبت و ورود</button>
          <button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">بازگشت خانه</button>
        </div>`;
      $('dh-p-home').onclick = function () { switchTab('home'); };
      $('dh-p-save').onclick = async function () {
        const name = ($('dh-p-name').value || '').trim();
        const phone = ($('dh-p-phone').value || '').trim();
        const err = $('dh-p-err');
        err.textContent = '';
        if (name.length < 2) { err.textContent = 'نام را وارد کن'; return; }
        if (!/^09\d{9}$/.test(phone)) { err.textContent = 'موبایل را درست وارد کن (09…)'; return; }

        // اگر API آماده بود از سرور؛ وگرنه محلی
        if (window.DHAuth && DHAuth.register) {
          try {
            await DHAuth.register(name, phone, phone.slice(-6) + 'aA1');
            renderProfile();
            return;
          } catch (e) {
            // fallback local
            console.warn('auth api', e);
          }
        }
        saveLocalUser({ name: name, phone: phone, is_premium: false, tests_remaining: canRunTest() ? 1 : 0 });
        renderProfile();
      };
      return;
    }

    const initial = (u.name || '؟').trim().charAt(0);
    const premium = !!(u.is_premium || q.premium);
    const used = u.free_tests_used != null ? u.free_tests_used : (q.used || 0);
    const remain = premium ? '∞' : (canRunTest() ? '1' : '0');

    root.innerHTML = `
      <div class="card" style="text-align:right;margin-top:8px;">
        <div class="dh-profile-avatar">${escape(initial)}</div>
        <h2 style="text-align:center;margin:0;color:#f0c040;">${escape(u.name)}</h2>
        <p style="text-align:center;color:#8a7a55;margin:6px 0 0;">${escape(u.phone || '')}</p>
        <div class="dh-stat-grid">
          <div class="dh-stat"><div class="n">${escape(String(remain))}</div><div class="l">تست باقی‌مانده</div></div>
          <div class="dh-stat"><div class="n">${premium ? '✓' : '—'}</div><div class="l">اشتراک</div></div>
        </div>
        <button class="btn btn-primary" style="width:100%;" id="dh-p-prem">${premium ? 'اشتراک فعال است' : 'فعال‌سازی اشتراک (تستی)'}</button>
        <button class="btn" style="width:100%;margin-top:8px;" id="dh-p-journey">رفتن به سفر</button>
        <button class="btn" style="width:100%;margin-top:8px;" id="dh-p-out">خروج از حساب</button>
        <button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">خانه</button>
      </div>`;

    $('dh-p-home').onclick = function () { switchTab('home'); };
    $('dh-p-journey').onclick = function () { startJourneyFromShell(); };
    $('dh-p-out').onclick = function () {
      if (window.DHAuth && DHAuth.logout) DHAuth.logout();
      localStorage.removeItem(LOCAL_USER_KEY);
      renderProfile();
    };
    $('dh-p-prem').onclick = async function () {
      if (premium) return;
      if (window.DHAuth && DHAuth.devActivatePremium) {
        try {
          await DHAuth.devActivatePremium();
          renderProfile();
          return;
        } catch (e) { console.warn(e); }
      }
      const qq = localQuota();
      qq.premium = true;
      saveQuota(qq);
      const lu = localUser();
      if (lu) { lu.is_premium = true; saveLocalUser(lu); }
      alert('اشتراک تستی فعال شد. بعداً به درگاه واقعی وصل می‌شود.');
      renderProfile();
    };
  }

  function switchTab(tab) {
    if (tab === 'home') renderHome();
    else if (tab === 'profile') renderProfile();
    else if (tab === 'journey') startJourneyFromShell();
  }

  // وقتی سفر تمام شد و نتایج آمد، یک واحد سهمیه محلی کم کن
  function patchConsumeOnResults() {
    if (typeof window.displayResults !== 'function') return;
    if (window.__dh_shell_quota_patched) return;
    const orig = window.displayResults;
    window.displayResults = function (data, type) {
      orig(data, type);
      try {
        const q = localQuota();
        if (!q.premium && (q.used || 0) < 1) {
          q.used = (q.used || 0) + 1;
          saveQuota(q);
        }
        if (window.DHAuth && DHAuth.consumeTest) {
          DHAuth.consumeTest().catch(function () {});
        }
      } catch (_) {}
    };
    window.__dh_shell_quota_patched = true;
  }

  function bootShell() {
    ensureTabbar();
    patchConsumeOnResults();
    // به‌جای مانیفست اول، خانه
    renderHome();
  }

  // بعد از init اپ
  function waitAndBoot() {
    ensureTabbar();
    // init اپ ممکن است manifesto نشان دهد — چند لحظه بعد خانه را جایگزین کن
    const start = Date.now();
    const t = setInterval(function () {
      if (typeof state !== 'undefined' && $('app')) {
        clearInterval(t);
        patchConsumeOnResults();
        // اگر هنوز اول مسیر است، خانه نشان بده
        const st = state.stage;
        if (!st || st === 'manifesto' || st === 'guide' || st === 'splash') {
          renderHome();
        } else {
          setActiveTab('journey');
        }
      } else if (Date.now() - start > 4000) {
        clearInterval(t);
        renderHome();
      }
    }, 50);
  }

  window.DHShell = {
    switchTab: switchTab,
    renderHome: renderHome,
    renderProfile: renderProfile,
    startJourney: startJourneyFromShell
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitAndBoot);
  } else {
    waitAndBoot();
  }
})();
