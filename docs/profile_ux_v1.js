/* Profile UX — user profile hierarchy + one admin panel.
 * The legacy support card is preserved as-is; only its channel navigation is repaired.
 * No scoring, quota calculation, or purchase semantics are changed.
 */
(function (global) {
  'use strict';

  var INSTALLED = false;
  var OBSERVER_INSTALLED = false;
  var EITAA_URL = 'https://eitaa.com/asbe_siah';

  function text(value) { return String(value == null ? '' : value); }

  function escapeHtml(value) {
    return text(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function authUser() {
    try {
      if (global.DHAuth && typeof global.DHAuth.getUser === 'function') return global.DHAuth.getUser();
    } catch (_) {}
    return null;
  }

  function isAdmin(user) {
    return !!(user && (user.is_admin === true || user.role === 'admin'));
  }

  function removeLocalSubscriptionState() {
    /* Remove only obsolete LOCAL test entitlement state. Never touch server premium state. */
    try {
      var quotaKey = 'dh_local_quota_v1';
      var rawQuota = localStorage.getItem(quotaKey);
      if (rawQuota) {
        var quota = JSON.parse(rawQuota);
        if (quota && Object.prototype.hasOwnProperty.call(quota, 'premium')) {
          delete quota.premium;
          localStorage.setItem(quotaKey, JSON.stringify(quota));
        }
      }
    } catch (_) {}

    try {
      var userKey = 'dh_local_user_v1';
      var rawUser = localStorage.getItem(userKey);
      if (rawUser) {
        var user = JSON.parse(rawUser);
        if (user && Object.prototype.hasOwnProperty.call(user, 'is_premium')) {
          delete user.is_premium;
          localStorage.setItem(userKey, JSON.stringify(user));
        }
      }
    } catch (_) {}
  }

  function removeLegacyProfileControls(card) {
    if (!card) return;
    ['dh-p-home', 'dh-p-prem', 'dh-p-exit'].forEach(function (id) {
      var node = card.querySelector('#' + id);
      if (node) node.remove();
    });
  }

  function findLegacySupportCard(card) {
    if (!card) return null;
    var children = card.children || [];
    for (var i = 0; i < children.length; i += 1) {
      var child = children[i];
      if (child && child.classList && child.classList.contains('card')) return child;
    }
    return null;
  }

  function findProfileCard(wrap) {
    if (!wrap) return null;
    var card = wrap.querySelector('.card');
    if (!card) return null;
    return card.querySelector('#dh-p-journey') ? card : null;
  }

  function readPhone(card, user) {
    var phone = user && user.phone ? text(user.phone).trim() : '';
    if (phone) return phone;
    var nodes = card ? card.querySelectorAll('p') : [];
    for (var i = 0; i < nodes.length; i += 1) {
      var value = text(nodes[i].textContent).trim();
      if (/^09\d{9}$/.test(value)) return value;
    }
    return '';
  }

  function repairEitaaChannelLink(supportCard) {
    if (!supportCard) return;
    var links = supportCard.querySelectorAll('a[href*="eitaa.com"]');
    for (var i = 0; i < links.length; i += 1) {
      var link = links[i];
      if (text(link.textContent).indexOf('عضویت در کانال ایتا') < 0 &&
          text(link.getAttribute('href')).indexOf('/asbe_siah') < 0) continue;
      link.setAttribute('href', EITAA_URL);
      link.setAttribute('target', '_self');
      link.setAttribute('rel', 'noopener noreferrer');
      link.onclick = function (event) {
        try {
          if (event) event.preventDefault();
          global.location.assign(EITAA_URL);
        } catch (_) {
          try { global.location.href = EITAA_URL; } catch (_) {}
        }
        return false;
      };
      break;
    }
  }

  function makeAdminPanel() {
    var panel = document.createElement('section');
    panel.id = 'dh-admin-panel';
    panel.className = 'dh-admin-panel';
    panel.setAttribute('aria-label', 'پنل مدیریت');
    panel.innerHTML =
      '<h3 class="dh-admin-title">پنل مدیریت</h3>' +
      '<div class="dh-admin-users" data-admin-users>' +
        '<p class="dh-admin-status" data-admin-status>در حال دریافت کاربران…</p>' +
      '</div>';
    return panel;
  }

  function renderAdminUsers(panel, users) {
    var target = panel.querySelector('[data-admin-users]');
    if (!target) return;
    target.innerHTML = '';

    if (!Array.isArray(users) || users.length === 0) {
      var empty = document.createElement('p');
      empty.className = 'dh-admin-status';
      empty.textContent = 'کاربری برای نمایش وجود ندارد.';
      target.appendChild(empty);
      return;
    }

    var tableWrap = document.createElement('div');
    tableWrap.className = 'dh-admin-users-table-wrap';
    tableWrap.setAttribute('role', 'region');
    tableWrap.setAttribute('aria-label', 'فهرست کاربران');
    tableWrap.tabIndex = 0;

    var table = document.createElement('table');
    table.className = 'dh-admin-users-table';
    table.dir = 'rtl';

    var thead = document.createElement('thead');
    var headerRow = document.createElement('tr');
    ['نام', 'شماره تماس', 'وضعیت'].forEach(function (label) {
      var th = document.createElement('th');
      th.scope = 'col';
      th.textContent = label;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');
    users.forEach(function (user) {
      var row = document.createElement('tr');

      var name = document.createElement('td');
      name.textContent = text(user && user.name ? user.name : '—');
      row.appendChild(name);

      var phone = document.createElement('td');
      phone.dir = 'ltr';
      phone.textContent = text(user && user.phone ? user.phone : '—');
      row.appendChild(phone);

      var status = document.createElement('td');
      var statusMap = { active: 'فعال', suspended: 'تعلیق‌شده', disabled: 'غیرفعال' };
      status.textContent = statusMap[user && user.status] || text(user && user.status ? user.status : '—');
      row.appendChild(status);

      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    tableWrap.appendChild(table);
    target.appendChild(tableWrap);

    var meta = document.createElement('p');
    meta.className = 'dh-admin-status';
    meta.textContent = users.length + ' کاربر اخیر';
    target.appendChild(meta);
  }

  async function loadAdminUsers(panel) {
    var status = panel.querySelector('[data-admin-status]');
    try {
      var session = global.DHAuth && typeof global.DHAuth.getSession === 'function'
        ? global.DHAuth.getSession()
        : null;
      var token = session && session.token ? String(session.token) : '';
      if (!token) throw new Error('auth');

      var base = text(global.API_BASE || 'https://api.asbe-siah.ir').replace(/\/$/, '');
      var response = await fetch(base + '/api/v1/admin/users?limit=100', {
        headers: { Authorization: 'Bearer ' + token }
      });
      var data = null;
      try { data = await response.json(); } catch (_) {}
      if (!response.ok) throw new Error('status');

      renderAdminUsers(panel, data);
      if (status) status.remove();
    } catch (_) {
      if (status) status.textContent = 'فهرست کاربران موقتاً در دسترس نیست.';
    }
  }

  function reflowProfile(wrap, card) {
    var user = authUser();
    if (!user || !wrap || !card || wrap.querySelector('.dh-profile-v2')) return;

    var avatar = card.querySelector('.dh-profile-avatar');
    var name = card.querySelector('.dh-prof-display-name');
    var date = card.querySelector('.dh-prof-date');
    var stats = card.querySelector('.dh-stat-grid');
    var last = card.querySelector('.dh-last-card');
    var journey = card.querySelector('#dh-p-journey');
    var share = card.querySelector('#dh-p-share');
    var buy = card.querySelector('#dh-p-buy');
    var logout = card.querySelector('#dh-p-out');
    var support = findLegacySupportCard(card);

    if (!avatar || !name || !stats || !journey || !buy || !logout) return;

    removeLegacyProfileControls(card);

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
    journey.classList.add('dh-profile-journey');
    actions.appendChild(journey);

    buy.classList.remove('btn-primary');
    buy.classList.add('dh-profile-buy');
    actions.appendChild(buy);

    if (hasResult && share) {
      share.classList.remove('btn-primary');
      share.classList.add('dh-profile-share');
      actions.appendChild(share);
    } else if (share) {
      share.remove();
    }

    var account = document.createElement('section');
    account.className = 'dh-profile-account';
    account.appendChild(logout);

    var admin = isAdmin(user) ? makeAdminPanel() : null;

    wrap.innerHTML = '';
    shell.appendChild(head);
    shell.appendChild(statsBox);
    if (lastBox) shell.appendChild(lastBox);
    shell.appendChild(actions);
    shell.appendChild(account);
    if (support) {
      shell.appendChild(support);
      repairEitaaChannelLink(support);
    }
    if (admin) shell.appendChild(admin);
    wrap.appendChild(shell);

    if (admin) loadAdminUsers(admin);
  }

  function ensureAdminPanel() {
    var user = authUser();
    var app = document.getElementById('app');
    var wrap = app && app.querySelector('.dh-home-wrap');
    if (!wrap) return;

    var profile = wrap.querySelector('.dh-profile-v2');
    if (!profile) {
      var card = findProfileCard(wrap);
      if (card && user) {
        try { reflowProfile(wrap, card); } catch (_) {}
        profile = wrap.querySelector('.dh-profile-v2');
      }
    }

    var existing = document.getElementById('dh-admin-panel');
    if (!user || !isAdmin(user) || !profile) {
      if (existing) existing.remove();
      return;
    }

    if (existing && existing.parentNode === profile) return;
    if (existing) existing.remove();

    var panel = makeAdminPanel();
    profile.appendChild(panel);
    loadAdminUsers(panel);
  }

  function cleanupLegacyControlsEverywhere() {
    removeLocalSubscriptionState();
    var app = document.getElementById('app');
    if (!app) return;
    var home = app.querySelector('#dh-p-home');
    if (home && !findProfileCard(app.querySelector('.dh-home-wrap'))) home.remove();
    var prem = app.querySelector('#dh-p-prem');
    if (prem) prem.remove();
    var exit = app.querySelector('#dh-p-exit');
    if (exit) exit.remove();
  }

  function install() {
    if (INSTALLED) return;
    INSTALLED = true;
    if (!global.DHShell || typeof global.DHShell.renderProfile !== 'function') return;

    var original = global.DHShell.renderProfile;
    global.DHShell.renderProfile = function () {
      var result = original.apply(this, arguments);
      try { ensureAdminPanel(); } catch (_) {}
      return result;
    };
  }

  function boot() {
    cleanupLegacyControlsEverywhere();
    install();
    if (OBSERVER_INSTALLED || !document.body || typeof MutationObserver === 'undefined') return;
    OBSERVER_INSTALLED = true;
    var observer = new MutationObserver(function () {
      try {
        cleanupLegacyControlsEverywhere();
        ensureAdminPanel();
      } catch (_) {}
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})(window);
