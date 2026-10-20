'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const officialPoles = JSON.parse(fs.readFileSync(path.join(root, 'value_poles_v2.json'), 'utf8'));
const clientPoles = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/value_poles_v2.json'), 'utf8'));
const questions = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/questions_v2.json'), 'utf8'));
const appSource = fs.readFileSync(path.join(root, 'docs/app.js'), 'utf8');

assert.deepEqual(clientPoles, officialPoles, 'client value poles must exactly match the official V2 file');
const valueQuestions = questions.layers && questions.layers.values && questions.layers.values.questions;
assert.ok(Array.isArray(valueQuestions), 'questions_v2.json must provide V2 value questions');

const functionMatch = appSource.match(/function analyzeValueStyle\(answers\) \{[\s\S]*?\n\}/);
assert.ok(functionMatch, 'analyzeValueStyle must exist in docs/app.js');
const sandbox = { state: { valuePoles: clientPoles } };
vm.runInNewContext(functionMatch[0] + '\nthis.__analyzeValueStyle = analyzeValueStyle;', sandbox);

let checked = 0;
for (const question of valueQuestions) {
  for (const option of question.options || []) {
    const code = option.code;
    assert.ok(/^Q\d+[AB]$/.test(code), `unexpected V2 value option code: ${code}`);
    assert.ok(Object.prototype.hasOwnProperty.call(officialPoles, code), `missing official pole for ${code}`);
    const result = sandbox.__analyzeValueStyle([code]);
    assert.equal(result.values[0].label, officialPoles[code], `UI label mismatch for ${code}`);
    checked++;
  }
}
assert.equal(checked, 30, `expected 30 A/B V2 options, found ${checked}`);
console.log(`V2 value-style contract: PASS (${checked} option labels match the official poles)`);
