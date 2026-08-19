/* pwa-boot.js v6 — نصب قابل‌مشاهده + SW */
(function () {
  'use strict';

  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true;
  }

  function isIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  }

  function isAndroid() {
    return /Android/i.test(navigator.userAgent);
  }

  // ----- Service Worker -----
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('./sw.js').then(function (reg) {
        try { reg.update(); } catch (e) {}
        console.log('SW ok');
      }).catch(function (err) {
        console.log('SW err', err);
      });
    });
    var refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', function () {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    });
  }

  // ----- Install prompt (Android Chrome) -----
  var deferredPrompt = null;

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    window.__dhCanInstall = true;
    showInstallUI('auto');
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    window.__dhCanInstall = false;
    hideInstallUI();
  });

  function hideInstallUI() {
    var a = document.getElementById('dh-install-banner');
    if (a) a.remove();
  }

  function showInstallUI(mode) {
    if (isStandalone()) return;
    if (document.getElementById('dh-install-banner')) return;

    var banner = document.createElement('div');
    banner.id = 'dh-install-banner';
    banner.style.cssText = [
      'position:fixed', 'left:10px', 'right:10px', 'bottom:72px', 'z-index:10002',
      'background:linear-gradient(135deg,#1a1a2e,#2a2210)',
      'border:1px solid #d4af37', 'border-radius:14px', 'padding:14px 14px 12px',
      'box-shadow:0 8px 28px rgba(0,0,0,.45)', 'text-align:right',
      'font-family:Vazirmatn,sans-serif', 'color:#e8e0d0'
    ].join(';');

    var title = 'نصب اپ اسب سیاه';
    var body = '';
    var btnLabel = 'نصب';

    if (mode === 'auto' && deferredPrompt) {
      body = 'روی گوشی مثل یک اپ واقعی نصب کن — بدون کافه بازار.';
      btnLabel = '⬇ دانلود و نصب';
    } else if (isIOS()) {
      body = 'در Safari بزن روی Share (مربع با فلش) → سپس «Add to Home Screen» یا «افزودن به صفحه اصلی».';
      btnLabel = 'متوجه شدم';
    } else if (isAndroid()) {
      body = 'از منوی ⋮ مرورگر گزینه «Install app» / «نصب برنامه» را بزن. یا دکمه زیر را امتحان کن.';
      btnLabel = '⬇ تلاش برای نصب';
    } else {
      body = 'از منوی مرورگر گزینه Install / نصب برنامه را انتخاب کن.';
      btnLabel = 'باشه';
    }

    banner.innerHTML =
      '<div style="font-weight:700;color:#f0c040;margin-bottom:6px;">' + title + '</div>' +
      '<div style="font-size:0.88rem;line-height:1.75;color:#cbb98a;margin-bottom:10px;">' + body + '</div>' +
      '<div style="display:flex;gap:8px;">' +
        '<button type="button" id="dh-install-go" style="flex:1;background:#d4af37;color:#111;border:none;border-radius:10px;padding:11px;font-weight:700;font-family:inherit;">' + btnLabel + '</button>' +
        '<button type="button" id="dh-install-x" style="background:transparent;color:#8a7a55;border:1px solid #444;border-radius:10px;padding:11px 14px;font-family:inherit;">بعداً</button>' +
      '</div>';

    document.body.appendChild(banner);

    document.getElementById('dh-install-x').onclick = function () {
      try { sessionStorage.setItem('dh_install_dismissed', '1'); } catch (e) {}
      hideInstallUI();
    };
    document.getElementById('dh-install-go').onclick = function () {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function () {
          deferredPrompt = null;
          hideInstallUI();
        });
        return;
      }
      if (isIOS()) {
        alert('در Safari: دکمه Share پایین صفحه → Add to Home Screen');
        return;
      }
      alert('از منوی ⋮ مرورگر گزینه Install app / نصب برنامه را بزن.\nاگر نبود، یک‌بار صفحه را رفرش کن یا در Chrome باز کن.');
    };
  }

  window.DHInstall = {
    show: function () { showInstallUI(deferredPrompt ? 'auto' : 'manual'); },
    prompt: function () {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        return true;
      }
      showInstallUI('manual');
      return false;
    },
    isStandalone: isStandalone
  };

  // بعد از لود — اگر نصب نیست بنر راهنما
  function maybeShow() {
    if (isStandalone()) return;
    try {
      if (sessionStorage.getItem('dh_install_dismissed') === '1') return;
    } catch (e) {}
    // کمی تأخیر تا UI خانه بنشیند
    setTimeout(function () {
      showInstallUI(deferredPrompt ? 'auto' : 'manual');
    }, 900);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', maybeShow);
  } else {
    maybeShow();
  }
  window.addEventListener('load', maybeShow);
})();
