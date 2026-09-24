const fs = require('fs');
const assert = require('assert');

const purchaseSource = fs.readFileSync('docs/purchase_ui_fix.js', 'utf8');
const indexSource = fs.readFileSync('docs/index.html', 'utf8');

assert.match(
  purchaseSource,
  /function openPayment\(url\)[\s\S]*?global\.location\.assign\(target\)/
);
assert.doesNotMatch(purchaseSource, /intent:\/\//);
assert.doesNotMatch(purchaseSource, /AndroidBridge/);
assert.doesNotMatch(purchaseSource, /global\.open\(target/);

const openPaymentBody = purchaseSource.match(
  /function openPayment\(url\)\s*\{([\s\S]*?)\n  \}/
);
assert.ok(openPaymentBody, 'openPayment() must remain a focused helper');
assert.ok(
  openPaymentBody[1].indexOf('global.location.assign(target)') <
    openPaymentBody[1].indexOf('global.location.href = target'),
  'direct HTTPS navigation must be attempted before the href fallback'
);

assert.match(indexSource, /purchase_ui_fix\.js\?v=2/);
assert.doesNotMatch(indexSource, /purchase_ui_fix\.js\?v=1/);

console.log('payment navigation regression: PASS');
