/* quota_runtime.js v1 — Phase 1 safe quota consolidation
 * The four legacy quota/session layers below are intentionally preserved in
 * their historical load order. No public API, request shape, scoring/ranking,
 * journey entry, result display, consume semantics, or failure UX is changed.
 * This module is a source-level consolidation only.
 */

/* journey_session_boot.js v1
 * Guarantees one persisted journey UUID before the first discovery request.
 * Does not alter scoring/ranking or resume an existing unfinished journey.
 */
(function (global) {
  'use strict';

  var KEY = 'darkhorse_session_v2';
  var AUTH_KEY = 'dh_auth_v1';

  function parse(raw) {
    try {
      var value = JSON.parse(raw || 'null');
      return value && typeof value === 'object' ? value : null;
    } catch (_) { return null; }
  }

  function loggedIn() {
    var auth = parse(localStorage.getItem(AUTH_KEY));
    return !!(auth && auth.token);
  }

  function uuid() {
    try {
      if (global.crypto && typeof global.crypto.randomUUID === 'function') return global.crypto.randomUUID();
    } catch (_) {}
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      var v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  function ensureAfterStart() {
    if (!loggedIn()) return null;
    var current = parse(localStorage.getItem(KEY)) || {};
    if (current.sessionId) return String(current.sessionId);
    var sessionId = uuid();
    current.sessionId = sessionId;
    try { localStorage.setItem(KEY, JSON.stringify(current)); } catch (_) {}
    return sessionId;
  }

  function patch() {
    if (!global.DHShell || typeof global.DHShell.startJourney !== 'function') return false;
    if (global.DHShell.startJourney.__dhJourneySessionBootWrapped) return true;
    var original = global.DHShell.startJourney;
    var wrapped = function () {
      var out = original.apply(this, arguments);
      try { ensureAfterStart(); } catch (_) {}
      return out;
    };
    wrapped.__dhJourneySessionBootWrapped = true;
    global.DHShell.startJourney = wrapped;
    return true;
  }

  if (!patch()) {
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      if (patch() || tries >= 30) clearInterval(timer);
    }, 100);
  }

  global.DHJourneySessionBoot = {
    ensureAfterStart: ensureAfterStart
  };
})(window);

/* quota_enforcement_bridge.js v3
 * Server-authoritative journey charging bridge.
 * A completed authenticated journey consumes exactly one server credit.
 * Each new journey receives a fresh UUID; retries within the same journey
 * reuse the persisted UUID so the backend can idempotently reject duplicate
 * charges.
 */
