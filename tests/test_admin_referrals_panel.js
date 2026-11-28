'use strict';
/* Referral admin panel contracts.
 *
 * Bug 1: the panel's "خروج" ended the whole account session. Leaving a panel and
 *        ending a login are different actions.
 * Bug 2: the commission rate must be the admin's own number, stored as sent and
 *        shown as stored - and the UI must fail loudly, not silently, when the
 *        API is too old to accept an edit.
 */
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');

const pagePath = path.join(__dirname, '..', 'docs', 'admin_referrals.html');
const page = fs.readFileSync(pagePath, 'utf8');
const inlineScript = page.match(/<script>([\s\S]*?)<\/script>/)[1];

function makeNode(tag) {
  const node = {
    tag: tag || 'div',
    _innerHTML: '',
    textContent: '',
    value: '',
    disabled: false,
    type: '',
    className: '',
    style: {},
    children: [],
    classList: { add() {}, remove() {}, toggle() {} },
    appendChild(child) { this.children.push(child); return child; },
    setAttribute(k, v) { this[k.replace(/-/g, '_')] = v; },
    get lastChild() { return this.children[this.children.length - 1] || makeNode(); }
  };
  // A real browser turns a table-row innerHTML string into cells. Mirror that so
  // the test exercises cell indices the page actually relies on.
  Object.defineProperty(node, 'innerHTML', {
    get: function () { return node._innerHTML; },
    set: function (html) {
      node._innerHTML = String(html);
      node.children = [];
      const cells = String(html).match(/<td\b/g) || [];
      for (let i = 0; i < cells.length; i++) node.children.push(makeNode('td'));
    }
  });
  return node;
}

function makeDocument() {
  const nodes = new Map();
  return {
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, makeNode('div'));
      return nodes.get(id);
    },
    createElement(tag) { return makeNode(tag); },
    readyState: 'complete',
    addEventListener() {}
  };
}

function run(options) {
  const opts = options || {};
  const document = makeDocument();
  const storage = new Map();
  if (opts.auth) storage.set('dh_auth_v1', JSON.stringify(opts.auth));
  const calls = [];
  const navigations = [];

  const context = {
    document: document,
    console: console,
    Date: Date,
    Promise: Promise,
    JSON: JSON,
    Number: Number,
    String: String,
    Math: Math,
    setTimeout: setTimeout,
    encodeURIComponent: encodeURIComponent,
    localStorage: {
      getItem: function (k) { return storage.has(k) ? storage.get(k) : null; },
      setItem: function (k, v) { storage.set(k, String(v)); },
      removeItem: function (k) { storage.delete(k); }
    },
    location: {
      search: '',
      replace: function (u) { navigations.push(u); }
    },
    history: { length: opts.historyLength || 1, back: function () { navigations.push('back'); } },
    fetch: function (url, init) {
      const body = init || {};
      const method = String(body.method || 'GET').toUpperCase();
      calls.push({ url: url, method: method, body: body.body });
      const res = opts.respond ? opts.respond(url, method, body.body) : null;
      if (!res) return Promise.reject(new Error('unexpected request ' + url));
      return Promise.resolve({
        ok: res.status >= 200 && res.status < 300,
        status: res.status,
        text: function () { return Promise.resolve(res.body == null ? '' : JSON.stringify(res.body)); }
      });
    }
  };
  context.location.href = '';
  Object.defineProperty(context.location, 'href', {
    get: function () { return ''; },
    set: function (u) { navigations.push(u); }
  });
  context.window = context;
  context.addEventListener = function () {};
  vm.createContext(context);
  vm.runInContext(inlineScript, context);
  return { document: document, storage: storage, calls: calls, navigations: navigations };
}

const settle = function () { return new Promise(function (r) { setTimeout(r, 0); }); };

function reports() {
  return {
    totals: { marketers: 2, signups: 4, confirmed_buyers: 1 },
    marketers: [
      {
        marketer_id: 7, name: 'M7', phone: null, commission_bps: 1500,
        commission_percent: 15, is_active: true, self_service: false,
        signups: 3, confirmed_buyers: 1, currencies: []
      },
      {
        marketer_id: 8, name: 'M8', phone: null, commission_bps: 0,
        commission_percent: 0, is_active: true, self_service: true,
        signups: 1, confirmed_buyers: 0, currencies: []
      }
    ]
  };
}

