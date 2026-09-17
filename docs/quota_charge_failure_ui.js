/* quota_charge_failure_ui.js v1
 * Observe consume-test responses and surface failures to the user.
 * The server remains authoritative; this layer never changes quota locally.
 */
(function (global) {
  'use strict';
  if (global.__dhQuotaChargeFailureUiInstalled) return;
  global.__dhQuotaChargeFailureUiInstalled = true;

  function parse(raw) {
    try { var value = JSON.parse(raw || 'null'); return value && typeof value === 'object' ? value : null; }
    catch (_) { return null; }
  }

  function escape(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;');
  }

  function showFailure(sessionId, status, payload) {
    try {
      var old = document.getElementById('dh-quota-charge-error');
      if (old) old.remove();
      var detail = payload && (payload.detail || payload.message);
      if (typeof detail !== 'string') detail = 'ثبت مصرف اعتبار در سرور ناموفق بود.';
      var box = document.createElement('div');
      box.id = 'dh-quota-charge-error';
      box.setAttribute('role', 'alert');
      box.style.cssText = 'margin:14px 0;padding:16px;border:1px solid #ff6b6b;border-radius:14px;background:#2a1717;color:#ffd6d6;line-height:1.9;text-align:right;';
      box.innerHTML = '<div style="font-weight:800;color:#ff9a9a;">⚠️ مصرف اعتبار ثبت نشد</div>' +
        '<div style="margin-top:5px;">نتیجه نمایش داده شده، اما شارژ آزمون در سرور کامل نشده است.</div>' +
        '<div style="font-size:.8rem;color:#ffc5c5;word-break:break-word;margin-top:5px;">HTTP ' + escape(status) + ' · ' + escape(detail) + '</div>' +
        '<div style="font-size:.78rem;color:#e7baba;margin-top:5px;">Session: <span dir="ltr">' + escape(sessionId) + '</span></div>' +
        '<button type="button" class="btn btn-primary" id="dh-quota-charge-retry" style="width:100%;margin-top:12px;">🔄 تلاش دوباره</button>';
      var app = document.getElementById('app');
      if (app) app.insertBefore(box, app.firstChild);
      else document.body.appendChild(box);

      var retry = document.getElementById('dh-quota-charge-retry');
      if (!retry) return;
      retry.onclick = function () {
        if (retry.disabled || !global.DHQuotaEnforcement || typeof global.DHQuotaEnforcement.consumeForJourney !== 'function') return;
        retry.disabled = true;
        retry.textContent = 'در حال ثبت…';
        global.DHQuotaEnforcement.consumeForJourney(String(sessionId)).then(function () {
          var done = document.getElementById('dh-quota-charge-error');
          if (done) done.remove();
        }).catch(function (err) {
          console.error('[DarkHorse quota] retry failed', err);
          retry.disabled = false;
          retry.textContent = '🔄 تلاش دوباره';
        });
      };
    } catch (_) {}
  }

  var originalFetch = global.fetch;
  if (typeof originalFetch !== 'function') return;
  global.fetch = function (input, init) {
    var url = '';
    try { url = typeof input === 'string' ? input : (input && input.url) || ''; } catch (_) {}
    var isConsume = /\/api\/v1\/me\/consume-test(?:\?|$)/.test(url);
    var sessionId = null;
    if (isConsume && init && typeof init.body === 'string') {
      var requestBody = parse(init.body);
      sessionId = requestBody && requestBody.session_uuid ? String(requestBody.session_uuid) : null;
    }
    var result = originalFetch.apply(this, arguments);
    if (!isConsume) return result;
    return result.then(function (res) {
      if (!res.ok) {
        try {
          var clone = res.clone();
          clone.json().then(function (payload) {
            console.error('[DarkHorse quota] consume HTTP failure', { status: res.status, session_uuid: sessionId, payload: payload });
            if (sessionId) showFailure(sessionId, res.status, payload);
          }).catch(function () {
            console.error('[DarkHorse quota] consume HTTP failure', { status: res.status, session_uuid: sessionId });
            if (sessionId) showFailure(sessionId, res.status, null);
          });
        } catch (_) {}
      }
      return res;
    });
  };
  global.fetch.__dhQuotaChargeFailureUiWrapped = true;
})(window);