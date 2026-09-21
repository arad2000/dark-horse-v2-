// ==================== Dark Horse App V2.0 ====================
// تغییرات نسبت به V1.0:
//   • API_BASE → api.asbe-siah.ir
//   • AI counsel → /api/v2/darkhorse/counsel
//   • Endpointها → /api/v2/darkhorse/...
//   • فایل سوالات → questions_v2.json
//   • اضافه شدن صفحه انتخاب بین هدایت تحصیلی و انتخاب رشته دانشگاهی

const API_BASE = 'https://api.asbe-siah.ir';
const DATA_BASE = './data/';

// ==================== GLOBAL STATE ====================
const state = {
  sessionId: null,
  stage: 'splash',
  history: [],
  selectedRealms: [],
  selectedSubRealms: [],
  selectedNarrowPaths: [],
  likedCodes: [],
  strategyAnswers: [],
  valueAnswers: [],
  currentQuestion: 0,
  currentValueQuestion: 0,
  swipeCards: [],
  swipeIndex: 0,
  totalSwipes: 0,
  likedCodesSet: new Set(),
  completedPaths: new Set(),
  completedSubRealms: new Set(),
  strategyQuestions: [],
  valueQuestions: [],
  lastPayload: null,
  microMotivesMap: {},
  cachedMotives: null,
  traitMap: {},
  traitMapReady: false,
  questionsReady: false,
  motivesReady: false,
  retryCount: 0,
  // کش نتایج برای جلوگیری از درخواست مجدد
  majorsResult: null,
  branchesResult: null
};

const app = document.getElementById('app');

// ==================== Sanitize HTML ====================
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ==================== ذخیره و بازیابی خودکار (localStorage) ====================

// ==================== UX 10/10 HELPERS ====================
const STAGE_FLOW = [
  { id: 'manifesto', label: 'شروع' },
  { id: 'guide', label: 'راهنما' },
  { id: 'splash', label: 'شهر رؤیاها' },
  { id: 'realm', label: 'محله‌ها' },
  { id: 'subRealm', label: 'گذرها' },
  { id: 'narrowPath', label: 'مسیرها' },
  { id: 'introSwipe', label: 'جرقه‌ها' },
  { id: 'swipe', label: 'جرقه‌ها' },
  { id: 'introStrategies', label: 'راهبرد' },
  { id: 'strategies', label: 'راهبرد' },
  { id: 'introValues', label: 'ارزش‌ها' },
  { id: 'values', label: 'ارزش‌ها' },
  { id: 'choice', label: 'انتخاب' },
  { id: 'results', label: 'نتیجه' }
];

