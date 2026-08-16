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

  function patchSwipeLoading() {
    if (typeof window.loadSwipeCards !== 'function') return;
    const original = window.loadSwipeCards;
    if (original.__dhPatched) return;
    const patched = async function () {
      await original();
      if (state.stage === 'swipe' && Array.isArray(state.swipeCards) && state.swipeCards.length > 1) {
        for (let i = state.swipeCards.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [state.swipeCards[i], state.swipeCards[j]] = [state.swipeCards[j], state.swipeCards[i]];
        }
        state.swipeIndex = 0;
        state.totalSwipes = state.swipeCards.length;
        if (typeof window.render === 'function') window.render();
      }
    };
    patched.__dhPatched = true;
    window.loadSwipeCards = patched;
  }

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

  function install() {
    patchSparkChip();
    patchSwipeLoading();
    patchSwipeLabels();
    patchStrategyIntro();
    patchStrategyQuestion();
    patchValueIntro();
    patchValueCompletion();
    patchResultsUI();
    if (typeof window.render === 'function' && state && state.stage !== 'manifesto') {
      setTimeout(() => window.render(), 0);
    }
  }

  install();
})();
