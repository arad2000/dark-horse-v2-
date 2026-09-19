const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

function read(path) {
  return fs.readFileSync(path, 'utf8');
}

for (const file of [
  'docs/shell.js',
  'docs/commercial_ui.js',
  'docs/admin_feedback_ui_v1.js'
]) {
  assert.doesNotThrow(() => new vm.Script(read(file), { filename: file }), file + ' syntax regression');
}

const shell = read('docs/shell.js');
const commercial = read('docs/commercial_ui.js');
const admin = read('docs/admin_feedback_ui_v1.js');
const index = read('docs/index.html');

assert.ok(shell.includes('dh-commercial-ui-loader'));
assert.ok(shell.includes('commercial_ui.js?v=30'));
assert.ok(shell.includes('ورود موقتاً در دسترس نیست'));
assert.ok(!shell.includes('ماژول ورود/ثبت‌نام هنوز بارگذاری نشده. صفحه را یک‌بار تازه کنید.'));

assert.ok(commercial.includes("if(el('dh-admin-panel'))return;"));
assert.ok(admin.includes('id="dh-admin-feedback"'));
assert.ok(admin.includes('DHAuth.adminGrantCredits'));
assert.ok(admin.includes('DHAuth.adminDashboard'));
assert.ok(admin.includes('DHAuth.adminFeedback'));
assert.ok(admin.includes('پنل ادمین · بازخورد و اعتبار'));

const p = index.indexOf('profile_ux_v1.js?v=6');
const a = index.indexOf('admin_feedback_ui_v1.js?v=1');
const c = index.indexOf('commercial_ui.js?v=30');
assert.ok(p >= 0 && a > p && c > a, 'admin/auth UI load order is not deterministic');
assert.ok(index.includes('auth_api_client.js?v=10'));

console.log('auth_admin_panel_runtime regression: PASS');
