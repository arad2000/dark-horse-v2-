const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const root = process.cwd();

const indexSource = fs.readFileSync('docs/index.html', 'utf8');
const bootSource = fs.readFileSync('docs/pwa-boot.js', 'utf8');
const swSource = fs.readFileSync('docs/sw.js', 'utf8');
const shellSource = fs.readFileSync('docs/shell.js', 'utf8');

function response(body, status = 200, type = 'basic') {
  return { body, status, type, clone() { return response(this.body, this.status, this.type); } };
}

function makeServiceWorker() {
  const listeners = {};
  const store = new Map();
  const fetchCalls = [];
  const timers = new Map();
  let timerId = 0;
  let mode = 'online';
  let serverBody = '<main>network-home-v1</main>';
  let pendingResolve = null;
  function key(req) {
    const value = typeof req === 'string' ? req : req.url;
    return new URL(value, 'https://asbe-siah.ir/sw.js').href;
  }
  const caches = {
    async open(name) {
      if (!store.has(name)) store.set(name, new Map());
      const map = store.get(name);
      return {
        async keys() { return Array.from(map.keys()).map(url => ({ url })); },
        async match(req) { return map.get(key(req)); },
        async put(req, res) { map.set(key(req), res.clone ? res.clone() : res); }
      };
    },
    async match(req) {
      const target = key(req);
      for (const map of store.values()) if (map.has(target)) return map.get(target);
      return undefined;
    },
    async keys() { return Array.from(store.keys()); },
    async delete(name) { return store.delete(name); }
  };
  const self = {
    location: { origin: 'https://asbe-siah.ir' },
    clients: { async claim() {} },
    skipWaiting() {},
    addEventListener(name, callback) { listeners[name] = callback; }
  };
  const fetch = (req, options) => {
    fetchCalls.push({ url: req.url, options: options || {} });
    if (mode === 'offline') return Promise.reject(new Error('simulated offline'));
    if (mode === 'pending') return new Promise(resolve => { pendingResolve = resolve; });
    return Promise.resolve(response(serverBody));
  };
  vm.runInNewContext(swSource, { self, caches, fetch, URL, Promise,
    setTimeout(fn, ms) { const id = ++timerId; timers.set(id, {fn, ms}); return id; },
    clearTimeout(id) { timers.delete(id); } });
  return {
    caches, fetchCalls,
    expire(ms) { for (const [id, timer] of [...timers]) if (timer.ms === ms) { timers.delete(id); timer.fn(); } },
    setOnline(body) { mode = 'online'; serverBody = body; },
    setOffline() { mode = 'offline'; },
    setPending() { mode = 'pending'; },
    resolvePending(body) {
      assert.ok(pendingResolve, 'expected pending network request');
      const resolve = pendingResolve; pendingResolve = null; resolve(response(body));
    },
    async cached(url) { return (await caches.open('darkhorse-v80')).match({ url }); },
    async triggerLifecycle(name) {
      const waiters = [];
      listeners[name]({ waitUntil(value) { waiters.push(Promise.resolve(value)); } });
      await Promise.all(waiters);
    },
    async dispatch(url) {
      let responsePromise;
      const waiters = [];
      const event = {
        request: { method: 'GET', url },
        respondWith(value) { responsePromise = Promise.resolve(value); },
        waitUntil(value) { waiters.push(Promise.resolve(value)); }
      };
      listeners.fetch(event);
      assert.ok(responsePromise, 'same-origin GET must use respondWith');
      return { responsePromise, waiters };
    }
  };
}

