/* Admission record G3 metadata renderer.
 * Only renders data already returned by the admission API.
 * No admission scoring, percentage, ranking, or calibration is performed here.
 */
(function (global) {
  'use strict';

  function text(value) {
    return String(value == null ? '' : value);
  }

  function escapeHtml(value) {
    return text(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatCoefficient(value) {
    var n = Number(value);
    if (!Number.isFinite(n)) return '';
    return Number.isInteger(n) ? String(n) : n.toFixed(1);
  }

  global.renderRecordGpaMeta = function renderRecordGpaMeta(item) {
    item = item || {};
    if (item.gpa_coefficient == null) return '';
    var coefficient = formatCoefficient(item.gpa_coefficient);
    var html =
      '<div class="dh-record-gpa-meta" dir="rtl">' +
      '<span class="dh-record-gpa-label">ضریب معدل</span>' +
      '<strong class="dh-record-gpa-value">' + escapeHtml(coefficient) + '</strong>';
    if (item.gpa_effective != null) {
      html +=
        '<span class="dh-record-gpa-effective">معدل مؤثر: ' +
        escapeHtml(formatCoefficient(item.gpa_effective)) +
        '</span>';
    }
    return html + '</div>';
  };

  global.recordGpaMetaCss =
    '.dh-record-gpa-meta{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-top:8px;padding:8px 10px;border-radius:10px;background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.22);font-size:.84rem}' +
    '.dh-record-gpa-label{opacity:.82}' +
    '.dh-record-gpa-value{font-size:1rem}' +
    '.dh-record-gpa-effective{opacity:.76;font-size:.78rem}';

  if (document && document.head && !document.getElementById('dh-record-g3-gpa-style')) {
    var style = document.createElement('style');
    style.id = 'dh-record-g3-gpa-style';
    style.textContent = global.recordGpaMetaCss;
    document.head.appendChild(style);
  }
})(window);
