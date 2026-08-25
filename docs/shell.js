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

  function homeLivingLine(pct, canContinue) {
    try {
      var stage = null;
      if (typeof state !== 'undefined' && state && state.stage) stage = state.stage;
      if (!stage) {
        var raw = localStorage.getItem('darkhorse_session_v2');
        if (raw) stage = (JSON.parse(raw) || {}).stage;
      }
      if (pct >= 100 || stage === 'results') return 'سه مسیر بیش از همه با تو همخوان شدند.';
      if (stage === 'choice') return 'آماده‌ای نتیجه را ببینی.';
      if (stage === 'values' || stage === 'introValues') return 'حالا داریم می‌فهمیم چه چیزی برای تو مهم است.';
      if (stage === 'strategies' || stage === 'introStrategies') return 'حالا داریم می‌فهمیم چگونه فکر می‌کنی.';
      if (stage === 'swipe' || stage === 'introSwipe') {
        var n = 0;
        try {
          if (typeof state !== 'undefined' && state && state.likedCodes) n = state.likedCodes.length;
          else n = (JSON.parse(localStorage.getItem('darkhorse_session_v2') || '{}').likedCodes || []).length;
        } catch (e1) {}
        if (n >= 25) return 'تصویر فردیتت دارد شکل می‌گیرد.';
        if (n > 0) return 'جرقه‌ها مسیرت را روشن می‌کنند.';
        return 'به لایه جرقه‌ها رسیده‌ای.';
      }
      if (stage === 'narrowPath' || stage === 'subRealm' || stage === 'realm') return 'داری محله‌ها و مسیرهای باریک را ورق می‌زنی.';
      if (canContinue) return 'سفر ناتمام داری؛ از همان‌جا ادامه بده.';
    } catch (e) {}
    return 'مسیر متفاوت تو از اینجا شروع می‌شود.';
  }


  function openSystemGuide() {
    var existing = document.getElementById('dh-sys-guide');
    if (existing) existing.remove();
    var page = 0;
    var pages = [
      {
        title: 'راهنمای سفر اکتشافی',
        body:
          '<p class="dh-g-quote">«موفقیت از تقلید دیگران به دست نمی‌آید؛ از شناخت فردیت و ساختن مسیر شخصی می‌آید.»</p>' +
          '<p class="dh-g-src">— تاد رز، کتاب اسب سیاه (پروژه هاروارد)</p>' +
          '<h3>مشکل از کجاست؟</h3>' +
          '<p>هر سال هزاران دانش‌آموز می‌پرسند «چه رشته‌ای بخوانم؟» پاسخ‌های رایج معمولاً بر پایه رتبه، پرستیژ یا بازار کار کلیشه‌ای است و <strong>فردیت تو را نادیده می‌گیرند</strong>.</p>' +
          '<h3>راه‌حل این سامانه</h3>' +
          '<p>بر اساس پژوهش Dark Horse در هاروارد، به‌جای «چه نمره‌ای آوردی؟» می‌پرسد: <strong>«از چه چیزی واقعاً انرژی می‌گیری؟»</strong></p>' +
          '<h3>سه لایه شناخت</h3>' +
          '<ul><li><strong>خرده‌انگیزه‌ها</strong> — جرقه‌های لذت روزمره</li>' +
          '<li><strong>راهبردهای شخصی</strong> — سبک فکر و یادگیری</li>' +
          '<li><strong>ارزش‌های بنیادین</strong> — معنای رضایت‌بخش کار</li></ul>' +
          '<p class="dh-g-note">این تست شخصیت نیست؛ سفر کوتاهی برای کشف خودت است.</p>'
      },
      {
        title: '',
        body:
          '<p>این یک تست نیست؛ <strong>سفری برای شناخت انگیزه، سبک فکر و ارزش‌های خودت</strong> است.</p>' +
          '<h3>مسیر سفر</h3>' +
          '<p><strong>۱) خرده‌انگیزه‌ها</strong><br>از میان بیش از ۱۱۰۰ جرقه، موارد انرژی‌بخش را انتخاب کن (حدود ۲۰ تا ۸۰).</p>' +
          '<p><strong>۲) راهبردهای شخصی</strong><br>حدود ۲۵ موقعیت کوتاه درباره سبک حل مسئله.</p>' +
          '<p><strong>۳) ارزش‌های بنیادین</strong><br>۱۵ دوگانه برای فهم رضایت بلندمدت.</p>' +
          '<h3>وزن‌ها</h3>' +
          '<p><strong>رشته دانشگاهی:</strong> خرده‌انگیزه ۵۵٪ · ارزش ۳۰٪ · راهبرد ۱۵٪</p>' +
          '<p><strong>شاخه دبیرستان:</strong> خرده‌انگیزه ۶۰٪ · راهبرد ۲۰٪ · ارزش ۲۰٪</p>' +
          '<p class="dh-g-note">انگیزه و ارزش پایدارترند؛ راهبرد را می‌توان ساخت.</p>'
      }
    ];
    var ov = document.createElement('div');
    ov.id = 'dh-sys-guide';
    ov.className = 'dh-guide-ov';
    ov.setAttribute('dir', 'rtl');
    function paint() {
      var p = pages[page];
      ov.innerHTML =
        '<div class="dh-guide-panel">' +
          '<button type="button" class="dh-guide-x" id="dh-guide-close">×</button>' +
          (p.title ? '<h2 class="dh-guide-title">' + p.title + '</h2>' : '') +
          '<div class="dh-guide-body">' + p.body + '</div>' +
          '<div class="dh-guide-dots"><span class="' + (page === 0 ? 'on' : '') + '"></span><span class="' + (page === 1 ? 'on' : '') + '"></span></div>' +
          '<div class="dh-guide-actions">' +
            (page === 0
              ? '<button type="button" class="dh-guide-btn" id="dh-guide-next">ادامه راهنما</button>'
              : '<button type="button" class="dh-guide-btn secondary" id="dh-guide-prev">قبلی</button><button type="button" class="dh-guide-btn" id="dh-guide-done">متوجه شدم</button>') +
          '</div></div>';
      var close = function () { ov.remove(); };
      var el;
      el = document.getElementById('dh-guide-close'); if (el) el.onclick = close;
      el = document.getElementById('dh-guide-next'); if (el) el.onclick = function () { page = 1; paint(); };
      el = document.getElementById('dh-guide-prev'); if (el) el.onclick = function () { page = 0; paint(); };
      el = document.getElementById('dh-guide-done'); if (el) el.onclick = close;
      ov.onclick = function (e) { if (e.target === ov) close(); };
    }
    document.body.appendChild(ov);
    paint();
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
    var progressLabel = pct >= 100 ? 'سفر قبلی کامل شده'
      : (canContinue ? 'آخرین مسیر شما' : 'هنوز سفری شروع نشده');

    var quote = { t: 'هیچ راهی به سوی موفقیت وجود ندارد، موفقیت خود یک راه است.', tag: 'وینستون چرچیل' };
    try {
      var bundle = [];
      if (window.DHQuote && DHQuote.todayBundle) bundle = DHQuote.todayBundle() || [];
      if (!bundle.length && window.DH_QUOTES && DH_QUOTES.length) {
        bundle = [DH_QUOTES[new Date().getDate() % DH_QUOTES.length]];
      }
      if (bundle[0]) {
        quote = { t: bundle[0].t || bundle[0].text || quote.t, tag: bundle[0].tag || bundle[0].a || quote.tag };
      }
    } catch (e2) {}

    var root = $('app');
    if (!root) return;

    var base = '';
    try {
      if ((location.pathname || '').indexOf('/dark-horse-v2-') === 0) base = '/dark-horse-v2-/';
    } catch (e0) {}

    function ico(file) {
      return '<span class="dh-mk2-orb"><img src="' + base + file + '" alt="" width="24" height="24"></span>';
    }

    var heroUrl = base + 'hero-journey.svg';
    var ringOff = (301.6 * (1 - Math.min(100, Math.max(0, pct)) / 100)).toFixed(1);

    root.innerHTML =
      '<div class="dh-home-wrap dh-mk2">' +
        '<div class="dh-mk2-meta">' +
          '<div class="dh-mk2-meta-stack">' +
            '<span class="dh-mk2-meta-name">سلام ' + escape(name) + '</span>' +
            '<span class="dh-mk2-meta-date">' + escape(faDate()) + '</span>' +
          '</div>' +
        '</div>' +
        '<header class="dh-mk2-brand">' +
          '<div class="dh-mk2-logo-ring"><img src="' + base + 'icon-192.png" alt="" width="96" height="96"></div>' +
          '<div class="dh-mk2-word">DARK HORSE</div>' +
          '<div class="dh-mk2-fa"><i></i><span>اسب سیاه</span><i></i></div>' +
          '<h1 class="dh-mk2-sys">سامانه هدایت تحصیلی و انتخاب رشته دانشگاهی</h1>' +
          '<p class="dh-mk2-sub">بر اساس فردیت</p>' +
        '</header>' +
        '<section class="dh-mk2-hero">' +
          '<div class="dh-mk2-hero-bg" style="background-image:url(\'' + heroUrl + '\')"></div>' +
          '<div class="dh-mk2-hero-shade"></div>' +
          '<div class="dh-mk2-hero-body">' +
            '<div class="dh-mk2-hero-top">' +
              '<span class="dh-mk2-compass"><img src="' + base + 'ico-compass.svg" alt="" width="40" height="40"></span>' +
              '<div><div class="dh-mk2-hero-title">سفر اکتشافی</div>' +
              '<div class="dh-mk2-hero-sub">مسیر متفاوت تو از اینجا شروع می‌شود</div></div>' +
            '</div>' +
            '<button type="button" class="dh-mk2-cta" id="dh-start-journey">' +
              (canContinue ? 'ادامه سفر' : 'شروع سفر') + ' <span>›</span></button>' +
          '</div></section>' +
        '<section class="dh-mk2-progress">' +
          '<div class="dh-mk2-ring"><svg viewBox="0 0 120 120">' +
            '<circle cx="60" cy="60" r="48" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="10"/>' +
            '<circle cx="60" cy="60" r="48" fill="none" stroke="#D4AF37" stroke-width="10" stroke-linecap="round" ' +
              'stroke-dasharray="301.6" stroke-dashoffset="' + ringOff + '" transform="rotate(-90 60 60)" class="dh-mk2-ring-val"/>' +
          '</svg><span>' + pct + '%</span></div>' +
          '<div class="dh-mk2-prog-body">' +
            '<div class="dh-mk2-prog-title">' + escape(progressLabel) + '</div>' +
            '<div class="dh-mk2-bar"><i style="width:' + pct + '%"></i></div>' +
            (canContinue ? '<button type="button" class="dh-mk2-cont" id="dh-continue-journey">ادامه سفر ‹</button>' : '') +
          '</div></section>' +
        '<section class="dh-mk2-quote">' +
          '<div class="dh-mk2-quote-top">' + ico('ico-quill.svg') +
          '<span class="dh-mk2-quote-label">پیام امروز</span><span class="dh-mk2-qq">”</span></div>' +
          '<p class="dh-mk2-quote-text">' + escape(quote.t) + '</p>' +
          '<div class="dh-mk2-quote-by">' + escape(quote.tag) + '</div></section>' +
        '<section class="dh-mk2-more">' +
          '<div class="dh-mk2-sep"><i></i><span>کشف بیشتر</span><i></i></div>' +
          '<button type="button" class="dh-mk2-row dh-mk2-row-hot" id="dh-open-spark">' +
            ico('ico-bolt.svg') +
            '<div class="dh-mk2-row-t"><strong>جرقه‌یاب</strong><span>کشف انگیزه‌هایی که تو را به حرکت درمی‌آورند</span></div>' +
            '<span class="dh-mk2-chev"><img src="' + base + 'ico-chevron.svg" alt="" width="18" height="18"></span></button>' +
          '<div class="dh-mk2-duo">' +
            '<button type="button" class="dh-mk2-tile" id="dh-open-stories">' + ico('ico-book.svg') +
            '<strong>داستان‌ها</strong><span>روایت مسیرهای واقعی</span></button>' +
            '<button type="button" class="dh-mk2-tile" id="dh-open-poems">' + ico('ico-quill.svg') +
            '<strong>سخن بزرگان</strong><span>یک فکر ارزشمند برای امروز</span></button></div>' +
          '<div class="dh-mk2-duo">' +
            '<button type="button" class="dh-mk2-tile" id="dh-open-parents">' + ico('ico-parents.svg') +
            '<strong>والدین</strong><span>همراهی بهتر در انتخاب مسیر</span></button>' +
            '<button type="button" class="dh-mk2-tile" id="dh-open-guide">' + ico('ico-compass.svg') +
            '<strong>راهنمای سامانه</strong><span>مشاور و معرفی سامانه</span></button></div>' +
        '</section></div>';

    function on(id, fn) { var el = $(id); if (el) el.onclick = fn; }
    on('dh-start-journey', function () { startJourneyFromShell(); });
    on('dh-continue-journey', function () { startJourneyFromShell(); });
    on('dh-open-spark', function () {
      if (window.DHSparkGame && DHSparkGame.open) DHSparkGame.open();
      else alert('ماژول جرقه‌یاب بارگذاری نشده.');
    });
    on('dh-open-stories', function () {
      if (window.DHStories && DHStories.open) DHStories.open();
      else alert('بخش داستان‌ها بارگذاری نشده.');
    });
    on('dh-open-poems', function () {
      if (window.DHPoems && DHPoems.open) DHPoems.open();
      else alert('بخش سخن بزرگان بارگذاری نشده.');
    });
    on('dh-open-parents', function () {
      if (window.DHParents && DHParents.open) DHParents.open();
      else alert('بخش والدین بارگذاری نشده.');
    });
    on('dh-open-guide', function () { openSystemGuide(); });
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
        fullResetState(true);
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

  function tryAutoResumeJourney() {
    try {
      var raw = localStorage.getItem('darkhorse_session_v2');
      if (!raw) return false;
      var data = JSON.parse(raw);
      if (!data || data.journeyFinished) return false;
      var mid = ['realm', 'subRealm', 'narrowPath', 'introSwipe', 'swipe',
        'introStrategies', 'strategies', 'introValues', 'values', 'choice'];
      if (mid.indexOf(data.stage) < 0) return false;
      window.__dhInJourney = true;
      setActiveTab('journey');
      if (typeof loadSession === 'function') loadSession();
      if (typeof render === 'function') render();
      return true;
    } catch (e) {
      return false;
    }
  }

  function boot() {
    ensureTabbar();
    patchRender();
    patchConsumeOnResults();
    // اگر سفر ناتمام است، از همان‌جا ادامه بده (خروج از اپ = از دست رفتن پیشرفت نباشد)
    if (tryAutoResumeJourney()) return;
    renderHome();
    setTimeout(function () {
      if (!window.__dhInJourney && !tryAutoResumeJourney()) renderHome();
    }, 200);
    setTimeout(function () {
      if (!window.__dhInJourney && !tryAutoResumeJourney()) renderHome();
    }, 700);
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
