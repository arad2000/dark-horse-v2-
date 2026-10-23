/**
 * اسب‌های سیاه واقعی — خلاصهٔ آموزشی تعاملی (بازنویسی، نه کپی متن کتاب)
 * منبع الهام: کتاب Dark Horse اثر Todd Rose و Ogi Ogas و روایت‌های عمومی آن‌ها
 * نمایش زنده: انتخاب مستقیم فصل + ورق زدن + تأمل شخصی تعاملی + اشتراک‌گذاری
 */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }

  var HORSES = [
    {
      name: 'سوزان راجرز',
      nameEn: 'Susan Rogers',
      role: 'مهندس صدا · استاد موسیقی و شناخت',
      lesson: 'جرقه را جدی بگیر؛ مسیر لازم نیست از اول کامل باشد.',
      body:
        'در شرایط سخت زندگی، موسیقی پناهگاهش بود. در یک کنسرت با خود عهد بست روزی پشت دستگاه صدا بایستد. ' +
        'بدون مسیر استاندارد دانشگاهی، قدم‌به‌قدم مهارت مهندسی صدا را ساخت و در نهایت با پرنس کار کرد — از جمله روی دورهٔ معروف Purple Rain. ' +
        'بعدتر، در میانسالی دوباره انتخاب کرد: به سراغ علم مغز و موسیقی رفت و استاد شد. ' +
        'درس: رضایت و مهارت می‌توانند مسیر را چندبار بازتعریف کنند؛ یک برچسب شغلی کافی نیست.',
      tip: 'اگر جرقه‌ات روشن است، لازم نیست از روز اول «رزومهٔ کامل» داشته باشی.'
    },
    {
      name: 'تی. وی. رامان',
      nameEn: 'T. V. Raman',
      role: 'دانشمند رایانه · دسترسی‌پذیری',
      lesson: 'محدودیت را با استراتژی شخصی دور بزن.',
      body:
        'رامان نابیناست. وقتی با مکعب روبیک روبه‌رو شد، به‌جای تقلید روش بیناها، راه خودش را ساخت: ' +
        'یک استراتژی لمسی و ساختاری که با توانمندی‌اش جور بود و توانست مکعب را حل کند. ' +
        'همین منطق — شناخت قوت و طراحی روش شخصی — در کار علمی‌اش در دسترس‌پذیری فناوری هم دیده می‌شود. ' +
        'درس: موفقیت کپیِ روش دیگران نیست؛ اغلب طراحی روش مناسبِ خودت است.',
      tip: 'به‌جای «مثل بقیه باش»، بپرس: من چطور می‌توانم این کار را به سبک خودم انجام دهم؟'
    },
    {
      name: 'جنی مک‌کورمیک',
      nameEn: 'Jennie McCormick',
      role: 'ستاره‌شناس آماتور · کاشف سیاره',
      lesson: 'کنجکاوی عملی، گاهی از مدرک جلو می‌زند.',
      body:
        'مسیر رسمی دانشگاهی ستاره‌شناسی را طی نکرده بود، اما با تلسکوپ و رصد مداوم جلو رفت. ' +
        'سال ۲۰۰۵ از رصدخانه‌ای در نیوزیلند سیاره‌ای را در سامانه‌ای دوردست کشف کرد — کاری که بسیاری فکر می‌کنند فقط از آزمایشگاه‌های بزرگ برمی‌آید. ' +
        'درس: تخصص می‌تواند از علاقهٔ پیگیر و تجربهٔ دستی رشد کند، نه فقط از مسیر کنکور و عنوان.',
      tip: 'اگر چیزی را عاشقانه تمرین می‌کنی، آن را کوچک نشمار — ممکن است هویت حرفه‌ای‌ات از همان‌جا شکل بگیرد.'
    },
    {
      name: 'تاد رز',
      nameEn: 'Todd Rose',
      role: 'نویسنده · پژوهشگر علم فردیت',
      lesson: 'شروع ضعیف، پایان داستان نیست.',
      body:
        'مسیر رسمی‌اش خطی نبود: ترک تحصیل، پدر شدن در نوجوانی، کار فروش. ' +
        'بعدتر به پژوهش دربارهٔ فردیت و «پایان میانگین» رسید و با پروژهٔ اسب سیاه، روایت موفقیت را از قالب یکسان خارج کرد. ' +
        'درس برای دانش‌آموز: یک کارنامه یا یک سال سخت، حکم ابدی هویت تو نیست.',
      tip: 'اگر الان در مسیر استاندارد گیر کرده‌ای، هنوز می‌توانی استراتژی خودت را بسازی.'
    },
    {
      name: 'اگی اوگاس',
      nameEn: 'Ogi Ogas',
      role: 'عصب‌شناس · نویسنده',
      lesson: 'رها کردن مسیر تکراری گاهی شروع واقعی است.',
      body:
        'چندبار ترک تحصیل و مسیرهای ناپایدار شغلی داشت؛ مدتی حتی با فروش کتاب دست‌دوم زندگی را می‌چرخاند. ' +
        'بعدتر در عصب‌شناسی و نویسندگی، با رز روی ایدهٔ اسب سیاه کار کرد. ' +
        'درس: تغییر مسیر نشانهٔ شکست نیست؛ گاهی اصلاح مسیر است.',
      tip: 'اگر چند بار «مسیر درست» را عوض کردی، شاید داری به فردیت نزدیک‌تر می‌شوی نه دورتر.'
    },
    {
      name: 'از کاخ سفید تا نظم شخصی',
      nameEn: 'White House → Organizer',
      role: 'تغییر شغل بر اساس انگیزه',
      lesson: 'پرستیژ بیرونی ≠ رضایت درونی.',
      body:
        'در کتاب از کسی گفته می‌شود که مسیر سیاسی نزدیک به قدرت را کنار گذاشت و به کاری روی آورد که با انگیزهٔ واقعی‌اش — نظم‌دادن و سامان‌بخشی — جور بود: سازمان‌دهی حرفه‌ای فضا و زندگی دیگران. ' +
        'درس: عنوان شغلی درخشان اگر با جرقه‌های تو نخواند، ممکن است خالی به نظر برسد.',
      tip: 'قبل از چسبیدن به «رشتهٔ باپرستیژ»، بپرس: من از چه کاری واقعاً انرژی می‌گیرم؟'
    },
    {
      name: 'از میز مدیر تا کار با دست',
      nameEn: 'Manager → Upholsterer',
      role: 'بازگشت به کار ملموس',
      lesson: 'کار با دست و نتیجهٔ دیدنی، برای بعضی‌ها سوخت اصلی است.',
      body:
        'نمونهٔ دیگری در کتاب، مدیری است که کار اداری را رها می‌کند تا با مواد و دست، روکش و تعمیر مبلمان انجام دهد — چون انگیزه‌اش ساختن و دیدن نتیجهٔ فیزیکی بود. ' +
        'درس: «شغل خوب» روی کاغذ با «شغل زنده برای تو» یکی نیست.',
      tip: 'اگر از کار تئوری خسته و از ساختن/تعمیر خوشحال می‌شوی، آن سیگنال را جدی بگیر.'
    },
    {
      name: 'چهار عنصر ذهنیت اسب سیاه',
      nameEn: 'Dark Horse Mindset',
      role: 'چارچوب شناخت فردیت',
      lesson: 'فردیت + رضایت ← شکوفایی و برتری',
      body:
        'خلاصهٔ آموزشی چارچوب کتاب: ۱) خرده‌انگیزه‌هایت را بشناس ۲) انتخاب‌هایت را فعالانه بساز ۳) استراتژی شخصی طراحی کن ۴) مقصد ثابت را شل کن و هدف عمیق را محکم بگیر. ' +
        'این اپ همان منطق را برای هدایت تحصیلی پیاده می‌کند: اول کشف، بعد پیشنهاد رشته — نه برعکس.',
      tip: 'سفر اکتشافی همین‌جاست تا جرقه‌ها و ارزش‌هایت را قبل از برچسب رشته ببینی.'
    }
  ];

  var REFLECTIONS = {
    spark: 'دقیقاً از همین‌جا شروع می‌شود: به جای این‌که بپرسی «بقیه کجا می‌روند؟»، یک کاری را که موقع انجامش زمان از دستت درمی‌رود جدی بگیر.',
    strategy: 'برگ برندهٔ اسب‌های سیاه همین است: مجبور نیستی به روش بقیه درس بخوانی یا کار کنی؛ روش شخصیِ متناسب با مغز خودت را بساز.',
    pivot: 'تغییر جهت در نوجوانی و جوانی شکست نیست؛ یعنی داری قطب‌نمای درونی‌ات را دقیق‌تر تنظیم می‌کنی.'
  };

  function dayIndex() {
    var d = new Date();
    return (d.getFullYear() * 372 + d.getMonth() * 31 + d.getDate()) % HORSES.length;
  }

  function loadCursor() {
    try {
      var raw = localStorage.getItem('dh_story_cursor_v1');
      if (!raw) return { day: dayIndex(), offset: 0 };
      var o = JSON.parse(raw);
      if (o.day !== dayIndex()) return { day: dayIndex(), offset: 0 };
      return o;
    } catch (e) {
      return { day: dayIndex(), offset: 0 };
    }
  }

  function saveCursor(c) {
    try { localStorage.setItem('dh_story_cursor_v1', JSON.stringify(c)); } catch (e) {}
  }

  function activeIndex() {
    var c = loadCursor();
    return ((c.day + c.offset) % HORSES.length + HORSES.length) % HORSES.length;
  }

  function currentHorse() {
    return HORSES[activeIndex()];
  }

  function renderStories() {
    var root = $('app');
    if (!root) return;
    window.__dhInJourney = false;
    var idx = activeIndex();
    var h = HORSES[idx];
    var n = idx + 1;

    var chaptersHtml = HORSES.map(function (item, i) {
      var on = i === idx ? ' is-active' : '';
      return '<button type="button" class="dh-mod-chip' + on + '" data-story-idx="' + i + '">' +
        (i + 1) + '. ' + item.name +
      '</button>';
    }).join('');

    root.innerHTML =
      '<div class="dh-home-wrap dh-stories-wrap dh-view-enter">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">' +
          '<button type="button" class="dh-back-link" id="dh-st-back">← بازگشت به صفحه اول</button>' +
          '<button type="button" class="dh-quote-share-btn" id="dh-st-share">اشتراک درس داستان ↗</button>' +
        '</div>' +

        '<div class="dh-mod-strip" id="dh-story-chapters" aria-label="فهرست داستان‌ها">' +
          chaptersHtml +
        '</div>' +

        '<div class="dh-story-live">' +
          '<div class="dh-story-live-top">' +
            '<span class="dh-story-pill">روایت‌های واقعی فردیت</span>' +
            '<span class="dh-story-count">' + n + ' از ' + HORSES.length + '</span>' +
          '</div>' +
          '<div class="dh-story-hero">' +
            '<div class="dh-story-name">' + h.name + '</div>' +
            '<div class="dh-story-en">' + h.nameEn + '</div>' +
            '<div class="dh-story-role">' + h.role + '</div>' +
            '<p class="dh-story-lesson">«' + h.lesson + '»</p>' +
            '<p class="dh-story-body">' + h.body + '</p>' +
            '<div class="dh-story-tip"><b>تلنگر برای مسیر تو:</b> ' + h.tip + '</div>' +
          '</div>' +

          '<div class="dh-mod-reflect">' +
            '<div class="dh-mod-reflect-title">کدام بخش این روایت به حالِ الان تو نزدیک‌تر است؟</div>' +
            '<div class="dh-mod-reflect-btns" id="dh-st-reflect-btns">' +
              '<button type="button" class="dh-mod-pill" data-ref="spark">🔥 جدی گرفتن جرقه‌ام</button>' +
              '<button type="button" class="dh-mod-pill" data-ref="strategy">🧭 ساختن روش شخصی خودم</button>' +
              '<button type="button" class="dh-mod-pill" data-ref="pivot">🌱 ترس نداشتن از تغییر مسیر</button>' +
            '</div>' +
            '<p class="dh-mod-reflect-ans" id="dh-st-reflect-ans" hidden></p>' +
          '</div>' +

          '<div class="dh-story-actions">' +
            '<button type="button" class="btn" id="dh-st-prev" style="flex:0.7;">‹ قبلی</button>' +
            '<button type="button" class="btn btn-primary" id="dh-st-next" style="flex:1.1;">داستان بعدی ›</button>' +
            '<button type="button" class="btn" id="dh-st-go" style="flex:1;">شروع سفر</button>' +
          '</div>' +
          '<p class="dh-story-foot">بازنویسی آموزشی با الهام از کتاب و مصاحبه‌های عمومی نویسندگان — متن کتاب کپی نشده است.</p>' +
        '</div>' +
        '<button type="button" class="btn" id="dh-st-home" style="width:100%;margin-top:10px;">صفحه اول</button>' +
      '</div>';

    $('dh-st-back').onclick = function () {
      if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
    };
    $('dh-st-home').onclick = function () {
      if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
    };
    $('dh-st-go').onclick = function () {
      if (window.DHShell && DHShell.startJourney) DHShell.startJourney();
    };
    $('dh-st-prev').onclick = function () {
      if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
      var cur = loadCursor();
      cur.offset = (cur.offset - 1 + HORSES.length) % HORSES.length;
      saveCursor(cur);
      renderStories();
    };
    $('dh-st-next').onclick = function () {
      if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
      var cur = loadCursor();
      cur.offset = (cur.offset + 1) % HORSES.length;
      saveCursor(cur);
      renderStories();
    };
    $('dh-st-share').onclick = function () {
      if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
      var txt = 'روایت «' + h.name + '» — اسب سیاه\n«' + h.lesson + '»\n' + h.tip + '\nhttps://asbe-siah.ir/';
      if (navigator.share) {
        navigator.share({ title: h.name, text: txt }).catch(function () {});
        return;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(function () {
          if (typeof window.dhToast === 'function') window.dhToast('درس داستان کپی شد ✨');
        }).catch(function () {});
      }
    };

    var chStrip = $('dh-story-chapters');
    if (chStrip) {
      chStrip.onclick = function (ev) {
        var btn = ev.target && ev.target.closest ? ev.target.closest('[data-story-idx]') : null;
        if (!btn) return;
        if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
        var targetIdx = parseInt(btn.getAttribute('data-story-idx'), 10);
        if (!isNaN(targetIdx)) {
          var d = dayIndex();
          saveCursor({ day: d, offset: (targetIdx - d + HORSES.length) % HORSES.length });
          renderStories();
        }
      };
    }

    var refBox = $('dh-st-reflect-btns');
    if (refBox) {
      refBox.onclick = function (ev) {
        var btn = ev.target && ev.target.closest ? ev.target.closest('[data-ref]') : null;
        if (!btn) return;
        if (typeof window.dhHaptic === 'function') window.dhHaptic('success');
        var key = btn.getAttribute('data-ref');
        refBox.querySelectorAll('.dh-mod-pill').forEach(function (p) {
          p.classList.toggle('is-active', p === btn);
        });
        var ans = $('dh-st-reflect-ans');
        if (ans && REFLECTIONS[key]) {
          ans.hidden = false;
          ans.textContent = '✨ ' + REFLECTIONS[key];
        }
      };
    }
  }

  window.DHStories = {
    open: function (opts) {
      if (!opts || !opts.fromPopState) {
        if (typeof window.dhPushSubView === 'function') window.dhPushSubView('stories');
      }
      renderStories();
    },
    peek: function () {
      var h = currentHorse();
      return { name: h.name, lesson: h.lesson, index: activeIndex() + 1, total: HORSES.length };
    },
    list: HORSES
  };
})();