function ensureUXStyles() {
  if (document.getElementById('dh-ux-styles')) return;
  const s = document.createElement('style');
  s.id = 'dh-ux-styles';
  s.textContent = `
    .dh-progress-wrap{position:sticky;top:0;z-index:50;background:rgba(18,18,26,.94);backdrop-filter:blur(10px);padding:10px 0 8px;margin-bottom:10px;border-bottom:1px solid rgba(240,192,64,.12)}
    .dh-progress-labels{display:flex;justify-content:space-between;font-size:.72rem;color:#c9b896;margin-bottom:6px}
    .dh-progress-labels .on{color:#f0c040;font-weight:700}
    .dh-progress-track{height:6px;background:#2a2a3e;border-radius:99px;overflow:hidden}
    .dh-progress-fill{height:100%;background:linear-gradient(90deg,#b8860b,#f0c040,#ffe9a0);border-radius:99px;transition:width .4s ease;box-shadow:0 0 12px rgba(240,192,64,.45)}
    .dh-spark-chip{display:inline-flex;align-items:center;gap:6px;background:rgba(240,192,64,.1);border:1px solid rgba(240,192,64,.35);color:#f0c040;border-radius:99px;padding:7px 14px;font-size:.85rem;margin:6px 0 12px;box-shadow:0 0 20px rgba(240,192,64,.08)}
    .dh-stage-hint{color:#c9b896;font-size:.82rem;text-align:center;margin:0 0 14px;line-height:1.7}
    .option{transition:transform .18s ease,box-shadow .18s ease,border-color .18s,background .18s;border-radius:14px}
    .option:active{transform:scale(.975)}
    .option.selected{transform:scale(1.015);box-shadow:0 0 0 1px rgba(240,192,64,.5),0 8px 24px rgba(240,192,64,.12)}
    .swipe-card{animation:dhIn .32s ease;position:relative;overflow:hidden}
    .swipe-card::after{content:"";position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at 30% 20%,rgba(240,192,64,.08),transparent 50%)}
    @keyframes dhIn{from{opacity:0;transform:translateY(14px) scale(.98)}to{opacity:1;transform:none}}
    @keyframes dhFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
    @keyframes dhGlow{0%,100%{text-shadow:0 0 12px rgba(240,192,64,.3)}50%{text-shadow:0 0 22px rgba(240,192,64,.7)}}
    @keyframes dhPulse{0%,100%{opacity:.55}50%{opacity:1}}
    .dh-result-hero{background:linear-gradient(145deg,#1a1a2e,#2a1f12);border:1px solid rgba(240,192,64,.4);border-radius:18px;padding:20px;margin:14px 0;text-align:center;box-shadow:0 10px 36px rgba(0,0,0,.4),0 0 40px rgba(240,192,64,.08)}
    .dh-result-score{font-size:2.1rem;color:#f0c040;font-weight:800;letter-spacing:-1px}
    .dh-share-box{background:linear-gradient(180deg,#14141f,#12121c);border:1px dashed rgba(240,192,64,.4);border-radius:14px;padding:14px;margin-top:12px;font-size:.86rem;color:#cbb98a;line-height:1.9}
    .dh-loading{text-align:center;padding:48px 16px}
    .dh-loading .spin{width:30px;height:30px;border:3px solid #2a2a3e;border-top-color:#f0c040;border-radius:50%;margin:0 auto 16px;animation:dhSpin .75s linear infinite}
    @keyframes dhSpin{to{transform:rotate(360deg)}}
    .btn-primary{transition:transform .15s ease,box-shadow .15s}
    .btn-primary:active{transform:scale(.97)}
    .option-icon{font-size:1.85rem;line-height:1;margin-bottom:8px;display:block;filter:drop-shadow(0 2px 6px rgba(0,0,0,.35))}
    .dh-hero{text-align:center;padding:8px 0 6px;position:relative}
    .dh-hero-title{font-size:2rem;color:#f0c040;margin:8px 0 4px;animation:dhGlow 3.2s ease-in-out infinite}
    .dh-hero-sub{color:#9a8b60;font-size:.92rem;margin-bottom:8px}
    .dh-stars{letter-spacing:6px;font-size:.75rem;opacity:.7;animation:dhPulse 2.8s ease-in-out infinite}
    .dh-quote-card{position:relative;overflow:hidden}
    .dh-quote-card::before{content:"✦";position:absolute;top:10px;left:12px;color:rgba(240,192,64,.25);font-size:1.2rem}
    .dh-gate{display:inline-block;padding:4px 12px;border-radius:99px;border:1px solid rgba(240,192,64,.3);color:#d4af37;font-size:.75rem;margin-bottom:10px}
    .dh-celebrate{animation:dhIn .4s ease}
    .dh-fab-spark{position:fixed;right:14px;bottom:14px;z-index:60;background:rgba(20,20,30,.92);border:1px solid rgba(240,192,64,.4);color:#f0c040;border-radius:99px;padding:10px 14px;font-size:.8rem;box-shadow:0 8px 24px rgba(0,0,0,.35);backdrop-filter:blur(8px)}
  `;
  document.head.appendChild(s);
}

