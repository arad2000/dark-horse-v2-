// ==================== Dark Horse App V2.0 ====================
// تغییرات نسبت به V1.0:
//   • API_BASE → dark-horse-v2.onrender.com
//   • Endpointها → /api/v2/darkhorse/...
//   • فایل سوالات → questions_v2.json
//   • اضافه شدن صفحه انتخاب بین هدایت تحصیلی و انتخاب رشته دانشگاهی

const API_BASE = 'https://dark-horse-v2.onrender.com';
const DATA_BASE = './data/';

// ==================== GLOBAL STATE ====================
const state = {
  sessionId: null,
  stage: 'manifesto',
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
    completedPaths: [...state.completedPaths],
    completedSubRealms: [...state.completedSubRealms]
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
    state.stage = data.stage || 'manifesto';
    state.history = data.history || [];
    state.swipeIndex = data.swipeIndex || 0;
    state.totalSwipes = data.totalSwipes || 0;
    state.completedPaths = new Set(data.completedPaths || []);
    state.completedSubRealms = new Set(data.completedSubRealms || []);
    state.likedCodesSet = new Set(data.likedCodes || []);
    return true;
  } catch (e) { return false; }
}

function clearSession() { localStorage.removeItem('darkhorse_session_v2'); }

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

// ==================== NAVIGATION ====================
function goTo(stage) {
  state.history.push(state.stage);
  state.stage = stage;
  saveSession();
  render();
}

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
}

// ==================== RENDER ====================
function render() {
  switch (state.stage) {
    case 'manifesto': renderManifesto(); break;
    case 'guide': renderGuide(); break;
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
    case 'choice': renderChoice(); break;    // <-- صفحه جدید انتخاب
    case 'results': break; // نتایج توسط displayResults رندر می‌شود
  }
}

// ==================== MANIFESTO (بدون تغییر) ====================
function renderManifesto() {
  app.innerHTML = `
    <div style="text-align:center;padding:20px;">
      <div style="font-size:3rem;margin-bottom:15px;">🐴</div>
      <h1 style="color:#f0c040;font-size:1.6rem;margin-bottom:10px;">اسب سیاه</h1>
      <p style="color:#b0a080;font-style:italic;margin-bottom:20px;">انتخاب مسیر با معیار خودت، نه فقط رتبه‌ات</p>
      <div class="card" style="text-align:right;">
        <p style="color:#b0a080;line-height:2.2;font-size:0.9rem;margin-bottom:15px;">
          <strong style="color:#f0c040;">«موفقیت از تقلید دیگران به دست نمی‌آید؛ از شناخت فردیت و ساختن مسیر شخصی می‌آید.»</strong>
          <br><span style="color:#888;font-size:0.8rem;">— تاد رز، کتاب «اسب سیاه» (پروژه هاروارد)</span>
        </p>

        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">مشکل از کجاست؟</p>
        <p style="color:#b0a080;line-height:2.2;font-size:0.9rem;margin-bottom:15px;">
          هر سال هزاران دانش‌آموز با این سؤال روبه‌رو می‌شوند: <strong>«چه رشته‌ای بخوانم؟»</strong><br>
          پاسخ‌های رایج معمولاً بر پایهٔ رتبه، پرستیژ یا بازار کار کلیشه‌ای است:
          «با این رتبه این رشته قبول می‌شوی»، «برو پزشکی چون اعتبار دارد»، «کامپیوتر بازار دارد».<br>
          این پاسخ‌ها <strong>فردیت تو را نادیده می‌گیرند</strong>؛
          نمی‌پرسند از چه چیزی واقعاً انرژی می‌گیری، چطور فکر می‌کنی، و چه چیزی به کار و زندگی‌ات معنا می‌دهد.
        </p>

        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">راه‌حل این سامانه</p>
        <p style="color:#b0a080;line-height:2.2;font-size:0.9rem;margin-bottom:15px;">
          بر اساس پژوهش <strong style="color:#f0c040;">Dark Horse</strong> در هاروارد و کتاب
          <strong style="color:#f0c040;">«اسب سیاه»</strong> نوشتهٔ تاد رز و اگی اوگاس،
          این سامانه به‌جای پرسیدن «چه نمره‌ای آوردی؟» می‌پرسد:<br>
          <strong style="color:#f0c040;">«از چه چیزی واقعاً انرژی می‌گیری؟»</strong>
        </p>

        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">سه لایهٔ شناخت</p>
        <p style="color:#b0a080;line-height:2.2;font-size:0.9rem;margin-bottom:5px;">
          🧩 <strong style="color:#f0c040;">خرده‌انگیزه‌ها</strong> — جرقه‌های لذت روزمره (پایهٔ اصلی انتخاب)<br>
          🧭 <strong style="color:#f0c040;">راهبردهای شخصی</strong> — سبک فکر و یادگیری (قابل رشد و یادگیری)<br>
          ⚖️ <strong style="color:#f0c040;">ارزش‌های بنیادین</strong> — آنچه به کارت معنا و رضایت عمیق می‌دهد
        </p>

        <p style="color:#d4af37;line-height:2.2;font-size:0.9rem;margin-top:15px;">
          <strong>این تست شخصیت نیست؛ یک سفر کوتاه برای کشف خودت است.</strong><br>
          نتیجه، پیشنهاد بر اساس فردیت توست — نه حکم نهایی بر اساس یک عدد.
        </p>
      </div>
      <button class="btn btn-primary" style="margin-top:20px;width:100%;" onclick="goTo('guide')">شروع سفر اکتشافی</button>
    </div>`;
}

