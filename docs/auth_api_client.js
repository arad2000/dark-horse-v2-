/* auth_api_client.js — Dark Horse Phase B */
(function (global) {
  const API = (global.API_BASE || 'https://asbe-siah.liara.run');
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
    get() { return load(); },
    isLoggedIn() { const a = load(); return !!(a && a.token); },
    async register(payload) {
      const body = await req('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) });
      if (body && body.token) save(body);
      return body;
    },
    async login(payload) {
      const body = await req('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) });
      if (body && body.token) save(body);
      return body;
    },
    logout() { clear(); },
    async me() { return req('/api/auth/me'); }
  };

  global.DHAuth = Auth;
})(typeof window !== 'undefined' ? window : globalThis);
