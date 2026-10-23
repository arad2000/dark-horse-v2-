/**
 * shell.js v25 — commercial charge gate + stable charged journey session
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
    if (typeof q.serverRemaining === 'number' && isFinite(q.serverRemaining) && q.serverRemaining > 0) return true;
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
      return st && ['splash', 'realm', 'subRealm', 'narrowPath', 'introSwipe', 'swipe',
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
    try { shellScrollTop(); } catch (eS) {}

    var existing = document.getElementById('dh-sys-guide');
    if (existing) existing.remove();
    var page = 0;
    var weightMode = 'uni';
    var pages = [
      {
        tab: '۱. فلسفه فردیت',
        title: 'چرا اسب سیاه متفاوت است؟',
        body: function () {
          return '<p class="dh-g-quote">«موفقیت از تقلید دیگران به دست نمی‌آید؛ از شناخت فردیت و ساختن مسیر شخصی می‌آید.»</p>' +
            '<p class="dh-g-src">— تاد رز و اگی اوگاس، کتاب اسب سیاه. این سامانه محصول یا تأیید دانشگاه هاروارد نیست.</p>' +
            '<h3>مشکل نگاه سنتی چیست؟</h3>' +
            '<p>پاسخ‌های رایج معمولاً فقط بر پایه رتبه، پرستیژ بیرونی یا تقلید از دیگران است و <strong>فردیت منحصر‌به‌فرد تو</strong> را نادیده می‌گیرند.</p>' +
            '<h3>پرسش بنیادین اسب سیاه</h3>' +
            '<p>به‌جای «چقدر شبیه میانگین هستی؟» می‌پرسد: <strong>«از چه کاری واقعاً انرژی می‌گیری و شکوفا می‌شوی؟»</strong></p>';
        }
      },
      {
        tab: '۲. سه لایه شناخت',
        title: 'سه لایهٔ عمیق شناخت خودت',
        body: function () {
          var weightsHtml = weightMode === 'uni'
            ? '<div class="dh-sc-box dh-sc-box--good"><strong>دانشگاه (۲۳۰ رشته):</strong> خرده‌انگیزه ۵۵٪ · ارزش بنیادین ۳۰٪ · راهبرد شخصی ۱۵٪</div>'
            : '<div class="dh-sc-box dh-sc-box--good"><strong>هدایت تحصیلی دبیرستان:</strong> خرده‌انگیزه ۶۰٪ · راهبرد شخصی ۲۰٪ · ارزش بنیادین ۲۰٪</div>';
          return '<p>این یک آزمون نمره‌دار نیست؛ <strong>سفری سه‌لایه برای کشف موتور درونی توست:</strong></p>' +
            '<ul>' +
              '<li><strong>۱) خرده‌انگیزه‌ها</strong> — جرقه‌های واقعی انرژی در جزئیات کار روزمره</li>' +
              '<li><strong>۲) راهبردهای شخصی</strong> — سبک طبیعی فکر کردن، یادگیری و حل مسئله</li>' +
              '<li><strong>۳) ارزش‌های بنیادین</strong> — معنایی که رضایت عمیق بلندمدت می‌سازد</li>' +
            '</ul>' +
            '<div style="display:flex;gap:6px;margin:10px 0 8px;">' +
              '<button type="button" class="dh-mod-chip' + (weightMode === 'uni' ? ' is-active' : '') + '" id="dh-g-mode-uni">وزن‌دهی رشته‌های دانشگاهی</button>' +
              '<button type="button" class="dh-mod-chip' + (weightMode === 'hs' ? ' is-active' : '') + '" id="dh-g-mode-hs">وزن‌دهی شاخه دبیرستان</button>' +
            '</div>' +
            weightsHtml +
            '<p class="dh-g-note">انگیزه و ارزش پایدارترند؛ راهبرد را می‌توان آگاهانه ساخت.</p>';
        }
      }
    ];
    var ov = document.createElement('div');
    ov.id = 'dh-sys-guide';
    ov.className = 'dh-guide-ov';
    ov.setAttribute('dir', 'rtl');
    function paint() {
      var p = pages[page];
      var tabsHtml = pages.map(function (it, i) {
        return '<button type="button" class="dh-mod-chip' + (i === page ? ' is-active' : '') + '" data-guide-tab="' + i + '">' + it.tab + '</button>';
      }).join('');
      ov.innerHTML =
        '<div class="dh-guide-panel">' +
          '<button type="button" class="dh-guide-x" id="dh-guide-close">×</button>' +
          (p.title ? '<h2 class="dh-guide-title">' + p.title + '</h2>' : '') +
          '<div class="dh-mod-strip" id="dh-guide-tabs" style="margin-bottom:8px;">' + tabsHtml + '</div>' +
          '<div class="dh-guide-body">' + p.body() + '</div>' +
          '<div class="dh-guide-dots"><span class="' + (page === 0 ? 'on' : '') + '"></span><span class="' + (page === 1 ? 'on' : '') + '"></span></div>' +
          '<div class="dh-guide-actions">' +
            (page === 0
              ? '<button type="button" class="dh-guide-btn" id="dh-guide-next">لایه بعدی شناخت ›</button>'
              : '<button type="button" class="dh-guide-btn secondary" id="dh-guide-prev">‹ قبلی</button><button type="button" class="dh-guide-btn" id="dh-guide-go-journey">شروع سفر ›</button><button type="button" class="dh-guide-btn secondary" id="dh-guide-done">بستن</button>') +
          '</div></div>';
      var close = function () { ov.remove(); };
      var el;
      el = document.getElementById('dh-guide-close'); if (el) el.onclick = close;
      el = document.getElementById('dh-guide-next'); if (el) el.onclick = function () { dhHaptic('light'); page = 1; paint(); };
      el = document.getElementById('dh-guide-prev'); if (el) el.onclick = function () { dhHaptic('light'); page = 0; paint(); };
      el = document.getElementById('dh-guide-done'); if (el) el.onclick = close;
      el = document.getElementById('dh-guide-go-journey'); if (el) el.onclick = function () { close(); startJourneyFromShell(); };
      el = document.getElementById('dh-g-mode-uni'); if (el) el.onclick = function () { dhHaptic('light'); weightMode = 'uni'; paint(); };
      el = document.getElementById('dh-g-mode-hs'); if (el) el.onclick = function () { dhHaptic('light'); weightMode = 'hs'; paint(); };
      var tabBox = document.getElementById('dh-guide-tabs');
      if (tabBox) {
        tabBox.onclick = function (ev) {
          var b = ev.target && ev.target.closest ? ev.target.closest('[data-guide-tab]') : null;
          if (!b) return;
          dhHaptic('light');
          page = parseInt(b.getAttribute('data-guide-tab'), 10) || 0;
          paint();
        };
      }
      ov.onclick = function (e) { if (e.target === ov) close(); };
    }
    document.body.appendChild(ov);
    paint();
  }


  var __dhFardiyatTickerTimer = null;
  var __dhFardiyatTickerIdx = 0;
  var DH_FARDIYAT_LINES = [
    'مسیرت را با <strong class="dh-fardiyat">فردیت‌ات</strong> بساز',
    'رتبه مقصد نیست؛ <strong class="dh-fardiyat">جرقه</strong> مسیر است',
    'استاندارد برای همه ساخته شد؛ تو <strong class="dh-fardiyat">ناهمواری</strong>',
    'موفقیت شخصی یعنی <strong class="dh-fardiyat">رضایت</strong> همراه با <strong class="dh-fardiyat">فردیت‌ات</strong>',
    'مثل بقیه، فقط بهتر؟ این همان <strong class="dh-fardiyat">میثاق استاندارد</strong> است',
    'اسب‌های سیاه اول <strong class="dh-fardiyat">رضایت</strong> را می‌جویند، بعد اوج می‌گیرند',
    '<strong class="dh-fardiyat">خرده‌انگیزه‌ات</strong> را بشناس؛ موتور پنهان تو همان است',
    'استعداد یک قالب نیست؛ <strong class="dh-fardiyat">فردیت‌ات</strong> راهش را می‌سازد',
    'مقصد را رها کن؛ <strong class="dh-fardiyat">انتخاب‌های</strong> هم‌راستا با خودت را جدی بگیر',
    'راهبرد واحد برای همه وجود ندارد؛ فقط بهترین راهبرد برای <strong class="dh-fardiyat">تو</strong>',
    'شوق را فقط دنبال نکن؛ با شناخت جرقه‌ها <strong class="dh-fardiyat">مهندسی</strong>اش کن',
    'تقلید مسیر دیگران، <strong class="dh-fardiyat">فردیت‌ات</strong> را خاموش می‌کند',
    'انرژی‌ات کجاست؟ همان‌جا <strong class="dh-fardiyat">نقشه</strong> شروع می‌شود',
    '<strong class="dh-fardiyat">جرقه</strong> کوچک امروز، مسیر بزرگ فرداست',
    'امتیاز کنکور برچسب است؛ <strong class="dh-fardiyat">رضایت</strong> جهت است',
    'فرصت وقتی معنا دارد که با <strong class="dh-fardiyat">فردیت‌ات</strong> جور باشد',
    'اسب سیاه از ناکجا می‌آید؛ چون مسیرش <strong class="dh-fardiyat">مال خودش</strong> است',
    'بهتر شدن در چیزی که برایت مهم است؛ نسخه <strong class="dh-fardiyat">اسب سیاه</strong>',
    'دفترچه انتخاب رشته عمومی است؛ <strong class="dh-fardiyat">تو</strong> عمومی نیستی',
    'استاندارد وعده امنیت داد؛ <strong class="dh-fardiyat">فردیت‌ات</strong> وعده زندگی می‌دهد',
    'اگر پرانرژی نیستی، شاید مسیر از آنِ <strong class="dh-fardiyat">تو</strong> نیست',
    'شناخت خود، کوتاه‌ترین راه به <strong class="dh-fardiyat">انتخاب درست</strong> است',
    'امروز یک سؤال: از چه چیزی واقعاً <strong class="dh-fardiyat">انرژی</strong> می‌گیری؟'
  ];



  
  function dhTickerJalaliDateLine() {
    try {
      var fmt = new Intl.DateTimeFormat('fa-IR', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      return 'امروز: ' + fmt.format(new Date());
    } catch (e) {
      try {
        return 'امروز: ' + new Date().toLocaleDateString('fa-IR');
      } catch (e2) {
        return '';
      }
    }
  }

  function dhBuildTickerQueue() {
    var out = [];
    var i;
    for (i = 0; i < DH_FARDIYAT_LINES.length; i++) {
      out.push(DH_FARDIYAT_LINES[i]);
      if ((i + 1) % 3 === 0) {
        var d = dhTickerJalaliDateLine();
        if (d) out.push(d);
      }
    }
    return out;
  }

  function stopFardiyatTicker() {
    if (__dhFardiyatTickerTimer) {
      clearInterval(__dhFardiyatTickerTimer);
      __dhFardiyatTickerTimer = null;
    }
  }

  function startFardiyatTicker() {
    stopFardiyatTicker();
    var el = document.getElementById('dh-fardiyat-ticker-text');
    if (!el) return;
    var queue = dhBuildTickerQueue();
    if (!queue.length) return;
    __dhFardiyatTickerIdx = 0;
    el.innerHTML = queue[0];
    el.classList.add('dh-ticker-in');
    __dhFardiyatTickerTimer = setInterval(function () {
      var node = document.getElementById('dh-fardiyat-ticker-text');
      if (!node) { stopFardiyatTicker(); return; }
      var q = dhBuildTickerQueue();
      if (!q.length) return;
      node.classList.remove('dh-ticker-in');
      node.classList.add('dh-ticker-out');
      setTimeout(function () {
        var n2 = document.getElementById('dh-fardiyat-ticker-text');
        if (!n2) return;
        __dhFardiyatTickerIdx = (__dhFardiyatTickerIdx + 1) % q.length;
        n2.innerHTML = q[__dhFardiyatTickerIdx];
        n2.classList.remove('dh-ticker-out');
        n2.classList.add('dh-ticker-in');
      }, 280);
    }, 4000);
  }

  function openSanjeshFromShell() {
    try { renderHome(); } catch (e) { return false; }
    var button = $('dh-open-sanjesh');
    if (!button) return false;
    button.click();
    return true;
  }

  /* ===== Native App Feedback, Toast, Bottom Sheet & Hardware Back Navigation ===== */
  function dhPrefersReducedMotion() {
    try {
      return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    } catch (_) {
      return false;
    }
  }

  function dhHaptic(kind) {
    if (dhPrefersReducedMotion()) return;
    try {
      if (navigator && typeof navigator.vibrate === 'function') {
        navigator.vibrate(kind === 'success' ? [10, 28, 12] : 8);
      }
    } catch (_) {}
  }
  window.dhHaptic = dhHaptic;

  var __dhToastTimer = null;
  function dhToast(message, durationMs) {
    try {
      if (!document || typeof document.createElement !== 'function' || !document.body || typeof document.body.appendChild !== 'function') return;
      var el = document.getElementById('dh-native-toast');
      if (!el) {
        el = document.createElement('div');
        el.id = 'dh-native-toast';
        el.className = 'dh-native-toast';
        el.setAttribute('role', 'status');
        el.setAttribute('aria-live', 'polite');
        document.body.appendChild(el);
      }
      el.textContent = String(message || '');
      if (el.classList) el.classList.add('is-open');
      if (__dhToastTimer) clearTimeout(__dhToastTimer);
      __dhToastTimer = setTimeout(function () {
        try { if (el && el.classList) el.classList.remove('is-open'); } catch (_) {}
      }, durationMs || 2600);
    } catch (_) {}
  }
  window.dhToast = dhToast;

  function dhCloseActiveSheet() {
    try {
      var sheet = document.getElementById('dh-native-sheet');
      if (sheet && typeof sheet.remove === 'function') {
        sheet.remove();
        return true;
      }
      if (window.DHSparkGame && typeof DHSparkGame.isOpen === 'function' && DHSparkGame.isOpen()) {
        DHSparkGame.close();
        return true;
      }
      var guide = document.getElementById('dh-sys-guide');
      if (guide && typeof guide.remove === 'function') {
        guide.remove();
        return true;
      }
    } catch (_) {}
    return false;
  }

  function dhPushSubView(viewName) {
    try {
      if (window.history && typeof window.history.pushState === 'function') {
        window.history.pushState({ dhSubView: String(viewName || 'sub') }, '');
      }
    } catch (_) {}
  }
  window.dhPushSubView = dhPushSubView;

  function dhOpenBottomSheet(opts) {
    opts = opts || {};
    try {
      if (!document || typeof document.createElement !== 'function' || !document.body || typeof document.body.appendChild !== 'function') return null;
      dhCloseActiveSheet();
      dhHaptic('light');
      dhPushSubView('sheet');
      var ov = document.createElement('div');
      ov.id = 'dh-native-sheet';
      ov.className = 'dh-sheet-ov';
      ov.setAttribute('dir', 'rtl');
      ov.setAttribute('role', 'dialog');
      ov.setAttribute('aria-modal', 'true');
      ov.innerHTML =
        '<div class="dh-sheet-panel" id="dh-native-sheet-panel">' +
          '<div class="dh-sheet-handle" aria-hidden="true"></div>' +
          (opts.title ? '<h2 class="dh-sheet-title">' + opts.title + '</h2>' : '') +
          (opts.bodyHtml || '') +
        '</div>';
      var dismiss = function () {
        try { ov.remove(); } catch (_) {}
      };
      ov.onclick = function (e) { if (e && e.target === ov) dismiss(); };
      document.body.appendChild(ov);

      // Native touch swipe-down to dismiss
      try {
        var panel = document.getElementById('dh-native-sheet-panel');
        var startY = 0;
        var deltaY = 0;
        if (panel && typeof panel.addEventListener === 'function') {
          panel.addEventListener('touchstart', function (ev) {
            if (panel.scrollTop > 0) { startY = 0; return; }
            startY = ev.touches && ev.touches[0] ? ev.touches[0].clientY : 0;
            deltaY = 0;
          }, { passive: true });
          panel.addEventListener('touchmove', function (ev) {
            if (!startY) return;
            var cur = ev.touches && ev.touches[0] ? ev.touches[0].clientY : 0;
            deltaY = Math.max(0, cur - startY);
            if (deltaY > 0) panel.style.transform = 'translateY(' + Math.min(deltaY, 260) + 'px)';
          }, { passive: true });
          panel.addEventListener('touchend', function () {
            if (deltaY > 95) {
              dismiss();
            } else if (panel) {
              panel.style.transform = '';
            }
            startY = 0;
            deltaY = 0;
          }, { passive: true });
        }
      } catch (_) {}

      if (typeof opts.onMount === 'function') opts.onMount(dismiss);
      return ov;
    } catch (_) {
      return null;
    }
  }
  window.dhOpenBottomSheet = dhOpenBottomSheet;

  var DAILY_SAVED_KEY = 'dh_daily_quote_saved_v1';
  var __dhQuoteCursor = 0;

  function loadSavedQuotes() {
    try { return JSON.parse(localStorage.getItem(DAILY_SAVED_KEY) || '[]'); } catch (_) { return []; }
  }
  function saveSavedQuotes(arr) {
    try { localStorage.setItem(DAILY_SAVED_KEY, JSON.stringify(arr)); } catch (_) {}
  }

  function renderHome() {
    try { shellScrollTop(); } catch (eS) {}

    ensureTabbar();
    setActiveTab('home');
    window.__dhInJourney = false;
    try { if (typeof saveSession === 'function') saveSession(); } catch (e) {}

    var quotesDeck = [];
    var fallbackQuotes = [
      { t: 'هیچ راهی به سوی موفقیت وجود ندارد، موفقیت خود یک راه است.', tag: 'وینستون چرچیل' },
      { t: 'شناخت دقیقِ آنچه به تو انرژی می‌دهد، مهم‌ترین قطب‌نمای زندگی است.', tag: 'نگاه فردیت' },
      { t: 'به جای تقلید از مسیر میانگین، راهی را بساز که با سرشت تو همخوان است.', tag: 'فلسفه اسب سیاه' }
    ];
    try {
      var rawBundle = getBundle() || [];
      for (var qi = 0; qi < rawBundle.length; qi++) {
        if (rawBundle[qi] && (rawBundle[qi].t || rawBundle[qi].text)) {
          quotesDeck.push({
            t: rawBundle[qi].t || rawBundle[qi].text,
            tag: rawBundle[qi].tag || rawBundle[qi].a || 'اسب سیاه'
          });
        }
      }
    } catch (e2) {}
    while (quotesDeck.length < 3) {
      quotesDeck.push(fallbackQuotes[quotesDeck.length % fallbackQuotes.length]);
    }
    quotesDeck = quotesDeck.slice(0, 3);

    var curQIdx = __dhQuoteCursor % quotesDeck.length;
    var quote = quotesDeck[curQIdx];
    var dateLabel = faDate();

    var root = $('app');
    if (!root) return;

    var base = '';
    try {
      if ((location.pathname || '').indexOf('/dark-horse-v2-') === 0) base = '/dark-horse-v2-/';
    } catch (e0) {}

    function ico(file) {
      return '<span class="dh-mk2-orb"><img src="' + base + file + '" alt="" width="24" height="24" decoding="async"></span>';
    }
    function feat(file) {
      return '<span class="dh-mk2-feat"><img src="' + base + file + '" alt="" loading="lazy" decoding="async"></span>';
    }

    /* Live deep-module preview metadata */
    var sparkPeek = { likedCount: 0, played: false };
    var storyPeek = { name: 'سوزان راجرز', index: 1, total: 8 };
    var poemPeek = { poet: 'مولوی', tag: 'خودشناسی', count: 64 };
    var parentPeek = { checked: 0, total: 5 };
    try { if (window.DHSparkGame && DHSparkGame.peek) sparkPeek = DHSparkGame.peek(); } catch (_) {}
    try { if (window.DHStories && DHStories.peek) storyPeek = DHStories.peek(); } catch (_) {}
    try { if (window.DHPoems && DHPoems.peek) poemPeek = DHPoems.peek(); } catch (_) {}
    try { if (window.DHParents && DHParents.peek) parentPeek = DHParents.peek(); } catch (_) {}

    var sparkBadgeText = sparkPeek.played && sparkPeek.likedCount > 0
      ? ('🔥 ' + sparkPeek.likedCount + ' جرقه کشف شد')
      : '۱٬۳۹۳ خرده‌انگیزه زنده';
    var storyBadgeText = 'روایت امروز: ' + escape(storyPeek.name);
    var poemBadgeText = escape(poemPeek.poet) + ' · ' + escape(poemPeek.tag);
    var parentBadgeText = parentPeek.checked > 0
      ? ('✓ ' + parentPeek.checked + ' از ' + parentPeek.total + ' عهد همراهی')
      : 'میثاق خانواده و نوجوان';

    var heroUrl = base + 'hero-journey.jpg';
    var heroUrl2x = base + 'hero-journey@2x.jpg';

    function buildDotsHtml(activeI) {
      var dHtml = '';
      for (var di = 0; di < quotesDeck.length; di++) {
        dHtml += '<i class="' + (di === activeI ? 'on' : '') + '"></i>';
      }
      return dHtml;
    }

    var isQuoteSaved = loadSavedQuotes().indexOf(quote.t) >= 0;

    root.innerHTML =
      '<div class="dh-home-wrap dh-mk2 dh-view-enter">' +
        /* ۱. هدر مجلل و باشکوه برند اسب سیاه */
        '<header class="dh-regal-brand" aria-label="هویت برند اسب سیاه">' +
          '<div class="dh-regal-crest">' +
            '<div class="dh-regal-crest-inner">' +
              '<img src="' + base + 'icon-192.png" srcset="' + base + 'icon-192.png 1x, ' + base + 'icon-512.png 2x, ' + base + 'icon-512.png 3x" alt="اسب سیاه" width="70" height="70" decoding="async">' +
            '</div>' +
          '</div>' +
          '<div class="dh-regal-en">DARK HORSE</div>' +
          '<div class="dh-regal-fa-row"><i></i><h1 class="dh-regal-fa">اسب سیاه</h1><i></i></div>' +
          '<p class="dh-regal-tagline">هدایت تحصیلی و انتخاب رشته بر اساس <strong class="dh-fardiyat">فردیت</strong></p>' +
        '</header>' +

        '<div class="dh-fardiyat-ticker" id="dh-fardiyat-ticker" aria-live="polite">' +
          '<span class="dh-fardiyat-ticker-dot" aria-hidden="true"></span>' +
          '<span id="dh-fardiyat-ticker-text" class="dh-ticker-in">مسیرت را با <strong class="dh-fardiyat">فردیت‌ات</strong> بساز</span>' +
        '</div>' +

        /* ۲. کارت سفر اکتشافی (فقط نشان ۲۳۰ رشته و شاخه) */
        '<section class="dh-mk2-hero">' +
          '<div class="dh-mk2-hero-bg" style="background-image:image-set(url(\'' + heroUrl + '\') 1x, url(\'' + heroUrl2x + '\') 2x);background-image:url(\'' + heroUrl + '\')"></div>' +
          '<div class="dh-mk2-hero-shade"></div>' +
          '<div class="dh-mk2-hero-body">' +
            '<div class="dh-mk2-hero-top">' +
              '<span class="dh-mk2-compass"><img src="' + base + 'ico-compass.svg" alt="" width="40" height="40" decoding="async"></span>' +
              '<div><div class="dh-mk2-hero-title">سفر اکتشافی</div>' +
              '<div class="dh-mk2-hero-sub">کشف رشته و شاخه بر اساس فردیت</div></div>' +
            '</div>' +
            '<div class="dh-hero-pills">' +
              '<span class="dh-hero-pill">۲۳۰ رشته و شاخه</span>' +
            '</div>' +
            '<button type="button" class="dh-mk2-cta" id="dh-start-journey">' +
              'شروع سفر <span>›</span></button>' +
          '</div></section>' +

        /* ۳. بلافاصله زیر سفر اکتشافی: انتخاب رشته با منطق سنجش */
        '<section class="dh-home-sanjesh-entry" aria-labelledby="dh-home-sanjesh-title">' +
          '<div class="dh-home-entry-top">' +
            '<span class="dh-home-entry-icon" aria-hidden="true">🎓</span>' +
            '<div><h2 id="dh-home-sanjesh-title">انتخاب رشته با منطق سنجش</h2>' +
            '<p>بررسی مستقل با داده‌های سنجش؛ بدون نیاز به تکمیل سفر اکتشافی.</p></div>' +
          '</div>' +
          '<button type="button" class="dh-home-sanjesh-toggle" id="dh-open-sanjesh" aria-controls="dh-home-sanjesh-panel" aria-expanded="false">ورود به بخش سنجش</button>' +
          '<div class="dh-home-sanjesh-panel" id="dh-home-sanjesh-panel" hidden>' +
            '<div class="dh-home-sanjesh-mount" id="dh-home-sanjesh-mount"></div>' +
          '</div>' +
        '</section>' +

        /* ۴. پیام روزانه در جایگاه استاندارد اپ‌های مدرن جهان (بین ناحیه تصمیم‌گیری و کاوش عمیق) */
        '<section class="dh-mk2-quote dh-daily-wisdom" id="dh-daily-wisdom" aria-label="پیام روزانه">' +
          '<div class="dh-mk2-quote-top">' +
            ico('ico-quill.svg') +
            '<span class="dh-mk2-quote-label">پیام روزانه</span>' +
            (dateLabel ? '<span class="dh-daily-date">' + escape(dateLabel) + '</span>' : '') +
            '<span class="dh-daily-dots" id="dh-daily-dots">' + buildDotsHtml(curQIdx) + '</span>' +
          '</div>' +
          '<div class="dh-daily-text-wrap" id="dh-daily-wrap">' +
            '<p class="dh-mk2-quote-text" id="dh-daily-text">' + escape(quote.t) + '</p>' +
          '</div>' +
          '<div class="dh-mk2-quote-foot">' +
            '<div class="dh-daily-actions">' +
              '<button type="button" class="dh-quote-share-btn" id="dh-next-quote" aria-label="پیام بعدی">پیام بعدی ↻</button>' +
              '<button type="button" class="dh-quote-share-btn' + (isQuoteSaved ? ' is-saved' : '') + '" id="dh-like-quote">' + (isQuoteSaved ? '♥ پسندیده شد' : '♡ پسندیدم') + '</button>' +
              '<button type="button" class="dh-quote-share-btn" id="dh-copy-quote">اشتراک ↗</button>' +
            '</div>' +
            '<div class="dh-mk2-quote-by" id="dh-daily-by">' + escape(quote.tag) + '</div>' +
          '</div></section>' +

        /* ۵. بخش‌های اصیل و عمیق اپ به فرم مدرن و تعاملی */
        '<section class="dh-mk2-more">' +
          '<div class="dh-mk2-sep"><i></i><span>کاوش عمیق‌تر در فردیت</span><i></i></div>' +
          '<button type="button" class="dh-mk2-row dh-mk2-row-hot" id="dh-open-spark">' +
            feat('spark-feature.jpg') +
            '<div class="dh-mk2-row-t">' +
              '<strong>جرقه‌یاب <span class="dh-bento-pill">' + sparkBadgeText + '</span></strong>' +
              '<span>آزمایشگاه زندهٔ کشف خرده‌انگیزه‌هایی که واقعاً به جانت انرژی می‌دهند</span>' +
            '</div>' +
            '<span class="dh-mk2-chev"><img src="' + base + 'ico-chevron.svg" alt="" width="18" height="18" decoding="async"></span></button>' +
          '<div class="dh-mk2-duo">' +
            '<button type="button" class="dh-mk2-tile" id="dh-open-stories">' +
              feat('stories-feature.jpg') +
              '<span class="dh-tile-live-pill">' + storyBadgeText + '</span>' +
              '<strong>داستان‌ها</strong><span>سرگذشت واقعی مسیرهای غیرخطی و اصیل</span></button>' +
            '<button type="button" class="dh-mk2-tile" id="dh-open-poems">' +
              feat('wisdom-feature.jpg') +
              '<span class="dh-tile-live-pill">' + poemBadgeText + '</span>' +
              '<strong>سخن بزرگان</strong><span>تأمل موضوعی در حکمت شاعران بزرگ</span></button></div>' +
          '<div class="dh-mk2-duo">' +
            '<button type="button" class="dh-mk2-tile" id="dh-open-parents">' +
              feat('parents-feature.jpg') +
              '<span class="dh-tile-live-pill">' + parentBadgeText + '</span>' +
              '<strong>والدین</strong><span>همراهی هوشمندانه به‌جای فشار مقایسه</span></button>' +
            '<button type="button" class="dh-mk2-tile" id="dh-open-guide">' +
              ico('ico-compass.svg') +
              '<span class="dh-tile-live-pill">سه لایه شناخت</span>' +
              '<strong>راهنمای سامانه</strong><span>فلسفهٔ انگیزه، راهبرد شخصی و ارزش بنیادین</span></button></div>' +
        '</section>' +

        '<section class="dh-sanjesh-box" id="dh-sanjesh-box">' +
          '<p class="dh-sanjesh-title">اخبار و اطلاع‌رسانی سازمان سنجش</p>' +
          '<p class="dh-sanjesh-desc">زمان‌بندی دفترچه، انتخاب رشته و اطلاعیه‌های رسمی را از پرتال سنجش دنبال کنید.</p>' +
          '<a class="dh-sanjesh-link" href="https://www.sanjesh.org" target="_blank" rel="noopener noreferrer">ورود به پرتال سازمان سنجش</a>' +
          '<p class="dh-sanjesh-note">تاریخ‌ها و جزئیات فقط از منبع رسمی سنجش معتبر است.</p>' +
        '</section>' +
        '</div>';


    function on(id, fn) { var el = $(id); if (el) el.onclick = fn; }
    try { startFardiyatTicker(); } catch (eTicker) {}

    on('dh-start-journey', function () {
      dhHaptic('light');
      startJourneyFromShell();
    });

    function paintDailyQuote() {
      var qNow = quotesDeck[__dhQuoteCursor % quotesDeck.length];
      var wrapEl = $('dh-daily-wrap');
      var tEl = $('dh-daily-text');
      var byEl = $('dh-daily-by');
      var dotsEl = $('dh-daily-dots');
      var likeEl = $('dh-like-quote');
      var applyNow = function () {
        if (tEl) tEl.textContent = qNow.t;
        if (byEl) byEl.textContent = qNow.tag;
        if (dotsEl) dotsEl.innerHTML = buildDotsHtml(__dhQuoteCursor % quotesDeck.length);
        if (likeEl) {
          var savedNow = loadSavedQuotes().indexOf(qNow.t) >= 0;
          likeEl.textContent = savedNow ? '♥ پسندیده شد' : '♡ پسندیدم';
          if (likeEl.classList) likeEl.classList.toggle('is-saved', savedNow);
        }
        if (wrapEl && wrapEl.classList) wrapEl.classList.remove('is-fading');
      };
      if (wrapEl && wrapEl.classList) {
        wrapEl.classList.add('is-fading');
        setTimeout(applyNow, 130);
      } else {
        applyNow();
      }
    }

    on('dh-next-quote', function () {
      dhHaptic('light');
      __dhQuoteCursor = (__dhQuoteCursor + 1) % quotesDeck.length;
      paintDailyQuote();
    });

    on('dh-like-quote', function () {
      dhHaptic('success');
      var qNow = quotesDeck[__dhQuoteCursor % quotesDeck.length];
      var list = loadSavedQuotes();
      var pos = list.indexOf(qNow.t);
      if (pos >= 0) {
        list.splice(pos, 1);
      } else {
        list.push(qNow.t);
        dhToast('پیام روزانه در برگزیده‌های تو ذخیره شد ✨');
      }
      saveSavedQuotes(list);
      paintDailyQuote();
    });

    on('dh-copy-quote', function () {
      dhHaptic('light');
      var qNow = quotesDeck[__dhQuoteCursor % quotesDeck.length];
      var qShare = '«' + qNow.t + '»\n— ' + qNow.tag + '\n\nاسب سیاه · https://asbe-siah.ir/';
      if (navigator.share) {
        navigator.share({ title: 'پیام روزانه · اسب سیاه', text: qShare }).catch(function () {});
        return;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(qShare).then(function () {
          dhToast('پیام روزانه کپی شد ✨ آماده اشتراک‌گذاری');
        }).catch(function () {});
      }
    });

    on('dh-open-sanjesh', function () {
      dhHaptic('light');
      var panel = $('dh-home-sanjesh-panel');
      var button = $('dh-open-sanjesh');
      if (!panel) return;
      var shouldOpen = !!panel.hidden;
      panel.hidden = !shouldOpen;
      if (button) {
        button.setAttribute('aria-expanded', String(shouldOpen));
        button.textContent = shouldOpen ? 'بستن بخش سنجش' : 'ورود به بخش سنجش';
      }
      if (shouldOpen) {
        dhPushSubView('sanjesh');
        var mount = $('dh-home-sanjesh-mount');
        if (mount && window.DHAdmissionChanceUI &&
            typeof window.DHAdmissionChanceUI.openHome === 'function') {
          window.DHAdmissionChanceUI.openHome('dh-home-sanjesh-mount');
        } else if (mount) {
          mount.textContent = 'بخش سنجش هنوز بارگذاری نشده است؛ صفحه را دوباره بارگذاری کنید.';
        }
        try {
          setTimeout(function () {
            if (panel && typeof panel.scrollIntoView === 'function') {
              panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          }, 80);
        } catch (eScroll) {}
      }
    });
    on('dh-open-spark', function () {
      dhHaptic('light');
      try { shellScrollTop(); } catch (eS) {}
      if (window.DHSparkGame && DHSparkGame.open) DHSparkGame.open();
      else dhToast('در حال آماده‌سازی جرقه‌یاب… یک لحظه دیگر امتحان کن.');
      try { setTimeout(shellScrollTop, 50); setTimeout(shellScrollTop, 200); } catch (eS2) {}
    });
    on('dh-open-stories', function () {
      dhHaptic('light');
      try { shellScrollTop(); } catch (eS) {}
      if (window.DHStories && DHStories.open) DHStories.open();
      else dhToast('در حال بارگذاری داستان‌ها…');
      try { setTimeout(shellScrollTop, 50); setTimeout(shellScrollTop, 200); } catch (eS2) {}
    });
    on('dh-open-poems', function () {
      dhHaptic('light');
      if (window.DHPoems && DHPoems.open) DHPoems.open();
      else dhToast('در حال بارگذاری سخن بزرگان…');
    });
    on('dh-open-parents', function () {
      dhHaptic('light');
      try { shellScrollTop(); } catch (eS) {}
      if (window.DHParents && DHParents.open) DHParents.open();
      else dhToast('در حال بارگذاری بخش والدین…');
      try { setTimeout(shellScrollTop, 50); setTimeout(shellScrollTop, 200); } catch (eS2) {}
    });
    on('dh-open-guide', function () {
      dhHaptic('light');
      try { shellScrollTop(); } catch (eS) {}
      dhPushSubView('guide');
      openSystemGuide();
      try { setTimeout(shellScrollTop, 50); setTimeout(shellScrollTop, 200); } catch (eS2) {}
    });
  }

  function authorizedCommercialJourneySessionId() {
    var authorized = '';
    var pending = '';
    try { authorized = String(window.__dhCommercialJourneyAuthorizedSessionId || ''); } catch (_) {}
    try { pending = String(localStorage.getItem('dh_pending_journey_session_id') || ''); } catch (_) {}
    return authorized && authorized === pending ? authorized : '';
  }

  async function startJourneyFromShell() {
    if (window.__dhJourneyStarting) return;
    var commercialRuntime = typeof window.dhHasCommercialRuntime !== 'function' || window.dhHasCommercialRuntime();
    var authorizedSessionId = authorizedCommercialJourneySessionId();
    if (commercialRuntime && !authorizedSessionId) {
      try {
        if (window.DHCommercialUI &&
            typeof window.DHCommercialUI.startServerAuthorizedJourney === 'function') {
          return window.DHCommercialUI.startServerAuthorizedJourney();
        }
      } catch (eGate) { console.warn('[DarkHorse][Journey] commercial start gate failed', eGate); }
      window.__dhInJourney = false;
      try { setActiveTab('home'); renderHome(); } catch (_) {}
      return;
    }
    if (authorizedSessionId && typeof state !== 'undefined' && state) state.sessionId = authorizedSessionId;
    var wasInJourney = Boolean(window.__dhInJourney);
    window.__dhJourneyStarting = true;

    try { shellScrollTop(); } catch (eS) {}

    // Lock the shell immediately so boot/profile timers cannot repaint Home
    // while the quota check or journey restoration is in progress.
    window.__dhInJourney = true;
    setActiveTab('journey');

    var root = $('app');
    if (root) {
      root.innerHTML =
        '<div class="card" style="margin:24px 0;text-align:center;">' +
          '<div style="font-size:1.8rem;margin-bottom:10px;">🧭</div>' +
          '<h2 style="color:#f0c040;margin:0 0 8px;">در حال آماده‌سازی سفر</h2>' +
          '<p style="color:#c9b896;margin:0;line-height:1.9;">داریم مسیرت را آماده می‌کنیم…</p>' +
        '</div>';
    }

    try {
      // The commercial gate already checked server quota and authorized this exact UUID.
      var allowed = commercialRuntime ? !!authorizedSessionId : canRunTest();
      var u = getDisplayUser();

      var quotaRefreshPromise = null;
      try {
        if (u && window.DHAuth &&
            typeof DHAuth.isLoggedIn === 'function' &&
            DHAuth.isLoggedIn() &&
            typeof DHAuth.quota === 'function') {
          quotaRefreshPromise = DHAuth.quota().catch(function (quotaError) {
            console.warn('[DarkHorse][Journey] quota refresh failed', quotaError);
            return null;
          });
          if (!allowed) {
            var quotaWait = await Promise.race([
              quotaRefreshPromise,
              new Promise(function (resolve) {
                setTimeout(function () { resolve(null); }, 2500);
              })
            ]);
            if (quotaWait) {
              var remaining = Number(quotaWait && quotaWait.credits_remaining);
              allowed = Number.isFinite(remaining) && remaining > 0;
            }
          } else {
            quotaRefreshPromise.catch(function (quotaError) {
              console.warn('[DarkHorse][Journey] background quota refresh failed', quotaError);
            });
          }
        }
      } catch (quotaError) {
        console.warn('[DarkHorse][Journey] quota refresh failed', quotaError);
      }

      if (!allowed) {
        window.__dhInJourney = false;
        setActiveTab('home');
        try { renderHome(); } catch (eHome) {}
        if (window.DHCommercialUI && typeof window.DHCommercialUI.showPurchase === 'function') {
          window.DHCommercialUI.showPurchase('اعتبار سفر اکتشافی شما به پایان رسیده است. برای شروع سفر جدید، بستهٔ اعتبار تهیه کنید.');
        }
        return;
      }

      if (wasInJourney && typeof saveSession === 'function') {
        try { saveSession(); } catch (e1) {}
      }
      if (typeof window.ensureJourneyDataLoaded === 'function') {
        try { await window.ensureJourneyDataLoaded(); } catch (eLoad) {}
      }

      var data = null;
      try {
        var raw = localStorage.getItem('darkhorse_session_v2');
        if (raw) data = JSON.parse(raw);
      } catch (e2) { data = null; }

      var storedResumeSessionId = data && data.sessionId ? String(data.sessionId) : '';
      var unfinished = data && !data.journeyFinished && data.stage &&
        ['splash', 'realm', 'subRealm', 'narrowPath', 'introSwipe', 'swipe',
         'introStrategies', 'strategies', 'introValues', 'values', 'choice'].indexOf(data.stage) >= 0 &&
        (!storedResumeSessionId || storedResumeSessionId === authorizedSessionId);

      if (unfinished) {
        // A paid/resumed journey must use the exact UUID charged by the server.
        var pendingResumeSessionId = null;
        try {
          pendingResumeSessionId = localStorage.getItem('dh_pending_journey_session_id');
          if (pendingResumeSessionId) {
            data.sessionId = String(pendingResumeSessionId);
            if (typeof state !== 'undefined' && state) state.sessionId = String(pendingResumeSessionId);
            localStorage.setItem('darkhorse_session_v2', JSON.stringify(data));
          }
        } catch (_) {}
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
          if (!state.stage || ['manifesto', 'guide', 'results'].indexOf(state.stage) >= 0) {
            state.stage = data.stage || 'splash';
          }
          if (state.stage === 'swipe' && typeof ensureSwipeDeckHydrated === 'function') {
            try { await ensureSwipeDeckHydrated(false); } catch (eDeck) {}
          }
        }
        var resumeY = Number((data && data.lastScrollY) || (typeof state !== 'undefined' && state && state.lastScrollY) || 0);
        if (typeof render === 'function') render({ preserveScroll: resumeY > 0 });
        if (resumeY > 0) {
          setTimeout(function () { try { window.scrollTo(0, resumeY); } catch (_) {} }, 40);
        }
        return;
      }

      // A fresh click on «سفر اکتشافی» enters the canonical City of Dreams
      // splash first; the splash action then advances into the realms.
      if (typeof fullResetState === 'function') {
        fullResetState(true);
      } else {
        try { localStorage.removeItem('darkhorse_session_v2'); } catch (e3) {}
      }
      // Fresh journey starts with the UUID already charged by the commercial gate.
      var pendingFreshSessionId = authorizedSessionId;
      if (pendingFreshSessionId && typeof state !== 'undefined' && state) {
        state.sessionId = String(pendingFreshSessionId);
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
      console.error('[DarkHorse][Journey] start failed', e);
      window.__dhInJourney = false;
      try { setActiveTab('home'); renderHome(); } catch (eHome) {}
      var msg = String(e && e.message ? e.message : e);
      if (/401|authentication/i.test(msg)) {
        if (window.DHCommercialUI && typeof window.DHCommercialUI.showAuth === 'function') {
          window.DHCommercialUI.showAuth('login');
        }
      } else if (window.DHCommercialUI && typeof window.DHCommercialUI.showPurchase === 'function') {
        window.DHCommercialUI.showPurchase('برای ورود به سفر اکتشافی، وضعیت اعتبار خود را بررسی کنید.');
      }
    } finally {
      window.__dhJourneyStarting = false;
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
      'https://asbe-siah.ir/\n' +
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
        url: 'https://asbe-siah.ir/'
      }).catch(function () {});
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        dhToast('نتیجه کپی شد ✨ آماده اشتراک‌گذاری');
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
    // همگام‌سازی اعتبار سرور (بدون بلاک UI)
    try {
      if (window.DHCommercialUI && typeof window.DHCommercialUI.syncQuota === 'function') {
        var now = Date.now();
        if (!window.__dh_quota_sync_at || (now - window.__dh_quota_sync_at) > 30000) {
          window.__dh_quota_sync_at = now;
          window.DHCommercialUI.syncQuota(function () {});
        }
      }
    } catch (_) {}

    try { shellScrollTop(); } catch (eS) {}

    ensureTabbar();
    setActiveTab('profile');
    window.__dhInJourney = false;
    var root = $('app');
    if (!root) return;
    var u = getDisplayUser();
    var q = localQuota();
    var last = loadLastResult();
    var dateStr = (typeof faDate === 'function') ? faDate() : '';
    var dateStr = (typeof faDate === 'function') ? faDate() : '';

    if (!u) {
      root.innerHTML =
        '<div class="dh-home-wrap">' +
        '<div class="card" style="text-align:right;margin-top:4px;">' +
        '<h2 style="text-align:center;color:#f0c040;">پروفایل</h2>' +
        '<p style="color:#c9b896;line-height:1.9;text-align:center;">برای حساب واقعی و پیامک تأیید از دکمه‌های زیر استفاده کنید.</p>' +
        '<button class="btn btn-primary" style="width:100%;margin-top:8px;" id="dh-p-register">ساخت حساب جدید (پیامک)</button>' +
        '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-login">ورود به حساب</button>' +
        '<div style="height:1px;background:rgba(255,255,255,.08);margin:16px 0;"></div>' +
        '<p style="color:#8f845f;line-height:1.8;font-size:.85rem;">اختیاری: ذخیره فقط روی همین دستگاه (بدون پیامک)</p>' +
        '<label style="display:block;margin:8px 0 4px;">نام</label>' +
        '<input id="dh-p-name" placeholder="مثلاً سارا" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">' +
        '<label style="display:block;margin:8px 0 4px;">موبایل</label>' +
        '<input id="dh-p-phone" inputmode="numeric" placeholder="09xxxxxxxxx" style="width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#12121c;color:#eee;font-size:16px;">' +
        '<p id="dh-p-err" style="color:#f66;min-height:1.2em;font-size:0.85rem;"></p>' +
        '<button class="btn" style="width:100%;" id="dh-p-save">ثبت پروفایل محلی</button>' +
        '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">خانه</button>' +
        '<div class="card" style="text-align:right;margin-top:12px;border:1px solid rgba(240,192,64,.25);"><h3 style="color:#f0c040;margin:0 0 8px;text-align:center;">پشتیبانی و ارتباط</h3><p style="color:#c9b896;line-height:1.9;font-size:.92rem;margin:0 0 12px;text-align:center;">برای راهنمایی، پیشنهاد و ارتباط با واحد سازنده به کانال رسمی اسب سیاه در ایتا بپیوندید.</p><a href="https://eitaa.com/asbe_siah" target="_blank" rel="noopener" class="btn btn-primary" style="display:block;width:100%;text-align:center;text-decoration:none;box-sizing:border-box;">عضویت در کانال ایتا</a><p style="color:#8f845f;font-size:.8rem;text-align:center;margin:10px 0 0;line-height:1.7;">آدرس کانال: eitaa.com/asbe_siah</p><div style="height:1px;background:rgba(255,255,255,.08);margin:14px 0;"></div><a href="privacy.html" style="display:block;text-align:center;color:#c4b896;font-size:.85rem;text-decoration:none;margin-bottom:6px;">حریم خصوصی</a><div id="enamad-seal" style="text-align:center;margin:18px 0 6px;"><p style="color:#c9b896;font-size:.8rem;margin:0 0 8px;">نماد اعتماد الکترونیکی</p><a referrerpolicy="origin" target="_blank" href="https://trustseal.enamad.ir/?id=7638931&Code=B04E6IpO9ivFnOcTrDySvqdKmiG011AS"><img referrerpolicy="origin" src="https://trustseal.enamad.ir/logo.aspx?id=7638931&Code=B04E6IpO9ivFnOcTrDySvqdKmiG011AS" alt="enamad" loading="lazy" decoding="async" style="cursor:pointer;max-width:125px;" code="B04E6IpO9ivFnOcTrDySvqdKmiG011AS"></a></div><p style="color:#6a6350;font-size:.75rem;text-align:center;margin:0;">اسب سیاه — نسخه ۱.۰.۱</p></div>' +
        '</div></div>';
      $('dh-p-home').onclick = function () { switchTab('home'); };
      var __dhAuthUiLoad = null;
      function reportAuthRuntimeError(phase, error) {
        var err = error instanceof Error ? error : new Error(String(error || 'unknown error'));
        try { console.error('[DarkHorse][AuthUI] ' + phase, err); } catch (_) {}
        var message = String(err.message || err || 'خطای ناشناخته');
        var host = document.getElementById('dh-p-auth-runtime-error');
        if (!host) {
          host = document.createElement('div');
          host.id = 'dh-p-auth-runtime-error';
          host.setAttribute('role', 'alert');
          host.style.cssText = 'margin:10px 0;padding:11px 13px;border-radius:10px;border:1px solid rgba(255,100,100,.42);background:rgba(120,20,20,.16);color:#ffb0b0;font-size:.8rem;line-height:1.8;text-align:right;';
          var card = document.querySelector('.dh-profile-v2') || document.querySelector('.dh-home-wrap') || document.getElementById('app');
          if (card) card.appendChild(host);
        }
        if (host) {
          host.textContent = 'خطای رابط ورود: ' + message + ' — دوباره تلاش کنید.';
          host.style.display = '';
        }
      }
      function loadCommercialAuthUi() {
        if (window.DHCommercialUI && typeof DHCommercialUI.showAuth === 'function') {
          return Promise.resolve();
        }
        if (__dhAuthUiLoad) return __dhAuthUiLoad;
        __dhAuthUiLoad = new Promise(function (resolve, reject) {
          var existing = document.getElementById('dh-commercial-ui-loader');
          if (existing) {
            if (existing.__dhReady) { resolve(); return; }
            existing.addEventListener('load', function () { resolve(); }, { once: true });
            existing.addEventListener('error', function () { reject(new Error('auth-ui-script-load-failed')); }, { once: true });
            return;
          }
          var script = document.createElement('script');
          var capturedError = null;
          var onWindowError = function (event) {
            if (event && event.error) capturedError = event.error;
          };
          script.id = 'dh-commercial-ui-loader';
          script.async = false;
          script.src = 'commercial_ui.js?v=46';
          script.setAttribute('data-dh-load-state', 'loading');
          window.addEventListener('error', onWindowError, true);
          function cleanup() {
            try { window.removeEventListener('error', onWindowError, true); } catch (_) {}
          }
          script.onload = function () {
            cleanup();
            if (window.DHCommercialUI && typeof DHCommercialUI.showAuth === 'function' && window.__dhCommercialUIReady) {
              script.__dhReady = true;
              script.setAttribute('data-dh-load-state', 'ready');
              resolve();
            } else {
              script.setAttribute('data-dh-load-state', 'failed');
              reject(capturedError || new Error('auth-ui-module-not-ready'));
            }
          };
          script.onerror = function () {
            cleanup();
            script.setAttribute('data-dh-load-state', 'failed');
            reject(capturedError || new Error('auth-ui-script-load-failed'));
          };
          document.head.appendChild(script);
        }).catch(function (error) {
          __dhAuthUiLoad = null;
          throw error;
        });
        return __dhAuthUiLoad;
      }
      var openAuth = function (mode) {
        try {
          if (!document || !document.body) throw new Error('auth-ui-dom-not-ready');
          if (window.DHCommercialUI && typeof DHCommercialUI.showAuth === 'function') {
            DHCommercialUI.showAuth(mode);
            return;
          }
        } catch (e) {
          reportAuthRuntimeError('showAuth initial call', e);
        }
        loadCommercialAuthUi().then(function () {
          try {
            if (!window.DHCommercialUI || typeof DHCommercialUI.showAuth !== 'function') {
              throw new Error('auth-ui-module-not-ready');
            }
            DHCommercialUI.showAuth(mode);
          } catch (e) {
            reportAuthRuntimeError('showAuth after module load', e);
          }
        }).catch(function (e) {
          reportAuthRuntimeError('commercial_ui dynamic load', e);
        });
      };
      var regBtn = $('dh-p-register');
      if (regBtn) regBtn.onclick = function () { openAuth('register'); };
      var loginBtn = $('dh-p-login');
      if (loginBtn) loginBtn.onclick = function () { openAuth('login'); };
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
    var remain;
    if (premium) {
      remain = '∞';
    } else if (q && typeof q.serverRemaining === 'number' && isFinite(q.serverRemaining)) {
      remain = String(Math.max(0, Math.floor(q.serverRemaining)));
    } else {
      remain = canRunTest() ? '1' : '0';
    }
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
      '<h2 class="dh-prof-display-name">' + escape(u.name) + '</h2>' +
      (dateStr ? '<p class="dh-prof-date">' + escape(dateStr) + '</p>' : '') +
      '<p style="text-align:center;color:#8a7a55;margin:6px 0 0;font-size:0.9rem;">' + escape(u.phone || '') + '</p>' +
      '<div class="dh-stat-grid">' +
        '<div class="dh-stat"><div class="n">' + escape(String(remain)) + '</div><div class="l">اکتشاف باقی</div></div>' +
        '<div class="dh-stat"><div class="n">' + (premium ? '✓' : String(used)) + '</div><div class="l">' + (premium ? 'اشتراک' : 'مصرف‌شده') + '</div></div>' +
      '</div>' +
      lastHtml +
      '<button class="btn btn-primary" style="width:100%;margin-top:14px;" id="dh-p-journey">' +
        (last && last.tops && last.tops.length ? 'سفر دوباره' : 'شروع اولین سفر') + '</button>' +
      (last && last.tops && last.tops.length ? '<button class="btn" style="width:100%;margin-top:8px;border-color:rgba(212,175,55,0.45);color:#f0c040;" id="dh-p-share">اشتراک‌گذاری نتیجه</button>' : '') +
      '<button class="btn btn-primary" style="width:100%;margin-top:8px;" id="dh-p-buy">خرید بسته ۳ تست</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-prem">' +
        (premium ? 'خاموش کردن اشتراک محلی' : 'اشتراک محلی آفلاین (تست)') + '</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;" id="dh-p-home">خانه</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;opacity:0.85;" id="dh-p-out">خروج از حساب</button>' +
      '<button class="btn" style="width:100%;margin-top:8px;color:#c08080;border-color:#543;" id="dh-p-exit">خروج از اپ</button>' +
      '<div class="card" style="text-align:right;margin-top:12px;border:1px solid rgba(240,192,64,.25);"><h3 style="color:#f0c040;margin:0 0 8px;text-align:center;">پشتیبانی و ارتباط</h3><p style="color:#c9b896;line-height:1.9;font-size:.92rem;margin:0 0 12px;text-align:center;">برای راهنمایی، پیشنهاد و ارتباط با واحد سازنده به کانال رسمی اسب سیاه در ایتا بپیوندید.</p><a href="https://eitaa.com/asbe_siah" target="_blank" rel="noopener" class="btn btn-primary" style="display:block;width:100%;text-align:center;text-decoration:none;box-sizing:border-box;">عضویت در کانال ایتا</a><p style="color:#8f845f;font-size:.8rem;text-align:center;margin:10px 0 0;line-height:1.7;">آدرس کانال: eitaa.com/asbe_siah</p><div style="height:1px;background:rgba(255,255,255,.08);margin:14px 0;"></div><a href="privacy.html" style="display:block;text-align:center;color:#c4b896;font-size:.85rem;text-decoration:none;margin-bottom:6px;">حریم خصوصی</a><div id="enamad-seal" style="text-align:center;margin:18px 0 6px;"><p style="color:#c9b896;font-size:.8rem;margin:0 0 8px;">نماد اعتماد الکترونیکی</p><a referrerpolicy="origin" target="_blank" href="https://trustseal.enamad.ir/?id=7638931&Code=B04E6IpO9ivFnOcTrDySvqdKmiG011AS"><img referrerpolicy="origin" src="https://trustseal.enamad.ir/logo.aspx?id=7638931&Code=B04E6IpO9ivFnOcTrDySvqdKmiG011AS" alt="enamad" loading="lazy" decoding="async" style="cursor:pointer;max-width:125px;" code="B04E6IpO9ivFnOcTrDySvqdKmiG011AS"></a></div><p style="color:#6a6350;font-size:.75rem;text-align:center;margin:0;">اسب سیاه — نسخه ۱.۰.۱</p></div>' +
      '</div></div>';

    $('dh-p-home').onclick = function () { switchTab('home'); };
    $('dh-p-journey').onclick = function () { startJourneyFromShell(); };
    var sh = $('dh-p-share');
    if (sh) sh.onclick = function () { shareLastResult(); };
    $('dh-p-out').onclick = function () {
      try {
        if (window.DHAuth && typeof window.DHAuth.logout === 'function') {
          window.DHAuth.logout();
        }
      } catch (_) {}
      try { localStorage.removeItem(LOCAL_USER_KEY); } catch (_) {}
      try { localStorage.removeItem('dh_local_user_v1'); } catch (_) {}
      try { localStorage.removeItem('dh_local_quota_v1'); } catch (_) {}
      try { localStorage.removeItem('dh_auth_v1'); } catch (_) {}
      try {
        if (window.DHCommercialUI && typeof window.DHCommercialUI.logout === 'function') {
          window.DHCommercialUI.logout();
          return;
        }
      } catch (_) {}
      try { renderProfile(); } catch (_) {}
      try { location.reload(); } catch (_) {}
    };
    var ex = $('dh-p-exit');
    if (ex) ex.onclick = function () { exitApp(); };
    var buyBtn = $('dh-p-buy');
    if (buyBtn) {
      buyBtn.onclick = function (ev) {
        if (ev) { try { ev.preventDefault(); ev.stopPropagation(); } catch (_) {} }
        var opened = false;
        try {
          if (window.DHCommercialUI && typeof window.DHCommercialUI.showPurchase === 'function') {
            window.DHCommercialUI.showPurchase();
            opened = true;
          }
        } catch (e1) { console.error(e1); }
        if (!opened) {
          try { window.dispatchEvent(new CustomEvent('dh-open-purchase')); opened = true; } catch (e2) {}
        }
        if (!opened) {
          dhToast('درگاه خرید در حال آماده‌سازی است؛ یک لحظه دیگر امتحان کنید.');
        }
      };
    }
    $('dh-p-prem').onclick = function () {
      var qq = localQuota();
      var lu = localUser();
      if (premium) {
        qq.premium = false;
        saveQuota(qq);
        if (lu) { lu.is_premium = false; saveLocalUser(lu); }
        dhToast('اشتراک آزمایشی محلی خاموش شد.');
      } else {
        qq.premium = true;
        saveQuota(qq);
        if (lu) { lu.is_premium = true; saveLocalUser(lu); }
        dhToast('اشتراک آزمایشی محلی فعال شد (فقط تست آفلاین).');
      }
      renderProfile();
    };
  }

  
  function shellScrollTop() {
    try {
      if (typeof window.scrollPageToTop === 'function') {
        window.scrollPageToTop();
        return;
      }
    } catch (e) {}
    try { window.scrollTo(0, 0); } catch (e2) {}
    try {
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      if (document.scrollingElement) document.scrollingElement.scrollTop = 0;
    } catch (e3) {}
    try {
      setTimeout(function () { try { window.scrollTo(0, 0); } catch (e4) {} }, 40);
    } catch (e5) {}
  }

  function switchTab(tab, opts) {
    dhHaptic('light');
    try { if (tab !== 'home') stopFardiyatTicker(); } catch (e) {}
    try { shellScrollTop(); } catch (eS) {}

    if (tab === 'home') {
      try { if (typeof saveSession === 'function') saveSession(); } catch (e) {}
      window.__dhInJourney = false;
      renderHome();
    }
    else if (tab === 'profile') {
      if (!opts || !opts.fromPopState) dhPushSubView('profile');
      renderProfile();
    }
    else if (tab === 'journey') startJourneyFromShell();
  }

  /* Android / Browser Hardware Back Button Handler for True Native App Navigation */
  try {
    if (!window.__dhPopStateBound && typeof window.addEventListener === 'function') {
      window.__dhPopStateBound = true;
      window.addEventListener('popstate', function () {
        if (dhCloseActiveSheet()) return;
        var sanjPanel = $('dh-home-sanjesh-panel');
        if (sanjPanel && !sanjPanel.hidden) {
          sanjPanel.hidden = true;
          var sanjBtn = $('dh-open-sanjesh');
          if (sanjBtn) {
            sanjBtn.setAttribute('aria-expanded', 'false');
            sanjBtn.textContent = 'ورود به بخش سنجش';
          }
          return;
        }
        if (window.__dhInJourney && typeof window.goBack === 'function') {
          window.goBack();
          return;
        }
        var root = $('app');
        if (root && root.querySelector && !root.querySelector('#dh-start-journey')) {
          renderHome();
        }
      });
    }
  } catch (_) {}

  function patchRender() {
    if (typeof window.render !== 'function' || window.__dhShellRenderPatched) return;
    var _render = window.render;
    window.render = function (opts) {
      if (!window.__dhInJourney && typeof state !== 'undefined') {
        renderHome();
        return;
      }
      _render(opts);
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
    if (window.__dhInJourney || window.__dhJourneyStarting) return;
    window.__dhInJourney = false;
    var root = $('app');
    if (!root || !root.querySelector || !root.querySelector('#dh-start-journey')) {
      renderHome();
    }
  }

  window.DHShell = {
    switchTab: switchTab,
    renderHome: renderHome,
    renderProfile: renderProfile,
    startJourney: startJourneyFromShell,
    openSanjesh: openSanjeshFromShell,
    setActiveTab: setActiveTab
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  setTimeout(boot, 0);
})();
