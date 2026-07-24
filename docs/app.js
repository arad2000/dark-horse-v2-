// ==================== Dark Horse App V2.0 (Standalone / Hardcoded) ====================
// این نسخه کاملاً مستقل از فایل questions_v2.json است.
// فقط به data.js (برای REALMS و ...) و micro_motives.json (اختیاری) نیاز دارد.

const API_BASE = 'https://dark-horse-v2.onrender.com';

console.log('🚀 Dark Horse V2.0 راه‌اندازی شد (Hardcoded Mode)');

// ==================== حالت عمومی ====================
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
  questionsReady: true, // Hardcoded -> همیشه درست
  motivesReady: false,
  retryCount: 0,
  cardLikeStatus: new Map()
};

const app = document.getElementById('app');

// ==================== توابع کمکی ====================
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ==================== داده‌های هاردکد سوالات (۲۵ سوال راهبردی + ۱۵ ارزشی) ====================
const STRATEGY_QUESTIONS_HARD = [
  { id: "S1", number: 1, question: "وقتی با یک مسئلهٔ پیچیده روبرو می‌شوی، اولین قدمت چیست؟", options: [
    { index: 0, text: "مسئله را به اجزای کوچک‌تر تقسیم می‌کنم و هر جزء را جداگانه بررسی می‌کنم." },
    { index: 1, text: "چندین راه‌حل ممکن را به‌طور همزمان آزمایش می‌کنم تا ببینم کدام جواب می‌دهد." },
    { index: 2, text: "با دیگران مشورت می‌کنم و نظرات مختلف را جمع‌آوری می‌کنم." },
    { index: 3, text: "به شهودم اعتماد می‌کنم و اولین راه‌حلی که به ذهنم می‌رسد را امتحان می‌کنم." },
    { index: 4, text: "بلافاصله دست به کار می‌شوم و در حین انجام، راه‌حل را پیدا می‌کنم." }
  ]},
  { id: "S2", number: 2, question: "چگونه یک مهارت جدید را یاد می‌گیری؟", options: [
    { index: 0, text: "یک کتاب یا دورهٔ آموزشی جامع پیدا می‌کنم و قدم‌به‌قدم پیش می‌روم." },
    { index: 1, text: "سریعاً شروع به کار عملی می‌کنم و در حین کار، اشتباهات را یاد می‌گیرم." },
    { index: 2, text: "از یک متخصص می‌خواهم که به من آموزش دهد و راهنماییم کند." },
    { index: 3, text: "به‌طور شهودی با موضوع درگیر می‌شوم و الگوها را خودم کشف می‌کنم." },
    { index: 4, text: "تکه‌تکه یاد می‌گیرم و هر بار یک بخش را کامل می‌کنم." }
  ]},
  { id: "S3", number: 3, question: "در یک پروژهٔ گروهی، معمولاً چه نقشی را ترجیح می‌دهی؟", options: [
    { index: 0, text: "برنامه‌ریزی و ساختاردهی کارها." },
    { index: 1, text: "ایجاد ایده‌های جدید و خارج از چارچوب." },
    { index: 2, text: "هماهنگی بین اعضا و حل اختلافات." },
    { index: 3, text: "تمرکز روی جزئیات و کیفیت نهایی." },
    { index: 4, text: "پیش‌بردن کارها و انجام سریع تسک‌ها." }
  ]},
  { id: "S4", number: 4, question: "کدام محیط کاری بیشترین انرژی را به تو می‌دهد؟", options: [
    { index: 0, text: "یک محیط ساختاریافته با قوانین مشخص." },
    { index: 1, text: "یک محیط پویا که هر روز چالش جدیدی دارد." },
    { index: 2, text: "یک محیط مشارکتی که در آن تبادل نظر دائمی است." },
    { index: 3, text: "یک محیط آرام و شخصی با کمترین حواس‌پرتی." },
    { index: 4, text: "یک محیط رقابتی که آدرنالین را بالا می‌برد." }
  ]},
  { id: "S5", number: 5, question: "وقتی با یک شکست مواجه می‌شوی، چه واکنشی نشان می‌دهی؟", options: [
    { index: 0, text: "تحلیل می‌کنم که دقیقاً کجا اشتباه کرده‌ام." },
    { index: 1, text: "به سراغ راه‌حل جدید می‌روم و تجربه را فراموش می‌کنم." },
    { index: 2, text: "با دیگران صحبت می‌کنم تا دیدگاه‌های جدید پیدا کنم." },
    { index: 3, text: "کمی مکث می‌کنم تا شهودم راه درست را نشانم دهد." },
    { index: 4, text: "با قدرت بیشتری تلاش می‌کنم تا ثابت کنم می‌توانم." }
  ]},
  { id: "S6", number: 6, question: "چه چیزی برایت لذت‌بخش‌تر است؟", options: [
    { index: 0, text: "کشف یک حقیقت یا قانون پنهان." },
    { index: 1, text: "اختراع یا ساخت یک چیز جدید." },
    { index: 2, text: "کمک به دیگران برای حل مشکلشان." },
    { index: 3, text: "خلق یک اثر زیبا و الهام‌بخش." },
    { index: 4, text: "بهبود یک فرآیند موجود." }
  ]},
  { id: "S7", number: 7, question: "چه سبکی از تفکر به تو نزدیک‌تر است؟", options: [
    { index: 0, text: "تفکر خطی و منطقی." },
    { index: 1, text: "تفکر سیستمی و کل‌نگر." },
    { index: 2, text: "تفکر همدلانه و انسانی." },
    { index: 3, text: "تفکر انتزاعی و فلسفی." },
    { index: 4, text: "تفکر عمل‌گرا و نتیجه‌محور." }
  ]},
  { id: "S8", number: 8, question: "در یک جلسهٔ طوفان فکری، معمولاً چه کار می‌کنی؟", options: [
    { index: 0, text: "ایده‌ها را دسته‌بندی و ارزیابی می‌کنم." },
    { index: 1, text: "ایده‌های عجیب و غریب و خلاقانه می‌دهم." },
    { index: 2, text: "نظرات دیگران را گسترش می‌دهم و به آن‌ها اضافه می‌کنم." },
    { index: 3, text: "ساکت می‌نشینم و بعداً بهترین ایده را انتخاب می‌کنم." },
    { index: 4, text: "سعی می‌کنم زودتر به یک جمع‌بندی عملی برسم." }
  ]},
  { id: "S9", number: 9, question: "چه پاداشی برایت ارزشمندتر است؟", options: [
    { index: 0, text: "تقدیر و احترام دیگران." },
    { index: 1, text: "رضایت درونی از انجام یک کار سخت." },
    { index: 2, text: "مشاهدهٔ تأثیر مستقیم کارم روی زندگی دیگران." },
    { index: 3, text: "آزادی مالی و استقلال." },
    { index: 4, text: "فرصت یادگیری و رشد." }
  ]},
  { id: "S10", number: 10, question: "چگونه در یک موقعیت مبهم و نامشخص تصمیم می‌گیری؟", options: [
    { index: 0, text: "تا جایی که ممکن است اطلاعات جمع‌آوری می‌کنم و بعد تصمیم می‌گیرم." },
    { index: 1, text: "بر اساس غریزه و احساساتم عمل می‌کنم." },
    { index: 2, text: "با افرادی که قابل اعتماد هستند مشورت می‌کنم." },
    { index: 3, text: "تصمیم را به تعویق می‌اندازم تا شرایط شفاف‌تر شود." },
    { index: 4, text: "سریع یک تصمیم می‌گیرم و اگر اشتباه بود، مسیر را عوض می‌کنم." }
  ]},
  { id: "S11", number: 11, question: "کدامیک برایت هیجان‌انگیزتر است؟", options: [
    { index: 0, text: "حل یک معما یا پازل پیچیده." },
    { index: 1, text: "ساختن یک چیز از صفر." },
    { index: 2, text: "مذاکره و متقاعد کردن دیگران." },
    { index: 3, text: "کشف یک مکان یا فرهنگ جدید." },
    { index: 4, text: "بهبود یک رکورد یا رکوردشکنی." }
  ]},
  { id: "S12", number: 12, question: "چه چیزی باعث می‌شود یک روز کاری را عالی بدانی؟", options: [
    { index: 0, text: "پیشرفت قابل‌اندازه‌گیری در پروژه‌ها." },
    { index: 1, text: "روبرو شدن با چالش‌های غیرمنتظره و غلبه بر آن‌ها." },
    { index: 2, text: "ارتباطات خوب و عمیق با همکاران." },
    { index: 3, text: "لحظات خلاقیت و جرقه‌های ذهنی." },
    { index: 4, text: "تکمیل کارها و بستن پرونده‌ها." }
  ]},
  { id: "S13", number: 13, question: "چه نقشی در یک تیم ایفا می‌کنی؟", options: [
    { index: 0, text: "تحلیل‌گر و برنامه‌ریز." },
    { index: 1, text: "ایده‌پرداز و مبتکر." },
    { index: 2, text: "هماهنگ‌کننده و ارتباط‌دهنده." },
    { index: 3, text: "ارزیاب و کنترل‌کننده کیفیت." },
    { index: 4, text: "مجری و عملیات‌کننده." }
  ]},
  { id: "S14", number: 14, question: "چه رویکردی به حل مسئله داری؟", options: [
    { index: 0, text: "تحلیل ریشه‌ای مشکل." },
    { index: 1, text: "آزمایش راه‌حل‌های مختلف." },
    { index: 2, text: "جستجوی راه‌حل‌های مشابه در گذشته." },
    { index: 3, text: "اتکا به ایده‌های جدید و بدیع." },
    { index: 4, text: "تمرکز روی راه‌حل‌هایی که سریع‌تر جواب می‌دهند." }
  ]},
  { id: "S15", number: 15, question: "چه ویژگی‌ای در یک کار برایت اولویت دارد؟", options: [
    { index: 0, text: "دقت و صحت." },
    { index: 1, text: "خلاقیت و نوآوری." },
    { index: 2, text: "تأثیر بر انسان‌ها." },
    { index: 3, text: "معنا و هدف." },
    { index: 4, text: "بازده و سرعت." }
  ]},
  { id: "S16", number: 16, question: "چگونه با حجم بالای اطلاعات برخورد می‌کنی؟", options: [
    { index: 0, text: "ساختاردهی و اولویت‌بندی می‌کنم." },
    { index: 1, text: "به‌سرعت الگوها را تشخیص می‌دهم." },
    { index: 2, text: "با دیگران به اشتراک می‌گذارم تا تحلیل کنند." },
    { index: 3, text: "روی بخشی که بیشترین حس شهودی را دارم تمرکز می‌کنم." },
    { index: 4, text: "سعی می‌کنم همه را بخوانم، اما ممکن است خسته شوم." }
  ]},
  { id: "S17", number: 17, question: "چه چیزی تو را به حرکت وادار می‌کند؟", options: [
    { index: 0, text: "چالش‌های فکری." },
    { index: 1, text: "حس ماجراجویی." },
    { index: 2, text: "ارتباط با آدم‌ها." },
    { index: 3, text: "جستجوی زیبایی و کمال." },
    { index: 4, text: "رقابت و موفقیت." }
  ]},
  { id: "S18", number: 18, question: "در یک بحث علمی، بیشتر به چه چیزی تکیه می‌کنی؟", options: [
    { index: 0, text: "داده‌ها و شواهد." },
    { index: 1, text: "منطق و استدلال." },
    { index: 2, text: "تجربیات عملی." },
    { index: 3, text: "نظریه‌های معتبر." },
    { index: 4, text: "شهود و احساس." }
  ]},
  { id: "S19", number: 19, question: "چه فضایی برای یادگیری برایت جذاب‌تر است؟", options: [
    { index: 0, text: "کلاس درس با ساختار مشخص." },
    { index: 1, text: "آزمایشگاه یا کارگاه عملی." },
    { index: 2, text: "گروه‌های مباحثه و گفتگو." },
    { index: 3, text: "فضای مجازی و منابع آنلاین." },
    { index: 4, text: "طبیعت و محیط‌های باز." }
  ]},
  { id: "S20", number: 20, question: "چه واکنشی به انتقاد نشان می‌دهی؟", options: [
    { index: 0, text: "آن را به‌عنوان فرصت بهبود می‌پذیرم." },
    { index: 1, text: "اگر منطقی باشد می‌پذیرم، در غیر این صورت نادیده می‌گیرم." },
    { index: 2, text: "با دیگران دربارهٔ صحت آن مشورت می‌کنم." },
    { index: 3, text: "ممکن است کمی ناراحت شوم اما بعداً به آن فکر می‌کنم." },
    { index: 4, text: "سعی می‌کنم سریع آن را اصلاح کنم." }
  ]},
  { id: "S21", number: 21, question: "چه چیزی برایت خسته‌کننده است؟", options: [
    { index: 0, text: "کارهای تکراری و بدون چالش." },
    { index: 1, text: "بروکراسی و قوانین دست‌وپاگیر." },
    { index: 2, text: "انزوای اجتماعی و تنهایی." },
    { index: 3, text: "کارهای جزئی و بی‌اهمیت." },
    { index: 4, text: "بی‌برنامگی و بی‌هدفی." }
  ]},
  { id: "S22", number: 22, question: "در مواجهه با یک کار جدید، چه حسی داری؟", options: [
    { index: 0, text: "هیجان و کنجکاوی." },
    { index: 1, text: "اضطراب و استرس." },
    { index: 2, text: "اعتمادبه‌نفس و آمادگی." },
    { index: 3, text: "نیاز به کسب اطلاعات بیشتر." },
    { index: 4, text: "بی‌صبری برای شروع." }
  ]},
  { id: "S23", number: 23, question: "چه سبک رهبری به تو نزدیک‌تر است؟", options: [
    { index: 0, text: "رهبری تحلیلی و مبتنی بر داده." },
    { index: 1, text: "رهبری الهام‌بخش و رویایی." },
    { index: 2, text: "رهبری مشارکتی و دموکراتیک." },
    { index: 3, text: "رهبری خادم و حمایت‌گر." },
    { index: 4, text: "رهبری عملیاتی و اجرایی." }
  ]},
  { id: "S24", number: 24, question: "چه چیزی باعث می‌شود از یک فعالیت لذت ببری؟", options: [
    { index: 0, text: "دیدن نتیجهٔ نهایی کارم." },
    { index: 1, text: "خود فرآیند انجام کار." },
    { index: 2, text: "مشارکت با دیگران." },
    { index: 3, text: "غلبه بر موانع." },
    { index: 4, text: "یادگیری چیزهای جدید." }
  ]},
  { id: "S25", number: 25, question: "چه دیدگاهی به موفقیت داری؟", options: [
    { index: 0, text: "موفقیت یعنی رسیدن به اهداف تعیین‌شده." },
    { index: 1, text: "موفقیت یعنی تجربه‌های جدید و رشد." },
    { index: 2, text: "موفقیت یعنی تأثیر مثبت بر جامعه." },
    { index: 3, text: "موفقیت یعنی خلق چیزی ماندگار." },
    { index: 4, text: "موفقیت یعنی شاد بودن و رضایت." }
  ]}
];

