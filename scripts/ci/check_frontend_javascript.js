'use strict';

// Offline gate: no browser, server, provider, or database is started.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const docs = path.join(root, 'docs');

function parses(source) {
  const result = spawnSync(process.execPath, ['--check'], { input: source, encoding: 'utf8' });
  if (result.error) throw result.error;
  return result;
}

if (process.argv.includes('--self-test')) {
  assert.equal(parses('const paths = [{id: 1}, {id: 2}];').status, 0);
  assert.notEqual(parses('const paths = [{id: 1} {id: 2}];').status, 0,
    'The gate must reject the missing-comma regression in data.js');
}

const files = fs.readdirSync(docs).filter(name => name.endsWith('.js')).sort();
assert.ok(files.length > 0, 'No frontend scripts found');
for (const name of files) {
  const result = parses(fs.readFileSync(path.join(docs, name), 'utf8'));
  assert.equal(result.status, 0, `${name}: ${result.stderr}`);
}

const html = fs.readFileSync(path.join(docs, 'index.html'), 'utf8');
for (const match of html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["']/gi)) {
  const src = match[1];
  if (/^(?:https?:)?\/\//i.test(src)) continue;
  const file = path.resolve(docs, src.split(/[?#]/)[0]);
  assert.ok(file.startsWith(docs + path.sep), `Script outside docs: ${src}`);
  assert.ok(fs.statSync(file).isFile(), `Missing script: ${src}`);
}

// Exercise actual data declarations, not grep markers. No syntax repair in this check.
const data = vm.runInNewContext(
  fs.readFileSync(path.join(docs, 'data.js'), 'utf8') +
  '; JSON.stringify({realms: REALMS, paths: NARROW_PATHS});',
  Object.create(null), { timeout: 2000 }
);
const parsed = JSON.parse(data);
assert.ok(Array.isArray(parsed.realms) && parsed.realms.length > 0);
assert.ok(Object.values(parsed.paths).flat().length > 0);
for (const item of Object.values(parsed.paths).flat()) {
  assert.ok(item.id && Array.isArray(item.majorCodes) && item.majorCodes.length > 0,
    `Invalid narrow path: ${item.id}`);
}
console.log(`Frontend offline gate: PASS (${files.length} scripts parsed, index assets present, data.js evaluated)`);
