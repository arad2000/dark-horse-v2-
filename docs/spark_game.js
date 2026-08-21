/**
 * جرقه‌یاب + نشان افتخار (localStorage)
 * روی امتیاز سفر اصلی اثر ندارد.
 */
(function () {
  var BADGE_KEY = 'dh_spark_badges_v1';
  var DECK = [
    { t: 'وقتی چیزی را می‌سازم که کار می‌کند، انرژی می‌گیرم.', ok: true },
    { t: 'باید همان رشته‌ای را بخوانم که همه می‌گویند آینده دارد.', ok: false },
    { t: 'با کلمات و توضیح دادن به دیگران حال خوبی دارم.', ok: true },
    { t: 'رتبه‌ام تعریف کامل من است.', ok: false },
    { t: 'وقتی مشکل پیچیده را تکه‌تکه حل می‌کنم، زنده‌ام.', ok: true },
    { t: 'اگر با بقیه فرق داشته باشم، یعنی مسیرم اشتباه است.', ok: false },
    { t: 'کمک به یک نفر در لحظه سخت، برایم معنا دارد.', ok: true },
    { t: 'فقط وقتی موفق می‌شوم که از بقیه جلوتر باشم.', ok: false },
    { t: 'ایده‌های تصویری و زیبایی در ذهنم می‌جوشد.', ok: true },
    { t: 'باید اول مدرک بگیرم، بعد بفهمم کیستم.', ok: false },
    { t: 'کنجکاوی دربارهٔ «چرا» مرا جلو می‌برد.', ok: true },
    { t: 'نظر خانواده باید جای علاقهٔ من را بگیرد.', ok: false }
  ];

  var BADGE_DEFS = [
    { id: 'first_spark', title: 'اولین جرقه', desc: 'اولین بار جرقه‌یاب را تمام کردی', icon: '✦' },
    { id: 'clear_ear', title: 'گوش تیز', desc: 'حداقل ۳ جرقهٔ همسو با حداکثر ۱ جملهٔ تحت‌فشار', icon: '◎' },
    { id: 'self_listener', title: 'شنوندهٔ خود', desc: '۴ جرقه یا بیشتر بدون جملهٔ تحت‌فشار', icon: '◈' },
    { id: 'persistent', title: 'پافشار', desc: '۳ بار بازی را کامل کردی', icon: '△' },
    { id: 'speed_mind', title: 'ذهن چابک', desc: 'قبل از اتمام زمان، خودت نتیجه را زدی', icon: '⚡' }
  ];

  function $(id) { return document.getElementById(id); }

  function loadBadges() {
    try {
      return JSON.parse(localStorage.getItem(BADGE_KEY) || '{"earned":{},"plays":0}');
    } catch (e) {
      return { earned: {}, plays: 0 };
    }
  }

  function saveBadges(data) {
    try { localStorage.setItem(BADGE_KEY, JSON.stringify(data)); } catch (e) {}
  }

  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function award(state, id) {
    if (state.earned[id]) return false;
    state.earned[id] = { at: Date.now() };
    return true;
  }

  function badgeStrip(state) {
    return BADGE_DEFS.map(function (b) {
      var on = !!state.earned[b.id];
      return '<div class="dh-badge' + (on ? ' on' : '') + '" title="' + b.desc + '">' +
        '<span class="dh-badge-ico">' + b.icon + '</span>' +
        '<span class="dh-badge-t">' + b.title + '</span>' +
        '</div>';
    }).join('');
  }

  function renderSparkGame() {
    var root = $('app');
    if (!root) return;
    window.__dhInJourney = false;

    var cards = shuffle(DECK).slice(0, 8);
    var selected = {};
    var seconds = 45;
    var timer = null;
    var finished = false;
    var earlyFinish = false;
    var state = loadBadges();

    root.innerHTML =
      '<div class="dh-home-wrap dh-spark-wrap">' +
        '<button type="button" class="dh-back-link" id="dh-spark-back">← بازگشت به خانه</button>' +
        '<h2 class="dh-spark-title">جرقه‌یاب</h2>' +
        '<p class="dh-spark-desc">در <b>۴۵ ثانیه</b> جمله‌هایی را لمس کن که واقعاً به تو انرژی می‌دهند — نه انتظار دیگران.</p>' +
        '<div class="dh-badge-row">' + badgeStrip(state) + '</div>' +
        '<div class="dh-spark-bar"><div class="dh-spark-time" id="dh-spark-time">۴۵</div>' +
        '<div class="dh-spark-track"><i id="dh-spark-fill"></i></div></div>' +
        '<div class="dh-spark-grid" id="dh-spark-grid"></div>' +
        '<button class="btn btn-primary" id="dh-spark-done" style="width:100%;margin-top:12px;">تمام — نتیجه</button>' +
        '<p class="dh-spark-hint">بازی فقط گرم‌کردن است و روی نتیجهٔ سفر اصلی اثر ندارد.</p>' +
      '</div>';

    var grid = $('dh-spark-grid');
    cards.forEach(function (c, idx) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'dh-spark-card';
      btn.textContent = c.t;
      btn.onclick = function () {
        if (finished) return;
        if (selected[idx]) {
          delete selected[idx];
          btn.classList.remove('on');
        } else {
          selected[idx] = true;
          btn.classList.add('on');
        }
      };
      grid.appendChild(btn);
    });

    function tick() {
      seconds -= 1;
      var el = $('dh-spark-time');
      var fill = $('dh-spark-fill');
      if (el) el.textContent = String(Math.max(0, seconds));
      if (fill) fill.style.width = Math.max(0, (seconds / 45) * 100) + '%';
      if (seconds <= 0) finish(false);
    }
    timer = setInterval(tick, 1000);
    if ($('dh-spark-fill')) $('dh-spark-fill').style.width = '100%';

    function finish(fromButton) {
      if (finished) return;
      finished = true;
      earlyFinish = !!fromButton && seconds > 0;
      if (timer) clearInterval(timer);

      var hit = 0, miss = 0, picks = 0;
      cards.forEach(function (c, idx) {
        if (!selected[idx]) return;
        picks += 1;
        if (c.ok) hit += 1; else miss += 1;
      });

      state = loadBadges();
      state.plays = (state.plays || 0) + 1;
      var newly = [];
      if (award(state, 'first_spark')) newly.push('اولین جرقه');
      if (hit >= 3 && miss <= 1 && award(state, 'clear_ear')) newly.push('گوش تیز');
      if (hit >= 4 && miss === 0 && award(state, 'self_listener')) newly.push('شنوندهٔ خود');
      if (state.plays >= 3 && award(state, 'persistent')) newly.push('پافشار');
      if (earlyFinish && picks >= 2 && award(state, 'speed_mind')) newly.push('ذهن چابک');
      saveBadges(state);

      var msg;
      if (picks === 0) {
        msg = 'هنوز جرقه‌ای برنداشتی. در سفر اصلی عجله لازم نیست.';
      } else if (hit >= 3 && miss <= 1) {
        msg = 'خوب شنیدی خودت را. جرقه‌ها را از فشار جدا کردی.';
      } else if (miss > hit) {
        msg = 'بعضی انتخاب‌ها بیشتر شبیه انتظار دیگران بود. در سفر اصلی روی حس درونی تمرکز کن.';
      } else {
        msg = 'شروع خوبی است. در سفر اکتشافی دقیق‌تر می‌فهمی چه چیزی تو را زنده می‌کند.';
      }

      var newHtml = newly.length
        ? '<div class="dh-badge-new">نشان تازه: ' + newly.map(function (n) { return '«' + n + '»'; }).join(' · ') + '</div>'
        : '';

      root.innerHTML =
        '<div class="dh-home-wrap">' +
          '<h2 class="dh-spark-title">نتیجهٔ جرقه‌یاب</h2>' +
          '<div class="dh-spark-result">' +
            '<p><b>' + hit + '</b> جرقهٔ همسو · <b>' + miss + '</b> جملهٔ تحت‌فشار</p>' +
            '<p class="dh-spark-msg">' + msg + '</p>' +
            newHtml +
          '</div>' +
          '<div class="dh-badge-row" style="margin-top:14px;">' + badgeStrip(state) + '</div>' +
          '<button class="btn btn-primary" id="dh-spark-go" style="width:100%;margin-top:14px;">شروع سفر اکتشافی</button>' +
          '<button class="btn" id="dh-spark-again" style="width:100%;margin-top:8px;">بازی دوباره</button>' +
          '<button class="btn" id="dh-spark-home" style="width:100%;margin-top:8px;">خانه</button>' +
        '</div>';
      $('dh-spark-go').onclick = function () {
        if (window.DHShell && DHShell.startJourney) DHShell.startJourney();
      };
      $('dh-spark-again').onclick = function () { renderSparkGame(); };
      $('dh-spark-home').onclick = function () {
        if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
      };
    }

    $('dh-spark-done').onclick = function () { finish(true); };
    $('dh-spark-back').onclick = function () {
      if (timer) clearInterval(timer);
      if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
    };
  }

  window.DHSparkGame = {
    open: renderSparkGame,
    getBadges: loadBadges,
    defs: BADGE_DEFS
  };
})();
