/* Dark Horse — Phase 3 university admission chance UI.
 * UI-only admission path switch. Independent from scoring/ranking.
 * Sends the Phase 3 API contract: admission_path=exam|record.
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

  var PROVINCES = [
    'آذربایجان شرقی', 'آذربایجان غربی', 'اردبیل', 'اصفهان', 'البرز', 'ایلام',
    'بوشهر', 'تهران', 'چهارمحال و بختیاری', 'خراسان جنوبی', 'خراسان رضوی',
    'خراسان شمالی', 'خوزستان', 'زنجان', 'سمنان', 'سیستان و بلوچستان', 'فارس',
    'قزوین', 'قم', 'کردستان', 'کرمان', 'کرمانشاه', 'کهگیلویه و بویراحمد',
    'گلستان', 'گیلان', 'لرستان', 'مازندران', 'مرکزی', 'هرمزگان', 'همدان', 'یزد'
  ];

  var REGION_OPTIONS = [
    { value: '1', label: 'منطقه ۱' },
    { value: '2', label: 'منطقه ۲' },
    { value: '3', label: 'منطقه ۳' }
  ];

  var SPECIAL_QUOTA_OPTIONS = [
    { value: 'none', label: 'بدون سهمیه خاص' },
    { value: 'isargaran_25', label: 'ایثارگران ۲۵٪' },
    { value: 'isargaran_5', label: 'ایثارگران ۵٪' },
    { value: 'shahid', label: 'خانواده شهدا' }
  ];

  var DIPLOMA_OPTIONS = [
    { value: 'riazi', label: 'ریاضی‌فیزیک' },
    { value: 'tajrobi', label: 'علوم تجربی' },
    { value: 'ensani', label: 'علوم انسانی' },
    { value: 'maaref', label: 'علوم و معارف اسلامی' },
    { value: 'other_fani', label: 'فنی / کاردانش / سایر' }
  ];

  var TARGET_GROUP_OPTIONS = [
    { value: '', label: 'تشخیص خودکار از رشته' },
    { value: 'riazi', label: 'ریاضی' },
    { value: 'tajrobi', label: 'تجربی' },
    { value: 'ensani', label: 'انسانی' },
    { value: 'honar', label: 'هنر' },
    { value: 'zaban', label: 'زبان' }
  ];

  function escapeHtml(value) {
    var text = String(value == null ? '' : value);
    return text.replace(/[&<>\"']/g, function (ch) {
      return ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '\"': '&quot;',
        "'": '&#39;'
      })[ch];
    });
  }

  function getMajorRecommendations() {
    try {
      if (typeof state === 'undefined' || !state || !state.majorsResult) return [];
      var result = state.majorsResult.discovery_result;
      return result && Array.isArray(result.recommendations) ? result.recommendations : [];
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
      if (!Number.isInteger(id) || id <= 0 || seen[id]) return;
      seen[id] = true;
      ids.push(id);
    });
    return ids;
  }

  function optionsHtml(options) {
    return options.map(function (option) {
      return '<option value="' + escapeHtml(option.value) + '">' +
        escapeHtml(option.label) + '</option>';
    }).join('');
  }

  function provinceOptionsHtml() {
    return PROVINCES.map(function (province) {
      return '<option value="' + escapeHtml(province) + '">' +
        escapeHtml(province) + '</option>';
    }).join('');
  }

  function selectedFormValues(form, path) {
    if (path === 'record') {
      var diploma = String(form.diploma_type.value || '').trim();
      var target = String(form.target_field_group.value || '').trim();
      var gpaField = diploma === 'other_fani' ? 'gpa_total' : 'gpa_written';
      return {
        province: String(form.province.value || '').trim(),
        diploma_type: diploma,
        target_field_group: target || null,
        gpa_field: gpaField,
        gpa_value: Number(form[gpaField].value)
      };
    }

    return {
      rank_in_quota: Number(form.rank_in_quota.value),
      region_zone: Number(form.region_zone.value),
      special_quota: String(form.special_quota.value || 'none').trim() || 'none',
      province: String(form.province.value || '').trim(),
      national_rank: form.national_rank.value ? Number(form.national_rank.value) : null,
      diploma_type: String(form.diploma_type.value || '').trim() || null,
      gpa_written: form.gpa_written.value ? Number(form.gpa_written.value) : null
    };
  }

  function buildRequestPayload(recommendations, form, path) {
    var majorIds = uniqueMajorIds(recommendations);
    var values = selectedFormValues(form, path);

    if (path === 'record') {
      var payload = {
        admission_path: 'record',
        major_ids: majorIds,
        province: values.province || null,
        diploma_type: values.diploma_type || null,
        target_field_group: values.target_field_group || null,
        limit: 30
      };
      if (values.diploma_type === 'other_fani') {
        payload.gpa_total = values.gpa_value;
      } else {
        payload.gpa_written = values.gpa_value;
      }
      return payload;
    }

    return {
      admission_path: 'exam',
      major_ids: majorIds,
      rank_in_quota: values.rank_in_quota,
      region_zone: values.region_zone,
      special_quota: values.special_quota,
      province: values.province || null,
      national_rank: values.national_rank,
      diploma_type: values.diploma_type,
      gpa_written: values.gpa_written,
      limit: 30
    };
  }

  function validateValues(values, path, majorIds) {
    if (!majorIds.length) {
      return 'رشته‌ای برای بررسی شانس قبولی در نتیجهٔ کشف رشته پیدا نشد.';
    }

    if (!values.province) {
      return 'استان داوطلب را از فهرست ۳۱ استان انتخاب کن.';
    }

    if (path === 'exam') {
      if (!Number.isInteger(values.rank_in_quota) || values.rank_in_quota < 1) {
        return 'رتبه در سهمیه را به صورت یک عدد صحیح بزرگ‌تر از صفر وارد کن.';
      }
      if (![1, 2, 3].includes(values.region_zone)) {
        return 'منطقه باید ۱، ۲ یا ۳ باشد.';
      }
      if (values.national_rank != null &&
          (!Number.isInteger(values.national_rank) || values.national_rank < 1)) {
        return 'رتبه کشوری اختیاری باید عددی بزرگ‌تر از صفر باشد.';
      }
      if (values.gpa_written != null &&
          (!Number.isFinite(values.gpa_written) || values.gpa_written < 0 || values.gpa_written > 20)) {
        return 'معدل کتبی اختیاری را بین ۰ تا ۲۰ وارد کن.';
      }
      return '';
    }

    if (!values.diploma_type) return 'نوع دیپلم را انتخاب کن.';
    if (!Number.isFinite(values.gpa_value) || values.gpa_value < 0 || values.gpa_value > 20) {
      return values.gpa_field === 'gpa_total'
        ? 'معدل کل را بین ۰ تا ۲۰ وارد کن.'
        : 'معدل کتبی نهایی را بین ۰ تا ۲۰ وارد کن.';
    }
    return '';
  }

  function cutoffText(item, path) {
    if (path === 'record') {
      var academic = item && item.cutoff_used;
      if (!academic || typeof academic !== 'object') return 'حداقل معدل: ثبت نشده';
      var minimum = academic.minimum_gpa;
      return minimum == null ? 'حداقل معدل: ثبت نشده' : 'حداقل معدل برنامه: ' + minimum;
    }

    var cutoff = item && item.cutoff_used;
    if (cutoff == null) return 'cutoff: اطلاعات کافی نیست';
    var dimension = item.cutoff_dimension ? ' · بعد: ' + item.cutoff_dimension : '';
    var year = item.cutoff_year ? ' · سال ' + item.cutoff_year : '';
    return 'cutoff: ' + cutoff + dimension + year;
  }

  function renderItems(items, majorMap, path) {
    if (!Array.isArray(items) || !items.length) {
      var emptyText = path === 'record'
        ? 'برای رشته‌های فعلی، برنامه‌ای با پذیرش «صرفاً سوابق تحصیلی» و دادهٔ قابل استفاده پیدا نشد. این وضعیت به معنی رد شدن داوطلب نیست.'
        : 'برای ورودی فعلی، برنامه‌ای با دادهٔ cutoff قابل استفاده پیدا نشد.';
      return '<div class="dh-admission-card dh-admission-empty"><p>' +
        escapeHtml(emptyText) + '</p></div>';
    }

    return items.map(function (item) {
      var majorName = majorMap[String(item.major_id)] ||
        ('رشته ' + String(item.major_id || 'نامشخص'));
      var course = COURSE_LABELS[item.course_type] || item.course_type || 'نوع دوره نامشخص';
      var method = item.method || (path === 'record' ? 'سوابق تحصیلی' : 'با آزمون');
      var note = item.note
        ? '<p class="dh-admission-note">' + escapeHtml(item.note) + '</p>'
        : '';

      var pathMeta = path === 'record'
        ? (
          '<span>🧮 ضریب معدل: ' + escapeHtml(item.gpa_coefficient) + '%</span>' +
          '<span>📚 معدل مؤثر: ' + escapeHtml(item.gpa_effective) + '</span>'
        )
        : (
          '<span>🏁 بعد cutoff: ' + escapeHtml(item.cutoff_dimension || '—') + '</span>' +
          '<span>📌 ' + escapeHtml(cutoffText(item, path)) + '</span>'
        );

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
            pathMeta +
            '<span>🏷️ program_id: ' + escapeHtml(item.program_id || '—') + '</span>' +
          '</div>' +
          note +
        '</article>'
      );
    }).join('');
  }

  function examFormHtml() {
    return (
      '<form class="dh-admission-chance-form dh-admission-path-form" id="dh-admission-exam-form" data-path="exam">' +
        '<div class="dh-admission-field full">' +
          '<label for="dh-admission-rank">رتبه در سهمیه *</label>' +
          '<input id="dh-admission-rank" name="rank_in_quota" type="number" min="1" step="1" inputmode="numeric" placeholder="مثلاً 2500" required>' +
          '<small class="dh-admission-help">رتبه در سهمیه از کارنامه ملاک عمل انتخاب رشته سنجش؛ این فیلد در مسیر با آزمون اصلی است.</small>' +
        '</div>' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-region">منطقه *</label>' +
          '<select id="dh-admission-region" name="region_zone" required>' +
            '<option value="">انتخاب منطقه</option>' + optionsHtml(REGION_OPTIONS) +
          '</select>' +
        '</div>' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-special-quota">سهمیه خاص</label>' +
          '<select id="dh-admission-special-quota" name="special_quota">' +
            optionsHtml(SPECIAL_QUOTA_OPTIONS) +
          '</select>' +
        '</div>' +
        '<div class="dh-admission-field full">' +
          '<label for="dh-admission-exam-province">استان بومی *</label>' +
          '<select id="dh-admission-exam-province" name="province" required>' +
            '<option value="">انتخاب استان</option>' + provinceOptionsHtml() +
          '</select>' +
          '<small class="dh-admission-help">منطقه و سهمیه خاص عمداً دو انتخاب مستقل هستند.</small>' +
        '</div>' +
        '<div class="dh-admission-subtitle full">اطلاعات تکمیلی اختیاری</div>' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-national-rank">رتبه کشوری</label>' +
          '<input id="dh-admission-national-rank" name="national_rank" type="number" min="1" step="1" inputmode="numeric" placeholder="اختیاری">' +
        '</div>' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-exam-diploma">نوع دیپلم</label>' +
          '<select id="dh-admission-exam-diploma" name="diploma_type">' +
            '<option value="">ثبت نشود</option>' + optionsHtml(DIPLOMA_OPTIONS) +
          '</select>' +
        '</div>' +
        '<div class="dh-admission-field full">' +
          '<label for="dh-admission-exam-gpa">معدل کتبی نهایی (اطلاعاتی)</label>' +
          '<input id="dh-admission-exam-gpa" name="gpa_written" type="number" min="0" max="20" step="0.01" inputmode="decimal" placeholder="اختیاری؛ مثلاً 18.75">' +
          '<small class="dh-admission-help">در مسیر با آزمون، رتبه در سهمیه معیار اصلی این سرویس است؛ این معدل جایگزین رتبه نمی‌شود.</small>' +
        '</div>' +
        '<button class="dh-admission-submit full" type="submit">🎯 بررسی شانس با آزمون</button>' +
      '</form>'
    );
  }

  function recordFormHtml() {
    return (
      '<form class="dh-admission-chance-form dh-admission-path-form" id="dh-admission-record-form" data-path="record">' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-record-diploma">نوع دیپلم *</label>' +
          '<select id="dh-admission-record-diploma" name="diploma_type" required>' +
            '<option value="">انتخاب نوع دیپلم</option>' + optionsHtml(DIPLOMA_OPTIONS) +
          '</select>' +
        '</div>' +
        '<div class="dh-admission-field">' +
          '<label for="dh-admission-target-group">گروه رشته هدف</label>' +
          '<select id="dh-admission-target-group" name="target_field_group">' +
            optionsHtml(TARGET_GROUP_OPTIONS) +
          '</select>' +
          '<small class="dh-admission-help">برای رشته‌های قابل استنتاج، تشخیص خودکار انجام می‌شود.</small>' +
        '</div>' +
        '<div class="dh-admission-field full">' +
          '<label for="dh-admission-record-province">استان بومی *</label>' +
          '<select id="dh-admission-record-province" name="province" required>' +
            '<option value="">انتخاب استان</option>' + provinceOptionsHtml() +
          '</select>' +
        '</div>' +
        '<div class="dh-admission-field full">' +
          '<label id="dh-admission-record-gpa-label" for="dh-admission-record-gpa">معدل کتبی نهایی *</label>' +
          '<input id="dh-admission-record-gpa" name="gpa_written" type="number" min="0" max="20" step="0.01" inputmode="decimal" placeholder="مثلاً 18.50" required>' +
          '<small class="dh-admission-help" id="dh-admission-record-gpa-help">برای دیپلم‌های نظری، gpa_written استفاده می‌شود.</small>' +
        '</div>' +
        '<div class="dh-admission-info full">' +
          'این مسیر رتبه نمی‌گیرد؛ معدل مؤثر از جدول ضریب «نوع دیپلم × گروه رشته هدف» محاسبه و با حداقل معدل برنامه مقایسه می‌شود.' +
        '</div>' +
        '<button class="dh-admission-submit full" type="submit">📚 بررسی شانس با سوابق تحصیلی</button>' +
      '</form>'
    );
  }

  function widgetHtml() {
    return (
      '<section class="dh-admission-chance-widget" id="' + WIDGET_ID + '">' +
        '<div class="dh-admission-heading-row">' +
          '<div>' +
            '<h3>🎓 تخمین شانس قبولی دانشگاه</h3>' +
            '<p class="dh-admission-chance-lead">مسیر پذیرش را جدا انتخاب کن؛ «با آزمون» و «سوابق تحصیلی» منطق و ورودی مستقل دارند.</p>' +
          '</div>' +
        '</div>' +
        '<div class="dh-admission-tabs" role="tablist" aria-label="مسیر پذیرش">' +
          '<button type="button" class="dh-admission-tab active" role="tab" aria-selected="true" aria-controls="dh-admission-exam-panel" id="dh-admission-tab-exam" data-admission-tab="exam">با آزمون</button>' +
          '<button type="button" class="dh-admission-tab" role="tab" aria-selected="false" aria-controls="dh-admission-record-panel" id="dh-admission-tab-record" data-admission-tab="record">سوابق تحصیلی</button>' +
        '</div>' +
        '<div class="dh-admission-panel" id="dh-admission-exam-panel" role="tabpanel" aria-labelledby="dh-admission-tab-exam">' +
          examFormHtml() +
        '</div>' +
        '<div class="dh-admission-panel" id="dh-admission-record-panel" role="tabpanel" aria-labelledby="dh-admission-tab-record" hidden>' +
          recordFormHtml() +
        '</div>' +
        '<div class="dh-admission-status" id="dh-admission-status" aria-live="polite"></div>' +
        '<div class="dh-admission-results" id="dh-admission-results"></div>' +
        '<div class="dh-admission-disclaimer">این بخش مستقل از امتیاز فردیت و رتبه‌بندی اسب سیاه است. نتایج فقط تخمینی و بر اساس داده‌های cutoff/سوابق موجود هستند و جایگزین دفترچه و اعلام رسمی سنجش نیستند.</div>' +
      '</section>'
    );
  }

  function setStatus(text, isError) {
    var el = document.getElementById('dh-admission-status');
    if (!el) return;
    el.textContent = text || '';
    el.classList.toggle('error', !!isError);
  }

  function updateRecordGpaField() {
    var form = document.getElementById('dh-admission-record-form');
    var diploma = form && form.diploma_type ? form.diploma_type.value : '';
    var input = document.getElementById('dh-admission-record-gpa');
    var label = document.getElementById('dh-admission-record-gpa-label');
    var help = document.getElementById('dh-admission-record-gpa-help');
    if (!input || !label || !help) return;

    var isFani = diploma === 'other_fani';
    input.name = isFani ? 'gpa_total' : 'gpa_written';
    input.placeholder = isFani ? 'مثلاً 17.50' : 'مثلاً 18.50';
    label.textContent = isFani ? 'معدل کل *' : 'معدل کتبی نهایی *';
    help.textContent = isFani
      ? 'برای دیپلم فنی/کاردانش، فقط gpa_total ارسال می‌شود.'
      : 'برای دیپلم‌های نظری، فقط gpa_written ارسال می‌شود.';
  }

  async function requestAdmissionChance(recommendations, form, path) {
    var majorIds = uniqueMajorIds(recommendations);
    var values = selectedFormValues(form, path);
    var validationError = validateValues(values, path, majorIds);
    if (validationError) {
      setStatus(validationError, true);
      return;
    }

    var submit = form.querySelector('.dh-admission-submit');
    var results = document.getElementById('dh-admission-results');
    if (submit) {
      submit.disabled = true;
      submit.textContent = path === 'record' ? 'در حال بررسی سوابق…' : 'در حال بررسی رتبه…';
    }
    setStatus(path === 'record'
      ? 'در حال محاسبهٔ معدل مؤثر و مقایسه با برنامه‌های سوابق تحصیلی…'
      : 'در حال محاسبهٔ نتایج دانشگاهی بر اساس رتبه در سهمیه…', false);
    if (results) results.innerHTML = '';

    try {
      var response = await fetch(API_BASE_URL + ADMISSION_PATH, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(buildRequestPayload(recommendations, form, path))
      });

      var payload = null;
      try {
        payload = await response.json();
      } catch (_) {}

      if (!response.ok) {
        var detail = payload && (payload.detail || payload.message);
        throw new Error(typeof detail === 'string'
          ? detail
          : ('خطا در سرویس شانس قبولی: ' + response.status));
      }

      var resultPath = payload && payload.admission_path ? payload.admission_path : path;
      if (results) {
        var majorMap = buildMajorMap(recommendations);
        results.innerHTML =
          '<p class="dh-admission-summary">' +
            'مسیر: <strong>' + escapeHtml(resultPath === 'record' ? 'سوابق تحصیلی' : 'با آزمون') + '</strong> · ' +
            'تعداد نتایج: <strong>' + escapeHtml(payload.count || 0) + '</strong> مورد' +
          '</p>' +
          renderItems(payload.items || [], majorMap, resultPath) +
          '<div class="dh-admission-disclaimer">' +
            escapeHtml(payload.disclaimer || 'نتایج تخمینی و جایگزین دفترچه و اعلام رسمی سنجش نیستند.') +
          '</div>';
      }
      setStatus('✅ نتایج مسیر انتخاب‌شده دریافت شد.', false);
    } catch (error) {
      setStatus('❌ ' + String(error && error.message ? error.message : error), true);
    } finally {
      if (submit) {
        submit.disabled = false;
        submit.textContent = path === 'record'
          ? '📚 بررسی شانس با سوابق تحصیلی'
          : '🎯 بررسی شانس با آزمون';
      }
    }
  }

  function switchTab(path) {
    var examTab = document.getElementById('dh-admission-tab-exam');
    var recordTab = document.getElementById('dh-admission-tab-record');
    var examPanel = document.getElementById('dh-admission-exam-panel');
    var recordPanel = document.getElementById('dh-admission-record-panel');
    if (!examTab || !recordTab || !examPanel || !recordPanel) return;

    var isExam = path === 'exam';
    examTab.classList.toggle('active', isExam);
    recordTab.classList.toggle('active', !isExam);
    examTab.setAttribute('aria-selected', String(isExam));
    recordTab.setAttribute('aria-selected', String(!isExam));
    examPanel.hidden = !isExam;
    recordPanel.hidden = isExam;

    var results = document.getElementById('dh-admission-results');
    if (results) results.innerHTML = '';
    setStatus('', false);

    if (!isExam) updateRecordGpaField();
  }

  function bindWidget(recommendations) {
    var root = document.getElementById(WIDGET_ID);
    if (!root) return;

    root.querySelectorAll('[data-admission-tab]').forEach(function (tab) {
      tab.addEventListener('click', function () {
        switchTab(tab.getAttribute('data-admission-tab'));
      });
    });

    var recordForm = document.getElementById('dh-admission-record-form');
    if (recordForm) {
      recordForm.diploma_type.addEventListener('change', updateRecordGpaField);
      recordForm.addEventListener('submit', function (event) {
        event.preventDefault();
        requestAdmissionChance(recommendations, recordForm, 'record');
      });
    }

    var examForm = document.getElementById('dh-admission-exam-form');
    if (examForm) {
      examForm.addEventListener('submit', function (event) {
        event.preventDefault();
        requestAdmissionChance(recommendations, examForm, 'exam');
      });
    }
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
    var wrapper = document.createElement('div');
    wrapper.innerHTML = widgetHtml();
    var section = wrapper.firstElementChild;
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
    uniqueMajorIds: uniqueMajorIds,
    provinces: PROVINCES.slice()
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
