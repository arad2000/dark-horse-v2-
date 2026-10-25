// Dark Horse V2 — UX Polish Patch
// Runtime patch loaded after app.js; the core app.js and engine remain untouched.
(function () {
  'use strict';

  const safeAfterRender = (fn) => { try { fn(); } catch (e) { console.warn('Dark Horse UX patch:', e); } };

  function patchSparkChip() {
    if (typeof window.sparkChipHTML !== 'function') return;
    const original = window.sparkChipHTML;
    if (original.__dhPatched) return;
    const patched = function () {
      const n = Array.isArray(state.likedCodes) ? state.likedCodes.length : 0;
      const hint = n < 20
        ? `${20 - n} جرقه تا حداقل`
        : n < 30
          ? 'حداقل ثبت شد · ۳۰ تا ۴۰ جرقه پیشنهاد می‌شود'
          : n <= 40
            ? 'در محدودهٔ پیشنهادی'
            : n >= 80
              ? 'سقف انتخاب تکمیل شد'
              : 'انتخاب‌های بیشتر هم مجاز است';
      return `<div class="dh-spark-chip">✦ ${n} جرقه <span style="color:#8a7a55;font-size:.75rem">· ${hint}</span></div>`;
    };
    patched.__dhPatched = true;
    window.sparkChipHTML = patched;
  }

  // IMPORTANT: spark-card order is part of the assessment presentation.
  // Do not shuffle, reseed, or otherwise reorder the cards in the UX layer.
  // The underlying app.js remains the single source of truth for sampling,
  // identity/code mapping, progress and response collection.

  function patchSwipeLabels() {
    if (typeof window.renderSwipe !== 'function') return;
    const original = window.renderSwipe;
    if (original.__dhPatched) return;
    const patched = function () {
      original();
      safeAfterRender(() => {
        document.querySelectorAll('.btn-skip').forEach(btn => {
          if (/❌/.test(btn.textContent || '') || /ادامه/.test(btn.textContent || '')) btn.textContent = '❌ جذبم نکرد';
        });
        document.querySelectorAll('.swipe-card').forEach(card => {
          card.innerHTML = card.innerHTML
            .replace(/حداقل ۲۰\s*-\s*حداکثر ۸۰/g, 'حداقل ۲۰ · پیشنهاد ۳۰ تا ۴۰ · سقف ۸۰')
            .replace(/هرچه جرقه‌های بیشتری بزنی، خودِ واقعی‌ات را دقیق‌تر کشف می‌کنی/g, '۳۰ تا ۴۰ جرقه معمولاً برای ساختن تصویر دقیق‌تر کافی است؛ انتخاب بیشتر هم امکان‌پذیر است.')
            .replace(/هرچه بیشتر بزنی، دقیق‌تر کشف می‌شوی/g, '۳۰ تا ۴۰ جرقه معمولاً برای ساختن تصویر دقیق‌تر کافی است؛ انتخاب بیشتر هم امکان‌پذیر است.');
        });
      });
    };
    patched.__dhPatched = true;
    window.renderSwipe = patched;
  }

  function patchStrategyIntro() {
    if (typeof window.renderIntroStrategies !== 'function') return;
    const original = window.renderIntroStrategies;
    if (original.__dhPatched) return;
    const patched = function () {
      original();
      safeAfterRender(() => {
        const card = document.querySelector('.card');
        if (!card || card.querySelector('.dh-response-hint')) return;
        const p = document.createElement('p');
        p.className = 'dh-response-hint';
        p.style.cssText = 'color:#d4af37;line-height:2;margin:10px 0;font-size:.9rem;';
        p.textContent = 'جواب ایده‌آل را انتخاب نکن؛ چیزی را بزن که معمولاً واقعاً انجام می‌دهی، حتی اگر به نظرت بهترین رفتار نباشد.';
        card.insertBefore(p, card.querySelector('button'));
      });
    };
    patched.__dhPatched = true;
    window.renderIntroStrategies = patched;
  }

  function patchStrategyQuestion() {
    if (typeof window.renderStrategy !== 'function') return;
    const original = window.renderStrategy;
    if (original.__dhPatched) return;
    const patched = function () {
      original();
      safeAfterRender(() => {
        const h2 = document.querySelector('h2');
        const q = state.strategyQuestions ? state.strategyQuestions[state.currentQuestion] : null;
        if (!h2 || !q || !/راهبرد/.test(h2.textContent || '')) return;
        h2.innerHTML = `🧭 وقتی این اتفاق می‌افتد، معمولاً چه می‌کنی؟<span style="display:block;font-size:.78rem;color:#8a7a55;font-weight:400;margin-top:6px">موقعیت ${q.number} از ${state.strategyQuestions.length}</span>`;
      });
    };
    patched.__dhPatched = true;
    window.renderStrategy = patched;
  }

  function patchValueIntro() {
    if (typeof window.renderIntroValues !== 'function') return;
    const original = window.renderIntroValues;
    if (original.__dhPatched) return;
    const patched = function () {
      original();
      safeAfterRender(() => {
        const h2 = document.querySelector('h2');
        if (h2 && /ارزش‌های بنیادین/.test(h2.textContent || '')) h2.textContent = '⚖️ مرحلهٔ سوم: چه چیزی برایت مهم است؟';
        const card = document.querySelector('.card');
        const p = card && card.querySelector('p');
        if (p) p.innerHTML = 'اینجا بین دو گزینه انتخاب می‌کنی که هر دو می‌توانند ارزشمند باشند. جواب درست یا غلطی وجود ندارد. اگر مجبور باشی یکی را بیشتر ترجیح بدهی، کدام به زندگی‌ای که برای خودت می‌خواهی نزدیک‌تر است؟';
      });
    };
    patched.__dhPatched = true;
    window.renderIntroValues = patched;
  }

  function patchValueCompletion() {
    if (typeof window.renderValue !== 'function') return;
    const original = window.renderValue;
    if (original.__dhPatched) return;
    const patched = function () {
      original();
      safeAfterRender(() => {
        const h2 = document.querySelector('h2');
        if (!h2 || !/پایان سفر اکتشافی/.test(h2.textContent || '')) return;
        h2.textContent = '✅ تصویر اولیهٔ تو آماده شد';
        const p = h2.parentElement && h2.parentElement.querySelector('.card p');
        if (p) p.textContent = 'جرقه‌ها، راهبردها و ارزش‌هایت را کنار هم گذاشتیم. حالا ببینیم این ترکیب در چه مسیرهایی خودش را بهتر نشان می‌دهد.';
      });
    };
    patched.__dhPatched = true;
    window.renderValue = patched;
  }

  function inferAlternativeReason(path) {
    const vd = Number(path && path.value_distance);
    const sd = Number(path && path.strategy_distance);
    if (!Number.isFinite(vd) || !Number.isFinite(sd)) return '';
    if (Math.abs(vd - sd) < 0.02) return 'از نظر ارزش‌ها و راهبردها نزدیک است';
    return vd < sd ? 'از نظر ارزش‌ها نزدیک‌تر است' : 'از نظر راهبردها نزدیک‌تر است';
  }

  function patchResultsUI() {
    if (typeof window.displayResults !== 'function') return;
    const original = window.displayResults;
    if (original.__dhPatched) return;
    const patched = function (data, type) {
      original(data, type);
      safeAfterRender(() => {
        document.querySelectorAll('[style*="background:#d4af37"]').forEach(el => {
          const t = (el.textContent || '').trim();
          if (/^\d+(?:\.\d+)?%$/.test(t) && !/همخوانی/.test(t)) {
            el.textContent = `${t} همخوانی`;
            el.style.fontSize = '.82rem';
          }
        });

        if (!document.querySelector('.dh-score-note')) {
          const h2 = document.querySelector('h2');
          if (h2 && /نتیجه/.test(h2.textContent || '')) {
            const note = document.createElement('p');
            note.className = 'dh-score-note';
            note.style.cssText = 'text-align:center;color:#8a7a55;font-size:.76rem;line-height:1.8;margin:4px 0 10px;';
            note.textContent = 'این درصد، میزان همخوانی با الگوی فردیت توست؛ احتمال موفقیت یا قبولی نیست.';
            h2.insertAdjacentElement('afterend', note);
          }
        }

        document.querySelectorAll('p').forEach(p => {
          if ((p.textContent || '').includes('بهترین شاخهٔ پیشنهادی')) {
            p.innerHTML = p.innerHTML.replace('🏆 بهترین شاخهٔ پیشنهادی:', '🧭 شاخه‌ای که در حال حاضر بیشترین همخوانی را دارد:');
            const next = p.nextElementSibling;
            if (next && /این شاخه بیشترین هماهنگی/.test(next.textContent || '')) next.textContent = 'این نتیجه نقطه شروع بررسی است، نه تصمیم نهایی.';
          }
        });

        document.querySelectorAll('div').forEach(box => {
          if (!(box.textContent || '').trim().startsWith('🔄 مسیرهای جایگزین:')) return;
          const label = box.querySelector('div');
          if (label) label.textContent = '🔄 مسیرهای نزدیک دیگر:';
          if (box.querySelector('.dh-alt-reason')) return;

          const sourceItems = type === 'branches'
            ? ((data && data.branch_discovery_result && data.branch_discovery_result.branches) || [])
            : ((data && data.discovery_result && data.discovery_result.recommendations) || []);
          const allItems = [];
          sourceItems.forEach(item => (item.alternative_paths || []).forEach(p => allItems.push(p)));

          const reasons = [];
          box.querySelectorAll('span').forEach(chip => {
            const name = (chip.textContent || '').trim();
            const found = allItems.find(p => (p.branch_name || p.major_name || p.name || '').trim() === name);
            const reason = inferAlternativeReason(found);
            if (reason) reasons.push(`${name}: ${reason}`);
          });

          if (reasons.length) {
            const small = document.createElement('div');
            small.className = 'dh-alt-reason';
            small.style.cssText = 'color:#8a7a55;font-size:.76rem;line-height:1.9;margin-top:7px;';
            small.textContent = reasons.join(' · ');
            box.appendChild(small);
          }
        });
      });
    };
    patched.__dhPatched = true;
    window.displayResults = patched;
  }

  function installVisualSystem() {
    if (document.getElementById('dh-visual-polish-v1')) return;
    const style = document.createElement('style');
    style.id = 'dh-visual-polish-v1';
    style.textContent = `
      /* V21.1 visual polish: semantic tab icons, clearer hierarchy, typography and contrast. */
      #dh-tabbar button { font-size: .80rem !important; color: #a99d88 !important; min-height: 56px !important; }
      #dh-tabbar button.active { color: #f0c040 !important; }
      #dh-tabbar button .ico { font-size: 0 !important; width: 24px; height: 24px; line-height: 24px; display: inline-flex; align-items: center; justify-content: center; }
      #dh-tabbar button .ico::before { content: ''; display: block; width: 22px; height: 22px; background-repeat: no-repeat; background-position: center; background-size: 22px 22px; opacity: .90; }
      #dh-tabbar button.active .ico::before { opacity: 1; }
      #dh-tabbar button[data-tab="home"] .ico::before {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23F0C040' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m3 10 9-7 9 7'/%3E%3Cpath d='M5 9v11h14V9'/%3E%3Cpath d='M9 20v-6h6v6'/%3E%3C/svg%3E");
      }
      #dh-tabbar button[data-tab="journey"] .ico::before {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23F0C040' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='8.5'/%3E%3Cpath d='M12 7v5l3 2'/%3E%3Cpath d='M9.5 4.8 12 3l2.5 1.8'/%3E%3C/svg%3E");
      }
      #dh-tabbar button[data-tab="profile"] .ico::before {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23F0C040' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='8' r='3.5'/%3E%3Cpath d='M5 20c.8-3.3 3.2-5 7-5s6.2 1.7 7 5'/%3E%3C/svg%3E");
      }
      #dh-tabbar button:not(.active) .ico::before { filter: saturate(.7) brightness(.76); }
      #dh-tabbar button.active { box-shadow: inset 0 2px 0 #d4af37; }

      .dh-home-wrap { display: flex !important; flex-direction: column !important; }
      .dh-home-top { order: 0 !important; }
      .dh-cta-card { order: 1 !important; border-color: rgba(212,175,55,.42) !important; box-shadow: 0 10px 30px rgba(0,0,0,.22); }
      .dh-quote-hero { order: 2 !important; }
      .dh-feature-row { order: 3 !important; }
      .dh-mini-grid { order: 4 !important; }
      .dh-feature-row { opacity: .94; }

      .dh-brand-name { font-size: 1.42rem !important; }
      .dh-brand-sub { font-size: .82rem !important; color: #b8ad97 !important; }
      .dh-greet { font-size: 1.10rem !important; }
      .dh-date { font-size: .84rem !important; color: #b8ad97 !important; }
      .dh-chip { font-size: .76rem !important; }
      .dh-quote-label { font-size: .95rem !important; }
      .dh-quote-sub { font-size: .82rem !important; color: #a99d88 !important; }
      .dh-q-line p { font-size: 1rem !important; line-height: 1.95 !important; }
      .dh-q-tag { font-size: .76rem !important; color: #a99d88 !important; }
      .dh-quote-foot { font-size: .74rem !important; color: #8f8268 !important; }
      .dh-cta-title { font-size: 1.08rem !important; }
      .dh-cta-desc { font-size: .92rem !important; color: #b8ad97 !important; }
      .dh-feature .dh-f-t { font-size: .84rem !important; }
      .dh-feature .dh-f-d { font-size: .74rem !important; color: #a99d88 !important; }
      .dh-mini { font-size: .88rem !important; color: #d0c29e !important; }
      .dh-stat .l { font-size: .80rem !important; color: #a99d88 !important; }
      .dh-last-meta { font-size: .80rem !important; color: #a99d88 !important; }
      .dh-last-name { font-size: .92rem !important; }
      .dh-last-score { font-size: .88rem !important; }
    `;
    document.head.appendChild(style);
  }

  function install() {
    patchSparkChip();
    patchSwipeLabels();
    patchStrategyIntro();
    patchStrategyQuestion();
    patchValueIntro();
    patchValueCompletion();
    patchResultsUI();
    installVisualSystem();
    if (typeof window.render === 'function' && state && state.stage !== 'manifesto') {
      setTimeout(() => window.render(), 0);
    }
  }

  install();
})();
