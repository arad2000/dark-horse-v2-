/**
 * Dark Horse — Tactile Journey Physics, Keyboard Flow & Story Card Export
 * Pure client-side UX layer — zero impact on scoring formulas, catalog, or quota contracts.
 */
(function () {
  'use strict';

  function haptic(ms) {
    try {
      if (navigator && typeof navigator.vibrate === 'function') {
        navigator.vibrate(ms || 12);
      }
    } catch (_) {}
  }

  function isInteractiveTarget(el) {
    if (!el || typeof el.closest !== 'function') return false;
    return Boolean(el.closest('button, a, summary, details, input, select, textarea'));
  }

  // ==================== 1. 60-FPS Pointer Drag & Tilt on #dh-swipe-card ====================
  function bindSwipeGestureDelegation() {
    var root = document.getElementById('app');
    if (!root || root.__dhSwipeGestureBound) return;
    root.__dhSwipeGestureBound = true;

    var drag = null;

    root.addEventListener('pointerdown', function (e) {
      if (e.button && e.button !== 0) return;
      if (isInteractiveTarget(e.target)) return;
      var card = e.target && typeof e.target.closest === 'function'
        ? e.target.closest('#dh-swipe-card')
        : null;
      if (!card) return;

      drag = {
        pointerId: e.pointerId,
        card: card,
        startX: e.clientX,
        startY: e.clientY,
        dx: 0,
        dy: 0,
        locked: null, // 'x' | 'y'
        likeStamp: card.querySelector('.dh-swipe-stamp--like'),
        skipStamp: card.querySelector('.dh-swipe-stamp--skip')
      };
    }, { passive: true });

    root.addEventListener('pointermove', function (e) {
      if (!drag || e.pointerId !== drag.pointerId) return;
      var dx = e.clientX - drag.startX;
      var dy = e.clientY - drag.startY;
      drag.dx = dx;
      drag.dy = dy;

      if (!drag.locked) {
        if (Math.abs(dx) < 9 && Math.abs(dy) < 9) return;
        drag.locked = Math.abs(dx) > Math.abs(dy) * 1.15 ? 'x' : 'y';
        if (drag.locked === 'x') {
          drag.card.classList.add('is-dragging');
          try { drag.card.setPointerCapture(e.pointerId); } catch (_) {}
        }
      }
      if (drag.locked !== 'x') return;

      var rot = Math.max(-13, Math.min(13, dx * 0.055));
      var lift = Math.min(18, Math.abs(dx) * 0.08);
      drag.card.style.transform = 'translate3d(' + dx.toFixed(1) + 'px,' + (-lift * 0.35).toFixed(1) + 'px,0) rotate(' + rot.toFixed(2) + 'deg)';

      var ratio = Math.min(1, Math.abs(dx) / 72);
      if (drag.likeStamp) drag.likeStamp.style.opacity = dx > 12 ? String(ratio.toFixed(2)) : '0';
      if (drag.skipStamp) drag.skipStamp.style.opacity = dx < -12 ? String(ratio.toFixed(2)) : '0';
    }, { passive: true });

    function finishDrag(cancelled) {
      if (!drag) return;
      var cur = drag;
      drag = null;
      var card = cur.card;
      card.classList.remove('is-dragging');

      if (!cancelled && cur.locked === 'x' && Math.abs(cur.dx) >= 72 && typeof window.likeCard === 'function') {
        var liked = cur.dx > 0;
        var exitX = liked ? 360 : -360;
        var exitRot = liked ? 18 : -18;
        haptic(14);
        card.style.transition = 'transform 0.19s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.19s ease';
        card.style.transform = 'translate3d(' + exitX + 'px, -12px, 0) rotate(' + exitRot + 'deg)';
        card.style.opacity = '0.25';
        setTimeout(function () {
          card.style.transition = '';
          card.style.transform = '';
          card.style.opacity = '';
          if (cur.likeStamp) cur.likeStamp.style.opacity = '0';
          if (cur.skipStamp) cur.skipStamp.style.opacity = '0';
          window.likeCard(liked);
        }, 175);
        return;
      }

      card.style.transition = 'transform 0.28s cubic-bezier(0.22, 1, 0.36, 1)';
      card.style.transform = '';
      if (cur.likeStamp) cur.likeStamp.style.opacity = '0';
      if (cur.skipStamp) cur.skipStamp.style.opacity = '0';
      setTimeout(function () {
        if (card) card.style.transition = '';
      }, 290);
    }

    root.addEventListener('pointerup', function (e) {
      if (drag && e.pointerId === drag.pointerId) finishDrag(false);
    });
    root.addEventListener('pointercancel', function (e) {
      if (drag && e.pointerId === drag.pointerId) finishDrag(true);
    });
  }

  // ==================== 2. Smart Keyboard Flow for Desktop & Power Users ====================
  function bindKeyboardShortcuts() {
    if (window.__dhJourneyKeysBound) return;
    window.__dhJourneyKeysBound = true;

    document.addEventListener('keydown', function (e) {
      if (!window.__dhInJourney || !window.state) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      var tag = e.target && e.target.tagName ? e.target.tagName.toLowerCase() : '';
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      var st = window.state;
      if (st.stage === 'swipe' && document.getElementById('dh-swipe-card')) {
        if (e.key === 'ArrowRight') {
          e.preventDefault();
          haptic(10);
          window.likeCard(true);
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault();
          haptic(8);
          window.likeCard(false);
        } else if (e.key === 'Backspace' && typeof window.previousCard === 'function') {
          e.preventDefault();
          window.previousCard();
        }
      } else if (st.stage === 'strategies' && typeof window.answerStrategy === 'function') {
        var n = parseInt(e.key, 10);
        if (n >= 1 && n <= 5) {
          e.preventDefault();
          haptic(10);
          window.answerStrategy(n - 1);
        }
      } else if (st.stage === 'values' && typeof window.answerValue === 'function') {
        var q = st.valueQuestions && st.valueQuestions[st.currentValueQuestion];
        if (!q || !Array.isArray(q.options) || q.options.length < 2) return;
        if (e.key === '1' || e.key === 'ArrowRight') {
          e.preventDefault();
          haptic(10);
          window.answerValue(q.options[0].code);
        } else if (e.key === '2' || e.key === 'ArrowLeft') {
          e.preventDefault();
          haptic(10);
          window.answerValue(q.options[1].code);
        }
      }
    });
  }

  // ==================== 3. 3-Step Animated Reveal Loader Ticker ====================
  var revealTimer = null;
  function startRevealTickerIfPresent() {
    var stepEl = document.getElementById('dh-reveal-step-text');
    if (!stepEl) {
      if (revealTimer) { clearInterval(revealTimer); revealTimer = null; }
      return;
    }
    if (revealTimer) return;
    var messages = [
      '۱ از ۳ · در حال خوانش جرقه‌های انرژی درونی تو...',
      '۲ از ۳ · ترکیب با سبک حل مسئله و دوراهی‌های ارزشی...',
      '۳ از ۳ · تطبیق دقیق با کاتالوگ رشته‌ها و محاسبهٔ هم‌خوانی...'
    ];
    var idx = 0;
    revealTimer = setInterval(function () {
      var el = document.getElementById('dh-reveal-step-text');
      if (!el) {
        clearInterval(revealTimer);
        revealTimer = null;
        return;
      }
      idx = (idx + 1) % messages.length;
      el.textContent = messages[idx];
    }, 1150);
  }

  // ==================== 4. 1080×1920 Native Story Identity Card Export ====================
  function wrapRtlLines(ctx, text, maxWidth) {
    var words = String(text || '').split(/\s+/).filter(Boolean);
    var lines = [];
    var line = '';
    for (var i = 0; i < words.length; i++) {
      var test = line ? (line + ' ' + words[i]) : words[i];
      if (ctx.measureText(test).width > maxWidth && line) {
        lines.push(line);
        line = words[i];
      } else {
        line = test;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  window.dhShareIdentityStoryCard = async function () {
    var payload = window.__dhIdentityStoryPayload || {};
    var topMatch = payload.topMatch || 'پروفایل فردیت اسب سیاه';
    var fitPct = payload.fitPct || '';
    var worldsText = payload.worldsText || 'شهر رؤیاها';
    var styleText = payload.styleText || '';
    var valueText = payload.valueText || '';
    var colorA = payload.colorA || '#f0c040';
    var colorB = payload.colorB || '#38bdf8';

    try {
      var canvas = document.createElement('canvas');
      canvas.width = 1080;
      canvas.height = 1920;
      var ctx = canvas.getContext('2d');
      ctx.direction = 'rtl';
      ctx.textAlign = 'right';

      // Rich layered dark background + dual world aura
      var bg = ctx.createLinearGradient(0, 0, 1080, 1920);
      bg.addColorStop(0, '#131726');
      bg.addColorStop(0.55, '#0e1017');
      bg.addColorStop(1, '#15192b');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, 1080, 1920);

      var glowA = ctx.createRadialGradient(880, 260, 40, 880, 260, 620);
      glowA.addColorStop(0, colorA + '55');
      glowA.addColorStop(1, 'rgba(14,16,23,0)');
      ctx.fillStyle = glowA;
      ctx.fillRect(0, 0, 1080, 1920);

      var glowB = ctx.createRadialGradient(200, 1520, 40, 200, 1520, 640);
      glowB.addColorStop(0, colorB + '48');
      glowB.addColorStop(1, 'rgba(14,16,23,0)');
      ctx.fillStyle = glowB;
      ctx.fillRect(0, 0, 1080, 1920);

      // Card frame
      ctx.strokeStyle = 'rgba(240, 192, 64, 0.5)';
      ctx.lineWidth = 3;
      ctx.strokeRect(72, 130, 936, 1660);

      ctx.fillStyle = '#f0c040';
      ctx.font = '800 38px Vazirmatn, Tahoma, sans-serif';
      ctx.fillText('✦ اسب سیاه · فرضیه‌های کاوش من', 944, 245);

      ctx.fillStyle = '#b8b2a4';
      ctx.font = '600 30px Vazirmatn, Tahoma, sans-serif';
      ctx.fillText('یک گزینه برای بررسی فعالیت‌ها، راهبردها و ارزش‌ها:', 944, 380);

      ctx.fillStyle = '#fff8eb';
      ctx.font = '900 68px Vazirmatn, Tahoma, sans-serif';
      var titleLines = wrapRtlLines(ctx, topMatch, 820);
      var y = 495;
      titleLines.slice(0, 2).forEach(function (ln) {
        ctx.fillText(ln, 944, y);
        y += 92;
      });

      if (fitPct) {
        ctx.fillStyle = colorA;
        ctx.font = '800 46px Vazirmatn, Tahoma, sans-serif';
        ctx.fillText('هم‌خوانی فردی: ' + fitPct, 944, y + 35);
        y += 120;
      }

      var blocks = [
        { k: 'قلمروهای انرژی غالب', v: worldsText },
        styleText ? { k: 'سبک فکری و حل مسئله', v: styleText } : null,
        valueText ? { k: 'قطب‌های ارزشی کلیدی', v: valueText } : null
      ].filter(Boolean);

      blocks.forEach(function (b) {
        y += 55;
        ctx.fillStyle = '#f5d472';
        ctx.font = '800 32px Vazirmatn, Tahoma, sans-serif';
        ctx.fillText(b.k, 944, y);
        y += 58;
        ctx.fillStyle = '#e5dfd2';
        ctx.font = '600 34px Vazirmatn, Tahoma, sans-serif';
        wrapRtlLines(ctx, b.v, 820).slice(0, 2).forEach(function (ln) {
          ctx.fillText(ln, 944, y);
          y += 54;
        });
      });

      ctx.fillStyle = '#9e988a';
      ctx.font = '800 26px Vazirmatn, Tahoma, sans-serif';
      ctx.fillText('نقطهٔ آغاز بررسی؛ نه حکم قطعی یا پیش‌بینی رضایت و موفقیت.', 944, 1590);
      ctx.fillText('درصد همخوانی، احتمال قبولی یا خوشبختی نیست.', 944, 1640);
      ctx.fillText('asbe-siah.ir · انتخاب مسیر بر اساس فردیت، نه کلیشه', 944, 1710);

      var blob = await new Promise(function (resolve) {
        if (canvas.toBlob) canvas.toBlob(resolve, 'image/png');
        else resolve(null);
      });

      if (blob && navigator.canShare && navigator.share) {
        var file = new File([blob], 'darkhorse-identity.png', { type: 'image/png' });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({
            title: 'فرضیه‌های کاوش من در اسب سیاه',
            text: window.__dhShareText || '',
            files: [file]
          });
          return;
        }
      }

      var url = canvas.toDataURL('image/png');
      var link = document.createElement('a');
      link.href = url;
      link.download = 'darkhorse-story.png';
      document.body.appendChild(link);
      link.click();
      link.remove();
      if (typeof window.dhShowJourneyToast === 'function') {
        window.dhShowJourneyToast('کارت استوری با کیفیت بالا ذخیره شد.');
      }
    } catch (_) {
      if (typeof window.dhCopyShare === 'function') window.dhCopyShare();
    }
  };

  function boot() {
    bindSwipeGestureDelegation();
    bindKeyboardShortcuts();
    if (typeof MutationObserver !== 'undefined') {
      var appEl = document.getElementById('app');
      if (appEl && !appEl.__dhRevealObserver) {
        appEl.__dhRevealObserver = new MutationObserver(startRevealTickerIfPresent);
        appEl.__dhRevealObserver.observe(appEl, { childList: true });
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
