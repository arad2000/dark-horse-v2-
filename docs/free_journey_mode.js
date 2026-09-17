/* free_journey_mode.js — intentionally disabled.
 * Commercial quota enforcement is server-authoritative.
 * This compatibility stub prevents stale/cached HTML from restoring
 * the old free-access journey handlers.
 */
(function (global) {
  'use strict';

  global.DHFreeJourney = {
    enabled: false,
    start: function () {}
  };
})(window);
