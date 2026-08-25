/* pwa-boot.js v55 — force SW update + one reload */
(function () {
  'use strict';

  function isStandalone() {
    try {
      if (window.matchMedia('(display-mode: standalone)').matches) return true;
      if (window.matchMedia('(display-mode: fullscreen)').matches) return true;
    } catch (e) {}
    return window.navigator.standalone === true;
  }

  window.__dhIsInstalled = isStandalone();
  if (window.__dhIsInstalled) {
    document.documentElement.classList.add('dh-installed');
  }

  if ('serviceWorker' in navigator) {
    // URL جدید = نصب SW جدید اجباری
    var SW_URL = './sw.js?v=55';

    window.addEventListener('load', function () {
      navigator.serviceWorker.register(SW_URL).then(function (reg) {
        try { reg.update(); } catch (e) {}

        // اگر SW منتظر است، فعالش کن
        if (reg.waiting) {
          try { reg.waiting.postMessage({ type: 'SKIP_WAITING' }); } catch (e) {}
        }
        reg.addEventListener('updatefound', function () {
          var nw = reg.installing;
          if (!nw) return;
          nw.addEventListener('statechange', function () {
            if (nw.state === 'installed' && navigator.serviceWorker.controller) {
              // نسخه جدید آماده
            }
          });
        });
      }).catch(function () {});

      // یک‌بار رفرش وقتی کنترلر عوض شد
      var refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', function () {
        if (refreshing) return;
        try {
          if (sessionStorage.getItem('dh_sw_reloaded_v55') === '1') return;
          sessionStorage.setItem('dh_sw_reloaded_v55', '1');
        } catch (e) {}
        refreshing = true;
        window.location.reload();
      });
    });
  }

  if (isStandalone()) {
    window.DHInstall = { show: function () {}, hide: function () {}, isStandalone: function () { return true; } };
    return;
  }

  var deferredPrompt = null;
  function hideBanner() {
    var el = document.getElementById('dh-install-banner');
    if (el) el.remove();
  }
  function showBanner() {
    if (isStandalone()) return;
    if (document.getElementById('dh-install-banner')) return;
    try {
      if (sessionStorage.getItem('dh_install_dismissed') === '1') return;
    } catch (e) {}
    var banner = document.createElement('div');
    banner.id = 'dh-install-banner';
    banner.setAttribute('dir', 'rtl');
    banner.style.cssText = 'position:fixed;left:12px;right:12px;bottom:72px;z-index:10002;background:linear-gradient(135deg,#1a1a2e,#2a2210);border:1px solid #d4af37;border-radius:14px;padding:14px;box-shadow:0 10px 32px rgba(0,0,0,.5);text-align:right;font-family:Vazirmatn,tahoma,sans-serif;color:#e8e0d0';
    banner.innerHTML =
      '<div style="font-weight:700;color:#f0c040;margin-bottom:6px;">نصب اسب سیاه روی گوشی</div>' +
      '<div style="font-size:0.88rem;line-height:1.75;color:#cbb98a;margin-bottom:12px;">با نصب، دفعات بعد سریع‌تر باز می‌شود.</div>' +
      '<div style="display:flex;gap:8px;">' +
        '<button type="button" id="dh-install-go" style="flex:1;background:#d4af37;color:#111;border:none;border-radius:10px;padding:12px;font-weight:700;font-family:inherit;">نصب</button>' +
        '<button type="button" id="dh-install-x" style="background:transparent;color:#8a7a55;border:1px solid #555;border-radius:10px;padding:12px 16px;font-family:inherit;">بعداً</button>' +
      '</div>';
    document.body.appendChild(banner);
    var go = document.getElementById('dh-install-go');
    var x = document.getElementById('dh-install-x');
    if (go) go.onclick = function () {
      if (!deferredPrompt) { hideBanner(); return; }
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(function () { deferredPrompt = null; hideBanner(); });
    };
    if (x) x.onclick = function () {
      try { sessionStorage.setItem('dh_install_dismissed', '1'); } catch (e) {}
      hideBanner();
    };
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    setTimeout(showBanner, 2500);
  });

  window.DHInstall = {
    show: showBanner,
    hide: hideBanner,
    isStandalone: isStandalone
  };
})();
