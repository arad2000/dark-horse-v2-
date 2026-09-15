/* Dark Horse SW v59 — release hotfix cache reset */
const CACHE = 'darkhorse-v59';
const PRECACHE = [
  './index.html',
  './shell.js',
  './shell.css',
  './app.js',
  './data.js',
  './auth_api_client.js?v=2',
  './commercial_ui.js?v=2',
  './commercial_ui_bridge_v2.js?v=4',
  './password_reset_ui.js?v=2',
  './auth_ui_hotfix.js?v=1',
  './icon-192.png'
];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE).catch(function () {}))
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => {
        if (k !== CACHE) return caches.delete(k);
      }))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  let url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;
  if (url.pathname.includes('/api/')) {
    e.respondWith(fetch(req));
    return;
  }

  e.respondWith(
    fetch(req).then((res) => {
      if (res && res.status === 200 && res.type === 'basic') {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(function () {});
      }
      return res;
    }).catch(() => caches.match(req).then((r) => r || caches.match('./index.html')))
  );
});
