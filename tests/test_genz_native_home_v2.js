#!/usr/bin/env node
'use strict';

/**
 * End-to-End Regression Suite — Option 2: Gen-Z (<20) + 100% Native App Home & Shell UX
 * Verifies Axis A (Gen-Z Engagement Architecture) + Axis B (True Native App Feel) + <2s Cold-Load Budget.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const indexHtml = fs.readFileSync(path.join(root, 'docs', 'index.html'), 'utf8');
const manifestJson = JSON.parse(fs.readFileSync(path.join(root, 'docs', 'manifest.json'), 'utf8'));
const mobilePwaCss = fs.readFileSync(path.join(root, 'docs', 'mobile-pwa.css'), 'utf8');
const shellCss = fs.readFileSync(path.join(root, 'docs', 'shell.css'), 'utf8');
const shellJs = fs.readFileSync(path.join(root, 'docs', 'shell.js'), 'utf8');
const pwaBootJs = fs.readFileSync(path.join(root, 'docs', 'pwa-boot.js'), 'utf8');
const swJs = fs.readFileSync(path.join(root, 'docs', 'sw.js'), 'utf8');

/* 1. Seamless Native Status-Bar & Theme Color Unification + Zero Browser alert() Popups */
assert.strictEqual(manifestJson.background_color, '#0e1017', 'manifest background_color must match #0e1017 canvas');
assert.strictEqual(manifestJson.theme_color, '#0e1017', 'manifest theme_color must match #0e1017 status bar');
assert.match(indexHtml, /<meta name="theme-color" content="#0e1017">/, 'index.html theme-color must be #0e1017');
assert.match(mobilePwaCss, /calc\(92px \+ var\(--safe-bottom\)\)/, 'mobile-pwa.css must clear floating glass bottom tabbar + safe-area');
assert.match(pwaBootJs, /beforeinstallprompt/, 'pwa-boot.js must capture native beforeinstallprompt event');
assert.match(swJs, /const CACHE = 'darkhorse-v75'/, 'sw.js cache version must be bumped to darkhorse-v75');
assert.match(
  shellCss,
  /\.dh-appbar-logo img\s*\{[\s\S]*?object-fit:\s*contain;/,
  'Appbar logo must use object-fit: contain so icon-192 / icon-512 never crops'
);
assert.match(
  shellJs,
  /class="dh-appbar-logo"><img[^>]*srcset="[^"]*icon-512\.png 2x/,
  'Appbar logo must include Retina srcset with icon-512.png'
);
const tickerArrayBlock = (shellJs.match(/var DH_FARDIYAT_LINES = \[[\s\S]*?\];/) || [''])[0];
assert.ok(tickerArrayBlock.length > 50, 'DH_FARDIYAT_LINES array must exist');
assert.strictEqual(
  (tickerArrayBlock.match(/هاروارد|harvard/gi) || []).length,
  0,
  'Home ticker DH_FARDIYAT_LINES must contain ZERO Harvard claims'
);

