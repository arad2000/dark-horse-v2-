/* quota_state_reconciler.js v1
 * Keep the client quota cache merge-based. Server state is authoritative;
 * this prevents legacy UI writers from erasing consumed-credit state.
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
    } catch (_) { return {}; }
  }

  var nativeSetItem = Storage.prototype.setItem;
  Storage.prototype.setItem = function (key, value) {
    if (key !== KEY) return nativeSetItem.call(this, key, value);
    var incoming = parse(value);
    var current = parse(this.getItem(KEY));
    var merged = Object.assign({}, current, incoming);
    var incomingUser = String(incoming.userKey || '');
    var currentUser = String(current.userKey || '');
    var sameUser = !!incomingUser && !!currentUser && incomingUser === currentUser;

    if (sameUser) {
      // Legacy writers may send only {remaining} or reset used to 0.
      // Preserve the server-synchronized consumed total in both cases.
      if (!Object.prototype.hasOwnProperty.call(incoming, 'used') ||
          (Number(incoming.used) === 0 && Number(current.used) > 0 &&
           !Object.prototype.hasOwnProperty.call(incoming, 'serverConsumed'))) {
        merged.used = current.used;
      }
      if (!Object.prototype.hasOwnProperty.call(incoming, 'serverRemaining') &&
          Object.prototype.hasOwnProperty.call(current, 'serverRemaining')) {
        merged.serverRemaining = current.serverRemaining;
      }
      if (!Object.prototype.hasOwnProperty.call(incoming, 'serverGranted') &&
          Object.prototype.hasOwnProperty.call(current, 'serverGranted')) {
        merged.serverGranted = current.serverGranted;
      }
      if (!Object.prototype.hasOwnProperty.call(incoming, 'userKey')) merged.userKey = current.userKey;
    }
    if (!incomingUser && currentUser) merged.userKey = currentUser;
    if (Number.isFinite(Number(merged.serverRemaining)) && Number(merged.serverRemaining) >= 0) {
      merged.remaining = Number(merged.serverRemaining);
    }
    return nativeSetItem.call(this, key, JSON.stringify(merged));
  };

  function refresh() {
    try {
      if (!global.DHAuth || typeof global.DHAuth.quota !== 'function' ||
          !global.DHAuth.isLoggedIn || !global.DHAuth.isLoggedIn()) return;
      global.DHAuth.quota().catch(function () {});
    } catch (_) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(refresh, 0); }, { once: true });
  } else {
    setTimeout(refresh, 0);
  }
})(window);
