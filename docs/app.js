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
const VALUE_SCHEMA_VERSION = 'v2-canonical-poles-1';
const VALUE_SCHEMA_RESET_NOTICE =
  'به‌دلیل به‌روزرسانی علمی قطب‌های ارزش برای دقت بیشتر تحلیل، پاسخ‌های ناتمام بخش ارزش بازنشانی شد تا دوباره با مقیاس جدید پاسخ دهی.';

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
  valueSchemaResetNotice: '',
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
try { window.state = state; } catch (_) {}

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

function dhFaNum(val) {
  return String(val == null ? '' : val).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[Number(d)]);
}

function dhShowJourneyToast(msg) {
  if (!msg) return;
  let el = document.getElementById('dh-journey-toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'dh-journey-toast';
    el.className = 'dh-journey-toast';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('is-visible');
  clearTimeout(window.__dhToastTimer);
  window.__dhToastTimer = setTimeout(() => {
    try { el.classList.remove('is-visible'); } catch (_) {}
  }, 2800);
}
window.dhShowJourneyToast = dhShowJourneyToast;

const DH_NAV_STAGES = [
  { id: 'realm', label: 'محله‌ها', match: ['splash', 'manifesto', 'guide', 'realm'] },
  { id: 'subRealm', label: 'گذرها', match: ['subRealm'] },
  { id: 'narrowPath', label: 'مسیرها', match: ['narrowPath'] },
  { id: 'swipe', label: 'خرده‌انگیزه‌ها', match: ['introSwipe', 'swipe'] },
  { id: 'strategies', label: 'راهبردها', match: ['introStrategies', 'strategies'] },
  { id: 'values', label: 'ارزش‌ها', match: ['introValues', 'values'] },
  { id: 'choice', label: 'نتیجه', match: ['choice', 'results'] }
];

function dhAnsweredCount(arr) {
  if (!Array.isArray(arr)) return 0;
  let c = 0;
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] !== undefined && arr[i] !== null && String(arr[i]).trim() !== '') c++;
  }
  return c;
}

function dhIsStageUnlocked(targetId) {
  const sTotal = (state.strategyQuestions && state.strategyQuestions.length) || 25;
  const vTotal = (state.valueQuestions && state.valueQuestions.length) || 15;
  const sDone = dhAnsweredCount(state.strategyAnswers);
  const vDone = dhAnsweredCount(state.valueAnswers);
  switch (targetId) {
    case 'splash':
    case 'realm':
      return true;
    case 'subRealm':
      return (state.selectedRealms && state.selectedRealms.length >= 1) || state.stage === 'subRealm';
    case 'narrowPath':
      return (state.selectedSubRealms && state.selectedSubRealms.length >= 1) || state.stage === 'narrowPath';
    case 'introSwipe':
    case 'swipe':
      return (state.selectedNarrowPaths && state.selectedNarrowPaths.length >= 1) ||
             (state.likedCodes && state.likedCodes.length > 0) ||
             state.stage === 'swipe' || state.stage === 'introSwipe';
    case 'introStrategies':
    case 'strategies':
      return (state.likedCodes && state.likedCodes.length >= 20) || sDone > 0 ||
             state.stage === 'strategies' || state.stage === 'introStrategies';
    case 'introValues':
    case 'values':
      return sDone >= sTotal || vDone > 0 ||
             state.stage === 'values' || state.stage === 'introValues';
    case 'choice':
    case 'results':
      return vDone >= vTotal || Boolean(state.majorsResult || state.branchesResult) ||
             state.stage === 'choice' || state.stage === 'results';
    default:
      return false;
  }
}
window.dhIsStageUnlocked = dhIsStageUnlocked;

function dhStageUnlockHint(targetId) {
  switch (targetId) {
    case 'subRealm':
      return 'ابتدا حداقل یک محله انتخاب کن تا گذرهای آن باز شوند.';
    case 'narrowPath':
      return 'ابتدا حداقل یک گذر انتخاب کن تا مسیرهای باریک نمایش داده شوند.';
    case 'swipe':
      return 'ابتدا حداقل یک مسیر باریک انتخاب کن تا خرده‌انگیزه‌ها باز شوند.';
    case 'strategies': {
      const rem = Math.max(0, 20 - ((state.likedCodes && state.likedCodes.length) || 0));
      return rem > 0
        ? `برای ورود به سؤالات راهبرد، ${dhFaNum(rem)} جرقهٔ دیگر لازم داری (حداقل ۲۰ جرقه).`
        : 'اکنون می‌توانی وارد سؤالات راهبرد شوی.';
    }
    case 'values':
      return 'ابتدا به همهٔ سؤالات راهبرد پاسخ بده تا بخش ارزش‌ها باز شود.';
    case 'choice':
      return 'پس از تکمیل سؤالات ارزش، صفحهٔ تحلیل و نتیجه باز می‌شود.';
    default:
      return '';
  }
}

function dhStageBadgeText(stageId) {
  const sDone = dhAnsweredCount(state.strategyAnswers);
  const vDone = dhAnsweredCount(state.valueAnswers);
  switch (stageId) {
    case 'realm':
      return state.selectedRealms && state.selectedRealms.length ? dhFaNum(state.selectedRealms.length) : '';
    case 'subRealm':
      return state.selectedSubRealms && state.selectedSubRealms.length ? dhFaNum(state.selectedSubRealms.length) : '';
    case 'narrowPath':
      return state.selectedNarrowPaths && state.selectedNarrowPaths.length ? dhFaNum(state.selectedNarrowPaths.length) : '';
    case 'swipe':
      return state.likedCodes && state.likedCodes.length ? '✦' + dhFaNum(state.likedCodes.length) : '';
    case 'strategies':
      return sDone > 0 ? dhFaNum(sDone) : '';
    case 'values':
      return vDone > 0 ? dhFaNum(vDone) : '';
    case 'choice':
      return (state.majorsResult || state.branchesResult) ? '✓' : '';
    default:
      return '';
  }
}

function dhStageDetailLabel(stageId) {
  const sTotal = (state.strategyQuestions && state.strategyQuestions.length) || 25;
  const vTotal = (state.valueQuestions && state.valueQuestions.length) || 15;
  switch (stageId) {
    case 'splash':
      return 'دروازهٔ شهر رؤیاها';
    case 'realm':
      return state.selectedRealms && state.selectedRealms.length
        ? `محله‌ها · ${dhFaNum(state.selectedRealms.length)} انتخاب`
        : 'انتخاب محله';
    case 'subRealm':
      return state.selectedSubRealms && state.selectedSubRealms.length
        ? `گذرها · ${dhFaNum(state.selectedSubRealms.length)} انتخاب`
        : 'انتخاب گذر';
    case 'narrowPath':
      return state.selectedNarrowPaths && state.selectedNarrowPaths.length
        ? `مسیرهای باریک · ${dhFaNum(state.selectedNarrowPaths.length)} انتخاب`
        : 'انتخاب مسیر باریک';
    case 'introSwipe':
      return 'آمادهٔ ورود به خرده‌انگیزه‌ها';
    case 'swipe': {
      const deckLen = (state.swipeCards && state.swipeCards.length) || state.totalSwipes || 0;
      const cur = Math.min((state.swipeIndex || 0) + 1, Math.max(deckLen, 1));
      return deckLen > 0 && (state.swipeIndex || 0) < deckLen
        ? `خرده‌انگیزه‌ها · کارت ${dhFaNum(cur)} از ${dhFaNum(deckLen)}`
        : `خرده‌انگیزه‌ها · ${dhFaNum((state.likedCodes || []).length)} جرقه`;
    }
    case 'introStrategies':
      return 'ورود به سؤالات راهبرد';
    case 'strategies':
      return `سؤالات راهبرد · سؤال ${dhFaNum((state.currentQuestion || 0) + 1)} از ${dhFaNum(sTotal)}`;
    case 'introValues':
      return 'ورود به سؤالات ارزش';
    case 'values':
      return `سؤالات ارزش · سؤال ${dhFaNum((state.currentValueQuestion || 0) + 1)} از ${dhFaNum(vTotal)}`;
    case 'choice':
      return 'انتخاب نوع تحلیل';
    case 'results':
      return state.lastCounselKind === 'branches' ? 'نتیجهٔ هدایت تحصیلی' : 'نتیجهٔ انتخاب رشته';
    default:
      return (STAGE_FLOW.find(x => x.id === stageId) || {}).label || 'سفر اکتشافی';
  }
}

function dhComputeJourneyPercent(stageId) {
  const sTotal = (state.strategyQuestions && state.strategyQuestions.length) || 25;
  const vTotal = (state.valueQuestions && state.valueQuestions.length) || 15;
  const sparks = Math.min(20, (state.likedCodes && state.likedCodes.length) || 0);
  const sDone = Math.min(sTotal, dhAnsweredCount(state.strategyAnswers));
  const vDone = Math.min(vTotal, dhAnsweredCount(state.valueAnswers));
  if (stageId === 'results') return 100;
  if (stageId === 'choice') return 94;
  let score = 0;
  if (stageId !== 'splash') score += 6;
  if (state.selectedRealms && state.selectedRealms.length) score += 8;
  if (state.selectedSubRealms && state.selectedSubRealms.length) score += 8;
  if (state.selectedNarrowPaths && state.selectedNarrowPaths.length) score += 8;
  score += Math.round((sparks / 20) * 24);
  score += Math.round((sDone / sTotal) * 24);
  score += Math.round((vDone / vTotal) * 20);
  return Math.max(0, Math.min(96, score));
}

function dhCaptureCurrentScroll() {
  try {
    const y = window.scrollY || window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    state.lastScrollY = Math.max(0, Math.round(y));
  } catch (_) {
    state.lastScrollY = 0;
  }
}

function dhGoHomeKeepPlace() {
  dhCaptureCurrentScroll();
  if (state.stage === 'results' && (state.majorsResult || state.branchesResult)) {
    window.__dhCachedResultsPlace = {
      kind: state.lastCounselKind === 'branches' && state.branchesResult ? 'branches' : 'majors',
      scrollY: state.lastScrollY || 0,
      savedAt: Date.now()
    };
  } else {
    try { saveSession(); } catch (_) {}
    window.__dhActiveInMemoryPlace = {
      stage: state.stage || 'splash',
      scrollY: state.lastScrollY || 0,
      savedAt: Date.now()
    };
  }
  window.__dhInJourney = false;
  if (window.DHShell && typeof window.DHShell.renderHome === 'function') {
    window.DHShell.renderHome();
  }
}
window.dhGoHomeKeepPlace = dhGoHomeKeepPlace;

async function dhJumpToStage(targetId) {
  if (!targetId) return;
  if (state.journeyFinished && targetId !== 'choice' && targetId !== 'results') {
    const gateOk = dhEnsureServerQuotaGate({
      mode: 'new',
      sessionId: '',
      isFinished: true,
      targetStage: targetId
    });
    if (!gateOk) return;
  }
  if (!dhIsStageUnlocked(targetId)) {
    dhShowJourneyToast(dhStageUnlockHint(targetId));
    return;
  }
  if (targetId === 'choice' && state.stage !== 'choice' && (state.majorsResult || state.branchesResult) && state.journeyFinished) {
    const kind = state.lastCounselKind === 'branches' && state.branchesResult ? 'branches' : 'majors';
    displayResults(kind === 'branches' ? state.branchesResult : state.majorsResult, kind);
    return;
  }
  if (targetId === 'swipe') {
    if ((!state.swipeCards || state.swipeCards.length === 0) && state.selectedNarrowPaths && state.selectedNarrowPaths.length > 0) {
      await ensureSwipeDeckHydrated(false);
    }
    if (!state.swipeCards || state.swipeCards.length === 0) {
      goTo('introSwipe');
      return;
    }
  }
  if (state.stage === targetId) return;
  goTo(targetId);
}
window.dhJumpToStage = dhJumpToStage;

function ensureUXStyles() {
  try {
    if (!document.getElementById('dh-journey-exp-link') && document.head && typeof document.createElement === 'function') {
      const link = document.createElement('link');
      link.id = 'dh-journey-exp-link';
      link.rel = 'stylesheet';
      link.href = 'journey_experience.css?v=2';
      document.head.appendChild(link);
    }
  } catch (_) {}
  if (document.getElementById('dh-ux-styles')) return;
  const s = document.createElement('style');
  s.id = 'dh-ux-styles';
  s.textContent = `
    .dh-progress-wrap{position:sticky;top:0;z-index:50;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
    .dh-stage-hint{color:#cfc9bb;font-size:.9rem;text-align:center;margin:0 0 12px;line-height:1.85}
    .dh-dreamcity-invite{margin:8px auto 12px;max-width:425px;color:#efe9dc!important;font-size:.94rem!important;font-weight:500;line-height:1.9!important}
    .dh-realm-invite{margin:0 auto 12px!important;max-width:460px;padding:10px 14px;border-radius:13px;background:rgba(240,192,64,.07);border:1px solid rgba(240,192,64,.24);color:#ece6d8!important;font-size:.91rem!important;line-height:1.88!important;text-align:right!important}
    .option{transition:border-color .18s ease,background .18s ease,box-shadow .18s ease,transform .14s ease}
    .option:active:not(.disabled):not(.dh-path-done){transform:scale(.988)}
    .dh-card-meta-row{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:9px}
    .dh-world-tag{display:inline-flex;align-items:center;gap:7px;font-size:.78rem;font-weight:800;color:var(--dh-world,#f0c040)}
    .dh-sigil-box{width:28px;height:28px;min-width:28px;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;background:var(--dh-world-soft,rgba(240,192,64,.12));border:1px solid var(--dh-world-border,rgba(240,192,64,.35));color:var(--dh-world,#f0c040);box-shadow:0 3px 10px var(--dh-world-glow,rgba(0,0,0,.2));flex:0 0 28px}
    .dh-sigil-box svg{width:18px;height:18px;flex:0 0 18px;display:block}
    .dh-sigil-box--sm{width:24px;height:24px;min-width:24px;border-radius:7px;flex:0 0 24px}
    .dh-sigil-box--sm svg{width:15px;height:15px;flex:0 0 15px}
    .dh-world-orb svg,.dh-swipe-world-pill svg{width:14px;height:14px;flex:0 0 14px;display:block}
    #app .option.dh-route-card .dh-route-motto{color:#fbf6ea!important;font-size:1.05rem!important;font-weight:800!important;line-height:1.72!important}
    #app .option.dh-route-card .dh-route-desc{color:#e2dcd0!important;font-size:.935rem!important;font-weight:500!important;line-height:1.9!important}
    #app .option.dh-route-card.selected .dh-route-motto{color:#fff3cf!important}
    #app .option.dh-route-card.selected .dh-route-desc{color:#efe9dc!important}
    .dh-choice-modes{display:grid;grid-template-columns:minmax(0,1fr);gap:14px;margin:16px 0}
    #app .dh-choice-mode-card{width:100%;display:block;margin:0!important;text-align:right;padding:18px 18px!important;border-radius:18px!important;cursor:pointer;border:1.5px solid #fbe38e!important;background:linear-gradient(135deg,#f8da72 0%,#f0c040 52%,#cfa125 100%)!important;color:#141108!important;font-family:inherit;box-shadow:0 12px 30px rgba(240,192,64,.34),inset 0 1px 0 rgba(255,250,224,.55)!important;transition:transform .18s ease,box-shadow .2s ease,filter .2s ease!important}
    #app .dh-choice-mode-card--alt{border-color:#ffe8a3!important;background:linear-gradient(135deg,#f5d259 0%,#e7b532 54%,#c7951c 100%)!important}
    #app .dh-choice-mode-card:hover:not(:disabled):not([aria-disabled="true"]){transform:translateY(-2px);filter:brightness(1.03);box-shadow:0 16px 36px rgba(240,192,64,.45),inset 0 1px 0 rgba(255,252,232,.72)!important}
    #app .dh-choice-mode-card:active:not(:disabled):not([aria-disabled="true"]){transform:scale(.986)}
    #app .dh-choice-mode-card:disabled,#app .dh-choice-mode-card[aria-disabled="true"]{background:#222634!important;border:1.5px solid rgba(255,255,255,.13)!important;color:#8e8a7f!important;box-shadow:none!important;opacity:.62!important;cursor:not-allowed!important;transform:none!important;filter:none!important}
    .dh-choice-kicker{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.74rem;font-weight:800;color:#f8da72;background:rgba(14,16,23,.88);border:1px solid rgba(255,248,220,.22);margin-bottom:8px}
    .dh-choice-title{font-size:1.08rem;font-weight:900;color:#120f07;line-height:1.6;margin-bottom:5px}
    .dh-choice-sub{font-size:.86rem;font-weight:600;color:#26200f;line-height:1.75}
    #app .dh-choice-mode-card:disabled .dh-choice-kicker,#app .dh-choice-mode-card[aria-disabled="true"] .dh-choice-kicker{color:#9e9a8f;background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.1)}
    #app .dh-choice-mode-card:disabled .dh-choice-title,#app .dh-choice-mode-card[aria-disabled="true"] .dh-choice-title{color:#a6a296}
    #app .dh-choice-mode-card:disabled .dh-choice-sub,#app .dh-choice-mode-card[aria-disabled="true"] .dh-choice-sub{color:#858176}
    .swipe-card{animation:dhIn .24s ease;position:relative;overflow:hidden}
    .swipe-card::after{content:"";position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at 30% 18%,rgba(240,192,64,.06),transparent 52%)}
    @keyframes dhIn{from{opacity:0;transform:translateY(10px) scale(.99)}to{opacity:1;transform:none}}
    @keyframes dhFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
    @keyframes dhGlow{0%,100%{text-shadow:0 0 10px rgba(240,192,64,.22)}50%{text-shadow:0 0 18px rgba(240,192,64,.45)}}
    @keyframes dhPulse{0%,100%{opacity:.6}50%{opacity:1}}
    .dh-result-hero{background:#171a25;border:1px solid rgba(240,192,64,.42);border-radius:18px;padding:20px;margin:14px 0;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,.35)}
    .dh-result-score{font-size:2.1rem;color:#f0c040;font-weight:800;letter-spacing:-1px}
    .dh-share-box{background:#151824;border:1px dashed rgba(240,192,64,.36);border-radius:14px;padding:14px;margin-top:12px;font-size:.86rem;color:#d6d1c4;line-height:1.9}
    .dh-loading{text-align:center;padding:48px 16px}
    .dh-loading .spin{width:30px;height:30px;border:3px solid #252a3a;border-top-color:#f0c040;border-radius:50%;margin:0 auto 16px;animation:dhSpin .75s linear infinite}
    @keyframes dhSpin{to{transform:rotate(360deg)}}
    .btn-primary{transition:transform .15s ease,box-shadow .15s}
    .btn-primary:active{transform:scale(.975)}
    .dh-hero{text-align:center;padding:8px 0 6px;position:relative}
    .dh-hero-title{font-size:1.85rem;color:#f5efe2;margin:8px 0 4px}
    .dh-hero-sub{color:#b8b2a4;font-size:.9rem;margin-bottom:8px}
    .dh-stars{letter-spacing:6px;font-size:.75rem;color:#f0c040;opacity:.75;animation:dhPulse 2.8s ease-in-out infinite}
    .dh-gate{display:inline-block;padding:4px 12px;border-radius:99px;border:1px solid rgba(240,192,64,.3);color:#f0c040;font-size:.75rem;margin-bottom:10px}
    .dh-celebrate{animation:dhIn .35s ease}
    .dh-journey-toast{position:fixed;left:50%;bottom:74px;transform:translateX(-50%) translateY(14px);background:#1c2030;color:#f5efe2;border:1px solid rgba(240,192,64,.5);border-radius:14px;padding:10px 16px;font-size:.82rem;line-height:1.7;max-width:min(92vw,440px);text-align:center;z-index:9998;opacity:0;pointer-events:none;box-shadow:0 12px 30px rgba(0,0,0,.45);transition:opacity .2s ease,transform .2s ease}
    .dh-journey-toast.is-visible{opacity:1;transform:translateX(-50%) translateY(0)}
  `;
  document.head.appendChild(s);
}

function progressHTML(stageId) {
  const pct = dhComputeJourneyPercent(stageId);
  const detail = dhStageDetailLabel(stageId);
  const hideStageNav = stageId === 'results' || Boolean(state && state.journeyFinished);
  const activeNavIdx = DH_NAV_STAGES.findIndex(s => s.match.includes(stageId));
  const navPills = hideStageNav ? '' : DH_NAV_STAGES.map((s, i) => {
    const isCurrent = s.match.includes(stageId);
    const unlocked = dhIsStageUnlocked(s.id);
    const badge = dhStageBadgeText(s.id);
    const cls = [
      'dh-step',
      'dh-stage-pill',
      isCurrent ? 'active' : '',
      !isCurrent && unlocked && i < (activeNavIdx < 0 ? 0 : activeNavIdx) ? 'done' : '',
      unlocked ? 'is-unlocked' : 'is-locked'
    ].filter(Boolean).join(' ');
    return `<button type="button" class="${cls}" onclick="dhJumpToStage('${s.id}')" aria-current="${isCurrent ? 'step' : 'false'}"><i></i><span>${s.label}</span>${badge ? `<em class="dh-pill-count">${badge}</em>` : ''}</button>`;
  }).join('');
  return `
    <div class="dh-progress-wrap dh-edu-header" role="navigation" aria-label="ناوبری مراحل سفر">
      <div class="dh-progress-labels">
        <button type="button" class="dh-home-chip" onclick="dhGoHomeKeepPlace()" title="بازگشت به صفحه اول و حفظ دقیق همین صفحه">⌂ صفحه اول</button>
        <span class="on">${detail} · ${dhFaNum(pct)}٪</span>
      </div>
      <div class="dh-progress-track"><div class="dh-progress-fill" style="width:${pct}%"></div></div>
      ${hideStageNav ? '' : `<div class="dh-steps dh-stage-nav">${navPills}</div>`}
    </div>`;
}

function sparkChipHTML() {
  const n = state.likedCodes.length;
  const min = 20, max = 80;
  let hint = n < min
    ? `حداقل ${dhFaNum(min)} جرقه لازم است (${dhFaNum(min - n)} مانده)`
    : (n >= max ? 'ظرفیت کامل شد' : 'محدودهٔ مناسب برای تحلیل دقیق');
  const pct = Math.min(100, Math.round((n / max) * 100));
  return `<div class="dh-spark-chip" role="status" aria-live="polite">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">
      <span>✦ ${dhFaNum(n)} جرقه انتخاب‌شده</span>
      <span style="color:#b8b2a4;font-size:.77rem;font-weight:500;">${hint}</span>
    </div>
    <div class="dh-spark-bar"><div class="dh-spark-fill" style="width:${pct}%"></div></div>
  </div>`;
}

