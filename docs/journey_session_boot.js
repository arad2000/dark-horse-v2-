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