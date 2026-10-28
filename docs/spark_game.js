/**
 * آزمایشگاه جرقه — نمونهٔ تصادفی خرده‌انگیزه‌ها از فایل‌های استاتیک همین سایت
 * روی امتیاز و likedCodes سفر اصلی اثر ندارد.
 * ورودی UI: window.DHSparkGame.open()؛ مستقل از session، سهمیه و پرداخت سفر.
 */
(function () {
  'use strict';

  var LAB_KEY = 'dh_spark_lab_v1';
  var BADGE_KEY = 'dh_spark_badges_v1';
  var DURATION_SEC = 60;
  var TARGET_CARDS = 6;
  var motivesCache = null;
  var timerId = null;
  var overlay = null;

  function $(id) { return document.getElementById(id); }

  function loadLab() {
    try { return JSON.parse(localStorage.getItem(LAB_KEY) || '{}'); } catch (e) { return {}; }
  }
  function saveLab(o) {
    try { localStorage.setItem(LAB_KEY, JSON.stringify(o)); } catch (e) {}
  }

  function loadBadges() {
    try { return JSON.parse(localStorage.getItem(BADGE_KEY) || '[]'); } catch (e) { return []; }
  }
  function saveBadges(arr) {
    try { localStorage.setItem(BADGE_KEY, JSON.stringify(arr)); } catch (e) {}
  }

  function ensureStyles() {
    if ($('dh-spark-lab-css')) return;
    var s = document.createElement('style');
    s.id = 'dh-spark-lab-css';
    s.textContent = [
      '#dh-spark-lab{position:fixed;inset:0;z-index:9999;background:rgba(12,14,20,.95);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);overflow:auto;padding:16px 14px calc(100px + env(safe-area-inset-bottom, 0px));font-family:Vazirmatn,sans-serif;color:#f5efe2;direction:rtl}',
      '#dh-spark-lab .lab-wrap{max-width:440px;margin:0 auto}',
      '#dh-spark-lab .lab-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}',
      '#dh-spark-lab .lab-title{font-size:1.08rem;font-weight:800;color:#f5efe2}',
      '#dh-spark-lab .lab-close{min-height:38px;background:#171a25;border:1px solid rgba(255,255,255,.14);color:#c8c3b7;border-radius:999px;padding:6px 15px;font-family:inherit;cursor:pointer}',
      '#dh-spark-lab .lab-note{font-size:.85rem;line-height:1.78;color:#b8b3a6;margin:0 0 14px;text-align:center}',
      '#dh-spark-lab .lab-timer{text-align:center;font-size:1.55rem;font-weight:800;color:#f0c040;margin:8px 0 14px;letter-spacing:.03em}',
      '#dh-spark-lab .lab-timer.warn{color:#ff8a6a}',
      '#dh-spark-lab .lab-card{background:#171a25;border:1px solid rgba(255,255,255,.1);border-radius:18px;padding:22px 18px;min-height:148px;margin-bottom:14px;box-shadow:0 8px 24px rgba(0,0,0,.3)}',
      '#dh-spark-lab .lab-card p{margin:0;color:#f5efe2;font-size:1.02rem;line-height:1.9;text-align:center}',
      '#dh-spark-lab .lab-meta{text-align:center;font-size:.77rem;color:#9d988c;margin-top:12px}',
      '#dh-spark-lab .lab-actions{display:flex;gap:10px}',
      '#dh-spark-lab .lab-actions button{flex:1;min-height:48px;padding:12px;border-radius:14px;font-family:inherit;font-size:.95rem;font-weight:700;cursor:pointer;border:none}',
      '#dh-spark-lab .btn-like{background:linear-gradient(135deg,#d4af37,#f0c040);color:#15130b}',
      '#dh-spark-lab .btn-skip{background:#1e2230;color:#c8c3b7;border:1px solid rgba(255,255,255,.12)!important}',
      '#dh-spark-lab .lab-progress{height:5px;background:#232736;border-radius:99px;margin-bottom:12px;overflow:hidden}',
      '#dh-spark-lab .lab-progress i{display:block;height:100%;background:linear-gradient(90deg,#d4af37,#f0c040);width:0%;transition:width .25s}',
      '#dh-spark-lab .lab-result{background:#151824;border:1px solid rgba(255,255,255,.09);border-radius:16px;padding:15px;margin:10px 0;text-align:right}',
      '#dh-spark-lab .lab-result h3{margin:0 0 8px;color:#f5d472;font-size:.98rem}',
      '#dh-spark-lab .lab-result ul{margin:0;padding-right:18px;color:#d6d1c4;line-height:1.85;font-size:.88rem}',
      '#dh-spark-lab .lab-empty{text-align:center;color:#b8b3a6;line-height:1.8;padding:20px}',
      '#dh-spark-lab .lab-cta{display:block;width:100%;min-height:48px;margin-top:12px;padding:12px;border-radius:14px;border:none;background:linear-gradient(135deg,#d4af37,#f0c040);color:#15130b;font-family:inherit;font-weight:700;font-size:.95rem;cursor:pointer}',
      '#dh-spark-lab .lab-ghost{display:block;width:100%;min-height:46px;margin-top:8px;padding:10px;border-radius:14px;border:1px solid rgba(255,255,255,.12);background:#171a25;color:#c8c3b7;font-family:inherit;cursor:pointer}'
    ].join('');
    document.head.appendChild(s);
  }

  /** فیلتر صریح خرده‌انگیزه‌های متعلق به مسیرهای فعال و motive_driven (بدون تغییر وزن موتور) */
  function filterMotiveDrivenSparks(all, pathIndex) {
    var list = Array.isArray(all) ? all : [];
    var idx = pathIndex || buildPathIndex();
    return list.filter(function (item) {
      if (!item || !item.code || !item.description_fa) return false;
      return completeHits(item.code, idx).length > 0;
    });
  }

  function fetchMotives() {
    if (motivesCache) return Promise.resolve(motivesCache);
    // Same-origin Pages asset only: no credentials, redirects or API fallback.
    return fetch('data/micro_motives.json', {
      mode: 'same-origin', credentials: 'omit', redirect: 'error'
    })
      .then(function (r) {
        if (!r.ok) throw new Error('Static spark data unavailable');
        return r.json();
      })
      .then(function (arr) {
        if (!Array.isArray(arr)) throw new Error('Invalid static spark data');
        motivesCache = filterMotiveDrivenSparks(arr);
        return motivesCache;
      });
  }

  // Locked UI labels: independent of app.js, API and journey initialization.
  var REALM_TITLES = {
    healer: 'درمان و زندگی', builder: 'ساختن و مهندسی', explorer: 'کشف و دانش',
    thinker: 'اندیشه و جامعه', artist: 'خلق و هنر', speaker: 'واژه و فرهنگ'
  };

  function realmTitle(realmId) {
    return Object.prototype.hasOwnProperty.call(REALM_TITLES, realmId)
      ? 'محلهٔ ' + REALM_TITLES[realmId] : '';
  }

  function displayTitle(item) {
    return (item && (String(item.name || '').trim() || String(item.motto || '').trim())) || '';
  }

  /** پیشوند کد: MED-001 → MED- */
  function codePrefix(code) {
    if (!code) return '';
    var i = String(code).indexOf('-');
    if (i < 0) return String(code);
    return String(code).slice(0, i + 1);
  }

  /**
   * نگاشت پیشوند → مسیر باریک / گذر / محله
   * از NARROW_PATHS + SUB_REALMS + REALMS (data.js)
   */
  function buildPathIndex() {
    var index = {}; // prefix -> [{path, sub, realm}]
    var realmById = {};
    if (typeof REALMS !== 'undefined' && Array.isArray(REALMS)) {
      REALMS.forEach(function (r) { realmById[r.id] = r; });
    }
    var subById = {};
    if (typeof SUB_REALMS !== 'undefined') {
      Object.keys(SUB_REALMS).forEach(function (rid) {
        (SUB_REALMS[rid] || []).forEach(function (s) {
          subById[s.id] = { sub: s, realmId: rid };
        });
      });
    }
    if (typeof NARROW_PATHS === 'undefined') return index;
    Object.keys(NARROW_PATHS).forEach(function (subId) {
      var paths = NARROW_PATHS[subId] || [];
      var meta = subById[subId] || {};
      var realm = realmById[meta.realmId] || null;
      paths.forEach(function (p) {
        (p.majorCodes || []).forEach(function (pref) {
          if (!index[pref]) index[pref] = [];
          index[pref].push({
            pathId: p.id,
            pathName: displayTitle(p),
            pathIcon: p.icon || '',
            subId: subId,
            subName: displayTitle(meta.sub),
            realmId: meta.realmId || '',
            realmName: realmTitle(meta.realmId),
            realmIcon: (realm && realm.icon) || ''
          });
        });
      });
    });
    return index;
  }

  function resolveCode(code, index) {
    var pref = codePrefix(code);
    var hits = index[pref] || [];
    // اگر دقیق نبود، طولانی‌ترین پیشوند مطابق
    if (!hits.length) {
      Object.keys(index).forEach(function (k) {
        if (code && String(code).indexOf(k) === 0) hits = hits.concat(index[k]);
      });
    }
    return hits;
  }

  function completeHits(code, index) {
    return resolveCode(code, index).filter(function (hit) {
      return Boolean(realmTitle(hit.realmId) &&
        String(hit.subName || '').trim() && String(hit.pathName || '').trim());
    });
  }

  /** ۵–۶ نمونه متنوع از پیشوندهای مختلف */
  function sampleDiverse(all, n) {
    if (!all || !all.length) return [];
    var byPref = {};
    all.forEach(function (m) {
      var p = codePrefix(m.code);
      if (!byPref[p]) byPref[p] = [];
      byPref[p].push(m);
    });
    var prefs = Object.keys(byPref);
    // shuffle prefixes
    for (var i = prefs.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = prefs[i]; prefs[i] = prefs[j]; prefs[j] = t;
    }
    var out = [];
    var used = {};
    // یک از هر پیشوند تا n
    for (var k = 0; k < prefs.length && out.length < n; k++) {
      var list = byPref[prefs[k]];
      var pick = list[Math.floor(Math.random() * list.length)];
      if (pick && !used[pick.code]) {
        used[pick.code] = true;
        out.push(pick);
      }
    }
    // اگر کم بود از باقی
    if (out.length < n) {
      var rest = all.filter(function (m) { return !used[m.code]; });
      for (var r = rest.length - 1; r > 0; r--) {
        var j2 = Math.floor(Math.random() * (r + 1));
        var tmp = rest[r]; rest[r] = rest[j2]; rest[j2] = tmp;
      }
      for (var x = 0; x < rest.length && out.length < n; x++) out.push(rest[x]);
    }
    return out;
  }

  function stopTimer() {
    if (timerId) { clearInterval(timerId); timerId = null; }
  }

  function closeLab() {
    stopTimer();
    if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
    overlay = null;
    if (window.DHShell && typeof window.DHShell.restoreSparkTab === 'function') {
      window.DHShell.restoreSparkTab();
    }
  }

  function aggregateHits(likedCodes, index) {
    var pathScore = {};
    var subScore = {};
    var realmScore = {};
    var pathMeta = {};
    var subMeta = {};
    var realmMeta = {};
    likedCodes.forEach(function (code) {
      var seenPaths = {}, seenSubs = {}, seenRealms = {};
      completeHits(code, index).forEach(function (h) {
        // Count distinct selected sparks per node, not duplicate route links.
        if (!seenPaths[h.pathId]) pathScore[h.pathId] = (pathScore[h.pathId] || 0) + 1;
        if (!seenSubs[h.subId]) subScore[h.subId] = (subScore[h.subId] || 0) + 1;
        if (!seenRealms[h.realmId] && realmTitle(h.realmId)) {
          realmScore[h.realmId] = (realmScore[h.realmId] || 0) + 1;
        }
        seenPaths[h.pathId] = seenSubs[h.subId] = seenRealms[h.realmId] = true;
        pathMeta[h.pathId] = h;
        subMeta[h.subId] = h;
        realmMeta[h.realmId] = h;
      });
    });
    function top(scoreMap, metaMap, limit) {
      return Object.keys(scoreMap)
        .sort(function (a, b) { return scoreMap[b] - scoreMap[a]; })
        .slice(0, limit)
        .map(function (id) {
          return { id: id, count: scoreMap[id], meta: metaMap[id] };
        });
    }
    return {
      paths: top(pathScore, pathMeta, Object.keys(pathScore).length),
      subs: top(subScore, subMeta, Object.keys(subScore).length),
      realms: top(realmScore, realmMeta, Object.keys(realmScore).length)
    };
  }

  function renderResult(state) {
    var index = buildPathIndex();
    // Revalidate before rendering as well: incomplete chains never reach results.
    var selectedItems = state.likedItems.filter(function (item) {
      return completeHits(item.code, index).length > 0;
    });
    var selectedCodes = selectedItems.map(function (item) { return item.code; });
    var agg = aggregateHits(selectedCodes, index);
    var html = '<div class="lab-wrap">';
    html += '<div class="lab-top"><div class="lab-title">✦ نتیجهٔ یهویی</div>';
    html += '<button type="button" class="lab-close" id="dh-lab-x">بستن</button></div>';

    if (!selectedCodes.length) {
      html += '<div class="lab-empty">در این دقیقه هیچ جرقه‌ای انتخاب نشد.<br>می‌توانی دوباره امتحان کنی.</div>';
    } else {
      html += '<div class="lab-result"><h3>جرقه‌هایی که انتخاب کردی (' + selectedCodes.length + ')</h3><ul>';
      selectedItems.forEach(function (m) {
        html += '<li>' + escapeHtml(m.description_fa || 'جرقهٔ انتخابی') + '</li>';
      });
      html += '</ul></div>';

      if (agg.realms.length) {
        html += '<div class="lab-result"><h3>محله‌ها</h3><ul>';
        agg.realms.forEach(function (r) {
          var m = r.meta || {};
          html += '<li>' + (m.realmIcon || '') + ' ' + escapeHtml(m.realmName || realmTitle(r.id)) +
            ' <span style="color:#9d988c">(' + r.count + ' جرقه)</span></li>';
        });
        html += '</ul></div>';
      }
      if (agg.subs.length) {
        html += '<div class="lab-result"><h3>گذرها</h3><ul>';
        agg.subs.forEach(function (r) {
          var m = r.meta || {};
          html += '<li>' + escapeHtml(m.subName || 'عنوان گذر در نقشهٔ استاتیک ثبت نشده') +
            ' <span style="color:#9d988c">(' + r.count + ')</span></li>';
        });
        html += '</ul></div>';
      }
      if (agg.paths.length) {
        html += '<div class="lab-result"><h3>مسیرهای باریک</h3><ul>';
        agg.paths.forEach(function (r) {
          var m = r.meta || {};
          html += '<li>' + (m.pathIcon || '') + ' <strong>' + escapeHtml(m.pathName || 'عنوان مسیر باریک در نقشهٔ استاتیک ثبت نشده') + '</strong>' +
            ' <span style="color:#9d988c">— ' + escapeHtml(m.realmName || '') + '</span></li>';
        });
        html += '</ul></div>';
      }
      html += '<p class="lab-note">اگر این جرقه‌ها را دوست داشتی، در سفر اکتشافی از همان محله‌ها و مسیرهای باریک وارد شو.</p>';
    }

    html += '<button type="button" class="lab-ghost" id="dh-lab-again">یک دور دیگر جرقه‌یابی ↻</button>';
    html += '<button type="button" class="lab-ghost" id="dh-lab-done">بازگشت به صفحه اول</button>';
    html += '</div>';

    overlay.innerHTML = html;
    $('dh-lab-x').onclick = closeLab;
    $('dh-lab-done').onclick = closeLab;
    $('dh-lab-again').onclick = function () { startSession(); };

    // نشان ساده
    var badges = loadBadges();
    if (selectedCodes.length > 0 && badges.indexOf('lab_first') < 0) {
      badges.push('lab_first');
      saveBadges(badges);
    }

    saveLab({
      lastAt: Date.now(),
      likedCodes: selectedCodes,
      paths: agg.paths.map(function (p) { return p.id; })
    });
  }

  function escapeHtml(t) {
    return String(t || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function startSession() {
    stopTimer();
    ensureStyles();
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'dh-spark-lab';
      document.body.appendChild(overlay);
    }
    overlay.innerHTML = '<div class="lab-wrap"><p class="lab-empty">در حال بارگذاری جرقه‌ها از فایل‌های سایت…</p></div>';

    var sessionOverlay = overlay;
    fetchMotives().then(function (all) {
      if (overlay !== sessionOverlay) return;
      all = filterMotiveDrivenSparks(all);
      if (!all.length) {
        overlay.innerHTML = '<div class="lab-wrap"><p class="lab-empty">بارگذاری خرده‌انگیزه‌ها ممکن نشد.</p>' +
          '<button type="button" class="lab-ghost" id="dh-lab-x">بستن</button></div>';
        $('dh-lab-x').onclick = closeLab;
        return;
      }

      var deck = sampleDiverse(all, TARGET_CARDS);
      var state = {
        deck: deck,
        index: 0,
        liked: [],
        likedItems: [],
        left: DURATION_SEC
      };

      function paint() {
        if (state.left <= 0 || state.index >= state.deck.length) {
          stopTimer();
          renderResult(state);
          return;
        }
        var card = state.deck[state.index];
        var pct = Math.round((state.index / state.deck.length) * 100);
        var warn = state.left <= 10 ? ' warn' : '';
        overlay.innerHTML =
          '<div class="lab-wrap"><p class="lab-note">اتفاقی ببین؛ خودت بگو چی بهت می‌چسبه.</p>' +
            '<div class="lab-top">' +
              '<div class="lab-title">✦ یهویی</div>' +
              '<button type="button" class="lab-close" id="dh-lab-x">بستن</button>' +
            '</div>' +
            '<p class="lab-note">از بیش از هزار خرده‌انگیزه، چند مورد تصادفی — ' +
              'روی نتیجهٔ سفر اصلی اثر ندارد.</p>' +
            '<div class="lab-timer' + warn + '" id="dh-lab-timer">' + state.left + ' ثانیه</div>' +
            '<div class="lab-progress"><i style="width:' + pct + '%"></i></div>' +
            '<div class="lab-card">' +
              '<p>' + escapeHtml(card.description_fa || '') + '</p>' +
              '<div class="lab-meta">' + (state.index + 1) + ' از ' + state.deck.length + '</div>' +
            '</div>' +
            '<div class="lab-actions">' +
              '<button type="button" class="btn-skip" id="dh-lab-skip">جذبم نکرد</button>' +
              '<button type="button" class="btn-like" id="dh-lab-like">جرقه زد ❤️</button>' +
            '</div>' +
          '</div>';

        $('dh-lab-x').onclick = closeLab;
        $('dh-lab-like').onclick = function () {
          if (typeof window.dhHaptic === 'function') window.dhHaptic('success');
          state.liked.push(card.code);
          state.likedItems.push(card);
          state.index++;
          paint();
        };
        $('dh-lab-skip').onclick = function () {
          if (typeof window.dhHaptic === 'function') window.dhHaptic('light');
          state.index++;
          paint();
        };
      }

      paint();
      timerId = setInterval(function () {
        state.left--;
        var el = $('dh-lab-timer');
        if (el) {
          el.textContent = Math.max(0, state.left) + ' ثانیه';
          if (state.left <= 10) el.classList.add('warn');
        }
        if (state.left <= 0) {
          stopTimer();
          renderResult(state);
        }
      }, 1000);
    }).catch(function () {
      if (overlay !== sessionOverlay) return;
      overlay.innerHTML = '<div class="lab-wrap"><p class="lab-empty">خطا در بارگذاری.</p>' +
        '<button type="button" class="lab-ghost" id="dh-lab-x">بستن</button></div>';
      var x = $('dh-lab-x');
      if (x) x.onclick = closeLab;
    });
  }

  window.DHSparkGame = {
    open: function (opts) {
      if (overlay && overlay.parentNode) return;
      if (!opts || !opts.fromPopState) {
        if (typeof window.dhPushSubView === 'function') window.dhPushSubView('spark');
      }
      startSession();
      if (window.DHShell && typeof window.DHShell.setActiveTab === 'function') {
        window.DHShell.setActiveTab('spark');
      }
    },
    peek: function () {
      var saved = loadLab();
      var cnt = (saved && Array.isArray(saved.likedCodes)) ? saved.likedCodes.length : 0;
      return { likedCount: cnt, played: Boolean(saved && saved.lastAt) };
    },
    close: closeLab,
    filterMotiveDrivenSparks: filterMotiveDrivenSparks,
    buildPathIndex: buildPathIndex,
    isOpen: function () { return Boolean(overlay && overlay.parentNode); }
  };
})();