function progressHTML(stageId) {
  const ids = STAGE_FLOW.map(x => x.id);
  let idx = ids.indexOf(stageId);
  if (idx < 0) idx = 0;
  const uniqueSteps = ['splash','realm','subRealm','narrowPath','swipe','strategies','values','choice','results'];
  const stepMeta = [
    { id: 'realm', label: 'محله' },
    { id: 'swipe', label: 'جرقه' },
    { id: 'strategies', label: 'راهبرد' },
    { id: 'values', label: 'ارزش' },
    { id: 'results', label: 'نتیجه' }
  ];
  let u = uniqueSteps.indexOf(stageId);
  if (stageId === 'introSwipe') u = uniqueSteps.indexOf('swipe');
  if (stageId === 'introStrategies') u = uniqueSteps.indexOf('strategies');
  if (stageId === 'introValues') u = uniqueSteps.indexOf('values');
  if (u < 0) u = Math.min(idx, uniqueSteps.length - 1);
  const pct = Math.round((u / (uniqueSteps.length - 1)) * 100);
  const label = (STAGE_FLOW.find(x => x.id === stageId) || {}).label || '';
  // نگاشت مرحله به ۵ نقطهٔ اصلی
  const mapDot = (sid) => {
    if (['manifesto','guide','splash','realm','subRealm','narrowPath'].includes(sid)) return 0;
    if (['swipe','introSwipe'].includes(sid)) return 1;
    if (['strategies','introStrategies'].includes(sid)) return 2;
    if (['values','introValues'].includes(sid)) return 3;
    return 4;
  };
  const activeDot = mapDot(stageId);
  const dots = stepMeta.map((s, i) => {
    const cls = i < activeDot ? 'done' : (i === activeDot ? 'active' : '');
    return `<div class="dh-step ${cls}"><i></i><span>${s.label}</span></div>`;
  }).join('');
  return `
    <div class="dh-progress-wrap dh-edu-header">
      <div class="dh-progress-labels">
        <span class="dh-brand-mini">اسب سیاه</span>
        <span class="on">${label || 'سفر'} · ${pct}%</span>
      </div>
      <div class="dh-progress-track"><div class="dh-progress-fill" style="width:${pct}%"></div></div>
      <div class="dh-steps">${dots}</div>
    </div>`;
}

function sparkChipHTML() {
  const n = state.likedCodes.length;
  const min = 20, max = 80;
  let hint = n < min ? `${min - n} تا حداقل` : (n >= max ? 'کامل' : 'در حال تکمیل');
  const pct = Math.min(100, Math.round((n / max) * 100));
  return `<div class="dh-spark-chip">
    <div class="dh-spark-top"><span>✦ ${n} جرقه</span><span class="dh-spark-hint">${hint}</span></div>
    <div class="dh-spark-bar"><i style="width:${pct}%"></i></div>
  </div>`;
}

function loadingHTML(msg) {
  return `<div class="dh-loading"><div class="spin"></div><p style="color:#f0c040">${msg || 'داره پروفایلت چیده می‌شه...'}</p><p style="color:#c9b896;font-size:.85rem;margin-top:8px">اگر طول کشید، سرور در حال بیدار شدن است</p></div>`;
}

function wrapWithProgress(innerHTML) {
  ensureUXStyles();
  const show = !['manifesto'].includes(state.stage);
  return (show ? progressHTML(state.stage) : '') + innerHTML;
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    return false;
  }
}

async function dhCopyShare() {
  const text = window.__dhShareText || '';
  const ok = await copyText(text);
  alert(ok ? 'کپی شد ✅ می‌تونی تو پیام یا استوری بذاری' : 'کپی خودکار نشد؛ متن در کنسول موجود است');
  if (!ok && text) console.log(text);
}



