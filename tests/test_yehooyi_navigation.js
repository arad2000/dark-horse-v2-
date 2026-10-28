'use strict';
// Offline VM regression: real shell navigation functions + real spark UI module.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const shell = fs.readFileSync(path.join(root, 'docs/shell.js'), 'utf8');
const spark = fs.readFileSync(path.join(root, 'docs/spark_game.js'), 'utf8');
function extract(name) {
  const match = shell.match(new RegExp('  function ' + name + '\\([^]*?\\n  }'));
  assert.ok(match, name + ' must exist');
  return match[0];
}
const nodes = new Map();
function element() {
  return {
    innerHTML: '', parentNode: null, attrs: {},
    setAttribute(k, v) { this.attrs[k] = v; },
    removeAttribute(k) { delete this.attrs[k]; },
    addEventListener() {},
    appendChild(el) { el.parentNode = this; if (el.id) nodes.set(el.id, el); },
    removeChild(el) { el.parentNode = null; nodes.delete(el.id); }
  };
}
const buttons = ['home', 'journey', 'spark', 'profile'].map(tab => ({
  selected: false, attrs: {},
  getAttribute() { return tab; },
  classList: { toggle(name, selected) { buttons.find(b => b.getAttribute() === tab).selected = selected; } },
  setAttribute(k, v) { this.attrs[k] = v; },
  removeAttribute(k) { delete this.attrs[k]; }
}));
const document = {
  body: element(), head: element(), createElement: element,
  getElementById(id) { return nodes.get(id) || null; },
  querySelectorAll() { return buttons; }
};
let starts = 0, history = 0, saved = 0, requests = 0;
const pending = [];
const ctx = {
  document, console, Promise,
  $: id => document.getElementById(id),
  dhHaptic() {}, stopFardiyatTicker() {}, shellScrollTop() {}, dhToast() {},
  saveSession() { saved++; },
  dhPushSubView() { history++; },
  startJourneyFromShell() { starts++; ctx.setActiveTab('journey'); },
  renderHome() { ctx.setActiveTab('home'); },
  renderProfile() { ctx.setActiveTab('profile'); },
  localStorage: { getItem() { return null; }, setItem() {} },
  fetch(url) {
    assert.equal(url, 'data/micro_motives.json', 'Existing JSON loading only; no journey/quota request');
    requests++; return new Promise(resolve => pending.push(resolve));
  },
  setInterval() { return 1; }, clearInterval() {}
};
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext("var activeTab = 'home', sparkReturnTab = 'home';\n" +
  ['ensureTabbar', 'restoreSparkTab', 'setActiveTab', 'switchTab'].map(extract).join('\n'), ctx);
ctx.DHShell = { setActiveTab: ctx.setActiveTab, restoreSparkTab: ctx.restoreSparkTab };
vm.runInContext(spark, ctx);
ctx.ensureTabbar();
assert.equal(nodes.get('dh-tabbar').attrs.dir, 'rtl');
const markup = nodes.get('dh-tabbar').innerHTML;
assert.deepEqual([...markup.matchAll(/data-tab="([^"]+)"/g)].map(m => m[1]),
  ['home', 'journey', 'spark', 'profile']);
assert.match(markup, /aria-label="یهویی"/);
assert.match(markup, /M12 3l2\.5 6\.5/); // Distinct four-point spark, not journey clock.
function active() { return buttons.filter(b => b.selected).map(b => b.getAttribute()); }
async function run() {
  ctx.setActiveTab('journey');
  ctx.switchTab('spark');
  assert.equal(starts, 0, 'Spark entry must not start a journey');
  assert.equal(saved, 0, 'Spark entry must not change journey persistence');
  assert.equal(requests, 1);
  assert.equal(ctx.DHSparkGame.isOpen(), true);
  assert.deepEqual(active(), ['spark']);
  assert.equal(buttons[2].attrs['aria-current'], 'page');
  const firstOverlay = nodes.get('dh-spark-lab');
  ctx.switchTab('spark');
  assert.equal(nodes.get('dh-spark-lab'), firstOverlay);
  assert.equal(requests, 1, 'Repeated tap must not restart or refetch');
  assert.equal(history, 1, 'Repeated tap must not duplicate history');
  ctx.DHSparkGame.close(); // Close button / existing hardware-back sheet handler.
  assert.deepEqual(active(), ['journey']);
  assert.equal(ctx.DHSparkGame.isOpen(), false);
  // Pending response after close must not write into a removed overlay.
  pending.shift()({ ok: true, json: () => Promise.resolve([]) });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(ctx.DHSparkGame.isOpen(), false);
  ctx.setActiveTab('profile');
  ctx.DHSparkGame.open(); // Same public entry used by the home shortcut.
  ctx.DHSparkGame.close();
  assert.deepEqual(active(), ['profile']);
  ctx.switchTab('spark');
  ctx.switchTab('home');
  assert.equal(ctx.DHSparkGame.isOpen(), false);
  assert.deepEqual(active(), ['home']);
  ctx.switchTab('spark');
  ctx.switchTab('profile');
  assert.equal(ctx.DHSparkGame.isOpen(), false);
  assert.deepEqual(active(), ['profile']);
  ctx.switchTab('spark');
  ctx.switchTab('journey');
  assert.equal(ctx.DHSparkGame.isOpen(), false);
  assert.equal(starts, 1, 'Only explicit journey navigation calls its existing entry');
  assert.deepEqual(active(), ['journey']);
  assert.match(spark, /padding:16px 14px calc\(100px \+ env\(safe-area-inset-bottom, 0px\)\)/);
  const index = fs.readFileSync(path.join(root, 'docs/index.html'), 'utf8');
  assert.match(index, /shell\.js\?v=91&/);
  assert.match(index, /spark_game\.js\?v=yehooyi-static-v2&/);
  console.log('Yehooyi navigation: PASS (4 tabs, direct entry, repeat tap, return tab, late response, home/profile/journey, cache-bust)');
}
run().catch(err => { console.error(err); process.exitCode = 1; });
