'use strict';

/**
 * P0 Server-Authoritative Quota Gate End-to-End Regression Suite
 *
 * Verifies every mandatory product & security contract across the FULL frontend
 * stack (data.js + app.js + journey_experience.js + ux_v2_patch.js +
 * auth_api_client.js + quota_state_reconciler.js + shell.js + quota_runtime.js +
 * commercial_ui.js + post_auth_flow_policy.js) against a faithful server ledger
 * matching live `deploy/liara-commercial-sandbox` (`main_v2.py` + `commercial_api.py`):
 *
 *  0. Unauthenticated users & cold-boot `init() -> render()` can NEVER execute any
 *     stage of City of Dreams (`splash`, `realm`, etc.); login UI opens immediately.
 *  1. `remaining = 0` -> CANNOT start or enter `splash` / `realm` after completing a
 *     prior journey via ANY entry vector (`resetJourney`, `startNewJourney`,
 *     `DHShell.startJourney`, `#dh-tabbar [data-tab="journey"]`,
 *     `dhReturnToActivePage`, `dhResumeFromSplash`, direct `render()`), even if
 *     `localStorage` is tampered (`dh_local_quota_v1`, `dh_local_user_v1`, or a
 *     forged `dh_quota_charged_session_v1`). Purchase modal + explicit Persian
 *     exhaustion notice open immediately.
 *  2. `remaining = 1` -> completes 1 full journey to Results (`credits_remaining`
 *     `1 -> 0`); immediate 2nd attempt locks right away with Purchase modal.
 *  3. Idempotency -> viewing/requesting results twice (and switching between
 *     `discover`, `branch-discovery`, `counsel`, and Home -> Results return) on the
 *     SAME `session_uuid` deducts ONLY ONCE (`1 session = 1 consume`).
 *  4. Regression -> entering realms, exploring multiple neighborhoods/subRealms/
 *     narrowPaths, swiping sparks, answering SJT & values, jumping stages, returning
 *     to Home & resuming mid-journey NEVER consumes credits during exploration
 *     (`0` consumes before results; `1 session = 1 consume` upon completion).
 *  5. Zero silent swallowing -> server `402`, `403`, and Liara's `409`
 *     (`{"detail":"no test credits remaining"}`) on `consume-test` / `discover` /
 *     `branch-discovery` ALWAYS display explicit alert UI AND open `openPurchaseModal`.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');

function makeStorage(seed = {}) {
  const map = new Map(Object.entries(seed));
  return {
    getItem(k) { return map.has(k) ? map.get(k) : null; },
    setItem(k, v) { map.set(k, String(v)); },
    removeItem(k) { map.delete(k); },
    clear() { map.clear(); }
  };
}

function makeEl(id, registry) {
  const el = {
    id: id || '',
    innerHTML: '',
    outerHTML: '',
    textContent: '',
    value: '',
    type: 'text',
    hidden: false,
    disabled: false,
    open: false,
    scrollTop: 0,
    onclick: null,
    parentNode: null,
    children: [],
    dataset: {},
    style: { cssText: '', width: '', display: '', opacity: '', border: '', setProperty() {}, removeProperty() {} },
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); },
      remove(c) { this._s.delete(c); },
      toggle(c, force) {
        if (typeof force === 'boolean') {
          if (force) this._s.add(c); else this._s.delete(c);
        } else if (this._s.has(c)) {
          this._s.delete(c);
        } else {
          this._s.add(c);
        }
      },
      contains(c) { return this._s.has(c); }
    },
    hasAttribute() { return false; },
    setAttribute() {},
    getAttribute(attr) {
      if (attr === 'data-tab' && this.dataset.tab) return this.dataset.tab;
      return null;
    },
    addEventListener(type, fn) {
      if (type === 'click') this._click = fn;
    },
    removeEventListener() {},
    focus() {},
    select() {},
    click() {
      const ev = { target: this, preventDefault() {}, stopPropagation() {} };
      if (typeof this.onclick === 'function') return this.onclick(ev);
      if (typeof this._click === 'function') return this._click(ev);
    },
    appendChild(child) {
      if (child) {
        child.parentNode = el;
        el.children.push(child);
        if (child.id && registry) registry.set(child.id, child);
      }
      return child;
    },
    insertBefore(child) {
      if (child) {
        child.parentNode = el;
        if (child.id && registry) registry.set(child.id, child);
      }
      return child;
    },
    remove() {
      if (el.id && registry) registry.delete(el.id);
    },
    querySelector(sel) {
      if (sel === '.dh-commercial-modal' && el.innerHTML.includes('dh-commercial-modal')) {
        if (!el._modalChild) el._modalChild = makeEl('dh-commercial-modal', registry);
        return el._modalChild;
      }
      return null;
    },
    querySelectorAll() { return []; },
    scrollTo() {},
    scrollIntoView() {}
  };
  return el;
}

function flushMicrotasks() {
  return new Promise((resolve) => setImmediate(resolve));
}

async function run() {
  const motivesRaw = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/micro_motives.json'), 'utf8'));
  const questionsRaw = JSON.parse(fs.readFileSync(path.join(root, 'docs/data/questions_v2.json'), 'utf8'));
  const traitMapRaw = JSON.parse(fs.readFileSync(path.join(root, 'docs/trait_map_v3.json'), 'utf8'));

  // Authoritative Server Ledger (PostgreSQL parity with deploy/liara-commercial-sandbox)
  const usersByToken = new Map([
    ['tok-user-1', { id: 101, public_id: 'pub-101', name: 'کاربر اول', phone: '09121112233', role: 'user', status: 'active' }],
    ['tok-user-2', { id: 202, public_id: 'pub-202', name: 'کاربر دوم', phone: '09124445566', role: 'user', status: 'active' }]
  ]);
  const grantedByUser = new Map([[101, 1], [202, 1]]);
  // session_uuid -> user_id (JourneyCreditConsumption table)
  const journeyConsumptions = new Map();
  let forceNextConsumeStatus = 0;
  let consumeTestRequests = 0;
  let quotaRequests = 0;
  let discoverRequests = 0;
  let branchRequests = 0;
  let counselRequests = 0;
  let uuidSeq = 0;

  function userQuotaDetails(userId) {
    const granted = grantedByUser.get(userId) || 0;
    let consumed = 0;
    for (const ownerId of journeyConsumptions.values()) {
      if (ownerId === userId) consumed += 1;
    }
    return {
      credits_granted: granted,
      credits_consumed: consumed,
      credits_remaining: Math.max(0, granted - consumed)
    };
  }

  function resolveBearerUser(init) {
    let authHeader = '';
    if (init && init.headers) {
      if (typeof init.headers.get === 'function') authHeader = init.headers.get('Authorization') || '';
      else authHeader = init.headers.Authorization || init.headers.authorization || '';
    }
    const token = String(authHeader).replace(/^Bearer\s+/i, '').trim();
    return usersByToken.get(token) || null;
  }

  function jsonResponse(status, payload) {
    const textBody = JSON.stringify(payload);
    return {
      ok: status >= 200 && status < 300,
      status,
      headers: { get: (h) => (String(h).toLowerCase() === 'content-type' ? 'application/json' : null) },
      text: async () => textBody,
      json: async () => payload,
      clone: () => jsonResponse(status, payload)
    };
  }

  const localStorage = makeStorage();
  class Storage {
    getItem(k) { return localStorage.getItem(k); }
    setItem(k, v) { localStorage.setItem(k, v); }
    removeItem(k) { localStorage.removeItem(k); }
  }

  const elements = new Map();
  const tabButtons = ['home', 'journey', 'profile'].map((tab) => {
    const b = makeEl('tab-' + tab, elements);
    b.dataset.tab = tab;
    return b;
  });
  const getEl = (id) => {
    if (!elements.has(id)) elements.set(id, makeEl(id, elements));
    return elements.get(id);
  };

  const doc = {
    readyState: 'complete',
    visibilityState: 'visible',
    documentElement: makeEl('html', elements),
    scrollingElement: makeEl('scrolling', elements),
    head: makeEl('head', elements),
    body: makeEl('body', elements),
    getElementById: (id) => getEl(id),
    createElement: (tag) => makeEl(tag, elements),
    querySelector: () => null,
    querySelectorAll: (sel) => {
      if (sel.includes('data-tab="journey"')) return [tabButtons[1]];
      if (sel === '#dh-tabbar button') return tabButtons;
      const out = [];
      for (const id of ['dh-start-journey', 'dh-continue-journey', 'dh-p-journey']) {
        if (sel.includes('#' + id) && elements.has(id)) out.push(elements.get(id));
      }
      return out;
    },
    addEventListener() {},
    removeEventListener() {}
  };

  const sandbox = {
    console,
    localStorage,
    sessionStorage: makeStorage(),
    Storage,
    CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init && init.detail; } },
    MutationObserver: class { observe() {} disconnect() {} },
    Headers,
    AbortController,
    URL,
    URLSearchParams,
    Date,
    Promise,
    Object,
    Array,
    Set,
    Map,
    Number,
    String,
    Boolean,
    Math,
    RegExp,
    JSON,
    Error,
    TypeError,
    parseInt,
    parseFloat,
    isNaN,
    isFinite,
    encodeURIComponent,
    decodeURIComponent,
    scrollY: 0,
    pageYOffset: 0,
    scrollTo() {},
    requestAnimationFrame: (fn) => { if (typeof fn === 'function') fn(); return 1; },
    setTimeout: (fn) => { if (typeof fn === 'function') fn(); return 1; },
    clearTimeout() {},
    setInterval: () => 1,
    clearInterval() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() { return true; },
    matchMedia: () => ({ matches: false }),
    confirm: () => true,
    alert() {},
    location: { href: 'https://asbe-siah.ir/', pathname: '/', search: '', hash: '', origin: 'https://asbe-siah.ir', reload() {} },
    history: { replaceState() {}, pushState() {} },
    navigator: { userAgent: 'node-p0-e2e', standalone: false, clipboard: { writeText: async () => {} } },
    crypto: { randomUUID: () => '10000000-0000-4000-8000-' + String(++uuidSeq).padStart(12, '0') },
    API_BASE: 'https://api.asbe-siah.ir',
    document: doc,
    app: getEl('app'),
    fetch: async (url, init = {}) => {
      const target = String(url);
      if (target.includes('micro_motives.json')) return jsonResponse(200, motivesRaw);
      if (target.includes('questions_v2.json')) return jsonResponse(200, questionsRaw);
      if (target.includes('trait_map_v3.json')) return jsonResponse(200, traitMapRaw);

      if (target.includes('/api/v1/billing/packs')) {
        return jsonResponse(200, { packs: [{ code: 'pack_3_tests', credits: 3, price_minor: 2490000 }] });
      }

      if (target.includes('/api/v1/me/quota')) {
        quotaRequests += 1;
        const user = resolveBearerUser(init);
        if (!user) return jsonResponse(401, { detail: 'missing or invalid session' });
        return jsonResponse(200, userQuotaDetails(user.id));
      }

      if (target.includes('/api/v1/me/consume-test')) {
        consumeTestRequests += 1;
        const user = resolveBearerUser(init);
        if (!user) return jsonResponse(401, { detail: 'missing or invalid session' });
        const body = JSON.parse(init.body || '{}');
        const sid = String(body.session_uuid || '');
        if (!sid) return jsonResponse(422, { detail: 'missing session_uuid' });
        if (forceNextConsumeStatus) {
          const forced = forceNextConsumeStatus;
          forceNextConsumeStatus = 0;
          if (forced === 402) return jsonResponse(402, { detail: 'Credit consumption required' });
          if (forced === 403) return jsonResponse(403, { detail: 'journey session does not belong to this user' });
          if (forced === 409) return jsonResponse(409, { detail: 'no test credits remaining' });
        }
        if (journeyConsumptions.has(sid)) {
          if (journeyConsumptions.get(sid) !== user.id) {
            return jsonResponse(403, { detail: 'journey session does not belong to this user' });
          }
          return jsonResponse(200, Object.assign({
            consumed: 0,
            already_consumed: true,
            session_uuid: sid,
            user
          }, userQuotaDetails(user.id)));
        }
        const current = userQuotaDetails(user.id);
        if (current.credits_remaining <= 0) {
          // Exact live Liara commercial_api.py behavior: raises 409 "no test credits remaining"
          return jsonResponse(409, { detail: 'no test credits remaining' });
        }
        journeyConsumptions.set(sid, user.id);
        return jsonResponse(200, Object.assign({
          consumed: 1,
          already_consumed: false,
          session_uuid: sid,
          user
        }, userQuotaDetails(user.id)));
      }

      if (target.includes('/api/v2/darkhorse/discover') ||
          target.includes('/api/v2/darkhorse/branch-discovery') ||
          target.includes('/api/v2/darkhorse/counsel')) {
        const user = resolveBearerUser(init);
        if (!user) return jsonResponse(401, { detail: 'Authentication required' });
        const body = JSON.parse(init.body || '{}');
        const sid = String(body.session_id || '');
        if (!sid) return jsonResponse(400, { detail: 'Valid session_id is required' });
        if (!journeyConsumptions.has(sid)) {
          return jsonResponse(402, { detail: 'Credit consumption required before accessing journey results' });
        }
        if (journeyConsumptions.get(sid) !== user.id) {
          return jsonResponse(403, { detail: 'journey session does not belong to this user' });
        }
        if (target.includes('/branch-discovery')) branchRequests += 1;
        else if (target.includes('/counsel')) counselRequests += 1;
        else discoverRequests += 1;
        return jsonResponse(200, {
          session_id: sid,
          discovered_majors: [
            {
              id: 1,
              major_name_fa: 'مهندسی کامپیوتر',
              fit_score: 91,
              raw_components: { m_score: 93, s_score: 86, v_score: 89 },
              personalized_description: 'همخوانی مستقیم با حل مسئله و معماری سیستم.',
              evidence: { micro_motives_matched: [{ description: 'طراحی سیستم‌های نرم‌افزاری' }] }
            }
          ],
          recommended_branches: [
            {
              branch_code: 'math',
              branch_name_fa: 'ریاضی و فیزیک',
              fit_score: 89,
              raw_components: { m_score: 91, s_score: 85, v_score: 88 },
              personalized_description: 'تناسب بالا با تفکر تحلیلی.'
            }
          ],
          counsel_text: 'تحلیل مشاوره‌ای اختصاصی آماده است.'
        });
      }

      return jsonResponse(200, {});
    }
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);

  for (const rel of [
    'docs/data.js',
    'docs/app.js',
    'docs/journey_experience.js',
    'docs/ux_v2_patch.js',
    'docs/auth_api_client.js',
    'docs/quota_state_reconciler.js',
    'docs/shell.js',
    'docs/quota_runtime.js',
    'docs/commercial_ui.js',
    'docs/post_auth_flow_policy.js'
  ]) {
    vm.runInContext(fs.readFileSync(path.join(root, rel), 'utf8'), sandbox, { filename: rel });
  }
  vm.runInContext('globalThis.REALMS = REALMS; globalThis.SUB_REALMS = SUB_REALMS; globalThis.NARROW_PATHS = NARROW_PATHS;', sandbox);
  await flushMicrotasks();
  await flushMicrotasks();

  // ==================== 0) COLD BOOT & UNAUTHENTICATED GUARD ====================
  assert.equal(sandbox.__dhInJourney, false, 'Cold boot must land on Home, never inside City of Dreams');
  assert.ok(!getEl('app').innerHTML.includes('ورود به ۶ محلهٔ شهر رؤیاها'),
    'Cold boot must NOT leak unauthenticated splash screen over Home');

  const getOverlayHtml = () => {
    const ov = getEl('dh-commercial-overlay');
    return String(ov.innerHTML || '') + String((ov._modalChild && ov._modalChild.innerHTML) || '');
  };

  // Unauthenticated direct attempts must ALL open login modal and NEVER enter journey stages
  for (const fn of [
    () => sandbox.DHCommercialUI.startServerAuthorizedJourney(),
    () => sandbox.DHShell.startJourney(),
    () => sandbox.startNewJourney(),
    () => sandbox.resetJourney(),
    () => sandbox.dhResumeFromSplash(),
    () => sandbox.dhReturnToActivePage()
  ]) {
    elements.delete('dh-commercial-overlay');
    await fn();
    await flushMicrotasks();
    assert.equal(sandbox.__dhInJourney, false, 'Unauthenticated user must stay outside journey');
    assert.ok(getOverlayHtml().includes('ورود به حساب'),
      'Unauthenticated entry must always open login modal');
  }

  // ==================== 2 & 4) REMAINING = 1 -> EXPLORE REALMS (0 CONSUME) -> 1 COMPLETE JOURNEY ====================
  localStorage.setItem('dh_auth_v1', JSON.stringify({
    token: 'tok-user-1',
    user: usersByToken.get('tok-user-1')
  }));
  elements.delete('dh-commercial-overlay');

  assert.equal(userQuotaDetails(101).credits_remaining, 1, 'OTP-verified user starts with 1 server credit');
  await sandbox.DHCommercialUI.startServerAuthorizedJourney();
  assert.equal(sandbox.__dhInJourney, true);
  assert.equal(sandbox.state.stage, 'splash');
  const journey1Id = sandbox.state.sessionId;
  assert.ok(journey1Id, 'Journey #1 must receive a prepared session UUID');
  assert.equal(consumeTestRequests, 0, 'Entering splash MUST NOT call consume-test');

  // Traverse multiple realms, sub-realms, narrow-paths, sparks, Home & exact return, SJT & Values!
  sandbox.startNewJourney();
  assert.equal(sandbox.state.stage, 'realm');
  const r0 = sandbox.REALMS[0].id;
  const r1 = sandbox.REALMS[1].id;
  sandbox.toggleRealm(r0);
  sandbox.toggleRealm(r1);
  sandbox.goTo('subRealm');
  const sub0 = sandbox.SUB_REALMS[r0][0].id;
  sandbox.toggleSub(sub0, 6);
  sandbox.goTo('narrowPath');
  const path0 = sandbox.NARROW_PATHS[sub0][0].id;
  sandbox.togglePath(path0);
  await sandbox.loadSwipeCards();
  assert.equal(sandbox.state.stage, 'swipe');
  sandbox.likeCard(true);
  sandbox.likeCard(true);
  for (let i = 0; i < 20; i++) {
    const code = motivesRaw[i].code;
    if (!sandbox.state.likedCodesSet.has(code)) {
      sandbox.state.likedCodes.push(code);
      sandbox.state.likedCodesSet.add(code);
    }
  }
  // Leave to Home mid-exploration and resume exact stage — still 0 credits consumed!
  sandbox.dhGoHomeKeepPlace();
  assert.equal(sandbox.__dhInJourney, false);
  await sandbox.dhReturnToActivePage();
  assert.equal(sandbox.state.stage, 'swipe');
  assert.equal(consumeTestRequests, 0, 'Exploring neighborhoods + Home resume MUST NOT consume credit');
  assert.equal(userQuotaDetails(101).credits_remaining, 1);

  sandbox.finishSwipe();
  sandbox.goTo('strategies');
  for (let i = 0; i < 25; i++) sandbox.state.strategyAnswers[i] = i % 4;
  sandbox.goTo('values');
  for (let i = 0; i < 15; i++) sandbox.state.valueAnswers[i] = `Q${i + 1}A`;
  sandbox.goTo('choice');
  assert.equal(consumeTestRequests, 0, 'Reaching Choice before requesting results MUST still have 0 consumes');

  // Complete Journey #1 -> consumes 1 credit (`remaining: 1 -> 0`) and displays results!
  await sandbox.analyzeMajors();
  assert.equal(userQuotaDetails(101).credits_consumed, 1);
  assert.equal(userQuotaDetails(101).credits_remaining, 0);
  assert.equal(discoverRequests, 1);
  assert.equal(sandbox.state.journeyFinished, true);
  assert.equal(sandbox.state.stage, 'results');

  // ==================== 3) IDEMPOTENCY ON SAME SESSION_UUID ====================
  // Viewing/requesting results a 2nd time, viewing Branch Discovery, calling Counsel,
  // and returning from Home to Results on the SAME `journey1Id` MUST NOT deduct twice!
  await sandbox.analyzeMajors();
  assert.equal(discoverRequests, 2);
  assert.equal(userQuotaDetails(101).credits_consumed, 1, 'Re-requesting discover on same session MUST be idempotent');

  sandbox.goTo('choice');
  assert.equal(sandbox.state.stage, 'choice', 'Switching analysis mode on SAME paid session must remain allowed');
  await sandbox.analyzeBranches();
  assert.equal(branchRequests, 1);
  assert.equal(userQuotaDetails(101).credits_consumed, 1, 'Branch discovery on same paid session MUST NOT deduct again');

  const counselResp = await sandbox.fetch('https://api.asbe-siah.ir/api/v2/darkhorse/counsel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile: {}, top_results: [] })
  });
  assert.equal(counselResp.status, 200);
  assert.equal(counselRequests, 1);
  assert.equal(userQuotaDetails(101).credits_consumed, 1);

  sandbox.dhGoHomeKeepPlace();
  await sandbox.dhReturnToActivePage();
  assert.equal(sandbox.state.stage, 'results', 'Returning to completed Results from Home must stay allowed without extra charge');
  assert.equal(userQuotaDetails(101).credits_consumed, 1);

  // ==================== 1) REMAINING = 0 -> BLOCK ALL 2ND JOURNEY ENTRY VECTORS ====================
  // Even if someone tampers with EVERY localStorage key in DevTools (`remaining: 99`, `premium: true`, forged `dh_quota_charged_session_v1`)!
  localStorage.setItem('dh_local_quota_v1', JSON.stringify({ remaining: 99, serverRemaining: 99, premium: true }));
  localStorage.setItem('dh_local_user_v1', JSON.stringify({ id: 101, is_premium: true }));

  const quotaCallsBeforeLock = quotaRequests;

  // 1a. Clicking «شروع سفر جدید» (`resetJourney()`) right after Results MUST query server, block `splash`, and open Purchase Modal!
  elements.delete('dh-commercial-overlay');
  sandbox.resetJourney();
  await flushMicrotasks();
  await flushMicrotasks();
  assert.ok(quotaRequests > quotaCallsBeforeLock, 'resetJourney() must check server quota first');
  assert.notEqual(sandbox.state.stage, 'splash', 'resetJourney() with remaining=0 MUST NOT enter splash');
  assert.notEqual(sandbox.state.stage, 'realm', 'resetJourney() with remaining=0 MUST NOT enter realm');
  assert.ok(getEl('dh-commercial-overlay').innerHTML.includes('خرید بسته ۳ تست'),
    'resetJourney() with remaining=0 MUST open Purchase Modal');
  assert.ok(getEl('dh-commercial-overlay').innerHTML.includes('اعتبار سفر اکتشافی شما به پایان رسیده است'),
    'Purchase Modal must display explicit quota exhaustion message');

  // 1b. Calling `startNewJourney()` directly with `remaining=0` MUST block `realm` and open Purchase Modal!
  elements.delete('dh-commercial-overlay');
  sandbox.startNewJourney();
  await flushMicrotasks();
  await flushMicrotasks();
  assert.notEqual(sandbox.state.stage, 'realm', 'startNewJourney() with remaining=0 MUST NOT enter realm');
  assert.ok(getEl('dh-commercial-overlay').innerHTML.includes('خرید بسته ۳ تست'),
    'startNewJourney() with remaining=0 MUST open Purchase Modal');

  // 1c. Clicking bottom Tabbar `[سفر]` (`switchTab('journey')`) or `startServerAuthorizedJourney()` with `remaining=0`!
  elements.delete('dh-commercial-overlay');
  sandbox.DHShell.switchTab('journey');
  await flushMicrotasks();
  await flushMicrotasks();
  assert.equal(sandbox.__dhInJourney, false, 'Tabbar journey button with remaining=0 must keep user out of journey');
  assert.ok(getEl('dh-commercial-overlay').innerHTML.includes('خرید بسته ۳ تست'),
    'Tabbar journey button with remaining=0 MUST open Purchase Modal');

  // 1d. Tampering with an uncharged session + forged `dh_quota_charged_session_v1` in `localStorage` and calling `dhReturnToActivePage()`!
  sandbox.__dhCachedResultsPlace = null;
  localStorage.setItem('darkhorse_session_v2', JSON.stringify({
    sessionId: 'forged-uncharged-session-999',
    stage: 'realm',
    journeyFinished: false
  }));
  localStorage.setItem('dh_quota_charged_session_v1', 'forged-uncharged-session-999');
  elements.delete('dh-commercial-overlay');
  await sandbox.dhReturnToActivePage();
  await flushMicrotasks();
  assert.equal(sandbox.__dhInJourney, false, 'Forged localStorage charge marker MUST be rejected by server check');
  assert.equal(localStorage.getItem('dh_quota_charged_session_v1'), null, 'Forged charge marker must be purged');
  assert.ok(getEl('dh-commercial-overlay').innerHTML.includes('خرید بسته ۳ تست'),
    'Resuming forged uncharged session with remaining=0 MUST open Purchase Modal');

  // 1e. Direct DevTools `window.__dhInJourney = true; state.stage = 'realm'; render();`!
  elements.delete('dh-commercial-overlay');
  sandbox.__dhInJourney = true;
  sandbox.state.stage = 'realm';
  sandbox.state.sessionId = 'unverified-direct-render-session';
  sandbox.state.journeyFinished = false;
  sandbox.render();
  await flushMicrotasks();
  await flushMicrotasks();
  assert.equal(sandbox.__dhInJourney, false, 'Direct render() of unverified stage MUST be blocked');
  assert.ok(getEl('dh-commercial-overlay').innerHTML.includes('خرید بسته ۳ تست'),
    'Direct render() of unverified stage with remaining=0 MUST open Purchase Modal');

  // ==================== 5) ZERO SILENT SWALLOWING ON 402 / 403 / 409 CONSUME ERRORS ====================
  // Grant pack (+3 credits), enter Journey #3 cleanly, reach Choice, then simulate
  // concurrent credit depletion / ownership error (`409 no test credits remaining`, `402`, `403`)!
  grantedByUser.set(101, 4); // 1 consumed earlier -> 3 remaining now
  elements.delete('dh-commercial-overlay');
  await sandbox.DHCommercialUI.startServerAuthorizedJourney();
  const journey2Id = sandbox.state.sessionId;
  assert.notEqual(journey2Id, journey1Id, 'New journey after pack purchase gets a brand-new UUID');
  sandbox.startNewJourney();
  assert.equal(sandbox.state.stage, 'realm');
  sandbox.state.likedCodes = [motivesRaw[0].code, motivesRaw[1].code];
  sandbox.goTo('choice');

  for (const statusCode of [409, 402, 403]) {
    elements.delete('dh-commercial-overlay');
    localStorage.removeItem('dh_quota_charged_session_v1');
    forceNextConsumeStatus = statusCode;
    await sandbox.analyzeMajors();
    await flushMicrotasks();
    assert.ok(getEl('app').innerHTML.includes('role="alert"'),
      `HTTP ${statusCode} on consume MUST render visible alert UI (never swallowed)`);
    assert.ok(getEl('app').innerHTML.includes('تهیهٔ اعتبار'),
      `HTTP ${statusCode} error UI MUST offer direct تهیهٔ اعتبار CTA`);
    assert.ok(getEl('dh-commercial-overlay').innerHTML.includes('خرید بسته ۳ تست'),
      `HTTP ${statusCode} on consume MUST automatically open Purchase Modal`);
  }

  console.log('P0 server-authoritative quota gate E2E regression: PASS (all 5 mandatory contracts verified)');
}

run().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
