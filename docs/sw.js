/* Dark Horse SW v59 — nuclear cache reset */
const CACHE = 'darkhorse-v59';
const PRECACHE = [
  './index.html',
  './shell.js',
  './shell.css',
  './app.js',
  './data.js',
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
  // JS/CSS همیشه از شبکه (جلوگیری از کش کهنه دکمه خرید)
  try {
    const u = new URL(e.request.url);
    if (/\.(js|css)(\?|$)/i.test(u.pathname+u.search) || /commercial_ui|shell\.js|auth_api/i.test(u.href)) {
      e.respondWith(fetch(e.request).catch(function(){ return caches.match(e.request); }));
      return;
    }
  } catch (_) {}

  const req = e.request;
  if (req.method !== 'GET') return;
  let url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;
  if (url.pathname.includes('/api/')) {
    e.respondWith(fetch(req));
    return;
  }

  // همیشه اول شبکه — کش فقط پشتیبان آفلاین
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
