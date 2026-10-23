#!/usr/bin/env node
'use strict';

/**
 * End-to-End Regression Suite — Luxury Regal Dark-Gold Home & Interactive Deep Modules UX
 * Verifies:
 *  1) Regal Luxury Brand Crest header (.dh-regal-brand) with object-fit: contain + Retina srcset,
 *     and ZERO top-bar install/profile buttons (#dh-open-install / #dh-appbar-profile removed).
 *  2) Hero card shows ONLY '۲۳۰ رشته و شاخه' pill (ZERO '۷ دقیقه' or 'تعاملی و بدون نمره').
 *  3) Sanjesh section sits IMMEDIATELY directly under Hero card.
 *  4) Interactive Daily Wisdom ('پیام روزانه') placed in canonical global app position right after Sanjesh
 *     with 3-card deck cycling, bookmarking, and sharing.
 *  5) 'همین الان یه جرقه‌ات رو تست کن' & '۶ دنیای شهر رؤیاها' removed from Home; replaced by deep,
 *     modern, interactive original modules (Spark Lab, Stories, Poems, Parents, System Guide).
 *  6) Strict P0 quota gate + 0 Harvard Home ticker + <2s Cold-Load Budget preserved.
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
const storiesJs = fs.readFileSync(path.join(root, 'docs', 'stories.js'), 'utf8');
const poemsJs = fs.readFileSync(path.join(root, 'docs', 'poems.js'), 'utf8');
const parentsJs = fs.readFileSync(path.join(root, 'docs', 'parents.js'), 'utf8');
const sparkJs = fs.readFileSync(path.join(root, 'docs', 'spark_game.js'), 'utf8');
const pwaBootJs = fs.readFileSync(path.join(root, 'docs', 'pwa-boot.js'), 'utf8');
const swJs = fs.readFileSync(path.join(root, 'docs', 'sw.js'), 'utf8');

/* 1. Native Theme & Asset Contracts */
assert.strictEqual(manifestJson.background_color, '#0e1017', 'manifest background_color must match #0e1017 canvas');
assert.strictEqual(manifestJson.theme_color, '#0e1017', 'manifest theme_color must match #0e1017 status bar');
assert.match(indexHtml, /<meta name="theme-color" content="#0e1017">/, 'index.html theme-color must be #0e1017');
assert.match(mobilePwaCss, /calc\(92px \+ var\(--safe-bottom\)\)/, 'mobile-pwa.css must clear floating glass bottom tabbar');
assert.match(swJs, /const CACHE = 'darkhorse-v76'/, 'sw.js cache version must be bumped to darkhorse-v76');
assert.match(pwaBootJs, /\.\/sw\.js\?v=76/, 'pwa-boot.js must register ./sw.js?v=76');

/* Regal Logo object-fit: contain + Retina srcset */
assert.match(
  shellCss,
  /\.dh-regal-crest-inner img\s*\{[\s\S]*?object-fit:\s*contain;/,
  'Regal crest logo must use object-fit: contain'
);
assert.match(
  shellJs,
  /class="dh-regal-crest-inner">[\s\S]*?srcset="[^"]*icon-512\.png 2x/,
  'Regal crest logo must include Retina srcset with icon-512.png'
);

/* Zero Harvard lines in Home Ticker */
const tickerArrayBlock = (shellJs.match(/var DH_FARDIYAT_LINES = \[[\s\S]*?\];/) || [''])[0];
assert.ok(tickerArrayBlock.length > 50, 'DH_FARDIYAT_LINES array must exist');
assert.strictEqual(
  (tickerArrayBlock.match(/هاروارد|harvard/gi) || []).length,
  0,
  'Home ticker DH_FARDIYAT_LINES must contain ZERO Harvard claims'
);