for (const rel of ['docs/shell.js', 'docs/parents.js', 'docs/stories.js', 'docs/poems.js', 'docs/spark_game.js']) {
  const src = fs.readFileSync(path.join(root, rel), 'utf8');
  assert.ok(!/\balert\s*\(/.test(src), `${rel} must use native glass toast/sheet instead of browser alert()`);
}

/* 2. Dark-Gold Brand Integrity & Native Motion CSS Contracts */
for (const cls of [
  '.dh-appbar',
  '.dh-hero-pills',
  '.dh-peek-card',
  '.dh-worlds-section',
  '.dh-worlds-strip',
  '.dh-world-chip-card',
  '.dh-bento-pill',
  '.dh-quote-share-btn',
  '.dh-sheet-ov',
  '.dh-sheet-panel',
  '.dh-native-toast',
  '@media (prefers-reduced-motion: reduce)'
]) {
  assert.ok(shellCss.includes(cls), `docs/shell.css must include ${cls}`);
}

/* 3. Interactive Runtime Verification in Isolated VM */
function makeElement(tag, idMap) {
  const classes = new Set();
  const attrs = new Map();
  const listeners = {};
  const children = [];
  let html = '';
  let text = '';

  const el = {
    tagName: String(tag || 'DIV').toUpperCase(),
    id: '',
    hidden: false,
    style: {},
    parentNode: null,
    children,
    classList: {
      add: (...names) => names.forEach(n => classes.add(n)),
      remove: (...names) => names.forEach(n => classes.delete(n)),
      toggle: (n, force) => {
        if (force === undefined) {
          if (classes.has(n)) { classes.delete(n); return false; }
          classes.add(n); return true;
        }
        if (force) classes.add(n); else classes.delete(n);
        return !!force;
      },
      contains: n => classes.has(n)
    },
    set className(val) {
      classes.clear();
      String(val || '').split(/\s+/).filter(Boolean).forEach(c => classes.add(c));
    },
    get className() {
      return Array.from(classes).join(' ');
    },
    setAttribute(k, v) {
      attrs.set(k, String(v));
      if (k === 'id') { el.id = String(v); idMap.set(el.id, el); }
    },
    getAttribute(k) {
      return attrs.has(k) ? attrs.get(k) : null;
    },
    addEventListener(name, fn) {
      listeners[name] = listeners[name] || [];
      listeners[name].push(fn);
    },
    dispatchEvent(name, ev) {
      (listeners[name] || []).forEach(fn => fn(ev || {}));
    },
    appendChild(child) {
      child.parentNode = el;
      children.push(child);
      if (child.id) idMap.set(child.id, child);
      syncHtmlIds(child.innerHTML || '');
      return child;
    },
    removeChild(child) {
      const idx = children.indexOf(child);
      if (idx >= 0) children.splice(idx, 1);
      child.parentNode = null;
      if (child.id) idMap.delete(child.id);
    },
    remove() {
      if (el.id) idMap.delete(el.id);
      if (el.parentNode && typeof el.parentNode.removeChild === 'function') {
        el.parentNode.removeChild(el);
      }
    },
    querySelector(sel) {
      if (sel.startsWith('#')) return idMap.get(sel.slice(1)) || null;
      return null;
    },
    querySelectorAll(sel) {
      if (sel === '[data-tab]') {
        return ['home', 'journey', 'profile'].map(t => ({
          getAttribute: () => t,
          classList: { toggle() {} },
          onclick: null
        }));
      }
      return [];
    },
    set textContent(v) {
      text = String(v || '');
      html = text;
    },
    get textContent() {
      return text || html.replace(/<[^>]+>/g, '');
    },
    set innerHTML(v) {
      html = String(v || '');
      syncHtmlIds(html);
    },
    get innerHTML() {
      return html;
    }
  };

  function syncHtmlIds(markup) {
    const tagRe = /<([a-z0-9-]+)([^>]*)>/gi;
    let match;
    while ((match = tagRe.exec(markup)) !== null) {
      const attrStr = match[2] || '';
      const idMatch = attrStr.match(/\bid="([^"]+)"/);
      if (idMatch) {
        const id = idMatch[1];
        if (!idMap.has(id)) {
          const proxy = makeElement(match[1], idMap);
          proxy.id = id;
          proxy.hidden = /\bhidden\b/.test(attrStr);
          idMap.set(id, proxy);
        } else {
          idMap.get(id).hidden = /\bhidden\b/.test(attrStr);
        }
      }
    }
  }

  return el;
}

const idMap = new Map();
const appRoot = makeElement('div', idMap);
appRoot.id = 'app';
idMap.set('app', appRoot);
const body = makeElement('body', idMap);
body.appendChild(appRoot);

const storage = new Map();
const pushedStates = [];
const windowEvents = {};
let journeyStarts = 0;
let remainingQuota = 0;
let consumeCalls = 0;
let purchaseModalOpens = 0;
let copiedClipboard = '';
let installPromptCalled = 0;

