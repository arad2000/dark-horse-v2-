/* Show the 1405 information banner only in the main Home shell. */
(function () {
  'use strict';

  var STORAGE_KEY = 'dh_banner_1405_v1';
  var BANNER_ID = 'dh-banner-1405-v1';
  var HOME_SELECTOR = '.dh-home-wrap.dh-mk2';
  var dismissedInMemory = false;

  function wasDismissed() {
    if (dismissedInMemory) return true;
    try {
      return window.sessionStorage.getItem(STORAGE_KEY) === '1';
    } catch (e) {
      return dismissedInMemory;
    }
  }

  function dismiss(banner) {
    dismissedInMemory = true;
    try {
      window.sessionStorage.setItem(STORAGE_KEY, '1');
    } catch (e) {
      // The current banner still closes for this page session if storage is unavailable.
    }
    if (banner && banner.parentNode) {
      banner.parentNode.removeChild(banner);
    }
  }

  function ensureBanner() {
    if (wasDismissed()) return;

    var app = document.getElementById('app');
    if (!app) return;

    var home = app.querySelector(HOME_SELECTOR);
    if (!home || home.querySelector('#' + BANNER_ID)) return;

    var banner = document.createElement('section');
    banner.id = BANNER_ID;
    banner.className = 'dh-update-banner-1405';
    banner.setAttribute('role', 'region');
    banner.setAttribute('aria-labelledby', BANNER_ID + '-title');

    var title = document.createElement('h2');
    title.id = BANNER_ID + '-title';
    title.className = 'dh-update-banner-1405__title';
    title.textContent = 'به‌روزرسانی انتخاب رشته ۱۴۰۵';

    var firstText = document.createElement('p');
    firstText.className = 'dh-update-banner-1405__text';
    firstText.textContent = 'ظرفیت رشته‌محل‌ها بر اساس دفترچه‌های جدید سازمان سنجش (۱۴۰۵) به‌روز شده است.';

    var secondText = document.createElement('p');
    secondText.className = 'dh-update-banner-1405__text';
    secondText.textContent = '«مقایسه با آخرین رتبه» فقط برای رشته‌هایی است که دادهٔ تاریخی در سامانه دارند؛ اگر نتیجه‌ای نبود، از منبع «ظرفیت دفترچه» استفاده کنید.';

    var actions = document.createElement('div');
    actions.className = 'dh-update-banner-1405__actions';

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'dh-update-banner-1405__dismiss';
    button.textContent = 'متوجه شدم';
    button.addEventListener('click', function () {
      dismiss(banner);
    });

    actions.appendChild(button);
    banner.appendChild(title);
    banner.appendChild(firstText);
    banner.appendChild(secondText);
    banner.appendChild(actions);

    // Insert at the very top of the Home content in normal document flow.
    // The Journey view does not use HOME_SELECTOR, so it is never overlaid.
    home.insertBefore(banner, home.firstChild);
  }

  function start() {
    var app = document.getElementById('app');
    if (!app) return;

    ensureBanner();
    if (typeof MutationObserver !== 'undefined') {
      var observer = new MutationObserver(ensureBanner);
      observer.observe(app, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
}());