const VALUE_QUESTIONS_HARD = [
  { id: "V1", number: 1, question: "کدام یک برایت مهم‌تر است؟", options: [
    { code: "Q1A", text: "تأثیر مستقیم و فوری بر زندگی یک انسان خاص" },
    { code: "Q1B", text: "بهینه‌سازی یک سیستم که به هزاران نفر کمک می‌کند" }
  ]},
  { id: "V2", number: 2, question: "چه چیزی برایت ارزشمندتر است؟", options: [
    { code: "Q2A", text: "ساختن چیزی که تا سال‌ها باقی بماند" },
    { code: "Q2B", text: "پرورش ایده‌ای که در ذهن‌ها تکثیر شود" }
  ]},
  { id: "V3", number: 3, question: "کدام یک را ترجیح می‌دهی؟", options: [
    { code: "Q3A", text: "روزهایی پر از تنوع و چالش‌های جدید" },
    { code: "Q3B", text: "روزهایی عمیق و متمرکز بر یک موضوع خاص" }
  ]},
  { id: "V4", number: 4, question: "چه چیزی برایت مهم‌تر است؟", options: [
    { code: "Q4A", text: "مسئولیت فردی در قبال کارها" },
    { code: "Q4B", text: "مسئولیت سیستمی در قبال کل سازمان" }
  ]},
  { id: "V5", number: 5, question: "دوست داری چگونه دیده شوی؟", options: [
    { code: "Q5A", text: "به‌عنوان فردی دقیق و منظم" },
    { code: "Q5B", text: "به‌عنوان فردی خلاق و بدیع" }
  ]},
  { id: "V6", number: 6, question: "انرژی خود را از چه چیزی می‌گیری؟", options: [
    { code: "Q6A", text: "تعامل و گفتگو با دیگران" },
    { code: "Q6B", text: "تمرکز عمیق و تنهایی" }
  ]},
  { id: "V7", number: 7, question: "چه مسیری را بیشتر دوست داری؟", options: [
    { code: "Q7A", text: "نوآوری و اختراع راه‌های جدید" },
    { code: "Q7B", text: "مربی‌گری و پرورش استعدادهای دیگران" }
  ]},
  { id: "V8", number: 8, question: "چه چیزی برایت امنیت می‌آورد؟", options: [
    { code: "Q8A", text: "ثبات، امنیت و آینده‌ای قابل‌پیش‌بینی" },
    { code: "Q8B", text: "آزادی، انعطاف و استقلال" }
  ]},
  { id: "V9", number: 9, question: "چه هدفی برایت عمیق‌تر است؟", options: [
    { code: "Q9A", text: "کاهش رنج و درد انسان‌ها" },
    { code: "Q9B", text: "خلق زیبایی، دانش و آگاهی" }
  ]},
  { id: "V10", number: 10, question: "چه نقشی را ترجیح می‌دهی؟", options: [
    { code: "Q10A", text: "رهبری و تعیین مسیر برای دیگران" },
    { code: "Q10B", text: "همدلی و وفاق‌سازی در تیم" }
  ]},
  { id: "V11", number: 11, question: "چه چیزی برایت لذت‌بخش‌تر است؟", options: [
    { code: "Q11A", text: "کار با داده‌ها، الگوریتم‌ها و سیستم‌ها" },
    { code: "Q11B", text: "کار با انسان‌ها، احساسات و ارتباطات" }
  ]},
  { id: "V12", number: 12, question: "چه چیزی تو را به جلو می‌برد؟", options: [
    { code: "Q12A", text: "خطرپذیری و امتحان کردن مسیرهای نرفته" },
    { code: "Q12B", text: "ثبات‌طلبی و حرکت در مسیرهای مطمئن" }
  ]},
  { id: "V13", number: 13, question: "چه نوع تأثیری را دوست داری بگذاری؟", options: [
    { code: "Q13A", text: "نتیجهٔ فوری و قابل‌مشاهده" },
    { code: "Q13B", text: "اثر ماندگار و بلندمدت" }
  ]},
  { id: "V14", number: 14, question: "چه رابطه‌ای با سازمان یا تیم داری؟", options: [
    { code: "Q14A", text: "استقلال کامل و کار به‌عنوان یک فرد مستقل" },
    { code: "Q14B", text: "تعلق سازمانی و همکاری در یک تیم بزرگ" }
  ]},
  { id: "V15", number: 15, question: "چه چیزی برایت خوشایندتر است؟", options: [
    { code: "Q15A", text: "تسلط عمیق بر یک حوزهٔ خاص" },
    { code: "Q15B", text: "کنجکاوی بی‌پایان و یادگیری مداوم" }
  ]}
];

