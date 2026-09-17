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