(function (global) {
  'use strict';
  if (global.__dhQuotaEnforcementBridgeInstalled) return;
  global.__dhQuotaEnforcementBridgeInstalled = true;

  var API = global.API_BASE || 'https://api.asbe-siah.ir';
  var AUTH_KEY = 'dh_auth_v1';
  var JOURNEY_KEY = 'darkhorse_session_v2';
  var QUOTA_KEY = 'dh_local_quota_v1';
  var CHARGED_SESSION_KEY = 'dh_quota_charged_session_v1';
  var SESSION_MEMORY = null;

  function parse(raw) {
    try { var v = JSON.parse(raw || 'null'); return v && typeof v === 'object' ? v : null; }
    catch (_) { return null; }
  }

  function auth() { return parse(localStorage.getItem(AUTH_KEY)); }
  function loggedIn() { var a = auth(); return !!(a && a.token); }
  function userKey() {
    var a = auth() || {}, u = a.user || {};
    return String(u.id || u.user_id || u.public_id || u.phone || u.mobile || '');
  }

  function readJourney() { return parse(localStorage.getItem(JOURNEY_KEY)) || {}; }

  function uuid() {
    try { if (global.crypto && typeof global.crypto.randomUUID === 'function') return global.crypto.randomUUID(); } catch (_) {}
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  function ensureJourneySession() {
    var j = readJourney();
    if (j.sessionId) {
      SESSION_MEMORY = String(j.sessionId);
      return SESSION_MEMORY;
    }
    if (!loggedIn()) {
      SESSION_MEMORY = null;
      return null;
    }
    // No persisted session means a deliberate/new journey. Never reuse the
    // in-memory UUID from a previous journey in the same page lifetime.
    SESSION_MEMORY = uuid();
    j.sessionId = SESSION_MEMORY;
    try { localStorage.setItem(JOURNEY_KEY, JSON.stringify(j)); } catch (_) {}
    return SESSION_MEMORY;
  }

  function setJourneySession(sessionId) {
    if (!sessionId) return;
    var candidate = String(sessionId);
    var j = readJourney();
    // The client creates the journey UUID before the first discovery request.
    // Discovery responses must never replace it: doing so can turn one journey
    // into two billing identities and charge the same completed test twice.
    if (j.sessionId && String(j.sessionId) !== candidate) {
      SESSION_MEMORY = String(j.sessionId);
      return SESSION_MEMORY;
    }
    SESSION_MEMORY = candidate;
    j.sessionId = SESSION_MEMORY;
    try { localStorage.setItem(JOURNEY_KEY, JSON.stringify(j)); } catch (_) {}
    return SESSION_MEMORY;
  }

  function chargedSessionId() {
    try {
      var raw = localStorage.getItem(CHARGED_SESSION_KEY);
      return raw ? String(raw) : null;
    } catch (_) { return null; }
  }

  function markCharged(sessionId) {
    try { localStorage.setItem(CHARGED_SESSION_KEY, String(sessionId)); } catch (_) {}
  }

  function persistQuota(data) {
    if (!data) return;
    var remaining = Number(data.credits_remaining);
    var consumed = Number(data.credits_consumed);
    var granted = Number(data.credits_granted);
    if (!Number.isFinite(remaining) || remaining < 0) return;
    var current = parse(localStorage.getItem(QUOTA_KEY)) || {};
    var next = Object.assign({}, current, {
      userKey: userKey(),
      serverRemaining: remaining,
      remaining: remaining,
      used: Number.isFinite(consumed) && consumed >= 0 ? consumed : Number(current.used || 0),
      serverConsumed: Number.isFinite(consumed) && consumed >= 0 ? consumed : Number(current.serverConsumed || 0),
      serverGranted: Number.isFinite(granted) && granted >= 0 ? granted : Number(current.serverGranted || 0),
      syncedAt: new Date().toISOString()
    });
    try { localStorage.setItem(QUOTA_KEY, JSON.stringify(next)); } catch (_) {}
  }

  function nativeFetch() { return global.fetch.apply(global, arguments); }

  var originalFetch = global.fetch;
  if (!originalFetch.__dhQuotaBridgeWrapped) {
    var wrappedFetch = function (input, init) {
      var url = '';
      try { url = typeof input === 'string' ? input : (input && input.url) || ''; } catch (_) {}
      var isDiscovery = /\/api\/v2\/darkhorse\/(discover|branch-discovery)(?:\?|$)/.test(url);
      if (isDiscovery && loggedIn()) {
        var sid = ensureJourneySession();
        if (sid) {
          var nextInit = Object.assign({}, init || {});
          var body = nextInit.body;
          if (typeof body === 'string') {
            try {
              var parsed = JSON.parse(body);
              if (!parsed.session_id) { parsed.session_id = sid; nextInit.body = JSON.stringify(parsed); }
            } catch (_) {}
          }
          return originalFetch.call(global, input, nextInit).then(function (res) {
            try {
              var clone = res.clone();
              clone.json().then(function (data) {
                if (data && data.session_id) setJourneySession(data.session_id);
              }).catch(function () {});
            } catch (_) {}
            return res;
          });
        }
      }
      return originalFetch.apply(global, arguments);
    };
    wrappedFetch.__dhQuotaBridgeWrapped = true;
    global.fetch = wrappedFetch;
  }

  async function consumeForJourney(sessionId) {
    if (!loggedIn() || !sessionId) return null;
    sessionId = String(sessionId);
    if (chargedSessionId() === sessionId) return { consumed: 0, already_consumed: true, local_guard: true, session_uuid: sessionId };
    var a = auth();
    var headers = { 'Content-Type': 'application/json' };
    if (a && a.token) headers.Authorization = 'Bearer ' + a.token;
    var res = await nativeFetch(API + '/api/v1/me/consume-test', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({ session_uuid: sessionId })
    });
    var body = null;
    try { body = await res.json(); } catch (_) {}
    if (!res.ok) {
      var msg = body && (body.detail || body.message);
      throw new Error(typeof msg === 'string' ? msg : ('خطا در ثبت مصرف اعتبار (' + res.status + ')'));
    }
    persistQuota(body);
    if (body && (body.consumed === 1 || body.already_consumed === true)) markCharged(sessionId);
    return body;
  }

  function wrapResults() {
    if (typeof global.displayResults !== 'function' || global.displayResults.__dhQuotaChargeWrapped) return false;
    var original = global.displayResults;
    var wrapped = function () {
      var args = arguments;
      try {
        var sid = ensureJourneySession();
        if (sid) setJourneySession(sid);
      } catch (_) {}
      var out = original.apply(this, args);
      var sid2 = SESSION_MEMORY || readJourney().sessionId;
      if (sid2 && loggedIn()) {
        consumeForJourney(String(sid2)).catch(function (err) {
          try { console.error('[DarkHorse quota] consume failed', err); } catch (_) {}
        });
      }
      return out;
    };
    wrapped.__dhQuotaChargeWrapped = true;
    global.displayResults = wrapped;
    return true;
  }

  function clampLegacyQuotaWrites() {
    if (Storage.prototype.__dhQuotaClampWrapped) return;
    var nativeSetItem = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) {
      if (key === QUOTA_KEY) {
        var current = parse(this.getItem(QUOTA_KEY));
        var incoming = parse(value) || {};
        var same = current && incoming && current.userKey && incoming.userKey && String(current.userKey) === String(incoming.userKey);
        if (same && Number.isFinite(Number(current.serverConsumed)) && !Object.prototype.hasOwnProperty.call(incoming, 'serverConsumed')) {
          incoming.used = Number(current.serverConsumed);
        }
        if (same && Number.isFinite(Number(current.serverRemaining)) && !Object.prototype.hasOwnProperty.call(incoming, 'serverRemaining')) {
          incoming.serverRemaining = Number(current.serverRemaining);
          incoming.remaining = Number(current.serverRemaining);
        }
        value = JSON.stringify(Object.assign({}, current || {}, incoming));
      }
      return nativeSetItem.call(this, key, value);
    };
    Storage.prototype.__dhQuotaClampWrapped = true;
  }

  function refreshQuota() {
    if (!loggedIn()) return;
    var a = auth();
    var headers = { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + a.token };
    nativeFetch(API + '/api/v1/me/quota', { headers: headers }).then(function (res) {
      return res.ok ? res.json() : null;
    }).then(function (data) { persistQuota(data); }).catch(function () {});
  }

  function boot() {
    clampLegacyQuotaWrites();
    wrapResults();
    refreshQuota();
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      wrapResults();
      if (tries >= 30) clearInterval(timer);
    }, 100);
  }

  global.DHQuotaEnforcement = {
    ensureJourneySession: ensureJourneySession,
    refresh: refreshQuota,
    consumeForJourney: consumeForJourney,
    getSnapshot: function () { return parse(localStorage.getItem(QUOTA_KEY)); }
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})(window);