// ==================== ذخیره و بازیابی ====================
function saveSession() {
  try {
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
      completedSubRealms: [...state.completedSubRealms],
      cardLikeStatus: Array.from(state.cardLikeStatus.entries())
    };
    localStorage.setItem('darkhorse_session_v2', JSON.stringify(sessionData));
  } catch (e) { console.warn('ذخیره session ناموفق:', e); }
}

function loadSession() {
  try {
    const saved = localStorage.getItem('darkhorse_session_v2');
    if (!saved) return false;
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
    if (data.cardLikeStatus) state.cardLikeStatus = new Map(data.cardLikeStatus);
    return true;
  } catch (e) { return false; }
}

function clearSession() { localStorage.removeItem('darkhorse_session_v2'); }

// ==================== بارگذاری داده‌ها (Hardcoded) ====================
function loadHardcodedQuestions() {
  state.strategyQuestions = STRATEGY_QUESTIONS_HARD;
  state.valueQuestions = VALUE_QUESTIONS_HARD;
  state.questionsReady = true;
  console.log(`✅ ${state.strategyQuestions.length} سوال راهبردی و ${state.valueQuestions.length} سوال ارزشی (Hardcoded) بارگذاری شد.`);
}

async function loadMicroMotivesMap() {
  try {
    const res = await fetch('./micro_motives.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const all = await res.json();
    if (!Array.isArray(all)) throw new Error('فرمت داده نامعتبر');
    all.forEach(m => { state.microMotivesMap[m.code] = m.description_fa; });
    state.motivesReady = true;
    console.log(`✅ ${all.length} میکروموتیو از فایل بارگذاری شد.`);
    state.cachedMotives = all;
  } catch (e) {
    console.warn('⚠️ بارگذاری micro_motives.json ناموفق (یا وجود ندارد). از داده‌های خالی استفاده می‌شود.', e);
    state.motivesReady = false;
    state.cachedMotives = [];
  }
}

// ==================== بررسی داده‌های استاتیک ====================
function ensureStaticData() {
  if (typeof REALMS === 'undefined') {
    app.innerHTML = `
      <div style="text-align:center;padding:40px;color:#f0c040;">
        <h2>⚠️ خطا در بارگذاری داده</h2>
        <p style="color:#b0a080;">فایل data.js بارگذاری نشده است. لطفاً مطمئن شوید که data.js قبل از app.js در HTML قرار دارد.</p>
        <button class="btn btn-primary" onclick="location.reload()">🔄 بارگذاری مجدد</button>
      </div>
    `;
    return false;
  }
  return true;
}

// ==================== NAVIGATION ====================
function goTo(stage) {
  if (!ensureStaticData()) return;
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
  if (!ensureStaticData()) return;
  console.log(`🔄 رندر: ${state.stage}`);
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
    case 'results': renderResults(); break;
    default: app.innerHTML = `<p style="color:#f0c040;">مرحلهٔ ناشناخته: ${state.stage}</p>`;
  }
}

