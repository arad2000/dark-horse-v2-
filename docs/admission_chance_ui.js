/* Dark Horse — Phase 1 university admission chance UI.
 * This module is intentionally independent from scoring/ranking.
 */
(function () {
  'use strict';

  var API_BASE_URL = 'https://api.asbe-siah.ir';
  var ADMISSION_PATH = '/api/v1/admission/chance';
  var WIDGET_ID = 'dh-admission-chance-widget';

  var COURSE_LABELS = {
    roozaneh: 'روزانه',
    nobat_dovom: 'نوبت دوم',
    savabegh_dolati: 'سوابق تحصیلی دولتی',
    azad: 'آزاد',
    payam_noor: 'پیام نور',
    nonprofit: 'غیرانتفاعی'
  };

  var QUOTA_OPTIONS = [
    { value: 'azad', label: 'عادی / سایر سهمیه‌ها' },
    { value: 'isargaran_25', label: 'ایثارگران ۲۵٪' },
    { value: 'isargaran_5', label: 'ایثارگران ۵٪' },
    { value: 'shahid', label: 'خانواده شهدا' }
  ];

  function escapeHtml(value) {
    var text = String(value == null ? '' : value);
    return text.replace(/[&<>"']/g, function (ch) {
      return ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      })[ch];
    });
  }

  function getMajorRecommendations() {
    try {
      if (typeof state === 'undefined' || !state || !state.majorsResult) return [];
      var result = state.majorsResult.discovery_result;
      var recommendations = result && Array.isArray(result.recommendations)
        ? result.recommendations
        : [];
      return recommendations;
    } catch (_) {
      return [];
    }
  }

  function buildMajorMap(recommendations) {
    var map = {};
    recommendations.forEach(function (item) {
      var id = Number(item && item.major_id);
      if (!Number.isInteger(id) || id <= 0) return;
      map[String(id)] = item.major_name_fa || item.major_name || ('رشته ' + id);
    });
    return map;
  }

  function uniqueMajorIds(recommendations) {
    var seen = {};
    var ids = [];
    recommendations.forEach(function (item) {
      var id = Number(item && item.major_id);
      if (!Number.isInteger(id) || id <= 0) return;
      if (seen[id]) return;
      seen[id] = true;
      ids.push(id);
    });
    return ids;
  }

  function selectedFormValues(form) {
    return {
      rank: Number(form.rank.value),
      region_zone: Number(form.region_zone.value),
      quota: String(form.quota.value || '').trim(),
      province: String(form.province.value || '').trim()
    };
  }

  function buildRequestPayload(recommendations, form) {
    var values = selectedFormValues(form);
    return {
      major_ids: uniqueMajorIds(recommendations),
      rank: values.rank,
      region_zone: values.region_zone,
      quota: values.quota,
      province: values.province || null,
      limit: 30
    };
  }

  function validateValues(values, majorIds) {
    if (!majorIds.length) return 'رشته‌ای برای بررسی شانس قبولی در نتیجهٔ کشف رشته پیدا نشد.';
    if (!Number.isInteger(values.rank) || values.rank < 1) {
      return 'رتبه را به صورت یک عدد صحیح بزرگ‌تر از صفر وارد کن.';
    }
    if (![1, 2, 3].includes(values.region_zone)) {
      return 'منطقه باید ۱، ۲ یا ۳ باشد.';
    }
    if (!values.quota) return 'سهمیه را انتخاب کن.';
    if (!values.province) return 'استان داوطلب را وارد کن.';
    return '';
  }

  function cutoffText(item) {
    var cutoff = item && item.cutoff_used;
    if (cutoff == null) return 'cutoff: اطلاعات کافی نیست';
    if (typeof cutoff === 'object') {
      var parts = [];
      if (cutoff.minimum_gpa != null) parts.push('حداقل معدل: ' + cutoff.minimum_gpa);
      if (cutoff.minimum_traz != null) parts.push('حداقل تراز: ' + cutoff.minimum_traz);
      return parts.length ? parts.join(' · ') : 'cutoff: اطلاعات تحصیلی';
    }
    var year = item.cutoff_year ? ' · سال ' + item.cutoff_year : '';
    return 'cutoff: ' + cutoff + year;
  }

  function renderItems(items, majorMap) {
    if (!Array.isArray(items) || !items.length) {
      return '<div class="dh-admission-card"><p style="margin:0;color:#c9b896;">برای ورودی فعلی، برنامه‌ای با دادهٔ cutoff قابل استفاده پیدا نشد.</p></div>';
    }

    return items.map(function (item) {
      var majorName = majorMap[String(item.major_id)] || ('رشته ' + String(item.major_id || 'نامشخص'));
      var course = COURSE_LABELS[item.course_type] || item.course_type || 'نوع دوره نامشخص';
      var method = item.method || 'روش پذیرش نامشخص';
      var note = item.note
        ? '<p class="dh-admission-note">' + escapeHtml(item.note) + '</p>'
        : '';

      return (
        '<article class="dh-admission-card">' +
          '<div class="dh-admission-card-head">' +
            '<div>' +
              '<h4 class="dh-admission-university">' + escapeHtml(item.university_name || 'دانشگاه نامشخص') + '</h4>' +
              '<p class="dh-admission-major">' + escapeHtml(majorName) + '</p>' +
            '</div>' +
            '<span class="dh-admission-label">' + escapeHtml(item.label || 'نتیجه تخمینی') + '</span>' +
          '</div>' +
          '<div class="dh-admission-meta">' +
            '<span>🎓 نوع دوره: ' + escapeHtml(course) + '</span>' +
            '<span>🧾 روش پذیرش: ' + escapeHtml(method) + '</span>' +
            '<span>📌 ' + escapeHtml(cutoffText(item)) + '</span>' +
            '<span>🏷️ program_id: ' + escapeHtml(item.program_id || '—') + '</span>' +
          '</div>' +
          note +
        '</article>'
      );
    }).join('');
  }

  function formHtml() {
    var quotaOptions = QUOTA_OPTIONS.map(function (option) {
      return '<option value="' + escapeHtml(option.value) + '">' + escapeHtml(option.label) + '</option>';
    }).join('');

    return (
      '<form class="dh-admission-chance-form" id="dh-admission-chance-form">' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-rank">رتبه</label>' +
          '<input id="dh-admission-rank" name="rank" type="number" min="1" step="1" inputmode="numeric" placeholder="مثلاً 2500" required>' +
        '</div>' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-region">منطقه</label>' +
          '<select id="dh-admission-region" name="region_zone" required>' +
            '<option value="">انتخاب منطقه</option>' +
            '<option value="1">منطقه ۱</option>' +
            '<option value="2">منطقه ۲</option>' +
            '<option value="3">منطقه ۳</option>' +
          '</select>' +
        '</div>' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-quota">سهمیه</label>' +
          '<select id="dh-admission-quota" name="quota" required>' +
            '<option value="">انتخاب سهمیه</option>' +
            quotaOptions +
          '</select>' +
        '</div>' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-province">استان داوطلب</label>' +
          '<input id="dh-admission-province" name="province" type="text" maxlength="128" placeholder="مثلاً تهران" autocomplete="address-level1" required>' +
        '</div>' +
        '<button class="dh-admission-submit" id="dh-admission-submit" type="submit">🎯 بررسی شانس قبولی دانشگاه</button>' +
      '</form>' +
      '<div class="dh-admission-status" id="dh-admission-status" aria-live="polite"></div>' +
      '<div class="dh-admission-results" id="dh-admission-results"></div>'
    );
  }

  function widgetHtml() {
    return (
      '<section class="dh-admission-chance-widget" id="' + WIDGET_ID + '">' +
        '<h3>🎓 تخمین شانس قبولی دانشگاه</h3>' +
        '<p class="dh-admission-chance-lead">' +
          'بعد از کشف رشته‌ها، می‌توانی با رتبه، منطقه، سهمیه و استان، برنامه‌های دانشگاهی مرتبط را با برچسب کیفی ببینی.' +
        '</p>' +
        '<button type="button" class="btn btn-primary dh-admission-submit" id="dh-admission-open-form">بررسی شانس قبولی</button>' +
        '<div id="dh-admission-form-wrap" hidden style="margin-top:14px;">' +
          formHtml() +
        '</div>' +
        '<div class="dh-admission-disclaimer">' +
          'این بخش مستقل از امتیاز فردیت و رتبه‌بندی اسب سیاه است. نتایج فقط تخمینی و بر اساس مدل‌سازی آماری هستند و جایگزین دفترچه و نتایج رسمی سنجش نیستند.' +
        '</div>' +
      '</section>'
    );
  }

  function setStatus(text, isError) {
    var el = document.getElementById('dh-admission-status');
    if (!el) return;
    el.textContent = text || '';
    el.classList.toggle('error', !!isError);
  }

  async function requestAdmissionChance(recommendations, form) {
    var majorIds = uniqueMajorIds(recommendations);
    var values = selectedFormValues(form);
    var validationError = validateValues(values, majorIds);
    if (validationError) {
      setStatus(validationError, true);
      return;
    }

    var submit = document.getElementById('dh-admission-submit');
    var results = document.getElementById('dh-admission-results');
    if (submit) {
      submit.disabled = true;
      submit.textContent = 'در حال بررسی…';
    }
    setStatus('در حال محاسبهٔ نتایج دانشگاهی…', false);
    if (results) results.innerHTML = '';

    try {
      var response = await fetch(API_BASE_URL + ADMISSION_PATH, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(buildRequestPayload(recommendations, form))
      });

      var payload = null;
      try {
        payload = await response.json();
      } catch (_) {}

      if (!response.ok) {
        var detail = payload && (payload.detail || payload.message);
        throw new Error(typeof detail === 'string' ? detail : ('خطا در سرویس شانس قبولی: ' + response.status));
      }

      if (results) {
        var majorMap = buildMajorMap(recommendations);
        results.innerHTML =
          '<p class="dh-admission-summary">تعداد نتایج: <strong>' +
          escapeHtml(payload.count || 0) +
          '</strong> مورد</p>' +
          renderItems(payload.items || [], majorMap) +
          '<div class="dh-admission-disclaimer">' +
          escapeHtml(payload.disclaimer || 'نتایج تخمینی و جایگزین دفترچه و نتایج رسمی سنجش نیستند.') +
          '</div>';
      }
      setStatus('✅ نتایج شانس قبولی دریافت شد.', false);
    } catch (error) {
      setStatus('❌ ' + String(error && error.message ? error.message : error), true);
    } finally {
      if (submit) {
        submit.disabled = false;
        submit.textContent = '🎯 بررسی شانس قبولی دانشگاه';
      }
    }
  }

  function bindWidget(recommendations) {
    var openButton = document.getElementById('dh-admission-open-form');
    var wrap = document.getElementById('dh-admission-form-wrap');
    var form = document.getElementById('dh-admission-chance-form');
    if (!openButton || !wrap || !form) return;

    openButton.addEventListener('click', function () {
      wrap.hidden = !wrap.hidden;
      if (!wrap.hidden) {
        openButton.textContent = 'بستن فرم شانس قبولی';
        var rank = document.getElementById('dh-admission-rank');
        if (rank) rank.focus();
      } else {
        openButton.textContent = 'بررسی شانس قبولی';
      }
    });

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      requestAdmissionChance(recommendations, form);
    });
  }

  function isMajorResultsView() {
    var app = document.getElementById('app');
    if (!app) return false;
    var heading = app.querySelector('h2');
    return !!(
      heading &&
      String(heading.textContent || '').indexOf('نتیجه انتخاب رشته') >= 0 &&
      getMajorRecommendations().length
    );
  }

  function inject() {
    var app = document.getElementById('app');
    if (!app || !isMajorResultsView()) return;
    if (document.getElementById(WIDGET_ID)) return;

    var recommendations = getMajorRecommendations();
    var widget = document.createElement('div');
    widget.innerHTML = widgetHtml();
    var section = widget.firstElementChild;
    if (!section) return;

    var feedback = document.getElementById('feedbackSection');
    if (feedback && feedback.parentNode === app) {
      app.insertBefore(section, feedback);
    } else {
      app.appendChild(section);
    }
    bindWidget(recommendations);
  }

  function init() {
    var app = document.getElementById('app');
    if (!app) return;

    var observer = new MutationObserver(function () {
      inject();
    });
    observer.observe(app, { childList: true, subtree: true });
    inject();
  }

  window.DHAdmissionChanceUI = {
    init: init,
    buildRequestPayload: buildRequestPayload,
    uniqueMajorIds: uniqueMajorIds
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