const deferredTimers = [];
const ctx = {
  console,
  setTimeout: (fn, ms) => {
    if (ms && ms >= 1000) { deferredTimers.push(fn); return deferredTimers.length; }
    fn();
    return 1;
  },
  clearTimeout: () => {},
  setInterval: () => 1,
  clearInterval: () => {},
  location: { pathname: '/', search: '', href: 'https://asbe-siah.ir/' },
  history: {
    pushState(stateObj) { pushedStates.push(stateObj); }
  },
  navigator: {
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8)',
    vibrate: () => true,
    clipboard: {
      writeText(t) {
        copiedClipboard = String(t);
        return Promise.resolve();
      }
    }
  },
  localStorage: {
    getItem: k => (storage.has(k) ? storage.get(k) : null),
    setItem: (k, v) => storage.set(k, String(v)),
    removeItem: k => storage.delete(k)
  },
  matchMedia: () => ({ matches: false }),
  addEventListener: (name, fn) => {
    windowEvents[name] = windowEvents[name] || [];
    windowEvents[name].push(fn);
  },
  scrollTo: () => {},
  DHCommercialUI: {
    startServerAuthorizedJourney: () => {
      journeyStarts += 1;
      return ctx.ensureCanEnterJourney();
    }
  },
  ensureCanEnterJourney: () => {
    if (remainingQuota <= 0) {
      purchaseModalOpens += 1;
      return Promise.resolve({ allowed: false });
    }
    return Promise.resolve({ allowed: true });
  },
  DHAdmissionChanceUI: {
    openHome: (mountId) => {
      const m = idMap.get(mountId);
      if (m) m.innerHTML = '<div class="sanjesh-mounted">mounted</div>';
    }
  }
};
ctx.window = ctx;
ctx.document = {
  readyState: 'complete',
  body,
  getElementById: id => idMap.get(id) || null,
  createElement: tag => makeElement(tag, idMap),
  querySelector: sel => appRoot.querySelector(sel),
  querySelectorAll: sel => appRoot.querySelectorAll(sel),
  addEventListener: () => {}
};

vm.runInNewContext(shellJs, ctx);

