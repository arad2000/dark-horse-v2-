'use strict';
// Real static route data + shared UI themes + real lab, with all backend traffic denied.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const read = p => fs.readFileSync(path.join(root, p), 'utf8');
const lab = read('docs/spark_game.js');
const app = read('docs/app.js');
const themes = app.slice(app.indexOf('const DH_WORLD_THEMES ='), app.indexOf('window.DH_WORLD_THEMES ='));
const motives = JSON.parse(read('docs/data/micro_motives.json'));
const expected = {
  healer: 'درمان و زندگی', builder: 'ساختن و مهندسی', explorer: 'کشف و دانش',
  thinker: 'اندیشه و جامعه', artist: 'خلق و هنر', speaker: 'واژه و فرهنگ'
};
function setup({ status = 200, hybrid = false } = {}) {
  const nodes = new Map();
  function element() {
    let html = '';
    return {
      parentNode: null, classList: { add() {} },
      get innerHTML() { return html; },
      set innerHTML(value) {
        html = value;
        for (const [, id] of value.matchAll(/id="([^"]+)"/g)) nodes.set(id, element());
      },
      appendChild(el) { el.parentNode = this; nodes.set(el.id, el); },
      removeChild(el) { el.parentNode = null; nodes.delete(el.id); }
    };
  }
  const storage = new Map([
    ['darkhorse_session_v2', 'unchanged journey'],
    ['dh_quota_charged_session_v1', 'unchanged charged session'],
    ['dh_local_quota_v1', 'unchanged quota']
  ]);
  const originalStorage = new Map(storage);
  const requests = [];
  function forbidden() { throw new Error('Backend/paid journey is down and must not be called'); }
  const ctx = {
    console, Promise,
    document: { body: element(), head: element(), createElement: element,
      getElementById(id) { return nodes.get(id) || null; } },
    localStorage: { getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value) },
    setInterval() { return 1; }, clearInterval() {},
    DHShell: { setActiveTab() {}, restoreSparkTab() {}, startJourney: forbidden },
    DHCommercialUI: { startServerAuthorizedJourney: forbidden, showPurchase: forbidden },
    ensureJourneySession: forbidden, ensureJourneyDataLoaded: forbidden,
    dhPushSubView() {},
    fetch(url, options) {
      // Equivalent API-down environment: only the Pages asset can succeed.
      const resolved = new URL(url, 'https://asbe-siah.ir/site/');
      requests.push(resolved.href);
      if (resolved.origin !== 'https://asbe-siah.ir' || resolved.pathname !== '/site/data/micro_motives.json') {
        return Promise.reject(new Error('API offline: ' + resolved.href));
      }
      assert.equal(options.mode, 'same-origin');
      assert.equal(options.credentials, 'omit');
      assert.equal(options.redirect, 'error');
      return Promise.resolve({ ok: status === 200, status, json: () => Promise.resolve(ctx.fixture) });
    }
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(read('docs/data.js'), ctx);
  vm.runInContext(themes + '\nwindow.DH_WORLD_THEMES = DH_WORLD_THEMES;', ctx);
  vm.runInContext(lab, ctx);
  for (const [id, title] of Object.entries(expected)) assert.equal(ctx.DH_WORLD_THEMES[id].title, title);
  const index = ctx.DHSparkGame.buildPathIndex();
  const fixture = Object.keys(expected).map(id => motives.find(m =>
    Object.entries(index).some(([prefix, hits]) => m.code.startsWith(prefix) && hits.some(h => h.realmId === id))));
  assert.ok(fixture.every(Boolean));
  ctx.fixture = hybrid ? [fixture[0]] : fixture;
  if (hybrid) {
    // Synthetic multi-realm link in memory only; repository data is never changed.
    ctx.hybridPrefix = fixture[0].code.slice(0, fixture[0].code.indexOf('-') + 1);
    vm.runInContext("NARROW_PATHS[SUB_REALMS.explorer[0].id].push({id:'test-hybrid',name:'مسیر آزمایشی',majorCodes:[hybridPrefix]})", ctx);
  }
  return { ctx, nodes, requests, storage, originalStorage };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
async function run() {
  const x = setup();
  x.ctx.DHSparkGame.open();
  await flush();
  assert.match(x.nodes.get('dh-spark-lab').innerHTML, /lab-card/);
  for (let i = 0; i < 6; i++) x.nodes.get('dh-lab-like').onclick();
  const result = x.nodes.get('dh-spark-lab').innerHTML;
  for (const title of Object.values(expected)) assert.ok(result.includes(title), title + ' must render');
  for (const id of Object.keys(expected)) assert.ok(!result.includes(id), 'Never expose realm ID ' + id);
  assert.match(result, /نه امتیاز یا تحلیل سروری/);
  assert.ok(!result.includes('dh-lab-start-journey'), 'No paid-journey CTA inside free results');
  assert.equal(x.requests.length, 1);
  for (const [key, value] of x.originalStorage) assert.equal(x.storage.get(key), value);
  assert.deepEqual([...x.storage.keys()].filter(k => !x.originalStorage.has(k)).sort(),
    ['dh_spark_badges_v1', 'dh_spark_lab_v1']);
  x.ctx.DHSparkGame.close();

  const h = setup({ hybrid: true });
  h.ctx.DHSparkGame.open(); await flush(); h.nodes.get('dh-lab-like').onclick();
  const hybridResult = h.nodes.get('dh-spark-lab').innerHTML;
  assert.ok(hybridResult.includes(expected.healer) && hybridResult.includes(expected.explorer),
    'A spark linked to multiple realms displays all their Persian names');
  h.ctx.DHSparkGame.close();

  const f = setup({ status: 404 });
  f.ctx.DHSparkGame.open(); await flush();
  assert.match(f.nodes.get('dh-spark-lab').innerHTML, /خطا در بارگذاری/);
  assert.equal(f.requests.length, 1, 'No backend fallback on static-asset error');
  f.nodes.get('dh-lab-x').onclick();
  assert.equal(f.ctx.DHSparkGame.isOpen(), false);
  console.log('Yehooyi static: PASS (API down → cards/results OK, six shared Persian titles, multi-realm, no billing/session mutation, static error without API fallback)');
}
run().catch(err => { console.error(err); process.exitCode = 1; });
