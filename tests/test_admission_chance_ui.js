const fs = require('fs');
const assert = require('assert');

const source = fs.readFileSync('docs/admission_chance_ui.js', 'utf8');
const css = fs.readFileSync('docs/admission_chance_ui.css', 'utf8');
const indexSource = fs.readFileSync('docs/index.html', 'utf8');

assert.ok(source.includes('/api/v1/admission/chance'));
assert.match(source, /state\.majorsResult/);
assert.match(source, /major_ids/);
assert.match(source, /admission_path:\s*'exam'/);
assert.match(source, /admission_path:\s*'record'/);
assert.match(source, /rank_in_quota/);
assert.match(source, /region_zone/);
assert.match(source, /special_quota/);
assert.match(source, /gpa_written/);
assert.match(source, /gpa_total/);
assert.match(source, /PROVINCES/);
assert.match(source, /آذربایجان شرقی/);
assert.match(source, /یزد/);
assert.match(source, /isargaran_25/);
assert.match(source, /isargaran_5/);
assert.match(source, /shahid/);
assert.match(source, /نتایج تخمینی/);
assert.match(source, /جایگزین دفترچه و اعلام رسمی سنجش نیست/);
assert.match(source, /رتبه در سهمیه/);
assert.match(source, /معدل کتبی نهایی/);
assert.match(source, /معدل کل/);
assert.match(source, /ضریب معدل/);
assert.match(source, /معدل مؤثر/);
assert.match(source, /DHAdmissionChanceUI/);
assert.doesNotMatch(source, /quota_type/);
assert.doesNotMatch(source, /darkhorse\/discover/);
assert.doesNotMatch(source, /individuality_fit\s*=|individuality_fit\s*=/);

assert.match(css, /\.dh-admission-chance-widget/);
assert.match(css, /\.dh-admission-card/);
assert.match(css, /\.dh-admission-help/);
assert.match(css, /\.dh-admission-tabs/);
assert.match(css, /\.dh-admission-tab/);
assert.match(css, /@media/);

assert.match(indexSource, /admission_chance_ui\.css\?v=3/);
assert.match(indexSource, /admission_chance_ui\.js\?v=3/);

console.log('admission_chance_ui phase3 regression: PASS');