// ==================== صفحات (ساده و کاربردی) ====================
function renderManifesto() {
  app.innerHTML = `
    <div style="text-align:center;padding:20px;">
      <div style="font-size:3rem;margin-bottom:15px;">🐴</div>
      <h1 style="color:#f0c040;font-size:1.6rem;margin-bottom:10px;">انقلاب شخصی‌سازی</h1>
      <p style="color:#b0a080;font-style:italic;margin-bottom:20px;">انتخاب رشته با معیار خودت، نه رتبه‌ات</p>
      <div class="card" style="text-align:right;">
        <p style="color:#b0a080;line-height:2.2;font-size:0.9rem;">
          <strong style="color:#f0c040;">«موفقیت از تقلید دیگران به دست نمی‌آید، بلکه از شناخت دقیق فردیت و ساختن مسیر شخصی حاصل می‌شود.»</strong>
          <br><span style="color:#888;font-size:0.8rem;">— تاد رز، نویسندهٔ کتاب «اسب سیاه»</span>
        </p>
        <p style="color:#d4af37;line-height:2.2;font-size:0.9rem;margin-top:15px;">
          <strong>این یک تست نیست — یک سفر اکتشافی به درون خودت است.</strong>
        </p>
      </div>
      <button class="btn btn-primary" style="margin-top:20px;width:100%;" onclick="goTo('guide')">🚀 شروع سفر اکتشافی</button>
    </div>`;
}

