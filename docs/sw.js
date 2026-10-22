/* Dark Horse SW v71 — instant cached HTML shell + fresh network updates.
 * JSON stays network-only with cache: 'no-store'; versioned assets stay guarded SWR.
 */
const CACHE = 'darkhorse-v71';

self.addEventListener('install', function (e) {
  self.skipWaiting();
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) { return caches.delete(k); }));
    })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k !== CACHE) return caches.delete(k);
      }));
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

  // Versioned assets (?v=) and static media: stale-while-revalidate —
  // serve cached content immediately, while keeping the background refresh alive.
  if (!isJson && (/[?&]v=/.test(url.search) || /\.(png|jpe?g|svg|webp|woff2?)$/i.test(url.pathname))) {
    var cachePromise = caches.open(CACHE);
    var networkPromise = cachePromise.then(function (c) {
      return fetch(req, { cache: 'no-store' }).then(function (res) {
        if (res && res.status === 200 && res.type === 'basic') {
          return c.put(req, res.clone()).catch(function () {}).then(function () { return res; });
        }
        return res;
      });
    });
    e.waitUntil(networkPromise.then(function () {}, function () {}));
    e.respondWith(cachePromise.then(function (c) {
      return c.match(req).then(function (cached) {
        return cached || networkPromise;
      });
    }));
    return;
  }

  // Everything else: network-first with cache fallback.
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
