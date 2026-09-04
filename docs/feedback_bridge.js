/* feedback_bridge.js — server submit + visible yes/no/maybe selection */
(function (global) {
  'use strict';
  var API = (global.API_BASE || 'https://asbe-siah.liara.run');

  function star(fb, k) {
    var n = Number(fb && fb[k]);
    if (!isFinite(n) || n < 1) return null;
    return Math.max(1, Math.min(5, Math.round(n)));
  }
  function nps(v) {
    if (v === 'yes') return 10;
    if (v === 'maybe') return 7;
    if (v === 'no') return 2;
    return null;
  }
  function buildPayload(fb, state) {
    fb = fb || {};
    state = state || {};
    var suggested = null;
    try {
      if (state.lastResult && state.lastResult.tops && state.lastResult.tops[0]) {
        suggested = state.lastResult.tops[0].name || null;
      }
    } catch (_) {}
    var bits = [];
    if (fb.q9) bits.push(String(fb.q9).trim());
    if (fb.q6) bits.push('need_traditional=' + fb.q6);
    if (fb.q7) bits.push('pay_for_individuality=' + fb.q7);
    if (fb.q8) bits.push('pay_for_career=' + fb.q8);
    if (fb.q10 != null) bits.push('innovation_score=' + fb.q10);
    if (state.likedCodes) bits.push('liked_codes=' + state.likedCodes.length);
    if (state.strategyAnswers) bits.push('strategy_answers=' + state.strategyAnswers.length);
    if (state.valueAnswers) bits.push('value_answers=' + state.valueAnswers.length);
    if (state.sessionId) bits.push('client_session=' + state.sessionId);
    return {
      exam_code: state.examCode || null,
      suggested_major: suggested,
      major_fit: star(fb, 'q1'),
      motive_accuracy: star(fb, 'q2'),
      strategy_fit: star(fb, 'q4'),
      value_fit: star(fb, 'q5') != null ? star(fb, 'q5') : star(fb, 'q10'),
      nps: nps(fb.q3),
      comments: bits.length ? bits.join(' | ') : null,
      submitted_at: new Date().toISOString(),
      contact_for_research: false
    };
  }

  async function postFeedback(payload) {
    var res = await fetch(API + '/api/v1/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      var detail = '';
      try { var body = await res.json(); detail = body.detail || body.message || ''; } catch (_) {}
      throw new Error(detail || ('HTTP ' + res.status));
    }
    return res.json();
  }

  // Strong visual selection for yes/maybe/no + stars (mobile-friendly)
  function paintChoice(question, value) {
    if (typeof value === 'number') {
      for (var i = 1; i <= 5; i++) {
        var starEl = document.getElementById('star-' + question + '-' + i);
        if (starEl) {
          starEl.style.opacity = i <= value ? '1' : '0.3';
          starEl.style.transform = i <= value ? 'scale(1.12)' : 'scale(1)';
        }
      }
      return;
    }
    ['yes', 'maybe', 'no'].forEach(function (v) {
      var btn = document.getElementById('btn-' + question + '-' + v);
      if (!btn) return;
      var on = v === value;
      btn.style.border = on ? '2px solid #f0c040' : '1px solid #333';
      btn.style.background = on ? 'rgba(240,192,64,0.22)' : '#2a2a42';
      btn.style.color = on ? '#f0c040' : '#e0e0e0';
      btn.style.fontWeight = on ? '800' : '500';
      btn.style.boxShadow = on ? '0 0 0 1px rgba(240,192,64,0.35)' : 'none';
    });
  }

  function patchSetFeedback() {
    var original = global.setFeedback;
    global.setFeedback = function (question, value) {
      try {
        if (typeof feedback !== 'undefined') feedback[question] = value;
      } catch (_) {}
      if (typeof original === 'function' && !original.__dhChoicePatched) {
        try { original(question, value); } catch (_) {}
      }
      paintChoice(question, value);
    };
    global.setFeedback.__dhChoicePatched = true;
    // also keep legacy name reachable for inline onclick
    try { window.setFeedback = global.setFeedback; } catch (_) {}
    return true;
  }

  function bindDelegatedClicks() {
    if (document.__dhFeedbackClickBound) return;
    document.__dhFeedbackClickBound = true;
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (!t) return;
      // buttons: btn-q3-yes etc
      var id = t.id || '';
      var m = id.match(/^btn-(q\d+)-(yes|maybe|no)$/);
      if (m) {
        e.preventDefault();
        e.stopPropagation();
        global.setFeedback(m[1], m[2]);
        return;
      }
      // stars: star-q1-3
      var sm = id.match(/^star-(q\d+)-(\d)$/);
      if (sm) {
        e.preventDefault();
        e.stopPropagation();
        global.setFeedback(sm[1], Number(sm[2]));
      }
    }, true);
  }

  function patchSubmit() {
    if (typeof global.submitFeedback !== 'function') return false;
    if (global.submitFeedback.__dhBridged) return true;
    global.submitFeedback = async function () {
      try {
        if (typeof feedback !== 'undefined' && document.getElementById('feedback-q9')) {
          feedback.q9 = document.getElementById('feedback-q9').value || '';
        }
      } catch (_) {}
      var localOk = false;
      try {
        if (typeof feedback !== 'undefined' && typeof state !== 'undefined') {
          var allFeedback = {
            session_id: state.sessionId || 'unknown',
            timestamp: new Date().toISOString(),
            likedCodes: (state.likedCodes || []).length,
            strategyAnswers: (state.strategyAnswers || []).length,
            valueAnswers: (state.valueAnswers || []).length,
            feedback: feedback
          };
          var existing = JSON.parse(localStorage.getItem('darkhorse_feedback_v2') || '[]');
          existing.push(allFeedback);
          localStorage.setItem('darkhorse_feedback_v2', JSON.stringify(existing));
          localOk = true;
        }
      } catch (_) {}

      var serverOk = false;
      var errMsg = '';
      try {
        var payload = buildPayload(typeof feedback !== 'undefined' ? feedback : {}, typeof state !== 'undefined' ? state : {});
        await postFeedback(payload);
        serverOk = true;
      } catch (e) {
        errMsg = (e && e.message) ? e.message : String(e);
        try {
          var r = await fetch(API + '/api/feedback/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: (typeof state !== 'undefined' && state.sessionId) || 'unknown',
              timestamp: new Date().toISOString(),
              likedCodes: (typeof state !== 'undefined' && state.likedCodes) ? state.likedCodes.length : 0,
              strategyAnswers: (typeof state !== 'undefined' && state.strategyAnswers) ? state.strategyAnswers.length : 0,
              valueAnswers: (typeof state !== 'undefined' && state.valueAnswers) ? state.valueAnswers.length : 0,
              feedback: (typeof feedback !== 'undefined' ? feedback : {})
            })
          });
          if (r.ok) serverOk = true;
          else if (!errMsg) errMsg = 'legacy HTTP ' + r.status;
        } catch (e2) {
          if (!errMsg) errMsg = (e2 && e2.message) ? e2.message : String(e2);
        }
      }

      var msgEl = document.getElementById('feedback-msg');
      if (msgEl) {
        msgEl.style.display = 'block';
        if (serverOk) {
          msgEl.style.color = '#f0c040';
          msgEl.textContent = '✅ ممنون از بازخوردت! نظرت با موفقیت در سرور ثبت شد.';
        } else if (localOk) {
          msgEl.style.color = '#f0c040';
          msgEl.textContent = '✅ بازخورد روی دستگاه ذخیره شد؛ ارسال به سرور ممکن نشد' + (errMsg ? (' (' + errMsg + ')') : '') + '.';
        } else {
          msgEl.style.color = '#ff6b6b';
          msgEl.textContent = '⚠️ ذخیره‌سازی بازخورد با مشکل مواجه شد.';
        }
      }
    };
    global.submitFeedback.__dhBridged = true;
    return true;
  }

  function boot() {
    patchSetFeedback();
    bindDelegatedClicks();
    if (patchSubmit()) return;
    var n = 0;
    var t = setInterval(function () {
      n += 1;
      patchSetFeedback();
      if (patchSubmit() || n > 40) clearInterval(t);
    }, 250);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})(window);
