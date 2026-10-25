/* Dark Horse SW v62 — nuclear drop of stale PWA caches
 * Never precache versioned JS (old v59 list served deleted files).
 * HTML/JS/CSS always network-first with no-store.
 */
const CACHE = 'darkhorse-v62';

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

  var path = url.pathname + url.search;
  var isFresh = /\.(js|css)(\?|$)/i.test(path) ||
    /index\.html$/i.test(url.pathname) ||
    url.pathname === '/' ||
    /\/docs\/?$/.test(url.pathname);

  if (isFresh) {
    e.respondWith(
      fetch(req, { cache: 'no-store' }).catch(function () {
        return caches.match(req);
      })
    );
    return;
  }

  e.respondWith(
    fetch(req).then(function (res) {
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
