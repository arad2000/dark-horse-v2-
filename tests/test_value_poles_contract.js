const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const appSource = fs.readFileSync(path.join(root, 'docs', 'app.js'), 'utf8');
const indexSource = fs.readFileSync(path.join(root, 'docs', 'index.html'), 'utf8');
const canonicalPoles = JSON.parse(fs.readFileSync(path.join(root, 'value_poles_v2.json'), 'utf8'));

function extractFunction(src, fnName) {
  const marker = `function ${fnName}(`;
  const start = src.indexOf(marker);
  assert.notEqual(start, -1, `Missing function ${fnName} in docs/app.js`);
  let depth = 0;
  let opened = false;
  for (let i = start; i < src.length; i++) {
    if (src[i] === '{') {
      depth++;
      opened = true;
    } else if (src[i] === '}') {
      depth--;
      if (opened && depth === 0) {
        return src.slice(start, i + 1);
      }
    }
  }
  throw new Error(`Unbalanced braces for ${fnName}`);
}

function makeStorage(seed = {}) {
  const store = new Map(Object.entries(seed).map(([k, v]) => [k, String(v)]));
  return {
    getItem(k) { return store.has(k) ? store.get(k) : null; },
    setItem(k, v) { store.set(k, String(v)); },
    removeItem(k) { store.delete(k); },
    clear() { store.clear(); }
  };
}

// 1. Cache-bust contract in docs/index.html
assert.ok(
  indexSource.includes('app.js?v=73&poles-fix=1'),
  'docs/index.html must cache-bust app.js via ?v=73&poles-fix=1'
);

// 2. All 30 canonical poles in value_poles_v2.json must match analyzeValueStyle 1:1
const fnCode = [
  extractFunction(appSource, 'escapeHtml'),
  extractFunction(appSource, 'dhStrategyLetter'),
  extractFunction(appSource, 'durableJourneySessionIdForSave'),
  extractFunction(appSource, 'saveSession'),
  extractFunction(appSource, 'loadSession'),
  extractFunction(appSource, 'renderIntroValues'),
  extractFunction(appSource, 'dhResumeFromSplash'),
  extractFunction(appSource, 'analyzeValueStyle')
].join('\n\n');

const localStorage = makeStorage();
const appEl = { innerHTML: '' };
const sandbox = {
  localStorage,
  window: {},
  app: appEl,
  console,
  progressHTML: (id) => `<progress data-stage="${id}"></progress>`,
  fullResetState: () => {},
  render: () => {},
  state: {
    sessionId: null,
    stage: 'splash',
    history: [],
    selectedRealms: [],
    selectedSubRealms: [],
    selectedNarrowPaths: [],
    likedCodes: [],
    likedCodesSet: new Set(),
    strategyAnswers: [],
    valueAnswers: [],
    valueSchemaResetNotice: '',
    currentQuestion: 0,
    currentValueQuestion: 0,
    swipeIndex: 0,
    totalSwipes: 0,
    completedPaths: new Set(),
    completedSubRealms: new Set(),
    valueQuestions: Array.from({ length: 15 }, (_, i) => ({ id: `V${i + 1}`, number: i + 1 })),
    journeyFinished: false
  }
};
sandbox.window = sandbox;
vm.runInNewContext(fnCode, sandbox, { filename: 'docs/app.js' });

const canonicalKeys = Object.keys(canonicalPoles);
assert.equal(canonicalKeys.length, 30, 'value_poles_v2.json must define 30 poles');
for (const code of canonicalKeys) {
  const res = sandbox.analyzeValueStyle([code]);
  assert.equal(res.values[0].pole, canonicalPoles[code], `Pole mismatch on ${code}`);
  assert.ok(res.values[0].label.includes(canonicalPoles[code]), `Label mismatch on ${code}`);
  assert.equal(res.summary, canonicalPoles[code], `Summary mismatch on ${code}`);
}

const invertedCheck = sandbox.analyzeValueStyle({ Q3: 'A', Q8: 'A', Q14: 'B' });
assert.deepEqual(
  Array.from(invertedCheck.values.map((v) => v.pole)),
  ['عمق‌محور', 'آزادی‌خواه', 'استقلال‌طلب'],
  'Previously inverted Q3A, Q8A, Q14B poles must match canonical definitions'
);

// 3. Stale incomplete session without valueSchemaVersion must reset legacy valueAnswers
//    with explicit user message while preserving charged sessionId, sparks, and SJT answers
localStorage.setItem('dh_quota_charged_session_v1', 'charged-session-pr-a');
localStorage.setItem('darkhorse_session_v2', JSON.stringify({
  sessionId: 'charged-session-pr-a',
  stage: 'values',
  likedCodes: ['CS-001', 'CS-002'],
  strategyAnswers: [0, 1, 2],
  valueAnswers: ['Q3A', 'Q8A'],
  currentValueQuestion: 2,
  journeyFinished: false
}));

assert.equal(sandbox.loadSession(), true);
assert.equal(sandbox.state.sessionId, 'charged-session-pr-a', 'Paid/free sessionId must remain intact');
assert.deepEqual(Array.from(sandbox.state.likedCodes), ['CS-001', 'CS-002']);
assert.deepEqual(Array.from(sandbox.state.strategyAnswers), [0, 1, 2]);
assert.deepEqual(Array.from(sandbox.state.valueAnswers), [], 'Legacy unversioned valueAnswers must be cleared');
assert.equal(sandbox.state.currentValueQuestion, 0);
assert.equal(sandbox.state.stage, 'introValues', 'Stage must rewind from values to introValues');
assert.ok(sandbox.state.valueSchemaResetNotice.includes('بازنشانی'), 'Clear reset notice must be populated');

sandbox.renderIntroValues();
assert.ok(appEl.innerHTML.includes('data-dh-value-schema-reset="1"'), 'Reset banner must render in introValues UI');
assert.ok(appEl.innerHTML.includes('بازنشانی شد'), 'Persian reset explanation must be shown to user');

// 4. Current-version incomplete session saved by saveSession() resumes cleanly with no reset
sandbox.state.valueSchemaResetNotice = '';
sandbox.state.stage = 'values';
sandbox.state.valueAnswers = ['Q1A', 'Q3A'];
sandbox.state.currentValueQuestion = 2;
sandbox.saveSession();

sandbox.state.valueAnswers = [];
sandbox.state.currentValueQuestion = 0;
assert.equal(sandbox.loadSession(), true);
assert.deepEqual(Array.from(sandbox.state.valueAnswers), ['Q1A', 'Q3A']);
assert.equal(sandbox.state.currentValueQuestion, 2);
assert.equal(sandbox.state.valueSchemaResetNotice, '');

console.log('PR-A value-poles & incomplete-session schema guard contract: PASS (30/30 poles + localStorage guard verified)');
