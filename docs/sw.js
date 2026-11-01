/* Dark Horse SW v80 — instant cached HTML shell + non-destructive cache migration.
 * Preserves previously cached static assets across SW upgrades instead of wiping
 * the user's cache on every version bump.
 */
const CACHE = 'darkhorse-v80';

self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (nextCache) {
      return caches.keys().then(function (keys) {
        var oldKeys = keys.filter(function (k) { return k !== CACHE; });
        return Promise.all(oldKeys.map(function (oldKey) {
          return caches.open(oldKey).then(function (oldCache) {
            if (typeof oldCache.keys !== 'function') return null;
            return oldCache.keys().then(function (requests) {
              return Promise.all(requests.map(function (req) {
                return nextCache.match(req).then(function (already) {
                  if (already) return null;
                  return oldCache.match(req).then(function (res) {
                    return res ? nextCache.put(req, res).catch(function () {}) : null;
                  });
                });
              }));
            });
          }).catch(function () {}).then(function () {
            return caches.delete(oldKey);
          });
        }));
      });
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('message', function (e) {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;
  if (url.pathname.indexOf('/api/') !== -1) {
    e.respondWith(fetch(req));
    return;
  }

  // Only public static boot dependencies may fall back after a slow network.
  // Keep fresh network-first semantics, but never block forever behind it.
  if (/\/spark_game\.js$/i.test(url.pathname) ||
      /\/data\/(micro_motives|questions_v2|trait_map_v3)\.json$/i.test(url.pathname) ||
      /\/trait_map_v3\.json$/i.test(url.pathname)) {
    var options = { cache: 'no-store', credentials: 'omit', redirect: 'error' };
    var staticNetwork = fetch(req, options).then(function (res) {
      if (!res || res.status !== 200 || res.type !== 'basic') throw new Error('Static asset unavailable');
      return caches.open(CACHE).then(function (c) {
        return c.put(req, res.clone()).catch(function () {});
      }).catch(function () {}).then(function () { return res; });
    });
    // A late successful response still refreshes the cache for the next visit.
    e.waitUntil(staticNetwork.then(function () {}, function () {}));
    e.respondWith(caches.match(req).catch(function () { return null; }).then(function (cached) {
      var timer;
      var deadline = new Promise(function (_, reject) {
        timer = setTimeout(function () { reject(new Error('Static asset timeout')); }, cached ? 1500 : 8000);
      });
      return Promise.race([staticNetwork, deadline]).catch(function (error) {
        if (cached) return cached;
        throw error; // Never substitute HTML or API data for a missing JS/JSON asset.
      }).finally(function () { clearTimeout(timer); });
    }));
    return;
  }

  var isJson = /\.json$/i.test(url.pathname);

  // HTML shell: serve the last known home immediately, then refresh it in the background.
  // Other JSON retains no-store network-first; the public boot allowlist above
  // additionally has a bounded cache fallback.
  if (/index\.html$/i.test(url.pathname) ||
      url.pathname === '/' ||
      /\/docs\/?$/.test(url.pathname)) {
    var htmlNetwork = fetch(req, { cache: 'no-store' });
    var htmlRefresh = htmlNetwork.then(function (res) {
      if (res && res.status === 200 && res.type === 'basic') {
        return caches.open(CACHE).then(function (c) {
          return c.put(req, res.clone()).catch(function () {});
        }).then(function () { return res; });
      }
      return res;
    });
    e.waitUntil(htmlRefresh.then(function () {}, function () {}));
    e.respondWith(
      caches.open(CACHE).then(function (c) {
        return c.match(req);
      }).then(function (cached) {
        if (cached) return cached;
        return htmlNetwork.catch(function () {
          return caches.match(req).then(function (r) {
            return r || caches.match('./index.html');
          });
        });
      }).catch(function () {
        return htmlNetwork;
      })
    );
    return;
  }

  // Versioned assets (?v=), fonts, and static media: instant cache hit; allow browser HTTP cache on miss.
  if (!isJson && (/[?&]v=/.test(url.search) || /\.(png|jpe?g|svg|webp|woff2?)$/i.test(url.pathname))) {
    e.respondWith(
      caches.open(CACHE).then(function (c) {
        return c.match(req).then(function (cached) {
          var net = fetch(req).then(function (res) {
            if (res && res.status === 200 && res.type === 'basic') {
              c.put(req, res.clone()).catch(function () {});
            }
            return res;
          });
          if (cached) {
            e.waitUntil(net.catch(function () {}));
            return cached;
          }
          return net;
        });
      })
    );
    return;
  }

  // Everything else (including JSON with no-store): network-first with cache fallback.
  var networkFetch = isJson ? fetch(req, { cache: 'no-store' }) : fetch(req);
  e.respondWith(
    networkFetch.then(function (res) {
      if (res && res.status === 200 && res.type === 'basic') {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(req, copy); }).catch(function () {});
      }
      return res;
    }).catch(function () {
      return caches.match(req).then(function (r) { return r || caches.match('./index.html'); });
    })
  );
});
