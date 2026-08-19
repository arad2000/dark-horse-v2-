/* Dark Horse PWA boot — register SW + install CTA */
(function () {
  if (!('serviceWorker' in navigator)) return;

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('./sw.js').catch(function (err) {
      console.warn('SW register failed', err);
    });
  });

  var deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    showInstallBar();
  });

  function showInstallBar() {
    if (document.getElementById('dh-install-bar')) return;
    if (window.matchMedia('(display-mode: standalone)').matches) return;
    var bar = document.createElement('div');
    bar.id = 'dh-install-bar';
    bar.className = 'dh-install-bar';
    bar.innerHTML =
      '<p>برای تجربه بهتر، «اسب سیاه» را مثل اپ روی گوشی نصب کن.</p>' +
      '<div class="row">' +
      '<button type="button" class="btn btn-primary" id="dh-install-yes">نصب اپ</button>' +
      '<button type="button" class="btn" id="dh-install-no">الان نه</button>' +
      '</div>';
    var app = document.getElementById('app');
    if (app) app.appendChild(bar);
    else document.body.appendChild(bar);

    document.getElementById('dh-install-yes').onclick = function () {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
        bar.remove();
      });
    };
    document.getElementById('dh-install-no').onclick = function () {
      bar.remove();
    };
  }
})();
