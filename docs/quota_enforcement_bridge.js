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