// ==================== GUIDE ====================
function renderGuide() {
  app.innerHTML = `
    <div style="text-align:right;padding:10px;">
      <h2 style="color:#f0c040;text-align:center;">قبل از شروع</h2>
      <p style="color:#b0a080;line-height:2.2;text-align:center;">
        این یک تست شخصیت نیست؛
        <strong style="color:#f0c040;">سفری برای شناخت انگیزه‌ها، سبک فکر و ارزش‌های خودت</strong> است.
        با آرامش و صداقت پیش برو. پاسخ درست یا غلط وجود ندارد.
      </p>

      <div class="card" style="margin-top:15px;">
        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">مسیر سفر چگونه است؟</p>

        <p style="color:#b0a080;line-height:2.2;">
          <strong style="color:#f0c040;">۱) خرده‌انگیزه‌ها — پایهٔ اصلی</strong><br>
          وارد «شهر رؤیاها» می‌شوی: چند حوزه و داخل هر کدام، فعالیت‌های ملموس.
          از میان <strong>بیش از ۱۱۰۰ خرده‌انگیزه</strong>، آن‌هایی را که واقعاً به تو انرژی می‌دهند ❤️ بزن.
          پیشنهاد: حدود <strong>۲۰ تا ۸۰</strong> مورد را انتخاب کن تا تصویر دقیق‌تری از خودت ساخته شود.
        </p>

        <p style="color:#b0a080;line-height:2.2;">
          <strong style="color:#f0c040;">۲) راهبردهای شخصی — سبک تو</strong><br>
          حدود ۲۵ موقعیت کوتاه: چطور مسئله حل می‌کنی و یاد می‌گیری.
          راهبردها قابل یادگیری‌اند؛ اگر با رشته‌ای ناهمسو بود، یعنی
          <strong>هشدار برای رشد</strong>، نه رد شدن.
        </p>

        <p style="color:#b0a080;line-height:2.2;">
          <strong style="color:#f0c040;">۳) ارزش‌های بنیادین — معنای کار</strong><br>
          ۱۵ دوگانهٔ ساده (مثلاً عمق تأثیر یا گستره تأثیر).
          این بخش کمک می‌کند بفهمی رضایت بلندمدت برای تو از کجا می‌آید.
        </p>
      </div>

      <div class="card" style="margin-top:15px;">
        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">وزن‌ها در نتیجهٔ نهایی</p>
        <p style="color:#b0a080;line-height:2.2;">
          <strong style="color:#f0c040;">انتخاب رشتهٔ دانشگاهی</strong><br>
          خرده‌انگیزه ۵۵٪ | ارزش ۳۰٪ | راهبرد ۱۵٪
        </p>
        <p style="color:#b0a080;line-height:2.2;">
          <strong style="color:#f0c040;">هدایت شاخهٔ دبیرستان</strong><br>
          خرده‌انگیزه ۶۰٪ | راهبرد ۲۰٪ | ارزش ۲۰٪
        </p>
        <p style="color:#b0a080;line-height:2.2;margin-top:8px;">
          چرا؟ چون انگیزه و ارزش پایدارترند.
          راهبرد را می‌توان در طول زمان ساخت و تقویت کرد.
        </p>
      </div>

      <div class="card" style="margin-top:15px;">
        <p style="color:#f0c040;font-weight:bold;font-size:1rem;margin-bottom:8px;">در پایان چه می‌بینی؟</p>
        <p style="color:#b0a080;line-height:2.2;">
          می‌توانی نتیجه را برای <strong>شاخهٔ دبیرستان</strong> یا
          <strong>رشته‌های دانشگاهی</strong> ببینی.
        </p>
        <p style="color:#d4af37;line-height:2.2;margin-top:10px;">
          اینجا قرار نیست کسی به‌جای تو تصمیم بگیرد.
          قرار است خودت کشف کنی از چه چیزی انرژی می‌گیری
          و مسیر را بر اساس انگیزه و فردیت خودت انتخاب کنی.
        </p>
      </div>

      <button class="btn btn-primary" style="margin-top:20px;width:100%;" onclick="goTo('splash')">ادامه</button>
      <button class="btn" style="margin-top:10px;width:100%;" onclick="goTo('manifesto')">بازگشت</button>
    </div>`;
}

// ==================== SPLASH ====================
function renderSplash() {
  const hasSession = localStorage.getItem('darkhorse_session_v2');
  let actionButtonHTML = '';
  if (hasSession) {
    actionButtonHTML = `<button class="btn btn-primary" onclick="resumeJourney()">📋 ادامهٔ سفر ناتمام</button>`;
  } else {
    actionButtonHTML = `<button class="btn btn-primary" onclick="startNewJourney()">ادامه</button>`;
  }
  app.innerHTML = `
    <div style="position:relative;display:inline-block;margin-bottom:20px;">
      <div style="font-size:6rem;filter:blur(6px) brightness(0.6);opacity:0.4;position:absolute;top:-20px;left:50%;transform:translateX(-50%);">🐴</div>
      <div style="font-size:4rem;position:relative;z-index:1;text-shadow:0 0 30px #d4af37;">🐴</div>
    </div>
    <h1 style="margin-top:0;">اسب سیاه</h1>
    <div class="card">
      <p class="quote">«شهر رؤیاها، جایی که هر کودکی قبل از خواب به آن سفر می‌کرد...»</p>
      <p>یادت می‌آید بچه که بودی، چشمانت را می‌بستی و خودت را جای یک نفر دیگر تصور می‌کردی؟ یک روز دکتر بودی، یک روز خلبان، یک روز نقاش، یک روز هم کاشف سیارات دور. آن تصویرها، آن حس‌ها، هنوز هم جایی در عمق وجودت زنده‌اند.</p>
      <p>حالا وقت آن رسیده که دوباره به آن شهر برگردی. اما این بار، نه با خیال کودکانه، که با نگاه دقیق یک بزرگسال. در «شهر رؤیاها»، شش محله وجود دارد. هر محله، بوی خاصی می‌دهد، نوری متفاوت دارد، و آدم‌هایش کاری می‌کنند که انگار برای آن به دنیا آمده‌اند.</p>
      <p><strong>کدام یک از این محله‌ها، هنوز هم قلبت را به تپش می‌اندازد؟</strong></p>
      ${actionButtonHTML}
    </div>
    <button class="btn" onclick="showAllFeedback()" style="margin-top:10px;font-size:0.8rem;background:#333;color:#aaa;">📋 مشاهده بازخوردها (مدیر)</button>`;
}

function startNewJourney() {
  clearSession();
  state.sessionId = crypto.randomUUID ? crypto.randomUUID() : 'id-' + Date.now();
  state.stage = 'realm'; state.history = [];
  state.selectedRealms = []; state.selectedSubRealms = []; state.selectedNarrowPaths = [];
  state.likedCodes = []; state.strategyAnswers = []; state.valueAnswers = []; state.currentQuestion = 0; state.currentValueQuestion = 0;
  state.likedCodesSet.clear(); state.completedPaths.clear(); state.completedSubRealms.clear();
  state.swipeIndex = 0; state.totalSwipes = 0;
  state.lastPayload = null; state.cachedMotives = null;
  state.retryCount = 0;
  state.majorsResult = null; state.branchesResult = null; // پاک کردن کش
  saveSession();
  render();
}

function resumeJourney() {
  if (loadSession()) {
    if (state.stage === 'results' || state.stage === 'splash' || state.stage === 'manifesto' || state.stage === 'guide') {
      state.stage = 'realm';
    } else if (state.stage === 'swipe') {
      state.stage = 'introSwipe';
    }
    render();
  }
}

// ==================== REALM / SUB-REALM / NARROW PATH (بدون تغییر) ====================
// (بخش‌های REALMS, SUB_REALMS, NARROW_PATHS باید در اینجا تعریف شوند.
//  برای اختصار، تعریف آن‌ها حذف شده اما در کد واقعی باید وجود داشته باشند)

function renderRealm() {
  const maxSelect = Math.min(3, REALMS.length);
  let html = `<h2>🌃 شهر رؤیاها</h2>
    <p style="color:#b0a080;">کدام محله‌ها تو را صدا می‌زنند؟ (۱ تا ${maxSelect})</p>
    <p style="color:#f0c040;">💛 جرقه‌های تو: <strong>${state.likedCodes.length}</strong></p>
    <div class="grid" id="realmGrid">`;
  REALMS.forEach(r => {
    html += `<div class="option ${state.selectedRealms.includes(r.id) ? 'selected' : ''}" onclick="toggleRealm('${r.id}')">
      <span class="option-icon">${r.icon}</span><strong>${escapeHtml(r.name)}</strong>
      <p style="color:#d4af37;">${escapeHtml(r.motto)}</p><small>${escapeHtml(r.description)}</small></div>`;
  });
  html += `</div>
    <button class="btn" onclick="goBack()">⬅️ بازگشت</button>
    <button class="btn btn-primary" onclick="if(state.selectedRealms.length>=1) goTo('subRealm')">ادامه</button>`;
  app.innerHTML = html;
}

function toggleRealm(id) {
  const idx = state.selectedRealms.indexOf(id);
  if (idx > -1) state.selectedRealms.splice(idx, 1);
  else if (state.selectedRealms.length < 3) state.selectedRealms.push(id);
  renderRealm();
}