function loadingHTML(msg) {
  return `<div class="dh-loading"><div class="dh-reveal-orb" aria-hidden="true"></div><p id="dh-reveal-step-text" style="color:#f5efe2;font-weight:800;font-size:.98rem;">${msg || '۱ از ۳ · در حال خوانش جرقه‌های انرژی درونی تو...'}</p><p style="color:#b8b2a4;font-size:.84rem;margin-top:8px">نقشهٔ فردیت تو در حال ترکیب است؛ همهٔ انتخاب‌هایت محفوظ مانده‌اند.</p></div>`;
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



function durableJourneySessionIdForSave() {
  var authorizedSessionId = null;
  var pendingSessionId = null;
  var chargedSessionId = null;
  var savedSessionId = null;
  try { authorizedSessionId = String(window.__dhCommercialJourneyAuthorizedSessionId || ''); } catch (_) {}
  try { pendingSessionId = String(localStorage.getItem('dh_pending_journey_session_id') || ''); } catch (_) {}
  try { chargedSessionId = String(localStorage.getItem('dh_quota_charged_session_v1') || ''); } catch (_) {}
  try {
    var persisted = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null');
    savedSessionId = persisted && persisted.sessionId ? String(persisted.sessionId) : '';
  } catch (_) {}
  // If commercial gate just authorized a specific session ID for starting/resuming a journey,
  // ALWAYS keep state.sessionId and storage strictly aligned with that authorized ID!
  if (authorizedSessionId) {
    state.sessionId = authorizedSessionId;
    return authorizedSessionId;
  }
  if (pendingSessionId && state && state.sessionId === pendingSessionId) {
    return pendingSessionId;
  }
  // During confirmed charge recovery, the matching pending UUID intentionally
  // rebinds the unfinished journey. Without that marker, never rewrite a
  // different, non-empty persisted UUID merely because in-memory state differs.
  if (chargedSessionId && (pendingSessionId === chargedSessionId || !savedSessionId || savedSessionId === chargedSessionId)) {
    state.sessionId = chargedSessionId;
    return chargedSessionId;
  }
  if (chargedSessionId && savedSessionId && savedSessionId !== chargedSessionId) {
    state.sessionId = savedSessionId;
    return savedSessionId;
  }
  if (state && state.sessionId) return String(state.sessionId);
  if (savedSessionId) state.sessionId = savedSessionId;
  return savedSessionId || null;
}

function saveSession() {
  const schemaVer = 'v2-canonical-poles-1';
  const stableSessionId = durableJourneySessionIdForSave();
  const deckCodes = Array.isArray(state.swipeCards) && state.swipeCards.length > 0
    ? state.swipeCards.map(function (c) { return c && c.code ? String(c.code) : ''; }).filter(Boolean)
    : (Array.isArray(state.swipeDeckCodes) ? state.swipeDeckCodes : []);
  const sessionData = {
    sessionId: stableSessionId,
    valueSchemaVersion: schemaVer,
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
    swipeDeckCodes: deckCodes,
    lastScrollY: typeof state.lastScrollY === 'number' ? state.lastScrollY : 0,
    completedPaths: [...(state.completedPaths || [])],
    completedSubRealms: [...(state.completedSubRealms || [])],
    journeyFinished: !!state.journeyFinished
  };
  try { localStorage.setItem('darkhorse_session_v2', JSON.stringify(sessionData)); } catch (e) {}
}

function loadSession() {
  const schemaVer = 'v2-canonical-poles-1';
  const resetMsg = 'به‌دلیل به‌روزرسانی علمی قطب‌های ارزش برای دقت بیشتر تحلیل، پاسخ‌های ناتمام بخش ارزش بازنشانی شد تا دوباره با مقیاس جدید پاسخ دهی.';
  const saved = localStorage.getItem('darkhorse_session_v2');
  if (!saved) return false;
  try {
    const data = JSON.parse(saved);
    var pendingSessionId = null;
    var chargedSessionId = null;
    try { pendingSessionId = localStorage.getItem('dh_pending_journey_session_id'); } catch (_) {}
    try { chargedSessionId = localStorage.getItem('dh_quota_charged_session_v1'); } catch (_) {}
    var storedSessionId = data.sessionId ? String(data.sessionId) : '';
    var pendingChargedId = pendingSessionId && chargedSessionId === pendingSessionId
      ? String(pendingSessionId) : '';
    // An explicit pending+charged pair marks a just-confirmed rebind. Otherwise
    // an unfinished journey with a conflicting UUID must not be resumed.
    if (chargedSessionId && storedSessionId && storedSessionId !== String(chargedSessionId) && !pendingChargedId) {
      return false;
    }
    var wasValueSchemaReset = false;
    if (data && typeof data === 'object' && !data.journeyFinished && data.valueSchemaVersion !== schemaVer) {
      var hasLegacyVals = Array.isArray(data.valueAnswers) &&
        data.valueAnswers.some(function (v) { return v !== undefined && v !== null && String(v).trim() !== ''; });
      var hasLegacyCur = Number(data.currentValueQuestion || 0) > 0;
      if (!hasLegacyVals && !hasLegacyCur) {
        data.valueSchemaVersion = schemaVer;
      } else {
        data.valueAnswers = [];
        data.currentValueQuestion = 0;
        data.valueSchemaVersion = schemaVer;
        if (data.stage === 'values' || data.stage === 'choice') {
          data.stage = 'introValues';
        }
        state.valueSchemaResetNotice = resetMsg;
        try {
          if (typeof window !== 'undefined' && window) window.__dhValueSchemaResetNotice = resetMsg;
        } catch (_) {}
        wasValueSchemaReset = true;
      }
    }
    var recoveredChargedId = pendingChargedId || (chargedSessionId && !storedSessionId ? String(chargedSessionId) : '');
    state.sessionId = recoveredChargedId || (storedSessionId || null);
    if (wasValueSchemaReset || (state.sessionId && String(data.sessionId || '') !== String(state.sessionId))) {
      if (state.sessionId) data.sessionId = String(state.sessionId);
      try { localStorage.setItem('darkhorse_session_v2', JSON.stringify(data)); } catch (_) {}
    }
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
    state.swipeDeckCodes = Array.isArray(data.swipeDeckCodes) ? data.swipeDeckCodes : [];
    state.lastScrollY = Number(data.lastScrollY || 0);
    if (Array.isArray(state.swipeDeckCodes) && state.swipeDeckCodes.length > 0 && Array.isArray(state.cachedMotives)) {
      var byCode = {};
      state.cachedMotives.forEach(function (m) { if (m && m.code) byCode[m.code] = m; });
      var restoredDeck = state.swipeDeckCodes.map(function (c) { return byCode[c]; }).filter(Boolean);
      if (restoredDeck.length > 0) {
        state.swipeCards = restoredDeck;
        state.totalSwipes = restoredDeck.length;
      }
    }
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
  state.swipeCards = [];
  state.swipeDeckCodes = [];
  state.lastScrollY = 0;
  state.swipeIndex = 0;
  state.totalSwipes = 0;
  state.completedPaths = new Set();
  state.completedSubRealms = new Set();
  state.lastPayload = null;
  state.cachedMotives = state.cachedMotives || null;
  state.majorsResult = null;
  state.branchesResult = null;
  state.retryCount = 0;
  state.journeyFinished = false;
  try { window.__dhCachedResultsPlace = null; } catch (_) {}
}


function dhHasCommercialRuntime() {
  return Boolean(typeof window !== 'undefined' && window && (window.DHAuth || window.DHCommercialUI));
}

function dhEnsureServerQuotaGate(opts) {
  var options = opts || {};
  if (!dhHasCommercialRuntime()) return true;
  if (!window.DHAuth || typeof window.DHAuth.isLoggedIn !== 'function' || !window.DHAuth.isLoggedIn()) {
    window.__dhInJourney = false;
    try {
      if (window.DHShell && typeof window.DHShell.renderHome === 'function' &&
          !(state && state.stage === 'results' && (state.majorsResult || state.branchesResult))) {
        window.DHShell.renderHome();
      }
    } catch (_) {}
    if (window.DHCommercialUI && typeof window.DHCommercialUI.showAuth === 'function') {
      window.DHCommercialUI.showAuth('login');
    }
    return false;
  }
  if (window.DHCommercialUI &&
      typeof window.DHCommercialUI.isActiveStageAuthorized === 'function' &&
      typeof window.DHCommercialUI.ensureCanEnterJourney === 'function') {
    if (options.mode !== 'new' &&
        window.DHCommercialUI.isActiveStageAuthorized(options.sessionId, Boolean(options.isFinished), options.targetStage || '')) {
      return true;
    }
    window.DHCommercialUI.ensureCanEnterJourney({
      mode: options.mode || 'new',
      sessionId: options.mode === 'new' ? '' : String(options.sessionId || ''),
      onAuthorized: options.onAuthorized
    });
    return false;
  }
  return true;
}

function dhExecuteStartNewJourney(approvedSessionId, prevWasFinished, prevUnchargedId) {
  fullResetState(true);
  if (approvedSessionId) {
    if (prevWasFinished) {
      try { localStorage.removeItem('dh_quota_charged_session_v1'); } catch (eClr0) {}
    }
    state.sessionId = String(approvedSessionId);
  } else if (prevWasFinished) {
    try { localStorage.removeItem('dh_quota_charged_session_v1'); } catch (eClr) {}
    if (window.DHQuotaEnforcement && typeof window.DHQuotaEnforcement.ensureJourneySession === 'function') {
      try { state.sessionId = window.DHQuotaEnforcement.ensureJourneySession(); } catch (eNewId) {}
    }
  } else if (prevUnchargedId) {
    state.sessionId = prevUnchargedId;
  } else if (window.DHQuotaEnforcement && typeof window.DHQuotaEnforcement.ensureJourneySession === 'function') {
    try { state.sessionId = window.DHQuotaEnforcement.ensureJourneySession(); } catch (eInitId) {}
  }
  if (typeof REALMS === 'undefined' || !REALMS || !REALMS.length) {
    app.innerHTML = `<div class="card" style="margin:20px;text-align:right;">
      <h2 style="color:#f0c040">دادهٔ شهر رؤیاها لود نشد</h2>
      <p style="color:#c9b896;line-height:2">فایل <code>data.js</code> در دسترس نیست یا خطا دارد.</p>
      <button class="btn btn-primary" style="width:100%;margin-top:12px" onclick="location.reload()">تلاش دوباره</button>
      <button class="btn" style="width:100%;margin-top:8px" onclick="dhGoHomeKeepPlace()">بازگشت به صفحه اول</button>
    </div>`;
    return;
  }
  state.stage = 'realm';
  window.__dhInJourney = true;
  try { if (window.DHShell && typeof window.DHShell.setActiveTab === 'function') window.DHShell.setActiveTab('journey'); } catch (e) {}
  // ذخیرهٔ تمیز بدون تیک‌های قبلی
  saveSession();
  render();
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
    var prevWasFinished = !!state.journeyFinished;
    var prevUnchargedId = !prevWasFinished && state.sessionId ? String(state.sessionId) : '';
    try {
      var prevSaved = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null');
      if (prevSaved && prevSaved.journeyFinished) prevWasFinished = true;
      if (!prevWasFinished && !prevUnchargedId && prevSaved && prevSaved.sessionId) {
        prevUnchargedId = String(prevSaved.sessionId);
      }
    } catch (ePrev) {}
    var prevAlreadyConsumed = Boolean(
      prevUnchargedId && window.DHCommercialUI &&
      typeof window.DHCommercialUI.isSessionConsumedLocallyOrServer === 'function' &&
      window.DHCommercialUI.isSessionConsumedLocallyOrServer(prevUnchargedId)
    );
    var alreadyAuthorizedUncharged = Boolean(
      !prevWasFinished && !prevAlreadyConsumed && prevUnchargedId &&
      window.DHCommercialUI && typeof window.DHCommercialUI.isActiveStageAuthorized === 'function' &&
      window.DHCommercialUI.isActiveStageAuthorized(prevUnchargedId, false, 'realm')
    );
    if (!alreadyAuthorizedUncharged) {
      var gateOk = dhEnsureServerQuotaGate({
        mode: 'new',
        sessionId: '',
        isFinished: true,
        targetStage: 'realm',
        onAuthorized: function (approvedId) {
          dhExecuteStartNewJourney(approvedId, true, '');
        }
      });
      if (!gateOk) return;
    }
    dhExecuteStartNewJourney('', prevWasFinished, prevUnchargedId);
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
let _motivesLoadPromise = null;
let _questionsLoadPromise = null;
let _traitMapLoadPromise = null;

async function loadMicroMotivesMap() {
  if (state.motivesReady && Array.isArray(state.cachedMotives) && state.cachedMotives.length > 0) return;
  if (_motivesLoadPromise) return _motivesLoadPromise;
  _motivesLoadPromise = (async () => {
    try {
      const res = await fetch(DATA_BASE + 'micro_motives.json?v=motives-1393-v1');
      const all = await res.json();
      state.cachedMotives = all;
      all.forEach(m => { state.microMotivesMap[m.code] = m.description_fa; });
      state.motivesReady = true;
    } catch (e) {
      console.error('خطا در بارگذاری میکروموتیوها:', e);
      state.motivesReady = false;
    } finally {
      _motivesLoadPromise = null;
    }
  })();
  return _motivesLoadPromise;
}

async function loadQuestions() {
  if (state.questionsReady &&
      Array.isArray(state.strategyQuestions) && state.strategyQuestions.length > 0 &&
      Array.isArray(state.valueQuestions) && state.valueQuestions.length > 0) return;
  if (_questionsLoadPromise) return _questionsLoadPromise;
  _questionsLoadPromise = (async () => {
    try {
      const res = await fetch(DATA_BASE + 'questions_v2.json');
      const data = await res.json();
      state.strategyQuestions = data.layers.strategies.questions;
      state.valueQuestions = data.layers.values.questions;
      state.questionsReady = true;
    } catch (e) {
      console.error('خطا در بارگذاری سوالات V2:', e);
      state.questionsReady = false;
    } finally {
      _questionsLoadPromise = null;
    }
  })();
  return _questionsLoadPromise;
}

// نگاشت واقعی برچسب شخصیتی هر سؤال-گزینه (S01..S25 × index 0..4)
// این فایل جایگزین فرضِ نادرستِ «موقعیت index معنی ثابت دارد» می‌شود —
// چون trait_map_v3.json نشان داده در سؤالات مختلف، همان index معنی متفاوتی دارد.
async function loadTraitMap() {
  if (state.traitMapReady && state.traitMap && Object.keys(state.traitMap).length > 0) return;
  if (_traitMapLoadPromise) return _traitMapLoadPromise;
  _traitMapLoadPromise = (async () => {
    const candidates = [DATA_BASE + 'trait_map_v3.json', './trait_map_v3.json'];
    for (const url of candidates) {
      try {
        const res = await fetch(url);
        if (!res.ok) continue;
        const data = await res.json();
        if (data && typeof data === 'object' && (data.S01 || data.s01)) {
          state.traitMap = data;
          state.traitMapReady = true;
          return;
        }
      } catch (e) {
        console.warn('trait_map try failed', url, e);
      }
    }
    console.error('نقشهٔ صفات بارگذاری نشد');
    state.traitMapReady = false;
    state.traitMap = {};
  })().finally(() => {
    _traitMapLoadPromise = null;
  });
  return _traitMapLoadPromise;
}

function ensureJourneyDataLoaded() {
  return Promise.all([loadQuestions(), loadMicroMotivesMap(), loadTraitMap()]);
}
window.ensureJourneyDataLoaded = ensureJourneyDataLoaded;

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

const DH_CANONICAL_PREV = {
  splash: null,
  realm: 'splash',
  subRealm: 'realm',
  narrowPath: 'subRealm',
  introSwipe: 'narrowPath',
  swipe: 'narrowPath',
  introStrategies: 'swipe',
  strategies: 'introStrategies',
  introValues: 'strategies',
  values: 'introValues',
  choice: 'values',
  results: 'choice'
};

function pruneOrphanRouteSelections() {
  if (typeof SUB_REALMS !== 'undefined' && SUB_REALMS) {
    const allowedSubs = new Set();
    (state.selectedRealms || []).forEach(rid => {
      (SUB_REALMS[rid] || []).forEach(s => { if (s && s.id) allowedSubs.add(s.id); });
    });
    state.selectedSubRealms = (state.selectedSubRealms || []).filter(sid => allowedSubs.has(sid));
  }
  if (typeof NARROW_PATHS !== 'undefined' && NARROW_PATHS) {
    const allowedPaths = new Set();
    (state.selectedSubRealms || []).forEach(sid => {
      (NARROW_PATHS[sid] || []).forEach(p => { if (p && p.id) allowedPaths.add(p.id); });
    });
    state.selectedNarrowPaths = (state.selectedNarrowPaths || []).filter(pid => allowedPaths.has(pid));
  }
}
window.pruneOrphanRouteSelections = pruneOrphanRouteSelections;

function dhRouteBreadcrumbHTML(currentStage) {
  const rCount = (state.selectedRealms || []).length;
  const sCount = (state.selectedSubRealms || []).length;
  const pCount = (state.selectedNarrowPaths || []).length;
  const parts = [];
  if (currentStage === 'subRealm') {
    parts.push(`<button type="button" class="dh-crumb-link" onclick="dhJumpToStage('realm')">${dhFaNum(rCount)} محله</button>`);
    parts.push(`<span class="dh-crumb-cur">گذرها</span>`);
  } else if (currentStage === 'narrowPath') {
    parts.push(`<button type="button" class="dh-crumb-link" onclick="dhJumpToStage('realm')">${dhFaNum(rCount)} محله</button>`);
    parts.push(`<button type="button" class="dh-crumb-link" onclick="dhJumpToStage('subRealm')">${dhFaNum(sCount)} گذر</button>`);
    parts.push(`<span class="dh-crumb-cur">مسیرهای باریک</span>`);
  } else if (currentStage === 'swipe' || currentStage === 'introSwipe') {
    if (rCount) parts.push(`<button type="button" class="dh-crumb-link" onclick="dhJumpToStage('realm')">${dhFaNum(rCount)} محله</button>`);
    if (sCount) parts.push(`<button type="button" class="dh-crumb-link" onclick="dhJumpToStage('subRealm')">${dhFaNum(sCount)} گذر</button>`);
    if (pCount) parts.push(`<button type="button" class="dh-crumb-link" onclick="dhJumpToStage('narrowPath')">${dhFaNum(pCount)} مسیر باریک</button>`);
    parts.push(`<span class="dh-crumb-cur">خرده‌انگیزه‌ها</span>`);
  }
  if (!parts.length) return '';
  return `<div class="dh-breadcrumb" aria-label="مسیر فعلی تو">${parts.join('<span class="dh-crumb-sep">‹</span>')}</div>`;
}

function dhApplyStageTransition(stage) {
  if (state.stage && state.stage !== stage) {
    if (state.history[state.history.length - 1] !== state.stage) {
      state.history.push(state.stage);
    }
    if (state.history.length > 40) state.history = state.history.slice(-40);
  }
  state.stage = stage;
  state.lastScrollY = 0;
  if (stage === 'strategies') syncStrategyCursor();
  if (stage === 'values') syncValueCursor();
  saveSession();
  render();
  scrollPageToTop();
}

function goTo(stage) {
  const needsNewCredit = Boolean(state.journeyFinished && stage !== 'choice' && stage !== 'results');
  const gateOk = dhEnsureServerQuotaGate({
    mode: needsNewCredit ? 'new' : 'resume',
    sessionId: needsNewCredit ? '' : state.sessionId,
    isFinished: Boolean(state.journeyFinished),
    targetStage: stage,
    onAuthorized: function (approvedId) {
      if (needsNewCredit) {
        fullResetState(true);
        try { localStorage.removeItem('dh_quota_charged_session_v1'); } catch (_) {}
      }
      if (approvedId) state.sessionId = String(approvedId);
      dhApplyStageTransition(stage);
    }
  });
  if (!gateOk) return;
  dhApplyStageTransition(stage);
}
window.goTo = goTo;

function dhReturnToFinishedResults() {
  if (state.majorsResult || state.branchesResult) {
    const kind = state.lastCounselKind === 'branches' && state.branchesResult ? 'branches' : 'majors';
    displayResults(kind === 'branches' ? state.branchesResult : state.majorsResult, kind);
    return;
  }
  dhGoHomeKeepPlace();
}
window.dhReturnToFinishedResults = dhReturnToFinishedResults;

function goBack() {
  if (state.journeyFinished) {
    dhReturnToFinishedResults();
    return;
  }
  const popped = [];
  let prev = null;
  while (state.history && state.history.length > 0) {
    const cand = state.history.pop();
    popped.push(cand);
    if (cand && cand !== state.stage) {
      prev = cand;
      break;
    }
  }
  if (!prev) {
    prev = Object.prototype.hasOwnProperty.call(DH_CANONICAL_PREV, state.stage)
      ? DH_CANONICAL_PREV[state.stage]
      : null;
  }
  if (!prev) {
    dhGoHomeKeepPlace();
    return;
  }
  const gateOk = dhEnsureServerQuotaGate({
    mode: 'resume',
    sessionId: state.sessionId,
    isFinished: Boolean(state.journeyFinished),
    targetStage: prev
  });
  if (!gateOk) {
    while (popped.length > 0) state.history.push(popped.pop());
    return;
  }
  // هیچ‌گاه انتخاب‌های گذر/مسیر باریک یا مکان سؤال کاربر را پاک نکن!
  if (prev === 'strategies') {
    const sTotal = (state.strategyQuestions && state.strategyQuestions.length) || 25;
    state.currentQuestion = Math.min(Math.max(0, state.currentQuestion || 0), Math.max(0, sTotal - 1));
  }
  if (prev === 'values') {
    const vTotal = (state.valueQuestions && state.valueQuestions.length) || 15;
    state.currentValueQuestion = Math.min(Math.max(0, state.currentValueQuestion || 0), Math.max(0, vTotal - 1));
  }
  state.stage = prev;
  state.lastScrollY = 0;
  saveSession();
  render();
  scrollPageToTop();
}

// ==================== RENDER ====================
function render(opts) {
  const preserveScroll = Boolean(opts && opts.preserveScroll);
  try {
    if (typeof dhHasCommercialRuntime === 'function' && dhHasCommercialRuntime()) {
      if (!window.DHAuth || typeof window.DHAuth.isLoggedIn !== 'function' || !window.DHAuth.isLoggedIn()) {
        window.__dhInJourney = false;
        if (window.DHShell && typeof window.DHShell.renderHome === 'function') {
          window.DHShell.renderHome();
        }
        if (window.DHCommercialUI && typeof window.DHCommercialUI.showAuth === 'function') {
          window.DHCommercialUI.showAuth('login');
        }
        return;
      }
      if (window.DHCommercialUI &&
          typeof window.DHCommercialUI.isActiveStageAuthorized === 'function' &&
          !window.DHCommercialUI.isActiveStageAuthorized(state.sessionId, Boolean(state.journeyFinished), state.stage)) {
        const pendingStage = state.stage || 'splash';
        const pendingId = state.sessionId || '';
        const wasFin = Boolean(state.journeyFinished && pendingStage !== 'choice' && pendingStage !== 'results');
        window.__dhInJourney = false;
        if (window.DHShell && typeof window.DHShell.renderHome === 'function') {
          window.DHShell.renderHome();
        }
        if (typeof window.DHCommercialUI.ensureCanEnterJourney === 'function') {
          window.DHCommercialUI.ensureCanEnterJourney({
            mode: wasFin ? 'new' : 'resume',
            sessionId: wasFin ? '' : pendingId,
            onAuthorized: function (approvedId) {
              if (wasFin) {
                fullResetState(true);
                try { localStorage.removeItem('dh_quota_charged_session_v1'); } catch (_) {}
              }
              if (approvedId) state.sessionId = approvedId;
              state.stage = pendingStage;
              window.__dhInJourney = true;
              saveSession();
              render({ preserveScroll: preserveScroll });
            }
          });
        }
        return;
      }
    }
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
      case 'results':
        if (state.branchesResult && state.lastCounselKind === 'branches') {
          displayResults(state.branchesResult, 'branches');
        } else if (state.majorsResult) {
          displayResults(state.majorsResult, 'majors');
        } else if (state.branchesResult) {
          displayResults(state.branchesResult, 'branches');
        } else {
          state.stage = 'choice';
          renderChoice();
        }
        break;
      default:
        console.warn('unknown stage', state.stage);
        state.stage = 'splash';
        renderSplash();
    }
    if (!preserveScroll) {
      scrollPageToTop();
      requestAnimationFrame(function () { scrollPageToTop(); });
      setTimeout(scrollPageToTop, 50);
    }
  } catch (e) {
    console.error('render failed', state.stage, e);
    const root = document.getElementById('app');
    if (root) {
      root.innerHTML = `<div class="card" style="margin:16px;text-align:right">
        <h2 style="color:#f5efe2">خطا در نمایش صفحه</h2>
        <p style="color:#b8b2a4">مرحلهٔ فعلی: <b>${escapeHtml(state.stage || '?')}</b></p>
        <p style="direction:ltr;text-align:left;color:#a9a497;font-size:.8rem">${escapeHtml(String(e && e.message ? e.message : e))}</p>
        <button class="btn btn-primary" style="width:100%;margin-top:10px" onclick="dhGoHomeKeepPlace()">بازگشت به صفحه اول</button>
      </div>`;
    }
  }
}
window.render = render;


// ==================== MANIFESTO (بدون تغییر) ====================
function renderManifesto() {
  app.innerHTML = `
    <div style="text-align:center;padding:20px;">
      <div style="font-size:3rem;margin-bottom:15px;">🐴</div>
      <h1 style="color:#f0c040;font-size:1.6rem;margin-bottom:10px;">اسب سیاه</h1>
      <p style="color:#c9b896;font-style:italic;margin-bottom:20px;">انتخاب مسیر با معیار خودت، نه فقط رتبه‌ات</p>
      <div class="card" style="text-align:right;">
        <p style="color:#c9b896;line-height:2.2;font-size:0.9rem;margin-bottom:15px;">
          <strong style="color:#f0c040;">«موفقیت از تقلید دیگران به دست نمی‌آید؛ از شناخت فردیت و ساختن مسیر شخصی می‌آید.»</strong>
          <br><span style="color:#888;font-size:0.8rem;">— تاد رز، کتاب «اسب سیاه» (پروژه هاروارد)</span>
        </p>

        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">مشکل از کجاست؟</p>
        <p style="color:#c9b896;line-height:2.2;font-size:0.9rem;margin-bottom:15px;">
          هر سال هزاران دانش‌آموز با این سؤال روبه‌رو می‌شوند: <strong>«چه رشته‌ای بخوانم؟»</strong><br>
          پاسخ‌های رایج معمولاً بر پایهٔ رتبه، پرستیژ یا بازار کار کلیشه‌ای است:
          «با این رتبه این رشته قبول می‌شوی»، «برو پزشکی چون اعتبار دارد»، «کامپیوتر بازار دارد».<br>
          این پاسخ‌ها <strong>فردیت تو را نادیده می‌گیرند</strong>؛
          نمی‌پرسند از چه چیزی واقعاً انرژی می‌گیری، چطور فکر می‌کنی، و چه چیزی به کار و زندگی‌ات معنا می‌دهد.
        </p>

        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">راه‌حل این سامانه</p>
        <p style="color:#c9b896;line-height:2.2;font-size:0.9rem;margin-bottom:15px;">
          بر اساس پژوهش <strong style="color:#f0c040;">Dark Horse</strong> در هاروارد و کتاب
          <strong style="color:#f0c040;">«اسب سیاه»</strong> نوشتهٔ تاد رز و اگی اوگاس،
          این سامانه به‌جای پرسیدن «چه نمره‌ای آوردی؟» می‌پرسد:<br>
          <strong style="color:#f0c040;">«از چه چیزی واقعاً انرژی می‌گیری؟»</strong>
        </p>

        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">سه لایهٔ شناخت</p>
        <p style="color:#c9b896;line-height:2.2;font-size:0.9rem;margin-bottom:5px;">
          🧩 <strong style="color:#f0c040;">خرده‌انگیزه‌ها</strong> — جرقه‌های لذت روزمره (پایهٔ اصلی انتخاب)<br>
          🧭 <strong style="color:#f0c040;">راهبردهای شخصی</strong> — سبک فکر و یادگیری (قابل رشد و یادگیری)<br>
          ⚖️ <strong style="color:#f0c040;">ارزش‌های بنیادین</strong> — آنچه به کارت معنا و رضایت عمیق می‌دهد
        </p>

        <p style="color:#d4af37;line-height:2.2;font-size:0.9rem;margin-top:15px;">
          <strong>این تست شخصیت نیست؛ یک سفر کوتاه برای کشف خودت است.</strong><br>
          نتیجه، پیشنهاد بر اساس فردیت توست — نه حکم نهایی بر اساس یک عدد.
        </p>
      </div>
      <button class="btn btn-primary" style="margin-top:20px;width:100%;" onclick="dhGoHomeKeepPlace()">بازگشت به صفحه اول</button>
    </div>`;
}

// ==================== GUIDE ====================
function renderGuide() {
  app.innerHTML = progressHTML('guide') + `
    <div style="text-align:right;padding:10px;">
      <h2 style="color:#f0c040;text-align:center;">🧭 راهنمای سفر اکتشافی</h2>
      <p style="color:#c9b896;line-height:2.2;text-align:center;">
        این یک تست شخصیت نیست؛
        <strong style="color:#f0c040;">سفری برای شناخت انگیزه‌ها، سبک فکر و ارزش‌های خودت</strong> است.
        با آرامش و صداقت پیش برو. پاسخ درست یا غلط وجود ندارد.
      </p>

      <div class="card" style="margin-top:15px;">
        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">مسیر سفر چگونه است؟</p>

        <p style="color:#c9b896;line-height:2.2;">
          <strong style="color:#f0c040;">۱) خرده‌انگیزه‌ها — پایهٔ اصلی</strong><br>
          وارد «شهر رؤیاها» می‌شوی: چند حوزه و داخل هر کدام، فعالیت‌های ملموس.
          از میان <strong>بیش از ۱۳۰۰ جرقه</strong>، آن‌هایی را که واقعاً به تو انرژی می‌دهند ❤️ بزن.
          پیشنهاد: حدود <strong>۲۰ تا ۸۰</strong> مورد را انتخاب کن تا تصویر دقیق‌تری از خودت ساخته شود.
        </p>

        <p style="color:#c9b896;line-height:2.2;">
          <strong style="color:#f0c040;">۲) راهبردهای شخصی — سبک تو</strong><br>
          حدود ۲۵ موقعیت کوتاه: چطور مسئله حل می‌کنی و یاد می‌گیری.
          راهبردها قابل یادگیری‌اند؛ اگر با رشته‌ای ناهمسو بود، یعنی
          <strong>هشدار برای رشد</strong>، نه رد شدن.
        </p>

        <p style="color:#c9b896;line-height:2.2;">
          <strong style="color:#f0c040;">۳) ارزش‌های بنیادین — معنای کار</strong><br>
          ۱۵ دوگانهٔ ساده (مثلاً عمق تأثیر یا گستره تأثیر).
          این بخش کمک می‌کند بفهمی رضایت بلندمدت برای تو از کجا می‌آید.
        </p>
      </div>

      <div class="card" style="margin-top:15px;">
        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">وزن‌ها در نتیجهٔ نهایی</p>
        <p style="color:#c9b896;line-height:2.2;">
          <strong style="color:#f0c040;">انتخاب رشتهٔ دانشگاهی</strong><br>
          خرده‌انگیزه ۵۵٪ | ارزش ۳۰٪ | راهبرد ۱۵٪
        </p>
        <p style="color:#c9b896;line-height:2.2;">
          <strong style="color:#f0c040;">هدایت شاخهٔ دبیرستان</strong><br>
          خرده‌انگیزه ۶۰٪ | راهبرد ۲۰٪ | ارزش ۲۰٪
        </p>
        <p style="color:#c9b896;line-height:2.2;margin-top:8px;">
          چرا؟ چون انگیزه و ارزش پایدارترند.
          راهبرد را می‌توان در طول زمان ساخت و تقویت کرد.
        </p>
      </div>

      <div class="card" style="margin-top:15px;">
        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">در پایان چه می‌بینی؟</p>
        <p style="color:#c9b896;line-height:2.2;">
          می‌توانی نتیجه را برای <strong>شاخهٔ دبیرستان</strong> یا
          <strong>رشته‌های دانشگاهی</strong> ببینی.
        </p>
        <p style="color:#d4af37;line-height:2.2;margin-top:10px;">
          اینجا قرار نیست کسی به‌جای تو تصمیم بگیرد.
          قرار است خودت کشف کنی از چه چیزی انرژی می‌گیری
          و مسیر را بر اساس انگیزه و فردیت خودت انتخاب کنی.
        </p>
      </div>

      <button class="btn" style="margin-top:14px;width:100%;" onclick="dhGoHomeKeepPlace()">بازگشت به صفحه اول</button>
    </div>`;
}

// ==================== 6-WORLD VISUAL ARCHITECTURE & LIVE MIRROR ====================
const DH_WORLD_THEMES = {
  healer: {
    id: 'healer',
    title: 'درمان و زندگی',
    short: 'درمان',
    color: '#34d399',
    soft: 'rgba(52, 211, 153, 0.13)',
    selected: 'rgba(52, 211, 153, 0.24)',
    border: 'rgba(52, 211, 153, 0.48)',
    borderMuted: 'rgba(52, 211, 153, 0.24)',
    glow: 'rgba(52, 211, 153, 0.26)',
    soloDesc: 'ذهن و حس تو به زنده‌نگه‌داشتن، التیام و بازگرداندن توان به موجودات زنده واکنش نشان می‌دهد.',
    svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;flex:0 0 18px;display:block;color:#34d399" aria-hidden="true"><path d="M12 21s-7-4.5-8.5-9.5A5.2 5.2 0 0 1 12 6a5.2 5.2 0 0 1 8.5 5.5C19 16.5 12 21 12 21z"/><path d="M6.5 12h3l1.6-2.8 2.2 5.4 1.6-2.6h2.6"/></svg>'
  },
  builder: {
    id: 'builder',
    title: 'ساختن و مهندسی',
    short: 'ساختن',
    color: '#38bdf8',
    soft: 'rgba(56, 189, 248, 0.13)',
    selected: 'rgba(56, 189, 248, 0.24)',
    border: 'rgba(56, 189, 248, 0.48)',
    borderMuted: 'rgba(56, 189, 248, 0.24)',
    glow: 'rgba(56, 189, 248, 0.26)',
    soloDesc: 'تو از تبدیل نقشهٔ ذهنی به سیستم، ابزار یا سازه‌ای که واقعاً کار کند انرژی می‌گیری.',
    svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;flex:0 0 18px;display:block;color:#38bdf8" aria-hidden="true"><path d="M12 2.5l8.5 4.9v9.2L12 21.5l-8.5-4.9V7.4L12 2.5z"/><path d="M12 21.5V12"/><path d="M20.5 7.4L12 12 3.5 7.4"/></svg>'
  },
  explorer: {
    id: 'explorer',
    title: 'کشف و دانش',
    short: 'کشف',
    color: '#a78bfa',
    soft: 'rgba(167, 139, 250, 0.14)',
    selected: 'rgba(167, 139, 250, 0.25)',
    border: 'rgba(167, 139, 250, 0.5)',
    borderMuted: 'rgba(167, 139, 250, 0.25)',
    glow: 'rgba(167, 139, 250, 0.28)',
    soloDesc: 'کنجکاوی تو به جواب‌های آماده قانع نمی‌شود؛ دنبال کشف الگو و قانون پنهان پدیده‌ها می‌گردی.',
    svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;flex:0 0 18px;display:block;color:#a78bfa" aria-hidden="true"><ellipse cx="12" cy="12" rx="9" ry="4" transform="rotate(32 12 12)"/><ellipse cx="12" cy="12" rx="9" ry="4" transform="rotate(-32 12 12)"/><circle cx="12" cy="12" r="2"/></svg>'
  },
  thinker: {
    id: 'thinker',
    title: 'اندیشه و جامعه',
    short: 'اندیشه',
    color: '#fbbf24',
    soft: 'rgba(251, 191, 36, 0.13)',
    selected: 'rgba(251, 191, 36, 0.24)',
    border: 'rgba(251, 191, 36, 0.5)',
    borderMuted: 'rgba(251, 191, 36, 0.25)',
    glow: 'rgba(251, 191, 36, 0.25)',
    soloDesc: 'در تحلیل رفتار آدم‌ها، استدلال، تصمیم‌گیری و هدایت جریان‌های انسانی می‌درخشی.',
    svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;flex:0 0 18px;display:block;color:#fbbf24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><polygon points="15.8 8.2 13.6 13.6 8.2 15.8 10.4 10.4 15.8 8.2"/></svg>'
  },
  artist: {
    id: 'artist',
    title: 'خلق و هنر',
    short: 'هنر',
    color: '#fb7185',
    soft: 'rgba(251, 113, 133, 0.13)',
    selected: 'rgba(251, 113, 133, 0.24)',
    border: 'rgba(251, 113, 133, 0.48)',
    borderMuted: 'rgba(251, 113, 133, 0.24)',
    glow: 'rgba(251, 113, 133, 0.26)',
    soloDesc: 'به حس‌ها و ایده‌های نادیدنی فرم، رنگ، تصویر، فضا و ریتم می‌بخشی.',
    svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fb7185" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;flex:0 0 18px;display:block;color:#fb7185" aria-hidden="true"><path d="M12 3l2.6 5.8L20.5 11l-5.2 4.1 1.5 6.4L12 18.2 7.2 21.5l1.5-6.4L3.5 11l5.9-2.2L12 3z"/></svg>'
  },
  speaker: {
    id: 'speaker',
    title: 'واژه و فرهنگ',
    short: 'واژه',
    color: '#2dd4bf',
    soft: 'rgba(45, 212, 191, 0.13)',
    selected: 'rgba(45, 212, 191, 0.24)',
    border: 'rgba(45, 212, 191, 0.48)',
    borderMuted: 'rgba(45, 212, 191, 0.24)',
    glow: 'rgba(45, 212, 191, 0.26)',
    soloDesc: 'قدرت واژه‌ها، روایت، یاددادن و ساختن پل میان زبان‌ها و فرهنگ‌ها به تو جان می‌دهد.',
    svg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;flex:0 0 18px;display:block;color:#2dd4bf" aria-hidden="true"><path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v7A2.5 2.5 0 0 1 17.5 16H10l-4.5 3.5V16H6.5A2.5 2.5 0 0 1 4 13.5v-7z"/><path d="M8.5 9.5h7"/><path d="M8.5 12.5h4.5"/></svg>'
  }
};
window.DH_WORLD_THEMES = DH_WORLD_THEMES;

const DH_SYNERGY_PAIRS = {
  'builder+healer':   { title: 'معمار سلامت و زیست‌فناوری', desc: 'ترکیب دقت مهندسی با دغدغهٔ جان و سلامت انسان؛ امضای رشته‌های پیشرو پزشکی‌ـ‌مهندسی.' },
  'explorer+healer':  { title: 'پژوهشگر مرزهای حیات', desc: 'کسی که هم درمان را می‌فهمد و هم تا کشف سازوکار سلولی و علمی بیماری جلو می‌رود.' },
  'healer+thinker':   { title: 'درمانگر ذهن و تصمیم', desc: 'پیوند شناخت روان و جامعه با التیام واقعی انسان‌ها در لحظه‌های حساس.' },
  'artist+healer':    { title: 'التیام‌بخش با حس و زیبایی', desc: 'ترکیب کمیاب ظرافت هنری با بازگرداندن آرامش، حرکت و کیفیت زندگی.' },
  'healer+speaker':   { title: 'همراه توان‌بخش و ارتباط‌گر', desc: 'قدرت ارتباط انسانی و کلام در خدمت درمان، آموزش سلامت و توان‌بخشی.' },
  'builder+explorer': { title: 'پیشگام علم و فناوری', desc: 'هم قانون پشت طبیعت را کشف می‌کنی و هم از دل آن سیستم و ابزار تازه می‌سازی.' },
  'builder+thinker':  { title: 'معمار سیستم و استراتژی', desc: 'پیوند ساختن فنی با مدیریت، اقتصاد و تصمیم‌گیری کلان؛ ترکیب کلاسیک کارآفرینان.' },
  'artist+builder':   { title: 'مهندسِ خلاق و طراح تجربه', desc: 'جایی که کد، سازه و صنعت با فرم، معماری و حس زیبایی‌شناسی گره می‌خورند.' },
  'builder+speaker':  { title: 'پل‌ساز فناوری و انسان', desc: 'تبدیل پیچیده‌ترین سیستم‌های فنی به زبانی قابل‌فهم و انسانی برای جهان.' },
  'explorer+thinker': { title: 'تحلیل‌گر الگوهای بزرگ', desc: 'ترکیب کنجکاوی علمی و داده‌کاوی با فهم عمیق جامعه، اقتصاد و تصمیم.' },
  'artist+explorer':  { title: 'کاوشگر فرم و شگفتی', desc: 'ذهنی که هم مثل دانشمند الگو می‌بیند و هم مثل هنرمند جهان تازه خلق می‌کند.' },
  'explorer+speaker': { title: 'راوی دانش و فرهنگ', desc: 'کشف ریشه‌های علمی و زبانی و روایت جذاب آن برای دیگران.' },
  'artist+thinker':   { title: 'کارگردان معنا و فرهنگ', desc: 'وقتی اندیشهٔ انتقادی و شناخت انسان در قالب هنر، سینما یا طراحی جان می‌گیرد.' },
  'speaker+thinker':  { title: 'صدای اثرگذار جامعه', desc: 'قدرت استدلال، اقناع، حقوق، آموزش و رهبری فکری با نیروی کلمات.' },
  'artist+speaker':   { title: 'خالق روایت، تصویر و صدا', desc: 'آمیختن زیبایی تصویر و موسیقی با جادوی داستان‌گویی و زبان.' }
};

function dhGetWorldTheme(realmId) {
  return DH_WORLD_THEMES[realmId] || DH_WORLD_THEMES.thinker;
}

function dhWorldStyleVars(realmId, delayIndex) {
  const t = dhGetWorldTheme(realmId);
  const d = typeof delayIndex === 'number' ? `;animation-delay:${Math.min(delayIndex * 32, 220)}ms` : '';
  return `--dh-world:${t.color};--dh-world-soft:${t.soft};--dh-world-selected:${t.selected};--dh-world-border:${t.border};--dh-world-border-muted:${t.borderMuted};--dh-world-glow:${t.glow}${d}`;
}

let __dhRouteIndexCache = null;
function dhGetRouteLookup() {
  if (__dhRouteIndexCache) return __dhRouteIndexCache;
  const subToRealm = {};
  const pathToMeta = {};
  const prefixToRealm = {};
  if (typeof SUB_REALMS !== 'undefined' && SUB_REALMS) {
    Object.keys(SUB_REALMS).forEach(rid => {
      (SUB_REALMS[rid] || []).forEach(s => {
        if (s && s.id) subToRealm[s.id] = rid;
      });
    });
  }
  if (typeof NARROW_PATHS !== 'undefined' && NARROW_PATHS) {
    Object.keys(NARROW_PATHS).forEach(sid => {
      const rid = subToRealm[sid] || 'thinker';
      (NARROW_PATHS[sid] || []).forEach(p => {
        if (!p || !p.id) return;
        pathToMeta[p.id] = { realmId: rid, subId: sid, path: p };
        (p.majorCodes || []).forEach(pref => {
          if (pref && !prefixToRealm[pref]) prefixToRealm[pref] = rid;
        });
      });
    });
  }
  __dhRouteIndexCache = { subToRealm, pathToMeta, prefixToRealm };
  return __dhRouteIndexCache;
}

function dhResolveMotiveWorldId(code) {
  if (!code) return 'thinker';
  const lookup = dhGetRouteLookup();
  const s = String(code);
  const dash = s.indexOf('-');
  if (dash > 0) {
    const exactPref = s.slice(0, dash + 1);
    if (lookup.prefixToRealm[exactPref]) return lookup.prefixToRealm[exactPref];
  }
  const prefs = Object.keys(lookup.prefixToRealm);
  for (let i = 0; i < prefs.length; i++) {
    if (s.startsWith(prefs[i])) return lookup.prefixToRealm[prefs[i]];
  }
  return (state.selectedRealms && state.selectedRealms[0]) || 'thinker';
}

function dhSynergyBannerHTML() {
  const sel = state.selectedRealms || [];
  if (!sel.length) return '';
  if (sel.length === 1) {
    const t = dhGetWorldTheme(sel[0]);
    return `<div class="dh-synergy-card" style="--dh-syn-a:${t.soft};--dh-syn-b:rgba(240,192,64,0.08)">
      <span class="dh-synergy-kicker">✦ قطب انتخابی تو · می‌توانی تا ۲ محلهٔ دیگر هم ترکیب کنی</span>
      <p class="dh-synergy-title">قلمرو ${escapeHtml(t.title)}</p>
      <p class="dh-synergy-desc">${escapeHtml(t.soloDesc)}</p>
    </div>`;
  }
  const sortedPair = sel.slice(0, 2).sort().join('+');
  const t1 = dhGetWorldTheme(sel[0]);
  const t2 = dhGetWorldTheme(sel[1]);
  if (sel.length === 2) {
    const syn = DH_SYNERGY_PAIRS[sortedPair] || {
      title: `${t1.short} × ${t2.short}`,
      desc: 'ترکیب دو دنیای متفاوت، مسیرهای میان‌رشته‌ای منحصربه‌فردی جلوی پایت می‌گذارد.'
    };
    return `<div class="dh-synergy-card" style="--dh-syn-a:${t1.selected};--dh-syn-b:${t2.selected}">
      <span class="dh-synergy-kicker">✦ هم‌افزایی زندهٔ انتخاب‌های تو (${escapeHtml(t1.short)} + ${escapeHtml(t2.short)})</span>
      <p class="dh-synergy-title">${escapeHtml(syn.title)}</p>
      <p class="dh-synergy-desc">${escapeHtml(syn.desc)}</p>
    </div>`;
  }
  const t3 = dhGetWorldTheme(sel[2]);
  return `<div class="dh-synergy-card" style="--dh-syn-a:${t1.selected};--dh-syn-b:${t3.selected}">
    <span class="dh-synergy-kicker">✦ ترکیب سه‌گانهٔ کامل (${escapeHtml(t1.short)} × ${escapeHtml(t2.short)} × ${escapeHtml(t3.short)})</span>
    <p class="dh-synergy-title">ذهن چندبعدی و میان‌رشته‌ای</p>
    <p class="dh-synergy-desc">هر سه دروازهٔ تو آمادهٔ کاوش‌اند؛ حالا بزن بریم ببینیم داخل گذرهای هرکدام چه خبر است.</p>
  </div>`;
}

function dhComputeWorldSparkMix() {
  const counts = {};
  const codes = state.likedCodes || [];
  codes.forEach(c => {
    const rid = dhResolveMotiveWorldId(c);
    counts[rid] = (counts[rid] || 0) + 1;
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([rid, count]) => ({
      realmId: rid,
      theme: dhGetWorldTheme(rid),
      count,
      pct: codes.length ? Math.round((count / codes.length) * 100) : 0
    }));
}

function renderSplash() {
  const hasSession = window.__dhHasSavedSession || !!localStorage.getItem('darkhorse_session_v2');
  const schemaNoticeHTML = state.valueSchemaResetNotice
    ? `<p data-dh-value-schema-reset="1" style="color:#f0c040;background:rgba(240,192,64,.10);border:1px solid rgba(240,192,64,.35);border-radius:12px;padding:10px 12px;margin-bottom:12px;font-size:0.86rem;line-height:1.9;">${escapeHtml(state.valueSchemaResetNotice)}</p>`
    : '';
  const orbsHTML = Object.keys(DH_WORLD_THEMES).map(rid => {
    const t = DH_WORLD_THEMES[rid];
    return `<span class="dh-world-orb" style="--dh-world:${t.color};--dh-world-border:${t.borderMuted};--dh-world-glow:${t.glow}">${t.svg}<span>${escapeHtml(t.title)}</span></span>`;
  }).join('');

  let actionButtonHTML = '';
  if (hasSession) {
    actionButtonHTML = `
      <div class="dh-stage-actions">
        <button type="button" class="btn btn-primary" onclick="dhResumeFromSplash()">ادامهٔ سفر دقیقاً از همان‌جا</button>
        <button type="button" class="btn" onclick="dhGoHomeKeepPlace()">بازگشت به صفحه اول</button>
      </div>`;
  } else {
    actionButtonHTML = `
      <div class="dh-stage-actions">
        <button type="button" class="btn btn-primary" onclick="startNewJourney()">ورود به ۶ محلهٔ شهر رؤیاها</button>
        <button type="button" class="btn" onclick="dhGoHomeKeepPlace()">بازگشت به صفحه اول</button>
      </div>`;
  }

  ensureUXStyles();
  app.innerHTML = progressHTML('splash') + `
    <div class="dh-gateway-hero">
      <div class="dh-gateway-kicker">✦ سفر تعاملی کشف فردیت · بدون نمره و کلیشه</div>
      <h1 style="color:#fff8eb;font-size:1.72rem;margin:4px 0 6px;font-weight:900;">به شهر رؤیاها خوش آمدی</h1>
      <p class="dh-dreamcity-invite">دروازه‌های شهر رؤیاها به روی تو باز است؛ به ۶ محلهٔ این شهر سر بزن و ببین در کدام فضا گذر زمان یادت می‌رود. اینجا آزمون درسی نیست — فقط دنبال حس و کنجکاوی واقعی خودت برو.</p>
      <div class="dh-world-orbs">${orbsHTML}</div>
    </div>
    <div class="card dh-surface-card" style="text-align:right;padding:18px 16px;">
      ${schemaNoticeHTML}
      <div class="dh-act-roadmap">
        <div class="dh-act-step" style="--dh-step-color:#38bdf8">
          <span class="dh-act-step-num">گام ۱ · نقشهٔ شهر</span>
          <span class="dh-act-step-title">محله‌ها، گذرها و کارگاه‌ها</span>
          <span class="dh-act-step-sub">فقط جاهایی که کنجکاوت می‌کنند</span>
        </div>
        <div class="dh-act-step" style="--dh-step-color:#34d399">
          <span class="dh-act-step-num">گام ۲ · دسته کارت زنده</span>
          <span class="dh-act-step-title">شکار حداقل ۲۰ جرقه</span>
          <span class="dh-act-step-sub">با کشیدن کارت به راست یا چپ</span>
        </div>
        <div class="dh-act-step" style="--dh-step-color:#a78bfa">
          <span class="dh-act-step-num">گام ۳ · ۵ فصل کوتاه</span>
          <span class="dh-act-step-title">۲۵ موقعیت واقعی</span>
          <span class="dh-act-step-sub">همراه با آینهٔ زندهٔ سبک فکر</span>
        </div>
        <div class="dh-act-step" style="--dh-step-color:#fbbf24">
          <span class="dh-act-step-num">گام ۴ · دوئل دوراهی</span>
          <span class="dh-act-step-title">۱۵ انتخاب روبه‌رو</span>
          <span class="dh-act-step-sub">کشف ارزش‌های ریشه‌ای تو</span>
        </div>
      </div>
      ${actionButtonHTML}
    </div>`;
}

function dhResumeFromSplash() {
  let data = window.__dhSavedSession;
  if (!data) {
    try { data = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null'); } catch (_) {}
  }
  const finished = Boolean(!data || data.journeyFinished || window.__dhJourneyFinished);
  const candidateId = !finished && data && data.sessionId ? String(data.sessionId) : (state && state.sessionId ? String(state.sessionId) : '');
  const gateOk = dhEnsureServerQuotaGate({
    mode: finished ? 'new' : 'resume',
    sessionId: finished ? '' : candidateId,
    isFinished: finished,
    onAuthorized: function (approvedId) {
      if (finished) {
        dhExecuteStartNewJourney(approvedId, true, '');
        return;
      }
      if (approvedId && data) data.sessionId = approvedId;
      dhResumeFromSplash();
    }
  });
  if (!gateOk) return;
  window.__dhInJourney = true;
  try { if (window.DHShell && typeof window.DHShell.setActiveTab === 'function') window.DHShell.setActiveTab('journey'); } catch (e0) {}
  // اگر کاربر قبلاً نتیجه را دیده، ادامه = شروع تمیز (بدون تیک‌های قبلی)
  if (finished) {
    fullResetState();
    state.stage = 'realm';
    saveSession();
    render();
    return;
  }
  try {
    const schemaVer = 'v2-canonical-poles-1';
    const resetMsg = 'به‌دلیل به‌روزرسانی علمی قطب‌های ارزش برای دقت بیشتر تحلیل، پاسخ‌های ناتمام بخش ارزش بازنشانی شد تا دوباره با مقیاس جدید پاسخ دهی.';
    if (data && typeof data === 'object' && !data.journeyFinished && data.valueSchemaVersion !== schemaVer) {
      const hasLegacyVals = Array.isArray(data.valueAnswers) &&
        data.valueAnswers.some(function (v) { return v !== undefined && v !== null && String(v).trim() !== ''; });
      const hasLegacyCur = Number(data.currentValueQuestion || 0) > 0;
      if (hasLegacyVals || hasLegacyCur) {
        data.valueAnswers = [];
        data.currentValueQuestion = 0;
        if (data.stage === 'values' || data.stage === 'choice') {
          data.stage = 'introValues';
        }
        state.valueSchemaResetNotice = resetMsg;
        try {
          if (typeof window !== 'undefined' && window) window.__dhValueSchemaResetNotice = resetMsg;
        } catch (_) {}
      }
      data.valueSchemaVersion = schemaVer;
    }
    state.sessionId = data.sessionId || null;
    state.selectedRealms = data.selectedRealms || [];
    state.selectedSubRealms = data.selectedSubRealms || [];
    state.selectedNarrowPaths = data.selectedNarrowPaths || [];
    state.likedCodes = data.likedCodes || [];
    state.likedCodesSet = new Set(state.likedCodes);
    state.strategyAnswers = data.strategyAnswers || [];
    state.valueAnswers = data.valueAnswers || [];
    state.currentQuestion = data.currentQuestion || 0;
    state.currentValueQuestion = data.currentValueQuestion || 0;
    state.history = data.history || [];
    state.swipeIndex = data.swipeIndex || 0;
    state.totalSwipes = data.totalSwipes || 0;
    state.swipeDeckCodes = Array.isArray(data.swipeDeckCodes) ? data.swipeDeckCodes : [];
    state.lastScrollY = Number(data.lastScrollY || 0);
    state.completedPaths = new Set(data.completedPaths || []);
    state.completedSubRealms = new Set(data.completedSubRealms || []);
    state.journeyFinished = false;
    state.stage = data.stage || 'realm';
    // choice و stages میانی را به realm برنگردان — کاربر باید قبل از نتایج همان‌جا بماند
    if (['manifesto', 'guide', 'splash'].indexOf(state.stage) >= 0) {
      state.stage = 'realm';
    }
    if (state.stage === 'results' && data.journeyFinished) {
      state.stage = 'realm';
    }
  } catch (e) {
    fullResetState(true);
    state.stage = 'realm';
  }
  saveSession();
  render();
}
window.dhResumeFromSplash = dhResumeFromSplash;


function renderRouteCardHTML(opts) {
  const isSelected = Boolean(opts.isSelected);
  const isComplete = Boolean(opts.isComplete);
  const realmId = opts.realmId || 'thinker';
  const theme = dhGetWorldTheme(realmId);
  const compactSigil = Boolean(opts.compactSigil);
  const boxPx = compactSigil ? 24 : 28;
  const extraCls = opts.extraCls ? ' ' + opts.extraCls : '';
  const stateCls = (isSelected ? ' selected' : '') + (isComplete ? ' disabled dh-path-done' : '');
  const action = isComplete ? '' : opts.onclickExpr;
  const keyAction = isComplete
    ? ''
    : `if(event.key==='Enter'||event.key===' '){event.preventDefault();${opts.onclickExpr};}`;
  const descText = isComplete && opts.doneDescription
    ? escapeHtml(opts.doneDescription)
    : escapeHtml(opts.description || '');
  const sigilStyle = `width:${boxPx}px;height:${boxPx}px;min-width:${boxPx}px;flex:0 0 ${boxPx}px;display:inline-flex;align-items:center;justify-content:center;border-radius:${compactSigil ? 7 : 9}px;background:${theme.soft};border:1px solid ${theme.border};color:${theme.color}`;
  const metaRight = `<span class="dh-world-tag" style="color:${theme.color}"><span class="dh-sigil-box${compactSigil ? ' dh-sigil-box--sm' : ''}" style="${sigilStyle}">${theme.svg}</span><span>${escapeHtml(opts.tagLabel || theme.title)}</span></span>`;
  const metaLeft = opts.orderNum
    ? `<span class="dh-order-badge">انتخاب ${dhFaNum(opts.orderNum)}</span>`
    : (opts.countLabel ? `<span class="dh-card-subcount">${escapeHtml(opts.countLabel)}</span>` : '');
  return `<div class="option dh-world-card dh-route-card${extraCls}${stateCls}" style="${dhWorldStyleVars(realmId, opts.index)}" role="button" tabindex="${isComplete ? '-1' : '0'}" aria-pressed="${isSelected ? 'true' : 'false'}" aria-disabled="${isComplete ? 'true' : 'false'}" onclick="${action}" onkeydown="${keyAction}">
      <div class="dh-card-meta-row">${metaRight}${metaLeft}</div>
      <div class="dh-route-card__head">
        <p class="dh-route-motto">${escapeHtml(opts.motto || '')}</p>
        <span class="dh-route-check" aria-hidden="true"></span>
      </div>
      <small class="dh-route-desc">${descText}</small>${isComplete ? '<span class="dh-route-badge">انجام شد</span>' : ''}</div>`;
}

function renderRealm() {
  try {
    ensureUXStyles();
    if (typeof REALMS === 'undefined' || !Array.isArray(REALMS) || REALMS.length === 0) {
      app.innerHTML = `<div class="card" style="margin:16px;text-align:right">
        <h2 style="color:#f5efe2">محله‌ها بارگذاری نشدند</h2>
        <p style="color:#b8b2a4">آرایهٔ REALMS از data.js خوانده نشد.</p>
        <button class="btn btn-primary" style="width:100%" onclick="location.reload()">بارگذاری مجدد</button>
      </div>`;
      return;
    }
    const maxSelect = Math.min(3, REALMS.length);
    const selCount = state.selectedRealms.length;
    let html = progressHTML('realm') + sparkChipHTML() + `<div class="dh-stage-head">
        <h2 class="dh-stage-title">محله‌های شهر رؤیاها</h2>
        <p class="dh-stage-hint dh-realm-invite">قدم به شهر رؤیاها بگذار؛ هر محله دنیای آدم‌هایی است که از یک جنس کار انرژی می‌گیرند. نجواهای هر محله را بخوان و ۱ تا ${dhFaNum(maxSelect)} محله‌ای را که دلت می‌خواهد واردشان شوی روشن کن.</p>
        <div class="dh-selection-pill ${selCount > 0 ? 'has-selection' : ''}">${dhFaNum(selCount)} از ${dhFaNum(maxSelect)} محله روشن شده</div>
      </div>
      <div class="grid dh-route-grid" id="realmGrid">`;
    REALMS.forEach((r, idx) => {
      const selIdx = state.selectedRealms.indexOf(r.id);
      const subLen = (typeof SUB_REALMS !== 'undefined' && SUB_REALMS[r.id]) ? SUB_REALMS[r.id].length : 0;
      html += renderRouteCardHTML({
        realmId: r.id,
        index: idx,
        orderNum: selIdx >= 0 ? selIdx + 1 : 0,
        countLabel: subLen ? `${dhFaNum(subLen)} گذر` : '',
        isSelected: selIdx >= 0,
        isComplete: false,
        onclickExpr: `toggleRealm('${r.id}')`,
        motto: r.motto,
        description: r.description
      });
    });
    html += `</div>` + dhSynergyBannerHTML() + `
      <div class="dh-stage-actions">
        <button type="button" class="btn btn-primary" onclick="if(state.selectedRealms.length>=1) goTo('subRealm'); else alert('حداقل یک محله را انتخاب کن');">ورود به گذرهای انتخابی ›</button>
        <button type="button" class="btn" onclick="goBack()">بازگشت</button>
      </div>`;
    app.innerHTML = html;
  } catch (e) {
    console.error('renderRealm', e);
    app.innerHTML = `<div class="card" style="margin:16px;text-align:right"><h2 style="color:#f5efe2">خطای نمایش محله‌ها</h2>
      <p style="direction:ltr;text-align:left;color:#a9a497;font-size:.8rem">${escapeHtml(String(e && e.message ? e.message : e))}</p>
      <button class="btn" style="width:100%" onclick="location.reload()">تلاش دوباره</button></div>`;
  }
}


function toggleRealm(id) {
  const idx = state.selectedRealms.indexOf(id);
  if (idx > -1) state.selectedRealms.splice(idx, 1);
  else if (state.selectedRealms.length < 3) state.selectedRealms.push(id);
  else dhShowJourneyToast('حداکثر ۳ محله می‌توانی هم‌زمان انتخاب کنی.');
  pruneOrphanRouteSelections();
  saveSession();
  renderRealm();
}
window.toggleRealm = toggleRealm;
window.startNewJourney = window.startNewJourney || startNewJourney;
window.dhResumeFromSplash = dhResumeFromSplash;
window.goBack = goBack;

function renderSubRealm() {
  ensureUXStyles();
  const groups = [];
  let totalSubs = 0;
  state.selectedRealms.forEach(realmId => {
    const arr = (typeof SUB_REALMS !== 'undefined' && SUB_REALMS[realmId]) ? SUB_REALMS[realmId] : [];
    if (arr.length) {
      groups.push({ realmId, list: arr });
      totalSubs += arr.length;
    }
  });
  const maxSelect = Math.min(3 * state.selectedRealms.length, totalSubs);
  const selCount = state.selectedSubRealms.length;
  let cardIdx = 0;
  let html = progressHTML('subRealm') + sparkChipHTML() + dhRouteBreadcrumbHTML('subRealm') + `<div class="dh-stage-head">
      <h2 class="dh-stage-title">گذرهای نیمه‌روشن هر محله</h2>
      <p class="dh-stage-hint">گذرها بر اساس محلهٔ رنگی‌شان دسته‌بندی شده‌اند — هر گذری که چشمت را گرفت روشن کن.</p>
      <div class="dh-selection-pill ${selCount > 0 ? 'has-selection' : ''}">${dhFaNum(selCount)} از ${dhFaNum(maxSelect)} گذر روشن شده</div>
    </div>
    <div id="subGrid">`;

  groups.forEach(g => {
    const theme = dhGetWorldTheme(g.realmId);
    const inGroupSelected = g.list.filter(s => state.selectedSubRealms.includes(s.id)).length;
    html += `<section class="dh-district-group" style="${dhWorldStyleVars(g.realmId)}">
      <div class="dh-district-head">
        <div class="dh-district-head-main">
          <span class="dh-sigil-box dh-sigil-box--sm" style="width:24px;height:24px;min-width:24px;flex:0 0 24px;display:inline-flex;align-items:center;justify-content:center;border-radius:7px;background:${theme.soft};border:1px solid ${theme.border};color:${theme.color}">${theme.svg}</span>
          <div>
            <span class="dh-district-head-title">گذرهای محلهٔ ${escapeHtml(theme.title)}</span>
            <span class="dh-district-head-sub">${dhFaNum(g.list.length)} گذر پیش رو</span>
          </div>
        </div>
        <span class="dh-district-count">${inGroupSelected > 0 ? dhFaNum(inGroupSelected) + ' انتخاب شده' : 'آمادهٔ انتخاب'}</span>
      </div>
      <div class="grid dh-route-grid">`;
    g.list.forEach(s => {
      const isComplete = state.completedSubRealms.has(s.id);
      const pathLen = (typeof NARROW_PATHS !== 'undefined' && NARROW_PATHS[s.id]) ? NARROW_PATHS[s.id].length : 0;
      html += renderRouteCardHTML({
        realmId: g.realmId,
        index: cardIdx++,
        compactSigil: true,
        tagLabel: theme.short,
        countLabel: pathLen ? `${dhFaNum(pathLen)} کارگاه` : '',
        isSelected: state.selectedSubRealms.includes(s.id),
        isComplete: isComplete,
        onclickExpr: `toggleSub('${s.id}', ${maxSelect})`,
        motto: s.motto,
        description: s.description
      });
    });
    html += `</div></section>`;
  });

  html += `</div>
    <div class="dh-stage-actions">
      <button type="button" class="btn btn-primary" onclick="if(state.selectedSubRealms.length>=1) goTo('narrowPath'); else alert('حداقل یک گذر را انتخاب کن');">ورود به کارگاه‌ها و مسیرهای باریک ›</button>
      <button type="button" class="btn" onclick="goBack()">‹ بازگشت به محله‌ها</button>
    </div>`;
  app.innerHTML = html;
}

function toggleSub(id, maxSelect) {
  const idx = state.selectedSubRealms.indexOf(id);
  if (idx > -1) state.selectedSubRealms.splice(idx, 1);
  else if (state.selectedSubRealms.length < maxSelect) state.selectedSubRealms.push(id);
  else dhShowJourneyToast(`در حال حاضر تا ${dhFaNum(maxSelect)} گذر می‌توانی انتخاب کنی.`);
  pruneOrphanRouteSelections();
  saveSession();
  renderSubRealm();
}
window.toggleSub = toggleSub;

function renderNarrowPath() {
  ensureUXStyles();
  if (!(state.completedPaths instanceof Set)) {
    state.completedPaths = new Set(state.completedPaths || []);
  }
  const lookup = dhGetRouteLookup();
  const subGroups = [];
  state.selectedSubRealms.forEach(subId => {
    const arr = (typeof NARROW_PATHS !== 'undefined' && NARROW_PATHS[subId]) ? NARROW_PATHS[subId] : [];
    if (!arr.length) return;
    const realmId = lookup.subToRealm[subId] || 'thinker';
    let subMotto = '';
    if (typeof SUB_REALMS !== 'undefined' && SUB_REALMS[realmId]) {
      const foundSub = SUB_REALMS[realmId].find(x => x.id === subId);
      if (foundSub) subMotto = foundSub.motto || '';
    }
    subGroups.push({ subId, realmId, subMotto, list: arr });
  });

  const selCount = state.selectedNarrowPaths.length;
  let cardIdx = 0;
  let html = progressHTML('narrowPath') + sparkChipHTML() + dhRouteBreadcrumbHTML('narrowPath') + `<div class="dh-stage-head">
      <h2 class="dh-stage-title">کارگاه‌ها و مسیرهای باریک</h2>
      <p class="dh-stage-hint">اینجا دیگر خبری از کلیشه نیست — هر کارگاهی که دوست داری دست‌به‌کارش شوی تیک بزن تا جرقه‌هایش باز شوند.</p>
      <div class="dh-selection-pill ${selCount > 0 ? 'has-selection' : ''}">${selCount > 0 ? dhFaNum(selCount) + ' مسیر آمادهٔ شکار جرقه' : 'حداقل ۱ مسیر انتخاب کن'}</div>
    </div>
    <div id="pathGrid">`;

  subGroups.forEach(g => {
    const theme = dhGetWorldTheme(g.realmId);
    const inGroupSel = g.list.filter(p => state.selectedNarrowPaths.includes(p.id)).length;
    html += `<section class="dh-district-group" style="${dhWorldStyleVars(g.realmId)}">
      <div class="dh-district-head">
        <div class="dh-district-head-main">
          <span class="dh-sigil-box dh-sigil-box--sm" style="width:24px;height:24px;min-width:24px;flex:0 0 24px;display:inline-flex;align-items:center;justify-content:center;border-radius:7px;background:${theme.soft};border:1px solid ${theme.border};color:${theme.color}">${theme.svg}</span>
          <div>
            <span class="dh-district-head-title">${escapeHtml(g.subMotto || theme.title)}</span>
            <span class="dh-district-head-sub">قلمرو ${escapeHtml(theme.title)} · ${dhFaNum(g.list.length)} مسیر تخصصی</span>
          </div>
        </div>
        <span class="dh-district-count">${inGroupSel > 0 ? dhFaNum(inGroupSel) + ' انتخاب شده' : ''}</span>
      </div>
      <div class="grid dh-route-grid">`;
    g.list.forEach(p => {
      const isComplete = state.completedPaths.has(p.id);
      const codeCount = (p.majorCodes || []).length;
      html += renderRouteCardHTML({
        realmId: g.realmId,
        index: cardIdx++,
        compactSigil: true,
        tagLabel: `کارگاه · ${theme.short}`,
        countLabel: codeCount ? `${dhFaNum(codeCount)} شاخهٔ تخصصی` : '',
        extraCls: 'dh-path-card',
        isSelected: state.selectedNarrowPaths.includes(p.id),
        isComplete: isComplete,
        onclickExpr: `togglePath('${p.id}')`,
        motto: p.motto,
        description: p.description,
        doneDescription: 'جرقه‌های این مسیر بررسی شد — می‌توانی مسیر دیگری هم انتخاب کنی.'
      });
    });
    html += `</div></section>`;
  });

  html += `</div>
    <div class="dh-stage-actions">
      <button type="button" class="btn btn-primary" onclick="if(state.selectedNarrowPaths.length>=1) goTo('introSwipe'); else alert('حداقل یک مسیر را انتخاب کن');">ورود به دسته کارت جرقه‌ها ›</button>
      <button type="button" class="btn" onclick="goBack()">‹ بازگشت به گذرها</button>
    </div>`;
  app.innerHTML = html;
}

function togglePath(id) {
  const idx = state.selectedNarrowPaths.indexOf(id);
  if (idx > -1) state.selectedNarrowPaths.splice(idx, 1);
  else state.selectedNarrowPaths.push(id);
  saveSession();
  renderNarrowPath();
}
window.togglePath = togglePath;

function dhWorldMixHTML() {
  const n = (state.likedCodes || []).length;
  if (n < 2) return '';
  const mix = dhComputeWorldSparkMix();
  if (!mix.length) return '';
  const segs = mix.map(item =>
    `<span class="dh-world-mix-seg" style="width:${Math.max(6, item.pct)}%;background:${item.theme.color}"></span>`
  ).join('');
  const legend = mix.slice(0, 3).map(item =>
    `<span><b style="color:${item.theme.color}">●</b> ${escapeHtml(item.theme.short)} ${dhFaNum(item.pct)}٪</span>`
  ).join('');
  return `<div class="dh-world-mix-card">
    <div style="display:flex;justify-content:space-between;align-items:center;font-size:.75rem;color:#b8b2a4;">
      <span>ترکیب زندهٔ جرقه‌های تو تا اینجا</span>
      <span style="color:#f5efe2;font-weight:800;">${dhFaNum(n)} جرقه</span>
    </div>
    <div class="dh-world-mix-bar">${segs}</div>
    <div class="dh-world-mix-legend">${legend}</div>
  </div>`;
}

function dhMilestoneBannerHTML() {
  const n = (state.likedCodes || []).length;
  const mix = n >= 5 ? dhComputeWorldSparkMix() : [];
  const topTitle = mix.length ? mix[0].theme.title : '';
  if (n === 5) {
    return `<div class="dh-milestone-banner">✦ ۵ جرقه روشن شد! ریتم عالیه — همین‌طور با حس درونی خودت پیش برو.</div>`;
  }
  if (n === 10) {
    return `<div class="dh-milestone-banner">✦ ۱۰ جرقه ثبت شد! بیشترین کشش تو تا اینجا به سمت «${escapeHtml(topTitle)}» بوده است.</div>`;
  }
  if (n === 15) {
    return `<div class="dh-milestone-banner">✦ فقط ۵ جرقهٔ دیگر تا باز شدن مرحلهٔ بعد باقی مانده!</div>`;
  }
  if (n === 20) {
    return `<div class="dh-milestone-banner">✦ مرز ۲۰ جرقه باز شد! می‌تونی همین الان بری سراغ چالش موقعیت‌ها یا باز هم جرقه جمع کنی.</div>`;
  }
  if (n === 30 || n === 40) {
    return `<div class="dh-milestone-banner">✦ ${dhFaNum(n)} جرقهٔ دقیق! نقشهٔ انرژی تو فوق‌العاده شفاف شده است.</div>`;
  }
  return '';
}

function renderIntroSwipe() {
  const selWorlds = (state.selectedRealms || []).map(rid => {
    const t = dhGetWorldTheme(rid);
    return `<span class="dh-world-orb" style="--dh-world:${t.color};--dh-world-border:${t.border};--dh-world-glow:${t.glow}">${t.svg}<span>${escapeHtml(t.title)}</span></span>`;
  }).join('');
  app.innerHTML = progressHTML('introSwipe') + sparkChipHTML() + dhRouteBreadcrumbHTML('introSwipe') + `
    <div class="dh-stage-head">
      <h2 class="dh-stage-title">لایهٔ اول: دسته کارت جرقه‌ها</h2>
      <p class="dh-stage-hint">کارت‌های فعالیت‌های واقعی بر اساس انتخاب‌های تو چیده شدند — سریع و شهودی تصمیم بگیر.</p>
      ${selWorlds ? `<div class="dh-world-orbs">${selWorlds}</div>` : ''}
    </div>
    <div class="card dh-surface-card" style="text-align:right;">
      <p style="color:#f5efe2;line-height:1.95;margin-bottom:8px;font-weight:600;">هر کارتی را که خواندنش حتی یک لحظه در دلت حس کنجکاوی یا ذوق روشن کرد، <strong style="color:#34d399;">به راست بکش</strong> (یا «جرقه زد» را بزن) و بقیه را رد کن.</p>
      <p style="color:#b8b2a4;font-size:0.84rem;line-height:1.85;margin-bottom:4px;">هدف: جمع‌کردن حداقل <strong style="color:#f0c040;">۲۰ جرقه</strong> واقعی از کارهایی که به تو انرژی می‌دهند.</p>
      <div class="dh-stage-actions">
        <button type="button" class="btn btn-primary" onclick="loadSwipeCards()">باز کردن دسته کارت‌ها ›</button>
        <button type="button" class="btn" onclick="goBack()">‹ بازگشت به مسیرهای باریک</button>
      </div>
    </div>`;
}

function buildOrderedDeckFromMotives(all, excludeAlreadyLiked) {
  const orderedPrefixes = [];
  (state.selectedNarrowPaths || []).forEach(pathId => {
    const path = findNarrowPath(pathId);
    (path && path.majorCodes ? path.majorCodes : []).forEach(prefix => {
      if (prefix && orderedPrefixes.indexOf(prefix) === -1) orderedPrefixes.push(prefix);
    });
  });
  const filtered = (all || []).filter(m =>
    m && m.code &&
    orderedPrefixes.some(prefix => m.code.startsWith(prefix)) &&
    (!excludeAlreadyLiked || !state.likedCodesSet.has(m.code))
  );
  filtered.sort((a, b) => {
    const ia = orderedPrefixes.findIndex(p => a.code && a.code.startsWith(p));
    const ib = orderedPrefixes.findIndex(p => b.code && b.code.startsWith(p));
    const pa = ia < 0 ? 999 : ia;
    const pb = ib < 0 ? 999 : ib;
    if (pa !== pb) return pa - pb;
    return String(a.code || '').localeCompare(String(b.code || ''), 'en', { numeric: true });
  });
  return filtered;
}

let __dhHydratingDeck = false;
async function ensureSwipeDeckHydrated(rerenderWhenReady) {
  if (Array.isArray(state.swipeCards) && state.swipeCards.length > 0) return true;
  if (__dhHydratingDeck) return false;
  __dhHydratingDeck = true;
  try {
    let all = state.cachedMotives;
    if (!all) {
      const res = await fetch(DATA_BASE + 'micro_motives.json?v=motives-1393-v1');
      all = await res.json();
      state.cachedMotives = all;
      if (Array.isArray(all)) {
        all.forEach(m => { if (m && m.code) state.microMotivesMap[m.code] = m.description_fa; });
        state.motivesReady = true;
      }
    }
    if (Array.isArray(state.swipeDeckCodes) && state.swipeDeckCodes.length > 0) {
      const byCode = {};
      all.forEach(m => { if (m && m.code) byCode[m.code] = m; });
      const restored = state.swipeDeckCodes.map(c => byCode[c]).filter(Boolean);
      if (restored.length > 0) {
        state.swipeCards = restored;
        state.totalSwipes = restored.length;
        state.swipeIndex = Math.min(Math.max(0, state.swipeIndex || 0), restored.length);
        saveSession();
        if (rerenderWhenReady && state.stage === 'swipe') renderSwipe();
        return true;
      }
    }
    const built = buildOrderedDeckFromMotives(all, false);
    if (built.length > 0) {
      state.swipeCards = built;
      state.totalSwipes = built.length;
      state.swipeIndex = Math.min(Math.max(0, state.swipeIndex || 0), built.length);
      saveSession();
      if (rerenderWhenReady && state.stage === 'swipe') renderSwipe();
      return true;
    }
    return false;
  } catch (e) {
    console.warn('ensureSwipeDeckHydrated failed', e);
    return false;
  } finally {
    __dhHydratingDeck = false;
  }
}

async function loadSwipeCards() {
  const majorCodes = [];
  state.selectedNarrowPaths.forEach(pathId => {
    const path = findNarrowPath(pathId);
    if (path?.majorCodes) majorCodes.push(...path.majorCodes);
  });
  if (majorCodes.length === 0) { alert('هیچ جرقه‌ای در این مسیر یافت نشد.'); goBack(); return; }
  try {
    let all;
    if (state.cachedMotives) {
      all = state.cachedMotives;
    } else {
      const res = await fetch(DATA_BASE + 'micro_motives.json?v=motives-1393-v1');
      all = await res.json();
      state.cachedMotives = all;
      if (Array.isArray(all)) {
        all.forEach(m => { if (m && m.code) state.microMotivesMap[m.code] = m.description_fa; });
        state.motivesReady = true;
      }
    }
    let deck = buildOrderedDeckFromMotives(all, true);
    if (deck.length === 0) {
      deck = buildOrderedDeckFromMotives(all, false);
    }
    state.swipeCards = deck;
    state.swipeDeckCodes = deck.map(c => c.code);
    state.swipeIndex = 0;
    state.totalSwipes = state.swipeCards.length;
    goTo('swipe');
  } catch (e) { alert('خطا در بارگذاری جرقه‌ها.'); }
}

function dhLikedSparksDrawerHTML() {
  const codes = state.likedCodes || [];
  if (!codes.length) return '';
  const items = codes.slice().reverse().map(code => {
    const txt = (state.microMotivesMap && state.microMotivesMap[code]) || code;
    return `<div class="dh-liked-row">
      <span>${escapeHtml(txt)}</span>
      <button type="button" class="dh-liked-rm" onclick="removeLikedSpark('${escapeHtml(code)}')" title="حذف این جرقه">حذف</button>
    </div>`;
  }).join('');
  return `<details class="dh-liked-drawer" id="dh-liked-drawer">
    <summary>مشاهده و مدیریت جرقه‌های انتخاب‌شده (${dhFaNum(codes.length)})</summary>
    <div class="dh-liked-list">${items}</div>
  </details>`;
}

function removeLikedSpark(code) {
  if (!code) return;
  state.likedCodes = (state.likedCodes || []).filter(c => c !== code);
  state.likedCodesSet.delete(code);
  saveSession();
  const existing = document.getElementById('dh-swipe-card');
  if (existing) existing.remove();
  renderSwipe();
}
window.removeLikedSpark = removeLikedSpark;

function findNarrowPath(id) {
  for (const subId in NARROW_PATHS) {
    const pathArray = NARROW_PATHS[subId];
    if (Array.isArray(pathArray)) {
      const found = pathArray.find(p => p.id === id);
      if (found) return found;
    }
  }
  return null;
}

function updateCompletionStatus() {
  // مسیرهایی که جرقه‌شان تمام شده، خاموش شوند
  if (!(state.completedPaths instanceof Set)) {
    state.completedPaths = new Set(state.completedPaths || []);
  }
  if (!(state.completedSubRealms instanceof Set)) {
    state.completedSubRealms = new Set(state.completedSubRealms || []);
  }
  const deckDone = state.swipeCards.length > 0 && state.swipeIndex >= state.swipeCards.length;
  if (deckDone) {
    (state.selectedNarrowPaths || []).forEach(pathId => {
      state.completedPaths.add(pathId);
    });
  }
  (state.selectedSubRealms || []).forEach(subId => {
    const allPaths = NARROW_PATHS[subId] || [];
    if (allPaths.length > 0 && allPaths.every(p => state.completedPaths.has(p.id))) {
      state.completedSubRealms.add(subId);
    }
  });
  try { saveSession(); } catch (e) {}
}

/** وقتی کاربر وارد لایهٔ بعد می‌شود، مسیرهای انتخاب‌شده را کامل‌شده علامت بزن */
function markSelectedPathsCompleted() {
  (state.selectedNarrowPaths || []).forEach(id => state.completedPaths.add(id));
  (state.selectedSubRealms || []).forEach(subId => {
    const allPaths = NARROW_PATHS[subId] || [];
    if (allPaths.length > 0 && allPaths.every(p => state.completedPaths.has(p.id))) {
      state.completedSubRealms.add(subId);
    }
  });
  saveSession();
}

function renderSwipe() {
  if (state.likedCodes.length >= 80) {
    markSelectedPathsCompleted();
    updateCompletionStatus();
    setTimeout(() => goTo('introStrategies'), 450);
    app.innerHTML = progressHTML('swipe') + `<div class="dh-hero dh-celebrate"><div class="dh-stars">✦ · ✦ · ✦</div><h2 class="dh-stage-title">سقف انتخاب جرقه‌ها تکمیل شد</h2><p class="dh-stage-hint">به‌اندازهٔ کافی از علاقه‌های واقعی خودت نشانه ثبت کردی.</p></div><div class="card dh-surface-card"><p style="text-align:center;color:#d6d1c4">در حال ورود به لایهٔ راهبردها...</p></div>`;
    return;
  }
  if (!state.swipeCards || state.swipeCards.length === 0) {
    if ((state.swipeDeckCodes && state.swipeDeckCodes.length > 0) || (state.selectedNarrowPaths && state.selectedNarrowPaths.length > 0)) {
      app.innerHTML = progressHTML('swipe') + loadingHTML('در حال بازیابی کارت‌های خرده‌انگیزه دقیقاً از همان نقطه...');
      ensureSwipeDeckHydrated(true);
      return;
    }
  }
  if (state.swipeIndex >= state.swipeCards.length) {
    updateCompletionStatus();
    if (state.likedCodes.length < 20) {
      const remaining = 20 - state.likedCodes.length;
      app.innerHTML = progressHTML('swipe') + sparkChipHTML() + dhRouteBreadcrumbHTML('swipe') + `
        <div class="dh-stage-head">
          <h2 class="dh-stage-title">کارت‌های این مسیر بررسی شد</h2>
          <p class="dh-stage-hint">تا اینجای کار ${dhFaNum(state.likedCodes.length)} جرقه انتخاب کرده‌ای؛ برای دقت تحلیل، ${dhFaNum(remaining)} جرقهٔ دیگر لازم داری.</p>
        </div>
        <div class="card dh-surface-card">
          <p style="color:#d6d1c4;line-height:1.9;">کافی است یک مسیر باریک، گذر یا محلهٔ دیگر هم ببینی تا به حداقل ۲۰ جرقه برسی.</p>
          <div class="dh-stage-actions">
            <button type="button" class="btn btn-primary" onclick="dhJumpToStage('narrowPath')">انتخاب مسیر باریک دیگر</button>
            <button type="button" class="btn" onclick="dhJumpToStage('subRealm')">انتخاب گذر جدید</button>
            ${state.swipeCards.length > 0 ? `<button type="button" class="btn" onclick="previousCard()">بازگشت به کارت قبل</button>` : ''}
          </div>
          ${dhLikedSparksDrawerHTML()}
        </div>`;
      return;
    }
    app.innerHTML = progressHTML('swipe') + sparkChipHTML() + dhRouteBreadcrumbHTML('swipe') + `
      <div class="dh-stage-head">
        <h2 class="dh-stage-title">آمادهٔ ورود به لایهٔ راهبردها</h2>
        <p class="dh-stage-hint">${dhFaNum(state.likedCodes.length)} جرقه ثبت شده است. می‌توانی همین حالا وارد سؤالات راهبرد شوی یا مسیرهای بیشتری ببینی.</p>
      </div>
      <div class="card dh-surface-card">
        <div class="dh-stage-actions">
          <button type="button" class="btn btn-primary" onclick="finishSwipe()">ورود به سؤالات راهبرد</button>
          <button type="button" class="btn" onclick="dhJumpToStage('narrowPath')">مشاهدهٔ مسیرهای باریک دیگر</button>
          ${state.swipeCards.length > 0 ? `<button type="button" class="btn" onclick="previousCard()">مرور کارت قبل</button>` : ''}
        </div>
        ${dhLikedSparksDrawerHTML()}
      </div>`;
    return;
  }

  const card = state.swipeCards[state.swipeIndex];
  const deckLen = state.swipeCards.length;
  const progress = deckLen > 0 ? ((state.swipeIndex + 1) / deckLen) * 100 : 0;
  const alreadyLiked = Boolean(card && card.code && state.likedCodesSet.has(card.code));
  const cardWorldId = dhResolveMotiveWorldId(card && card.code);
  const cardTheme = dhGetWorldTheme(cardWorldId);

  if (document.getElementById('dh-swipe-card') && app.innerHTML.indexOf('id="dh-swipe-card"') !== -1 && state.stage === 'swipe') {
    updateSwipeCardInPlace();
    return;
  }

  app.innerHTML = progressHTML('swipe') + sparkChipHTML() + dhRouteBreadcrumbHTML('swipe') + `
    <div id="dh-milestone-host">${dhMilestoneBannerHTML()}</div>
    <div id="dh-world-mix-host">${dhWorldMixHTML()}</div>
    <div class="dh-stage-head" style="margin-bottom:6px;">
      <h2 class="dh-stage-title">شکار خرده‌انگیزه‌ها</h2>
      <p class="dh-stage-hint" id="dh-swipe-pos-label">کارت ${dhFaNum(state.swipeIndex + 1)} از ${dhFaNum(deckLen)} در این دسته</p>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="dh-swipe-progress-fill" style="width:${progress}%"></div></div>
    <div class="dh-gesture-hint" aria-hidden="true">
      <span style="color:#34d399;">→ بکش به راست: این منم!</span>
      <span style="color:#b8b2a4;">← بکش به چپ: رد کردن</span>
    </div>
    <div class="dh-swipe-stage" id="dh-swipe-stage">
      ${state.swipeIndex + 2 < deckLen ? '<div class="dh-swipe-stack-back dh-swipe-stack-back--2" aria-hidden="true"></div>' : ''}
      ${state.swipeIndex + 1 < deckLen ? '<div class="dh-swipe-stack-back dh-swipe-stack-back--1" aria-hidden="true"></div>' : ''}
      <div class="swipe-card dh-surface-card dh-deal-anim" id="dh-swipe-card" style="min-height:256px;${dhWorldStyleVars(cardWorldId)}">
        <div class="dh-swipe-stamp dh-swipe-stamp--like" aria-hidden="true">✦ این منم!</div>
        <div class="dh-swipe-stamp dh-swipe-stamp--skip" aria-hidden="true">فعلاً نه</div>
        <div id="dh-swipe-world-badge"><span class="dh-swipe-world-pill">${cardTheme.svg}<span>${escapeHtml(cardTheme.title)}</span></span></div>
        <div id="dh-swipe-picked-badge" style="min-height:22px;margin-bottom:4px;">${alreadyLiked ? '<span class="dh-picked-pill">✓ در فهرست جرقه‌های تو ثبت شده</span>' : ''}</div>
        <p id="dh-swipe-text" style="font-size:1.12rem;line-height:2.05;color:#fff8eb;min-height:5.2em;margin:0 0 18px 0;font-weight:700;">${escapeHtml(card.description_fa || '')}</p>
        <div id="dh-spark-actions" class="dh-spark-action-row">
          <button type="button" class="btn btn-heart" id="dh-btn-heart"
            style="width:100%;touch-action:manipulation;"
            onclick="likeCard(true, this)">✦ جرقه زد!</button>
          <button type="button" class="btn btn-skip" id="dh-btn-skip"
            style="width:100%;touch-action:manipulation;"
            onclick="likeCard(false, this)">جذبم نکرد</button>
        </div>
        <div id="dh-prev-wrap" style="margin-top:10px;width:100%;"></div>
        <div id="dh-spark-need" style="margin-top:14px;padding-top:12px;width:100%;border-top:1px solid rgba(255,255,255,.08);"></div>
      </div>
    </div>
    <div id="dh-liked-drawer-host">${dhLikedSparksDrawerHTML()}</div>`;
  updateSwipeChrome();
}

function updateSwipeChrome() {
  const n = state.likedCodes.length;
  const deckLen = (state.swipeCards && state.swipeCards.length) || state.totalSwipes || 0;
  const curCard = state.swipeCards && state.swipeCards[state.swipeIndex];
  const progress = deckLen > 0 ? ((state.swipeIndex + 1) / deckLen) * 100 : 0;

  const posEl = document.getElementById('dh-swipe-pos-label');
  if (posEl && deckLen > 0) {
    posEl.textContent = `کارت ${dhFaNum(state.swipeIndex + 1)} از ${dhFaNum(deckLen)} در این دسته`;
  }
  const worldEl = document.getElementById('dh-swipe-world-badge');
  const cardEl = document.getElementById('dh-swipe-card');
  if (curCard) {
    const wid = dhResolveMotiveWorldId(curCard.code);
    const wTheme = dhGetWorldTheme(wid);
    if (worldEl) {
      worldEl.innerHTML = `<span class="dh-swipe-world-pill">${wTheme.svg}<span>${escapeHtml(wTheme.title)}</span></span>`;
    }
    if (cardEl && cardEl.style && typeof cardEl.style.setProperty === 'function') {
      cardEl.style.setProperty('--dh-world', wTheme.color);
      cardEl.style.setProperty('--dh-world-soft', wTheme.soft);
      cardEl.style.setProperty('--dh-world-border', wTheme.border);
      cardEl.style.setProperty('--dh-world-glow', wTheme.glow);
    }
  }
  const pickedEl = document.getElementById('dh-swipe-picked-badge');
  if (pickedEl) {
    pickedEl.innerHTML = (curCard && curCard.code && state.likedCodesSet.has(curCard.code))
      ? '<span class="dh-picked-pill">✓ در فهرست جرقه‌های تو ثبت شده</span>'
      : '';
  }
  const mixHost = document.getElementById('dh-world-mix-host');
  if (mixHost) mixHost.innerHTML = dhWorldMixHTML();
  const mileHost = document.getElementById('dh-milestone-host');
  if (mileHost) mileHost.innerHTML = dhMilestoneBannerHTML();

  const fill = document.getElementById('dh-swipe-progress-fill');
  if (fill) fill.style.width = progress + '%';

  const chipEl = document.querySelector('#app .dh-spark-chip');
  if (chipEl) {
    chipEl.outerHTML = sparkChipHTML();
  }
  const headerEl = document.querySelector('#app .dh-progress-wrap');
  if (headerEl) {
    headerEl.outerHTML = progressHTML('swipe');
  }
  const drawerHost = document.getElementById('dh-liked-drawer-host');
  if (drawerHost) {
    const wasOpen = Boolean(document.getElementById('dh-liked-drawer')?.open);
    drawerHost.innerHTML = dhLikedSparksDrawerHTML();
    if (wasOpen && document.getElementById('dh-liked-drawer')) {
      document.getElementById('dh-liked-drawer').open = true;
    }
  }

  const prevWrap = document.getElementById('dh-prev-wrap');
  if (prevWrap) {
    prevWrap.innerHTML = `<div style="display:flex;gap:8px;flex-wrap:wrap;">
      ${state.swipeIndex > 0 ? `<button type="button" class="btn" style="flex:1;min-width:125px;margin:0;" onclick="previousCard()">‹ کارت قبلی</button>` : ''}
      <button type="button" class="btn" style="flex:1;min-width:140px;margin:0;" onclick="dhJumpToStage('narrowPath')">مسیر باریک جدید</button>
    </div>`;
  }

  const need = document.getElementById('dh-spark-need');
  if (need) {
    if (n >= 20) {
      need.innerHTML = `<p style="color:#d6d1c4;font-size:.86rem;margin-bottom:8px;">مرز ۲۰ جرقه باز شده است — هر زمان خواستی وارد مرحلهٔ بعد شو.</p>
        <button type="button" class="btn btn-primary" style="width:100%;" onclick="finishSwipe()">ادامه به چالش موقعیت‌ها (${dhFaNum(n)} جرقه) ›</button>`;
    } else {
      need.innerHTML = `<p style="color:#b8b2a4;font-size:.84rem;margin:0;">تا باز شدن مرحلهٔ بعد، <strong style="color:#f0c040;">${dhFaNum(20 - n)}</strong> جرقهٔ دیگر لازم داری.</p>`;
    }
  }
}

function updateSwipeCardInPlace() {
  const card = state.swipeCards[state.swipeIndex];
  const textEl = document.getElementById('dh-swipe-text');
  const box = document.getElementById('dh-swipe-card');
  if (!card || !textEl) {
    const tmp = document.getElementById('dh-swipe-card');
    if (tmp) tmp.remove();
    renderSwipe();
    return;
  }
  textEl.textContent = card.description_fa || card.description || '';
  if (box) {
    box.classList.remove('dh-deal-anim');
    void box.offsetWidth;
    box.classList.add('dh-deal-anim');
  }
  updateSwipeChrome();
}

function likeCard(liked, btnEl) {
  if (state.swipeIndex >= state.swipeCards.length) return;
  try {
    if (navigator && typeof navigator.vibrate === 'function') navigator.vibrate(liked ? 12 : 7);
  } catch (_) {}

  const c = state.swipeCards[state.swipeIndex];
  if (liked && state.likedCodes.length < 80) {
    if (c && c.code && !state.likedCodesSet.has(c.code)) {
      state.likedCodes.push(c.code);
      state.likedCodesSet.add(c.code);
    }
  } else if (!liked && c && c.code && state.likedCodesSet.has(c.code)) {
    state.likedCodes = state.likedCodes.filter(code => code !== c.code);
    state.likedCodesSet.delete(c.code);
  }
  state.swipeIndex++;
  saveSession();

  if (state.swipeIndex >= state.swipeCards.length || state.likedCodes.length >= 80) {
    const existing = document.getElementById('dh-swipe-card');
    if (existing) existing.remove();
    renderSwipe();
    return;
  }
  updateSwipeCardInPlace();
}

function previousCard() {
  if (state.swipeIndex > 0) {
    state.swipeIndex--;
    saveSession();
    if (document.getElementById('dh-swipe-card')) updateSwipeCardInPlace();
    else renderSwipe();
  }
}

function finishSwipe() {
  markSelectedPathsCompleted();
  updateCompletionStatus();
  // فقط اگر هنوز وارد سوالات نشده، از صفر شروع کن
  const answeredS = (state.strategyAnswers || []).filter(a => a !== undefined && a !== null).length;
  if (answeredS === 0) {
    state.currentQuestion = 0;
    state.strategyAnswers = [];
  }
  const answeredV = (state.valueAnswers || []).filter(a => a !== undefined && a !== null).length;
  if (answeredV === 0) {
    state.currentValueQuestion = 0;
    state.valueAnswers = [];
  }
  goTo('introStrategies');
}

// ==================== STRATEGIES ====================
function dhQuestionJumperHTML(total, answersArr, currentIdx, clickFnName) {
  let pills = '';
  for (let i = 0; i < total; i++) {
    const isAns = answersArr[i] !== undefined && answersArr[i] !== null && String(answersArr[i]).trim() !== '';
    const isCur = i === currentIdx;
    const cls = ['dh-q-dot', isAns ? 'is-answered' : '', isCur ? 'is-current' : ''].filter(Boolean).join(' ');
    pills += `<button type="button" class="${cls}" onclick="${clickFnName}(${i})" aria-label="سؤال ${i + 1}">${dhFaNum(i + 1)}</button>`;
  }
  return `<div class="dh-q-jumper-wrap">
    <div class="dh-q-jumper-head">
      <span>پرش سریع بین سؤالات</span>
      <span>${dhFaNum(dhAnsweredCount(answersArr))} از ${dhFaNum(total)} پاسخ داده شده</span>
    </div>
    <div class="dh-q-jumper" role="group" aria-label="شماره سؤالات">${pills}</div>
  </div>`;
}

function jumpStrategyQ(idx) {
  const total = (state.strategyQuestions && state.strategyQuestions.length) || 0;
  if (idx < 0 || idx >= total) return;
  state.stage = 'strategies';
  state.currentQuestion = idx;
  saveSession();
  render();
}
window.jumpStrategyQ = jumpStrategyQ;

function nextStrategyStep() {
  const total = (state.strategyQuestions && state.strategyQuestions.length) || 0;
  if (state.currentQuestion < total - 1) {
    state.currentQuestion++;
    saveSession();
    render();
  }
}
window.nextStrategyStep = nextStrategyStep;

function renderIntroStrategies() {
  const answered = dhAnsweredCount(state.strategyAnswers);
  const total = (state.strategyQuestions && state.strategyQuestions.length) || 25;
  const canResume = answered > 0 && answered < total;
  const allDone = answered >= total;
  const startLabel = allDone
    ? 'مرور پاسخ‌ها یا ادامه به ارزش‌ها'
    : (canResume ? `ادامه از سؤال ${dhFaNum(answered + 1)} از ${dhFaNum(total)}` : 'شروع سؤالات راهبرد');
  const resumeHint = answered > 0
    ? `<p style="color:#f0c040;background:rgba(240,192,64,.08);border:1px solid rgba(240,192,64,.25);border-radius:12px;padding:9px 12px;text-align:center;margin-top:10px;font-size:.86rem;">✓ ${dhFaNum(answered)} از ${dhFaNum(total)} پاسخ ذخیره شده است — در هر لحظه می‌توانی هر سؤال را ویرایش کنی.</p>`
    : '';
  app.innerHTML = progressHTML('introStrategies') + sparkChipHTML() + `
    <div class="dh-stage-head">
      <h2 class="dh-stage-title">لایهٔ دوم: راهبردهای فردی</h2>
      <p class="dh-stage-hint">اینجا می‌بینی در موقعیت‌های واقعی چطور فکر می‌کنی، تصمیم می‌گیری و جلو می‌روی.</p>
    </div>
    <div class="card dh-surface-card">
      <p style="color:#d6d1c4;line-height:1.95;">${dhFaNum(total)} موقعیت واقعی پیش روی توست. پاسخ «درست» یا «غلط» وجود ندارد؛ گزینه‌ای را انتخاب کن که به رفتار واقعی تو نزدیک‌تر است.</p>
      ${resumeHint}
      <div class="dh-stage-actions">
        <button type="button" class="btn btn-primary" onclick="goTo('strategies')">${startLabel}</button>
        ${canResume ? `<button type="button" class="btn" onclick="state.currentQuestion=0;saveSession();goTo('strategies')">مرور از سؤال اول</button>` : ''}
        ${allDone ? `<button type="button" class="btn" onclick="goTo('introValues')">رفتن به لایهٔ ارزش‌ها</button>` : ''}
        <button type="button" class="btn" onclick="goBack()">بازگشت به خرده‌انگیزه‌ها</button>
      </div>
    </div>`;
}

const DH_STRATEGY_CHAPTERS = [
  'فصل ۱ از ۵ · مواجهه با ناشناخته‌ها',
  'فصل ۲ از ۵ · ریتم یادگیری و تمرکز',
  'فصل ۳ از ۵ · تعامل، تیم و بازخورد',
  'فصل ۴ از ۵ · تصمیم‌گیری در چالش',
  'فصل ۵ از ۵ · ساختن مسیر شخصی'
];
const DH_OPT_LETTERS = ['الف', 'ب', 'ج', 'د', 'هـ'];

function dhStrategyChapterHTML(qIdx) {
  const chapIdx = Math.min(4, Math.floor((qIdx || 0) / 5));
  let pips = '';
  for (let i = 0; i < 5; i++) {
    const cls = i < chapIdx ? 'is-done' : (i === chapIdx ? 'is-now' : '');
    pips += `<span class="dh-chapter-pip ${cls}"></span>`;
  }
  return `<div class="dh-chapter-bar">
    <span class="dh-chapter-title">${DH_STRATEGY_CHAPTERS[chapIdx]}</span>
    <span class="dh-chapter-steps" aria-hidden="true">${pips}</span>
  </div>`;
}

function dhStrategyMirrorHTML(answeredCount) {
  if (answeredCount < 5 || typeof analyzeStrategyStyle !== 'function') return '';
  const st = analyzeStrategyStyle(state.strategyAnswers || []);
  if (!st || !st.style) return '';
  const isCheckpoint = answeredCount === 8 || answeredCount === 16 || answeredCount >= 24;
  return `<div class="dh-live-mirror${isCheckpoint ? ' is-checkpoint' : ''}">
    <div class="dh-live-mirror-kicker">${isCheckpoint ? `✦ ایستگاه شناخت (${dhFaNum(answeredCount)} موقعیت طی شد)` : 'آینهٔ زندهٔ سبک فکری تو تا اینجا'}</div>
    <div class="dh-live-mirror-main">گرایش برجسته: <span style="color:#f5d472;">${escapeHtml(st.style)}</span> <span style="font-size:.78rem;color:#b8b2a4;">(${dhFaNum(st.strength)}٪ هم‌سویی)</span></div>
  </div>`;
}

function renderStrategy() {
  if (!state.questionsReady) {
    app.innerHTML = progressHTML('strategies') + `<div class="card dh-surface-card" style="text-align:center;">
      <h2 style="color:#f5efe2;font-size:1.15rem;margin-bottom:10px;">در حال بارگذاری موقعیت‌های راهبرد...</h2>
      <button type="button" class="btn btn-primary" onclick="retryLoadQuestions()">تلاش دوباره</button>
    </div>`;
    return;
  }
  const total = state.strategyQuestions.length;
  if (state.currentQuestion >= total) {
    state.currentQuestion = 0;
    state.currentValueQuestion = state.currentValueQuestion || 0;
    goTo('introValues');
    return;
  }
  const q = state.strategyQuestions[state.currentQuestion];
  const currentAnswer = state.strategyAnswers[state.currentQuestion];
  const answeredCount = dhAnsweredCount(state.strategyAnswers);
  let html = progressHTML('strategies') +
    dhStrategyChapterHTML(state.currentQuestion) +
    dhStrategyMirrorHTML(answeredCount) +
    dhQuestionJumperHTML(total, state.strategyAnswers, state.currentQuestion, 'jumpStrategyQ') +
    `<div class="card dh-surface-card dh-q-card">
      <div class="dh-q-top">
        <span class="dh-sjt-badge">موقعیت ${dhFaNum(q.number)} از ${dhFaNum(total)}</span>
        ${currentAnswer !== undefined && currentAnswer !== null ? '<span class="dh-picked-pill">✓ پاسخ ثبت‌شده</span>' : ''}
      </div>
      <p class="dh-q-prompt">${escapeHtml(q.question)}</p>
      <div class="dh-answer-list">`;
  q.options.forEach((o, idx) => {
    const isSelected = currentAnswer === o.index;
    const letter = DH_OPT_LETTERS[idx] || String(idx + 1);
    html += `<button type="button" class="dh-answer-option${isSelected ? ' selected' : ''}" aria-pressed="${isSelected ? 'true' : 'false'}" onclick="answerStrategy(${o.index})">
      <span class="dh-opt-letter" aria-hidden="true">${letter}</span>
      <span class="dh-answer-text">${escapeHtml(o.text)}</span>
      <span class="dh-route-check" aria-hidden="true"></span>
    </button>`;
  });
  html += `</div></div>
    <div class="dh-q-nav">
      ${state.currentQuestion > 0 ? `<button type="button" class="btn" onclick="previousStrategy()">‹ سؤال قبلی</button>` : ''}
      ${state.currentQuestion < total - 1 ? `<button type="button" class="btn" onclick="nextStrategyStep()">سؤال بعدی ›</button>` : ''}
      <button type="button" class="btn btn-primary" onclick="continueStrategy()">${answeredCount >= total ? 'ورود به دوراهی ارزش‌ها ›' : 'ادامه به اولین بی‌پاسخ'}</button>
      <button type="button" class="btn" onclick="goBack()">بازگشت</button>
    </div>`;
  app.innerHTML = html;
}

function answerStrategy(idx) {
  state.strategyAnswers[state.currentQuestion] = idx;
  const total = (state.strategyQuestions || []).length;
  let next = state.currentQuestion + 1;
  while (next < total && state.strategyAnswers[next] !== undefined && state.strategyAnswers[next] !== null) next++;
  state.currentQuestion = next;
  saveSession();
  render();
}
function previousStrategy() {
  if (state.currentQuestion > 0) {
    state.currentQuestion--;
    saveSession();
    render();
  }
}
function continueStrategy() {
  const total = (state.strategyQuestions || []).length;
  if (!total) return;
  syncStrategyCursor();
  let answered = 0;
  for (let i = 0; i < total; i++) {
    if (state.strategyAnswers[i] !== undefined && state.strategyAnswers[i] !== null) answered++;
  }
  if (answered >= total) {
    state.currentValueQuestion = state.currentValueQuestion || 0;
    goTo('introValues');
    return;
  }
  saveSession();
  render();
}
/** پرش به اولین سوال بی‌پاسخ (برای ادامه نشست) */
function syncStrategyCursor() {
  const total = (state.strategyQuestions || []).length;
  if (!total) return;
  let i = 0;
  while (i < total && state.strategyAnswers[i] !== undefined && state.strategyAnswers[i] !== null) i++;
  if (i < total) state.currentQuestion = i;
  else state.currentQuestion = Math.min(state.currentQuestion || 0, total - 1);
}
function syncValueCursor() {
  const total = (state.valueQuestions || []).length;
  if (!total) return;
  let i = 0;
  while (i < total && state.valueAnswers[i] !== undefined && state.valueAnswers[i] !== null) i++;
  if (i < total) state.currentValueQuestion = i;
  else state.currentValueQuestion = Math.min(state.currentValueQuestion || 0, total - 1);
}

async function retryLoadQuestions() {
  state.retryCount++;
  app.innerHTML = progressHTML(state.stage) + `<div class="card dh-surface-card" style="text-align:center;"><p style="color:#f5efe2;">در حال تلاش دوباره (${dhFaNum(state.retryCount)})...</p></div>`;
  await loadQuestions();
  render();
}

// ==================== VALUES + CHOICE ====================
function jumpValueQ(idx) {
  const total = (state.valueQuestions && state.valueQuestions.length) || 0;
  if (idx < 0 || idx >= total) return;
  state.stage = 'values';
  state.currentValueQuestion = idx;
  saveSession();
  render();
}
window.jumpValueQ = jumpValueQ;

function nextValueStep() {
  const total = (state.valueQuestions && state.valueQuestions.length) || 0;
  if (state.currentValueQuestion < total - 1) {
    state.currentValueQuestion++;
    saveSession();
    render();
  }
}
window.nextValueStep = nextValueStep;

function renderIntroValues() {
  const fmt = typeof dhFaNum === 'function' ? dhFaNum : function (x) { return String(x); };
  const answered = (state.valueAnswers || []).filter(a => a !== undefined && a !== null && String(a).trim() !== '').length;
  const total = (state.valueQuestions && state.valueQuestions.length) || 15;
  const canResume = answered > 0 && answered < total;
  const allDone = answered >= total;
  const startLabel = allDone
    ? 'مرور پاسخ‌ها یا رفتن به صفحهٔ تحلیل'
    : (canResume ? `ادامه از سؤال ${fmt(answered + 1)} از ${fmt(total)}` : 'شروع سؤالات ارزش');
  const schemaNoticeHTML = state.valueSchemaResetNotice
    ? `<p data-dh-value-schema-reset="1" style="color:#f0c040;background:rgba(240,192,64,.10);border:1px solid rgba(240,192,64,.35);border-radius:12px;padding:10px 12px;margin-top:12px;font-size:0.86rem;line-height:1.9;">${escapeHtml(state.valueSchemaResetNotice)}</p>`
    : '';
  const resumeHint = answered > 0
    ? `<p style="color:#f0c040;background:rgba(240,192,64,.08);border:1px solid rgba(240,192,64,.25);border-radius:12px;padding:9px 12px;text-align:center;margin-top:10px;font-size:.86rem;">✓ ${fmt(answered)} از ${fmt(total)} پاسخ ذخیره شده است.</p>`
    : '';
  const chip = typeof sparkChipHTML === 'function' ? sparkChipHTML() : '';
  app.innerHTML = progressHTML('introValues') + chip + `
    <div class="dh-stage-head">
      <h2 class="dh-stage-title">لایهٔ سوم: ارزش‌های بنیادین</h2>
      <p class="dh-stage-hint">اینجا بین دو قطب ارزشمند دست به انتخاب می‌زنی تا مشخص شود چه چیزی برایت اولویت عمیق‌تری دارد.</p>
    </div>
    <div class="card dh-surface-card">
      <p style="color:#d6d1c4;line-height:1.95;">هیچ گزینه‌ای خوب یا بدِ مطلق نیست؛ هر دو قطب ارزشمندند. گزینه‌ای را برگزین که در درازمدت رضایت بیشتری برایت می‌آورد.</p>
      ${schemaNoticeHTML}
      ${resumeHint}
      <div class="dh-stage-actions">
        <button type="button" class="btn btn-primary" onclick="goTo('values')">${startLabel}</button>
        ${canResume ? `<button type="button" class="btn" onclick="state.currentValueQuestion=0;saveSession();goTo('values')">مرور از سؤال اول</button>` : ''}
        ${allDone ? `<button type="button" class="btn" onclick="goTo('choice')">رفتن به صفحهٔ انتخاب تحلیل</button>` : ''}
        <button type="button" class="btn" onclick="goBack()">بازگشت به راهبردها</button>
      </div>
    </div>`;
}

const DH_VALUE_POLE_TITLES = {
  Q1A: 'عمق‌تأثیر',       Q1B: 'گستره‌تأثیر',
  Q2A: 'میراث‌مادی',      Q2B: 'میراث‌انسانی',
  Q3A: 'عمق‌محور',        Q3B: 'گستره‌محور',
  Q4A: 'حقیقت‌جو',        Q4B: 'خلق‌زیبایی',
  Q5A: 'نظم‌خواه',        Q5B: 'آشوب‌پذیر',
  Q6A: 'مسئولیت‌فردی',    Q6B: 'مسئولیت‌سیستمی',
  Q7A: 'خالق',            Q7B: 'ناقل',
  Q8A: 'آزادی‌خواه',      Q8B: 'امنیت‌خواه',
  Q9A: 'تغییرگر',         Q9B: 'محافظ',
  Q10A: 'دیده‌شدن',       Q10B: 'بی‌نام‌تأثیرگذار',
  Q11A: 'داده‌نگر',       Q11B: 'انسان‌نگر',
  Q12A: 'ریسک‌پذیر',      Q12B: 'ثبات‌خواه',
  Q13A: 'نتیجه‌فوری',     Q13B: 'اثر‌بلندمدت',
  Q14A: 'تعلق‌خواه',      Q14B: 'استقلال‌طلب',
  Q15A: 'تسلط‌گرا',       Q15B: 'کنجکاوی‌گرا'
};

function renderValue() {
  const fmt = typeof dhFaNum === 'function' ? dhFaNum : function (x) { return String(x); };
  const cntFn = typeof dhAnsweredCount === 'function'
    ? dhAnsweredCount
    : function (arr) { return (arr || []).filter(function (v) { return v !== undefined && v !== null && String(v).trim() !== ''; }).length; };
  if (!state.questionsReady) {
    app.innerHTML = progressHTML('values') + `<div class="card dh-surface-card" style="text-align:center;">
      <h2 style="color:#f5efe2;font-size:1.15rem;margin-bottom:10px;">در حال بارگذاری دوراهی‌های ارزش...</h2>
      <button type="button" class="btn btn-primary" onclick="retryLoadQuestions()">تلاش دوباره</button>
    </div>`;
    return;
  }
  const total = state.valueQuestions.length;
  if (state.currentValueQuestion >= total) {
    app.innerHTML = progressHTML('values') + `
      <div class="dh-done-box">
        <h2 style="color:#fff8eb;font-size:1.35rem;margin-bottom:8px;">✦ هر سه لایهٔ شناخت کامل شد!</h2>
        <p style="color:#d6d1c4;line-height:1.9;">تا اینجا ${fmt(state.likedCodes.length)} خرده‌انگیزه، ${fmt(cntFn(state.strategyAnswers))} موقعیت راهبردی و ${fmt(cntFn(state.valueAnswers))} دوراهی ارزشی از خودت ثبت کرده‌ای.</p>
        <div class="dh-stage-actions">
          <button type="button" class="btn btn-primary" onclick="goTo('choice')">رفتن به صفحهٔ رمزگشایی نهایی ›</button>
          <button type="button" class="btn" onclick="state.currentValueQuestion=${Math.max(0, total - 1)};saveSession();render()">مرور دوراهی‌های ارزش</button>
        </div>
      </div>`;
    return;
  }
  const q = state.valueQuestions[state.currentValueQuestion];
  const opts = q.options;
  const currentAnswer = state.valueAnswers[state.currentValueQuestion];
  const answeredCount = cntFn(state.valueAnswers);
  const poleA = DH_VALUE_POLE_TITLES[opts[0].code] || 'قطب اول';
  const poleB = DH_VALUE_POLE_TITLES[opts[1].code] || 'قطب دوم';
  const jumperHTML = typeof dhQuestionJumperHTML === 'function'
    ? dhQuestionJumperHTML(total, state.valueAnswers, state.currentValueQuestion, 'jumpValueQ')
    : '';
  app.innerHTML = progressHTML('values') +
    jumperHTML +
    `<div class="card dh-surface-card dh-q-card">
      <div class="dh-q-top">
        <span class="dh-sjt-badge">دوئل دوراهی · ${fmt(q.number)} از ${fmt(total)}</span>
        ${currentAnswer ? '<span class="dh-picked-pill">✓ انتخاب ثبت‌شده</span>' : ''}
      </div>
      <p class="dh-q-prompt" style="text-align:center;">${escapeHtml(q.question)}</p>
      <div class="dh-duel-arena">
        <button type="button" class="dh-answer-option dh-duel-card dh-duel-card--a${currentAnswer === opts[0].code ? ' selected' : ''}" aria-pressed="${currentAnswer === opts[0].code ? 'true' : 'false'}" onclick="answerValue('${opts[0].code}')">
          <div class="dh-duel-pole-head">
            <span class="dh-duel-pole-tag">✦ ${escapeHtml(poleA)}</span>
            <span class="dh-route-check" aria-hidden="true"></span>
          </div>
          <p class="dh-duel-body">${escapeHtml(opts[0].text)}</p>
        </button>
        <div class="dh-duel-vs" aria-hidden="true">یا</div>
        <button type="button" class="dh-answer-option dh-duel-card dh-duel-card--b${currentAnswer === opts[1].code ? ' selected' : ''}" aria-pressed="${currentAnswer === opts[1].code ? 'true' : 'false'}" onclick="answerValue('${opts[1].code}')">
          <div class="dh-duel-pole-head">
            <span class="dh-duel-pole-tag">✦ ${escapeHtml(poleB)}</span>
            <span class="dh-route-check" aria-hidden="true"></span>
          </div>
          <p class="dh-duel-body">${escapeHtml(opts[1].text)}</p>
        </button>
      </div>
    </div>
    <div class="dh-q-nav">
      ${state.currentValueQuestion > 0 ? `<button type="button" class="btn" onclick="previousValue()">‹ دوراهی قبلی</button>` : ''}
      ${state.currentValueQuestion < total - 1 ? `<button type="button" class="btn" onclick="nextValueStep()">دوراهی بعدی ›</button>` : ''}
      <button type="button" class="btn btn-primary" onclick="continueValue()">${answeredCount >= total ? 'ادامه به رمزگشایی نهایی ›' : 'ادامه به اولین بی‌پاسخ'}</button>
      <button type="button" class="btn" onclick="goBack()">بازگشت</button>
    </div>`;
}

function answerValue(code) {
  state.valueSchemaResetNotice = '';
  state.valueAnswers[state.currentValueQuestion] = code;
  const total = (state.valueQuestions || []).length;
  let next = state.currentValueQuestion + 1;
  while (next < total && state.valueAnswers[next] !== undefined && state.valueAnswers[next] !== null) next++;
  state.currentValueQuestion = next;
  saveSession();
  render();
}
function previousValue() { if (state.currentValueQuestion > 0) { state.currentValueQuestion--; saveSession(); render(); } }
function continueValue() {
  const total = (state.valueQuestions || []).length;
  if (!total) return;
  syncValueCursor();
  let answered = 0;
  for (let i = 0; i < total; i++) {
    if (state.valueAnswers[i] !== undefined && state.valueAnswers[i] !== null) answered++;
  }
  if (answered >= total) {
    goTo('choice');
    return;
  }
  saveSession();
  render();
}

// ==================== صفحه انتخاب ====================
function renderChoice() {
  ensureUXStyles();
  const mix = dhComputeWorldSparkMix();
  const topWorldsHTML = mix.slice(0, 3).map(m =>
    `<span class="dh-world-orb" style="--dh-world:${m.theme.color};--dh-world-border:${m.theme.border};--dh-world-glow:${m.theme.glow}">${m.theme.svg}<span>${escapeHtml(m.theme.title)} · ${dhFaNum(m.pct)}٪</span></span>`
  ).join('');
  const sStyle = (state.strategyAnswers || []).length >= 5 && typeof analyzeStrategyStyle === 'function'
    ? analyzeStrategyStyle(state.strategyAnswers)
    : null;
  const isDisabled = Boolean(state.choiceDisabled) || (Array.isArray(state.likedCodes) && state.likedCodes.length < 20);
  const disabledAttr = isDisabled ? ' disabled aria-disabled="true"' : '';
  const btnPrimaryInline = isDisabled
    ? 'width:100%;display:block;margin:0;text-align:right;padding:18px;border-radius:18px;background:#222634;border:1.5px solid rgba(255,255,255,.13);color:#8e8a7f;box-shadow:none;opacity:.62;cursor:not-allowed'
    : 'width:100%;display:block;margin:0;text-align:right;padding:18px;border-radius:18px;background:linear-gradient(135deg,#f8da72 0%,#f0c040 52%,#cfa125 100%);border:1.5px solid #fbe38e;color:#141108;box-shadow:0 12px 30px rgba(240,192,64,.34)';
  const btnAltInline = isDisabled
    ? btnPrimaryInline
    : 'width:100%;display:block;margin:0;text-align:right;padding:18px;border-radius:18px;background:linear-gradient(135deg,#f5d259 0%,#e7b532 54%,#c7951c 100%);border:1.5px solid #ffe8a3;color:#141108;box-shadow:0 12px 30px rgba(240,192,64,.34)';

  app.innerHTML = progressHTML('choice') + sparkChipHTML() + `
    <div class="dh-stage-head">
      <h2 class="dh-stage-title">رمزگشایی نقشهٔ فردیت تو</h2>
      <p class="dh-stage-hint">همهٔ داده‌های درونی تو آمادهٔ ترکیب‌اند — بگو می‌خواهی نقشه را در چه افقی ببینی؟</p>
      ${topWorldsHTML ? `<div class="dh-world-orbs">${topWorldsHTML}</div>` : ''}
    </div>
    ${sStyle && sStyle.style ? `<div class="dh-live-mirror is-checkpoint" style="margin-bottom:14px;">
      <div class="dh-live-mirror-kicker">✦ چکیدهٔ زندهٔ پروفایل تو پیش از تطبیق نهایی</div>
      <div class="dh-live-mirror-main">${dhFaNum(state.likedCodes.length)} جرقهٔ فعال · سبک فکری غالب: <span style="color:#f5d472;">${escapeHtml(sStyle.style)}</span></div>
    </div>` : ''}
    ${isDisabled ? `<p class="dh-stage-hint" style="color:#f5d472;font-weight:700;">برای فعال شدن تحلیل نهایی، حداقل ${dhFaNum(20)} جرقه باید انتخاب شده باشد.</p>` : ''}
    <div class="dh-choice-modes">
      <button type="button" id="dh-choice-branches-btn" class="btn btn-primary dh-choice-mode-card"${disabledAttr} style="${btnPrimaryInline}" onclick="if(!this.disabled) analyzeBranches()">
        <span class="dh-choice-kicker">مناسب پایهٔ نهم و دورهٔ متوسطه</span>
        <div class="dh-choice-title">تحلیل شاخه (هدایت تحصیلی دبیرستان) ›</div>
        <div class="dh-choice-sub">مقایسهٔ هم‌خوانی فردیت تو با شاخه‌های نظری، فنی‌وحرفه‌ای و کاردانش بر اساس جرقه‌ها، راهبردها و ارزش‌ها.</div>
      </button>
      <button type="button" id="dh-choice-majors-btn" class="btn btn-primary dh-choice-mode-card dh-choice-mode-card--alt"${disabledAttr} style="${btnAltInline}" onclick="if(!this.disabled) analyzeMajors()">
        <span class="dh-choice-kicker">مناسب دبیرستانی‌ها، کنکوری‌ها و دانشجویان</span>
        <div class="dh-choice-title">تحلیل دانشگاه (انتخاب رشته‌های دانشگاهی) ›</div>
        <div class="dh-choice-sub">کشف دقیق‌ترین رشته‌های دانشگاهی هم‌سو با انرژی درونی تو از میان کاتالوگ جامع رشته‌ها.</div>
      </button>
    </div>
    <div class="dh-stage-actions">
      ${state.journeyFinished
        ? `<button type="button" class="btn" onclick="dhReturnToFinishedResults()">‹ بازگشت به نتیجهٔ تحلیل</button>
           <button type="button" class="btn" onclick="dhGoHomeKeepPlace()">بازگشت به صفحه اول</button>`
        : `<button type="button" class="btn" onclick="goBack()">‹ مرور دوراهی‌های ارزش</button>`}
    </div>
  `;
}

// ==================== BUILD PAYLOAD (بدون تغییر) ====================
function buildPayload() {
  const sjt = {};
  state.strategyQuestions.forEach((q, i) => {
    if (state.strategyAnswers[i] !== undefined) {
      const num = parseInt(q.id.replace("S", ""), 10);
      sjt[`sjt_${num}`] = String.fromCharCode(65 + state.strategyAnswers[i]);
    }
  });

  const conj = {};
  state.valueQuestions.forEach((q, i) => {
    if (state.valueAnswers[i] !== undefined) {
      let val = state.valueAnswers[i];
      if (/^[AB]\d+Q$/.test(val)) {
        const letter = val[0];
        const number = val.slice(1, -1);
        val = `Q${number}${letter}`;
      }
      const num = parseInt(q.id.replace("V", ""), 10);
      conj[`conj_${num}`] = val;
    }
  });

  return {
    micro_motives: state.likedCodes,
    sjt_answers: sjt,
    conjoint_choices: conj
  };
}


async function ensureJourneyChargedForResults() {
  var authState = null;
  var journey = null;
  var pendingSessionId = null;
  var chargedSessionId = null;
  try { authState = JSON.parse(localStorage.getItem('dh_auth_v1') || 'null'); } catch (_) {}
  var token = authState && typeof authState.token === 'string' ? authState.token.trim() : '';
  if (!token) {
    var authError = new Error('ورود تجاری معتبر نیست یا نشست ورود پایان یافته است.');
    authError.code = 'AUTH_REQUIRED';
    throw authError;
  }
  try { journey = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null'); } catch (_) {}
  try { pendingSessionId = localStorage.getItem('dh_pending_journey_session_id'); } catch (_) {}
  try { chargedSessionId = localStorage.getItem('dh_quota_charged_session_v1'); } catch (_) {}
  var pendingChargedId = pendingSessionId && chargedSessionId === pendingSessionId
    ? String(pendingSessionId) : '';
  var journeySessionId = journey && journey.sessionId ? String(journey.sessionId) : '';
  var stateSessionId = state && state.sessionId ? String(state.sessionId) : '';

  if (chargedSessionId) {
    if (pendingChargedId || !journeySessionId || journeySessionId === String(chargedSessionId)) {
      var existingCharged = pendingChargedId || String(chargedSessionId);
      if (state) state.sessionId = existingCharged;
      try { if (typeof saveSession === 'function') saveSession(); } catch (_) {}
      return existingCharged;
    }
    var conflictError = new Error('شناسهٔ سفر شارژشده با سفر ذخیره‌شده تطبیق ندارد؛ از خانه سفر را از مسیر تجاری شروع کنید.');
    conflictError.code = 'JOURNEY_SESSION_REQUIRED';
    throw conflictError;
  }

  var candidateId = stateSessionId || journeySessionId ||
    (typeof window !== 'undefined' && window && window.DHQuotaEnforcement &&
     typeof window.DHQuotaEnforcement.ensureJourneySession === 'function'
       ? String(window.DHQuotaEnforcement.ensureJourneySession() || '')
       : '');
  if (!candidateId) {
    var missingError = new Error('شناسهٔ سفر آماده نیست؛ از خانه سفر را از مسیر تجاری شروع کنید.');
    missingError.code = 'JOURNEY_SESSION_REQUIRED';
    throw missingError;
  }
  if (typeof window === 'undefined' || !window || !window.DHQuotaEnforcement ||
      typeof window.DHQuotaEnforcement.consumeForJourney !== 'function') {
    var bridgeError = new Error('اتصال ایمن سهمیه برای ثبت نتیجهٔ سفر آماده نیست.');
    bridgeError.code = 'QUOTA_BRIDGE_UNAVAILABLE';
    throw bridgeError;
  }

  var charge = await window.DHQuotaEnforcement.consumeForJourney(candidateId);
  if (!charge || !(charge.consumed === 1 || charge.already_consumed === true || charge.local_guard === true)) {
    var unconfirmedError = new Error('ثبت مصرف اعتبار برای دریافت نتیجه تأیید نشد.');
    unconfirmedError.code = 'QUOTA_CHARGE_UNCONFIRMED';
    throw unconfirmedError;
  }
  if (state) state.sessionId = candidateId;
  try { if (typeof saveSession === 'function') saveSession(); } catch (_) {}
  return candidateId;
}

function buildJourneyAnalysisRequest(payload) {
  var authState = null;
  var journey = null;
  var pendingSessionId = null;
  var chargedSessionId = null;
  try { authState = JSON.parse(localStorage.getItem('dh_auth_v1') || 'null'); } catch (_) {}
  var token = authState && typeof authState.token === 'string' ? authState.token.trim() : '';
  if (!token) {
    var authError = new Error('ورود تجاری معتبر نیست یا نشست ورود پایان یافته است.');
    authError.code = 'AUTH_REQUIRED';
    throw authError;
  }
  try { journey = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null'); } catch (_) {}
  try { pendingSessionId = localStorage.getItem('dh_pending_journey_session_id'); } catch (_) {}
  try { chargedSessionId = localStorage.getItem('dh_quota_charged_session_v1'); } catch (_) {}
  var pendingChargedId = pendingSessionId && chargedSessionId === pendingSessionId
    ? String(pendingSessionId) : '';
  var journeySessionId = journey && journey.sessionId ? String(journey.sessionId) : '';
  var stateSessionId = state && state.sessionId ? String(state.sessionId) : '';
  var prefix = function (value) { return value ? String(value).slice(0, 8) : null; };
  try {
    if (typeof console !== 'undefined' && console.debug) console.debug('[DarkHorse][session-diagnostic]', {
      hasToken: !!token,
      chargedIdPrefix: prefix(chargedSessionId),
      stateSessionPrefix: prefix(stateSessionId),
      journeySessionPrefix: prefix(journeySessionId)
    });
  } catch (_) {}

  var sessionId = '';
  if (chargedSessionId) {
    if (pendingChargedId) {
      // Pending+charged is the explicit hand-off window: attach this UUID to
      // the in-flight journey before discover, even if a stale record existed.
      sessionId = pendingChargedId;
      if (!journey) journey = {};
      journey.sessionId = sessionId;
      try { localStorage.setItem('darkhorse_session_v2', JSON.stringify(journey)); } catch (_) {}
    } else if (journeySessionId && journeySessionId === String(chargedSessionId)) {
      sessionId = journeySessionId;
    } else if (!journeySessionId) {
      // Recover a missing journey UUID from the server-confirmed local charge.
      sessionId = String(chargedSessionId);
      if (!journey) journey = {};
      journey.sessionId = sessionId;
      try { localStorage.setItem('darkhorse_session_v2', JSON.stringify(journey)); } catch (_) {}
    } else {
      // Never silently continue a saved journey charged under another UUID.
      sessionId = stateSessionId || journeySessionId;
    }
  }
  if (!sessionId || String(chargedSessionId || '') !== String(sessionId) ||
      (journey && journey.sessionId && String(journey.sessionId) !== String(sessionId))) {
    var journeyError = new Error('شناسهٔ سفر شارژشده با سفر ذخیره‌شده تطبیق ندارد؛ از خانه سفر را از مسیر تجاری شروع کنید.');
    journeyError.code = 'JOURNEY_SESSION_REQUIRED';
    throw journeyError;
  }
  if (state && String(state.sessionId || '') !== String(sessionId)) state.sessionId = String(sessionId);
  try { if (typeof saveSession === 'function') saveSession(); } catch (_) {}
  var requestPayload = Object.assign({}, payload || {}, { session_id: sessionId });
  return {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token
    },
    body: JSON.stringify(requestPayload)
  };
}

function journeyAnalysisErrorHTML(error, journeyType) {
  var status = Number(error && error.status || 0);
  var errMsg = String(error && error.message || '');
  var quotaExhausted = status === 402 || Boolean(error && error.quotaExhausted) ||
    (status === 409 && /credit|quota|remaining|اعتبار|سهمیه/i.test(errMsg));
  var retryCall = journeyType === 'branches' ? 'analyzeBranches()' : 'analyzeMajors()';
  var title = 'خطا در آماده‌سازی نتیجه';
  var message = 'در دریافت نتیجه مشکلی رخ داد. وضعیت سفر حفظ شده است؛ دوباره تلاش کنید یا به مرحلهٔ قبل برگردید.';
  var actions = '<button class="btn btn-primary" style="width:100%;margin-top:15px;" onclick="' + retryCall + '">🔄 تلاش دوباره</button>';
  if (error && error.code === 'AUTH_REQUIRED' && !status) {
    title = 'ورود به حساب تجاری لازم است';
    message = 'نشست تجاری در این دستگاه موجود نیست؛ درخواست نتیجه ارسال نشد. وارد حساب شوید و سفر را از خانه ادامه دهید.';
    actions = "<button class=\"btn btn-primary\" style=\"width:100%;margin-top:15px;\" onclick=\"if(window.DHCommercialUI&&typeof window.DHCommercialUI.showAuth==='function'){window.DHCommercialUI.showAuth('login')}else{location.reload()}\">ورود به حساب</button>";
  } else if (error && error.code === 'JOURNEY_SESSION_REQUIRED' && !status) {
    title = 'شناسهٔ سفر آماده نیست';
    message = 'اعتبار حساب فقط سهمیهٔ شما را نشان می‌دهد و جای شناسهٔ اختصاصی همین سفر را نمی‌گیرد؛ هیچ درخواست نتیجه‌ای به سرور ارسال نشد. از خانه، سفر را از مسیر تجاری دوباره شروع کنید.';
    actions = "<button class=\"btn btn-primary\" style=\"width:100%;margin-top:15px;\" onclick=\"if(window.DHShell&&typeof window.DHShell.switchTab==='function'){window.DHShell.switchTab('home')}else{location.reload()}\">شروع مجدد از خانه</button>";
  } else if (status === 401) {
    title = 'ورود دوباره لازم است (HTTP 401)';
    message = 'سرور نشست ورود را نامعتبر یا منقضی تشخیص داد. با همان حساب تجاری دوباره وارد شوید؛ این خطا به معنی قطع شبکه نیست.';
    actions = "<button class=\"btn btn-primary\" style=\"width:100%;margin-top:15px;\" onclick=\"if(window.DHCommercialUI&&typeof window.DHCommercialUI.showAuth==='function'){window.DHCommercialUI.showAuth('login')}else{location.reload()}\">ورود دوباره</button>";
  } else if (quotaExhausted) {
    title = 'اعتبار کافی برای مشاهدهٔ نتیجه وجود ندارد' + (status ? ' (HTTP ' + status + ')' : '');
    message = 'اعتبار سفر اکتشافی شما در سرور به پایان رسیده است. همهٔ پاسخ‌های این سفر ذخیره شده است؛ پس از تهیهٔ بستهٔ اعتبار، با زدن «تلاش دوباره پس از شارژ» نتیجهٔ همین سفر را بدون تکرار مراحل دریافت کنید.';
    actions = "<button class=\"btn btn-primary\" style=\"width:100%;margin-top:15px;\" onclick=\"if(window.DHCommercialUI&&typeof window.DHCommercialUI.showPurchase==='function'){window.DHCommercialUI.showPurchase()}else{location.reload()}\">تهیهٔ اعتبار</button>" +
      '<button class="btn" style="width:100%;margin-top:8px;" onclick="' + retryCall + '">🔄 تلاش دوباره پس از شارژ</button>';
  } else if (status === 403) {
    title = 'دسترسی به سفر تأیید نشد (HTTP 403)';
    message = 'سرور این شناسهٔ سفر را برای دریافت نتیجه مجاز ندانست. در صورت اتمام اعتبار، بستهٔ اعتبار تهیه کنید یا سفر را از خانه و با حساب تجاری ادامه دهید؛ این یک خطای مجوز/سشن است، نه خطای شبکه.';
    actions = "<button class=\"btn btn-primary\" style=\"width:100%;margin-top:15px;\" onclick=\"if(window.DHCommercialUI&&typeof window.DHCommercialUI.showPurchase==='function'){window.DHCommercialUI.showPurchase()}else{location.reload()}\">تهیهٔ اعتبار</button>" +
      "<button class=\"btn\" style=\"width:100%;margin-top:8px;\" onclick=\"if(window.DHShell&&typeof window.DHShell.switchTab==='function'){window.DHShell.switchTab('home')}else{location.reload()}\">بازگشت به خانه</button>";
  } else if (status >= 400) {
    title = 'سرور پاسخ خطا داد (HTTP ' + status + ')';
    message = 'درخواست به سرور رسید، اما سرور نتیجه را نپذیرفت یا نتوانست پردازش کند. وضعیت HTTP بالا را برای بررسی ثبت کنید.';
  } else if (error && (error.name === 'AbortError' || error.name === 'TypeError')) {
    title = 'ارتباط شبکه با سرور برقرار نشد';
    message = 'پاسخی از سرور دریافت نشد یا مهلت انتظار پایان یافت. اتصال اینترنت را بررسی و دوباره تلاش کنید.';
  }
  return progressHTML('results') + '<div class="card" role="alert"><h2>' + title + '</h2><p>' + message + '</p>' + actions +
    '<button class="btn" style="width:100%;margin-top:8px;" onclick="goTo(&quot;choice&quot;)">⬅️ بازگشت به انتخاب</button></div>';
}

// ==================== توابع تحلیل (جدید/تغییر نام) ====================
function dhNotifyAnalysisGateError(err) {
  var st = Number(err && err.status || 0);
  var msg = String(err && err.message || '');
  var exhausted = st === 402 || Boolean(err && err.quotaExhausted) ||
    (st === 409 && /credit|quota|remaining|اعتبار|سهمیه/i.test(msg));
  if (exhausted || st === 403) {
    try {
      if (window.DHCommercialUI && typeof window.DHCommercialUI.showPurchase === 'function') {
        window.DHCommercialUI.showPurchase(
          exhausted
            ? 'اعتبار سفر اکتشافی شما به پایان رسیده است. پس از تهیهٔ اعتبار، بدون تکرار مراحل نتیجه را مشاهده کنید.'
            : 'دسترسی یا اعتبار این سفر در سرور تأیید نشد. برای ادامه، بستهٔ اعتبار تهیه کنید.'
        );
      }
    } catch (_) {}
  } else if (st === 401 || (err && err.code === 'AUTH_REQUIRED')) {
    try {
      if (window.DHCommercialUI && typeof window.DHCommercialUI.showAuth === 'function') {
        window.DHCommercialUI.showAuth('login');
      }
    } catch (_) {}
  }
}

async function analyzeMajors() {
  state.stage = 'results';
  const payload = buildPayload();
  state.lastPayload = payload;
  app.innerHTML = progressHTML('results') + loadingHTML('داره جرقه‌هات رو به رشته‌ها وصل می‌کنه...');
  try {
    await ensureJourneyChargedForResults();
    const res = await fetchWithRetry(API_BASE + '/api/v2/darkhorse/discover', buildJourneyAnalysisRequest(payload));
    const data = await res.json();
    state.majorsResult = data;
    displayResults(data, 'majors');
  } catch (e) {
    console.error(e);
    app.innerHTML = journeyAnalysisErrorHTML(e, 'majors');
    dhNotifyAnalysisGateError(e);
  }
}

async function analyzeBranches() {
  state.stage = 'results';
  const payload = buildPayload();
  state.lastPayload = payload;
  app.innerHTML = progressHTML('results') + loadingHTML('داره نقشهٔ شاخه‌ها رو با انگیزه‌هات میزان می‌کنه...');
  try {
    await ensureJourneyChargedForResults();
    const res = await fetchWithRetry(API_BASE + '/api/v2/darkhorse/branch-discovery', buildJourneyAnalysisRequest(payload));
    const data = await res.json();
    state.branchesResult = data;
    displayResults(data, 'branches');
  } catch (e) {
    console.error(e);
    app.innerHTML = journeyAnalysisErrorHTML(e, 'branches');
    dhNotifyAnalysisGateError(e);
  }
}

async function fetchWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 90000);
      let res;
      try {
        res = await fetch(url, { ...options, signal: controller.signal });
      } finally {
        clearTimeout(timeout);
      }
      if (!res.ok) {
        const error = new Error('HTTP ' + res.status);
        error.status = Number(res.status) || 0;
        throw error;
      }
      return res;
    } catch (e) {
      const status = Number(e && e.status || 0);
      // Authentication/authorization and other non-transient client errors are not network failures.
      if ((status >= 400 && status < 500) && status !== 408 && status !== 429) throw e;
      if (i === maxRetries - 1) throw e;
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
}

// ==================== DISPLAY RESULTS (نسخه نهایی با UI/UX بهبودیافته) ====================

// ==================== توضیح مشاوره‌ای (Cloudflare Workers AI) ====================
async function loadDeepCounselItem(index, mode) {
  mode = mode || 'main';
  const box = document.getElementById('dh-counsel-box-' + index);
  if (!box) return;

  const tops = state.lastCounselTops || [];
  const item = tops[index];
  if (!item) {
    box.style.display = 'block';
    box.innerHTML = '<p style="color:#f88;text-align:center;">داده‌ای برای این مسیر در دسترس نیست.</p>';
    return;
  }

  box.style.display = 'block';
  box.innerHTML = '<p style="color:#f0c040;line-height:1.9;margin:0;text-align:center;">در حال آماده‌سازی توضیح مشاوره‌ای برای «' + escapeHtml(item.name || '') + '»...</p>';

  const profile = {
    kind: state.lastCounselKind || 'majors',
    micro_motives: state.likedCodes || [],
    liked_motives: state.likedCodes || []
  };

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 65000);
    const res = await fetch(API_BASE + '/api/v2/darkhorse/counsel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile: profile,
        top_results: [item],
        journey_type: state.lastCounselKind || 'majors',
        mode: mode
      }),
      signal: controller.signal
    });
    clearTimeout(timeout);
    let data = null;
    try { data = await res.json(); } catch (_) {}
    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) || ('خطا ' + res.status);
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    const text = (data && data.counseling) ? String(data.counseling).trim() : '';
    if (!text) throw new Error('پاسخ خالی');
    const safe = escapeHtml(text).replace(/\n/g, '<br>');
    const title = mode === 'alternatives'
      ? ('🔄 مسیرهای جایگزین «' + escapeHtml(item.name || '') + '»')
      : ('✨ مشاوره «' + escapeHtml(item.name || '') + '»');
    box.innerHTML =
      '<div style="background:linear-gradient(145deg,#14141f,#0f0f18);border:1px solid rgba(212,175,55,.45);border-radius:16px;padding:18px;text-align:right;line-height:2;color:#e8dcc0;">' +
      '<h3 style="color:#f0c040;margin:0 0 12px;font-size:1.02rem;">' + title + '</h3>' +
      '<div style="font-size:0.95rem;">' + safe + '</div></div>';
  } catch (e) {
    console.error(e);
    box.innerHTML = '<p style="color:#f88;line-height:1.8;margin:0;text-align:center;">الان نتوانستیم توضیح مشاوره‌ای را بگیریم. کمی بعد دوباره تلاش کنید.</p>';
  }
}

