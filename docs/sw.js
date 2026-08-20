/* Dark Horse PWA SW v18 — FAST open (cache-first) */
const CACHE = 'darkhorse-shell-v18';
const SHELL = [
  './',
  './index.html',
  './app.js',
  './data.js',
  './ux_v2_patch.js',
  './shell.js',
  './shell.css',
  './mobile-pwa.css',
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
    caches.open(CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
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
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // API همیشه شبکه
  if (url.origin.includes('onrender.com') || url.pathname.includes('/api/')) {
    event.respondWith(fetch(req));
    return;
  }

  // فقط same-origin
  if (url.origin !== self.location.origin) {
    return; // مثلا فونت CDN — مرورگر عادی
  }

  // استاتیک اپ: اول کش (سریع)، بعد در پس‌زمینه تازه کن
  event.respondWith(
    caches.open(CACHE).then((cache) =>
      cache.match(req).then((cached) => {
        const networkFetch = fetch(req)
          .then((res) => {
            if (res && res.status === 200 && (res.type === 'basic' || res.type === 'cors')) {
              cache.put(req, res.clone());
            }
            return res;
          })
          .catch(() => cached);

        // اگر در کش هست همان را فوری برگردان
        if (cached) {
          networkFetch.catch(() => {});
          return cached;
        }
        // اولین بار: از شبکه
        return networkFetch;
      })
    )
  );
});

// پیام برای اجبار آپدیت از صفحه (اختیاری)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