function renderSubRealm() {
  const subs = [];
  state.selectedRealms.forEach(realmId => { if (SUB_REALMS[realmId]) subs.push(...SUB_REALMS[realmId]); });
  const maxSelect = Math.min(3 * state.selectedRealms.length, subs.length);
  let html = `<h2>راهروهای محله</h2>
    <p style="color:#b0a080;">از میان این گذرها، کدام یک تو را به عمق می‌کشاند؟</p>
    <p style="font-size:0.85rem;color:#888;">(۱ تا ${maxSelect} گذر انتخاب کن)</p>
    <div class="grid" id="subGrid">`;
  subs.forEach(s => {
    const isComplete = state.completedSubRealms.has(s.id);
    html += `<div class="option ${state.selectedSubRealms.includes(s.id) ? 'selected' : ''} ${isComplete ? 'disabled' : ''}" 
      onclick="${isComplete ? '' : `toggleSub('${s.id}', ${maxSelect})`}" 
      style="${isComplete ? 'opacity:0.5;pointer-events:none;' : ''}">
      <span class="option-icon">${s.icon}</span>
      <strong>${escapeHtml(s.name)} ${isComplete ? '✅' : ''}</strong>
      <p style="color:#d4af37;">«${escapeHtml(s.motto)}»</p><small>${escapeHtml(s.description)}</small></div>`;
  });
  html += `</div>
    <button class="btn" onclick="goBack()">⬅️ بازگشت</button>
    <button class="btn btn-primary" onclick="if(state.selectedSubRealms.length>=1) goTo('narrowPath')">ادامه</button>`;
  app.innerHTML = html;
}

function toggleSub(id, maxSelect) {
  const idx = state.selectedSubRealms.indexOf(id);
  if (idx > -1) state.selectedSubRealms.splice(idx, 1);
  else if (state.selectedSubRealms.length < maxSelect) state.selectedSubRealms.push(id);
  renderSubRealm();
}

function renderNarrowPath() {
  const paths = [];
  state.selectedSubRealms.forEach(subId => { if (NARROW_PATHS[subId]) paths.push(...NARROW_PATHS[subId]); });
  let html = `<h2>مسیرهای باریک</h2>
    <p style="color:#b0a080;">کدام مسیر تو را صدا می‌زند؟</p>
    <div class="grid" id="pathGrid">`;
  paths.forEach(p => {
    const isComplete = state.completedPaths.has(p.id);
    html += `<div class="option ${state.selectedNarrowPaths.includes(p.id) ? 'selected' : ''} ${isComplete ? 'disabled' : ''}" 
      onclick="${isComplete ? '' : `togglePath('${p.id}')`}" 
      style="${isComplete ? 'opacity:0.5;pointer-events:none;' : ''}">
      <span class="option-icon">${p.icon}</span>
      <strong>${escapeHtml(p.name)} ${isComplete ? '✅' : ''}</strong>
      <p style="color:#d4af37;">${escapeHtml(p.description)}</p></div>`;
  });
  html += `</div>
    <button class="btn" onclick="goBack()">⬅️ بازگشت</button>
    <button class="btn btn-primary" onclick="if(state.selectedNarrowPaths.length>=1) goTo('introSwipe')">مشاهدهٔ جرقه‌های انرژی</button>`;
  app.innerHTML = html;
}

function togglePath(id) {
  const idx = state.selectedNarrowPaths.indexOf(id);
  if (idx > -1) state.selectedNarrowPaths.splice(idx, 1);
  else state.selectedNarrowPaths.push(id);
  renderNarrowPath();
}

// ==================== SWIPE (بدون تغییر) ====================
function renderIntroSwipe() {
  app.innerHTML = `
    <h2>🔥 به عمیق‌ترین لایه وجودت رسیدی!</h2>
    <div class="card">
      <p style="color:#b0a080;line-height:2.2;">بر اساس تمام انتخاب‌هایی که تا اینجا کردی — از قلمروها و زیرقلمروها تا مسیرهای باریک — حالا درست در همان جایی ایستاده‌ای که <strong>ناخودآگاه و خودآگاهت</strong> به هم گره خورده‌اند.</p>
      <p style="color:#d4af37;">در این مرحله، فعالیت‌های جزئی‌ای را می‌بینی. آن‌هایی که <strong>واقعاً</strong> به تو انرژی می‌دهند، ❤️ بزن. هرچه دقیق‌تر انتخاب کنی، خودِ واقعی‌ات شفاف‌تر کشف خواهد شد.</p>
      <button class="btn btn-primary" style="width:100%;margin-top:20px;" onclick="loadSwipeCards()">🚀 شروع جرقه‌های انرژی</button>
      <button class="btn" style="width:100%;margin-top:8px;" onclick="goBack()">⬅️ بازگشت</button>
    </div>`;
}

async function loadSwipeCards() {
  const majorCodes = [];
  state.selectedNarrowPaths.forEach(pathId => {
    const path = findNarrowPath(pathId);
    if (path?.majorCodes) majorCodes.push(...path.majorCodes);
  });
  if (majorCodes.length === 0) { alert('هیچ جرقه‌ای نیست.'); goBack(); return; }
  try {
    let all;
    if (state.cachedMotives) {
      all = state.cachedMotives;
    } else {
      const res = await fetch(DATA_BASE + 'micro_motives.json');
      all = await res.json();
      state.cachedMotives = all;
    }
    state.swipeCards = all.filter(m =>
      majorCodes.some(prefix => m.code.startsWith(prefix)) && !state.likedCodesSet.has(m.code)
    );
    state.swipeIndex = 0; state.totalSwipes = state.swipeCards.length;
    goTo('swipe');
  } catch (e) { alert('خطا در بارگذاری جرقه‌ها.'); }
}

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
  state.selectedNarrowPaths.forEach(pathId => { if (state.swipeCards.length === 0 || state.swipeIndex >= state.swipeCards.length) state.completedPaths.add(pathId); });
  state.selectedSubRealms.forEach(subId => { const allPaths = NARROW_PATHS[subId] || []; if (allPaths.length > 0 && allPaths.every(p => state.completedPaths.has(p.id))) state.completedSubRealms.add(subId); });
}

