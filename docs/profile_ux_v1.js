/* Profile admin layer — legacy user profile stays untouched.
 * Production cleanup removes the obsolete local subscription control/state.
 * Admins additionally receive the management panel with user name and phone.
 */
(function (global) {
  'use strict';

  var INSTALLED = false;
  var OBSERVER_INSTALLED = false;
  var EITAA_URL = 'https://eitaa.com/asbe_siah';

  function text(value) { return String(value == null ? '' : value); }

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
    try {
      var quotaKey = 'dh_local_quota_v1';
      var rawQuota = localStorage.getItem(quotaKey);
      if (rawQuota) {
        var quota = JSON.parse(rawQuota);
        if (quota && quota.premium) {
          quota.premium = false;
          localStorage.setItem(quotaKey, JSON.stringify(quota));
        }
      }
    } catch (_) {}

    try {
      var userKey = 'dh_local_user_v1';
      var rawUser = localStorage.getItem(userKey);
      if (rawUser) {
        var user = JSON.parse(rawUser);
        if (user && user.is_premium) {
          user.is_premium = false;
          localStorage.setItem(userKey, JSON.stringify(user));
        }
      }
    } catch (_) {}
  }

  function removeLegacyLocalSubscription(root) {
    if (!root) return;
    var premiumButton = root.querySelector('#dh-p-prem');
    if (premiumButton) premiumButton.remove();
  }

  function repairEitaaChannelLink(root) {
    if (!root) return;
    var links = root.querySelectorAll('a[href*="eitaa.com"]');
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
          window.location.assign(EITAA_URL);
        } catch (_) {}
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

  function getProfileWrap() {
    var app = document.getElementById('app');
    if (!app) return null;
    return app.querySelector('.dh-home-wrap');
  }

  function ensureAdminPanel() {
    var wrap = getProfileWrap();
    if (!wrap) return;

    removeLocalSubscriptionState();
    removeLegacyLocalSubscription(wrap);
    repairEitaaChannelLink(wrap);

    var user = authUser();
    var existing = document.getElementById('dh-admin-panel');
    if (!isAdmin(user)) {
      if (existing) existing.remove();
      return;
    }
    if (existing && existing.parentNode === wrap) return;
    if (existing) existing.remove();

    var panel = makeAdminPanel();
    wrap.appendChild(panel);
    loadAdminUsers(panel);
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
    install();
    if (OBSERVER_INSTALLED || !document.body || typeof MutationObserver === 'undefined') return;
    OBSERVER_INSTALLED = true;
    var observer = new MutationObserver(function () {
      try { ensureAdminPanel(); } catch (_) {}
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})(window);
