'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');

const api = fs.readFileSync('main_v2.py', 'utf8');
const feedback = fs.readFileSync('feedback_api.py', 'utf8');

assert.match(api, /allow_origins=_cors_allowed_origins\(\)/, 'CORS must use the explicit origin config');
const defaults = api.match(/origins = \[([\s\S]*?)\]/);
assert.ok(defaults, 'CORS defaults must be explicit');
assert.deepEqual([...defaults[1].matchAll(/"([^"]+)"/g)].map(m => m[1]), [
  'https://asbe-siah.ir',
  'https://www.asbe-siah.ir',
  'https://asbe-siah-web-test.liara.run',
]);
assert.doesNotMatch(api, /allow_origins=\["\*"\]/, 'wildcard CORS origins are forbidden');
assert.match(api, /MAX_DISCOVERY_PAYLOAD_BYTES\s*=\s*16\s*\*\s*1024/, 'discovery input cap must remain present');
assert.match(api, /MAX_COUNSEL_PAYLOAD_BYTES\s*=\s*32\s*\*\s*1024/, 'counsel input cap must remain present');
assert.match(api, /_enforce_payload_limit\([\s\S]*?MAX_DISCOVERY_PAYLOAD_BYTES/, 'bounded payload enforcement must be wired to discovery routes');
assert.match(feedback, /MAX_FEEDBACK_PAYLOAD_BYTES\s*=\s*32\s*\*\s*1024/, 'feedback routes must use a finite JSON input cap');
assert.equal((feedback.match(/_read_feedback_json_limited\(request\)/g) || []).length, 2, 'both current and legacy feedback routes must read bounded JSON');
assert.match(feedback, /status_code=413/, 'oversized feedback JSON must fail with HTTP 413');
assert.match(feedback, /@router\.post\(["']\/feedback["']\)/, 'existing feedback route must remain intact');
assert.match(feedback, /@legacy_router\.post\(["']\/api\/feedback\/submit["']\)/, 'existing legacy feedback route must remain intact');

console.log('R3 API security contract: PASS (origin allowlist, existing body caps, bounded feedback JSON, route compatibility)');