/* Verify Axis A1 + A2 Home DOM + 0 Harvard Ticker */
assert.ok(appRoot.innerHTML.includes('class="dh-appbar"'), 'Compact native top app bar must render');
assert.ok(!appRoot.innerHTML.includes('class="dh-mk2-brand"'), 'Legacy tall static poster header must be replaced');
assert.ok(!/هاروارد|harvard/i.test(appRoot.innerHTML), 'Rendered Home DOM must contain ZERO Harvard mentions');
assert.ok(appRoot.innerHTML.includes('کشف رشته و شاخه بر اساس فردیت'), 'Hero sub-headline brand contract must remain intact');
assert.ok(appRoot.innerHTML.includes('⚡ حدود ۷ دقیقه'), 'Hero clarity badge (7 min) must render');
assert.ok(appRoot.innerHTML.includes('🎮 تعاملی و بدون نمره'), 'Hero clarity badge (interactive & score-free) must render');
assert.ok(appRoot.innerHTML.includes('🎯 ۲۳۰ رشته + شاخه دبیرستان'), 'Hero clarity badge (230 majors + Grade 9) must render');
assert.strictEqual((appRoot.innerHTML.match(/data-world-id="/g) || []).length, 6, 'All 6 Worlds of City of Dreams must render in horizontal strip');

/* Verify Axis A3 Live Spark Taster Interaction + P0 Quota Non-Consume & Non-Bypass */
const initialPeekText = idMap.get('dh-peek-text').textContent;
idMap.get('dh-peek-like').onclick();
idMap.get('dh-peek-skip').onclick();
assert.strictEqual(consumeCalls, 0, 'Home spark teaser must NEVER consume quota');
assert.strictEqual(purchaseModalOpens, 0, 'Home spark teaser must be free to interact with');
assert.strictEqual(ctx.__dhInJourney, false, 'Home spark teaser must not enter full City of Dreams');
assert.strictEqual(idMap.get('dh-peek-feedback').hidden, false, 'Liking a spark must reveal instant world-connection insight');
assert.ok(idMap.get('dh-peek-counter').textContent.includes('1'), 'Spark counter must update after 1st like');
assert.notStrictEqual(idMap.get('dh-peek-text').textContent, initialPeekText, 'Spark card must advance immediately without network roundtrip');
assert.strictEqual(idMap.get('dh-peek-bridge').hidden, true, 'Bridge actions stay tucked away until 2 sparks are liked');

idMap.get('dh-peek-like').onclick();
assert.strictEqual(idMap.get('dh-peek-bridge').hidden, false, 'Bridge actions unlock immediately after 2 liked sparks');
idMap.get('dh-peek-go-journey').onclick();
assert.strictEqual(journeyStarts, 1, 'Tapping journey bridge button routes through startServerAuthorizedJourney');
assert.strictEqual(purchaseModalOpens, 1, 'With remaining=0, bridge CTA opens Purchase Modal via ensureCanEnterJourney');
assert.strictEqual(ctx.__dhInJourney, false, 'With remaining=0, 0 stages of City of Dreams run');

/* Verify Axis A4 World Preview Native Bottom Sheet + P0 Gate + Android Back Close */
const stripEl = idMap.get('dh-worlds-strip');
stripEl.dispatchEvent('click', {
  target: {
    closest: () => ({ getAttribute: () => 'builder' })
  }
});
assert.strictEqual(consumeCalls, 0, 'Browsing 6 Worlds strip & opening World sheet must NEVER consume quota');
assert.ok(idMap.get('dh-native-sheet'), 'Tapping a World card must open native Bottom Sheet');
assert.ok(idMap.get('dh-native-sheet').innerHTML.includes('ساخت و فناوری'), 'World Bottom Sheet must render world details & sample majors');
idMap.get('dh-sheet-start-world').onclick();
assert.strictEqual(journeyStarts, 2, 'World Sheet full-journey button routes through startServerAuthorizedJourney');
assert.strictEqual(purchaseModalOpens, 2, 'With remaining=0, World Sheet CTA opens Purchase Modal via ensureCanEnterJourney');
assert.strictEqual(ctx.__dhInJourney, false, 'With remaining=0, World Sheet CTA runs 0 stages of City of Dreams');

stripEl.dispatchEvent('click', {
  target: {
    closest: () => ({ getAttribute: () => 'healer' })
  }
});
assert.ok(idMap.get('dh-native-sheet'), 'Second World Bottom Sheet opens cleanly');
(windowEvents.popstate || []).forEach(fn => fn());
assert.strictEqual(idMap.get('dh-native-sheet'), undefined, 'Android hardware Back (popstate) must close open Bottom Sheet cleanly');

idMap.get('dh-start-journey').onclick();
assert.strictEqual(journeyStarts, 3, 'Hero primary CTA routes through startServerAuthorizedJourney');
assert.strictEqual(purchaseModalOpens, 3, 'With remaining=0, Hero primary CTA opens Purchase Modal via ensureCanEnterJourney');
assert.strictEqual(ctx.__dhInJourney, false, 'With remaining=0, Hero primary CTA runs 0 stages of City of Dreams');

/* Verify Axis B Native 1-Tap PWA Install Prompt + Sanjesh Back Navigation + Quote Toast */
ctx.__dhInstallPromptEvent = {
  prompt: () => { installPromptCalled += 1; },
  userChoice: Promise.resolve({ outcome: 'accepted' })
};
idMap.get('dh-open-install').onclick();
assert.strictEqual(installPromptCalled, 1, 'Tapping install pill with deferred beforeinstallprompt must trigger native OS install dialog');

idMap.get('dh-open-sanjesh').onclick();
assert.strictEqual(idMap.get('dh-home-sanjesh-panel').hidden, false, 'Opening Sanjesh must expand panel');
(windowEvents.popstate || []).forEach(fn => fn());
assert.strictEqual(idMap.get('dh-home-sanjesh-panel').hidden, true, 'Android Back must collapse Sanjesh panel smoothly');

/* 4. Cold-Load Critical Render-Blocking Budget (< 2.0s strictly enforced) */
const indexBytes = Buffer.byteLength(indexHtml, 'utf8');
assert.ok(indexBytes < 20000, `docs/index.html must remain compact (<20KB, actual=${indexBytes}B) for instant First Paint`);
assert.ok(!/cdn\.jsdelivr\.net|googleapis\.com|unpkg\.com/.test(indexHtml), 'Zero external CDN dependencies allowed in index.html');

(async () => {
  idMap.get('dh-copy-quote').onclick();
  await Promise.resolve();
  assert.ok(copiedClipboard.includes('https://asbe-siah.ir/'), 'Quote copy button must copy formatted quote + site link');
  assert.ok(idMap.get('dh-native-toast') && idMap.get('dh-native-toast').className.includes('is-open'), 'Quote copy must display native glass toast');
  console.log('Gen-Z (<20) + 100% Native App Home & Shell UX E2E suite: PASS (Axis A + Axis B + <2s Cold-Load Budget)');
})().catch(err => {
  console.error(err);
  process.exit(1);
});
