const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

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
      return { async match(req) { return map.get(key(req)); }, async put(req, res) { map.set(key(req), res.clone ? res.clone() : res); } };
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
  vm.runInNewContext(swSource, { self, caches, fetch, URL, Promise });
  return {
    caches, fetchCalls,
    setOnline(body) { mode = 'online'; serverBody = body; },
    setOffline() { mode = 'offline'; },
    setPending() { mode = 'pending'; },
    resolvePending(body) {
      assert.ok(pendingResolve, 'expected pending network request');
      const resolve = pendingResolve; pendingResolve = null; resolve(response(body));
    },
    async cached(url) { return (await caches.open('darkhorse-v68')).match({ url }); },
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
  assert.match(indexSource, /app\.js\?v=69/);
  assert.match(indexSource, /shell\.js\?v=84/);
  assert.match(indexSource, /pwa-boot\.js\?v=68/);
  assert.match(indexSource, /shell\.css\?v=65" media="print"/);
  assert.match(indexSource, /<script defer src="payment_hop_boot\.js\?v=3"/);
  assert.ok(indexSource.indexOf('payment_hop_boot.js?v=3') < indexSource.indexOf('app.js?v=69'),
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
  let starts = 0;
  const context = { document, setTimeout, Promise };
  context.window = context;
  vm.runInNewContext(source, context);
  context.__dhRequestStartupJourney();
  assert.strictEqual(button.disabled, true);
  assert.match(button.textContent, /در حال آماده‌سازی/);
  context.DHShell = { startJourney() { starts += 1; } };
  listeners.DOMContentLoaded();
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.strictEqual(starts, 1, 'queued CTA should launch when app shell is ready');
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
  assert.deepStrictEqual(registered, ['./sw.js?v=68']);
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
  console.log('cold/warm open, offline/online recovery, JSON no-store: PASS');
}

(async () => {
  await testStartupMarkup();
  await testStartupButtonQueue();
  await testSanjeshButtonQueue();
  await testPwaRegistrationAndSingleReload();
  await testColdWarmOfflineOnline();
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
