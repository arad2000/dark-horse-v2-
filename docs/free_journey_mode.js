/* Compatibility stub: legacy free-journey mode is intentionally disabled.
 * Server-authoritative quota enforcement is mandatory for authenticated
 * commercial journeys. Kept only for stale-cache compatibility.
 */
(function (global) {
  'use strict';
  global.DHFreeJourney = {
    enabled: false,
    start: function () {}
  };
})(window);
