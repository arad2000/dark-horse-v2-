/* pwa-boot.js — ثبت SW + اجبار آپدیت */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').then((reg) => {
      try { reg.update(); } catch (e) {}
      setInterval(() => { try { reg.update(); } catch (e) {} }, 60 * 1000);
      if (reg.waiting) {
        reg.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
      reg.addEventListener('updatefound', () => {
        const nw = reg.installing;
        if (!nw) return;
        nw.addEventListener('statechange', () => {
          if (nw.state === 'installed' && navigator.serviceWorker.controller) {
            // نسخه جدید آماده — یک‌بار رفرش نرم
            console.log('DH SW updated');
          }
        });
      });
      console.log('SW ثبت شد');
    }).catch((err) => console.log('SW خطا:', err));
  });
  // وقتی SW جدید کنترل را گرفت
  let refreshing = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (refreshing) return;
    refreshing = true;
    window.location.reload();
  });
}

let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  if (document.getElementById('dh-install-btn')) return;
  const installBtn = document.createElement('button');
  installBtn.id = 'dh-install-btn';
  installBtn.textContent = 'نصب اپ اسب سیاه';
  installBtn.style.cssText = 'position:fixed;bottom:76px;left:12px;right:12px;max-width:280px;margin:auto;background:#d4af77;color:#111;padding:12px 16px;border:none;border-radius:12px;z-index:10001;font-family:inherit;font-weight:700;';
  installBtn.onclick = () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    deferredPrompt = null;
    installBtn.remove();
  };
  document.body.appendChild(installBtn);
});
