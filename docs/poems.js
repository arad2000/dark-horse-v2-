/**
 * سخن بزرگان — ابیات کلاسیک و معاصر فارسی (مالکیت عمومی)
 * نسخهٔ تعاملی: فیلتر موضوعی زنده + ذخیرهٔ بیت محبوب + کپی ۱ کلیک + ورق زدن نرم
 */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }

  var VERSES = [
    /* مولوی */
    { poet: 'مولوی', tag: 'خودشناسی', lines: ['ای برادر تو همان اندیشه‌ای', 'مابقی خود استخوان و ریشه‌ای'] },
    { poet: 'مولوی', tag: 'حرکت', lines: ['از کجا آمده‌ام آمدنم بهر چه بود', 'به کجا می‌روم آخر ننمایی وطنم'] },
    { poet: 'مولوی', tag: 'یادگیری', lines: ['هر که را نبود به دانش اشتها', 'مرگ به زان زندگی بر وی روا'] },
    { poet: 'مولوی', tag: 'صبر', lines: ['صبر و ظفر هر دو دوستان قدیم‌اند', 'بر اثر صبر نوبت ظفر آید'] },
    { poet: 'مولوی', tag: 'راه', lines: ['تو پای به راه در نه و هیچ مپرس', 'خود راه بگویدت که چون باید رفت'] },
    { poet: 'مولوی', tag: 'معنا', lines: ['آینهٔ جان نیست الا روی دوست', 'روی آن یاری که باشد آینه‌اش'] },
    { poet: 'مولوی', tag: 'تلاش', lines: ['آب کم جو تشنگی آور به دست', 'تا بجوشد آبت از بالا و پست'] },
    { poet: 'مولوی', tag: 'درون', lines: ['خویش را تأویل کن نه ذکر را', 'خویش را معنی کن نه ذکر را'] },
    { poet: 'مولوی', tag: 'عشق به دانستن', lines: ['علم رسمی سر به سر قال است و قیل', 'نه از آن قال و قیل آید ای رحیل'] },
    { poet: 'مولوی', tag: 'رشد', lines: ['مرغ باغ ملکوتم نیم از عالم خاک', 'چند روزی قفسی ساخته‌اند از بدنم'] },

    /* حافظ */
    { poet: 'حافظ', tag: 'هوشیاری', lines: ['با خرابات‌نشینان ز کرامات ملاف', 'هر سخن وقتی و هر نکته مکانی دارد'] },
    { poet: 'حافظ', tag: 'صداقت', lines: ['آسایش دو گیتی تفسیر این دو حرف است', 'با دوستان مروت با دشمنان مدارا'] },
    { poet: 'حافظ', tag: 'زمان', lines: ['در کار گلاب و گل حکم ازلی این بود', 'کاین شاهد بازاری وان پرده‌نشین باشد'] },
    { poet: 'حافظ', tag: 'تلاش', lines: ['همت اگر سلسلهٔ جنبان شود', 'مور تواند که سلیمان شود'] },
    { poet: 'حافظ', tag: 'خویشتن', lines: ['خود را مبین که یار نبیند به هیچ رو', 'آن را که دیده بر رخ زیبا نمی‌کند'] },
    { poet: 'حافظ', tag: 'امید', lines: ['یوسف گم‌گشته بازآید به کنعان غم مخور', 'کلبهٔ احزان شود روزی گلستان غم مخور'] },
    { poet: 'حافظ', tag: 'ادب جان', lines: ['غلام همت آنم که زیر چرخ کبود', 'ز هر چه رنگ تعلق پذیرد آزاد است'] },
    { poet: 'حافظ', tag: 'اندیشه', lines: ['بشنو این نکته که خود را ز غم آزاده کنی', 'خون خود را گر به این نکته بدانی ببری'] },
    { poet: 'حافظ', tag: 'انتخاب', lines: ['برو این دام بر مرغ دگر نه', 'که عنقا را بلند است آشیانه'] },
    { poet: 'حافظ', tag: 'صبر', lines: ['زمانه گر بزند آتشم به خرمن عمر', 'بگو بسوز که بر من به برگ کاهی نیست'] },

    /* سعدی */
    { poet: 'سعدی', tag: 'انسانیت', lines: ['بنی‌آدم اعضای یکدیگرند', 'که در آفرینش ز یک گوهرند'] },
    { poet: 'سعدی', tag: 'یادگیری', lines: ['توانا بود هر که دانا بود', 'ز دانش دل پیر برنا بود'] },
    { poet: 'سعدی', tag: 'عمل', lines: ['دو چیز طیرهٔ عقل است دم فروبستن', 'به وقت گفتن و گفتن به وقت خاموشی'] },
    { poet: 'سعدی', tag: 'تلاش', lines: ['نابرده رنج گنج میسر نمی‌شود', 'مزد آن گرفت جان برادر که کار کرد'] },
    { poet: 'سعدی', tag: 'ادب', lines: ['تکیه بر جای بزرگان نتوان زد به گزاف', 'مگر اسباب بزرگی همه آماده کنی'] },
    { poet: 'سعدی', tag: 'خویش', lines: ['به راه بادیه رفتن به از نشستن باطل', 'که گر مراد نیابم به قدر وسع بکوشم'] },
    { poet: 'سعدی', tag: 'سخن', lines: ['کم گوی و گزیده گوی چون در', 'تا ز اندک تو جهان شود پر'] },
    { poet: 'سعدی', tag: 'دوستی دانش', lines: ['علم چندان که بیشتر خوانی', 'چون عمل در تو نیست نادانی'] },
    { poet: 'سعدی', tag: 'صبر', lines: ['صبر ایوب بباید که به گنج برسی', 'ورنه این راه پر از بیم و خطر می‌آید'] },
    { poet: 'سعدی', tag: 'هدف', lines: ['اگر باشی و اگر نه چه غم ما را از آن', 'که نیستیم به جز قطره‌ای از دریایی'] },

    /* فردوسی */
    { poet: 'فردوسی', tag: 'خرد', lines: ['خرد چشم جان است چون بنگری', 'تو بی‌چشم شادان جهان نسپری'] },
    { poet: 'فردوسی', tag: 'دانایی', lines: ['ز دانش به اندر جهان هیچ نیست', 'به از نیک‌نامی که جاوید زیست'] },
    { poet: 'فردوسی', tag: 'تلاش', lines: ['بکوشید و خوب و بد خویش را', 'بجویید و راز جهان پیش را'] },
    { poet: 'فردوسی', tag: 'میهن و معنا', lines: ['چو ایران نباشد تن من مباد', 'بدین بوم و بر زنده یک تن مباد'] },
    { poet: 'فردوسی', tag: 'پند', lines: ['به دانش گرای و بدو شو بلند', 'که بر دانش افسر بود بی‌گزند'] },
    { poet: 'فردوسی', tag: 'زمان', lines: ['زمانه زمانهٔ توست ای پسر', 'همان به که باشی به دانش پدر'] },
    { poet: 'فردوسی', tag: 'راستی', lines: ['مبادا که گردی به گیتی بلند', 'مگر آن که باشی به داد ارجمند'] },
    { poet: 'فردوسی', tag: 'کار', lines: ['به رنج اندر آری تنت را رواست', 'که رنج تو را گنج پیروزه‌است'] },

    /* خیام */
    { poet: 'خیام', tag: 'لحظه', lines: ['این قافلهٔ عمر عجب می‌گذرد', 'دریاب دمی که با طرب می‌گذرد'] },
    { poet: 'خیام', tag: 'آگاهی', lines: ['اسرار ازل را نه تو دانی و نه من', 'وین حرف معما نه تو خوانی و نه من'] },
    { poet: 'خیام', tag: 'ساده زیستن', lines: ['برخیز و بیا بتا برای دل ما', 'حل کن به جمال خویش مشکل ما'] },
    { poet: 'خیام', tag: 'فرصت', lines: ['فردا که از این قفس آزاد شوی', 'زین دام جهان به کام دل شاد شوی'] },
    { poet: 'خیام', tag: 'اندیشه', lines: ['چون نیست مقام ما در این دهر مقیم', 'پس بی می و معشوق خطایی‌ست عظیم'] },
    { poet: 'خیام', tag: 'فروتنی دانایی', lines: ['آنان که محیط فضل و آداب شدند', 'در جمع کمال شمع اصحاب شدند'] },

    /* نظامی */
    { poet: 'نظامی', tag: 'کوشش', lines: ['هر که در او جوهر دانایی است', 'هیچ گه از کوشش خود وانایی است'] },
    { poet: 'نظامی', tag: 'هنر', lines: ['به دانش توان کرد کار جهان', 'به شمشیر نتوان به نیروی جان'] },
    { poet: 'نظامی', tag: 'سخن', lines: ['سخن را چو آب روان بایدت', 'که در وی گهرها نهان بایدت'] },

    /* عطار */
    { poet: 'عطار', tag: 'راه', lines: ['تو خود حجاب خودی حافظ از میان برخیز', 'خوشا کسی که در این راه بی‌حجاب رود'] },
    { poet: 'عطار', tag: 'طلب', lines: ['سیمرغ را کسی رسد اندر قاف کوه', 'کاو دست از جان بشوید و پای در ره نهد'] },
    { poet: 'عطار', tag: 'دل', lines: ['دل به دست آور که حج اکبر است', 'از هزاران کعبه یک دل بهتر است'] },

    /* پروین اعتصامی */
    { poet: 'پروین اعتصامی', tag: 'تلاش', lines: ['ما نگوییم که این باغ گل و سنبل نیست', 'بیش از این‌هاست در این باغ گل و سنبل‌ها'] },
    { poet: 'پروین اعتصامی', tag: 'دانش', lines: ['هنر آن است که خود را نتوانی دیدن', 'ورنه هر ذره که بینی همه خورشید بود'] },
    { poet: 'پروین اعتصامی', tag: 'زن و همت', lines: ['به کهین پایه قناعت مکن ای همت مرد', 'که بلند است مکان تو در این قصر کبود'] },
    { poet: 'پروین اعتصامی', tag: 'عمل', lines: ['گهر بی‌هنر زار و خوار است و سست', 'به فرهنگ باشد نگین در درست'] },

    /* اقبال لاهوری */
    { poet: 'اقبال لاهوری', tag: 'خویشتن', lines: ['خودی را در جهان خوار دیدن خطاست', 'که خود را بلند آفریدن سزاست'] },
    { poet: 'اقبال لاهوری', tag: 'حرکت', lines: ['نشین دمی که این عالم گذر است', 'ولی در خود سفر کن کز خودی برتر است'] },
    { poet: 'اقبال لاهوری', tag: 'جستجو', lines: ['ستارهٔ صبحم و از شب نمی‌ترسم', 'که نور من از آفتاب دیگری است'] },

    /* صائب تبریزی */
    { poet: 'صائب', tag: 'کوشش', lines: ['به فکر آینه بودن به از نگارستان', 'که خودشناسی ما را به خود رساند تمام'] },
    { poet: 'صائب', tag: 'صبر', lines: ['قطره‌قطره جمع گردد وانگهی دریا شود', 'این مثل در کار اهل همت است'] },

    /* باباطاهر */
    { poet: 'باباطاهر', tag: 'دل', lines: ['ز دست دیده و دل هر دو فریاد', 'که هر چه دیده بیند دل کند یاد'] },
    { poet: 'باباطاهر', tag: 'سوز دانستن', lines: ['اگر دل دلبر آهسته بخواند', 'همه کوه و کمر با ما برانند'] },

    /* ناصر خسرو */
    { poet: 'ناصر خسرو', tag: 'دانش', lines: ['درخت تو گر بار دانش بگیرد', 'به زیر آوری چرخ نیلوفری را'] },
    { poet: 'ناصر خسرو', tag: 'هوشیاری', lines: ['آزاده مردی را که علم آموخت', 'بر جاهلان فضلی عظیم آموخت'] },

    /* سنایی */
    { poet: 'سنایی', tag: 'راه', lines: ['علم را گر تو برای نان پزی', 'کفشگر بهتر که در دکان پزی'] },
    { poet: 'سنایی', tag: 'معنا', lines: ['تا در این زندان دنیایی بسی', 'علم دین آموز و کم کن هوسی'] },

    /* جامی */
    { poet: 'جامی', tag: 'ادب', lines: ['علم چندان که بیشتر خوانی', 'چون عمل در تو نیست نادانی'] },
    { poet: 'جامی', tag: 'دل', lines: ['دل که فارغ شد از این آب و گل', 'می‌رود تا بارگاه وصل گل'] },

    /* اوحدی */
    { poet: 'اوحدی', tag: 'زمان', lines: ['وقت عزیز است غنیمت شمار', 'عمر به بازیچه مده از کنار'] },

    /* هاتف اصفهانی */
    { poet: 'هاتف', tag: 'وحدت معنا', lines: ['یکی هست و هیچ نیست جز او', 'وحده لا اله‌الا هو'] },

    /* بیدل */
    { poet: 'بیدل دهلوی', tag: 'فکر', lines: ['حیرت دمیده‌ام گل داغم بهانه‌ای است', 'طومار بی‌نهایت من یک نشانه‌ای است'] },

    /* فروغی بسطامی */
    { poet: 'فروغی بسطامی', tag: 'عشق دانایی', lines: ['کمال سر محبت ببین نه نقص گناه', 'که کوی عشق مظفر به هر که ره باشد'] },

    /* معاصر کوتاه */
    { poet: 'سهراب سپهری', tag: 'نگاه تازه', lines: ['چشم‌ها را باید شست', 'جور دیگر باید دید'] },
    { poet: 'سهراب سپهری', tag: 'زندگی', lines: ['زندگی رسم غربت نیست', 'زندگی باغبانی است در خاطره‌ها'] },
    { poet: 'اخوان ثالث', tag: 'پایداری', lines: ['زمستان است', 'سلامت را نمی‌خواهند پاسخ گفت'] },
    { poet: 'شاملو', tag: 'انسان', lines: ['انسان بودن را بیازمای', 'اگر مرد این میدانی'] },
    { poet: 'شهریار', tag: 'مهر', lines: ['آمدی جانم به قربانت ولی حالا چرا', 'بی‌وفا حالا که من افتاده‌ام از پا چرا'] },
    { poet: 'ملک‌الشعرا بهار', tag: 'آزادی دانایی', lines: ['اگر به دانش خود بنگریم و بکوشیم', 'از این تیره شب ما را رهایی است'] },

    /* پندهای کوتاه حکمی */
    { poet: 'سعدی', tag: 'رفاقت راه', lines: ['دشمن دانا که غم جان بود', 'بهتر از آن دوست که نادان بود'] },
    { poet: 'پروین اعتصامی', tag: 'امید', lines: ['شمع امید را مفشان از کف', 'که شب تیره می‌شود روشن'] },
    { poet: 'مولوی', tag: 'هم‌سفری', lines: ['هم‌صحبت نیک از کیمیا بهتر بود', 'هم‌صحبت بد از بلا بدتر بود'] },
    { poet: 'سعدی', tag: 'آغاز یادگیری', lines: ['استاد قدیم به از رفیق جدید', 'علم ازل به از مال ابد'] },
    { poet: 'خیام', tag: 'آرامش اندیشه', lines: ['آرام بگیر ای دل شوریده که آخر', 'این قصهٔ پرغصه به پایان برسد'] },
    { poet: 'حافظ', tag: 'نگاه بلند', lines: ['رسید مژده که ایام غم نخواهد ماند', 'چنان نماند و چنین نیز هم نخواهد ماند'] },
    { poet: 'فردوسی', tag: 'خرد پیشه کن', lines: ['خردمند کز کارها پیشه‌ور', 'شود شاد و پیروز و آزاده‌سر'] },
    { poet: 'ناصر خسرو', tag: 'پرسش', lines: ['بپرس از هر چه می‌دانی و می‌خوان', 'که نادان ماند آن کو نیست پرسان'] },
    { poet: 'سنایی', tag: 'نیت پاک', lines: ['نیت اگر پاک باشد در طلب', 'سنگ گردد در کف تو زرِ ناب'] },
    { poet: 'جامی', tag: 'دل و دانش', lines: ['دانش اندر دل چو آب زندگی است', 'بی‌دل دانش همه باد و دمی است'] },
    { poet: 'اقبال لاهوری', tag: 'ساختن خود', lines: ['پیکر خود را به خود تدبیر کن', 'در جهان خویش را تعبیر کن'] },
    { poet: 'سهراب سپهری', tag: 'آرامش کار', lines: ['کار ما شاید این باشد که میان گل و گیاه', 'آرام آرام قدم برداریم'] },
    { poet: 'مولوی', tag: 'یادگیری از درد', lines: ['درد دل را دارویی جز درد نیست', 'عاشقی را جز غم جان‌درد نیست'] },
    { poet: 'سعدی', tag: 'اندازه نگه دار', lines: ['نه هر که چهره برافروخت دلبری داند', 'نه هر که آینه سازد سکندری داند'] },
    { poet: 'حافظ', tag: 'حرکت نرم', lines: ['با مدعی مگویید اسرار عشق و مستی', 'تا بی‌خبر بمیرد در درد خودپرستی'] },
    { poet: 'پروین اعتصامی', tag: 'ساختن فردا', lines: ['تو برای خود مبال ای ناتوان', 'سعی کن تا شوی از خویشتن'] },
    { poet: 'فردوسی', tag: 'راستی پیشه', lines: ['که با راستی باشی و با خرد', 'از این هر دو پیوسته باشی به خود'] }
  ];

  var THEMES = [
    { id: 'all', label: 'همه مضامین', match: null },
    { id: 'self', label: 'خودشناسی و خویشتن', match: ['خودشناسی', 'خویشتن', 'درون', 'خویش', 'ساختن خود', 'انتخاب', 'معنا', 'نگاه تازه'] },
    { id: 'effort', label: 'تلاش و همت', match: ['تلاش', 'کوشش', 'صبر', 'عمل', 'کار', 'پایداری', 'ساختن فردا', 'زن و همت'] },
    { id: 'wisdom', label: 'دانایی و خرد', match: ['یادگیری', 'خرد', 'دانایی', 'دانش', 'آگاهی', 'اندیشه', 'پرسش', 'عشق به دانستن'] },
    { id: 'hope', label: 'راه و امید', match: ['راه', 'حرکت', 'امید', 'نگاه بلند', 'طلب', 'جستجو', 'رشد'] }
  ];

  var currentTheme = 'all';

  function loadSaved() {
    try { return JSON.parse(localStorage.getItem('dh_saved_verses_v1') || '[]'); } catch (e) { return []; }
  }
  function saveSaved(arr) {
    try { localStorage.setItem('dh_saved_verses_v1', JSON.stringify(arr)); } catch (e) {}
  }

  function dayIndex() {
    var d = new Date();
    return (d.getFullYear() * 372 + d.getMonth() * 31 + d.getDate()) % VERSES.length;
  }

  function loadCursor() {
    try {
      var raw = localStorage.getItem('dh_poem_cursor_v1');
      if (!raw) return { day: dayIndex(), offset: 0 };
      var o = JSON.parse(raw);
      if (o.day !== dayIndex()) return { day: dayIndex(), offset: 0 };
      return o;
    } catch (e) {
      return { day: dayIndex(), offset: 0 };
    }
  }

  function saveCursor(c) {
    try { localStorage.setItem('dh_poem_cursor_v1', JSON.stringify(c)); } catch (e) {}
  }

  function filteredList() {
    if (currentTheme === 'all') return VERSES;
    var themeObj = null;
    for (var i = 0; i < THEMES.length; i++) {
      if (THEMES[i].id === currentTheme) { themeObj = THEMES[i]; break; }
    }
    if (!themeObj || !themeObj.match) return VERSES;
    var out = VERSES.filter(function (v) { return themeObj.match.indexOf(v.tag) >= 0; });
    return out.length ? out : VERSES;
  }

  function pickPair() {
    var list = filteredList();
    var c = loadCursor();
    var i = ((c.day + c.offset) % list.length + list.length) % list.length;
    var a = list[i];
    var b = list[(i + 1) % list.length];
    return { a: a, b: b, index: i, total: list.length };
  }

  function cardHTML(v, label, slotIdx) {
    var key = v.poet + ':' + v.lines[0];
    var liked = loadSaved().indexOf(key) >= 0;
    return (
      '<article class="dh-poem-card">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
          (label ? '<span class="dh-poem-label" style="margin-bottom:0;">' + label + '</span>' : '<span></span>') +
          '<div style="display:flex;gap:6px;align-items:center;">' +
            '<button type="button" class="dh-quote-share-btn" data-copy-slot="' + slotIdx + '">کپی بیت ✨</button>' +
            '<button type="button" class="dh-quote-share-btn' + (liked ? ' is-saved' : '') + '" data-save-key="' + key.replace(/"/g, '&quot;') + '">' + (liked ? '♥ ذخیره‌شده' : '♡ پسندیدم') + '</button>' +
          '</div>' +
        '</div>' +
        '<p class="dh-poem-line">' + v.lines[0] + '</p>' +
        (v.lines[1] ? '<p class="dh-poem-line">' + v.lines[1] + '</p>' : '') +
        '<div class="dh-poem-meta">' +
          '<span class="dh-poem-poet">' + v.poet + '</span>' +
          '<span class="dh-poem-tag">' + v.tag + '</span>' +
        '</div>' +
      '</article>'
    );
  }

  function renderPoems() {
    var root = $('app');
    if (!root) return;
    window.__dhInJourney = false;
    var p = pickPair();

    var filterHtml = THEMES.map(function (t) {
      return '<button type="button" class="dh-mod-chip' + (t.id === currentTheme ? ' is-active' : '') + '" data-poem-theme="' + t.id + '">' +
        t.label +
      '</button>';
    }).join('');

    root.innerHTML =
      '<div class="dh-home-wrap dh-poems-wrap dh-view-enter">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">' +
          '<button type="button" class="dh-back-link" id="dh-po-back">← بازگشت به صفحه اول</button>' +
          '<span class="dh-story-count">' + (p.index + 1) + ' از ' + p.total + '</span>' +
        '</div>' +
        '<div class="dh-poem-live-top">' +
          '<span class="dh-story-pill">سخن بزرگان</span>' +
          '<span style="font-size:.78rem;color:#c8c1b2;">برای درنگ، معنا و خودشناسی</span>' +
        '</div>' +
        '<div class="dh-mod-strip" id="dh-poem-themes" aria-label="فیلتر مضامین شعر">' + filterHtml + '</div>' +
        cardHTML(p.a, 'بیت برگزیده', 0) +
        (p.total > 1 ? cardHTML(p.b, 'بیت همراه', 1) : '') +
        '<div class="dh-story-actions" style="margin-top:12px;">' +
          '<button type="button" class="btn btn-primary" id="dh-po-next" style="flex:1;">دو بیت بعدی ›</button>' +
          '<button type="button" class="btn" id="dh-po-go" style="flex:1;">شروع سفر</button>' +
        '</div>' +
        '<p class="dh-story-foot">گزیده از شعر کلاسیک و معاصر فارسی (میراث عمومی). برای خواندن بیشتر به دیوان‌ها رجوع کنید.</p>' +
        '<button type="button" class="btn" id="dh-po-home" style="width:100%;margin-top:10px;">صفحه اول</button>' +
      '</div>';

    $('dh-po-back').onclick = function () {
      if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
    };
    $('dh-po-home').onclick = function () {
      if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
    };
    $('dh-po-go').onclick = function () {
      if (window.DHCommercialUI && typeof window.DHCommercialUI.startServerAuthorizedJourney === 'function') {
        window.DHCommercialUI.startServerAuthorizedJourney();
      } else if (window.DHShell && DHShell.startJourney) {
        DHShell.startJourney();
      }
    };
    $('dh-po-next').onclick = function () {
      if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
      var cur = loadCursor();
      cur.offset = (cur.offset + 2) % VERSES.length;
      saveCursor(cur);
      renderPoems();
    };

    var themesEl = $('dh-poem-themes');
    if (themesEl) {
      themesEl.onclick = function (ev) {
        var btn = ev.target && ev.target.closest ? ev.target.closest('[data-poem-theme]') : null;
        if (!btn) return;
        if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
        currentTheme = btn.getAttribute('data-poem-theme') || 'all';
        var cur = loadCursor();
        cur.offset = 0;
        saveCursor(cur);
        renderPoems();
      };
    }

    root.onclick = function (ev) {
      var copyBtn = ev.target && ev.target.closest ? ev.target.closest('[data-copy-slot]') : null;
      if (copyBtn) {
        if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
        var v = copyBtn.getAttribute('data-copy-slot') === '1' ? p.b : p.a;
        var text = v.lines.join('\n') + '\n— ' + v.poet + ' · اسب سیاه\nhttps://asbe-siah.ir/';
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            if (typeof window.dhToast === 'function') window.dhToast('بیت با نام شاعر کپی شد ✨');
          }).catch(function () {});
        }
        return;
      }
      var saveBtn = ev.target && ev.target.closest ? ev.target.closest('[data-save-key]') : null;
      if (saveBtn) {
        if (typeof window.dhHaptic === 'function') window.dhHaptic('success');
        var k = saveBtn.getAttribute('data-save-key');
        var saved = loadSaved();
        var pos = saved.indexOf(k);
        if (pos >= 0) saved.splice(pos, 1);
        else saved.push(k);
        saveSaved(saved);
        renderPoems();
      }
    };
  }

  window.DHPoems = {
    open: function (opts) {
      if (!opts || !opts.fromPopState) {
        if (typeof window.dhPushSubView === 'function') window.dhPushSubView('poems');
      }
      renderPoems();
    },
    peek: function () {
      var v = VERSES[dayIndex() % VERSES.length];
      return { poet: v.poet, tag: v.tag, line: v.lines[0], count: VERSES.length };
    },
    count: VERSES.length
  };
})();
