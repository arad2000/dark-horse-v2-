'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('docs/app.js', 'utf8');
const start = source.indexOf('function displayResults(');
const end = source.indexOf('// ==================== تحلیل سبک شخصی', start);
const app = {innerHTML: ''};
const sandbox = {app, window: {}, state: {strategyAnswers: [], valueAnswers: [], likedCodes: []},
  localStorage: {getItem: () => null}, progressHTML: () => '',
  escapeHtml: s => String(s).replaceAll('<', '&lt;').replaceAll('>', '&gt;')};
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);
const invalid = {major_name_fa: '<bad>', individuality_fit: {score: 85,
  status: 'no_discriminative_evidence', raw_components: {m_score: 80, v_score: null}}};
const incomplete = {score: null, v_result: {score: null, status: 'no_discriminative_evidence'}};
const valid = {major_name_fa: 'valid', individuality_fit: {score: 75,
  raw_components: {m_score: 80, s_score: 75, v_score: 70}}};
for (const payload of [
  {discovered_majors: [invalid]},
  {discovery_result: {recommendations: [invalid]}},
  {discovery_result: {recommendations: [], incomplete_assessments: [incomplete]}},
  {branch_discovery_result: {branches: [], incomplete_assessments: [incomplete]}},
  {recommended_branches: [{branch_name: 'null branch', average_score: 85,
    avg_components: {m_score: 80, v_score: null}, status: 'no_discriminative_evidence'}]},
]) {
  sandbox.displayResults(payload, 'majors');
  assert.match(app.innerHTML, /فاقد شواهد تمایزبخش/);
  assert.doesNotMatch(app.innerHTML, /NaN|null%|width:null|85%/);
  assert.doesNotMatch(app.innerHTML, /به آستانهٔ ۳۰٪ نرسیده/);
  assert.doesNotMatch(app.innerHTML, /<bad>/);
}
sandbox.displayResults({discovered_majors: [valid, invalid]}, 'majors');
assert.match(app.innerHTML, /75%/);
assert.match(app.innerHTML, /فاقد شواهد تمایزبخش/);
sandbox.displayResults({discovered_majors: [{major_name_fa:'zero', individuality_fit:{score:0,raw_components:{v_score:0,m_score:80}}}]},'majors');
assert.doesNotMatch(app.innerHTML, /فاقد شواهد تمایزبخش/);
sandbox.displayResults({branch_discovery_result: {branches: [], incomplete_assessments: [
  {score: null, v_result: {score: null, status: 'incomplete'}}]}}, 'branches');
assert.match(app.innerHTML, /اطلاعات ناکافی برای محاسبهٔ امتیاز/);
assert.doesNotMatch(app.innerHTML, /فاقد شواهد تمایزبخش|NaN|null%|width:null/);
console.log('V null consumer: PASS (real displayResults, DOM sink stub; no browser layout test)');

// Real Python engine output -> real displayResults. No JS imitation of Python round.
const {execFileSync} = require('node:child_process');
const boundaryFixtures = JSON.parse(execFileSync(process.env.PYTHON || 'python', ['-c', `
import json
from test_v_range_norm import total_boundary_engine, TotalThresholdTests
out = []
for raw, expected in [(.2990,29.9),(.2994,29.9),(.2996,30.0),(.3000,30.0),(.3004,30.0),
                      (.3996,40.0),(.5996,60.0),(.7996,80.0)]:
    with total_boundary_engine(raw) as engine:
        a = engine.discover_individuality([], TotalThresholdTests.sjt, TotalThresholdTests.values)
        b = engine.recommend_school_branch([], TotalThresholdTests.sjt, TotalThresholdTests.values)
    for row in a['discovered_majors']: row['major_name_fa'] = 'total-boundary-major'
    for row in b['recommended_branches']: row['branch_name'] = 'total-boundary-branch'
    out.append({'raw':raw, 'expected':expected, 'major':a, 'branch':b})
print(json.dumps(out))
`], {encoding: 'utf8'}));
assert.equal(boundaryFixtures.length, 8);
for (const fixture of boundaryFixtures) {
  const {major, branch, expected, raw} = fixture;
  assert.equal(branch.recommended_branches[0].average_score, expected);
  // Check both engine-native and API-shaped payloads; API itself has a Python contract test.
  const majorAPI = {discovery_result: {recommendations: major.discovered_majors.map(row => ({
    major_name_fa: row.major_name_fa, fit_score: row.individuality_fit.score,
    raw_components: row.individuality_fit.raw_components}))}};
  const branchAPI = {branch_discovery_result: {branches: branch.recommended_branches.map(row => ({
    branch_name_fa: row.branch_name, fit_score: row.average_score, avg_components: row.avg_components}))}};
  for (const [payload, type, name] of [[major, 'majors', 'total-boundary-major'],
      [majorAPI, 'majors', 'total-boundary-major'], [branch, 'branches', 'total-boundary-branch'],
      [branchAPI, 'branches', 'total-boundary-branch']]) {
    sandbox.displayResults(payload, type);
    const card = new RegExp('<h3[^>]*>' + name + '</h3>');
    if (expected >= 30) {
      assert.match(app.innerHTML, card, `raw=${raw}, type=${type}`);
      assert.ok(app.innerHTML.includes(`${expected}%`));
    } else {
      assert.doesNotMatch(app.innerHTML, card, `raw=${raw}, type=${type}`);
      assert.match(app.innerHTML, /به آستانهٔ ۳۰٪ نرسیده/);
    }
  }
}
console.log('Total policy B: PASS (8 real-engine boundaries x 4 consumer shapes; DOM stub, not browser E2E)');