function renderSwipe() {
  if (state.likedCodes.length >= 80) {
    updateCompletionStatus();
    setTimeout(() => goTo('introStrategies'), 500);
    app.innerHTML = `<h2>🎉 تبریک!</h2><div class="card"><p>حداکثر جرقه! در حال انتقال...</p></div>`;
    return;
  }
  if (state.swipeIndex >= state.swipeCards.length && state.likedCodes.length < 20) {
    const remaining = 20 - state.likedCodes.length;
    app.innerHTML = `<h2>🔥 جرقه‌های انرژی</h2>
      <div style="color:#f0c040;margin:20px 0;">💛 <strong>${state.likedCodes.length}</strong> جرقه</div>
      <div class="card"><p style="color:#f0c040;">⚠️ هنوز ${remaining} جرقهٔ دیگر نیاز داری.</p>
      <button class="btn btn-primary" style="width:100%;margin-top:15px;" onclick="goBack()">🔙 بازگشت به قلمروها</button></div>`;
    return;
  }
  if (state.swipeIndex >= state.swipeCards.length && state.likedCodes.length >= 20) {
    updateCompletionStatus();
    app.innerHTML = `<h2>🔥 جرقه‌های انرژی</h2>
      <div style="color:#f0c040;margin:20px 0;">💛 <strong>${state.likedCodes.length}</strong> جرقه</div>
      <div class="card"><p style="color:#b0a080;">🌟 شما به حداقل جرقه‌ها رسیدید! اما هرچه جرقه‌های بیشتری بزنی، خودِ واقعی‌ات را دقیق‌تر کشف می‌کنی.</p>
      <button class="btn btn-primary" style="width:100%;margin-top:15px;" onclick="finishSwipe()">🚀 ورود به لایهٔ دوم</button>
      <button class="btn" style="width:100%;margin-top:8px;" onclick="goBack()">🔙 جرقه‌های بیشتر</button></div>`;
    return;
  }

  const card = state.swipeCards[state.swipeIndex];
  const progress = state.totalSwipes > 0 ? ((state.swipeIndex + 1) / state.totalSwipes) * 100 : 0;
  const canFinish = state.likedCodes.length >= 20;
  const remainingSlots = 80 - state.likedCodes.length;

  app.innerHTML = `
    <h2>🔥 جرقهٔ انرژی</h2>
    <div style="color:#f0c040;">💛 <strong>${state.likedCodes.length}</strong> جرقه <span style="font-size:0.8rem;color:#888;">(حداقل ۲۰ - حداکثر ۸۰)</span></div>
    <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
    <div class="swipe-card">
      <p style="font-size:1.2rem;line-height:2.2;">${escapeHtml(card.description_fa)}</p>
      <button class="btn btn-heart" onclick="likeCard(true)">❤️ جرقه زد</button>
      <button class="btn btn-skip" onclick="likeCard(false)">❌ ادامه</button>
      ${canFinish ? `
        <div style="margin-top:20px;border-top:1px solid #333;padding-top:15px;">
          <p style="color:#b0a080;">🌟 حداقل جرقه‌ها را داری! اما هرچه بیشتر بزنی، دقیق‌تر کشف می‌شوی.</p>
          <button class="btn btn-primary" style="width:100%;margin-top:10px;" onclick="finishSwipe()">🚀 ورود به لایهٔ دوم</button>
          <button class="btn" style="width:100%;margin-top:8px;" onclick="goBack()">🔙 جرقه‌های بیشتر (تا ${remainingSlots} جرقهٔ دیگر)</button>
        </div>` : `
        <p style="color:#f0c040;margin-top:15px;">⚠️ <strong>${20 - state.likedCodes.length}</strong> جرقهٔ دیگر لازم داری</p>
        <button class="btn" style="width:100%;margin-top:10px;" onclick="goBack()">🔙 بازگشت به قلمروها</button>`}
      ${state.swipeIndex > 0 ? `<button class="btn" style="margin-top:15px;width:100%;" onclick="previousCard()">⬅️ جرقهٔ قبل</button>` : ''}
    </div>`;
}

function likeCard(liked) {
  if (liked && state.likedCodes.length < 80) {
    state.likedCodes.push(state.swipeCards[state.swipeIndex].code);
    state.likedCodesSet.add(state.swipeCards[state.swipeIndex].code);
  }
  state.swipeIndex++;
  saveSession();
  renderSwipe();
}

function previousCard() {
  if (state.swipeIndex > 0) {
    state.swipeIndex--;
    const removedCode = state.swipeCards[state.swipeIndex]?.code;
    if (removedCode && state.likedCodes.length > 0 && state.likedCodes[state.likedCodes.length - 1] === removedCode) {
      state.likedCodes.pop();
      state.likedCodesSet.delete(removedCode);
    }
    saveSession();
    renderSwipe();
  }
}

function finishSwipe() {
  updateCompletionStatus();
  state.currentQuestion = 0;
  state.currentValueQuestion = 0;
  state.strategyAnswers = [];
  goTo('introStrategies');
}

// ==================== STRATEGIES (بدون تغییر) ====================
function renderIntroStrategies() {
  app.innerHTML = `
    <h2>🧭 لایهٔ دوم: راهبردهای فردی</h2>
    <div class="card">
      <p style="color:#b0a080;line-height:2.2;">حالا که جرقه‌های انرژی‌ات را شناختی، وقت آن رسیده که بفهمی <strong>چطور</strong> فکر می‌کنی، یاد می‌گیری و با چالش‌ها روبرو می‌شوی. در این بخش، <strong>۲۵ موقعیت واقعی</strong> پیش روی توست. هیچ پاسخ درست یا غلطی وجود ندارد — فقط مسیرهای متفاوت.</p>
      <button class="btn btn-primary" style="width:100%;margin-top:20px;" onclick="goTo('strategies')">🚀 شروع سوالات راهبرد</button>
      <button class="btn" style="width:100%;margin-top:8px;" onclick="goBack()">⬅️ بازگشت</button>
    </div>`;
}

function renderStrategy() {
  if (!state.questionsReady) {
    app.innerHTML = `<h2>⚠️ در حال بارگذاری سوالات...</h2><button class="btn" onclick="retryLoadQuestions()">🔄 تلاش دوباره</button>`;
    return;
  }
  if (state.currentQuestion >= state.strategyQuestions.length) {
    state.currentQuestion = 0;
    state.currentValueQuestion = 0;
    goTo('introValues');
    return;
  }
  const q = state.strategyQuestions[state.currentQuestion];
  const currentAnswer = state.strategyAnswers[state.currentQuestion];
  let html = `<h2>🧭 راهبرد ${q.number} از ${state.strategyQuestions.length}</h2>
    <div class="card"><p style="margin-bottom:20px;color:#f0c040;">${escapeHtml(q.question)}</p>`;
  q.options.forEach(o => {
    const isSelected = currentAnswer === o.index;
    html += `<button class="btn" style="display:block;width:100%;text-align:right;margin-bottom:8px;${isSelected ? 'border:2px solid #f0c040;' : ''}" onclick="answerStrategy(${o.index})">${escapeHtml(o.text)}</button>`;
  });
  html += `</div>
    <div style="display:flex;gap:10px;justify-content:center;margin-top:10px;">
      ${state.currentQuestion > 0 ? `<button class="btn" onclick="previousStrategy()">⬅️ سوال قبل</button>` : ''}
      <button class="btn" onclick="goBack()">⬅️ بازگشت</button>
    </div>`;
  app.innerHTML = html;
}

function answerStrategy(idx) { state.strategyAnswers[state.currentQuestion] = idx; state.currentQuestion++; saveSession(); render(); }
function previousStrategy() { if (state.currentQuestion > 0) { state.currentQuestion--; saveSession(); render(); } }

async function retryLoadQuestions() {
  state.retryCount++;
  app.innerHTML = `<h2>⏳ در حال تلاش مجدد (${state.retryCount})...</h2>`;
  await loadQuestions();
  render();
}

// ==================== VALUES + CHOICE (تغییر کرده) ====================
function renderIntroValues() {
  app.innerHTML = `
    <h2>⚖️ لایهٔ سوم: ارزش‌های بنیادین</h2>
    <div class="card">
      <p style="color:#b0a080;line-height:2.2;">و در آخر... چه چیزی به کارت <strong>معنا</strong> می‌دهد؟ در این مرحله، <strong>۱۵ دوگانهٔ قدرتمند</strong> پیش روی توست. باید یکی را انتخاب کنی — انتخابی که از اعماق وجودت می‌آید.</p>
      <button class="btn btn-primary" style="width:100%;margin-top:20px;" onclick="goTo('values')">🚀 شروع دوگانه‌های ارزشی</button>
      <button class="btn" style="width:100%;margin-top:8px;" onclick="goBack()">⬅️ بازگشت</button>
    </div>`;
}

