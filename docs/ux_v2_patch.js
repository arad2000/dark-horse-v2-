/* Dark Horse — UX Layer v3
 * هماهنگ با سامانه طراحی نسل زد: کنتراست استاندارد، نوار پیشرفت جرقه، و بدون بازنویسی مخرب DOM
 */
(function () {
  if (window.__dhUxV2Applied) return;
  window.__dhUxV2Applied = true;

  function toFa(n) {
    return String(n).replace(/\d/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'[Number(d)]; });
  }

  function injectStyles() {
    if (document.getElementById('dh-ux2-styles')) return;
    var s = document.createElement('style');
    s.id = 'dh-ux2-styles';
    s.textContent = [
      '.dh-sjt-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(240,192,64,.10);border:1px solid rgba(240,192,64,.26);border-radius:999px;padding:4px 12px;font-size:.76rem;color:#f0c040;margin-bottom:10px;font-weight:700}',
      '.dh-val-scale{margin:12px 0 16px;padding:12px 14px;background:#151824;border:1px solid rgba(255,255,255,.07);border-radius:14px}',
      '.dh-val-poles{display:flex;justify-content:space-between;align-items:center;font-size:.82rem;color:#d6d1c4;gap:8px}',
      '.dh-val-poles span{flex:1;line-height:1.6}',
      '.dh-val-poles span:first-child{text-align:right}',
      '.dh-val-poles span:last-child{text-align:left}',
      '.dh-val-poles b{color:#f0c040;font-size:.75rem;padding:0 6px;flex:0 0 auto}',
      '.dh-val-track{position:relative;height:6px;background:rgba(255,255,255,.08);border-radius:999px;margin-top:9px;overflow:hidden}',
      '.dh-val-track::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(86,199,193,.42),rgba(240,192,64,.55));border-radius:999px}',
      '.dh-tip{font-size:.82rem;color:#a9a497;line-height:1.8;background:#151824;border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:10px 14px;margin:10px 0 14px;text-align:right}',
      '.dh-done-box{text-align:center;padding:24px 18px;background:#171a25;border:1px solid rgba(240,192,64,.30);border-radius:18px;margin:16px 0}'
    ].join('');
    document.head.appendChild(s);
  }

  /* حفظ نوار پیشرفت جرقه (.dh-spark-bar) همراه با راهنمای گام‌به‌گام */
  function patchSparkChip() {
    if (typeof window.sparkChipHTML !== 'function') return;
    window.sparkChipHTML = function () {
      var st = (typeof state !== 'undefined' && state) ? state : window.state;
      var n = (st && Array.isArray(st.likedCodes)) ? st.likedCodes.length : 0;
      var max = 80;
      var pct = Math.min(100, Math.round((n / max) * 100));
      var hint = n < 20
        ? ('حداقل ' + toFa(20) + ' جرقه لازم است')
        : (n < 30
          ? 'عالی؛ پیشنهاد ' + toFa(30) + ' تا ' + toFa(40) + ' جرقه'
          : (n <= 40 ? 'محدودهٔ ایده‌آل برای تحلیل دقیق' : 'سقف انتخاب: ' + toFa(80) + ' جرقه'));
      return '<div class="dh-spark-chip" role="status" aria-live="polite">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">' +
          '<span>✦ ' + toFa(n) + ' جرقه انتخاب‌شده</span>' +
          '<span style="color:#b8b2a4;font-size:.77rem;font-weight:500;">' + hint + '</span>' +
        '</div>' +
        '<div class="dh-spark-bar"><div class="dh-spark-fill" style="width:' + pct + '%"></div></div>' +
      '</div>';
    };
  }

  function applyAll() {
    injectStyles();
    patchSparkChip();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyAll);
  } else {
    applyAll();
  }
})();
