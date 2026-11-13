'use strict';
// Actual app.js + real 25-question catalog in a DOM/transport VM harness.
// No live API, quota, DB, or browser-device acceptance is claimed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8');
const questions = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/questions_v2.json'), 'utf8'));

let uuidCounter = 0;
function harness(storage) {
  const values = storage || new Map();
  const elements = new Map();
  const events = {};
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      innerHTML: '', textContent: '', style: {setProperty() {}},
      classList: {add() {}, remove() {}, toggle() {}},
      setAttribute() {}, appendChild() {}, querySelectorAll() { return []; },
      scrollIntoView() {}, scrollTo() {}
    });
    return elements.get(id);
  };
  const app = element('app');
  const context = {
    console, app, Map, Set, AbortController,
    localStorage: {
      getItem: k => values.get(k) || null,
      setItem: (k, v) => values.set(k, String(v)), removeItem: k => values.delete(k)
    },
    document: {
      readyState: 'loading', body: element('body'), head: element('head'),
      documentElement: element('html'), getElementById: element,
      createElement: element, querySelectorAll: () => [], querySelector: () => null,
      addEventListener() {}
    },
    DHShell: {renderHome() {}, setActiveTab() {}},
    addEventListener: (name, fn) => { events[name] = fn; },
    setTimeout: () => 1, clearTimeout() {}, setInterval: () => 1, clearInterval() {},
    requestAnimationFrame: () => 1, scrollTo() {}, confirm: () => true,
    location: {search: '', href: 'https://example.test/'},
    navigator: {}, crypto: {randomUUID: () => 'display-seed-' + (++uuidCounter)},
    fetch: async () => { throw new Error('No network permitted in UI contract harness'); }
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root, 'docs/data.js'), 'utf8'), context);
  vm.runInContext(source, context, {filename: 'docs/app.js'});
  context.state.strategyQuestions = JSON.parse(JSON.stringify(questions.layers.strategies.questions));
  context.state.valueQuestions = JSON.parse(JSON.stringify(questions.layers.values.questions));
  context.state.questionsReady = true;
  return {c: context, app, values, events};
}

const {c, app, values} = harness();
const original = JSON.stringify(questions);
const realmIds = () => Array.from(app.innerHTML.matchAll(/onclick="toggleRealm\('([^']+)'\)"/g), m => m[1]);
const sIds = () => Array.from(app.innerHTML.matchAll(/onclick="answerStrategy\((\d)\)"/g), m => Number(m[1]));
const vIds = () => Array.from(app.innerHTML.matchAll(/onclick="answerValue\('([^']+)'\)"/g), m => m[1]);
c.state.displayShuffleSeed = 'fixed-test-seed';
c.state.selectedRealms = ['speaker', 'healer'];
c.renderRealm();
const realms = realmIds();
assert.equal(realms.length, 6);
assert.equal(new Set(realms).size, 6);
c.renderRealm();
assert.deepEqual(realmIds(), realms);
assert.deepEqual(Array.from(c.state.selectedRealms), ['speaker', 'healer']);

