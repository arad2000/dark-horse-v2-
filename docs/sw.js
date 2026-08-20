/* Dark Horse PWA SW v12 */
const CACHE = 'darkhorse-shell-v12';
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
  const url = new URL(e.request.url);
  if (url.origin.includes('onrender.com') || url.pathname.includes('/api/')) {
    e.respondWith(fetch(e.request));
    return;
  }
  const path = url.pathname || '';
  const isCode = path.endsWith('.js') || path.endsWith('.css') || path.endsWith('.html') || path.endsWith('/') || e.request.mode === 'navigate';
  if (isCode) {
    e.respondWith(
      fetch(e.request).then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      }).catch(() => caches.match(e.request).then((r) => r || caches.match('./index.html')))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request).then((cached) => cached || fetch(e.request).then((res) => {
      if (res && res.status === 200) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
      }
      return res;
    }))
  );
});