/* quota_charge_failure_ui.js v1
 * Observe consume-test responses and surface failures to the user.
 * The server remains authoritative; this layer never changes quota locally.
 */
(function (global) {
  'use strict';
  if (global.__dhQuotaChargeFailureUiInstalled) return;
  global.__dhQuotaChargeFailureUiInstalled = true;

  function parse(raw) {
    try { var value = JSON.parse(raw || 'null'); return value && typeof value === 'object' ? value : null; }
    catch (_) { return null; }
  }

  function escape(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;');
  }

  function showFailure(sessionId, status, payload) {
    try {
      var old = document.getElementById('dh-quota-charge-error');
      if (old) old.remove();
      var detail = payload && (payload.detail || payload.message);
      if (typeof detail !== 'string') detail = 'ثبت مصرف اعتبار در سرور ناموفق بود.';
      var box = document.createElement('div');
      box.id = 'dh-quota-charge-error';
      box.setAttribute('role', 'alert');
      box.style.cssText = 'margin:14px 0;padding:16px;border:1px solid #ff6b6b;border-radius:14px;background:#2a1717;color:#ffd6d6;line-height:1.9;text-align:right;';
      box.innerHTML = '<div style="font-weight:800;color:#ff9a9a;">⚠️ مصرف اعتبار ثبت نشد</div>' +
        '<div style="margin-top:5px;">نتیجه نمایش داده شده، اما شارژ آزمون در سرور کامل نشده است.</div>' +
        '<div style="font-size:.8rem;color:#ffc5c5;word-break:break-word;margin-top:5px;">HTTP ' + escape(status) + ' · ' + escape(detail) + '</div>' +
        '<div style="font-size:.78rem;color:#e7baba;margin-top:5px;">Session: <span dir="ltr">' + escape(sessionId) + '</span></div>' +
        '<button type="button" class="btn btn-primary" id="dh-quota-charge-retry" style="width:100%;margin-top:12px;">🔄 تلاش دوباره</button>';
      var app = document.getElementById('app');
      if (app) app.insertBefore(box, app.firstChild);
      else document.body.appendChild(box);

      var retry = document.getElementById('dh-quota-charge-retry');
      if (!retry) return;
      retry.onclick = function () {
        if (retry.disabled || !global.DHQuotaEnforcement || typeof global.DHQuotaEnforcement.consumeForJourney !== 'function') return;
        retry.disabled = true;
        retry.textContent = 'در حال ثبت…';
        global.DHQuotaEnforcement.consumeForJourney(String(sessionId)).then(function () {
          var done = document.getElementById('dh-quota-charge-error');
          if (done) done.remove();
        }).catch(function (err) {
          console.error('[DarkHorse quota] retry failed', err);
          retry.disabled = false;
          retry.textContent = '🔄 تلاش دوباره';
        });
      };
    } catch (_) {}
  }

  var originalFetch = global.fetch;
  if (typeof originalFetch !== 'function') return;
  global.fetch = function (input, init) {
    var url = '';
    try { url = typeof input === 'string' ? input : (input && input.url) || ''; } catch (_) {}
    var isConsume = /\/api\/v1\/me\/consume-test(?:\?|$)/.test(url);
    var sessionId = null;
    if (isConsume && init && typeof init.body === 'string') {
      var requestBody = parse(init.body);
      sessionId = requestBody && requestBody.session_uuid ? String(requestBody.session_uuid) : null;
    }
    var result = originalFetch.apply(this, arguments);
    if (!isConsume) return result;
    return result.then(function (res) {
      if (!res.ok) {
        try {
          var clone = res.clone();
          clone.json().then(function (payload) {
            console.error('[DarkHorse quota] consume HTTP failure', { status: res.status, session_uuid: sessionId, payload: payload });
            if (sessionId) showFailure(sessionId, res.status, payload);
          }).catch(function () {
            console.error('[DarkHorse quota] consume HTTP failure', { status: res.status, session_uuid: sessionId });
            if (sessionId) showFailure(sessionId, res.status, null);
          });
        } catch (_) {}
      }
      return res;
    });
  };
  global.fetch.__dhQuotaChargeFailureUiWrapped = true;
})(window);

