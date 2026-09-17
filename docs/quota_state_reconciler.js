/* quota_state_reconciler.js v2
 * Keep the client quota cache additive/merge-based. Server state remains
 * authoritative; this only prevents legacy UI helpers from erasing the
 * persisted consumed count, identity, and server snapshot.
 */
(function (global) {
  'use strict';

  var KEY = 'dh_local_quota_v1';
  if (global.__dhQuotaStateReconcilerInstalled) return;
  global.__dhQuotaStateReconcilerInstalled = true;

  function parse(raw) {
    try {
      var value = JSON.parse(raw || 'null');
      return value && typeof value === 'object' ? value : {};
    } catch (_) {
      return {};
    }
  }

  function finiteNonNegative(v) {
    var n = Number(v);
    return Number.isFinite(n) && n >= 0 ? n : null;
  }

  var nativeSetItem = Storage.prototype.setItem;
  Storage.prototype.setItem = function (key, value) {
    if (key !== KEY) {
      return nativeSetItem.call(this, key, value);
    }

    var incoming = parse(value);
    var current = parse(this.getItem(KEY));
    var merged = Object.assign({}, current, incoming);

    var incomingUser = String(incoming.userKey || '');
    var currentUser = String(current.userKey || '');
    var sameUser = !!incomingUser && !!currentUser && incomingUser === currentUser;

    if (sameUser || (!incomingUser && currentUser)) {
      var incomingConsumed = finiteNonNegative(incoming.serverConsumed);
      var currentConsumed = finiteNonNegative(current.serverConsumed);
      if (incomingConsumed !== null) {
        merged.serverConsumed = incomingConsumed;
        merged.used = incomingConsumed;
      } else if (currentConsumed !== null) {
        merged.serverConsumed = currentConsumed;
        merged.used = currentConsumed;
      } else if (!Object.prototype.hasOwnProperty.call(incoming, 'used') && Object.prototype.hasOwnProperty.call(current, 'used')) {
        merged.used = current.used;
      }

      if (!Object.prototype.hasOwnProperty.call(incoming, 'serverRemaining') && Object.prototype.hasOwnProperty.call(current, 'serverRemaining')) {
        merged.serverRemaining = current.serverRemaining;
      }
      if (!Object.prototype.hasOwnProperty.call(incoming, 'serverGranted') && Object.prototype.hasOwnProperty.call(current, 'serverGranted')) {
        merged.serverGranted = current.serverGranted;
      }
      if (!Object.prototype.hasOwnProperty.call(incoming, 'userKey')) {
        merged.userKey = current.userKey;
      }
    }

    if (!incomingUser && currentUser) merged.userKey = currentUser;

    var remaining = finiteNonNegative(merged.serverRemaining);
    if (remaining !== null) merged.remaining = remaining;

    return nativeSetItem.call(this, key, JSON.stringify(merged));
  };

  function refresh() {
    try {
      if (global.DHAuth && typeof global.DHAuth.quota === 'function' &&
          global.DHAuth.isLoggedIn && global.DHAuth.isLoggedIn()) {
        global.DHAuth.quota().then(function (data) {
          try {
            var current = parse(localStorage.getItem(KEY));
            var consumed = finiteNonNegative(data && data.credits_consumed);
            var granted = finiteNonNegative(data && data.credits_granted);
            var remaining = finiteNonNegative(data && data.credits_remaining);
            var next = Object.assign({}, current, {
              userKey: (function () {
                try {
                  var u = global.DHAuth.getUser ? (global.DHAuth.getUser() || {}) : {};
                  return String(u.id || u.user_id || u.public_id || u.phone || u.mobile || '');
                } catch (_) { return current.userKey || ''; }
              })(),
              serverRemaining: remaining !== null ? remaining : current.serverRemaining,
              remaining: remaining !== null ? remaining : current.remaining,
              syncedAt: new Date().toISOString()
            });
            if (consumed !== null) {
              next.serverConsumed = consumed;
              next.used = consumed;
            }
            if (granted !== null) next.serverGranted = granted;
            localStorage.setItem(KEY, JSON.stringify(next));
          } catch (_) {}
        }).catch(function () {});
      }
    } catch (_) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(refresh, 0); }, { once: true });
  } else {
    setTimeout(refresh, 0);
  }
})(window);