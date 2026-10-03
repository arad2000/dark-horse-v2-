const fs = require('fs');
const assert = require('assert');

const source = fs.readFileSync('docs/admission_chance_ui.js', 'utf8');
const css = fs.readFileSync('docs/admission_chance_ui.css', 'utf8');
const indexSource = fs.readFileSync('docs/index.html', 'utf8');

assert.ok(source.includes('/api/v1/admission/chance'));
assert.match(source, /state\.majorsResult/);
assert.match(source, /major_ids/);
assert.match(source, /admission_path:\s*'exam'/);
assert.match(source, /admission_path:\s*'record'/);

/* Exam + capacity contract: group, major, province, period only. */
assert.match(source, /data-path="exam"/);
assert.match(source, /id="dh-admission-exam-source" name="source" required/);
assert.match(source, /option value="capacity">ظرفیت دفترچه/);
assert.match(source, /option value="program">مقایسه با آخرین رتبه/);
assert.match(source, /id="dh-admission-exam-group" name="group" required/);
assert.match(source, /id="dh-admission-exam-major" name="major_id" required/);
assert.match(source, /id="dh-admission-exam-province" name="school_province_3y" required/);
assert.match(source, /id="dh-admission-exam-period" name="period" required/);
for (const group of ['riazi', 'tajrobi', 'ensani', 'honar', 'zaban']) {
  assert.match(source, new RegExp("value: '" + group + "'"));
}
assert.match(source, /source:\s*'capacity'/);
assert.match(source, /group:\s*EXAM_GROUP_LABELS\[values\.group\]\s*\?\s*values\.group\s*:\s*'riazi'/);
assert.match(source, /periods:\s*values\.period\s*\?\s*\[values\.period\]\s*:\s*\[\]/);
assert.match(source, /include_unknown:\s*false/);

/* Capacity mode keeps rank/region inactive; comparison mode enables rank/region. */
assert.match(source, /class="dh-admission-field dh-admission-exam-program-only" hidden/);
assert.match(source, /form\.rank_in_quota\.disabled = !isProgram/);
assert.match(source, /form\.region_zone\.disabled = !isProgram/);
assert.match(source, /form\.group\.disabled = isProgram/);
assert.match(source, /form\.period\.disabled = isProgram/);

const examProgramPayloadBlock = source.slice(
  source.indexOf("    if (values.source === 'program')"),
  source.indexOf("    return {", source.indexOf("    if (values.source === 'program')"))
);
assert.match(examProgramPayloadBlock, /source:\s*'program'/);
assert.match(examProgramPayloadBlock, /major_ids:/);
assert.match(examProgramPayloadBlock, /rank_in_quota:/);
assert.match(examProgramPayloadBlock, /region_zone:/);
assert.match(examProgramPayloadBlock, /province:/);
assert.doesNotMatch(examProgramPayloadBlock, /group:/);
assert.doesNotMatch(examProgramPayloadBlock, /periods:/);

const examCapacityPayloadBlock = source.slice(
  source.indexOf("    return {\n      admission_path: 'exam',\n      source: 'capacity'"),
  source.indexOf("    };", source.indexOf("    return {\n      admission_path: 'exam',\n      source: 'capacity'")) + 5
);
assert.match(examCapacityPayloadBlock, /source:\s*'capacity'/);
assert.match(examCapacityPayloadBlock, /group:/);
assert.match(examCapacityPayloadBlock, /major_ids:/);
assert.match(examCapacityPayloadBlock, /province:/);
assert.match(examCapacityPayloadBlock, /periods:/);
assert.match(examCapacityPayloadBlock, /include_unknown:\s*false/);
assert.doesNotMatch(examCapacityPayloadBlock, /rank_in_quota/);
assert.doesNotMatch(examCapacityPayloadBlock, /region_zone/);

/* Existing record path contract remains intact. */
assert.match(source, /diploma_type/);
assert.match(source, /gpa_written/);
assert.match(source, /gpa_total/);
assert.match(source, /target_field_group/);
assert.match(source, /region_zone:\s*values\.region_zone/);
assert.match(source, /special_quota:\s*values\.special_quota/);
assert.match(source, /dh-admission-record-region/);
assert.match(source, /dh-admission-record-special-quota/);

/* Shared province / admission copy and capacity result fields remain covered. */
assert.match(source, /PROVINCES/);
assert.match(source, /school_province_3y/);
assert.match(source, /استان محل تحصیل سه سال آخر/);
assert.match(source, /آذربایجان شرقی/);
assert.match(source, /یزد/);
assert.match(source, /isargaran_25/);
assert.match(source, /isargaran_5/);
assert.match(source, /shahid/);
assert.match(source, /DHAdmissionChanceUI/);
assert.match(source, /sanjesh_code/);
assert.match(source, /ظرفیت کل:/);
assert.match(source, /کد رشته‌محل:/);
assert.match(source, /برای ترکیب گروه آزمایشی، رشته، استان و دوره انتخاب‌شده/);
assert.match(source, /این پیام به معنی رد شدن داوطلب نیست/);
assert.match(source, /نتایج تخمینی/);
assert.match(source, /renderRankComparisonItems/);
assert.match(source, /status_label/);
assert.match(source, /cutoff_reference/);
assert.match(source, /above|near|below|unknown/);
assert.match(source, /این مقایسه فقط با دادهٔ cutoff تاریخی موجود انجام شده/);
assert.match(source, /جایگزین دفترچه و اعلام رسمی سنجش نیست/);

assert.doesNotMatch(source, /quota_type/);
assert.doesNotMatch(source, /darkhorse\/discover/);
assert.doesNotMatch(source, /individuality_fit\s*=|individuality_fit\s*=/);

assert.match(css, /\.dh-admission-chance-widget/);
assert.match(css, /\.dh-admission-card/);
assert.match(css, /\.dh-admission-help/);
assert.match(css, /\.dh-admission-tabs/);
assert.match(css, /\.dh-admission-tab/);
assert.match(css, /\.dh-admission-field select:disabled/);
assert.match(css, /@media/);

assert.match(indexSource, /admission_chance_ui\.css\?v=3/);
assert.match(indexSource, /admission_chance_ui\.js\?v=9/);

console.log('admission_chance_ui phase3 regression: PASS');
