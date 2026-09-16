/* auth_api_client.js — Dark Horse Commercial Auth */
(function (global) {
  const API = (global.API_BASE || 'https://api.asbe-siah.ir');
  const KEY = 'dh_auth_v1';
  const QUOTA_KEY = 'dh_local_quota_v1';

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; }
  }
  function save(data) { localStorage.setItem(KEY, JSON.stringify(data)); }
  function clear() { localStorage.removeItem(KEY); }

  function quotaIdentity(session) {
    const s = session || load() || {};
    const u = s.user || {};
    return String(u.id || u.user_id || u.phone || u.mobile || u.username || '');
  }

  function loadQuotaCache() {
    try {
      const raw = JSON.parse(localStorage.getItem(QUOTA_KEY) || 'null');
      return raw && typeof raw === 'object' ? raw : null;
    } catch (_) { return null; }
  }

  function saveQuotaCache(patch) {
    try {
      const current = loadQuotaCache() || {};
      const next = Object.assign({}, current, patch || {});
      localStorage.setItem(QUOTA_KEY, JSON.stringify(next));
      return next;
    } catch (_) { return null; }
  }

  function persistSuccessfulConsume(data) {
    const session = load();
    const identity = quotaIdentity(session);
    const current = loadQuotaCache();
    const sameUser = !!identity && !!current && String(current.userKey || '') === identity;
    let used = sameUser ? Number(current.used) : 0;
    if (!Number.isFinite(used) || used < 0) used = 0;

    // A successful consume-test request is the authoritative server-side event.
    // The endpoint returns successfully only when one entitlement was consumed.
    let consumedNow = 1;
    if (data && Object.prototype.hasOwnProperty.call(data, 'consumed')) {
      const serverConsumed = Number(data.consumed);
      if (Number.isFinite(serverConsumed)) consumedNow = serverConsumed > 0 ? 1 : 0;
    }
    used += consumedNow;

    const remainingRaw = data && data.credits_remaining;
    const remaining = Number(remainingRaw);
    const patch = {
      userKey: identity,
      used,
      premium: false,
      consumedAt: new Date().toISOString()
    };
    if (Number.isFinite(remaining) && remaining >= 0) {
      patch.serverRemaining = remaining;
      patch.remaining = remaining;
    }
    saveQuotaCache(patch);
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

    async quota() { return req('/api/v1/me/quota'); },

    async consumeTest() {
      const data = await req('/api/v1/me/consume-test', { method: 'POST', body: '{}' });
      const s = load() || {};
      if (data.user) { s.user = data.user; save(s); }
      persistSuccessfulConsume(data);
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
