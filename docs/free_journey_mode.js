/* Compatibility only: old HTML still loads this asset.
 * This does not enable free access or replace server-side quota checks.
 */
(function (global) {
  'use strict';
  global.DHFreeJourney = {
    enabled: false,
    start: function () {}
  };
})(window);
