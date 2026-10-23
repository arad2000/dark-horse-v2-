/**
 * سخنی با والدین — میثاق اسب سیاه در برابر استانداردسازی (نسخهٔ تعاملی عمیق)
 */
(function () {
  'use strict';

  var PACT_KEY = 'dh_parent_pact_v1';

  function $(id) { return document.getElementById(id); }

  var SCENARIOS = [
    {
      title: 'بعد از دیدن کارنامه یا نتیجه آزمون',
      standard: '«ببین فلانی چه رتبه‌ای آورده! با این تراز اصلاً به رشته‌های خوب نمی‌رسی.» ← نتیجه: پنهان‌کاری، اضطراب و خاموش شدن انگیزهٔ درونی.',
      darkhorse: '«خسته نباشی عزیزم. از بین درس‌ها یا کارهای این هفته، کجا حس کردی ذهنت واقعاً روشن و کنجکاو بود؟ بیا از همان نقطه تقویتش کنیم.» ← نتیجه: امنیت روانی و خودانگیختگی.'
    },
    {
      title: 'وقتی فرزند بین علاقه و رشتهٔ پرطرفدار مردد است',
      standard: '«علاقه نون و آب نمی‌شه؛ فقط برو رشته‌ای که همه می‌گن پرستیژ داره.» ← نتیجه: سال‌ها فرسودگی در مسیری که با فردیتش بیگانه است.',
      darkhorse: '«بیا اول در اسب سیاه جرقه‌ها و ارزش‌هایت را دقیق بشناسیم، بعد با دادهٔ واقعی بازار کار و سنجش کنار هم بگذاریم تا هم رضایت داشته باشی هم آیندهٔ محکم.»'
    },
    {
      title: 'وقتی نوجوان احساس سردرگمی یا تغییر نظر دارد',
      standard: '«تو هر روز یه حرف می‌زنی! هنوز تکلیفت با خودت مشخص نیست.» ← نتیجه: ترس از کشف و چسبیدن کورکورانه به اولین انتخاب اشتباه.',
      darkhorse: '«طبیعیه که در این سن در حال کشف خودت باشی. تغییر نگاه یعنی داری خودت رو دقیق‌تر می‌شناسی؛ من کنارتم تا آگاهانه انتخاب کنی.»'
    }
  ];

  var PACT_ITEMS = [
    { bold: 'سؤال را عوض می‌کنم:', rest: 'به‌جای «چند درصد شدی؟» می‌پرسم «امروز از کدام کار انرژی گرفتی؟»' },
    { bold: 'نتیجهٔ اپ را قطب‌نما می‌بینم نه حکم:', rest: 'از خروجی همخوانی برای شروع گفت‌وگو استفاده می‌کنم، نه تحمیل.' },
    { bold: 'فشار مقایسه را کنار می‌گذارم:', rest: 'نسخهٔ زندگی دیگران، نقشهٔ فرزند من نیست.' },
    { bold: 'فضای امن برای رشد می‌سازم:', rest: 'هویت فرزندم با یک آزمون یا اصلاح مسیر آسیب نمی‌بیند.' },
    { bold: 'همراه می‌مانم، نه فرمانده:', rest: 'اجازه می‌دهم خودش سفر اکتشافی را با صداقت طی کند.' }
  ];

  var activeScenario = 0;

  function loadPact() {
    try { return JSON.parse(localStorage.getItem(PACT_KEY) || '[]'); } catch (e) { return []; }
  }
  function savePact(arr) {
    try { localStorage.setItem(PACT_KEY, JSON.stringify(arr)); } catch (e) {}
  }

  function renderParents() {
    var root = $('app');
    if (!root) return;
    window.__dhInJourney = false;

    var checked = loadPact();
    var sc = SCENARIOS[activeScenario % SCENARIOS.length];

    var scTabs = SCENARIOS.map(function (item, idx) {
      return '<button type="button" class="dh-mod-chip' + (idx === activeScenario ? ' is-active' : '') + '" data-sc-idx="' + idx + '">' +
        'موقعیت ' + (idx + 1) +
      '</button>';
    }).join('');

    var pactHtml = PACT_ITEMS.map(function (p, idx) {
      var on = checked.indexOf(idx) >= 0;
      return '<li class="dh-pact-item' + (on ? ' is-checked' : '') + '" data-pact-idx="' + idx + '">' +
        '<span class="dh-pact-box" aria-hidden="true">' + (on ? '✓' : '') + '</span>' +
        '<div><b>' + p.bold + '</b> ' + p.rest + '</div>' +
      '</li>';
    }).join('');

    root.innerHTML =
      '<div class="dh-home-wrap dh-parents-wrap dh-view-enter">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">' +
          '<button type="button" class="dh-back-link" id="dh-par-back">← بازگشت به صفحه اول</button>' +
          '<span class="dh-story-count">میثاق خانواده · ' + checked.length + ' از ' + PACT_ITEMS.length + '</span>' +
        '</div>' +
        '<h2 class="dh-par-title">سخنی با والدین</h2>' +
        '<p class="dh-par-lead">این بخش برای پدر و مادر است — نه برای فشار بیشتر روی فرزند، بلکه برای تبدیل نگرانیِ دلسوزانه به همراهیِ هوشمندانه.</p>' +

        '<div class="dh-par-card warn">' +
          '<h3>میثاق استانداردسازی</h3>' +
          '<p>وقتی موفقیت را فقط با رتبه، رشتهٔ «باپرستیژ» و مقایسه با بقیه تعریف می‌کنیم، فرزند یاد می‌گیرد خودِ واقعی‌اش را پنهان کند. فشار مداوم، اضطراب می‌سازد نه انگیزهٔ پایدار.</p>' +
        '</div>' +

        '<div class="dh-par-card good">' +
          '<h3>میثاق اسب سیاه</h3>' +
          '<p>اسب‌های سیاه کسانی‌اند که مسیر متناسب با خودشان را پیدا کردند؛ نه مسیر میانگین. راهنمایی واقعی یعنی کمک کنیم نوجوان بفهمد چه چیزی به او انرژی می‌دهد و مسیر تحصیلی‌اش را بر همان اساس بسازد.</p>' +
        '</div>' +

        '<div class="dh-par-card">' +
          '<h3>تمرین تعاملی: تغییر یک جمله در خانه</h3>' +
          '<div class="dh-mod-strip" id="dh-par-scenarios" style="margin:8px 0 10px;">' + scTabs + '</div>' +
          '<div style="font-size:.86rem;font-weight:800;color:#ffe08a;margin-bottom:8px;">' + sc.title + '</div>' +
          '<div class="dh-sc-box dh-sc-box--bad"><strong>واکنش کلیشه‌ای:</strong> ' + sc.standard + '</div>' +
          '<div class="dh-sc-box dh-sc-box--good"><strong>گفت‌وگوی اسب سیاه:</strong> ' + sc.darkhorse + '</div>' +
        '</div>' +

        '<div class="dh-par-card">' +
          '<h3>پنج عهد همراهی والدین (لمس کنید و انتخاب کنید)</h3>' +
          '<ul class="dh-pact-list" id="dh-pact-list">' + pactHtml + '</ul>' +
        '</div>' +

        '<div class="dh-par-card">' +
          '<h3>چطور از این سامانه استفاده کنید؟</h3>' +
          '<p>بگذارید فرزند خودش با آرامش سفر اکتشافی را طی کند. بعد از دیدن نتیجه، با کنجکاوی دربارهٔ جرقه‌ها و ارزش‌هایش گفت‌وگو کنید — نه اینکه به‌جای او تیک بزنید.</p>' +
        '</div>' +

        '<button class="btn btn-primary" id="dh-par-share" style="width:100%;margin-top:8px;">اشتراک‌گذاری این منشور با والدین دیگر ↗</button>' +
        '<button class="btn" id="dh-par-home" style="width:100%;margin-top:8px;">خانه</button>' +
      '</div>';

    var shareText =
      'سخنی با والدین — از سامانه اسب سیاه\n\n' +
      'به‌جای فشار رتبه و مقایسه، کمک کنیم فرزند بفهمد چه چیزی به او انرژی می‌دهد.\n' +
      'استانداردسازی می‌پرسد «چقدر شبیه میانگین هستی؟»\n' +
      'فردیت می‌پرسد «چه چیزی تو را زنده می‌کند؟»\n\n' +
      'https://asbe-siah.ir/';

    $('dh-par-back').onclick = function () {
      if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
    };
    $('dh-par-home').onclick = function () {
      if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
    };
    $('dh-par-share').onclick = function () {
      if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
      if (navigator.share) {
        navigator.share({ title: 'سخنی با والدین · اسب سیاه', text: shareText }).catch(function () {});
        return;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(shareText).then(function () {
          if (typeof window.dhToast === 'function') {
            window.dhToast('متن کپی شد ✨ آماده ارسال در گروه والدین');
          }
        }).catch(function () {
          prompt('متن را کپی کنید:', shareText);
        });
      } else {
        prompt('متن را کپی کنید:', shareText);
      }
    };

    var scStrip = $('dh-par-scenarios');
    if (scStrip) {
      scStrip.onclick = function (ev) {
        var btn = ev.target && ev.target.closest ? ev.target.closest('[data-sc-idx]') : null;
        if (!btn) return;
        if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
        activeScenario = parseInt(btn.getAttribute('data-sc-idx'), 10) || 0;
        renderParents();
      };
    }

    var pactList = $('dh-pact-list');
    if (pactList) {
      pactList.onclick = function (ev) {
        var li = ev.target && ev.target.closest ? ev.target.closest('[data-pact-idx]') : null;
        if (!li) return;
        if (typeof window.dhHaptic === 'function') window.dhHaptic('success');
        var idx = parseInt(li.getAttribute('data-pact-idx'), 10);
        var arr = loadPact();
        var pos = arr.indexOf(idx);
        if (pos >= 0) arr.splice(pos, 1);
        else arr.push(idx);
        savePact(arr);
        renderParents();
      };
    }
  }

  window.DHParents = {
    open: function (opts) {
      if (!opts || !opts.fromPopState) {
        if (typeof window.dhPushSubView === 'function') window.dhPushSubView('parents');
      }
      renderParents();
    },
    peek: function () {
      return { checked: loadPact().length, total: PACT_ITEMS.length };
    }
  };
})();
