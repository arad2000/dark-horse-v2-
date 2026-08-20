/* Dark Horse PWA SW v20 — app syntax fix */
const CACHE = 'darkhorse-shell-v20';
const SHELL = [
  './', './index.html', './app.js', './data.js', './ux_v2_patch.js',
  './shell.js', './shell.css', './quotes_darkhorse.js', './auth_api_client.js',
  './pwa-boot.js', './manifest.json',
  './icon-192.png', './icon-512.png', './icon.png', './apple-touch-icon.png'
];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin.includes('onrender.com') || url.pathname.includes('/api/')) {
    e.respondWith(fetch(req));
    return;
  }
  if (url.origin !== self.location.origin) return;
  e.respondWith(
    caches.open(CACHE).then((cache) =>
      cache.match(req).then((cached) => {
        const networkFetch = fetch(req).then((res) => {
          if (res && res.status === 200 && (res.type === 'basic' || res.type === 'cors')) {
            cache.put(req, res.clone());
          }
          return res;
        }).catch(() => cached);
        if (cached) { networkFetch.catch(() => {}); return cached; }
        return networkFetch;
      })
    )
  );
});
