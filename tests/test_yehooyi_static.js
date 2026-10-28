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
function setup({ status = 200, hybrid = false, noThemes = false, noRoutes = false } = {}) {
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
  if (!noThemes) vm.runInContext(themes + '\nwindow.DH_WORLD_THEMES = DH_WORLD_THEMES;', ctx);
  vm.runInContext(lab, ctx);
  if (!noThemes) {
    for (const [id, title] of Object.entries(expected)) assert.equal(ctx.DH_WORLD_THEMES[id].title, title);
  }
  const index = ctx.DHSparkGame.buildPathIndex();
  const sourcePaths = vm.runInContext('Object.values(NARROW_PATHS).flat()', ctx);
  const sourceSubs = vm.runInContext('Object.values(SUB_REALMS).flat()', ctx);
  for (const hits of Object.values(index)) for (const hit of hits) {
    const p = sourcePaths.find(p => p.id === hit.pathId);
    const sub = sourceSubs.find(sub => sub.id === hit.subId);
    assert.equal(hit.pathName, p.name || p.motto, 'Exact display field from static path');
    assert.equal(hit.subName, sub.name || sub.motto, 'Exact display field from static subrealm');
    assert.equal(hit.realmName, 'محلهٔ ' + expected[hit.realmId]);
  }
  const fixture = Object.keys(expected).map(id => motives.find(m =>
    Object.entries(index).some(([prefix, hits]) => m.code.startsWith(prefix) && hits.some(h => h.realmId === id))));
  assert.ok(fixture.every(Boolean));
  ctx.fixture = hybrid ? [fixture[0]] : fixture;
  if (hybrid) {
    // Synthetic multi-realm link in memory only; repository data is never changed.
    ctx.hybridPrefix = fixture[0].code.slice(0, fixture[0].code.indexOf('-') + 1);
    vm.runInContext("NARROW_PATHS[SUB_REALMS.explorer[0].id].push({id:'test-hybrid',name:'مسیر آزمایشی',majorCodes:[hybridPrefix]}, {id:'invalid-sibling',name:'',motto:'',majorCodes:[hybridPrefix]})", ctx);
  }
  if (noRoutes) vm.runInContext('Object.keys(NARROW_PATHS).forEach(k => delete NARROW_PATHS[k]);', ctx);
  return { ctx, nodes, requests, storage, originalStorage };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
async function run() {
  const x = setup({ noThemes: true });
  x.ctx.DHSparkGame.open();
  await flush();
  assert.match(x.nodes.get('dh-spark-lab').innerHTML, /lab-card/);
  for (let i = 0; i < 6; i++) x.nodes.get('dh-lab-like').onclick();
  const result = x.nodes.get('dh-spark-lab').innerHTML;
  for (const title of Object.values(expected)) assert.ok(result.includes('محلهٔ ' + title), title + ' must render without app.js');
  for (const id of Object.keys(expected)) assert.ok(!result.includes(id), 'Never expose realm ID ' + id);
  assert.ok(!/نزدیک|محلهٔ مرتبط|پیشنهاد تقریبی|دیتابیس/.test(result));
  for (const heading of ['محله‌ها', 'گذرها', 'مسیرهای باریک']) assert.ok(result.includes('<h3>' + heading + '</h3>'));
  const idx = x.ctx.DHSparkGame.buildPathIndex();
  for (const m of x.ctx.fixture) {
    const hits = Object.entries(idx).filter(([pref]) => m.code.startsWith(pref)).flatMap(([, hits]) => hits);
    for (const hit of hits) {
      assert.ok(result.includes(hit.pathName), 'Exact path name/motto must render: ' + hit.pathId);
      assert.ok(result.includes(hit.subName), 'Exact subrealm name/motto must render: ' + hit.subId);
      assert.ok(!result.includes(hit.pathId) && !result.includes(hit.subId), 'No internal route IDs');
    }
  }
  assert.ok(!/یهویی رایگان است|نقشهٔ استاتیک شهرند|نه امتیاز یا تحلیل سروری/.test(result));
  const selectedList = result.match(/<h3>جرقه‌هایی که انتخاب کردی \(6\)<\/h3><ul>([\s\S]*?)<\/ul>/);
  assert.ok(selectedList, 'Selected sparks section must exist');
  assert.ok(!/<ul>|گذر:|مسیر باریک:|محلهٔ/.test(selectedList[1]), 'No nested route metadata under liked items');
  const escape = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const likedTexts = [...selectedList[1].matchAll(/<li>([\s\S]*?)<\/li>/g)].map(m => m[1]);
  assert.deepEqual(likedTexts.sort(), x.ctx.fixture.map(m => escape(m.description_fa)).sort(),
    'Liked list contains only the exact escaped spark texts');
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
  assert.ok(!hybridResult.includes('عنوان مسیر باریک در نقشهٔ استاتیک ثبت نشده'), 'Incomplete sibling hits must not render');
  assert.ok(!hybridResult.includes('invalid-sibling'));
  assert.ok(hybridResult.includes('مسیر آزمایشی'), 'Explicit Persian name takes precedence over motto');
  h.ctx.DHSparkGame.close();

  const u = setup({ noThemes: true, noRoutes: true });
  u.ctx.DHSparkGame.open(); await flush();
  const unmapped = u.nodes.get('dh-spark-lab').innerHTML;
  assert.match(unmapped, /بارگذاری خرده‌انگیزه‌ها ممکن نشد/);
  assert.ok(!unmapped.includes('lab-card'), 'No routes must fail closed, not show unlabelled sparks');
  assert.ok(!unmapped.includes('در نقشهٔ استاتیک محله/مسیر ثبت نشده'));
  u.ctx.DHSparkGame.close();

  const checks = setup({ noThemes: true });
  const candidate = checks.ctx.fixture[0];
  const prefix = candidate.code.slice(0, candidate.code.indexOf('-') + 1);
  const good = { realmId: 'healer', subName: 'گذر تست', pathName: 'مسیر تست' };
  for (const bad of [
    { ...good, realmId: 'unknown' }, { ...good, realmId: '' },
    { ...good, subName: '' }, { ...good, subName: '   ' },
    { ...good, pathName: '' }, { ...good, pathName: '   ' }
  ]) {
    assert.equal(checks.ctx.DHSparkGame.filterMotiveDrivenSparks([candidate], { [prefix]: [bad] }).length, 0);
  }
  assert.equal(checks.ctx.DHSparkGame.filterMotiveDrivenSparks([candidate], {}).length, 0);
  assert.equal(checks.ctx.DHSparkGame.filterMotiveDrivenSparks([candidate], { [prefix]: [good] }).length, 1);
  assert.equal(checks.ctx.DHSparkGame.filterMotiveDrivenSparks([candidate], {
    [prefix]: [{ ...good, pathName: '' }, good]
  }).length, 1, 'A valid chain is enough; invalid sibling hits must not invalidate it');

  const f = setup({ status: 404 });
  f.ctx.DHSparkGame.open(); await flush();
  assert.match(f.nodes.get('dh-spark-lab').innerHTML, /خطا در بارگذاری/);
  assert.equal(f.requests.length, 1, 'No backend fallback on static-asset error');
  f.nodes.get('dh-lab-x').onclick();
  assert.equal(f.ctx.DHSparkGame.isOpen(), false);
  console.log('Yehooyi static: PASS (API down → cards/results OK, six standalone Persian titles, exact path/subrealm labels, strict complete-chain filtering, multi-realm, no billing/session mutation, static error without API fallback)');
}
run().catch(err => { console.error(err); process.exitCode = 1; });
