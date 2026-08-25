/* Dark Horse SW v50 — network-first shell (anti-cache) */
const CACHE = 'darkhorse-shell-v50';
const SHELL = [
  './', './index.html', './app.js', './data.js', './ux_v2_patch.js',
  './shell.js', './shell.css', './quotes_darkhorse.js', './auth_api_client.js',
  './spark_game.js', './parents.js', './stories.js', './poems.js',
  './pwa-boot.js', './manifest.json',
  './icon-192.png', './icon-512.png', './icon.png', './apple-touch-icon.png',
  './hero-journey.svg', './ico-compass.svg', './ico-bolt.svg', './ico-book.svg',
  './ico-quill.svg', './ico-parents.svg', './ico-home.svg', './ico-journey.svg',
  './ico-profile.svg', './ico-chevron.svg', './ico-bell.svg'
];

// فایل‌هایی که همیشه اول از شبکه بیایند
function isShellCritical(url) {
  const p = url.pathname || '';
  return /\/(index\.html|shell\.js|shell\.css|sw\.js)$/.test(p) || p.endsWith('/dark-horse-v2-/') || p.endsWith('/dark-horse-v2-');
}

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
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

  // Network-first برای shell
  if (isShellCritical(url)) {
    e.respondWith(
      fetch(req).then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }

  // بقیه: cache سپس شبکه
  e.respondWith(
    caches.open(CACHE).then((cache) =>
      cache.match(req).then((cached) => {
        const net = fetch(req).then((res) => {
          if (res && res.status === 200 && (res.type === 'basic' || res.type === 'cors')) {
            cache.put(req, res.clone());
          }
          return res;
        }).catch(() => cached);
        if (cached) { net.catch(() => {}); return cached; }
        return net;
      })
    )
  );
});