async function loadDeepCounsel(mode) {
  // سازگاری عقب‌رو: اگر هنوز جایی سراسری صدا بزند، اولین نتیجه
  return loadDeepCounselItem(0, mode || 'main');
}


function displayResults(data, type) {
  // ===== ۱. استخراج آیتم‌ها =====
  let items = [];
  let isBranch = false;
  let bestBranch = null;
  let rawData = data;

  if (data.recommended_branches) {
    items = data.recommended_branches;
    isBranch = true;
    bestBranch = data.best_branch || null;
    rawData = data;
  } else if (data.discovered_majors) {
    items = data.discovered_majors;
    isBranch = false;
    rawData = data;
  } else if (data.branch_discovery_result?.branches) {
    items = data.branch_discovery_result.branches;
    isBranch = true;
    bestBranch = data.branch_discovery_result.best_branch || null;
    rawData = data.branch_discovery_result;
  } else if (data.discovery_result?.recommendations) {
    items = data.discovery_result.recommendations;
    isBranch = false;
    rawData = data.discovery_result;
  } else if (Array.isArray(data)) {
    items = data;
  } else {
    items = [];
  }

  // ===== ۲. نرمال‌سازی =====
  const normalized = items.map(item => {
    const fit = item.individuality_fit || item;
    let archetypeData = null;
    if (fit.archetype) archetypeData = fit.archetype;
    else if (item.archetype) archetypeData = item.archetype;
    if (typeof archetypeData === 'string') {
      archetypeData = { archetype: archetypeData, identity_sentence: '' };
    }
    return {
      name: item.major_name_fa || item.branch_name_fa || fit.major_name_fa || fit.branch_name_fa || item.name || item.branch_name || 'نامشخص',
      // شاخه‌ها average_score می‌دهند نه score — بدون این، همه صفر می‌شدند
      fit_score: fit.score || fit.fit_score || item.fit_score || item.average_score || 0,
      raw_components: fit.raw_components || item.raw_components || item.avg_components || {},
      evidence: fit.evidence || item.evidence || {},
      personalized_description: fit.personalized_description || item.personalized_description || '',
      archetype: archetypeData,
      fulfillment_source: fit.fulfillment_source || fit.archetype?.fulfillment_source || null,
      alternative_paths: fit.alternative_paths || item.alternative_paths || [],
      // موتور دو قرارداد مختلف دارد: recommend_school_branch یک رشتهٔ مفرد «warning» می‌دهد،
      // ولی discover_individuality آرایهٔ «evidence.warnings» (شامل پیام مهم «مسیر اسب‌سیاه») می‌دهد.
      // هر دو را جمع می‌کنیم تا هیچ‌کدام گم نشوند.
      warnings: [
        ...(fit.warning || item.warning ? [fit.warning || item.warning] : []),
        ...((fit.evidence && fit.evidence.warnings) || (item.evidence && item.evidence.warnings) || [])
      ],
      count: fit.count || item.count || null,
      avg_components: fit.avg_components || item.avg_components || null,
      micro_motives_matched: fit.evidence?.micro_motives_matched || item.evidence?.micro_motives_matched || []
    };
  });

  // ===== ۳. فیلتر و مرتب‌سازی =====
  // فقط رشته‌هایی که هم Total≥30 و هم خرده‌انگیزه واقعی (M≥15) دارند
  // بدون این فیلتر، رشته فقط با راهبرد/ارزش تا ~۴۵٪ می‌آمد
  const matched = normalized
    .filter(item => {
      const total = item.fit_score || 0;
      if (total < 30) return false;
      const m = (item.raw_components && (item.raw_components.m_score ?? item.raw_components.M)) ;
      const mVal = m != null ? Number(m) : 0;
      // m_score از موتور ۰–۱۰۰ است
      if (mVal < 15) return false;
      // اگر evidence خالی است ولی m گزارش شده، همان m را قبول کن
      return true;
    })
    .sort((a, b) => (b.fit_score || 0) - (a.fit_score || 0));

  // ===== ۴. تحلیل سبک شخصی =====
  const strategyStyle = state.strategyAnswers.length >= 15 ? analyzeStrategyStyle(state.strategyAnswers) : null;
  const valueStyle = state.valueAnswers.length >= 5 ? analyzeValueStyle(state.valueAnswers) : null;

      // پس از دیدن نتایج، نشست «تمام‌شده» محسوب می‌شود
  // تا «شروع دوباره» تیک‌های قبلی را نیاورد؛ فقط سفر ناتمام قابل ادامه است
  state.journeyFinished = true;
  try {
    const raw = localStorage.getItem('darkhorse_session_v2');
    if (raw) {
      const d = JSON.parse(raw);
      d.journeyFinished = true;
      // تیک‌ها را هم در حافظهٔ ذخیره‌شده قفل نکن برای شروع بعد
      localStorage.setItem('darkhorse_session_v2', JSON.stringify(d));
    }
  } catch (e) {}
  window.__dhJourneyFinished = true;

  state.stage = 'results';
  window.__dhCachedResultsPlace = {
    kind: isBranch ? 'branches' : 'majors',
    scrollY: 0,
    savedAt: Date.now()
  };

  const worldMix = dhComputeWorldSparkMix();
  const cA = worldMix[0] ? worldMix[0].theme.color : '#f0c040';
  const cB = worldMix[1] ? worldMix[1].theme.color : '#38bdf8';
  const sA = worldMix[0] ? worldMix[0].theme.selected : 'rgba(240, 192, 64, 0.22)';
  const sB = worldMix[1] ? worldMix[1].theme.selected : 'rgba(56, 189, 248, 0.18)';
  const topHeroMatch = matched.length > 0 ? matched[0] : null;
  const topWorldsText = worldMix.slice(0, 3).map(m => `${m.theme.title} (${dhFaNum(m.pct)}٪)`).join(' · ') || 'شهر رؤیاها';
  window.__dhIdentityStoryPayload = {
    topMatch: topHeroMatch ? topHeroMatch.name : (isBranch ? 'پروفایل هدایت تحصیلی' : 'پروفایل انتخاب رشته'),
    fitPct: topHeroMatch ? (dhFaNum(Math.round(topHeroMatch.fit_score || 0)) + '٪') : '',
    worldsText: topWorldsText,
    styleText: strategyStyle ? strategyStyle.style : '',
    valueText: valueStyle ? valueStyle.summary : '',
    colorA: cA,
    colorB: cB
  };

  let html = progressHTML('results') + `
    <div class="dh-stage-head">
      <h2 class="dh-stage-title">${isBranch ? 'نتیجه هدایت تحصیلی' : 'نتیجه انتخاب رشته'}</h2>
      <p class="dh-stage-hint">این گزارش بر پایهٔ رتبه نیست؛ نقشه‌ای زنده از فعالیت‌ها، راهبردها و ارزش‌هایی است که به تو انرژی می‌دهند.</p>
    </div>
    <div class="dh-story-id-card" style="--dh-id-a:${sA};--dh-id-b:${sB}">
      <div class="dh-story-id-top">
        <span class="dh-story-id-brand">✦ کارت هویت فردیت · اسب سیاه</span>
        <span style="font-size:.76rem;color:#d6d1c4;font-weight:700;">${dhFaNum(state.likedCodes.length)} جرقه</span>
      </div>
      ${topHeroMatch ? `<div class="dh-story-id-match">هم‌سوترين مسیر با تو: ${escapeHtml(topHeroMatch.name)} (${dhFaNum(Math.round(topHeroMatch.fit_score || 0))}٪)</div>` : `<div class="dh-story-id-match">نقشهٔ انرژی درونی تو</div>`}
      <div class="dh-story-id-pills">
        ${worldMix.slice(0, 3).map(m => `<span class="dh-story-id-pill" style="border-color:${m.theme.border};color:${m.theme.color};">${escapeHtml(m.theme.title)} · ${dhFaNum(m.pct)}٪</span>`).join('')}
        ${strategyStyle ? `<span class="dh-story-id-pill">سبک فکری: ${escapeHtml(strategyStyle.style)}</span>` : ''}
      </div>
      ${valueStyle ? `<p style="margin:0 0 12px 0;color:#dcd6c8;font-size:.82rem;line-height:1.8;"><strong style="color:#f5d472;">قطب‌های ارزشی کلیدی:</strong> ${escapeHtml(valueStyle.summary)}</p>` : ''}
      <button type="button" class="dh-story-share-btn" onclick="if(window.dhShareIdentityStoryCard){window.dhShareIdentityStoryCard()}else if(window.dhCopyShare){window.dhCopyShare()}">دانلود یا اشتراک کارت استوری فردیت من</button>
    </div>

    <p style="text-align:center;color:#b8b2a4;font-size:.9rem;margin:12px 0;">بر اساس <strong style="color:#f0c040;">${dhFaNum(state.likedCodes.length)}</strong> خرده‌انگیزه، <strong style="color:#f5efe2;">${dhFaNum(matched.length)}</strong> ${isBranch ? 'شاخه' : 'رشته'} با فردیت تو هم‌راستا هستند:</p>
  `;

  if (isBranch) {
    let bestName = null;
    let bestScore = null;
    if (matched.length > 0) {
      if (bestBranch) {
        const found = matched.find(m => m.name === bestBranch);
        if (found) {
          bestName = found.name;
          bestScore = found.fit_score;
        }
      }
      if (!bestName) {
        bestName = matched[0].name;
        bestScore = matched[0].fit_score;
      }
    }
    if (bestName) {
      html += `
        <div class="dh-result-hero">
          <p style="color:#f0c040;font-size:1.3rem;font-weight:800;margin-bottom:6px;">بیشترین همخوانی: <span style="color:#f5efe2;font-size:1.45rem;">${escapeHtml(bestName)}</span></p>
          <p style="color:#b8b2a4;font-size:0.88rem;margin:0;">امتیاز همخوانی ${bestScore != null ? dhFaNum(bestScore) + '٪ · ' : ''}نقطهٔ آغاز بررسی آگاهانه است، نه حکم قطعی.</p>
        </div>`;
    }
  }

  if (matched.length === 0) {
    html += `<div class="card dh-surface-card" style="text-align:center;"><p style="color:#d6d1c4;margin:0;">با خرده‌انگیزه‌های انتخاب‌شده، هیچ ${isBranch ? 'شاخه‌ای' : 'رشته‌ای'} به آستانهٔ ۳۰٪ نرسیده است.</p></div>`;
  } else {
    matched.forEach((r, ri) => {
      const score = r.fit_score || 0;
      const raw = r.raw_components || {};
      const mPct = raw.m_score !== undefined ? raw.m_score : (r.avg_components?.m_score || 0);
      const sPct = raw.s_score !== undefined ? raw.s_score : (r.avg_components?.s_score || 0);
      const vPct = raw.v_score !== undefined ? raw.v_score : (r.avg_components?.v_score || 0);

      const microMatch = r.micro_motives_matched || [];
      let motiveMatched = microMatch.length;
      if (mPct != null && Number(mPct) > 0) {
        const fromPct = Math.round((Number(mPct) / 100) * 7);
        if (fromPct > motiveMatched) motiveMatched = fromPct;
      }
      if (motiveMatched < 0) motiveMatched = 0;
      if (motiveMatched > 7) motiveMatched = 7;

      let sparkPillsHtml = '';
      if (microMatch.length > 0) {
        const pills = microMatch.slice(0, 3)
          .map(m => `<span class="dh-result-spark-pill">${escapeHtml(m.description || m.code || m)}</span>`)
          .join('');
        sparkPillsHtml = `<div style="margin:10px 0;">
          <div style="font-size:0.8rem;color:#b8b2a4;margin-bottom:5px;">جرقه‌های مشترک شاخص:</div>
          <div class="dh-result-sparks-wrap">${pills}</div>
        </div>`;
      }

      let warningHtml = '';
      if (r.warnings && r.warnings.length > 0) {
        warningHtml = r.warnings.map(w => `
          <div style="background:rgba(240,192,64,.08);border:1px solid rgba(240,192,64,.35);border-radius:10px;padding:10px 14px;margin-bottom:10px;">
            <span style="color:#f3dfb0;font-weight:600;font-size:.86rem;">توجه: ${escapeHtml(w)}</span>
          </div>`).join('');
      }

      html += `
        <div class="card dh-result-card" data-dh-result-item="1" data-rank="${ri + 1}" style="text-align:right;margin:16px 0;">
          ${warningHtml}
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
            <div style="flex:1;min-width:180px;">
              <span style="display:inline-block;font-size:0.74rem;color:#b8b2a4;margin-bottom:2px;">رتبهٔ همخوانی ${dhFaNum(ri + 1)}</span>
              <h3 style="color:#f5efe2;font-size:1.22rem;margin:0;font-weight:800;">${escapeHtml(r.name)}</h3>
            </div>
            <div style="background:rgba(240,192,64,.16);border:1px solid rgba(240,192,64,.55);color:#f0c040;font-weight:800;padding:5px 13px;border-radius:999px;font-size:0.9rem;">
              ${dhFaNum(score)}٪ همخوانی
            </div>
          </div>

          <div style="margin:12px 0;">
            <div class="dh-bar-row">
              <span style="min-width:74px;">انگیزه</span>
              <div class="dh-bar-track"><div class="dh-bar-fill-m" style="width:${mPct}%"></div></div>
              <span style="min-width:34px;text-align:left;color:#f5efe2;font-weight:600;">${dhFaNum(mPct)}٪</span>
            </div>
            <div class="dh-bar-row">
              <span style="min-width:74px;">راهبرد</span>
              <div class="dh-bar-track"><div class="dh-bar-fill-s" style="width:${sPct}%"></div></div>
              <span style="min-width:34px;text-align:left;color:#f5efe2;font-weight:600;">${dhFaNum(sPct)}٪</span>
            </div>
            <div class="dh-bar-row">
              <span style="min-width:74px;">ارزش</span>
              <div class="dh-bar-track"><div class="dh-bar-fill-v" style="width:${vPct}%"></div></div>
              <span style="min-width:34px;text-align:left;color:#f5efe2;font-weight:600;">${dhFaNum(vPct)}٪</span>
            </div>
          </div>

          ${sparkPillsHtml}

          ${r.personalized_description ? `
            <div class="dh-result-why">${escapeHtml(r.personalized_description)}</div>` : ''}

          ${!isBranch && r.archetype ? `
            <div style="background:#131621;border:1px solid rgba(240,192,64,.28);border-radius:12px;padding:13px;margin:12px 0;text-align:right;">
              <div style="font-size:0.8rem;color:#f0c040;font-weight:700;margin-bottom:4px;">کهن‌الگوی شناختی</div>
              <div style="font-size:1.08rem;font-weight:800;color:#f5efe2;margin-bottom:4px;">${escapeHtml(r.archetype.archetype || '')}</div>
              ${r.archetype.identity_sentence ? `<div style="font-size:0.86rem;color:#d6d1c4;line-height:1.8;">${escapeHtml(r.archetype.identity_sentence)}</div>` : ''}
            </div>` : ''}

          ${!isBranch && r.fulfillment_source ? `
            <div style="background:#131621;border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:12px;margin:10px 0;">
              <div style="color:#f0c040;font-weight:700;font-size:0.82rem;margin-bottom:4px;">منبع رضایت عمیق</div>
              <div style="color:#d6d1c4;font-size:0.88rem;line-height:1.85;">${escapeHtml(r.fulfillment_source)}</div>
            </div>` : ''}

          ${!isBranch && r.archetype && ((r.archetype.dominant_traits && r.archetype.dominant_traits.length) || (r.archetype.dominant_values && r.archetype.dominant_values.length)) ? `
            <div style="margin:10px 0;">
              ${r.archetype.dominant_traits && r.archetype.dominant_traits.length ? `
                <div style="font-size:0.82rem;color:#b8b2a4;margin-bottom:5px;">راهبردهای هم‌راستا:</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;">
                  ${r.archetype.dominant_traits.map(t => `<span style="background:#131621;border:1px solid rgba(255,255,255,.10);padding:3px 10px;border-radius:999px;font-size:0.79rem;color:#e6e1d5;">${escapeHtml(t)}</span>`).join('')}
                </div>` : ''}
              ${r.archetype.dominant_values && r.archetype.dominant_values.length ? `
                <div style="font-size:0.82rem;color:#b8b2a4;margin-bottom:5px;">ارزش‌های هم‌راستا:</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px;">
                  ${r.archetype.dominant_values.map(v => `<span style="background:#131621;border:1px solid rgba(255,255,255,.10);padding:3px 10px;border-radius:999px;font-size:0.79rem;color:#e6e1d5;">${escapeHtml(v)}</span>`).join('')}
                </div>` : ''}
            </div>` : ''}

          ${r.alternative_paths && r.alternative_paths.length > 0 ? `
            <div style="margin:10px 0;">
              <div style="font-size:0.82rem;color:#b8b2a4;margin-bottom:6px;">مسیرهای نزدیک و جایگزین:</div>
              <div style="display:flex;flex-wrap:wrap;gap:8px;">
                ${r.alternative_paths.map(p => {
                  const name = p.branch_name || p.major_name || p.name || '';
                  return name ? `<span style="background:#131621;border:1px solid rgba(240,192,64,.35);padding:4px 12px;border-radius:999px;font-size:0.82rem;color:#f3dfb0;">${escapeHtml(name)}</span>` : '';
                }).filter(Boolean).join('')}
              </div>
            </div>` : ''}

          ${isBranch && r.count ? `<div style="font-size:0.77rem;color:#a9a497;margin-top:8px;">تعداد زیرشاخه‌های تحلیل‌شده: ${dhFaNum(r.count)}</div>` : ''}

          <div style="margin-top:16px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.08);display:flex;flex-direction:column;gap:8px;">
            <button type="button" class="btn btn-primary"
              style="width:100%;"
              onclick="loadDeepCounselItem(${ri}, 'main')">
              توضیح مشاوره‌ای این ${isBranch ? 'شاخه' : 'رشته'}
            </button>
            <button type="button" class="btn"
              style="width:100%;"
              onclick="loadDeepCounselItem(${ri}, 'alternatives')">
              بررسی مسیرهای جایگزین این ${isBranch ? 'شاخه' : 'رشته'}
            </button>
            <div id="dh-counsel-box-${ri}" style="display:none;margin-top:8px;text-align:right;"></div>
          </div>
        </div>`;
    });
  }

    // ذخیره برای مشاوره AI (بدون دکمه سراسری — دکمه زیر هر نتیجه است)
  try {
    state.lastCounselKind = isBranch ? 'branches' : 'majors';
    state.lastCounselTops = (matched || []).map(function (r) {
      return {
        name: r.name,
        score: r.fit_score,
        fit_score: r.fit_score,
        raw_components: r.raw_components || r.avg_components || {},
        avg_components: r.avg_components || r.raw_components || {},
        archetype: r.archetype || null,
        fulfillment_source: r.fulfillment_source || null,
        alternative_paths: r.alternative_paths || [],
        micro_motives_matched: r.micro_motives_matched || []
      };
    });
  } catch (e) {}

  html += `
    <div class="dh-stage-actions" style="margin-top:24px;">
      ${!isBranch && state.branchesResult ? `
        <button type="button" class="btn btn-primary" onclick="displayResults(state.branchesResult, 'branches')">
          مشاهدهٔ نتایج هدایت تحصیلی (شاخه‌های دبیرستان)
        </button>` : ''}
      ${isBranch && state.majorsResult ? `
        <button type="button" class="btn btn-primary" onclick="displayResults(state.majorsResult, 'majors')">
          مشاهدهٔ نتایج رشته‌های دانشگاهی
        </button>` : ''}
      <button type="button" class="btn" onclick="goTo('choice')">بازگشت به صفحهٔ انتخاب تحلیل</button>
      <button type="button" class="btn" onclick="dhGoHomeKeepPlace()">بازگشت به صفحه اول</button>
    </div>

    <div id="feedbackSection" class="card dh-surface-card" style="padding:20px;margin:24px 0 15px 0;text-align:right;">
      <p style="color:#f5efe2;font-weight:800;margin-bottom:14px;font-size:1.05rem;">نظرت دربارهٔ تجربهٔ اسب سیاه چیست؟</p>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۱. چقدر از تجربهٔ کلی این سفر اکتشافی راضی بودی؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q1">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q1', ${i})" style="font-size:1.7rem;cursor:pointer;opacity:0.35;color:#f0c040;" id="star-q1-${i}">★</span>`).join('')}
      </div>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۲. چقدر نتایج با علایق و فردیت واقعی‌ات همخوانی داشت؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q2">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q2', ${i})" style="font-size:1.7rem;cursor:pointer;opacity:0.35;color:#f0c040;" id="star-q2-${i}">★</span>`).join('')}
      </div>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۳. آیا این سامانه را به دوستانت معرفی می‌کنی؟</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;" id="feedback-q3">
        <button type="button" class="btn btn-sm" onclick="setFeedback('q3', 'yes')" id="btn-q3-yes" style="padding:6px 16px;">بله</button>
        <button type="button" class="btn btn-sm" onclick="setFeedback('q3', 'maybe')" id="btn-q3-maybe" style="padding:6px 16px;">شاید</button>
        <button type="button" class="btn btn-sm" onclick="setFeedback('q3', 'no')" id="btn-q3-no" style="padding:6px 16px;">خیر</button>
      </div>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۴. نمایش <strong>شانس قبولی در دانشگاه‌های مختلف</strong> چقدر برایت مفید است؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q4">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q4', ${i})" style="font-size:1.7rem;cursor:pointer;opacity:0.35;color:#f0c040;" id="star-q4-${i}">★</span>`).join('')}
      </div>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۵. چقدر دوست داری <strong>آیندهٔ شغلی و بازار کار</strong> این رشته‌ها را ببینی؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q5">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q5', ${i})" style="font-size:1.7rem;cursor:pointer;opacity:0.35;color:#f0c040;" id="star-q5-${i}">★</span>`).join('')}
      </div>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۶. آیا به انتخاب رشته بر اساس رتبه هم نیاز داری؟</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;" id="feedback-q6">
        <button type="button" class="btn btn-sm" onclick="setFeedback('q6', 'yes')" id="btn-q6-yes" style="padding:6px 16px;">بله</button>
        <button type="button" class="btn btn-sm" onclick="setFeedback('q6', 'no')" id="btn-q6-no" style="padding:6px 16px;">خیر</button>
      </div>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۷. اگر سرویس <strong>کشف رشته‌های متناسب با فردیت</strong> پولی باشد، باز هم استفاده می‌کنی؟</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;" id="feedback-q7">
        <button type="button" class="btn btn-sm" onclick="setFeedback('q7', 'yes')" id="btn-q7-yes" style="padding:6px 16px;">بله</button>
        <button type="button" class="btn btn-sm" onclick="setFeedback('q7', 'maybe')" id="btn-q7-maybe" style="padding:6px 16px;">شاید</button>
        <button type="button" class="btn btn-sm" onclick="setFeedback('q7', 'no')" id="btn-q7-no" style="padding:6px 16px;">خیر</button>
      </div>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۸. اگر بخش <strong>آیندهٔ شغلی و بازار کار</strong> هر رشته با هزینهٔ مناسب ارائه شود، برایت ارزشمند است؟</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;" id="feedback-q8">
        <button type="button" class="btn btn-sm" onclick="setFeedback('q8', 'yes')" id="btn-q8-yes" style="padding:6px 16px;">بله</button>
        <button type="button" class="btn btn-sm" onclick="setFeedback('q8', 'maybe')" id="btn-q8-maybe" style="padding:6px 16px;">شاید</button>
        <button type="button" class="btn btn-sm" onclick="setFeedback('q8', 'no')" id="btn-q8-no" style="padding:6px 16px;">خیر</button>
      </div>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۹. این روش کشف رشته بر پایهٔ فردیت در مقایسه با روش‌های سنتی چقدر برایت تازه و کارآمد بود؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q10">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q10', ${i})" style="font-size:1.7rem;cursor:pointer;opacity:0.35;color:#f0c040;" id="star-q10-${i}">★</span>`).join('')}
      </div>
      <p style="color:#d6d1c4;margin:12px 0 6px 0;">۱۰. چه پیشنهادی برای بهبود سامانه داری؟ (اختیاری)</p>
      <textarea id="feedback-q9" placeholder="پیشنهادت را اینجا بنویس..." style="width:100%;padding:12px;background:#11141e;color:#f5efe2;border:1px solid rgba(255,255,255,.12);border-radius:12px;min-height:70px;font-family:Vazirmatn,sans-serif;"></textarea>
      <button type="button" class="btn btn-primary" style="width:100%;margin-top:14px;" onclick="submitFeedback()">ثبت بازخورد</button>
      <p id="feedback-msg" style="color:#f0c040;margin-top:8px;display:none;">ممنون از همراهی‌ات؛ بازخوردت ثبت شد.</p>
    </div>`;

  
  // share snippet
  const topNames = matched.slice(0, 3).map(x => x.name).join(' · ');
  const shareText = 'از شهر رؤیاها برگشتم.\nمسیرهایی که به من نزدیک‌تر بودن:\n' + topNames + '\n\nبا ' + state.likedCodes.length + ' جرقه از خودم.\n#اسب\u200cسیاه #شهررؤیاها';
  window.__dhShareText = shareText;
  html += `
    <div class="dh-share-box" style="text-align:center;">
      <p style="margin:0 0 10px;color:#f0c040;font-weight:bold;">اشتراک‌گذاری نتیجه</p>
      <p style="margin:0 0 12px;font-size:.8rem;">بدون دادهٔ خصوصی — فقط خلاصهٔ مسیر</p>
      <button class="btn btn-primary" style="width:100%;" onclick="dhCopyShare()">کپی متن نتیجه</button>
    </div>`;
  app.innerHTML = html;
}   
// ==================== تحلیل سبک شخصی (اصلاح‌شده) ====================
// نسخهٔ قبلی فرض می‌کرد شمارهٔ index (۰ تا ۴) در همهٔ ۲۵ سؤال معنی ثابتی دارد
// (مثلاً index=1 همیشه یعنی «آزمایشگر»). این فرض غلط بود — trait_map_v3.json
// نشان می‌دهد همان index در سؤالات مختلف به صفات کاملاً متفاوتی اشاره می‌کند.
// این نسخه از برچسب واقعی هر سؤال-گزینه (state.traitMap) استفاده می‌کند.
function analyzeStrategyStyle(answers) {
  const traitMap = state.traitMap || {};
  const labelCounts = {};
  let totalAnswered = 0;

  answers.forEach((idx, i) => {
    if (idx === undefined || idx === null) return;
    totalAnswered++;
    const qKey = 'S' + String(i + 1).padStart(2, '0');
    const labels = (traitMap[qKey] && traitMap[qKey][String(idx)]) || [];
    labels.forEach(l => { labelCounts[l] = (labelCounts[l] || 0) + 1; });
  });

  if (totalAnswered === 0 || Object.keys(labelCounts).length === 0) {
    return null; // نقشهٔ صفات بارگذاری نشده یا پاسخی ثبت نشده — چیزی نادرست نشان نده
  }

  const sorted = Object.entries(labelCounts).sort((a, b) => b[1] - a[1]);
  const topCount = sorted[0][1];
  const topLabels = sorted.filter(([, c]) => c === topCount).slice(0, 2).map(([l]) => l);
  const percentage = Math.round((topCount / totalAnswered) * 100);

  return {
    style: topLabels.join(' + '),
    icon: '🧭',
    strength: percentage,
    description: percentage >= 40
      ? `صفت غالب در پاسخ‌های شما «${topLabels.join(' و ')}» است (در ${topCount} از ${totalAnswered} سؤال).`
      : `پاسخ‌های شما ترکیب متنوعی از صفات مختلف است؛ برجسته‌ترین آن‌ها «${topLabels.join(' و ')}» است (${topCount} از ${totalAnswered} سؤال).`
  };
}

function analyzeValueStyle(answers) {
  const map = {
    'Q1A':  { pole: 'عمق‌تأثیر',       label: 'عمق‌تأثیر (کمک مستقیم به انسان)',      dim: 'خدمت‌محور و انسانی', icon: '❤️' },
    'Q1B':  { pole: 'گستره‌تأثیر',     label: 'گستره‌تأثیر (اثرگذاری کلان)',           dim: 'رهبر و اثرگذار',      icon: '🌐' },
    'Q2A':  { pole: 'میراث‌مادی',      label: 'میراث‌مادی (خلق اثر ماندگار)',          dim: 'خلاق و نوآور',        icon: '🏗️' },
    'Q2B':  { pole: 'میراث‌انسانی',    label: 'میراث‌انسانی (پرورش و رشد انسان‌ها)',   dim: 'خدمت‌محور و انسانی', icon: '🌱' },
    'Q3A':  { pole: 'عمق‌محور',        label: 'عمق‌محور (تخصص عمیق و مرجعیت)',         dim: 'علم‌گرا و کاشف',      icon: '🎯' },
    'Q3B':  { pole: 'گستره‌محور',      label: 'گستره‌محور (تنوع و یادگیری پیوسته)',    dim: 'خلاق و نوآور',        icon: '🎢' },
    'Q4A':  { pole: 'حقیقت‌جو',        label: 'حقیقت‌جو (کشف دانش ناشناخته)',          dim: 'علم‌گرا و کاشف',      icon: '🔬' },
    'Q4B':  { pole: 'خلق‌زیبایی',      label: 'خلق‌زیبایی (آفرینش هنر و الهام)',       dim: 'خلاق و نوآور',        icon: '🎨' },
    'Q5A':  { pole: 'نظم‌خواه',        label: 'نظم‌خواه (ساختار و برنامهٔ روشن)',      dim: 'پایدار و امنیت‌گرا',  icon: '📐' },
    'Q5B':  { pole: 'آشوب‌پذیر',       label: 'آشوب‌پذیر (پویایی و موقعیت‌های تازه)',  dim: 'مستقل و عمل‌گرا',     icon: '⚡' },
    'Q6A':  { pole: 'مسئولیت‌فردی',    label: 'مسئولیت‌فردی (حمایت از انسان مشخص)',    dim: 'خدمت‌محور و انسانی', icon: '🫂' },
    'Q6B':  { pole: 'مسئولیت‌سیستمی',  label: 'مسئولیت‌سیستمی (هدایت سیستم بزرگ)',     dim: 'رهبر و اثرگذار',      icon: '⚙️' },
    'Q7A':  { pole: 'خالق',            label: 'خالق (ابداع و نوآوری)',                 dim: 'خلاق و نوآور',        icon: '🚀' },
    'Q7B':  { pole: 'ناقل',            label: 'ناقل (انتقال اثربخش دانش)',             dim: 'خدمت‌محور و انسانی', icon: '👨‍🏫' },
    'Q8A':  { pole: 'آزادی‌خواه',      label: 'آزادی‌خواه (آزادی عمل و انعطاف)',       dim: 'مستقل و عمل‌گرا',     icon: '🕊️' },
    'Q8B':  { pole: 'امنیت‌خواه',      label: 'امنیت‌خواه (امنیت و ثبات شغلی)',        dim: 'پایدار و امنیت‌گرا',  icon: '🛡️' },
    'Q9A':  { pole: 'تغییرگر',         label: 'تغییرگر (اصلاح و تحول‌آفرینی)',         dim: 'رهبر و اثرگذار',      icon: '🔥' },
    'Q9B':  { pole: 'محافظ',           label: 'محافظ (پاسداشت ارزش‌های ماندگار)',      dim: 'پایدار و امنیت‌گرا',  icon: '🏰' },
    'Q10A': { pole: 'دیده‌شدن',        label: 'دیده‌شدن (رهبری و تصمیم‌گیری محوری)',   dim: 'رهبر و اثرگذار',      icon: '🧭' },
    'Q10B': { pole: 'بی‌نام‌تأثیرگذار', label: 'بی‌نام‌تأثیرگذار (اثر عمیق بی‌ادعا)',    dim: 'خدمت‌محور و انسانی', icon: '🕯️' },
    'Q11A': { pole: 'داده‌نگر',        label: 'داده‌نگر (تحلیل الگوها و داده‌ها)',     dim: 'علم‌گرا و کاشف',      icon: '📊' },
    'Q11B': { pole: 'انسان‌نگر',       label: 'انسان‌نگر (درک احساس و انگیزهٔ انسان)', dim: 'خدمت‌محور و انسانی', icon: '👥' },
    'Q12A': { pole: 'ریسک‌پذیر',       label: 'ریسک‌پذیر (جسارت برای دستاورد بزرگ)',   dim: 'مستقل و عمل‌گرا',     icon: '🎲' },
    'Q12B': { pole: 'ثبات‌خواه',       label: 'ثبات‌خواه (پیشرفت مطمئن و پایدار)',     dim: 'پایدار و امنیت‌گرا',  icon: '⚓' },
    'Q13A': { pole: 'نتیجه‌فوری',      label: 'نتیجه‌فوری (مشاهدهٔ سریع ثمرهٔ کار)',   dim: 'مستقل و عمل‌گرا',     icon: '⏱️' },
    'Q13B': { pole: 'اثر‌بلندمدت',     label: 'اثر‌بلندمدت (ماندگاری در افق سال‌ها)',  dim: 'رهبر و اثرگذار',      icon: '🏛️' },
    'Q14A': { pole: 'تعلق‌خواه',       label: 'تعلق‌خواه (هم‌افزایی در تیم و سازمان)', dim: 'پایدار و امنیت‌گرا',  icon: '🏢' },
    'Q14B': { pole: 'استقلال‌طلب',     label: 'استقلال‌طلب (خودآیینی و مسیر مستقل)',   dim: 'مستقل و عمل‌گرا',     icon: '🦅' },
    'Q15A': { pole: 'تسلط‌گرا',        label: 'تسلط‌گرا (چیرگی کامل در یک حوزه)',      dim: 'علم‌گرا و کاشف',      icon: '🏆' },
    'Q15B': { pole: 'کنجکاوی‌گرا',     label: 'کنجکاوی‌گرا (کشف و یادگیری بی‌پایان)',   dim: 'علم‌گرا و کاشف',      icon: '🌌' }
  };

  let normalizedCodes = [];
  if (Array.isArray(answers)) {
    normalizedCodes = answers
      .map(a => String(a || '').trim().toUpperCase())
      .filter(Boolean);
  } else if (answers && typeof answers === 'object') {
    Object.entries(answers).forEach(([k, v]) => {
      const rawKey = String(k || '').trim().toUpperCase();
      const rawVal = String(v || '').trim().toUpperCase();
      if (!rawVal) return;
      if (rawVal.startsWith('Q')) {
        normalizedCodes.push(rawVal);
      } else if (rawKey.startsWith('Q') && (rawVal === 'A' || rawVal === 'B')) {
        normalizedCodes.push(rawKey + rawVal);
      }
    });
  }

  const selected = normalizedCodes.map(code => map[code] || { pole: code, label: code, dim: 'متعادل', icon: '✨' });
  const uniquePoles = [...new Set(selected.map(s => s.pole))];
  const dimCounts = {};
  selected.forEach(s => {
    if (s.dim) dimCounts[s.dim] = (dimCounts[s.dim] || 0) + 1;
  });
  const sortedDims = Object.entries(dimCounts).sort((a, b) => b[1] - a[1]);
  const topDims = sortedDims.slice(0, 2).map(([d]) => d);
  const dominantStyle = topDims.length ? topDims.join(' · ') : 'متعادل';

  return {
    style: dominantStyle,
    dimension: dominantStyle,
    values: selected.slice(0, 5),
    summary: uniquePoles.slice(0, 4).join('، '),
    description: topDims.length
      ? `جهت‌گیری ارزشی غالب شما «${dominantStyle}» است که نشان می‌دهد چه نوع معنا و رضایتی برایتان اصالت دارد.`
      : 'ارزش‌های بنیادین شما نشان می‌دهد که چه چیزی به کارتان معنا می‌بخشد.'
  };
}

// ==================== بازخورد (بدون تغییر) ====================
const feedback = {};
function setFeedback(question, value) {
  feedback[question] = value;
  if (typeof value === 'number') {
    for (let i = 1; i <= 5; i++) {
      const star = document.getElementById(`star-${question}-${i}`);
      if (star) star.style.opacity = i <= value ? '1' : '0.3';
    }
  }
  if (['q3','q6','q7','q8'].includes(question)) {
    ['yes','maybe','no'].forEach(v => {
      const btn = document.getElementById(`btn-${question}-${v}`);
      if (btn) btn.style.border = v === value ? '2px solid #f0c040' : 'none';
    });
  }
}

async function submitFeedback() {
  feedback['q9'] = document.getElementById('feedback-q9')?.value || '';
  const allFeedback = {
    session_id: state.sessionId || 'unknown',
    timestamp: new Date().toISOString(),
    likedCodes: state.likedCodes.length,
    strategyAnswers: state.strategyAnswers.length,
    valueAnswers: state.valueAnswers.length,
    feedback: feedback
  };
  let savedLocally = false;
  try {
    const existing = JSON.parse(localStorage.getItem('darkhorse_feedback_v2') || '[]');
    existing.push(allFeedback);
    localStorage.setItem('darkhorse_feedback_v2', JSON.stringify(existing));
    savedLocally = true;
  } catch (e) { console.error(e); }
  let serverSuccess = false;
  try {
    const res = await fetch(API_BASE + '/api/feedback/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(allFeedback)
    });
    if (res.ok) serverSuccess = true;
  } catch (e) { console.warn(e); }
  const msgEl = document.getElementById('feedback-msg');
  if (msgEl) {
    msgEl.style.display = 'block';
    if (savedLocally) {
      msgEl.textContent = serverSuccess ? '✅ ممنون از بازخوردت! نظرت با موفقیت به سرور ارسال شد.' : '✅ بازخورد شما در دستگاه شما ذخیره شد. (ارسال به سرور ممکن نشد.)';
    } else {
      msgEl.textContent = '⚠️ متأسفانه ذخیره‌سازی بازخورد با مشکل مواجه شد.';
      msgEl.style.color = '#ff6b6b';
    }
  }
}

async function showAllFeedback() {
  try {
    const res = await fetch(API_BASE + '/api/feedback/all');
    const data = await res.json();
    const feedbackData = data.feedbacks || [];
    if (feedbackData.length === 0) { alert('هنوز هیچ بازخوردی ثبت نشده است.'); return; }
    let html = `<h2>📋 بازخوردهای ثبت‌شده (${feedbackData.length} مورد)</h2>
      <button class="btn" onclick="dhGoHomeKeepPlace()" style="margin-bottom:15px;">⬅️ بازگشت به صفحه اصلی</button>
      <button class="btn" onclick="copyAllFeedbackServer()" style="margin-bottom:15px;background:#d4af37;color:#000;">📋 کپی همه به صورت JSON</button>
      <div style="text-align:right;">`;
    feedbackData.forEach(fb => {
      const date = new Date(fb.timestamp).toLocaleString('fa-IR');
      html += `<div class="card" style="text-align:right;margin-bottom:15px;">
        <p style="color:#888;font-size:0.8rem;">📅 ${date} | 🆔 ${escapeHtml(fb.session_id || '؟')}</p>
        <p style="color:#c9b896;">✨ خرده‌انگیزه‌ها: <strong>${fb.likedCodes || '؟'}</strong> عدد</p>
        <p style="color:#c9b896;">🧭 پاسخ‌های راهبرد: <strong>${fb.strategyAnswers || '؟'}</strong> از ۲۵</p>
        <p style="color:#c9b896;">⚖️ پاسخ‌های ارزشی: <strong>${fb.valueAnswers || '؟'}</strong> از ۱۵</p>
        <hr style="border-color:#333;margin:8px 0;">
        <p style="color:#f0c040;">۱. رضایت از تجربه: ${'⭐'.repeat(fb.feedback?.q1 || 0)}</p>
        <p style="color:#f0c040;">۲. همخوانی با فردیت: ${'⭐'.repeat(fb.feedback?.q2 || 0)}</p>
        <p style="color:#f0c040;">۳. معرفی به دوست: ${fb.feedback?.q3 === 'yes' ? '✅ بله' : fb.feedback?.q3 === 'maybe' ? '🤷 شاید' : '❌ خیر'}</p>
        <p style="color:#f0c040;">۴. ارزشمندی شانس قبولی: ${'⭐'.repeat(fb.feedback?.q4 || 0)}</p>
        <p style="color:#f0c040;">۵. علاقه به آینده شغلی: ${'⭐'.repeat(fb.feedback?.q5 || 0)}</p>
        <p style="color:#f0c040;">۶. نیاز به روش سنتی: ${fb.feedback?.q6 === 'yes' ? '✅ بله' : '❌ خیر'}</p>
        <p style="color:#f0c040;">۷. کشف فردیت پولی: ${fb.feedback?.q7 === 'yes' ? '✅ بله' : fb.feedback?.q7 === 'maybe' ? '🤷 شاید' : '❌ خیر'}</p>
        <p style="color:#f0c040;">۸. آینده شغلی پولی: ${fb.feedback?.q8 === 'yes' ? '✅ بله' : fb.feedback?.q8 === 'maybe' ? '🤷 شاید' : '❌ خیر'}</p>
        <p style="color:#f0c040;">۹. نوآورانه بودن: ${'⭐'.repeat(fb.feedback?.q10 || 0)}</p>
        <p style="color:#f0c040;">۱۰. پیشنهاد بهبود: ${escapeHtml(fb.feedback?.q9) || 'ندارد'}</p>
      </div>`;
    });
    html += `</div><button class="btn" onclick="dhGoHomeKeepPlace()">⬅️ بازگشت به صفحه اصلی</button>`;
    app.innerHTML = html;
  } catch (e) { alert('نتوانستیم بازخوردها را از سرور بخوانیم.'); }
}

async function copyAllFeedbackServer() {
  try {
    const res = await fetch(API_BASE + '/api/feedback/all');
    const data = await res.json();
    await navigator.clipboard.writeText(JSON.stringify(data.feedbacks, null, 2));
    alert('✅ تمام بازخوردها به صورت JSON کپی شد.');
  } catch (e) { alert('❌ خطا در کپی.'); }
}

// ==================== RESET & INIT ====================
function resetJourney() {
  if (isPreResultsInProgress()) {
    if (!confirm('هنوز نتایج را ندیده‌ای. سفر فعلی پاک شود؟')) return;
  }
  const gateOk = dhEnsureServerQuotaGate({
    mode: 'new',
    sessionId: '',
    isFinished: true,
    onAuthorized: function (approvedId) {
      fullResetState(true);
      try { localStorage.removeItem('dh_quota_charged_session_v1'); } catch (_) {}
      if (approvedId) {
        state.sessionId = String(approvedId);
      } else if (window.DHQuotaEnforcement && typeof window.DHQuotaEnforcement.ensureJourneySession === 'function') {
        try { state.sessionId = window.DHQuotaEnforcement.ensureJourneySession(); } catch (_) {}
      }
      state.stage = 'splash';
      window.__dhInJourney = true;
      try { if (window.DHShell && typeof window.DHShell.setActiveTab === 'function') window.DHShell.setActiveTab('journey'); } catch (_) {}
      saveSession();
      render();
    }
  });
  if (!gateOk) return;
  fullResetState(true);
  state.stage = 'splash';
  window.__dhInJourney = true;
  saveSession();
  render();
}
window.resetJourney = resetJourney;

// با خروج/بستن اپ، سشن وسط سفر حفظ شود
function persistSessionOnExit() {
  try {
    if (typeof state !== 'undefined' && state && !state.journeyFinished) {
      if (typeof saveSession === 'function') saveSession();
    }
  } catch (e) {}
}
window.addEventListener('pagehide', persistSessionOnExit);
window.addEventListener('beforeunload', persistSessionOnExit);
document.addEventListener('visibilitychange', function () {
  if (document.visibilityState === 'hidden') persistSessionOnExit();
});



async function init() {
  const saved = localStorage.getItem('darkhorse_session_v2');
  let restored = false;
  if (saved) {
    try {
      const data = JSON.parse(saved);
      window.__dhSavedSession = data;
      window.__dhJourneyFinished = !!data.journeyFinished;
      window.__dhHasSavedSession = !data.journeyFinished;
      // سفر ناتمام: کامل در state بارگذاری شود تا با رفرش/خروج پاک نشود
      if (!data.journeyFinished && data.stage) {
        const mid = ['realm', 'subRealm', 'narrowPath', 'introSwipe', 'swipe',
          'introStrategies', 'strategies', 'introValues', 'values', 'choice'];
        if (mid.indexOf(data.stage) >= 0) {
          restored = loadSession();
          window.__dhShouldResumeJourney = true;
        }
      }
    } catch (e) {
      window.__dhHasSavedSession = false;
      window.__dhShouldResumeJourney = false;
    }
  } else {
    window.__dhHasSavedSession = false;
    window.__dhShouldResumeJourney = false;
  }
  // رندر فوری صفحهٔ خانه بدون معطلی برای ۲۸۱ کیلوبایت فایل‌های JSON
  if (window.__dhJourneyStarting || window.__dhInJourney) {
    await ensureJourneyDataLoaded();
    render();
    return;
  }
  if (!restored) {
    state.stage = 'splash';
    state.history = [];
  }
  if (window.DHShell && typeof window.DHShell.renderHome === 'function') {
    window.DHShell.renderHome();
  } else {
    render();
  }

  // در محیط تست/سند کامل‌شده بلافاصله بارگذاری کن؛ در مرورگر واقعی بعد از اتمام بالا آمدن خانه
  if (typeof document === 'undefined' || document.readyState === 'complete') {
    await ensureJourneyDataLoaded();
  } else {
    let warmed = false;
    const warmOnce = () => {
      if (warmed) return;
      warmed = true;
      const run = () => { ensureJourneyDataLoaded().catch(() => {}); };
      if (typeof window.requestIdleCallback === 'function') {
        window.requestIdleCallback(run, { timeout: 1200 });
      } else {
        setTimeout(run, 120);
      }
    };
    window.addEventListener('load', warmOnce, { once: true });
    setTimeout(warmOnce, 2000);
  }
}
init();