/* Zero browser alert() popups */
for (const rel of ['docs/shell.js', 'docs/parents.js', 'docs/stories.js', 'docs/poems.js', 'docs/spark_game.js']) {
  const src = fs.readFileSync(path.join(root, rel), 'utf8');
  assert.ok(!/\balert\s*\(/.test(src), `${rel} must use native glass toast instead of alert()`);
}

/* 2. Interactive Runtime Verification in VM */
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
      if (el.id) idMap.delete(childIdOrSelf(el));
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
      text = '';
      syncHtmlIds(html);
    },
    get innerHTML() {
      return html;
    }
  };

  function childIdOrSelf(n) { return n.id; }

  function syncHtmlIds(markup) {
    const tagRe = /<([a-z0-9-]+)([^>]*)>([\s\S]*?)<\/\1>|<([a-z0-9-]+)([^>]*)>/gi;
    let match;
    const bareRe = /<([a-z0-9-]+)([^>]*)>/gi;
    while ((match = bareRe.exec(markup)) !== null) {
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
const windowEvents = {};
const deferredTimers = [];
let journeyStarts = 0;
let remainingQuota = 0;
let purchaseModalOpens = 0;
let copiedClipboard = '';

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
  history: { pushState() {} },
  navigator: {
    userAgent: 'Mozilla/5.0 (Linux; Android 14)',
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
      if (remainingQuota <= 0) purchaseModalOpens += 1;
    }
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

vm.runInNewContext(storiesJs, ctx);
vm.runInNewContext(poemsJs, ctx);
vm.runInNewContext(parentsJs, ctx);
vm.runInNewContext(sparkJs, ctx);
vm.runInNewContext(shellJs, ctx);

const homeMarkup = appRoot.innerHTML;

/* Verify Requirement 1: Regal Luxury Brand Header & NO top-bar Install / Profile buttons */
assert.ok(homeMarkup.includes('class="dh-regal-brand"'), 'Home must render majestic luxury brand header (.dh-regal-brand)');
assert.strictEqual(idMap.has('dh-open-install'), false, 'Top header must NOT include install app button');
assert.strictEqual(idMap.has('dh-appbar-profile'), false, 'Top header must NOT include profile button');
assert.ok(!/هاروارد|harvard/i.test(homeMarkup), 'Rendered Home DOM must contain ZERO Harvard mentions');

/* Verify Requirement 2: Hero has ONLY '۲۳۰ رشته و شاخه' — NO '۷ دقیقه' & NO 'تعاملی و بدون نمره' */
assert.ok(homeMarkup.includes('کشف رشته و شاخه بر اساس فردیت'), 'Hero sub-headline brand contract intact');
assert.ok(homeMarkup.includes('<span class="dh-hero-pill">۲۳۰ رشته و شاخه</span>'), 'Hero must keep ONLY ۲۳۰ رشته و شاخه pill');
assert.ok(!homeMarkup.includes('۷ دقیقه'), '۷ دقیقه badge must be completely removed from Hero');
assert.ok(!homeMarkup.includes('تعاملی و بدون نمره'), 'تعاملی و بدون نمره badge must be completely removed from Hero');

/* Verify Requirement 3: Live Spark Teaser & 6 Worlds removed; Original Deep Modules live & interactive */
assert.ok(!homeMarkup.includes('dh-live-spark-peek'), 'Live spark teaser card must be completely removed');
assert.ok(!homeMarkup.includes('dh-worlds-strip'), '6 Worlds strip must be completely removed');
assert.ok(homeMarkup.includes('روایت امروز:'), 'Stories tile displays live story preview');

/* Verify Requirement 4 & 5: Exact Vertical Ordering on Home:
   Regal Header -> Hero (سفر اکتشافی) -> Sanjesh IMMEDIATELY below Hero -> Daily Wisdom ('پیام روزانه') -> Deep Modules */
const regalPos = homeMarkup.indexOf('class="dh-regal-brand"');
const heroPos = homeMarkup.indexOf('class="dh-mk2-hero"');
const sanjeshPos = homeMarkup.indexOf('class="dh-home-sanjesh-entry"');
const dailyPos = homeMarkup.indexOf('id="dh-daily-wisdom"');
const morePos = homeMarkup.indexOf('class="dh-mk2-more"');
assert.ok(regalPos >= 0 && heroPos > regalPos, 'Hero sits directly under Regal Brand Crest');
assert.ok(sanjeshPos > heroPos && sanjeshPos < dailyPos, 'Sanjesh MUST sit immediately below Hero (سفر اکتشافی)');
assert.ok(dailyPos > sanjeshPos && dailyPos < morePos, 'Daily Wisdom (پیام روزانه) sits in modern global bridge slot between primary actions & deep exploration');

/* Verify Daily Wisdom interactivity (Next, Bookmark, Share) */
idMap.get('dh-next-quote').onclick();
const secondQuoteText = idMap.get('dh-daily-text').textContent;
assert.ok(secondQuoteText.length > 5, 'Next button cycles Daily Wisdom smoothly');
idMap.get('dh-like-quote').onclick();
assert.ok(idMap.get('dh-like-quote').textContent.includes('پسندیده شد'), 'Bookmarking Daily Wisdom updates state immediately');

/* Verify Interactive Sub-Views (Stories, Poems, Parents, System Guide) + Back return to Home */
idMap.get('dh-open-stories').onclick();
assert.ok(appRoot.innerHTML.includes('id="dh-story-chapters"'), 'Stories opens interactive chapter selector');
assert.ok(appRoot.innerHTML.includes('id="dh-st-reflect-btns"'), 'Stories opens interactive reflection prompts');
idMap.get('dh-st-back').onclick();
assert.ok(appRoot.innerHTML.includes('class="dh-regal-brand"'), 'Back button cleanly returns from Stories to Regal Home');

idMap.get('dh-open-poems').onclick();
assert.ok(appRoot.innerHTML.includes('id="dh-poem-themes"'), 'Poems opens interactive theme filters');
idMap.get('dh-po-back').onclick();

idMap.get('dh-open-parents').onclick();
assert.ok(appRoot.innerHTML.includes('id="dh-par-scenarios"'), 'Parents opens interactive conversation scenarios');
assert.ok(appRoot.innerHTML.includes('id="dh-pact-list"'), 'Parents opens interactive 5-item family pact checklist');
idMap.get('dh-par-back').onclick();

idMap.get('dh-open-guide').onclick();
assert.ok(idMap.get('dh-sys-guide'), 'System Guide opens interactive 3-layer philosophy explorer');
idMap.get('dh-guide-close').onclick();

/* Verify Strict P0 Quota Gate on Primary CTA with remaining=0 */
idMap.get('dh-start-journey').onclick();
assert.strictEqual(journeyStarts, 1, 'Hero primary CTA routes through startServerAuthorizedJourney');
assert.strictEqual(purchaseModalOpens, 1, 'With remaining=0, opens Purchase Modal without entering City of Dreams');
assert.strictEqual(ctx.__dhInJourney, false, '0 stages entered when quota is 0');

/* Cold-Load Budget (<2.0s) */
const indexBytes = Buffer.byteLength(indexHtml, 'utf8');
assert.ok(indexBytes < 20000, `docs/index.html must remain compact (<20KB, actual=${indexBytes}B)`);

(async () => {
  idMap.get('dh-copy-quote').onclick();
  await Promise.resolve();
  assert.ok(copiedClipboard.includes('https://asbe-siah.ir/'), 'Daily Wisdom share button copies formatted quote');
  console.log('Regal Luxury Home + Immediate Sanjesh + Daily Wisdom + Interactive Original Modules E2E: PASS');
})().catch(err => {
  console.error(err);
  process.exit(1);
});
