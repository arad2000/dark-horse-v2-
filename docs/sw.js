/* Dark Horse SW v79 — instant cached HTML shell + non-destructive cache migration.
 * Preserves previously cached static assets across SW upgrades instead of wiping
 * the user's cache on every version bump.
 */
const CACHE = 'darkhorse-v79';

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

  // Yehooyi must refresh even when cached HTML still references an old ?v= URL.
  // Only this script changes strategy; other journey assets keep their policy.
  if (/\/spark_game\.js$/i.test(url.pathname)) {
    e.respondWith(
      fetch(req, { cache: 'no-store', credentials: 'omit', redirect: 'error' }).then(function (res) {
        if (!res || res.status !== 200 || res.type !== 'basic') return res;
        return caches.open(CACHE).then(function (c) {
          return c.put(req, res.clone()).catch(function () {});
        }).then(function () { return res; });
      }).catch(function () { return caches.match(req); })
    );
    return;
  }

  var isJson = /\.json$/i.test(url.pathname);

  // HTML shell: serve the last known home immediately, then refresh it in the background.
  // Only HTML changes strategy here; JSON remains network-only with cache: 'no-store'.
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