function saveSession() {
  const sessionData = {
    sessionId: state.sessionId,
    selectedRealms: state.selectedRealms,
    selectedSubRealms: state.selectedSubRealms,
    selectedNarrowPaths: state.selectedNarrowPaths,
    likedCodes: state.likedCodes,
    strategyAnswers: state.strategyAnswers,
    valueAnswers: state.valueAnswers,
    currentQuestion: state.currentQuestion,
    currentValueQuestion: state.currentValueQuestion,
    stage: state.stage,
    history: state.history,
    swipeIndex: state.swipeIndex,
    totalSwipes: state.totalSwipes,
    completedPaths: [...(state.completedPaths || [])],
    completedSubRealms: [...(state.completedSubRealms || [])],
    journeyFinished: !!state.journeyFinished
  };
  try { localStorage.setItem('darkhorse_session_v2', JSON.stringify(sessionData)); } catch (e) {}
}

function loadSession() {
  const saved = localStorage.getItem('darkhorse_session_v2');
  if (!saved) return false;
  try {
    const data = JSON.parse(saved);
    state.sessionId = data.sessionId || null;
    state.selectedRealms = data.selectedRealms || [];
    state.selectedSubRealms = data.selectedSubRealms || [];
    state.selectedNarrowPaths = data.selectedNarrowPaths || [];
    state.likedCodes = data.likedCodes || [];
    state.strategyAnswers = data.strategyAnswers || [];
    state.valueAnswers = data.valueAnswers || [];
    state.currentQuestion = data.currentQuestion || 0;
    state.currentValueQuestion = data.currentValueQuestion || 0;
    state.stage = data.stage || 'splash';
    state.history = data.history || [];
    state.swipeIndex = data.swipeIndex || 0;
    state.totalSwipes = data.totalSwipes || 0;
    state.completedPaths = new Set(data.completedPaths || []);
    state.completedSubRealms = new Set(data.completedSubRealms || []);
    state.likedCodesSet = new Set(data.likedCodes || []);
    return true;
  } catch (e) { return false; }
}

function clearSession() {
  localStorage.removeItem('darkhorse_session_v2');
  window.__dhHasSavedSession = false;
  window.__dhSavedSession = null;
  window.__dhJourneyFinished = false;
}

/** قبل از دیدن نتایج، سشن وسط سفر نباید پاک/عوض شود */
function isPreResultsInProgress() {
  if (state.journeyFinished) return false;
  const st = state.stage;
  return ['realm', 'subRealm', 'narrowPath', 'introSwipe', 'swipe',
    'introStrategies', 'strategies', 'introValues', 'values', 'choice'].indexOf(st) >= 0;
}

function fullResetState(force) {
  if (!force && isPreResultsInProgress()) {
    console.warn('blocked fullResetState: journey not finished to results yet');
    return false;
  }
  clearSession();
  state.sessionId = null;
  state.history = [];
  state.selectedRealms = [];
  state.selectedSubRealms = [];
  state.selectedNarrowPaths = [];
  state.likedCodes = [];
  state.likedCodesSet = new Set();
  state.strategyAnswers = [];
  state.valueAnswers = [];
  state.currentQuestion = 0;
  state.currentValueQuestion = 0;
  state.swipeIndex = 0;
  state.totalSwipes = 0;
  state.completedPaths = new Set();
  state.completedSubRealms = new Set();
  state.lastPayload = null;
  state.cachedMotives = null;
  state.majorsResult = null;
  state.branchesResult = null;
  state.retryCount = 0;
  state.journeyFinished = false;
}