function renderGuide() {
  app.innerHTML = `
    <div style="text-align:right;padding:10px;">
      <h2 style="color:#f0c040;text-align:center;">⏳ پیش از شروع</h2>
      <div class="card">
        <p style="color:#b0a080;line-height:2.2;">این سفر سه لایه دارد: خرده‌انگیزه‌ها (۶۰٪)، راهبردهای شخصی (۲۰٪) و ارزش‌های بنیادین (۲۰٪).</p>
        <p style="color:#b0a080;line-height:2.2;">از میان ۱۰۹۹ خرده‌انگیزه، حداقل ۲۰ و حداکثر ۸۰ مورد را انتخاب کن.</p>
      </div>
      <button class="btn btn-primary" style="width:100%;margin-top:15px;" onclick="goTo('splash')">🚀 ورود به شهر رؤیاها</button>
      <button class="btn" style="width:100%;margin-top:8px;" onclick="goBack()">⬅️ بازگشت</button>
    </div>`;
}

function renderSplash() {
  const hasSession = localStorage.getItem('darkhorse_session_v2');
  app.innerHTML = `
    <div style="text-align:center;padding:20px;">
      <div style="font-size:4rem;">🐴</div>
      <h1 style="color:#f0c040;">اسب سیاه</h1>
      <div class="card">
        <p class="quote">«شهر رؤیاها، جایی که هر کودکی قبل از خواب به آن سفر می‌کرد...»</p>
        <p><strong>کدام یک از این محله‌ها، هنوز هم قلبت را به تپش می‌اندازد؟</strong></p>
        ${hasSession ? `<button class="btn btn-primary" onclick="resumeJourney()">📋 ادامهٔ سفر ناتمام</button>` : `<button class="btn btn-primary" onclick="startNewJourney()">ادامه</button>`}
      </div>
    </div>`;
}