/* quota_consume_session_adapter.js
 * Ensure legacy DHAuth.consumeTest() requests carry the same journey UUID
 * used by the server-authoritative quota bridge. This preserves idempotency
 * between the entry gate and the result-completion safeguard.
 */
(function (global) {
  'use strict';
  if (global.__dhQuotaConsumeSessionAdapterInstalled) return;
  global.__dhQuotaConsumeSessionAdapterInstalled = true;

  var CONSUME_PATH = '/api/v1/me/consume-test';
  var originalFetch = global.fetch;
  if (!originalFetch || originalFetch.__dhQuotaConsumeSessionAdapterWrapped) return;

  function parse(raw) {
    try {
      var value = JSON.parse(raw || 'null');
      return value && typeof value === 'object' ? value : null;
    } catch (_) {
      return null;
    }
  }

  function sessionId() {
    try {
      if (global.DHQuotaEnforcement && typeof global.DHQuotaEnforcement.ensureJourneySession === 'function') {
        return global.DHQuotaEnforcement.ensureJourneySession();
      }
    } catch (_) {}
    try {
      var journey = parse(localStorage.getItem('darkhorse_session_v2')) || {};
      return journey.sessionId ? String(journey.sessionId) : null;
    } catch (_) {
      return null;
    }
  }

  var wrappedFetch = function (input, init) {
    var url = '';
    try { url = typeof input === 'string' ? input : (input && input.url) || ''; } catch (_) {}
    if (new RegExp(CONSUME_PATH.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?:\\?|$)').test(url)) {
      var nextInit = Object.assign({}, init || {});
      var sid = sessionId();
      if (sid && typeof nextInit.body === 'string') {
        try {
          var body = JSON.parse(nextInit.body || '{}');
          if (!body.session_uuid) {
            body.session_uuid = sid;
            nextInit.body = JSON.stringify(body);
          }
        } catch (_) {}
      }
      return originalFetch.call(global, input, nextInit);
    }
    return originalFetch.apply(global, arguments);
  };

  wrappedFetch.__dhQuotaConsumeSessionAdapterWrapped = true;
  global.fetch = wrappedFetch;
})(window);