// Every displayed option retains its canonical answer, text, and payload key.
c.state.strategyAnswers = Array(25).fill(0);
for (let q = 0; q < 25; q++) {
  c.state.currentQuestion = q;
  c.renderStrategy();
  const ids = sIds();
  assert.deepEqual([...ids].sort(), [0, 1, 2, 3, 4]);
  for (const id of ids) {
    c.state.currentQuestion = q;
    c.renderStrategy();
    const option = questions.layers.strategies.questions[q].options.find(o => o.index === id);
    assert.ok(app.innerHTML.includes('onclick="answerStrategy(' + id + ')"'));
    const button = app.innerHTML.split('onclick="answerStrategy(' + id + ')"')[1].split('</button>')[0];
    assert.ok(button.includes(c.escapeHtml(option.text)), 'Canonical index stays attached to its text');
    c.state.currentQuestion = q;
    c.answerStrategy(id);
    assert.equal(c.state.strategyAnswers[q], id);
    assert.equal(c.buildPayload().sjt_answers['sjt_' + (q + 1)], String.fromCharCode(65 + id));
  }
}
for (let q = 0; q < 15; q++) {
  c.state.currentValueQuestion = q;
  c.renderValue();
  const codes = vIds();
  assert.deepEqual([...codes].sort(), questions.layers.values.questions[q].options.map(o => o.code).sort());
  for (const code of codes) {
    c.state.currentValueQuestion = q;
    c.renderValue();
    const option = questions.layers.values.questions[q].options.find(o => o.code === code);
    const button = app.innerHTML.split('onclick="answerValue(\'' + code + '\')"')[1].split('</button>')[0];
    assert.ok(button.includes(c.escapeHtml(option.text)), 'V code stays attached to its text');
    c.state.currentValueQuestion = q;
    c.answerValue(code);
    assert.equal(c.state.valueAnswers[q], code);
    assert.equal(c.buildPayload().conjoint_choices['conj_' + (q + 1)], code);
  }
}
assert.equal(JSON.stringify(c.state.strategyQuestions), JSON.stringify(questions.layers.strategies.questions));
assert.equal(JSON.stringify(c.state.valueQuestions), JSON.stringify(questions.layers.values.questions));
assert.equal(JSON.stringify(questions), original);
const orderSnapshot = ctx => JSON.stringify([
  ctx.dhDisplayOrder(['a','b','c','d','e','f'], 'realms'),
  ...ctx.state.strategyQuestions.map(q => Array.from(ctx.dhDisplayOrder(q.options, 'S:' + q.id), o => o.index)),
  ...ctx.state.valueQuestions.map(q => Array.from(ctx.dhDisplayOrder(q.options, 'V:' + q.id), o => o.code))
]);
c.saveSession();
const expected = orderSnapshot(c);
const mounted = harness(values).c;
assert.equal(mounted.loadSession(), true);
assert.equal(orderSnapshot(mounted), expected, 'Reload preserves all display permutations');
mounted.__dhSavedSession = JSON.parse(values.get('darkhorse_session_v2'));
mounted.dhEnsureServerQuotaGate = () => true;
mounted.dhResumeFromSplash();
assert.equal(orderSnapshot(mounted), expected, 'Splash resume preserves all display permutations');
const legacy = JSON.parse(values.get('darkhorse_session_v2'));
delete legacy.displayShuffleSeed;
values.set('darkhorse_session_v2', JSON.stringify(legacy));
const oldA = harness(values).c, oldB = harness(values).c;
assert.equal(oldA.loadSession(), true); assert.equal(oldB.loadSession(), true);
assert.equal(orderSnapshot(oldA), orderSnapshot(oldB), 'Legacy resume remains stable');
assert.deepEqual(Array.from(oldA.state.strategyAnswers), Array.from(c.state.strategyAnswers));
const variants = new Set();
for (let i = 0; i < 12; i++) {
  c.fullResetState(true);
  c.saveSession();
  variants.add(orderSnapshot(c));
}
assert.ok(variants.size > 1, 'Fresh journeys can have different permutations');
console.log('Display shuffle: PASS (canonical S/V payloads, immutable catalogs, reload/resume, legacy and fresh journeys)');

// Pages uploads docs/ as site root: the versioned URL must resolve to this app.js.
const indexSource = fs.readFileSync(path.join(root, 'docs/index.html'), 'utf8');
const workflow = fs.readFileSync(path.join(root, '.github/workflows/publish-frontend-from-deploy.yml'), 'utf8');
const appScripts = Array.from(indexSource.matchAll(/<script\b[^>]*\bsrc="([^"]*app\.js[^"]*)"/g), m => m[1]);
assert.equal(appScripts.length, 1);
const scriptUrl = new URL(appScripts[0].replace(/&amp;/g, '&'), 'https://example.test/');
assert.equal(scriptUrl.pathname, '/app.js');
assert.equal(scriptUrl.searchParams.get('shuffle-v1'), '1');
assert.match(workflow, /uses: actions\/upload-pages-artifact@v3\s+with:\s+path: docs/);
assert.equal(fs.existsSync(path.join(root, 'app.js')), false, 'No competing root app.js');
const publishedSource = fs.readFileSync(path.join(root, 'docs', scriptUrl.pathname.slice(1)), 'utf8');
assert.equal(publishedSource, source);
assert.ok(publishedSource.includes('function dhDisplayOrder('));
assert.ok(publishedSource.includes('displayShuffleSeed'));
console.log('Pages source-root + shuffle-v1 cache-bust contract: PASS (not a downloaded/live artifact claim)');