function baseResponder(overrides) {
  return function (url, method, body) {
    if (url.endsWith('/api/v1/me')) return { status: 200, body: { user: { name: 'ADMIN', role: 'admin' } } };
    if (url.endsWith('/api/v1/admin/marketers/report')) return { status: 200, body: reports() };
    if (url.endsWith('/api/v1/admin/referrals/report')) return { status: 200, body: {} };
    if (overrides && overrides[url]) return overrides[url](method, body);
    return null;
  };
}

async function main() {
  /* ---------- Bug 1: panel exit is not account logout ---------- */
  {
    const app = run({ auth: { token: 'T0K', user: { name: 'A' } }, respond: baseResponder() });
    await settle();
    app.document.getElementById('exit-panel').onclick();

    assert.strictEqual(app.navigations.indexOf('back'), -1,
      'with no history depth, exit goes to a concrete page rather than back()');
    assert.deepStrictEqual(app.navigations, ['index.html?tab=profile'],
      'exit returns to the signed-in profile');
    assert(app.storage.has('dh_auth_v1'), 'exit must keep the auth session');
    assert.strictEqual(JSON.parse(app.storage.get('dh_auth_v1')).token, 'T0K',
      'the token is untouched');
    assert(!page.includes('id="logout"'), 'there is no bare account-logout button on the panel');
    assert(!/removeItem\('dh_auth_v1'\)/.test(inlineScript),
      'the panel contains no code path that clears the auth key');
    assert(!/DHAuth\.logout|doLogout/.test(inlineScript),
      'the panel never calls the global logout');
  }

  /* ---------- Bug 1b: real history depth prefers back(), session kept ---------- */
  {
    const app = run({ auth: { token: 'T1' }, historyLength: 3, respond: baseResponder() });
    await settle();
    app.document.getElementById('exit-panel').onclick();
    assert.deepStrictEqual(app.navigations, ['back'], 'exit returns through history when possible');
    assert(app.storage.has('dh_auth_v1'), 'session survives a history-back exit');
  }

  /* ---------- Bug 2: displayed rate is the stored rate, including a real 0% ---------- */
  {
    const app = run({ auth: { token: 'T2' }, respond: baseResponder() });
    await settle();
    const rows = app.document.getElementById('marketers').children;
    assert.strictEqual(rows.length, 2, 'both marketers rendered');

    const firstRate = rows[0].children[2].children[0];
    const secondRate = rows[1].children[2].children[0];
    assert.strictEqual(firstRate.textContent, '۱۵٪', '15% renders from the stored value');
    assert.strictEqual(secondRate.textContent, '۰٪', 'a stored 0% is shown as 0%, not as unknown');
  }

  /* ---------- Bug 2: the admin's number is what gets sent ---------- */
  {
    let patchSeen = null;
    const responder = baseResponder({
      'https://api.asbe-siah.ir/api/v1/admin/marketers/7/commission': function (method, body) {
        patchSeen = { method: method, body: JSON.parse(body) };
        const bps = patchSeen.body.commission_bps;
        return { status: 200, body: { marketer_id: 7, commission_bps: bps, commission_percent: bps / 100 } };
      }
    });
    const app = run({ auth: { token: 'T3' }, respond: responder });
    await settle();

    const row = app.document.getElementById('marketers').children[0];
    const editBtn = row.children[7].children[1];
    assert.strictEqual(editBtn.textContent, 'ویرایش درصد', 'rate edit control exists');
    editBtn.onclick();

    const cell = row.children[2];
    const input = cell.children[0];
    const save = cell.children[1];
    assert.strictEqual(input.value, '15', 'editor starts from the stored rate');

    input.value = '23.5';
    save.onclick();
    await settle();

    assert(patchSeen, 'a request was sent on save');
    assert.strictEqual(patchSeen.method, 'PATCH', 'rate update uses PATCH');
    assert.strictEqual(patchSeen.body.commission_bps, 2350,
      "the admin's 23.5% is sent as 2350 bps - not a system default");
    assert.deepStrictEqual(Object.keys(patchSeen.body), ['commission_bps'],
      'nothing but the rate is mutated');

    // the saved value survives a reload of the report
    const savedRate = app.document.getElementById('marketers').children[0].children[2].children[0];
    assert.strictEqual(savedRate.textContent, '۱۵٪', 'table repaints from the server report after save');
  }

  /* ---------- Bug 2: out-of-range input is refused before any request ---------- */
  {
    const app = run({ auth: { token: 'T4' }, respond: baseResponder() });
    await settle();
    const row = app.document.getElementById('marketers').children[0];
    row.children[7].children[1].onclick();
    const cell = row.children[2];
    const before = app.calls.length;

    cell.children[0].value = '101';
    cell.children[1].onclick();
    await settle();
    assert.strictEqual(app.calls.length, before, 'rate above 100 is rejected without a request');
    assert(/۰ و ۱۰۰/.test(app.document.getElementById('error').textContent),
      'the operator is told the valid range');

    cell.children[0].value = '-1';
    cell.children[1].onclick();
    await settle();
    assert.strictEqual(app.calls.length, before, 'a negative rate is rejected without a request');
  }

  /* ---------- Bug 2: an API without the route must fail loudly ---------- */
  {
    const responder = baseResponder({
      'https://api.asbe-siah.ir/api/v1/admin/marketers/7/commission': function () {
        return { status: 404, body: { detail: 'Not Found' } };
      }
    });
    const app = run({ auth: { token: 'T5' }, respond: responder });
    await settle();
    const row = app.document.getElementById('marketers').children[0];
    row.children[7].children[1].onclick();
    const cell = row.children[2];
    cell.children[0].value = '30';
    cell.children[1].onclick();
    await settle();

    const err = app.document.getElementById('error').textContent;
    assert(/ذخیره نشد/.test(err),
      'a missing endpoint is reported as "not saved", never as success');
    assert(!/ذخیره شد/.test(app.document.getElementById('add-msg').textContent),
      'no success message is shown when the server rejected the change');
  }

  /* ---------- exit destination: ?tab=profile only lands when signed in ---------- */
  {
    const policy = fs.readFileSync(path.join(__dirname, '..', 'docs', 'post_auth_flow_policy.js'), 'utf8');
    function land(search, signedIn) {
      let rendered = 0;
      const ctx = {
        console: { log() {} },
        Promise: Promise,
        URLSearchParams: URLSearchParams,
        JSON: JSON,
        setTimeout: function () { return 0; },
        setInterval: function () { return 0; },
        clearInterval: function () {},
        document: {
          readyState: 'complete',
          addEventListener() {},
          getElementById() { return null; },
          querySelector() { return null; },
          body: null
        },
        localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
        location: { search: search },
        MutationObserver: undefined,
        DHAuth: { isLoggedIn() { return signedIn; }, quota() { return Promise.resolve({ credits_remaining: 0 }); } },
        DHShell: { renderProfile() { rendered += 1; }, startJourney() {} }
      };
      ctx.window = ctx;
      ctx.addEventListener = function () {};
      vm.createContext(ctx);
      vm.runInContext(policy, ctx);
      return rendered;
    }
    assert.strictEqual(land('?tab=profile', true), 1,
      'the exit destination lands on the profile for a signed-in operator');
    assert.strictEqual(land('?tab=profile', false), 0,
      'a signed-out visitor is not pushed into the profile');
    assert.strictEqual(land('', true), 0, 'no tab parameter means no navigation');
    assert.strictEqual(land('?tab=sanjesh', true), 0, 'other tab values are untouched');
  }

  console.log('PASS admin_referrals panel: exit != logout (session kept); admin-set rate sent, stored, shown, and failures surfaced');
}

main().catch(function (e) {
  console.error('FAIL', e && e.message);
  process.exit(1);
});
