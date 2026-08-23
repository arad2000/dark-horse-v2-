/**
 * shell.js v24 — UI ماکت حرفه‌ای — خانه زنده‌تر + پروفایل + تب‌ها
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
    var h = new Date().getHours();
    if (h >= 5 && h < 9) return 'صبح بخیر';
    if (h >= 9 && h < 12) return 'وقت بخیر';
    if (h >= 12 && h < 15) return 'ظهر بخیر';
    if (h >= 15 && h < 19) return 'عصر بخیر';
    return 'شب بخیر';
  }

  function faDate() {
    try {
      return new Date().toLocaleDateString('fa-IR', { weekday: 'long', day: 'numeric', month: 'long' });
    } catch (e) {
      return '';
    }
  }

  function ensureTabbar() {
    var nav = $('dh-tabbar');
    var html =
      '<button type="button" data-tab="home" aria-label="خانه"><span class="ico" aria-hidden="true"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 10.5L12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5z"/></svg></span><span class="lbl">خانه</span></button>' +
      '<button type="button" data-tab="journey" aria-label="سفر"><span class="ico" aria-hidden="true"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></span><span class="lbl">سفر</span></button>' +
      '<button type="button" data-tab="profile" aria-label="پروفایل"><span class="ico" aria-hidden="true"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3.5"/><path d="M5 19c1.5-3.5 4-5 7-5s5.5 1.5 7 5"/></svg></span><span class="lbl">پروفایل</span></button>';
    if (!nav) {
      nav = document.createElement('nav');
      nav.id = 'dh-tabbar';
      nav.addEventListener('click', function (e) {
        var btn = e.target.closest('button[data-tab]');
        if (!btn) return;
        switchTab(btn.getAttribute('data-tab'));
      });
      document.body.appendChild(nav);
    }
    nav.innerHTML = html;
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


  function hasUnfinishedJourney() {
    try {
      var raw = localStorage.getItem('darkhorse_session_v2');
      if (!raw) return false;
      var data = JSON.parse(raw);
      if (!data || data.journeyFinished) return false;
      var st = data.stage;
      return st && ['realm', 'subRealm', 'narrowPath', 'introSwipe', 'swipe',
        'introStrategies', 'strategies', 'introValues', 'values', 'choice'].indexOf(st) >= 0;
    } catch (e) { return false; }
  }

  function journeyProgressPct() {
    try {
      var stageId = null;
      if (typeof state !== 'undefined' && state && state.stage) stageId = state.stage;
      if (!stageId) {
        var raw = localStorage.getItem('darkhorse_session_v2');
        if (raw) {
          var data = JSON.parse(raw);
          stageId = data.stage || null;
        }
      }
      if (!stageId) {
        var last = loadLastResult();
        if (last && last.tops && last.tops.length) return 100;
        return 0;
      }
      // همان منطق progressHTML در app.js
      var uniqueSteps = ['realm', 'swipe', 'strategies', 'values', 'choice', 'results'];
      var u = uniqueSteps.indexOf(stageId);
      if (stageId === 'introSwipe') u = uniqueSteps.indexOf('swipe');
      if (stageId === 'introStrategies') u = uniqueSteps.indexOf('strategies');
      if (stageId === 'introValues') u = uniqueSteps.indexOf('values');
      if (['manifesto', 'guide', 'splash'].indexOf(stageId) >= 0) return 0;
      if (['subRealm', 'narrowPath'].indexOf(stageId) >= 0) u = 0;
      if (u < 0) u = 0;
      return Math.round((u / (uniqueSteps.length - 1)) * 100);
    } catch (e) {}
    return 0;
  }

  function todaySparkQuote() {
    var fallback = {
      t: 'هیچ راهی به سوی موفقیت وجود ندارد، موفقیت خود یک راه است.',
      a: 'وینستون چرچیل'
    };
    try {
      if (window.DHQuote && DHQuote.todayBundle) {
        var b = DHQuote.todayBundle();
        if (b && b[0] && b[0].t) return { t: b[0].t, a: b[0].tag || b[0].a || 'اسب سیاه' };
      }
      if (window.DH_QUOTES && DH_QUOTES.length) {
        var i = new Date().getDate() % DH_QUOTES.length;
        var q = DH_QUOTES[i];
        return { t: q.t || q.text || fallback.t, a: q.tag || q.a || 'اسب سیاه' };
      }
    } catch (e) {}
    return fallback;
  }

  function renderHome() {
    ensureTabbar();
    setActiveTab('home');
    window.__dhInJourney = false;
    try { if (typeof saveSession === 'function') saveSession(); } catch (e) {}

    var u = getDisplayUser();
    var name = (u && u.name) ? u.name : 'مسافر';
    var pct = journeyProgressPct();
    var canContinue = hasUnfinishedJourney();
    var progressLabel = pct >= 100
      ? 'سفر قبلی کامل شده'
      : (canContinue ? 'می‌توانی از همین‌جا ادامه بدهی' : 'هنوز سفری شروع نشده');
    var ctaLabel = canContinue ? 'ادامه سفر' : 'شروع سفر';

    var bundle = [];
    try {
      if (window.DHQuote && DHQuote.todayBundle) bundle = DHQuote.todayBundle() || [];
    } catch (e) {}
    if (!bundle.length && window.DH_QUOTES && DH_QUOTES.length) {
      var di = new Date().getDate() % DH_QUOTES.length;
      for (var qi = 0; qi < Math.min(6, DH_QUOTES.length); qi++) {
        bundle.push(DH_QUOTES[(di + qi) % DH_QUOTES.length]);
      }
    }
    var showMore = !!window.__dhShowMoreQuotes;
    var lines = (bundle || []).slice(0, showMore ? 6 : 3).map(function (item, idx) {
      var t = item.t || item.text || '';
      var tag = item.tag || item.a || '';
      return '<div class="dh-q-line">' +
        '<span class="dh-q-num">' + (idx + 1) + '</span>' +
        '<div class="dh-q-body"><p>' + escape(t) + '</p>' +
        (tag ? '<span class="dh-q-tag">' + escape(tag) + '</span>' : '') +
        '</div></div>';
    }).join('');
    var moreBtn = '';
    if ((bundle || []).length > 3) {
      moreBtn = '<button type="button" class="dh-msg-more" id="dh-msg-toggle">' +
        (showMore ? 'نمایش کمتر' : 'پیام‌های بیشتر') + '</button>';
    }

    var root = $('app');
    if (!root) return;

    root.innerHTML =
      '<div class="dh-home-wrap dh-home-v24">' +
        '<header class="dh-topbar dh-topbar-center">' +
          '<div class="dh-top-brand dh-top-brand-center">' +
            '<div class="dh-logo-mark" aria-hidden="true">' +
              '<svg viewBox="0 0 64 64" width="42" height="42">' +
                '<defs><linearGradient id="hg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#f5d76e"/><stop offset="100%" stop-color="#c9a227"/></linearGradient></defs>' +
                '<path fill="url(#hg)" d="M12 44c4-14 14-24 28-26 2 6 1 12-2 16 6 1 10 5 12 10-8 2-16 1-22-2-3 4-8 6-14 6 0-2-1-3-2-4z"/>' +
                '<path fill="none" stroke="url(#hg)" stroke-width="2" d="M10 50c8-2 18-1 28 2"/>' +
              '</svg>' +
            '</div>' +
            '<div class="dh-brand-text">' +
              '<div class="dh-logo-title">DARK HORSE</div>' +
              '<div class="dh-logo-sub">اسب سیاه</div>' +
            '</div>' +
          '</div>' +
        '</header>' +

        '<section class="dh-hello">' +
          '<h1 class="dh-identity-title">سامانه هدایت تحصیلی و انتخاب رشته دانشگاهی بر اساس فردیت</h1>' +
          '<p class="dh-greet-date">' + greeting() + '، ' + escape(name) + ' · ' + escape(faDate()) + '</p>' +
        '</section>' +

        '<section class="dh-hero-journey">' +
          '<div class="dh-hero-text">' +
            '<h2>سفر اکتشافی</h2>' +
            '<button type="button" class="btn btn-primary dh-hero-cta" id="dh-start-journey">' + ctaLabel + '</button>' +
            (canContinue ? '<button type="button" class="btn dh-hero-secondary" id="dh-restart-journey">شروع از نو</button>' : '') +
          '</div>' +
          '<div class="dh-hero-visual" aria-hidden="true">' +
            '<div class="dh-compass">' +
              '<svg viewBox="0 0 80 80" width="72" height="72">' +
                '<circle cx="40" cy="40" r="34" fill="none" stroke="rgba(240,192,64,0.35)" stroke-width="2"/>' +
                '<circle cx="40" cy="40" r="26" fill="rgba(240,192,64,0.08)" stroke="rgba(240,192,64,0.5)" stroke-width="1.5"/>' +
                '<path d="M40 14 L46 40 L40 66 L34 40 Z" fill="#f0c040"/>' +
                '<circle cx="40" cy="40" r="4" fill="#0a0a0f" stroke="#f0c040"/>' +
              '</svg>' +
            '</div>' +
          '</div>' +
        '</section>' +

        '<section class="dh-progress-card">' +
          '<div class="dh-progress-head">' +
            '<div>' +
              '<div class="dh-progress-title">آخرین مسیر شما</div>' +
              '<div class="dh-progress-sub">' + escape(progressLabel) + '</div>' +
            '</div>' +
            '<span class="dh-progress-pct-big">' + pct + '٪</span>' +
          '</div>' +
          '<div class="dh-progress-bar"><div class="dh-progress-fill" style="width:' + pct + '%"></div></div>' +
        '</section>' +

        '<section class="dh-messages-card">' +
          '<div class="dh-messages-head">' +
            '<span class="dh-messages-label">✦ پیام‌های امروز</span>' +
            '<span class="dh-messages-sub">با الهام از روح کتاب اسب سیاه</span>' +
          '</div>' +
          (lines || '<p class="dh-messages-empty">پیام‌ها در حال آماده‌سازی…</p>') +
          moreBtn +
          '<div class="dh-quote-foot">تاد رز و اگی اوگاس · بازنویسی برای اپ</div>' +
        '</section>' +

        '<section class="dh-feature-row dh-feature-4 dh-feature-soft">' +
          '<button type="button" class="dh-feature" id="dh-open-spark">' +
            '<span class="dh-f-ico">⚡</span><span class="dh-f-t">جرقه‌یاب</span>' +
            '<span class="dh-f-d">کشف انگیزه‌ها</span></button>' +
          '<button type="button" class="dh-feature" id="dh-open-stories">' +
            '<span class="dh-f-ico">📖</span><span class="dh-f-t">داستان‌ها</span>' +
            '<span class="dh-f-d">الهام از مسیرها</span></button>' +
          '<button type="button" class="dh-feature" id="dh-open-poems">' +
            '<span class="dh-f-ico">🪶</span><span class="dh-f-t">سخن بزرگان</span>' +
            '<span class="dh-f-d">حکمت برای امروز</span></button>' +
          '<button type="button" class="dh-feature" id="dh-open-parents">' +
            '<span class="dh-f-ico">🤝</span><span class="dh-f-t">والدین</span>' +
            '<span class="dh-f-d">همراهی بهتر</span></button>' +
        '</section>' +
      '</div>';

    var sj = $('dh-start-journey');
    if (sj) sj.onclick = function () { startJourneyFromShell(); };
    var mt = $('dh-msg-toggle');
    if (mt) mt.onclick = function () {
      window.__dhShowMoreQuotes = !window.__dhShowMoreQuotes;
      renderHome();
    };
    var rs = $('dh-restart-journey');
    if (rs) rs.onclick = function () {
      if (!confirm('سفر فعلی پاک شود و از اول شروع کنی؟')) return;
      try {
        if (typeof fullResetState === 'function') fullResetState();
        else localStorage.removeItem('darkhorse_session_v2');
        window.__dhHasSavedSession = false;
        window.__dhJourneyFinished = false;
      } catch (e) {}
      window.__dhInJourney = true;
      setActiveTab('journey');
      if (typeof state !== 'undefined') {
        state.stage = 'splash';
        state.history = [];
      }
      if (typeof saveSession === 'function') {
        try { saveSession(); } catch (e) {}
      }
      if (typeof render === 'function') render();
    };
    var sp = $('dh-open-spark');
    if (sp) sp.onclick = function () {
      if (window.DHSparkGame && DHSparkGame.open) DHSparkGame.open();
      else alert('ماژول جرقه‌یاب بارگذاری نشده. صفحه را یک‌بار تازه کن.');
    };
    var pr = $('dh-open-parents');
    if (pr) pr.onclick = function () {
      if (window.DHParents && DHParents.open) DHParents.open();
      else alert('بخش والدین بارگذاری نشده. صفحه را یک‌بار تازه کن.');
    };
    var st = $('dh-open-stories');
    if (st) st.onclick = function () {
      if (window.DHStories && DHStories.open) DHStories.open();
      else alert('بخش داستان‌ها بارگذاری نشده. صفحه را یک‌بار تازه کن.');
    };
    var po = $('dh-open-poems');
    if (po) po.onclick = function () {
      if (window.DHPoems && DHPoems.open) DHPoems.open();
      else alert('بخش سخن بزرگان بارگذاری نشده. صفحه را یک‌بار تازه کن.');
    };
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
      if (typeof saveSession === 'function') {
        try { saveSession(); } catch (e1) {}
      }

      var data = null;
      try {
        var raw = localStorage.getItem('darkhorse_session_v2');
        if (raw) data = JSON.parse(raw);
      } catch (e2) { data = null; }

      var unfinished = data && !data.journeyFinished && data.stage &&
        ['realm', 'subRealm', 'narrowPath', 'introSwipe', 'swipe',
         'introStrategies', 'strategies', 'introValues', 'values', 'choice'].indexOf(data.stage) >= 0;

      if (unfinished) {
        if (typeof loadSession === 'function') {
          loadSession();
        } else if (typeof dhResumeFromSplash === 'function') {
          window.__dhSavedSession = data;
          window.__dhHasSavedSession = true;
          window.__dhJourneyFinished = false;
          dhResumeFromSplash();
          return;
        }
        if (typeof state !== 'undefined') {
          if (!state.stage || ['splash', 'manifesto', 'guide', 'results'].indexOf(state.stage) >= 0) {
            state.stage = data.stage || 'realm';
          }
        }
        if (typeof render === 'function') render();
        return;
      }

      // سفر تازه → صفحه شهر رؤیاها (splash)، نه پرش مستقیم به محله‌ها
      if (typeof fullResetState === 'function') {
        fullResetState();
      } else {
        try { localStorage.removeItem('darkhorse_session_v2'); } catch (e3) {}
      }
      window.__dhHasSavedSession = false;
      window.__dhJourneyFinished = false;
      window.__dhSavedSession = null;
      if (typeof state !== 'undefined') {
        state.stage = 'splash';
        state.history = [];
        state.journeyFinished = false;
      }
      if (typeof saveSession === 'function') {
        try { saveSession(); } catch (e4) {}
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
    if (!confirm('از اسب سیاه خارج می‌شوی؟')) return;
    try { window.close(); } catch (e) {}
    document.body.innerHTML = '<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0a0a0f;color:#cbb98a;font-family:Vazirmatn,sans-serif;text-align:center;padding:24px;line-height:2;"><div><div style="color:#f0c040;font-size:1.2rem;margin-bottom:8px;">اسب سیاه</div>این زبانه را ببند یا با دکمه Home از اپ خارج شو.</div></div>';
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
    if (tab === 'home') {
      try { if (typeof saveSession === 'function') saveSession(); } catch (e) {}
      window.__dhInJourney = false;
      renderHome();
    }
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
    startJourney: startJourneyFromShell,
    setActiveTab: setActiveTab
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  setTimeout(boot, 0);
})();
