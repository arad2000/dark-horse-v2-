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
    return String(u.id || u.user_id || u.phone || u.mobile || u.username || u.public_id || '');
  }

  function currentJourneySessionId() {
    try {
      const journey = JSON.parse(localStorage.getItem('darkhorse_session_v2') || 'null');
      return journey && journey.sessionId ? String(journey.sessionId) : null;
    } catch (_) { return null; }
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

  function persistQuotaSnapshot(data) {
    const session = load();
    const identity = quotaIdentity(session);
    const current = loadQuotaCache();
    const sameUser = !!identity && !!current && String(current.userKey || '') === identity;

    const remaining = Number(data && data.credits_remaining);
    const consumed = Number(data && data.credits_consumed);
    const granted = Number(data && data.credits_granted);

    const patch = {
      userKey: identity,
      premium: false,
      syncedAt: new Date().toISOString()
    };
    if (Number.isFinite(remaining) && remaining >= 0) {
      patch.serverRemaining = remaining;
      patch.remaining = remaining;
    } else if (sameUser && Number.isFinite(Number(current.serverRemaining))) {
      patch.serverRemaining = Number(current.serverRemaining);
      patch.remaining = Number(current.remaining);
    }
    if (Number.isFinite(consumed) && consumed >= 0) {
      patch.used = consumed;
      patch.serverConsumed = consumed;
    } else if (sameUser && Number.isFinite(Number(current.serverConsumed)) && Number(current.serverConsumed) >= 0) {
      patch.used = Number(current.serverConsumed);
      patch.serverConsumed = Number(current.serverConsumed);
    } else if (sameUser && Number.isFinite(Number(current.used)) && Number(current.used) >= 0) {
      patch.used = Number(current.used);
    }
    if (Number.isFinite(granted) && granted >= 0) patch.serverGranted = granted;
    saveQuotaCache(patch);
  }

  function persistSuccessfulConsume(data) {
    persistQuotaSnapshot(data || {});
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
      const error = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      error.status = res.status;
      error.serverMessage = msg;
      throw error;
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
      persistQuotaSnapshot(data);
      return data;
    },

    async login(phone, password) {
      const data = await req('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ phone, password })
      });
      save(data);
      persistQuotaSnapshot(data);
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
      const data = await req('/api/v1/me/quota');
      persistQuotaSnapshot(data);
      return data;
    },

    async consumeTest(sessionUuid) {
      const sid = sessionUuid || currentJourneySessionId();
      if (!sid) throw new Error('شناسه سفر کاربر پیدا نشد؛ ابتدا تحلیل را آغاز کنید.');
      const data = await req('/api/v1/me/consume-test', {
        method: 'POST',
        body: JSON.stringify({ session_uuid: String(sid) })
      });
      const s = load() || {};
      if (data.user) { s.user = data.user; save(s); }
      persistSuccessfulConsume(data);
      return data;
    },

    async saveResult(summary) {
      const sessionId = currentJourneySessionId();
      if (!sessionId) throw new Error('شناسه سفر کاربر پیدا نشد؛ ابتدا تحلیل را کامل کنید.');
      return req('/api/v1/me/save-result', {
        method: 'POST',
        body: JSON.stringify({ session_uuid: sessionId, result_summary: Object.assign({}, summary || {}, { session_uuid: sessionId }) })
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
    },

    async adminGrantCredits(userId, planCode = 'pack_3_tests', reason = 'هدیه مالک') {
      const id = Number(userId);
      if (!Number.isInteger(id) || id <= 0) {
        throw new Error('شناسه کاربر باید یک عدد صحیح مثبت باشد.');
      }
      const code = String(planCode || '').trim();
      const why = String(reason || '').trim() || 'هدیه مالک';
      if (!code) throw new Error('کد پلن اعتبار الزامی است.');
      try {
        return await req('/api/v1/admin/credits/grant', {
          method: 'POST',
          body: JSON.stringify({
            user_id: id,
            plan_code: code,
            reason: why
          })
        });
      } catch (e) {
        const status = Number(e && e.status);
        const server = String((e && (e.serverMessage || e.message)) || '');
        if (status === 401) throw new Error('احراز هویت لازم است.');
        if (status === 403 || /admin access required/i.test(server)) {
          throw new Error('دسترسی مدیر برای اعطای اعتبار لازم است.');
        }
        if (status === 404) throw new Error('کاربر یا سرویس اعطای اعتبار پیدا نشد.');
        if (status === 400 || status === 422) {
          if (/unknown\/inactive user|unknown.*user.*inactive|inactive plan/i.test(server)) {
            throw new Error('کاربر پیدا نشد یا غیرفعال است، یا پلن فعال نیست.');
          }
          if (/plan does not grant credits/i.test(server)) {
            throw new Error('این پلن قابلیت اعطای اعتبار ندارد.');
          }
          throw new Error(server || 'اطلاعات اعطای اعتبار نامعتبر است.');
        }
        throw new Error(server || 'اعطای اعتبار ناموفق بود.');
      }
    }
  };

  global.DHAuth = Auth;
})(window);