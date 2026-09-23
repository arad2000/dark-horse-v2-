const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const authSource = fs.readFileSync('docs/auth_api_client.js', 'utf8');
const commercialSource = fs.readFileSync('docs/commercial_ui.js', 'utf8');
const adminFeedbackSource = fs.readFileSync('docs/admin_feedback_ui_v1.js', 'utf8');
const indexSource = fs.readFileSync('docs/index.html', 'utf8');
const shellSource = fs.readFileSync('docs/shell.js', 'utf8');
const profileSource = fs.readFileSync('docs/profile_ux_v1.js', 'utf8');

const pwaBootSource = fs.readFileSync('docs/pwa-boot.js', 'utf8');
const swSource = fs.readFileSync('docs/sw.js', 'utf8');

function storage(seed) {
  const data = new Map(Object.entries(seed || {}));
  return {
    getItem(key) { return data.has(key) ? data.get(key) : null; },
    setItem(key, value) { data.set(key, String(value)); },
    removeItem(key) { data.delete(key); }
  };
}

function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() { return body; }
  };
}

async function loadAuth(fetchImpl) {
  const context = {
    localStorage: storage({
      dh_auth_v1: JSON.stringify({
        token: 'admin-token',
        user: { id: 1, role: 'admin', status: 'active' }
      })
    }),
    fetch: fetchImpl,
    window: null,
    Date,
    JSON,
    Number,
    String,
    Object,
    Math,
    console,
    Promise
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(authSource, context);
  return context;
}

(async () => {
  let calls = [];
  const okContext = await loadAuth(async (url, options) => {
    calls.push({ url, options });
    return response(200, {
      entitlement_id: 88,
      user_id: 123,
      plan_id: 3,
      credits_granted: 3,
      credits_remaining: 3,
      status: 'active'
    });
  });

  const granted = await okContext.DHAuth.adminGrantCredits(123, 'pack_3_tests', 'هدیه مالک');
  assert.strictEqual(granted.user_id, 123);
  assert.strictEqual(granted.credits_granted, 3);
  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].url, 'https://api.asbe-siah.ir/api/v1/admin/credits/grant');
  assert.strictEqual(calls[0].options.method, 'POST');
  assert.strictEqual(calls[0].options.headers.Authorization, 'Bearer admin-token');
  assert.deepStrictEqual(JSON.parse(calls[0].options.body), {
    user_id: 123,
    plan_code: 'pack_3_tests',
    reason: 'هدیه مالک'
  });

  await assert.rejects(
    () => okContext.DHAuth.adminGrantCredits(0, 'pack_3_tests', 'هدیه مالک'),
    /شناسه کاربر باید یک عدد صحیح مثبت باشد/
  );

  const badContext = await loadAuth(async () =>
    response(400, { detail: 'unknown/inactive user or inactive plan' })
  );
  await assert.rejects(
    () => badContext.DHAuth.adminGrantCredits(999, 'pack_3_tests', 'هدیه مالک'),
    /کاربر پیدا نشد یا غیرفعال است، یا پلن فعال نیست/
  );

  assert.match(commercialSource, /if\(!isAdminUser\(\)\)return;/);
  assert.match(commercialSource, /id="dh-admin-grant-user-id"/);
  assert.match(commercialSource, /id="dh-admin-grant-plan"[^>]+value="pack_3_tests"/);
  assert.match(commercialSource, /id="dh-admin-grant-reason"[^>]+value="هدیه مالک"/);
  assert.match(commercialSource, /DHAuth\.adminGrantCredits/);
  assert.match(commercialSource, /اعتبار به کاربر/);
  assert.match(commercialSource, /payments_verified/);
  assert.match(commercialSource, /ناموفق\/لغوشده/);
  assert.match(commercialSource, /در انتظار/);
  assert.doesNotMatch(commercialSource, /محیط تست/);
  assert.match(adminFeedbackSource, /پرداخت موفق/);
  assert.match(adminFeedbackSource, /payments_verified/);
  assert.doesNotMatch(adminFeedbackSource, /payments_total/);
  assert.match(indexSource, /admin_feedback_ui_v1\.js\?v=2/);
  assert.match(commercialSource, /در حال اعطا/);
  assert.match(indexSource, /auth_api_client\.js\?v=10/);

  assert.match(shellSource, /dh-commercial-ui-loader/);
  assert.match(shellSource, /capturedError/);
  assert.match(shellSource, /خطای رابط ورود/);
  assert.match(shellSource, /commercial_ui\\.js\\?v=34/);
  assert.doesNotMatch(shellSource, /ماژول ورود\/ثبت‌نام هنوز بارگذاری نشده/);
  assert.match(commercialSource, /auth-ui-modal-root-missing/);
  assert.match(commercialSource, /showAuthModal failed/);
  assert.match(commercialSource, /__dhCommercialUIReady/);
  assert.match(indexSource, /shell\.js\?v=76/);
  assert.match(indexSource, /commercial_ui\\.js\\?v=34/);
  assert.match(indexSource, /profile_ux_v1\.js\?v=7/);
  assert.match(profileSource, /function adminUserId\(user\)/);
  assert.match(profileSource, /user\.user_id \|\| user\.id \|\| user\.userId/);
  assert.match(profileSource, /textContent = 'کپی'/);
  assert.match(profileSource, /textContent = 'اعطا'/);
  assert.match(profileSource, /dh-admin-grant-user-id/);
  assert.match(profileSource, /__dhAdminGrantSelectedUserId/);
  const adminSource = fs.readFileSync('docs/admin.html', 'utf8');
  assert.match(adminSource, /شناسه \/ user_id/);
  assert.match(adminSource, /class="pick-grant"/);
  assert.match(adminSource, /class="copy-user-id"/);
  assert.match(adminSource, /api\/v1\/admin\/credits\/grant/);
  assert.match(adminSource, /user_id:userId/);
  assert.match(indexSource, /pwa-boot\.js\?v=63/);
  assert.match(swSource, /darkhorse-v63/);


  console.log('admin_credit_grant_ui regression: PASS');
})();