function startNewJourney() {
  try {
    if (isPreResultsInProgress()) {
      if (!confirm('سفر هنوز به نتیجه نرسیده. اگر از نو شروع کنی، پیشرفت فعلی پاک می‌شود. مطمئنی؟')) {
        try { if (typeof loadSession === 'function') loadSession(); } catch (e) {}
        if (typeof render === 'function') render();
        return;
      }
    }
    fullResetState(true);
    if (typeof REALMS === 'undefined' || !REALMS || !REALMS.length) {
      app.innerHTML = `<div class="card" style="margin:20px;text-align:right;">
        <h2 style="color:#f0c040">دادهٔ شهر رؤیاها لود نشد</h2>
        <p style="color:#c9b896;line-height:2">فایل <code>data.js</code> در دسترس نیست یا خطا دارد.</p>
        <button class="btn btn-primary" style="width:100%;margin-top:12px" onclick="location.reload()">تلاش دوباره</button>
        <button class="btn" style="width:100%;margin-top:8px" onclick="goTo('splash')">بازگشت</button>
      </div>`;
      return;
    }
    state.stage = 'realm';
    // Shell نباید پس از شروع سفر، صفحهٔ خانه را دوباره روی سفر نقاشی کند.
    window.__dhInJourney = true;
    try { if (typeof setActiveTab === 'function') setActiveTab('journey'); } catch (e) {}
    // ذخیرهٔ تمیز بدون تیک‌های قبلی
    saveSession();
    render();
  } catch (e) {
    console.error('startNewJourney error', e);
    app.innerHTML = `<div class="card" style="margin:20px;text-align:right;">
      <h2 style="color:#ff6b6b">خطا در ورود به محله‌ها</h2>
      <p style="color:#c9b896;direction:ltr;text-align:left;font-size:.8rem">${String(e && e.message ? e.message : e)}</p>
      <button class="btn btn-primary" style="width:100%;margin-top:12px" onclick="location.reload()">تلاش دوباره</button>
    </div>`;
  }
}
window.startNewJourney = startNewJourney;



function resumeJourney() {
  // از همان مرحلهٔ ذخیره‌شده ادامه بده
  if (!state.stage || state.stage === 'splash' || state.stage === 'manifesto' || state.stage === 'guide') {
    state.stage = 'realm';
  }
  saveSession();
  render();
}

// ==================== بارگذاری داده‌ها ====================
async function loadMicroMotivesMap() {
  try {
    const res = await fetch(DATA_BASE + 'micro_motives.json');
    const all = await res.json();
    all.forEach(m => { state.microMotivesMap[m.code] = m.description_fa; });
    state.motivesReady = true;
  } catch (e) {
    console.error('خطا در بارگذاری میکروموتیوها:', e);
    state.motivesReady = false;
  }
}

async function loadQuestions() {
  try {
    const res = await fetch(DATA_BASE + 'questions_v2.json');
    const data = await res.json();
    state.strategyQuestions = data.layers.strategies.questions;
    state.valueQuestions = data.layers.values.questions;
    state.questionsReady = true;
  } catch (e) {
    console.error('خطا در بارگذاری سوالات V2:', e);
    state.questionsReady = false;
  }
}

// نگاشت واقعی برچسب شخصیتی هر سؤال-گزینه (S01..S25 × index 0..4)
// این فایل جایگزین فرضِ نادرستِ «موقعیت index معنی ثابت دارد» می‌شود —
// چون trait_map_v3.json نشان داده در سؤالات مختلف، همان index معنی متفاوتی دارد.
async function loadTraitMap() {
  const candidates = [DATA_BASE + 'trait_map_v3.json', './trait_map_v3.json'];
  for (const url of candidates) {
    try {
      const res = await fetch(url);
      if (!res.ok) continue;
      const data = await res.json();
      if (data && typeof data === 'object' && (data.S01 || data.s01)) {
        state.traitMap = data;
        state.traitMapReady = true;
        console.log('trait_map loaded from', url);
        return;
      }
    } catch (e) {
      console.warn('trait_map try failed', url, e);
    }
  }
  console.error('نقشهٔ صفات بارگذاری نشد');
  state.traitMapReady = false;
  state.traitMap = {};
}

// ==================== NAVIGATION ====================

