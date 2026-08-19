/* Dark Horse PWA Service Worker v5 — network-first for app code */
const CACHE = 'darkhorse-shell-v6';
const SHELL = [
  './',
  './index.html',
  './app.js',
  './data.js',
  './ux_v2_patch.js',
  './shell.js',
  './shell.css',
  './quotes_darkhorse.js',
  './auth_api_client.js',
  './pwa-boot.js',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './icon.png',
  './apple-touch-icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  if (url.origin.includes('onrender.com') || url.pathname.includes('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  const path = url.pathname || '';
  const isAppCode =
    path.endsWith('.js') ||
    path.endsWith('.css') ||
    path.endsWith('.html') ||
    path.endsWith('/') ||
    event.request.mode === 'navigate';

  // کد اپ: اول شبکه، بعد کش (آپدیت سریع)
  if (isAppCode) {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(event.request, copy));
          }
          return res;
        })
        .catch(() => caches.match(event.request).then((r) => r || caches.match('./index.html')))
    );
    return;
  }

  // بقیه (آیکون و ...): کش اول
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((res) => {
        if (!res || res.status !== 200) return res;
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(event.request, copy));
        return res;
      });
    })
  );
});
