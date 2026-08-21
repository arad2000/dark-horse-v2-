/**
 * سخنی با والدین — میثاق اسب سیاه در برابر استانداردسازی
 */
(function () {
  function $(id) { return document.getElementById(id); }

  function renderParents() {
    var root = $('app');
    if (!root) return;
    window.__dhInJourney = false;

    root.innerHTML =
      '<div class="dh-home-wrap dh-parents-wrap">' +
        '<button type="button" class="dh-back-link" id="dh-par-back">← بازگشت به خانه</button>' +
        '<h2 class="dh-par-title">سخنی با والدین</h2>' +
        '<p class="dh-par-lead">این بخش برای پدر و مادر است — نه برای فشار بیشتر روی فرزند، بلکه برای همراهی هوشمندانه.</p>' +

        '<div class="dh-par-card warn">' +
          '<h3>میثاق استانداردسازی</h3>' +
          '<p>وقتی موفقیت را فقط با رتبه، رشتهٔ «باپرستیژ» و مقایسه با بقیه تعریف می‌کنیم، فرزند یاد می‌گیرد خود را پنهان کند. فشار مداوم، اضطراب می‌سازد نه انگیزهٔ پایدار.</p>' +
        '</div>' +

        '<div class="dh-par-card good">' +
          '<h3>میثاق اسب سیاه</h3>' +
          '<p>اسب‌های سیاه کسانی‌اند که مسیر خودشان را پیدا کردند؛ نه لزوماً مسیر میانگین. راهنمایی واقعی یعنی کمک کنیم بفهمند چه چیزی به آن‌ها انرژی می‌دهد، بعد مسیر تحصیلی را با همان همسو کنند.</p>' +
        '</div>' +

        '<div class="dh-par-card">' +
          '<h3>پنج توصیهٔ عملی</h3>' +
          '<ol class="dh-par-list">' +
            '<li><b>سؤال را عوض کنید:</b> به‌جای «چند درصد شدی؟» بپرسید «امروز از کدام کار انرژی گرفتی؟»</li>' +
            '<li><b>نتیجهٔ این اپ حکم نیست:</b> پیشنهاد همخوانی است، نه تضمین قبولی یا حکم قطعی رشته.</li>' +
            '<li><b>فشار مقایسه را کم کنید:</b> داستان موفقیت دیگران، نقشهٔ زندگی فرزند شما نیست.</li>' +
            '<li><b>فضای امن بسازید:</b> اگر اشتباه انتخاب کرد، هنوز می‌تواند مسیر را اصلاح کند — هویت‌اش با یک انتخاب نمی‌میرد.</li>' +
            '<li><b>همراه باشید، نه فرمانده:</b> تصمیم نهایی بهتر است از گفت‌وگوی مشترک و کشف خودِ نوجوان بیرون بیاید.</li>' +
          '</ol>' +
        '</div>' +

        '<div class="dh-par-card">' +
          '<h3>چطور از این سامانه استفاده کنید؟</h3>' +
          '<p>بگذارید فرزند خودش سفر را طی کند. شما می‌توانید بعد از نتیجه، با هم دربارهٔ جرقه‌ها و ارزش‌ها حرف بزنید — نه اینکه به‌جای او تیک بزنید.</p>' +
        '</div>' +

        '<button class="btn btn-primary" id="dh-par-share" style="width:100%;margin-top:8px;">کپی متن برای ارسال به والدین دیگر</button>' +
        '<button class="btn" id="dh-par-home" style="width:100%;margin-top:8px;">خانه</button>' +
      '</div>';

    var shareText =
      'سخنی با والدین — از سامانه اسب سیاه\n\n' +
      'به‌جای فشار رتبه و مقایسه، کمک کنیم فرزند بفهمد چه چیزی به او انرژی می‌دهد.\n' +
      'استانداردسازی می‌پرسد «چقدر شبیه میانگین هستی؟»\n' +
      'فردیت می‌پرسد «چه چیزی تو را زنده می‌کند؟»\n\n' +
      'نتیجهٔ اپ پیشنهاد همخوانی است، نه حکم. تصمیم را با گفت‌وگو بسازید، نه با اجبار.';

    $('dh-par-back').onclick = function () {
      if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
    };
    $('dh-par-home').onclick = function () {
      if (window.DHShell && DHShell.renderHome) DHShell.renderHome();
    };
    $('dh-par-share').onclick = function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(shareText).then(function () {
          alert('متن کپی شد — می‌توانید در گروه والدین بفرستید.');
        }).catch(function () {
          prompt('متن را کپی کنید:', shareText);
        });
      } else {
        prompt('متن را کپی کنید:', shareText);
      }
    };
  }

  window.DHParents = { open: renderParents };
})();