function scrollPageToTop() {
  try {
    var y = 0;
    try { window.scrollTo(0, 0); } catch (e0) {}
    try { window.scrollTo({ top: 0, left: 0, behavior: 'auto' }); } catch (e1) {}
    try {
      if (document.scrollingElement) document.scrollingElement.scrollTop = 0;
    } catch (e2) {}
    try { document.documentElement.scrollTop = 0; } catch (e3) {}
    try { document.body.scrollTop = 0; } catch (e4) {}

    var ids = ['app', 'dh-home-wrap'];
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      try { el.scrollTop = 0; } catch (e5) {}
      try { if (el.scrollTo) el.scrollTo(0, 0); } catch (e6) {}
    });

    // همه ظرف‌های اسکرول‌دار داخل صفحه
    try {
      var all = document.querySelectorAll('#app, .container, .dh-home-wrap, .card, .dh-guide-body, [style*="overflow"]');
      for (var i = 0; i < all.length; i++) {
        try { all[i].scrollTop = 0; } catch (e7) {}
      }
    } catch (e8) {}

    // موبایل / PWA: دوباره بعد از رسم
    try {
      requestAnimationFrame(function () {
        try { window.scrollTo(0, 0); } catch (e9) {}
        try { document.documentElement.scrollTop = 0; document.body.scrollTop = 0; } catch (e10) {}
      });
    } catch (e11) {}
    try {
      setTimeout(function () {
        try { window.scrollTo(0, 0); } catch (e12) {}
        try {
          if (document.scrollingElement) document.scrollingElement.scrollTop = 0;
        } catch (e13) {}
      }, 30);
      setTimeout(function () {
        try { window.scrollTo(0, 0); } catch (e14) {}
      }, 120);
    } catch (e15) {}
  } catch (eAll) {}
}
window.scrollPageToTop = scrollPageToTop;

function goTo(stage) {
  state.history.push(state.stage);
  state.stage = stage;
  if (stage === 'strategies') syncStrategyCursor();
  if (stage === 'values') syncValueCursor();
  saveSession();
  render();
  scrollPageToTop();
}
window.goTo = goTo;

function goBack() {
  if (state.history.length === 0) return;
  const prev = state.history.pop();
  state.stage = prev;
  if (prev === 'realm') { state.selectedSubRealms = []; state.selectedNarrowPaths = []; }
  else if (prev === 'subRealm') { state.selectedNarrowPaths = []; }
  state.currentQuestion = 0;
  state.currentValueQuestion = 0;
  saveSession();
  render();
  scrollPageToTop();
}

// ==================== RENDER ====================
function render() {
  try {
    ensureUXStyles();
    switch (state.stage) {
      case 'manifesto': state.stage='splash'; renderSplash(); break;
      case 'guide': state.stage='splash'; renderSplash(); break;
      case 'splash': renderSplash(); break;
      case 'realm': renderRealm(); break;
      case 'subRealm': renderSubRealm(); break;
      case 'narrowPath': renderNarrowPath(); break;
      case 'introSwipe': renderIntroSwipe(); break;
      case 'swipe': renderSwipe(); break;
      case 'introStrategies': renderIntroStrategies(); break;
      case 'strategies': renderStrategy(); break;
      case 'introValues': renderIntroValues(); break;
      case 'values': renderValue(); break;
      case 'choice': renderChoice(); break;
      case 'results': break;
      default:
        console.warn('unknown stage', state.stage);
        state.stage = 'splash';
        renderSplash();
    }
    scrollPageToTop();
    requestAnimationFrame(function () { scrollPageToTop(); });
    setTimeout(scrollPageToTop, 50);
  } catch (e) {
    console.error('render failed', state.stage, e);
    const root = document.getElementById('app');
    if (root) {
      root.innerHTML = `<div class="card" style="margin:16px;text-align:right">
        <h2 style="color:#ff6b6b">خطای نمایش</h2>
        <p style="color:#c9b896">مرحله: <b>${state.stage || '?'}</b></p>