function renderValue() {
  if (!state.questionsReady) {
    app.innerHTML = `<h2>⚠️ در حال بارگذاری سوالات...</h2><button class="btn" onclick="retryLoadQuestions()">🔄 تلاش دوباره</button>`;
    return;
  }
  if (state.currentValueQuestion >= state.valueQuestions.length) {
    // 🔥 تغییر: به جای submit مستقیم، به صفحه انتخاب می‌رویم
    app.innerHTML = `
      <h2>✅ پایان سفر اکتشافی</h2>
      <div class="card">
        <p>تبریک! شما ${state.likedCodes.length} جرقه و به ${state.strategyAnswers.length} موقعیت و ${state.valueAnswers.length} ارزش پاسخ داده‌اید.</p>
        <button class="btn btn-primary" style="width:100%;margin-top:15px;" onclick="goTo('choice')">
          🧭 انتخاب نوع تحلیل
        </button>
      </div>`;
    return;
  }
  const q = state.valueQuestions[state.currentValueQuestion];
  const opts = q.options;
  const currentAnswer = state.valueAnswers[state.currentValueQuestion];
  app.innerHTML = `
    <h2>⚖️ ارزش ${q.number} از ${state.valueQuestions.length}</h2>
    <div class="card">
      <p style="margin-bottom:20px;color:#f0c040;">${escapeHtml(q.question)}</p>
      <button class="btn" style="display:block;width:100%;margin-bottom:10px;text-align:right;${currentAnswer === opts[0].code ? 'border:2px solid #f0c040;' : ''}" onclick="answerValue('${opts[0].code}')">${escapeHtml(opts[0].text)}</button>
      <button class="btn" style="display:block;width:100%;text-align:right;${currentAnswer === opts[1].code ? 'border:2px solid #f0c040;' : ''}" onclick="answerValue('${opts[1].code}')">${escapeHtml(opts[1].text)}</button>
    </div>
    <div style="display:flex;gap:10px;justify-content:center;margin-top:10px;">
      ${state.currentValueQuestion > 0 ? `<button class="btn" onclick="previousValue()">⬅️ سوال قبل</button>` : ''}
      <button class="btn" onclick="goBack()">⬅️ بازگشت</button>
    </div>`;
}

function answerValue(code) { state.valueAnswers[state.currentValueQuestion] = code; state.currentValueQuestion++; saveSession(); render(); }
function previousValue() { if (state.currentValueQuestion > 0) { state.currentValueQuestion--; saveSession(); render(); } }

