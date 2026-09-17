/* Profile UX v1 — DOM-only hierarchy layer.
 * Deliberately does not alter scoring, quota calculation, consumption, or result data.
 */
(function (global) {
  'use strict';

  var INSTALLED = false;
  var WRAPPED = false;

  function el(id) { return document.getElementById(id); }
  function text(value) { return String(value == null ? '' : value); }
  function escapeHtml(value) {
    return text(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function debugEnabled() {
    var env = '';
    try { env = text(global.APP_ENV || global.__APP_ENV || '').toLowerCase(); } catch (_) {}
    return global.__DH_DEBUG__ === true || /^(debug|dev|development|test)$/.test(env);
  }

  function isAdmin(user) {
    return !!(user && (user.is_admin === true || user.role === 'admin'));
  }

  function authUser() {
    try {
      if (global.DHAuth && typeof global.DHAuth.getUser === 'function') return global.DHAuth.getUser();
    } catch (_) {}
    return null;
  }

  function clearLegacyProfileControls(card) {
    var home = card.querySelector('#dh-p-home');
    if (home) home.remove();
    var exit = card.querySelector('#dh-p-exit');
    if (exit) exit.remove();
  }

  function readPhone(card, user) {
    var phone = user && user.phone ? text(user.phone) : '';
    if (phone) return phone;
    var nodes = card.querySelectorAll('p');
    for (var i = 0; i < nodes.length; i += 1) {
      var value = text(nodes[i].textContent).trim();
      if (/^09\d{9}$/.test(value)) return value;
    }
    return '';
  }

  function makeBuyButton() {
    var buy = document.createElement('button');
    buy.type = 'button';
    buy.id = 'dh-p-buy';
    buy.className = 'btn dh-profile-buy';
    buy.setAttribute('data-testid', 'purchase-pack-3');
    buy.setAttribute('data-role', 'profile-action');
    buy.textContent = 'خرید بسته ۳ تست';
    buy.onclick = function () {
      try {
        if (global.DHCommercialUI && typeof global.DHCommercialUI.showPurchase === 'function') {
          global.DHCommercialUI.showPurchase();
        }
      } catch (_) {}
    };
    return buy;
  }

  function makeSupportCard() {
    var box = document.createElement('section');
    box.className = 'dh-support-card';
    box.setAttribute('aria-label', 'پشتیبانی و حریم خصوصی');
    box.innerHTML =
      '<div class="dh-support-line">' +
        '<span class="dh-support-copy">سؤال یا مشکلی داری؟ تیم اسب سیاه در ایتا پاسخ‌گوست.</span>' +
        '<a class="dh-support-link" href="https://eitaa.com/" target="_blank" rel="noopener noreferrer">پشتیبانی در ایتا</a>' +
      '</div>' +
      '<div class="dh-support-foot">' +
        '<a class="dh-enamad-chip" href="https://enamad.ir/" target="_blank" rel="noopener noreferrer" aria-label="اینماد">اینماد</a>' +
        '<span class="dh-support-dot">·</span>' +
        '<a class="dh-privacy-link" href="#dh-privacy-note">حریم خصوصی</a>' +
      '</div>' +
      '<div id="dh-privacy-note" class="dh-privacy-note">نام و شماره موبایل برای مدیریت حساب استفاده می‌شود؛ خلاصه نتیجه سفر برای قابلیت‌های حساب نگهداری می‌شود. برای اطلاعات بیشتر یا پرسش درباره حریم خصوصی، از پشتیبانی ایتا استفاده کنید.</div>';
    return box;
  }

  function makeAdminPanel() {
    var panel = document.createElement('section');
    panel.className = 'dh-admin-panel';
    panel.setAttribute('aria-label', 'خلاصه پنل مدیریت');
    panel.innerHTML =
      '<h3 class="dh-admin-title">پنل مدیریت</h3>' +
      '<div class="dh-admin-grid">' +
        '<div class="dh-admin-metric"><div class="n" data-admin-metric="users">—</div><div class="l">کاربران</div></div>' +
        '<div class="dh-admin-metric"><div class="n" data-admin-metric="feedback">—</div><div class="l">بازخورد</div></div>' +
        '<div class="dh-admin-metric"><div class="n" data-admin-metric="payments">—</div><div class="l">پرداخت‌ها</div></div>' +
      '</div>' +
      '<p class="dh-admin-status" data-admin-status>در حال دریافت آمار…</p>';
    return panel;
  }

  async function loadAdminStats(panel) {
    var status = panel.querySelector('[data-admin-status]');
    try {
      var session = global.DHAuth && typeof global.DHAuth.getSession === 'function'
        ? global.DHAuth.getSession()
        : null;
      var token = session && session.token ? String(session.token) : '';
      if (!token) throw new Error('auth');
      var base = text(global.API_BASE || 'https://api.asbe-siah.ir').replace(/\/$/, '');
      var response = await fetch(base + '/api/v1/admin/dashboard', {
        headers: { Authorization: 'Bearer ' + token }
      });
      var data = null;
      try { data = await response.json(); } catch (_) {}
      if (!response.ok) throw new Error('status');

      var users = panel.querySelector('[data-admin-metric="users"]');
      var feedback = panel.querySelector('[data-admin-metric="feedback"]');
      var payments = panel.querySelector('[data-admin-metric="payments"]');
      if (users) users.textContent = text(data && data.users_total != null ? data.users_total : '—');
      if (feedback) feedback.textContent = text(data && data.feedback_total != null ? data.feedback_total : '—');
      if (payments) payments.textContent = text(data && data.payments_total != null ? data.payments_total : '—');
      if (status) status.textContent = 'آمار سرور';
    } catch (_) {
      if (status) status.textContent = 'آمار موقتاً در دسترس نیست.';
    }
  }

  function scrollProfileToTop() {
    try {
      var scroller = document.scrollingElement || document.documentElement;
      if (typeof global.shellScrollTop !== 'number') global.shellScrollTop = Number(scroller.scrollTop || 0);
      requestAnimationFrame(function () {
        scroller.scrollTop = 0;
        document.documentElement.scrollTop = 0;
        if (document.body) document.body.scrollTop = 0;
      });
    } catch (_) {}
  }

  function reflowProfile() {
    var root = el('app');
    var user = authUser();
    if (!root || !user) return;

    var wrap = root.querySelector('.dh-home-wrap');
    var card = wrap && wrap.querySelector('.card');
    if (!wrap || !card || wrap.querySelector('.dh-profile-v2')) return;

    var avatar = card.querySelector('.dh-profile-avatar');
    var name = card.querySelector('.dh-prof-display-name');
    var date = card.querySelector('.dh-prof-date');
    var stats = card.querySelector('.dh-stat-grid');
    var last = card.querySelector('.dh-last-card');
    var journey = card.querySelector('#dh-p-journey');
    var share = card.querySelector('#dh-p-share');
    var legacyPrem = card.querySelector('#dh-p-prem');
    var logout = card.querySelector('#dh-p-out');

    if (!avatar || !name || !stats || !journey || !logout) return;

    clearLegacyProfileControls(card);

    var phone = readPhone(card, user);
    var hasResult = !!(last && !last.classList.contains('dh-last-empty'));

    var shell = document.createElement('div');
    shell.className = 'dh-profile-v2';

    var head = document.createElement('section');
    head.className = 'dh-profile-header';
    head.innerHTML =
      '<div class="dh-profile-avatar-v2">' + escapeHtml((user.name || '؟').trim().charAt(0) || '؟') + '</div>' +
      '<h2 class="dh-profile-name-v2">' + escapeHtml(user.name || 'مسافر') + '</h2>' +
      '<p class="dh-profile-meta-v2">' +
        (phone ? '<span dir="ltr">' + escapeHtml(phone) + '</span>' : '') +
        ((phone && date) ? ' · ' : '') +
        (date ? escapeHtml(date.textContent.trim()) : '') +
      '</p>';

    var statsBox = document.createElement('section');
    statsBox.className = 'dh-profile-stats';
    statsBox.appendChild(stats);

    var lastBox = null;
    if (hasResult) {
      lastBox = document.createElement('section');
      lastBox.className = 'dh-profile-last';
      lastBox.appendChild(last);
    } else if (last) {
      last.remove();
    }

    var actions = document.createElement('section');
    actions.className = 'dh-profile-actions';
    actions.setAttribute('aria-label', 'اقدامات پروفایل');
    journey.setAttribute('data-role', 'profile-action');
    journey.classList.add('dh-profile-journey');
    actions.appendChild(journey);

    actions.appendChild(makeBuyButton());

    if (hasResult && share) {
      share.classList.remove('btn-primary');
      share.classList.add('dh-profile-share');
      share.setAttribute('data-role', 'profile-action');
      actions.appendChild(share);
    } else if (share) {
      share.remove();
    }

    var debugBox = null;
    if (debugEnabled() && legacyPrem) {
      debugBox = document.createElement('div');
      debugBox.className = 'dh-profile-debug';
      legacyPrem.textContent = 'اشتراک محلی آفلاین (تست)';
      legacyPrem.removeAttribute('data-testid');
      debugBox.appendChild(legacyPrem);
    } else if (legacyPrem) {
      legacyPrem.remove();
    }

    var support = makeSupportCard();

    var account = document.createElement('section');
    account.className = 'dh-profile-account';
    account.appendChild(logout);

    var admin = null;
    if (isAdmin(user)) admin = makeAdminPanel();

    wrap.innerHTML = '';
    shell.appendChild(head);
    shell.appendChild(statsBox);
    if (lastBox) shell.appendChild(lastBox);
    shell.appendChild(actions);
    if (debugBox) shell.appendChild(debugBox);
    shell.appendChild(support);
    shell.appendChild(account);
    if (admin) shell.appendChild(admin);
    wrap.appendChild(shell);

    scrollProfileToTop();
    if (admin) loadAdminStats(admin);
  }

  function install() {
    if (INSTALLED) return;
    INSTALLED = true;
    if (!global.DHShell || typeof global.DHShell.renderProfile !== 'function') return;
    if (WRAPPED) return;

    var original = global.DHShell.renderProfile;
    global.DHShell.renderProfile = function () {
      var result = original.apply(this, arguments);
      try { reflowProfile(); } catch (e) { console.warn('Profile UX v1:', e); }
      return result;
    };
    WRAPPED = true;
  }

  function boot() {
    install();
    if (global.__dhProfileUxObserverInstalled || !document.body || typeof MutationObserver === 'undefined') return;
    global.__dhProfileUxObserverInstalled = true;
    var observer = new MutationObserver(function () {
      if (global.DHShell && typeof global.DHShell.renderProfile === 'function') install();
      if (authUser()) {
        try { reflowProfile(); } catch (_) {}
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})(window);
