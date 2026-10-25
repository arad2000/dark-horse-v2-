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
  assert.match(app.innerHTML, /dh-model-limitations/);
  assert.match(app.innerHTML, /اعتبارسنجی تجربی آن هنوز احراز نشده/);
  assert.match(app.innerHTML, /درصد استعداد یا احتمال موفقیت و قبولی نیست/);
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
assert.match(app.innerHTML, /dh-model-limitations/);
assert.doesNotMatch(source, /هرچه بیشتر بزنی، دقیق‌تر کشف می‌شوی|خودِ واقعی‌ات را دقیق‌تر کشف می‌کنی/);
console.log('V null consumer: PASS (real displayResults, DOM sink stub; no browser layout test)');