// ==================== صفحه انتخاب (جدید) ====================
function renderChoice() {
  app.innerHTML = `
    <h2>🧭 انتخاب مسیر تحلیل</h2>
    <div class="card" style="text-align:center;">
      <p style="color:#b0a080;line-height:2.2;">
        سفر اکتشافی شما کامل شد. حالا می‌توانید یکی از دو تحلیل زیر را مشاهده کنید:
      </p>
      <div style="display:flex;flex-direction:column;gap:15px;margin-top:20px;">
        <button class="btn btn-primary" style="width:100%;" onclick="analyzeBranches()">
          🏫 هدایت تحصیلی (شاخه‌های دبیرستان)
        </button>
        <button class="btn btn-primary" style="width:100%;" onclick="analyzeMajors()">
          🎓 انتخاب رشته‌های دانشگاهی
        </button>
      </div>
      <button class="btn" style="width:100%;margin-top:15px;" onclick="resetJourney()">🔄 شروع مجدد</button>
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

// ==================== توابع تحلیل (جدید/تغییر نام) ====================
async function analyzeMajors() {
  state.stage = 'results';
  const payload = buildPayload();
  state.lastPayload = payload;
  app.innerHTML = `<h2>⏳ در حال تحلیل رشته‌های دانشگاهی...</h2>`;
  try {
    const res = await fetchWithRetry(API_BASE + '/api/v2/darkhorse/discover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    state.majorsResult = data;
    displayResults(data, 'majors');
  } catch (e) {
    console.error(e);
    app.innerHTML = `<h2>❌ خطا در دریافت نتایج رشته‌ها</h2>
      <div class="card"><p>نتوانستیم با سرور ارتباط برقرار کنیم.</p>
      <button class="btn btn-primary" style="width:100%;margin-top:15px;" onclick="analyzeMajors()">🔄 تلاش دوباره</button>
      <button class="btn" style="width:100%;margin-top:8px;" onclick="goTo('choice')">⬅️ بازگشت به انتخاب</button></div>`;
  }
}

async function analyzeBranches() {
  state.stage = 'results';
  const payload = buildPayload();
  state.lastPayload = payload;
  app.innerHTML = `<h2>⏳ در حال تحلیل شاخه‌های دبیرستان...</h2>`;
  try {
    const res = await fetchWithRetry(API_BASE + '/api/v2/darkhorse/branch-discovery', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    state.branchesResult = data;
    displayResults(data, 'branches');
  } catch (e) {
    console.error(e);
    app.innerHTML = `<h2>❌ خطا در دریافت نتایج هدایت تحصیلی</h2>
      <div class="card"><p>نتوانستیم با سرور ارتباط برقرار کنیم.</p>
      <button class="btn btn-primary" style="width:100%;margin-top:15px;" onclick="analyzeBranches()">🔄 تلاش دوباره</button>
      <button class="btn" style="width:100%;margin-top:8px;" onclick="goTo('choice')">⬅️ بازگشت به انتخاب</button></div>`;
  }
}

async function fetchWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      const res = await fetch(url, { ...options, signal: controller.signal });
      clearTimeout(timeout);
      if (!res.ok) throw new Error(`Status ${res.status}`);
      return res;
    } catch (e) {
      if (i === maxRetries - 1) throw e;
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
}

// ==================== DISPLAY RESULTS (نسخه نهایی با UI/UX بهبودیافته) ====================
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
      name: item.major_name_fa || item.branch_name_fa || fit.major_name_fa || fit.branch_name_fa || item.name || 'نامشخص',
      fit_score: fit.score || fit.fit_score || item.fit_score || 0,
      raw_components: fit.raw_components || item.raw_components || {},
      evidence: fit.evidence || item.evidence || {},
      personalized_description: fit.personalized_description || item.personalized_description || '',
      archetype: archetypeData,
      fulfillment_source: fit.fulfillment_source || fit.archetype?.fulfillment_source || null,
      alternative_paths: fit.alternative_paths || item.alternative_paths || [],
      warning: fit.warning || item.warning || null,
      count: fit.count || item.count || null,
      avg_components: fit.avg_components || item.avg_components || null,
      micro_motives_matched: fit.evidence?.micro_motives_matched || item.evidence?.micro_motives_matched || []
    };
  });

  // ===== ۳. فیلتر و مرتب‌سازی =====
  const matched = normalized
    .filter(item => (item.fit_score || 0) >= 30)
    .sort((a, b) => (b.fit_score || 0) - (a.fit_score || 0));

  // ===== ۴. تحلیل سبک شخصی =====
  const strategyStyle = state.strategyAnswers.length >= 15 ? analyzeStrategyStyle(state.strategyAnswers) : null;
  const valueStyle = state.valueAnswers.length >= 5 ? analyzeValueStyle(state.valueAnswers) : null;

  let html = `
    <h2 style="text-align:center;color:#f0c040;font-size:1.8rem;">📊 نتایج ${isBranch ? 'هدایت تحصیلی' : 'انتخاب رشته'}</h2>
    <p style="color:#b0a080;font-style:italic;text-align:center;margin-bottom:20px;">
      ✨ این پیشنهادها بر اساس ویژگی‌هایی است که <strong>امروز</strong> در خودت کشف کردی. 
      فردیت یک سفر است، نه یک مقصد.
    </p>
    ${strategyStyle || valueStyle ? `
    <div style="background:linear-gradient(135deg,#1a1a2e,#2a1a3e);border:1px solid #d4af37;border-radius:12px;padding:18px;margin:15px 0;text-align:right;font-size:0.9rem;">
      <p style="margin:0 0 10px 0;color:#f0c040;font-weight:bold;">🧠 تحلیل سبک شخصی تو</p>
      ${strategyStyle ? `<p style="margin:5px 0;"><span style="font-size:1.2rem;">${strategyStyle.icon}</span> <strong>سبک فکری:</strong> ${escapeHtml(strategyStyle.style)} (${strategyStyle.strength}٪) — ${escapeHtml(strategyStyle.description)}</p>` : ''}
      ${valueStyle ? `<p style="margin:5px 0;"><span style="font-size:1.2rem;">⚖️</span> <strong>ارزش‌های کلیدی:</strong> ${escapeHtml(valueStyle.summary)}</p>` : ''}
    </div>` : ''}

    <p style="text-align:center;color:#b0a080;">بر اساس <strong style="color:#f0c040;">${state.likedCodes.length}</strong> خرده‌انگیزه، ${matched.length} ${isBranch ? 'شاخه' : 'رشته'} با فردیت تو هم‌راستا هستند:</p>
  `;

  // ===== بهترین شاخه (برای هدایت تحصیلی) =====
  if (isBranch) {
    let bestName = bestBranch;
    if (!bestName && matched.length > 0) {
      const eligible = matched.filter(item => (item.avg_components?.m_score || 0) >= 15);
      if (eligible.length > 0) bestName = eligible[0].name;
    }
    if (bestName) {
      html += `
        <div style="background:linear-gradient(135deg,#1a1a2e,#2a1a3e);border:2px solid #f0c040;border-radius:12px;padding:18px;margin:20px 0;text-align:center;">
          <p style="color:#f0c040;font-size:1.4rem;font-weight:bold;">🏆 بهترین شاخهٔ پیشنهادی: <span style="font-size:1.6rem;">${escapeHtml(bestName)}</span></p>
          <p style="color:#b0a080;font-size:0.9rem;">این شاخه بیشترین هماهنگی را با انگیزه‌ها، راهبردها و ارزش‌های شما دارد.</p>
        </div>`;
    }
  }

  if (matched.length === 0) {
    html += `<p style="color:#f0c040;text-align:center;">با همین خرده‌انگیزه‌ها، هیچ ${isBranch ? 'شاخه‌ای' : 'رشته‌ای'} به آستانهٔ ۳۰٪ نرسیده است.</p>`;
  } else {
    matched.forEach(r => {
      const score = r.fit_score || 0;
      const raw = r.raw_components || {};
      const mPct = raw.m_score !== undefined ? raw.m_score : (r.avg_components?.m_score || 0);
      const sPct = raw.s_score !== undefined ? raw.s_score : (r.avg_components?.s_score || 0);
      const vPct = raw.v_score !== undefined ? raw.v_score : (r.avg_components?.v_score || 0);

      // ===== جرقه‌های مشترک =====
      const microMatch = r.micro_motives_matched || [];
      let sparkText = '';
      if (microMatch.length > 0) {
        const names = microMatch.slice(0, 3).map(m => escapeHtml(m.description || m.code || m)).join('، ');
        sparkText = names;
        if (microMatch.length > 3) sparkText += ` و ${microMatch.length - 3} جرقهٔ دیگر`;
      }

      // ===== هشدار (در بالای کارت) =====
      let warningHtml = '';
      if (r.warning) {
        warningHtml = `
          <div style="background:#2a1a1a;border:1px solid #ff6b6b;border-radius:8px;padding:10px 14px;margin-bottom:12px;">
            <span style="color:#ff6b6b;font-weight:bold;">⚠️ ${escapeHtml(r.warning)}</span>
          </div>`;
      }

      html += `
        <div class="card" style="text-align:right;padding:20px;margin:20px 0;border-radius:12px;background:linear-gradient(145deg,#1a1a2e,#0a0a12);border:1px solid #333;box-shadow:0 4px 20px rgba(0,0,0,0.3);">
          ${warningHtml}
          
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-size:1.8rem;color:#f0c040;">${isBranch ? '📚' : '🎓'}</span>
              <h3 style="color:#f0c040;font-size:1.4rem;margin:0;">${escapeHtml(r.name)}</h3>
            </div>
            <div style="background:#d4af37;color:#000;font-weight:bold;padding:4px 14px;border-radius:20px;font-size:0.9rem;">
              ${score}%
            </div>
          </div>

          <!-- نوارهای پیشرفت M, S, V -->
          <div style="margin:12px 0;">
            <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:#b0a080;">
              <span>🔥 انگیزه (M)</span> <span>${mPct}%</span>
            </div>
            <div style="background:#333;height:6px;border-radius:4px;margin-bottom:6px;">
              <div style="background:#ff6b6b;width:${mPct}%;height:6px;border-radius:4px;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:#b0a080;">
              <span>🧭 راهبرد (S)</span> <span>${sPct}%</span>
            </div>
            <div style="background:#333;height:6px;border-radius:4px;margin-bottom:6px;">
              <div style="background:#4ecdc4;width:${sPct}%;height:6px;border-radius:4px;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:#b0a080;">
              <span>⚖️ ارزش (V)</span> <span>${vPct}%</span>
            </div>
            <div style="background:#333;height:6px;border-radius:4px;">
              <div style="background:#ffe66d;width:${vPct}%;height:6px;border-radius:4px;"></div>
            </div>
          </div>

          ${sparkText ? `<p style="font-size:0.85rem;color:#b0a080;margin:8px 0;">🔥 جرقه‌های مشترک: ${sparkText}</p>` : ''}
          
          ${r.personalized_description ? `
            <div style="background:#0a0a0f;border:1px solid #d4af37;border-radius:8px;padding:12px;margin:10px 0;font-size:0.9rem;line-height:1.9;">
              <p style="margin:0;color:#b0a080;">💬 ${escapeHtml(r.personalized_description)}</p>
            </div>` : ''}

          <!-- کهن‌الگو (با طراحی برجسته) -->
          ${!isBranch && r.archetype ? `
            <div style="background:linear-gradient(135deg,#1a1a2e,#2a1a3e);border:1px solid #d4af37;border-radius:8px;padding:14px;margin:12px 0;text-align:center;">
              <div style="display:flex;align-items:center;justify-content:center;gap:8px;font-size:1.2rem;color:#f0c040;">
                <span>🧠</span> <strong>کهن‌الگوی شناختی</strong>
              </div>
              <div style="font-size:1.3rem;font-weight:bold;color:#fff;margin:6px 0;">${escapeHtml(r.archetype.archetype || '')}</div>
              ${r.archetype.identity_sentence ? `<div style="font-size:0.9rem;color:#b0a080;">📖 ${escapeHtml(r.archetype.identity_sentence)}</div>` : ''}
            </div>` : ''}

          <!-- منبع رضایت عمیق -->
          ${!isBranch && r.fulfillment_source ? `
            <div style="background:#0a0a0f;border:1px solid #d4af37;border-radius:8px;padding:12px;margin:10px 0;">
              <div style="display:flex;align-items:center;gap:6px;color:#f0c040;font-weight:bold;margin-bottom:4px;">
                <span>🌟</span> منبع رضایت عمیق
              </div>
              <div style="color:#b0a080;font-size:0.9rem;line-height:1.7;">${escapeHtml(r.fulfillment_source)}</div>
            </div>` : ''}

          <!-- مسیرهای جایگزین (به‌صورت برچسب‌های قابل کلیک) -->
          ${r.alternative_paths && r.alternative_paths.length > 0 ? `
            <div style="margin:10px 0;">
              <div style="font-size:0.85rem;color:#b0a080;margin-bottom:6px;">🔄 مسیرهای جایگزین:</div>
              <div style="display:flex;flex-wrap:wrap;gap:8px;">
                ${r.alternative_paths.map(p => {
                  const name = p.branch_name || p.major_name || p.name || '';
                  return name ? `<span style="background:#1a1a2e;border:1px solid #d4af37;padding:4px 14px;border-radius:20px;font-size:0.85rem;color:#f0c040;cursor:default;">${escapeHtml(name)}</span>` : '';
                }).filter(Boolean).join('')}
              </div>
            </div>` : ''}

          ${isBranch && r.count ? `<div style="font-size:0.75rem;color:#888;margin-top:8px;">📌 تعداد کدهای تحلیل‌شده: ${r.count}</div>` : ''}
        </div>`;
    });
  }

  // ==================== دکمه‌های ناوبری ====================
  html += `
    <div style="display:flex;flex-direction:column;gap:12px;margin-top:25px;">
      <button class="btn" style="width:100%;padding:12px;" onclick="goTo('choice')">
        ⬅️ بازگشت به انتخاب نوع تحلیل
      </button>
      ${!isBranch && state.branchesResult ? `
        <button class="btn btn-primary" style="width:100%;padding:12px;" onclick="displayResults(state.branchesResult, 'branches')">
          🏫 مشاهدهٔ نتایج هدایت تحصیلی (شاخه‌های دبیرستان)
        </button>` : ''}
      ${isBranch && state.majorsResult ? `
        <button class="btn btn-primary" style="width:100%;padding:12px;" onclick="displayResults(state.majorsResult, 'majors')">
          🎓 مشاهدهٔ نتایج رشته‌های دانشگاهی
        </button>` : ''}
      <button class="btn" style="width:100%;padding:12px;" onclick="resetJourney()">🔄 شروع مجدد</button>
    </div>`;

  // ==================== بخش نظرسنجی ====================
  html += `
    <div id="feedbackSection" style="background:#1a1a2e;border:1px solid #d4af37;border-radius:12px;padding:20px;margin:30px 0 15px 0;text-align:right;">
      <p style="color:#f0c040;font-weight:bold;margin-bottom:15px;font-size:1.1rem;">💬 نظرت دربارهٔ اسب سیاه چیه؟</p>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۱. چقدر از تجربهٔ کلی این سفر اکتشافی راضی بودی؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q1">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q1', ${i})" style="font-size:1.8rem;cursor:pointer;opacity:0.3;" id="star-q1-${i}">⭐</span>`).join('')}
      </div>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۲. چقدر نتایج با علایق و فردیت واقعی‌ات همخوانی داشت؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q2">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q2', ${i})" style="font-size:1.8rem;cursor:pointer;opacity:0.3;" id="star-q2-${i}">⭐</span>`).join('')}
      </div>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۳. آیا این اپلیکیشن را به یک دوست معرفی می‌کنی؟</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;" id="feedback-q3">
        <button class="btn btn-sm" onclick="setFeedback('q3', 'yes')" id="btn-q3-yes" style="padding:6px 16px;">بله</button>
        <button class="btn btn-sm" onclick="setFeedback('q3', 'maybe')" id="btn-q3-maybe" style="padding:6px 16px;">شاید</button>
        <button class="btn btn-sm" onclick="setFeedback('q3', 'no')" id="btn-q3-no" style="padding:6px 16px;">خیر</button>
      </div>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۴. اگر می‌توانستی <strong>شانس قبولی خود را در دانشگاه‌های مختلف</strong> ببینی، چقدر برایت ارزشمند بود؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q4">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q4', ${i})" style="font-size:1.8rem;cursor:pointer;opacity:0.3;" id="star-q4-${i}">⭐</span>`).join('')}
      </div>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۵. چقدر دوست داری <strong>آیندهٔ شغلی و بازار کار</strong> این رشته‌ها را ببینی؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q5">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q5', ${i})" style="font-size:1.8rem;cursor:pointer;opacity:0.3;" id="star-q5-${i}">⭐</span>`).join('')}
      </div>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۶. آیا به انتخاب رشتهٔ سنتی (بر اساس رتبه) هم نیاز داری؟</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;" id="feedback-q6">
        <button class="btn btn-sm" onclick="setFeedback('q6', 'yes')" id="btn-q6-yes" style="padding:6px 16px;">بله</button>
        <button class="btn btn-sm" onclick="setFeedback('q6', 'no')" id="btn-q6-no" style="padding:6px 16px;">خیر</button>
      </div>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۷. اگر سرویس <strong>کشف رشته‌های متناسب با فردیت</strong> (همین سفر اکتشافی) پولی بود، باز هم استفاده می‌کردی؟</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;" id="feedback-q7">
        <button class="btn btn-sm" onclick="setFeedback('q7', 'yes')" id="btn-q7-yes" style="padding:6px 16px;">بله</button>
        <button class="btn btn-sm" onclick="setFeedback('q7', 'maybe')" id="btn-q7-maybe" style="padding:6px 16px;">شاید</button>
        <button class="btn btn-sm" onclick="setFeedback('q7', 'no')" id="btn-q7-no" style="padding:6px 16px;">خیر</button>
      </div>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۸. اگر بخش <strong>آیندهٔ شغلی و بازار کار</strong> هر رشته (با هزینهٔ کم) ارائه شود، برایت ارزشمند است؟</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;" id="feedback-q8">
        <button class="btn btn-sm" onclick="setFeedback('q8', 'yes')" id="btn-q8-yes" style="padding:6px 16px;">بله</button>
        <button class="btn btn-sm" onclick="setFeedback('q8', 'maybe')" id="btn-q8-maybe" style="padding:6px 16px;">شاید</button>
        <button class="btn btn-sm" onclick="setFeedback('q8', 'no')" id="btn-q8-no" style="padding:6px 16px;">خیر</button>
      </div>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۹. چقدر این روش (کشف رشته از طریق فردیت) نسبت به روش‌های سنتی برات نوآورانه بود؟</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;" id="feedback-q10">
        ${[1,2,3,4,5].map(i => `<span onclick="setFeedback('q10', ${i})" style="font-size:1.8rem;cursor:pointer;opacity:0.3;" id="star-q10-${i}">⭐</span>`).join('')}
      </div>
      <p style="color:#b0a080;margin:12px 0 5px 0;">۱۰. چه پیشنهادی برای بهبود داری؟ (اختیاری)</p>
      <textarea id="feedback-q9" placeholder="اینجا بنویس..." style="width:100%;padding:12px;background:#0a0a0f;color:#fff;border:1px solid #333;border-radius:8px;min-height:60px;font-family:Vazirmatn;"></textarea>
      <button class="btn btn-primary" style="width:100%;margin-top:15px;padding:12px;" onclick="submitFeedback()">📩 ثبت بازخورد</button>
      <p id="feedback-msg" style="color:#f0c040;margin-top:8px;display:none;">✅ ممنون از بازخوردت! نظرت ثبت شد.</p>
    </div>`;

  app.innerHTML = html;
}   
// ==================== تحلیل سبک شخصی (بدون تغییر) ====================
function analyzeStrategyStyle(answers) {
  const counts = [0,0,0,0,0];
  answers.forEach(a => { if (a !== undefined) counts[a]++; });
  const labels = [
    { label: 'تحلیلی و گام‌به‌گام', icon: '🔍', key: 0 },
    { label: 'آزمایشگر و جهشی', icon: '🧪', key: 1 },
    { label: 'مشورتی و اجتماعی', icon: '🤝', key: 2 },
    { label: 'شهودی و جرقه‌ای', icon: '💡', key: 3 },
    { label: 'اقدام‌گرا و سریع', icon: '⚡', key: 4 }
  ];
  const dominant = labels.sort((a, b) => counts[b.key] - counts[a.key])[0];
  const total = answers.filter(a => a !== undefined).length;
  const percentage = total > 0 ? Math.round((counts[dominant.key] / total) * 100) : 0;
  return {
    style: dominant.label,
    icon: dominant.icon,
    strength: percentage,
    description: percentage > 60
      ? `شما به‌وضوح یک فرد ${dominant.label} هستید (${percentage}٪ پاسخ‌ها).`
      : `سبک غالب شما ${dominant.label} است، اما انعطاف‌پذیری بالایی داری.`
  };
}

function analyzeValueStyle(answers) {
  const map = {
    'Q1A': { label: 'تأثیر فوری بر انسان', icon: '❤️' },
    'Q1B': { label: 'بهینه‌سازی سیستم‌ها', icon: '⚙️' },
    'Q2A': { label: 'ساختن ماندگار', icon: '🏗️' },
    'Q2B': { label: 'تکثیر ایده در ذهن‌ها', icon: '🌱' },
    'Q3A': { label: 'تنوع و چالش روزانه', icon: '🎢' },
    'Q3B': { label: 'عمق و تخصص مرجع', icon: '🎯' },
    'Q4A': { label: 'مسئولیت فردی', icon: '🫂' },
    'Q4B': { label: 'مسئولیت سیستمی', icon: '🌐' },
    'Q5A': { label: 'تقدیر از دقت و نظم', icon: '🏅' },
    'Q5B': { label: 'تقدیر از خلاقیت', icon: '🎨' },
    'Q6A': { label: 'انرژی از تعامل', icon: '💬' },
    'Q6B': { label: 'انرژی از تمرکز تنهایی', icon: '🧘' },
    'Q7A': { label: 'نوآوری و اختراع', icon: '🚀' },
    'Q7B': { label: 'مربی‌گری و پرورش', icon: '👨‍🏫' },
    'Q8A': { label: 'ثبات و امنیت', icon: '🏰' },
    'Q8B': { label: 'آزادی و انعطاف', icon: '🕊️' },
    'Q9A': { label: 'کاهش رنج انسان', icon: '🕯️' },
    'Q9B': { label: 'خلق زیبایی و دانش', icon: '✨' },
    'Q10A': { label: 'رهبری و تعیین مسیر', icon: '🧭' },
    'Q10B': { label: 'همدلی و وفاق‌سازی', icon: '🕊️' },
    'Q11A': { label: 'کار با داده‌ها', icon: '📊' },
    'Q11B': { label: 'کار با انسان‌ها', icon: '👥' },
    'Q12A': { label: 'خطرپذیری', icon: '🎲' },
    'Q12B': { label: 'ثبات‌طلبی', icon: '🛡️' },
    'Q13A': { label: 'نتیجهٔ فوری', icon: '⚡' },
    'Q13B': { label: 'اثر ماندگار', icon: '🏛️' },
    'Q14A': { label: 'استقلال کامل', icon: '🦅' },
    'Q14B': { label: 'تعلق سازمانی', icon: '🏢' },
    'Q15A': { label: 'تسلط بر یک حوزه', icon: '🎯' },
    'Q15B': { label: 'کنجکاوی بی‌پایان', icon: '🌌' }
  };
  const selected = answers.map(a => map[a] || { label: a, icon: '❓' });
  const unique = [...new Set(selected.map(s => s.label))];
  return {
    values: selected.slice(0, 5),
    summary: unique.slice(0, 4).join('، '),
    description: 'ارزش‌های بنیادین شما نشان می‌دهد که چه چیزی به کارتان معنا می‌بخشد.'
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
      <button class="btn" onclick="goTo('splash')" style="margin-bottom:15px;">⬅️ بازگشت به صفحه اصلی</button>
      <button class="btn" onclick="copyAllFeedbackServer()" style="margin-bottom:15px;background:#d4af37;color:#000;">📋 کپی همه به صورت JSON</button>
      <div style="text-align:right;">`;
    feedbackData.forEach(fb => {
      const date = new Date(fb.timestamp).toLocaleString('fa-IR');
      html += `<div class="card" style="text-align:right;margin-bottom:15px;">
        <p style="color:#888;font-size:0.8rem;">📅 ${date} | 🆔 ${escapeHtml(fb.session_id || '؟')}</p>
        <p style="color:#b0a080;">✨ خرده‌انگیزه‌ها: <strong>${fb.likedCodes || '؟'}</strong> عدد</p>
        <p style="color:#b0a080;">🧭 پاسخ‌های راهبرد: <strong>${fb.strategyAnswers || '؟'}</strong> از ۲۵</p>
        <p style="color:#b0a080;">⚖️ پاسخ‌های ارزشی: <strong>${fb.valueAnswers || '؟'}</strong> از ۱۵</p>
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
    html += `</div><button class="btn" onclick="goTo('splash')">⬅️ بازگشت به صفحه اصلی</button>`;
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
  clearSession();
  state.stage = 'manifesto';
  state.history = [];
  state.selectedRealms = [];
  state.selectedSubRealms = [];
  state.selectedNarrowPaths = [];
  state.likedCodes = [];
  state.likedCodesSet.clear();
  state.strategyAnswers = [];
  state.valueAnswers = [];
  state.currentQuestion = 0;
  state.currentValueQuestion = 0;
  state.completedPaths.clear();
  state.completedSubRealms.clear();
  state.lastPayload = null;
  state.cachedMotives = null;
  state.swipeIndex = 0;
  state.totalSwipes = 0;
  state.retryCount = 0;
  state.majorsResult = null;
  state.branchesResult = null;
  render();
}

async function init() {
  await Promise.all([loadQuestions(), loadMicroMotivesMap()]);
  if (localStorage.getItem('darkhorse_session_v2')) {
    loadSession();
  }
  render();
}
init();