function startNewJourney() {
  clearSession();
  state.sessionId = crypto.randomUUID ? crypto.randomUUID() : 'id-' + Date.now();
  state.stage = 'realm';
  state.history = [];
  state.selectedRealms = [];
  state.selectedSubRealms = [];
  state.selectedNarrowPaths = [];
  state.likedCodes = [];
  state.strategyAnswers = [];
  state.valueAnswers = [];
  state.currentQuestion = 0;
  state.currentValueQuestion = 0;
  state.likedCodesSet.clear();
  state.completedPaths.clear();
  state.completedSubRealms.clear();
  state.swipeIndex = 0;
  state.totalSwipes = 0;
  state.lastPayload = null;
  state.cachedMotives = null;
  state.retryCount = 0;
  state.cardLikeStatus.clear();
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

// ==================== انتخاب قلمروها ====================
function renderRealm() {
  const maxSelect = Math.min(3, REALMS.length);
  let html = `<h2>🌃 شهر رؤیاها</h2>
    <p style="color:#b0a080;">کدام محله‌ها تو را صدا می‌زنند؟ (۱ تا ${maxSelect})</p>
    <p style="color:#f0c040;">💛 جرقه‌های تو: <strong>${state.likedCodes.length}</strong></p>
    <div class="grid">`;
  REALMS.forEach(r => {
    const selected = state.selectedRealms.includes(r.id) ? 'selected' : '';
    html += `<div class="option ${selected}" onclick="toggleRealm('${r.id}')">
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

// ==================== زیر قلمروها ====================
function renderSubRealm() {
  const subs = [];
  state.selectedRealms.forEach(realmId => { if (SUB_REALMS[realmId]) subs.push(...SUB_REALMS[realmId]); });
  const maxSelect = Math.min(3 * state.selectedRealms.length, subs.length);
  let html = `<h2>راهروهای محله</h2>
    <p style="color:#b0a080;">(۱ تا ${maxSelect} گذر انتخاب کن)</p>
    <div class="grid">`;
  subs.forEach(s => {
    const selected = state.selectedSubRealms.includes(s.id) ? 'selected' : '';
    const completed = state.completedSubRealms.has(s.id) ? '✅' : '';
    html += `<div class="option ${selected}" onclick="toggleSub('${s.id}', ${maxSelect})">
      <span class="option-icon">${s.icon}</span>
      <strong>${escapeHtml(s.name)} ${completed}</strong>
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

// ==================== مسیرهای باریک ====================
function renderNarrowPath() {
  const paths = [];
  state.selectedSubRealms.forEach(subId => { if (NARROW_PATHS[subId]) paths.push(...NARROW_PATHS[subId]); });
  let html = `<h2>مسیرهای باریک</h2>
    <div class="grid">`;
  paths.forEach(p => {
    const selected = state.selectedNarrowPaths.includes(p.id) ? 'selected' : '';
    html += `<div class="option ${selected}" onclick="togglePath('${p.id}')">
      <span class="option-icon">${p.icon}</span>
      <strong>${escapeHtml(p.name)}</strong>
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

// ==================== جرقه‌ها (Swipe) ====================
function renderIntroSwipe() {
  app.innerHTML = `
    <h2>🔥 به عمیق‌ترین لایه وجودت رسیدی!</h2>
    <div class="card">
      <p style="color:#b0a080;">در این مرحله، فعالیت‌های جزئی‌ای را می‌بینی. آن‌هایی که واقعاً به تو انرژی می‌دهند، ❤️ بزن.</p>
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
    if (state.cachedMotives && state.cachedMotives.length > 0) {
      all = state.cachedMotives;
    } else {
      const res = await fetch('./micro_motives.json');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      all = await res.json();
      state.cachedMotives = all;
    }
    state.swipeCards = all.filter(m =>
      majorCodes.some(prefix => m.code.startsWith(prefix)) && !state.likedCodesSet.has(m.code)
    );
    state.swipeIndex = 0;
    state.totalSwipes = state.swipeCards.length;
    state.cardLikeStatus.clear();
    if (state.swipeCards.length === 0) {
      alert('هیچ جرقهٔ جدیدی برای این مسیر باقی نمانده است.');
      goBack();
      return;
    }
    goTo('swipe');
  } catch (e) {
    console.error('خطا در بارگذاری جرقه‌ها:', e);
    alert('خطا در بارگذاری جرقه‌ها. لطفاً دوباره تلاش کنید.');
  }
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

function renderSwipe() {
  if (state.swipeIndex >= state.swipeCards.length) {
    app.innerHTML = `<h2>✅ پایان جرقه‌ها</h2>
      <div class="card"><p>شما ${state.likedCodes.length} جرقه انتخاب کردید.</p>
      <button class="btn btn-primary" onclick="finishSwipe()">🚀 ادامه به لایهٔ دوم</button></div>`;
    return;
  }
  const card = state.swipeCards[state.swipeIndex];
  const progress = state.totalSwipes > 0 ? ((state.swipeIndex + 1) / state.totalSwipes) * 100 : 0;
  app.innerHTML = `
    <h2>🔥 جرقهٔ انرژی</h2>
    <div style="color:#f0c040;">💛 <strong>${state.likedCodes.length}</strong> جرقه</div>
    <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
    <div class="swipe-card">
      <p style="font-size:1.2rem;line-height:2.2;">${escapeHtml(card.description_fa)}</p>
      <button class="btn btn-heart" onclick="likeCard(true)">❤️ جرقه زد</button>
      <button class="btn btn-skip" onclick="likeCard(false)">❌ ادامه</button>
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

function finishSwipe() {
  state.currentQuestion = 0;
  state.currentValueQuestion = 0;
  state.strategyAnswers = [];
  goTo('introStrategies');
}

// ==================== راهبردها ====================
function renderIntroStrategies() {
  app.innerHTML = `
    <h2>🧭 لایهٔ دوم: راهبردهای فردی</h2>
    <div class="card">
      <p style="color:#b0a080;">۲۵ موقعیت واقعی پیش روی توست.</p>
      <button class="btn btn-primary" onclick="goTo('strategies')">🚀 شروع</button>
    </div>`;
}

function renderStrategy() {
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
    const selected = currentAnswer === o.index ? 'border:2px solid #f0c040;' : '';
    html += `<button class="btn" style="display:block;width:100%;text-align:right;margin-bottom:8px;${selected}" onclick="answerStrategy(${o.index})">${escapeHtml(o.text)}</button>`;
  });
  html += `</div>`;
  app.innerHTML = html;
}

function answerStrategy(idx) {
  state.strategyAnswers[state.currentQuestion] = idx;
  state.currentQuestion++;
  saveSession();
  render();
}

// ==================== ارزش‌ها ====================
function renderIntroValues() {
  app.innerHTML = `
    <h2>⚖️ لایهٔ سوم: ارزش‌های بنیادین</h2>
    <div class="card">
      <p style="color:#b0a080;">۱۵ دوگانهٔ قدرتمند.</p>
      <button class="btn btn-primary" onclick="goTo('values')">🚀 شروع</button>
    </div>`;
}

function renderValue() {
  if (state.currentValueQuestion >= state.valueQuestions.length) {
    app.innerHTML = `<h2>✅ پایان سفر</h2>
      <button class="btn btn-primary" onclick="submitResults()">🚀 تحلیل نتایج</button>`;
    return;
  }
  const q = state.valueQuestions[state.currentValueQuestion];
  const opts = q.options;
  const currentAnswer = state.valueAnswers[state.currentValueQuestion];
  app.innerHTML = `
    <h2>⚖️ ارزش ${q.number} از ${state.valueQuestions.length}</h2>
    <div class="card">
      <p style="margin-bottom:20px;color:#f0c040;">${escapeHtml(q.question)}</p>
      <button class="btn" style="display:block;width:100%;margin-bottom:10px;${currentAnswer === opts[0].code ? 'border:2px solid #f0c040;' : ''}" onclick="answerValue('${opts[0].code}')">${escapeHtml(opts[0].text)}</button>
      <button class="btn" style="display:block;width:100%;${currentAnswer === opts[1].code ? 'border:2px solid #f0c040;' : ''}" onclick="answerValue('${opts[1].code}')">${escapeHtml(opts[1].text)}</button>
    </div>`;
}

function answerValue(code) {
  state.valueAnswers[state.currentValueQuestion] = code;
  state.currentValueQuestion++;
  saveSession();
  render();
}

// ==================== ارسال به سرور ====================
async function submitResults() {
  app.innerHTML = `<h2>⏳ در حال تحلیل...</h2>`;
  const payload = buildPayload();
  try {
    const res = await fetch(API_BASE + '/api/v2/darkhorse/discover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    clearSession();
    displayResults(data);
  } catch (e) {
    console.error(e);
    app.innerHTML = `<h2>❌ خطا</h2><p>نتوانستیم با سرور ارتباط برقرار کنیم.</p>
      <button class="btn" onclick="submitResults()">🔄 تلاش دوباره</button>`;
  }
}

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
  return { micro_motives: state.likedCodes, sjt_answers: sjt, conjoint_choices: conj };
}

// ==================== نمایش نتایج ====================
function displayResults(data) {
  const items = data.discovery_result?.recommendations || [];
  const matched = items.filter(item => (item.fit_score || 0) >= 30).sort((a, b) => (b.fit_score || 0) - (a.fit_score || 0));
  let html = `<h2>📊 نتایج</h2><p>بر اساس ${state.likedCodes.length} خرده‌انگیزه:</p>`;
  if (matched.length === 0) {
    html += `<p style="color:#f0c040;">هیچ رشته‌ای به آستانهٔ ۳۰٪ نرسیده است.</p>`;
  } else {
    matched.forEach(r => {
      html += `<div class="card"><h3 style="color:#f0c040;">${escapeHtml(r.major_name_fa || 'رشته')}</h3>
        <div class="progress-bar"><div class="progress-fill" style="width:${r.fit_score || 0}%"></div></div>
        <p>🔹 <strong>${r.fit_score || 0}%</strong> تطابق</p></div>`;
    });
  }
  html += `<button class="btn btn-primary" onclick="resetJourney()">شروع دوباره</button>`;
  app.innerHTML = html;
}

// ==================== Reset ====================
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
  state.cardLikeStatus.clear();
  render();
}

// ==================== مقداردهی اولیه ====================
async function init() {
  console.log('⏳ مقداردهی اولیه...');
  
  if (typeof REALMS === 'undefined') {
    app.innerHTML = `
      <div style="text-align:center;padding:40px;color:#f0c040;">
        <h2>⚠️ خطا در بارگذاری داده</h2>
        <p style="color:#b0a080;">فایل data.js بارگذاری نشده است.</p>
        <button class="btn btn-primary" onclick="location.reload()">🔄 بارگذاری مجدد</button>
      </div>
    `;
    return;
  }
  console.log(`✅ REALMS loaded: ${REALMS.length} items`);

  loadHardcodedQuestions();
  await loadMicroMotivesMap();

  if (localStorage.getItem('darkhorse_session_v2')) {
    loadSession();
    console.log('📂 Session بازیابی شد.');
  }

  render();
  console.log('✅ برنامه راه‌اندازی شد.');
}

// اجرا
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
