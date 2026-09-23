const fs = require('fs');
const assert = require('assert');

const source = fs.readFileSync('docs/admission_chance_ui.js', 'utf8');
const css = fs.readFileSync('docs/admission_chance_ui.css', 'utf8');
const indexSource = fs.readFileSync('docs/index.html', 'utf8');

assert.ok(source.includes('/api/v1/admission/chance'));
assert.match(source, /state\.majorsResult/);
assert.match(source, /major_ids/);
assert.match(source, /rank/);
assert.match(source, /region_zone/);
assert.match(source, /quota/);
assert.match(source, /province/);
assert.match(source, /نتایج تخمینی/);
assert.match(source, /جایگزین دفترچه و نتایج رسمی سنجش نیست/);
assert.match(source, /DHAdmissionChanceUI/);
assert.doesNotMatch(source, /darkhorse\/discover/);
assert.doesNotMatch(source, /individuality_fit\s*=|individuality_fit\s*=/);

assert.match(css, /\.dh-admission-chance-widget/);
assert.match(css, /\.dh-admission-card/);
assert.match(css, /@media/);

assert.match(indexSource, /admission_chance_ui\.css\?v=1/);
assert.match(indexSource, /admission_chance_ui\.js\?v=1/);

console.log('admission_chance_ui regression: PASS');
