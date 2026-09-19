const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const files = [
  'docs/shell.js',
  'docs/commercial_ui.js',
  'docs/admin_feedback_ui_v1.js',
  'docs/profile_ux_v1.js'
];

for (const file of files) {
  const source = fs.readFileSync(file, 'utf8');
  assert.doesNotThrow(() => new vm.Script(source, { filename: file }), file + ' syntax regression');
}

const shell = fs.readFileSync('docs/shell.js', 'utf8');
const commercial = fs.readFileSync('docs/commercial_ui.js', 'utf8');
const admin = fs.readFileSync('docs/admin_feedback_ui_v1.js', 'utf8');
const index = fs.readFileSync('docs/index.html', 'utf8');

assert.match(shell, /dh-commercial-ui-loader/);
assert.match(shell, /commercial_ui\.js\?v=30/);
assert.match(shell, /ورود موقتاً در دسترس نیست/);
assert.doesNotMatch(shell, /alert\('ماژول ورود\/ثبت‌نام هنوز بارگذاری نشده\. صفحه را یک‌بار تازه کنید。'\)/);

assert.match(commercial, /if\(el\('dh-admin-panel'\)\)return;/);
assert.match(admin, /id="dh-admin-feedback"/);
assert.match(admin, /DHAuth\.adminGrantCredits/);
assert.match(admin, /DHAuth\.adminDashboard/);
assert.match(admin, /DHAuth\.adminFeedback/);
assert.match(admin, /پنل ادمین · بازخورد و اعتبار/);
assert.match(index, /profile_ux_v1\.js\?v=6/);
assert.match(index, /admin_feedback_ui_v1\.js\?v=1/);
assert.match(index, /commercial_ui\.js\?v=30/);

const p = index.indexOf('profile_ux_v1.js?v=6');
const a = index.indexOf('admin_feedback_ui_v1.js?v=1');
const c = index.indexOf('commercial_ui.js?v=30');
assert.ok(p >= 0 && a > p && c > a, 'admin/auth UI load order is not deterministic');

console.log('auth_admin_panel_runtime regression: PASS');
