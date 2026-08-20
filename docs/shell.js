/**
 * shell.js v2 — خانه زنده‌تر + پروفایل + تب‌ها
 */
(function () {
  'use strict';

  var LOCAL_USER_KEY = 'dh_local_user_v1';
  var LOCAL_QUOTA_KEY = 'dh_local_quota_v1';
  var LOCAL_RESULT_KEY = 'dh_last_result_v1';
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


  function loadLastResult() {
    try { return JSON.parse(localStorage.getItem(LOCAL_RESULT_KEY) || 'null'); } catch (e) { return null; }
  }
  function saveLastResult(summary) {
    try { localStorage.setItem(LOCAL_RESULT_KEY, JSON.stringify(summary)); } catch (e) {}
  }
  function extractResultSummary(data, type) {
    var items = [];
    var kind = type || 'majors';
    if (!data) return null;
    if (data.discovery_result && data.discovery_result.recommendations) {
      items = data.discovery_result.recommendations;
      kind = 'majors';
    } else if (data.branch_discovery_result && data.branch_discovery_result.branches) {
      items = data.branch_discovery_result.branches;
      kind = 'branches';
    } else if (data.recommendations) {
      items = data.recommendations;
    } else if (data.recommended_branches) {
      items = data.recommended_branches;
      kind = 'branches';
    }
    var tops = (items || []).slice(0, 5).map(function (it) {
      var fit = it.individuality_fit || it;
      return {
        name: it.major_name_fa || it.branch_name_fa || it.name || '—',
        score: fit.score || fit.fit_score || it.fit_score || 0
      };
    });
    var sparks = 0;
    try {
      if (typeof state !== 'undefined' && state.likedCodes) sparks = state.likedCodes.length;
    } catch (e) {}
    return {
      at: Date.now(),
      kind: kind,
      sparks: sparks,
      tops: tops
    };
  }

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
    // ساعت محلی دستگاه کاربر (ایران معمولاً Asia/Tehran)
    var h = new Date().getHours();
    if (h >= 5 && h < 9) return 'صبح بخیر';
    if (h >= 9 && h < 12) return 'وقت بخیر';
    if (h >= 12 && h < 15) return 'ظهر بخیر';
    if (h >= 15 && h < 19) return 'عصر بخیر';
    return 'شب بخیر';  // ۱۹ تا ۵
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
            '<div class="dh-brand">' +
              '<div class="dh-brand-name">اسب سیاه</div>' +
              '<div class="dh-brand-sub">سامانه کشف فردیت · هدایت تحصیلی و انتخاب رشته</div>' +
            '</div>' +
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
          '<p class="dh-cta-desc">بدون فشار رتبه و حرف دیگران — اول ببین چه چیزی به تو انرژی می‌دهد.</p>' +
          '<button class="btn btn-primary dh-cta-main" id="dh-start-journey">شروع سفر</button>' +
          
        '</div>' +

        '<div class="dh-mini-grid dh-mini-one">' +
          '<button type="button" class="dh-mini" id="dh-mini-quote"><span>✨</span>یک پیام تازه دیگر</button>' +
          '<button type="button" class="dh-mini dh-mini-exit" id="dh-home-exit"><span>⎋</span>خروج از اپ</button>' +
        '</div>' +
      '</div>';

    $('dh-start-journey').onclick = function () { startJourneyFromShell(); };
    $('dh-mini-quote').onclick = function () { shuffleExtraQuote(); };
    var hx = $('dh-home-exit');
    if (hx) hx.onclick = function () { exitApp(); };
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


  function buildShareText(last, userName) {
    if (!last || !last.tops || !last.tops.length) {
      return 'دارم با «اسب سیاه» مسیر تحصیلی‌ام را بر اساس جرقه‌های خودم کشف می‌کنم — نه فقط رتبه.\n#اسب‌سیاه #شهررؤیاها';
    }
    var kind = last.kind === 'branches' ? 'شاخه‌های نزدیک' : 'رشته‌های نزدیک';
    var lines = last.tops.slice(0, 3).map(function (t, i) {
      var sc = t.score;
      if (typeof sc === 'number' && sc <= 1) sc = Math.round(sc * 1000) / 10;
      else if (typeof sc === 'number') sc = Math.round(sc * 10) / 10;
      return (i + 1) + ') ' + t.name + ' — ' + sc + '٪';
    }).join('\n');
    var who = userName ? (userName + ' · ') : '';
    return who + 'از سفر اکتشافی «اسب سیاه» برگشتم.\n' +
      kind + ' من:\n' + lines + '\n\n' +
      'مسیر را با جرقه‌های خودم دیدم، نه فقط با رتبه.\n' +
      'https://arad2000.github.io/dark-horse-v2-/\n' +
      '#اسب‌سیاه #هدایت_تحصیلی #شهررؤیاها';
  }

  function shareLastResult() {
    var last = loadLastResult();
    var u = getDisplayUser();
    var text = buildShareText(last, u && u.name);
    if (navigator.share) {
      navigator.share({
        title: 'اسب سیاه',
        text: text,
        url: 'https://arad2000.github.io/dark-horse-v2-/'
      }).catch(function () {});
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        alert('متن نتیجه کپی شد؛ در تلگرام یا ایتا بچسبان.');
      }).catch(function () {
        prompt('کپی کن:', text);
      });
      return;
    }
    prompt('کپی کن:', text);
  }


  function exitApp() {
    var ok = confirm('از اسب سیاه خارج می‌شوی؟');
    if (!ok) return;
    // تلاش برای بستن پنجره/اپ
    try { window.close(); } catch (e) {}
    try {
      if (window.navigator && navigator.app && navigator.app.exitApp) navigator.app.exitApp();
    } catch (e) {}
    // اگر بسته نشد (مرورگر): به صفحه خالی راهنما
    document.body.innerHTML =
      '<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0a0a0f;color:#cbb98a;font-family:Vazirmatn,sans-serif;text-align:center;padding:24px;line-height:2;">' +
      '<div><div style="color:#f0c040;font-size:1.2rem;margin-bottom:8px;">اسب سیاه</div>' +
      'می‌توانی این زبانه را ببندی.<br>اگر از آیکون نصب‌شده باز کرده‌ای، از دکمهٔ Home گوشی خارج شو.</div></div>';
  }

  function renderProfile() {
    ensureTabbar();
    setActiveTab('profile');
    window.__dhInJourney = false;
    var root = $('app');
    if (!root) return;
    var u = getDisplayUser();
    var q = localQuota();
    var last = loadLastResult();

    if (!u) {
      root.innerHTML =
        '<div class="dh-home-wrap">' +
        '<div class="card" style="text-align:right;margin-top:4px;">' +
        '<h2 style="text-align:center;color:#f0c040;">پروفایل</h2>' +
        '<p style="color:#b0a080;line-height:1.9;">نام و موبایل فقط برای ذخیره روی همین دستگاه است؛ بدون اجبار به پیامک.</p>' +
        '<label style="display:block;margin:8px 0 4px;">نام</label>' +
        '<input id="dh-p-name" placeholder="مثلاً سارا" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">' +
        '<label style="display:block;margin:8px 0 4px;">موبایل</label>' +
        '<input id="dh-p-phone" inputmode="numeric" placeholder="09xxxxxxxxx" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">' +
        '<p id="dh-p-err" style="color:#f66;min-height:1.2em;font-size:0.85rem;"></p>' +
        '<button class="btn btn-primary" style="width:100%;" id="dh-p-save">ثبت پروفایل</button>' +
        '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">خانه</button>' +
        '</div></div>';
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
    var used = q.used || 0;

    var lastHtml = '';
    if (last && last.tops && last.tops.length) {
      var when = '';
      try {
        when = new Date(last.at).toLocaleDateString('fa-IR', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      } catch (e) { when = ''; }
      var kindLabel = last.kind === 'branches' ? 'شاخه دبیرستان' : 'رشته دانشگاهی';
      var rows = last.tops.map(function (t, i) {
        var sc = (typeof t.score === 'number') ? (t.score > 1 ? t.score : Math.round(t.score * 1000) / 10) : t.score;
        if (sc <= 1 && sc > 0) sc = Math.round(sc * 1000) / 10;
        return '<div class="dh-last-row">' +
          '<span class="dh-last-rank">' + (i + 1) + '</span>' +
          '<span class="dh-last-name">' + escape(t.name) + '</span>' +
          '<span class="dh-last-score">' + escape(String(sc)) + '٪</span>' +
          '</div>';
      }).join('');
      lastHtml =
        '<div class="dh-last-card">' +
          '<div class="dh-last-title">آخرین کشف تو</div>' +
          '<div class="dh-last-meta">' + escape(kindLabel) + (when ? ' · ' + escape(when) : '') +
            (last.sparks ? ' · ' + last.sparks + ' جرقه' : '') + '</div>' +
          rows +
        '</div>';
    } else {
      lastHtml =
        '<div class="dh-last-card dh-last-empty">' +
          '<div class="dh-last-title">هنوز سفری تمام نشده</div>' +
          '<p style="margin:8px 0 0;color:#8a7a55;font-size:0.88rem;line-height:1.7;">یک‌بار سفر اکتشافی را تا نتیجه برو؛ خلاصه اینجا می‌ماند.</p>' +
        '</div>';
    }

    root.innerHTML =
      '<div class="dh-home-wrap">' +
      '<div class="card" style="text-align:right;margin-top:4px;padding-bottom:18px;">' +
      '<div class="dh-profile-avatar">' + escape(initial) + '</div>' +
      '<h2 style="text-align:center;margin:0;color:#f0c040;">' + escape(u.name) + '</h2>' +
      '<p style="text-align:center;color:#8a7a55;margin:6px 0 0;font-size:0.9rem;">' + escape(u.phone || '') + '</p>' +
      '<div class="dh-stat-grid">' +
        '<div class="dh-stat"><div class="n">' + escape(String(remain)) + '</div><div class="l">اکتشاف باقی</div></div>' +
        '<div class="dh-stat"><div class="n">' + (premium ? '✓' : String(used)) + '</div><div class="l">' + (premium ? 'اشتراک' : 'مصرف‌شده') + '</div></div>' +
      '</div>' +
      lastHtml +
      '<button class="btn btn-primary" style="width:100%;margin-top:14px;" id="dh-p-journey">' +
        (last && last.tops && last.tops.length ? 'سفر دوباره' : 'شروع اولین سفر') + '</button>' +
      (last && last.tops && last.tops.length ? '<button class="btn" style="width:100%;margin-top:8px;border-color:rgba(212,175,55,0.45);color:#f0c040;" id="dh-p-share">اشتراک‌گذاری نتیجه</button>' : '') +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-prem">' +
        (premium ? 'اشتراک فعال است' : 'فعال‌سازی اشتراک (تستی)') + '</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">خانه</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;opacity:0.85;" id="dh-p-out">خروج از حساب</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;color:#c08080;border-color:#543;" id="dh-p-exit">خروج از اپ</button>' +
      '</div></div>';

    $('dh-p-home').onclick = function () { switchTab('home'); };
    $('dh-p-journey').onclick = function () { startJourneyFromShell(); };
    var sh = $('dh-p-share');
    if (sh) sh.onclick = function () { shareLastResult(); };
    $('dh-p-out').onclick = function () {
      localStorage.removeItem(LOCAL_USER_KEY);
      renderProfile();
    };
    var ex = $('dh-p-exit');
    if (ex) ex.onclick = function () { exitApp(); };
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
        var summary = extractResultSummary(data, type);
        if (summary && summary.tops && summary.tops.length) saveLastResult(summary);
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
