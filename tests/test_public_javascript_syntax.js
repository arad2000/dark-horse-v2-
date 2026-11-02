'use strict';

// Parse public classic scripts without executing UI, fetch, storage or app code.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function scriptsIn(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) return scriptsIn(file);
    return entry.isFile() && file.endsWith('.js') ? [file] : [];
  }).sort();
}

const files = scriptsIn(path.join(root, 'docs'));
assert.ok(files.length > 0, 'Public JavaScript artifact must not be empty');
const failures = [];
for (const file of files) {
  try {
    new vm.Script(fs.readFileSync(file, 'utf8'), { filename: path.relative(root, file) });
  } catch (error) {
    failures.push(error.stack);
  }
}
if (failures.length) {
  console.error(failures.join('\n\n'));
  process.exitCode = 1;
} else {
  console.log(`Public JavaScript syntax: PASS (${files.length} scripts; parse only, no execution)`);
}
