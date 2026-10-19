'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');

const api = fs.readFileSync('main_v2.py', 'utf8');
const feedback = fs.readFileSync('feedback_api.py', 'utf8');

assert.match(api, /allow_origins=\["https:\/\/asbe-siah\.ir"\]/, 'CORS must allow only the canonical product web origin');
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
