/* auth_api_client.js — Dark Horse Phase B */
(function (global) {
  'use strict';

  const API = (global.API_BASE || 'https://api.asbe-siah.ir');
  const KEY = 'dh_auth_v1';
  const REQUEST_TIMEOUT_MS = 15000;

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; }
  }
  function save(data) {
    localStorage.setItem(KEY, JSON.stringify(data));
  }
  function clear() {
    localStorage.removeItem(KEY);
  }
  function currentJourneySessionId() {
    try {
      const journey = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null');
      return journey && journey.sessionId ? String(journey.sessionId) : null;
    } catch (_) {
      return null;
    }
  }

  async function req(path, opts = {}) {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    const auth = load();
    if (auth && auth.token) headers['Authorization'] = 'Bearer ' + auth.token;

    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timeoutId = setTimeout(function () {
      if (controller) controller.abort();
    }, REQUEST_TIMEOUT_MS);
    const requestOpts = Object.assign({}, opts, { headers });
    if (controller) requestOpts.signal = controller.signal;

    let res;
    try {
      res = await fetch(API + path, requestOpts);
    } catch (e) {
      if (e && (e.name === 'AbortError' || e.code === 20)) {
        throw new Error('زمان پاسخ سرور تمام شد. اتصال اینترنت یا وضعیت سرویس را بررسی کنید.');
      }
      throw new Error('ارتباط با سرور برقرار نشد. لطفاً دوباره تلاش کنید.');
    } finally {
      clearTimeout(timeoutId);
    }

    let body = null;
    try { body = await res.json(); } catch (_) {}
    if (!res.ok) {
      const msg = (body && (body.detail || body.message)) || ('خطا ' + res.status);
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return body;
  }

  const Auth = {
    getSession() { return load(); },
    isLoggedIn() { const s = load(); return !!(s && s.token); },
    getUser() { const s = load(); return s && s.user ? s.user : null; },
    logout() { clear(); },

    async register(name, phone, password) {
      return req('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name, phone, password })
      });
    },

    async verifyRegistration(challengeId, code) {
      const data = await req('/api/v1/auth/register/verify', {
        method: 'POST',
        body: JSON.stringify({ challenge_id: challengeId, code })
      });
      save(data);
      return data;
    },

    async login(phone, password) {
      const data = await req('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ phone, password })
      });
      save(data);
      return data;
    },

    async requestPasswordReset(phone) {
      return req('/api/v1/auth/password-reset/request', {
        method: 'POST',
        body: JSON.stringify({ phone })
      });
    },

    async resetPassword(challengeId, code, newPassword) {
      const data = await req('/api/v1/auth/password-reset/confirm', {
        method: 'POST',
        body: JSON.stringify({
          challenge_id: challengeId,
          code,
          new_password: newPassword
        })
      });
      save(data);
      return data;
    },

    async refreshMe() {
      const data = await req('/api/v1/me');
      const s = load() || {};
      s.user = data.user;
      save(s);
      return data.user;
    },

    async quota() {
      return req('/api/v1/me/quota');
    },

    async consumeTest() {
      const data = await req('/api/v1/me/consume-test', { method: 'POST', body: '{}' });
      const s = load() || {};
      if (data.user) { s.user = data.user; save(s); }
      return data;
    },

    async saveResult(summary) {
      const sessionId = currentJourneySessionId();
      if (!sessionId) throw new Error('شناسه سفر کاربر پیدا نشد؛ ابتدا تحلیل را کامل کنید.');
      return req('/api/v1/me/save-result', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, result_summary: summary || {} })
      });
    },

    async createPayment() {
      return req('/api/v1/billing/create-payment', { method: 'POST', body: '{}' });
    }
  };

  global.DHAuth = Auth;
})(window);
