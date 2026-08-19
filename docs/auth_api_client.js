/* auth_api_client.js — Dark Horse Phase B */
(function (global) {
  const API = (global.API_BASE || 'https://dark-horse-v2.onrender.com');
  const KEY = 'dh_auth_v1';

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; }
  }
  function save(data) {
    localStorage.setItem(KEY, JSON.stringify(data));
  }
  function clear() {
    localStorage.removeItem(KEY);
  }

  async function req(path, opts = {}) {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    const auth = load();
    if (auth && auth.token) headers['Authorization'] = 'Bearer ' + auth.token;
    const res = await fetch(API + path, Object.assign({}, opts, { headers }));
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
      const data = await req('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name, phone, password })
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
      return req('/api/v1/me/save-result', {
        method: 'POST',
        body: JSON.stringify({ result_summary: summary })
      });
    },

    async createPayment() {
      return req('/api/v1/billing/create-payment', { method: 'POST', body: '{}' });
    },

    async devActivatePremium() {
      const data = await req('/api/v1/billing/dev-activate-premium', { method: 'POST', body: '{}' });
      const s = load() || {};
      if (data.user) { s.user = data.user; save(s); }
      return data;
    }
  };

  global.DHAuth = Auth;
})(window);
