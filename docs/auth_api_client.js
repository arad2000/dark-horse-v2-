/* auth_api_client.js — Dark Horse Commercial Auth */
(function (global) {
  const API = (global.API_BASE || 'https://asbe-siah.liara.run');
  const KEY = 'dh_auth_v1';

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; }
  }
  function save(data) { localStorage.setItem(KEY, JSON.stringify(data)); }
  function clear() { localStorage.removeItem(KEY); }

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
    isAdmin() {
      const u = this.getUser();
      return !!(u && (u.role === 'admin' || u.role === 'support'));
    },
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

    async refreshMe() {
      const data = await req('/api/v1/me');
      const s = load() || {};
      s.user = data.user;
      save(s);
      return data.user;
    },

    async quota() { return req('/api/v1/me/quota'); },

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

    async adminDashboard() {
      return req('/api/v1/admin/dashboard');
    },

    async adminFeedback(limit) {
      const n = Math.max(1, Math.min(200, Number(limit) || 50));
      return req('/api/v1/admin/feedback?limit=' + n);
    },

    async adminUsers(limit) {
      const n = Math.max(1, Math.min(500, Number(limit) || 50));
      return req('/api/v1/admin/users?limit=' + n);
    }
  };

  global.DHAuth = Auth;
})(window);
