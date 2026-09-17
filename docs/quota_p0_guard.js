/* quota_p0_guard.js v1
 * P0 defense-in-depth for production credit accounting.
 *
 * Canonical charge point: quota_enforcement_bridge at completed results.
 * Legacy DHAuth.consumeTest() is refresh-only and must never charge.
 * Duplicate POST /me/consume-test calls for the same journey UUID are
 * coalesced locally; the server remains authoritative and idempotent.
 */
(function (global) {
  'use strict';

  var AUTH_KEY = 'dh_auth_v1';
  var QUOTA_KEY = 'dh_local_quota_v1';
  var CHARGE_KEY = 'dh_quota_p0_charge_v1';
  var installed = global.__dhQuotaP0GuardInstalled;
  if (installed) return;
  global.__dhQuotaP0GuardInstalled = true;

  function parse(raw) {
    try {
      var v = JSON.parse(raw || 'null');
      return v && typeof v === 'object' ? v : null;
    } catch (_) {
      return null;
    }
  }

  function loggedIn() {
    var a = parse(localStorage.getItem(AUTH_KEY));
    return !!(a && a.token);
  }

  function makeResponse(status, data) {
    return new Response(JSON.stringify(data == null ? {} : data), {
      status: status,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  function readPersistedCharge() {
    var v = parse(localStorage.getItem(CHARGE_KEY));
    return v && v.session_uuid && v.body ? v : null;
  }

  function persistCharge(sessionId, body) {
    try {
      localStorage.setItem(CHARGE_KEY, JSON.stringify({
        session_uuid: String(sessionId),
        body: body,
        savedAt: Date.now()
      }));
    } catch (_) {}
  }

  var persisted = readPersistedCharge();
  var inflight = Object.create(null);
  var nativeFetch = global.fetch;

  // Legacy entry gate: refresh the authoritative snapshot; never consume here.
  if (global.DHAuth && typeof global.DHAuth.consumeTest === 'function') {
    global.DHAuth.consumeTest = async function () {
      if (!global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) {
        throw new Error('authentication required');
      }
      return global.DHAuth.quota();
    };
  }

  function requestSignature(input, init) {
    var url = '';
    try { url = typeof input === 'string' ? input : (input && input.url) || ''; } catch (_) {}
    var method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    if (method !== 'POST' || !/\/api\/v1\/me\/consume-test(?:\?|$)/.test(url)) return null;
    var body = null;
    try {
      var raw = init && init.body;
      body = typeof raw === 'string' ? parse(raw) : null;
    } catch (_) {}
    var sid = body && body.session_uuid ? String(body.session_uuid) : '';
    return { url: url, method: method, sessionId: sid };
  }

  global.fetch = function (input, init) {
    var sig = requestSignature(input, init);
    if (!sig) return nativeFetch.apply(global, arguments);

    // A legacy call without a UUID is never allowed to spend a credit.
    if (!sig.sessionId) {
      var auth = parse(localStorage.getItem(AUTH_KEY));
      var headers = Object.assign({}, (init && init.headers) || {});
      if (auth && auth.token) headers.Authorization = 'Bearer ' + auth.token;
      return nativeFetch.call(global, (global.API_BASE || 'https://api.asbe-siah.ir') + '/api/v1/me/quota', { headers: headers });
    }

    if (persisted && persisted.session_uuid === sig.sessionId) {
      return Promise.resolve(makeResponse(200, persisted.body));
    }

    if (inflight[sig.sessionId]) {
      return inflight[sig.sessionId].then(function (result) {
        return makeResponse(result.status, result.body);
      });
    }

    inflight[sig.sessionId] = nativeFetch.apply(global, arguments).then(async function (res) {
      var body = null;
      try { body = await res.clone().json(); } catch (_) {}
      if (res.ok && body) {
        persisted = { session_uuid: sig.sessionId, body: body };
        persistCharge(sig.sessionId, body);
      }
      return { status: res.status, body: body };
    }).finally(function () {
      delete inflight[sig.sessionId];
    });

    return inflight[sig.sessionId].then(function (result) {
      return makeResponse(result.status, result.body);
    });
  };

  // Final protection against legacy localStorage writes such as {used:0}.
  var priorSetItem = Storage.prototype.setItem;
  if (!priorSetItem.__dhP0GuardWrapped) {
    var guardedSetItem = function (key, value) {
      if (key === QUOTA_KEY && loggedIn()) {
        var current = parse(this.getItem(QUOTA_KEY)) || {};
        var incoming = parse(value) || {};
        var explicitConsumed = Object.prototype.hasOwnProperty.call(incoming, 'credits_consumed') ||
          Object.prototype.hasOwnProperty.call(incoming, 'serverConsumed');
        var currentConsumed = Number(current.serverConsumed);
        if (!Number.isFinite(currentConsumed) || currentConsumed < 0) currentConsumed = Number(current.used);

        if (!explicitConsumed && Number(incoming.used) === 0 && Number.isFinite(currentConsumed) && currentConsumed > 0) {
          incoming.used = currentConsumed;
          incoming.serverConsumed = currentConsumed;
        }
        if (!Object.prototype.hasOwnProperty.call(incoming, 'serverConsumed') && Number.isFinite(currentConsumed) && currentConsumed >= 0) {
          incoming.serverConsumed = currentConsumed;
        }
        if (!Object.prototype.hasOwnProperty.call(incoming, 'userKey') && current.userKey) incoming.userKey = current.userKey;
        if (!Object.prototype.hasOwnProperty.call(incoming, 'serverRemaining') && Number.isFinite(Number(current.serverRemaining))) {
          incoming.serverRemaining = Number(current.serverRemaining);
          incoming.remaining = Number(current.serverRemaining);
        }
        value = JSON.stringify(Object.assign({}, current, incoming));
      }
      return priorSetItem.call(this, key, value);
    };
    guardedSetItem.__dhP0GuardWrapped = true;
    Storage.prototype.setItem = guardedSetItem;
  }

  function repairFromServer() {
    if (!loggedIn() || !global.DHAuth || typeof global.DHAuth.quota !== 'function') return;
    global.DHAuth.quota().then(function () {
      try {
        if (global.DHShell && typeof global.DHShell.renderProfile === 'function') {
          global.DHShell.renderProfile();
        }
      } catch (_) {}
    }).catch(function () {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(repairFromServer, 0); }, { once: true });
  } else {
    setTimeout(repairFromServer, 0);
  }
})(window);
