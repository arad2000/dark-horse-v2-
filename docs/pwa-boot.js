/* pwa-boot.js v7 — نصب فقط وقتی هنوز نصب نشده */
(function () {
  'use strict';

  function isStandalone() {
    try {
      if (window.matchMedia('(display-mode: standalone)').matches) return true;
      if (window.matchMedia('(display-mode: fullscreen)').matches) return true;
      if (window.matchMedia('(display-mode: minimal-ui)').matches) return true;
    } catch (e) {}
    if (window.navigator.standalone === true) return true; // iOS
    // بعضی وب‌ویوها
    if (document.referrer && document.referrer.indexOf('android-app://') === 0) return true;
    return false;
  }

  function isIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  }

  function isAndroid() {
    return /Android/i.test(navigator.userAgent);
  }

  window.__dhIsInstalled = isStandalone();

  // اگر نصب شده: کلاً UI نصب را نشان نده
  if (window.__dhIsInstalled) {
    document.documentElement.classList.add('dh-installed');
  }

  // SW
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('./sw.js').then(function (reg) {
        try { reg.update(); } catch (e) {}
      }).catch(function () {});
    });
    var refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', function () {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    });
  }

  var deferredPrompt = null;

  window.addEventListener('beforeinstallprompt', function (e) {
    if (isStandalone()) return;
    e.preventDefault();
    deferredPrompt = e;
    window.__dhCanInstall = true;
    // فقط اگر کاربر خودش نخواسته مخفی کند
    try {
      if (localStorage.getItem('dh_install_forever_hide') === '1') return;
    } catch (err) {}
    showInstallUI('auto');
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    window.__dhCanInstall = false;
    window.__dhIsInstalled = true;
    try {
      localStorage.setItem('dh_installed_flag', '1');
      localStorage.setItem('dh_install_forever_hide', '1');
    } catch (e) {}
    hideInstallUI();
  });

  function hideInstallUI() {
    var a = document.getElementById('dh-install-banner');
    if (a) a.remove();
    var b = document.getElementById('dh-install-home');
    if (b) b.style.display = 'none';
  }

  function showInstallUI(mode) {
    if (isStandalone()) return;
    try {
      if (localStorage.getItem('dh_installed_flag') === '1') return;
      if (localStorage.getItem('dh_install_forever_hide') === '1') return;
    } catch (e) {}
    if (document.getElementById('dh-install-banner')) return;

    var banner = document.createElement('div');
    banner.id = 'dh-install-banner';
    banner.style.cssText = [
      'position:fixed', 'left:10px', 'right:10px', 'bottom:72px', 'z-index:10002',
      'background:linear-gradient(135deg,#1a1a2e,#2a2210)',
      'border:1px solid #d4af37', 'border-radius:14px', 'padding:14px',
      'box-shadow:0 8px 28px rgba(0,0,0,.45)', 'text-align:right',
      'font-family:Vazirmatn,sans-serif', 'color:#e8e0d0'
    ].join(';');

    var body, btnLabel;
    if (mode === 'auto' && deferredPrompt) {
      body = 'روی گوشی مثل یک اپ واقعی نصب کن — بدون فروشگاه.';
      btnLabel = '⬇ دانلود و نصب';
    } else if (isIOS()) {
      body = 'Safari → Share → افزودن به صفحه اصلی';
      btnLabel = 'راهنما';
    } else {
      body = 'از منوی ⋮ گزینه Install app را بزن یا دکمه زیر را امتحان کن.';
      btnLabel = '⬇ نصب';
    }

    banner.innerHTML =
      '<div style="font-weight:700;color:#f0c040;margin-bottom:6px;">نصب اپ اسب سیاه</div>' +
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
        deferredPrompt.userChoice.then(function (choice) {
          deferredPrompt = null;
          if (choice && choice.outcome === 'accepted') {
            try { localStorage.setItem('dh_install_forever_hide', '1'); } catch (e) {}
          }
          hideInstallUI();
        });
        return;
      }
      if (isIOS()) {
        alert('در Safari: Share → Add to Home Screen / افزودن به صفحه اصلی');
      } else {
        alert('منوی ⋮ مرورگر → Install app / نصب برنامه');
      }
    };
  }

  window.DHInstall = {
    show: function () {
      if (isStandalone()) {
        alert('اپ از قبل روی گوشی نصب است.');
        return;
      }
      showInstallUI(deferredPrompt ? 'auto' : 'manual');
    },
    hide: hideInstallUI,
    isStandalone: isStandalone
  };

  function maybeShow() {
    if (isStandalone()) {
      hideInstallUI();
      return;
    }
    try {
      if (sessionStorage.getItem('dh_install_dismissed') === '1') return;
      if (localStorage.getItem('dh_install_forever_hide') === '1') return;
    } catch (e) {}
    setTimeout(function () {
      if (!isStandalone()) showInstallUI(deferredPrompt ? 'auto' : 'manual');
    }, 1200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', maybeShow);
  } else {
    maybeShow();
  }
})();
