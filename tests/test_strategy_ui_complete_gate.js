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
    navigator: {}, crypto: {randomUUID: () => 'ui-gate-session'},
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

const contract = (async () => {
  const {c, app, values, events} = harness();
  const resetS = () => {
    c.state.strategyAnswers = [];
    c.state.currentQuestion = 0;
    c.state.stage = 'strategies';
    c.state.journeyFinished = false;
  };
  // 6: starting a journey and reaching S is not locked by the new policy.
  c.startNewJourney();
  assert.equal(c.state.stage, 'realm');
  c.state.likedCodes = Array.from({length: 20}, (_, i) => 'M-' + i);
  c.finishSwipe();
  assert.equal(c.state.stage, 'introStrategies');
  c.goTo('strategies');
  assert.equal(c.state.stage, 'strategies');

  // 1 + 4: both continuation controls and forward dots are locked, no S skip.
  resetS();
  c.renderStrategy();
  assert.match(app.innerHTML, /disabled aria-disabled="true" onclick="nextStrategyStep\(\)"/);
  assert.match(app.innerHTML, /disabled aria-disabled="true" onclick="continueStrategy\(\)"/);
  assert.doesNotMatch(app.innerHTML, /رد کردن|Skip|بعداً|فعلاً نه/i);
  c.nextStrategyStep(); c.continueStrategy(); c.jumpStrategyQ(24);
  assert.equal(c.state.currentQuestion, 0);
  assert.equal(c.state.stage, 'strategies');
  for (const bad of [undefined, null, '', ' ', 'F', 'AB', '0', true, false, -1, 5, 0.5, NaN]) {
    c.state.strategyAnswers[0] = bad;
    c.nextStrategyStep(); c.continueStrategy(); c.jumpStrategyQ(1);
    assert.equal(c.state.currentQuestion, 0, 'Invalid choice cannot move forward: ' + bad);
    c.answerStrategy(bad);
    assert.equal(c.state.currentQuestion, 0);
  }

  // 2: internal 0..4 and normalized A..E permit continuation; no answer invention.
  for (const valid of [0, 1, 2, 3, 4, ' a ', 'b', ' C ', 'd', 'E']) {
    resetS(); c.state.strategyAnswers[0] = valid;
    c.renderStrategy();
    assert.doesNotMatch(app.innerHTML, /disabled[^>]*onclick="nextStrategyStep/);
    c.nextStrategyStep();
    assert.equal(c.state.currentQuestion, 1);
  }
  resetS();
  c.answerStrategy(0);
  assert.equal(c.state.strategyAnswers[0], 0);
  assert.equal(c.state.currentQuestion, 1);
  c.jumpStrategyQ(8);
  assert.equal(c.state.currentQuestion, 1, 'Cannot jump across a sparse unanswered prefix');
  c.previousStrategy();
  assert.equal(c.state.currentQuestion, 0, 'Backward review remains possible');
  c.jumpStrategyQ(1);
  assert.equal(c.state.currentQuestion, 1);

  // 3: complete via actual answer handlers, including E, to exactly 25 canonical keys.
  resetS();
  for (let i = 0; i < 25; i++) c.answerStrategy(i % 5);
  assert.equal(c.state.stage, 'introValues');
  const payload = c.buildPayload();
  assert.deepEqual(Object.keys(payload.sjt_answers).sort(),
    Array.from({length: 25}, (_, i) => 'sjt_' + (i + 1)).sort());
  assert.ok(Object.values(payload.sjt_answers).every(a => /^[A-E]$/.test(a)));
  c.state.strategyAnswers[0] = ' e ';
  assert.equal(c.buildPayload().sjt_answers.sjt_1, 'E');
  const originalId = c.state.strategyQuestions[24].id;
  c.state.strategyQuestions[24].id = 'S01';
  assert.equal(c.dhBuildSjtAnswers(), null, 'Duplicate question IDs cannot create a complete payload');
  c.state.strategyQuestions[24].id = originalId;

  // 5: interrupted/reloaded or corrupt sessions cannot discover, consume, or show S/results.
  resetS();
  c.answerStrategy(2);
  c.__dhInJourney = true;
  events.pagehide();
  const restored = harness(new Map(values));
  assert.equal(restored.c.loadSession(), true);
  assert.equal(restored.c.state.strategyAnswers[0], 2);
  assert.equal(restored.c.dhBuildSjtAnswers(), null);
  assert.throws(() => restored.c.buildPayload(), {code: 'INCOMPLETE_S_RESPONSES'});
  let consumed = 0, discovered = 0;
  restored.c.ensureJourneyChargedForResults = async () => { consumed++; };
  restored.c.fetchWithRetry = async () => { discovered++; throw new Error('Must not discover'); };
  await restored.c.analyzeMajors();
  await restored.c.analyzeBranches();
  assert.equal(consumed, 0);
  assert.equal(discovered, 0);
  assert.equal(restored.c.state.stage, 'introStrategies');
  assert.equal(restored.c.state.journeyFinished, false);
  assert.match(restored.app.innerHTML, /هر ۲۵ سؤال/);
  assert.equal(restored.c.displayResults({discovered_majors: [{name: 'fake', raw_components: {s_score: 99}}]}, 'majors'), false);
  assert.doesNotMatch(restored.app.innerHTML, /fake|۹۹/);
  for (const stage of ['introValues', 'values', 'choice', 'results']) {
    restored.c.state.stage = stage;
    restored.c.render();
    assert.equal(restored.c.state.stage, 'introStrategies', 'Restored/direct stage cannot bypass S: ' + stage);
    assert.equal(restored.c.dhIsStageUnlocked(stage), false);
  }

  // A non-null but invalid restored answer must not satisfy the 25-answer gate.
  for (const bad of [null, ' ', 'F', 'AB', '0', false, 5]) {
    c.state.strategyAnswers = Array(25).fill(0);
    c.state.strategyAnswers[7] = bad;
    assert.equal(c.dhBuildSjtAnswers(), null);
    assert.throws(() => c.buildPayload(), {code: 'INCOMPLETE_S_RESPONSES'});
    c.state.currentQuestion = 99;
    c.syncStrategyCursor();
    assert.equal(c.state.currentQuestion, 7);
  }
  // Answering the last question cannot leap over a hole in a resumed session.
  c.state.stage = 'strategies';
  c.state.strategyAnswers = Array(25).fill(0);
  c.state.strategyAnswers[7] = null;
  c.state.currentQuestion = 24;
  c.answerStrategy(4);
  assert.equal(c.state.stage, 'strategies');
  assert.equal(c.state.currentQuestion, 7);

  // Server #334 is authoritative even when local answers look complete.
  c.state.strategyAnswers = Array(25).fill(0);
  for (const data of [
    {s_assessment: {status: 'incomplete_s_responses', score: null}},
    {discovery_result: {s_assessment: {status: 'incomplete_s_responses', score: null}}},
    {branch_discovery_result: {incomplete_assessments: [{status: 'incomplete_s_responses', score: null}]}}
  ]) {
    assert.equal(c.displayResults(data, 'majors'), false);
    assert.equal(c.state.stage, 'introStrategies');
  }
  // Existing shell wrapper must not cache a blocked result or run its quota bookkeeping.
  let cached = 0, quotaWrites = 0;
  c.extractResultSummary = () => ({tops: ['fake']});
  c.saveLastResult = () => { cached++; };
  c.localQuota = () => ({used: 0});
  c.saveQuota = () => { quotaWrites++; };
  const shell = fs.readFileSync(path.join(root, 'docs/shell.js'), 'utf8');
  vm.runInContext(shell.slice(shell.indexOf('  function patchConsumeOnResults()'),
    shell.indexOf('  function tryAutoResumeJourney()')) + '\npatchConsumeOnResults();', c);
  assert.equal(c.displayResults({s_assessment: {status: 'incomplete_s_responses'}}, 'branches'), false);
  assert.equal(cached, 0);
  assert.equal(quotaWrites, 0);
  // The outer quota wrapper must also honor the explicit blocked-result sentinel.
  let wrapperConsumes = 0;
  c.global = c;
  c.ensureJourneySession = () => 'ui-gate-session';
  c.setJourneySession = () => {};
  c.SESSION_MEMORY = 'ui-gate-session';
  c.readJourney = () => ({sessionId: 'ui-gate-session'});
  c.loggedIn = () => true;
  c.consumeForJourney = async () => { wrapperConsumes++; };
  const quota = fs.readFileSync(path.join(root, 'docs/quota_runtime.js'), 'utf8');
  vm.runInContext(quota.slice(quota.indexOf('  function wrapResults()'),
    quota.indexOf('  function clampLegacyQuotaWrites()')) + '\nwrapResults();', c);
  assert.equal(c.displayResults({s_assessment: {status: 'incomplete_s_responses'}}, 'branches'), false);
  assert.equal(wrapperConsumes, 0);
  c.displayResults = () => undefined; // Positive control for the wrapper alone.
  c.wrapResults();
  c.displayResults({}, 'majors');
  assert.equal(wrapperConsumes, 1, 'Normal completed-result wrapper behavior is unchanged');
  console.log('S UI exact-25 contract: PASS (acceptance 1–6 + resume, payload and wrapper guards)');
})();
module.exports = contract;
if (require.main === module) contract.catch(error => { console.error(error); process.exitCode = 1; });