async function testStartupMarkup() {
  assert.match(indexSource, /id="dh-startup-home"/);
  assert.match(indexSource, /id="dh-startup-start"/);
  assert.match(indexSource, /__dhRequestStartupJourney/);
  assert.match(indexSource, /کشف رشته و شاخه بر اساس فردیت/);
  assert.match(indexSource, /id="dh-startup-open-sanjesh"/);
  assert.match(indexSource, /__dhRequestStartupSanjesh/);
  assert.doesNotMatch(indexSource, /dh-startup-pill|منطق هاروارد/);
  assert.ok(shellSource.includes('کشف رشته و شاخه بر اساس فردیت'));
  assert.ok(shellSource.includes('openSanjesh: openSanjeshFromShell'));
  assert.ok(indexSource.indexOf('id="dh-startup-home"') < indexSource.indexOf('data.js?v='),
    'startup shell must be present before deferred data/app scripts');
  assert.match(indexSource, /data\.js\?v=motives-1393-catalog-230-v1&narrow-fix=1/);
  assert.match(indexSource, /app\.js\?v=74/);
  assert.match(indexSource, /shell\.js\?v=92/);
  assert.match(shellSource, /commercial_ui\.js\?v=46/);
  assert.match(indexSource, /pwa-boot\.js\?v=80/);
  assert.match(indexSource, /shell\.css\?v=70&ux=phase4-live-v2(&r=\d+)?" media="print"/);
  assert.match(indexSource, /journey_experience\.css\?v=2" media="print"/);
  assert.match(indexSource, /journey_experience\.js\?v=2">/);
  assert.match(indexSource, /fonts\/Vazirmatn-Variable\.woff2/);
  assert.doesNotMatch(indexSource, /cdn\.jsdelivr\.net/);
  assert.doesNotMatch(indexSource, /home_update_banner_1405/);
  assert.strictEqual(fs.existsSync(path.join(root, 'docs', 'home_update_banner_1405.js')), false,
    'home_update_banner_1405.js must be completely removed');
  assert.strictEqual(fs.existsSync(path.join(root, 'docs', 'home_update_banner_1405.css')), false,
    'home_update_banner_1405.css must be completely removed');
  assert.match(indexSource, /<script defer src="payment_hop_boot\.js\?v=3"/);
  assert.ok(indexSource.indexOf('payment_hop_boot.js?v=3') < indexSource.indexOf('app.js?v=74'),
    'payment hop bootstrap must precede app.js');
  assert.doesNotMatch(indexSource, /phase3-161-176-1|۱۱۰۰|1100/);
  console.log('startup markup and cache-bust preservation: PASS');
}

async function testStartupButtonQueue() {
  const marker = 'window.__dhRequestStartupJourney = function ()';
  const at = indexSource.indexOf(marker);
  assert.ok(at >= 0, 'startup click handler not found');
  const start = indexSource.lastIndexOf('  <script>', at);
  const close = indexSource.indexOf('  </script>', at);
  assert.ok(start >= 0 && close > at, 'startup script bounds not found');
  const source = indexSource.slice(start, close + '  </script>'.length)
    .replace(/^  <script>\s*/, '').replace(/\s*  <\/script>$/, '');
  const listeners = {};
  const button = { disabled: false, textContent: 'شروع سفر' };
  const document = {
    readyState: 'loading',
    getElementById(id) { return id === 'dh-startup-start' ? button : null; },
    addEventListener(name, callback) { listeners[name] = callback; }
  };
  let authorizedStarts = 0;
  let directShellStarts = 0;
  const context = { document, setTimeout, Promise };
  context.window = context;
  vm.runInNewContext(source, context);
  context.__dhRequestStartupJourney();
  assert.strictEqual(button.disabled, true);
  assert.match(button.textContent, /در حال آماده‌سازی/);
  context.DHShell = { startJourney() { directShellStarts += 1; } };
  context.DHCommercialUI = { startServerAuthorizedJourney() { authorizedStarts += 1; } };
  listeners.DOMContentLoaded();
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.strictEqual(authorizedStarts, 1, 'queued CTA must pass through commercial auth/quota gate');
  assert.strictEqual(directShellStarts, 0, 'startup CTA must not bypass commercial auth/quota gate');
  console.log('startup CTA queued until app boot: PASS');
}

async function testSanjeshButtonQueue() {
  const marker = 'window.__dhRequestStartupSanjesh = function ()';
  const at = indexSource.indexOf(marker);
  assert.ok(at >= 0, 'startup Sanjesh click handler not found');
  const start = indexSource.lastIndexOf('  <script>', at);
  const close = indexSource.indexOf('  </script>', at);
  assert.ok(start >= 0 && close > at, 'startup script bounds not found');
  const source = indexSource.slice(start, close + '  </script>'.length)
    .replace(/^  <script>\s*/, '').replace(/\s*  <\/script>$/, '');
  const listeners = {};
  const button = { disabled: false, textContent: 'ورود به بخش سنجش' };
  const document = {
    readyState: 'loading',
    getElementById(id) { return id === 'dh-startup-open-sanjesh' ? button : null; },
    addEventListener(name, callback) { listeners[name] = callback; }
  };
  let opens = 0;
  const context = { document, setTimeout, Promise };
  context.window = context;
  vm.runInNewContext(source, context);
  context.__dhRequestStartupSanjesh();
  assert.strictEqual(button.disabled, true);
  assert.match(button.textContent, /در حال آماده‌سازی/);
  context.DHShell = { openSanjesh() { opens += 1; } };
  listeners.DOMContentLoaded();
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.strictEqual(opens, 1, 'queued Sanjesh CTA should open after scripts are ready');
  console.log('startup Sanjesh CTA queued until app boot: PASS');
}

async function testPwaRegistrationAndSingleReload() {
  const windowListeners = {};
  const swListeners = {};
  const registered = [];
  let reloads = 0;
  const data = new Map();
  const navigator = {
    standalone: false,
    serviceWorker: {
      register(url) { registered.push(url); return Promise.resolve({ update() {}, waiting: null }); },
      addEventListener(name, callback) { swListeners[name] = callback; }
    }
  };
  const document = {
    documentElement: { classList: { add() {} } },
    getElementById() { return null; },
    createElement() { throw new Error('unexpected install banner creation'); },
    body: { appendChild() {} }
  };
  const context = {
    navigator, document,
    sessionStorage: {
      getItem(key) { return data.has(key) ? data.get(key) : null; },
      setItem(key, value) { data.set(key, String(value)); }
    },
    setTimeout(fn) { return setTimeout(fn, 0); },
    Promise
  };
  context.window = context;
  context.matchMedia = () => ({ matches: false });
  context.addEventListener = (name, callback) => { windowListeners[name] = callback; };
  context.location = { reload() { reloads += 1; } };
  vm.runInNewContext(bootSource, context);
  windowListeners.load();
  await Promise.resolve();
  await Promise.resolve();
  assert.deepStrictEqual(registered, ['./sw.js?v=80']);
  swListeners.controllerchange();
  swListeners.controllerchange();
  assert.strictEqual(reloads, 1, 'controller changes must not cause repeated reloads');
  console.log('PWA registration and single-reload guard: PASS');
}

async function testColdWarmOfflineOnline() {
  const sw = makeServiceWorker();
  const homeUrl = 'https://asbe-siah.ir/';
  // Cold open: without a cached home, load from network and cache the shell.
  sw.setOnline('<main>network-home-v1</main>');
  const cold = await sw.dispatch(homeUrl);
  assert.strictEqual((await cold.responsePromise).body, '<main>network-home-v1</main>');
  await Promise.all(cold.waiters);
  assert.strictEqual((await sw.cached(homeUrl)).body, '<main>network-home-v1</main>');

  // Warm open: cached shell responds before a deliberately pending network request.
  sw.setPending();
  const warm = await sw.dispatch(homeUrl);
  const returnedFromCache = await Promise.race([
    warm.responsePromise.then(() => true),
    new Promise(resolve => setTimeout(() => resolve(false), 100))
  ]);
  assert.strictEqual(returnedFromCache, true, 'warm open must not wait for slow network');
  assert.strictEqual((await warm.responsePromise).body, '<main>network-home-v1</main>');
  sw.resolvePending('<main>network-home-v2</main>');
  await Promise.all(warm.waiters);
  assert.strictEqual((await sw.cached(homeUrl)).body, '<main>network-home-v2</main>');

  // A short offline interval serves the last cached shell; online recovery refreshes in background.
  sw.setOffline();
  const offline = await sw.dispatch(homeUrl);
  assert.strictEqual((await offline.responsePromise).body, '<main>network-home-v2</main>');
  await Promise.all(offline.waiters);
  sw.setOnline('<main>network-home-v3</main>');
  const online = await sw.dispatch(homeUrl);
  assert.strictEqual((await online.responsePromise).body, '<main>network-home-v2</main>');
  await Promise.all(online.waiters);
  assert.strictEqual((await sw.cached(homeUrl)).body, '<main>network-home-v3</main>');

  // Versioned JSON stays on the network/no-store path rather than the HTML cache-first branch.
  const jsonUrl = 'https://asbe-siah.ir/docs/data/micro_motives.json?v=motives-1393-v1';
  sw.setOnline('[{"code":"TEST-001"}]');
  const json = await sw.dispatch(jsonUrl);
  assert.strictEqual((await json.responsePromise).body, '[{"code":"TEST-001"}]');
  assert.ok(sw.fetchCalls.some(call => call.url === jsonUrl && call.options.cache === 'no-store'),
    'JSON must keep cache:no-store');
  await Promise.all(json.waiters);
  // A stale HTML document may request the old query string: fresh script wins.
  const sparkUrl = 'https://asbe-siah.ir/spark_game.js?v=yehooyi-static-v2';
  await (await sw.caches.open('darkhorse-v80')).put({url: sparkUrl}, response('old-lab'));
  sw.setOnline('new-exact-lab');
  const freshLab = await sw.dispatch(sparkUrl);
  assert.strictEqual((await freshLab.responsePromise).body, 'new-exact-lab');
  assert.ok(sw.fetchCalls.some(c => c.url === sparkUrl && c.options.cache === 'no-store'));
  assert.strictEqual((await sw.cached(sparkUrl)).body, 'new-exact-lab');
  sw.setOffline();
  const cachedLab = await sw.dispatch(sparkUrl);
  assert.strictEqual((await cachedLab.responsePromise).body, 'new-exact-lab');
  sw.setOnline('network-restored');
  // Non-destructive SW upgrade contract: install MUST NOT wipe existing caches, and activate
  // must carry forward unchanged cached assets from darkhorse-v77 into darkhorse-v80.
  const oldCache = await sw.caches.open('darkhorse-v77');
  const heavyAssetUrl = 'https://asbe-siah.ir/data.js?v=motives-1393-catalog-230-v1&narrow-fix=1&wood-fix=1&copy=grade9-v1';
  await oldCache.put({ url: heavyAssetUrl }, response('/* cached-data-js */'));
  await sw.triggerLifecycle('install');
  assert.ok((await sw.caches.open('darkhorse-v77')).match({ url: heavyAssetUrl }),
    'SW install MUST NOT wipe user cache during version upgrade');
  await sw.triggerLifecycle('activate');
  assert.strictEqual((await sw.cached(heavyAssetUrl)).body, '/* cached-data-js */',
    'SW activate must carry cached static assets forward into darkhorse-v80 without cold re-download');
  console.log('non-destructive SW cache migration: PASS');
  console.log('cold/warm open, offline/online recovery, JSON no-store: PASS');
}

async function testJourneyJsonDeadline() {
  const app = fs.readFileSync('docs/app.js', 'utf8');
  assert.doesNotMatch(app, /await fetch\(DATA_BASE \+ '(micro_motives|questions_v2|trait_map_v3)\.json/ ,
    'Fresh and resumed journeys must use the bounded static loader');
  const helper = app.slice(app.indexOf('function fetchJourneyJson('), app.indexOf('async function loadMicroMotivesMap()'));
  for (const mode of ['pending-fetch', 'pending-body', 'healthy', 'http-error']) {
    const timers = new Map(); let timerId = 0; let signal;
    const context = { Promise, AbortController,
      setTimeout(fn) { const id = ++timerId; timers.set(id, fn); return id; },
      clearTimeout(id) { timers.delete(id); },
      fetch(url, options) {
        assert.strictEqual(url, 'data/questions_v2.json'); signal = options.signal;
        if (mode === 'pending-fetch') return new Promise(() => {});
        return Promise.resolve({ok: mode !== 'http-error', json() {
          return mode === 'pending-body' ? new Promise(() => {}) : Promise.resolve({ready: true});
        }});
      }
    };
    vm.runInNewContext(helper, context);
    const request = context.fetchJourneyJson('data/questions_v2.json');
    if (mode.startsWith('pending')) {
      const rejected = assert.rejects(request, /Journey static data timeout/);
      for (let i = 0; i < 10; i++) await Promise.resolve();
      for (const fn of [...timers.values()]) fn();
      await rejected;
      assert.strictEqual(signal.aborted, true);
    } else if (mode === 'healthy') {
      assert.strictEqual((await request).ready, true);
    } else {
      await assert.rejects(request, /unavailable/);
    }
    assert.strictEqual(timers.size, 0, 'All deadline timers must be released');
  }
  console.log('journey JSON: fetch/body deadlines, abort, healthy/error paths, timer cleanup: PASS');
}

async function testSlowStaticFallback() {
  const flush = async () => { for (let i = 0; i < 30; i++) await Promise.resolve(); };
  for (const pathname of ['spark_game.js?v=yehooyi-simple-v5',
    'data/micro_motives.json', 'data/questions_v2.json', 'data/trait_map_v3.json', 'trait_map_v3.json']) {
    const sw = makeServiceWorker();
    const url = 'https://asbe-siah.ir/' + pathname;
    await (await sw.caches.open('darkhorse-v80')).put({url}, response('valid-cached-static'));
    sw.setPending();
    const event = await sw.dispatch(url);
    let settled = false;
    event.responsePromise.then(() => { settled = true; });
    await flush();
    assert.strictEqual(settled, false, 'Healthy network gets first opportunity');
    sw.expire(1500); await flush();
    assert.strictEqual(settled, true, 'Cached static response must settle by the deadline');
    assert.strictEqual((await event.responsePromise).body, 'valid-cached-static');
    assert.ok(sw.fetchCalls.every(call => call.options.cache === 'no-store'));
    sw.resolvePending('late-fresh-static');
    await Promise.all(event.waiters);
    assert.strictEqual((await sw.cached(url)).body, 'late-fresh-static');
  }
  const sw = makeServiceWorker();
  await (await sw.caches.open('darkhorse-v80')).put({url:'https://asbe-siah.ir/index.html'}, response('HTML-NOT-JSON'));
  sw.setPending();
  const cold = await sw.dispatch('https://asbe-siah.ir/data/questions_v2.json');
  let coldRejected = false;
  const rejected = assert.rejects(cold.responsePromise, /Static asset timeout/).then(() => { coldRejected = true; });
  await flush(); sw.expire(8000); await flush();
  assert.strictEqual(coldRejected, true, 'Cold static request must fail instead of hanging');
  await rejected;
  sw.resolvePending('recovered-json'); await Promise.all(cold.waiters);
  const apiUrl = 'https://asbe-siah.ir/api/v1/me/quota';
  await (await sw.caches.open('darkhorse-v80')).put({url:apiUrl}, response('UNTRUSTED-CACHED-QUOTA'));
  sw.setPending();
  const api = await sw.dispatch(apiUrl);
  let apiDone = false; api.responsePromise.then(() => { apiDone = true; });
  await flush(); sw.expire(1500); sw.expire(8000); await flush();
  assert.strictEqual(apiDone, false, 'Quota/API must never use static fallback');
  sw.resolvePending('authoritative-quota');
  assert.strictEqual((await api.responsePromise).body, 'authoritative-quota');
  console.log('slow static: cached deadline fallback, late refresh, cold timeout, no HTML substitution, API isolation: PASS');
}

(async () => {
  await testStartupMarkup();
  await testStartupButtonQueue();
  await testSanjeshButtonQueue();
  await testPwaRegistrationAndSingleReload();
  await testColdWarmOfflineOnline();
  await testSlowStaticFallback();
  await testJourneyJsonDeadline();
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
