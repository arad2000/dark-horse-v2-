const fs = require('fs');
const assert = require('assert');

const source = fs.readFileSync('docs/admission_chance_ui.js', 'utf8');
const css = fs.readFileSync('docs/admission_chance_ui.css', 'utf8');
const shellCss = fs.readFileSync('docs/shell.css', 'utf8');
const indexSource = fs.readFileSync('docs/index.html', 'utf8');
const shellSource = fs.readFileSync('docs/shell.js', 'utf8');
const catalog = JSON.parse(fs.readFileSync('docs/majors_catalog_ui_v1.json', 'utf8'));

assert.ok(source.includes('/api/v1/admission/chance'));
assert.match(source, /state\.majorsResult/);
assert.match(source, /majors_catalog_ui_v1\.json\?v=7/);
assert.match(source, /function openHome\(mountId\)/);
assert.match(shellSource, /انتخاب رشته با منطق سنجش/);
assert.strictEqual(catalog.majors.length, 230);
assert.ok(Math.max(...catalog.majors.map(item => item.id)) >= 230);
assert.deepStrictEqual(catalog.majors.map(item => item.id), Array.from({length: 230}, (_, i) => i + 1));
const archaeology = catalog.majors.find(item => item.id === 166);
assert.ok(archaeology, 'major id 166 must exist');
assert.strictEqual(archaeology.name, 'باستان‌شناسی');
assert.strictEqual(archaeology.group, 'علوم انسانی');
assert.strictEqual(catalog.source_ref, 'deploy/liara-commercial-sandbox');
assert.strictEqual(catalog.source_sha, 'a487335cfd79b290e015f071f46f62b24484a2c7');
assert.match(source, /major_ids/);
assert.match(source, /admission_path:\s*'exam'/);
assert.match(source, /admission_path:\s*'record'/);

/* Exam + capacity contract: group, province, period; no mandatory major. */
assert.match(source, /data-path="exam"/);
assert.match(source, /id="dh-admission-exam-source" name="source" required/);
assert.match(source, /option value="capacity">ظرفیت دفترچه/);
assert.match(source, /option value="program">مقایسه با آخرین رتبه/);
assert.match(source, /id="dh-admission-exam-group" name="group" required/);
assert.match(source, /id="dh-admission-exam-major" name="major_id"/);
assert.match(source, /dh-admission-exam-major-only" hidden/);
assert.match(source, /form\.major_id\.required = isProgram/);
assert.match(source, /id="dh-admission-exam-province" name="school_province_3y" required/);
assert.match(source, /id="dh-admission-exam-period" name="period" required/);
assert.match(source, /id="dh-admission-exam-source-help" class="dh-admission-help"/);
assert.match(source, /در ظرفیت دفترچه، همه رشته‌های گروه انتخاب‌شده بر اساس استان و دوره از دفترچه ۱۴۰۵ فهرست می‌شوند/);
assert.match(source, /برای مقایسه آخرین رتبه تاریخی، انتخاب رشته الزامی است/);
assert.match(source, /برای مقایسه cutoff تاریخی، انتخاب رشته، رتبه در سهمیه و منطقه لازم‌اند/);
assert.match(source, /این خروجی درصد شانس نیست/);
assert.match(source, /id="dh-admission-exam-special-quota" name="special_quota"/);
assert.match(source, /optionsHtml\(SPECIAL_QUOTA_OPTIONS\)/);
assert.match(source, /form\.special_quota\.disabled = !isProgram/);
assert.match(source, /special_quota:\s*values\.special_quota/);
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

const programStart = source.indexOf("    if (values.source === 'program')");
const programEnd = source.indexOf("\n    }\n\n    return {", programStart);
const examProgramPayloadBlock = source.slice(programStart, programEnd);
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
assert.match(examCapacityPayloadBlock, /major_ids:\s*\[\]/);
assert.match(examCapacityPayloadBlock, /limit:\s*100/);
assert.match(examCapacityPayloadBlock, /province:/);
assert.match(examCapacityPayloadBlock, /periods:/);
assert.match(examCapacityPayloadBlock, /include_unknown:\s*false/);
assert.doesNotMatch(examCapacityPayloadBlock, /rank_in_quota/);
assert.doesNotMatch(examCapacityPayloadBlock, /region_zone/);
assert.doesNotMatch(examCapacityPayloadBlock, /special_quota/);

/* Record + capacity defaults to direct 1405 rows; program2s is explicit opt-in. */
assert.ok(source.includes('id="dh-admission-record-source" name="source" required'));
assert.ok(source.includes('<option value="capacity" selected>ظرفیت دفترچه ۱۴۰۵ / صرفاً سوابق</option>'));
assert.ok(source.includes('<option value="program">مقایسه با حداقل معدل برنامه (program2s)</option>'));
assert.ok(source.includes("source: values.source === 'program' ? 'program' : 'capacity'"));
assert.ok(source.includes('payload.group = values.group;'));
assert.ok(source.includes('payload.periods = values.period ? [values.period] : [];'));
assert.ok(source.includes('دوره پذیرش از دفترچه ۱۴۰۵ را انتخاب کن'));
assert.ok(source.includes('sourceNotesHtml'));

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
assert.match(source, /برای ترکیب گروه آزمایشی، استان و دوره انتخاب‌شده/);
assert.match(source, /دفترچه ۱۴۰۵/);
assert.doesNotMatch(source, /دفترچه ۱۴۰۴|دفترچه 1404/);
assert.match(source, /API این مسیر بدون major_ids را پشتیبانی نمی‌کند/);
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

assert.match(indexSource, /shell\.css\?v=67/);
assert.match(indexSource, /shell\.js\?v=/);
assert.match(indexSource, /admission_chance_ui\.css\?v=5/);
assert.match(indexSource, /admission_chance_ui\.js\?v=20/);
assert.match(css, /\.dh-admission-source-limitation/);
assert.ok(shellCss.includes('.dh-mk2-hero-sub {\n  color: #F0C040 !important;\n  font-weight: 800 !important;\n}'));

console.log('admission_chance_ui phase3 regression: PASS');

assert.strictEqual(catalog.majors.find(item => item.id === 170).name, 'هنر اسلامی');
assert.strictEqual(catalog.majors.find(item => item.id === 185).name, 'نمایش عروسکی');
assert.strictEqual(catalog.majors.find(item => item.id === 189).name, 'چاپ');
assert.deepStrictEqual(catalog.majors.slice(-36).map(item => [item.id, item.name]), [
  [195, 'مهندسی حرفه‌ای کامپیوتر'],
  [196, 'علم اطلاعات و دانش‌شناسی'],
  [197, 'مهندسی حرفه‌ای معماری'],
  [198, 'مهندسی ساخت و تولید'],
  [199, 'مهندسی هوانوردی و مراقبت پرواز'],
  [200, 'فناوری اطلاعات و ارتباطات'],
  [201, 'خلبانی بالگرد'],
  [202, 'خلبانی پهپاد'],
  [203, 'هوانوردی خلبانی'],
  [204, 'مهندسی نگهداری و تعمیر بالگرد'],
  [205, 'زبان روسی'],
  [206, 'سیاستگذاری اجتماعی'],
  [207, 'فقه شافعی'],
  [208, 'علوم قضایی'],
  [209, 'زبان و ادبیات آلمانی'],
  [210, 'زبان و ادبیات اسپانیایی'],
  [211, 'زبان و ادبیات ترکی استانبولی'],
  [212, 'زبان و ادبیات ایتالیایی'],
  [213, 'زبان و ادبیات ژاپنی'],
  [214, 'زبان و ادبیات کردی'],
  [215, 'کارشناسی ارشد پیوسته علوم قضایی'],
  [216, 'مهندسی تولید و ژنتیک گیاهی'],
  [217, 'مهندسی طبیعت'],
  [218, 'علوم و مهندسی جنگل'],
  [219, 'مهندسی فضای سبز'],
  [220, 'مهندسی مکانیزاسیون کشاورزی'],
  [221, 'زیست‌شناسی دریا'],
  [222, 'مهندسی گیاه‌پزشکی'],
  [223, 'کاردانی معماری'],
  [224, 'کاردانی امور بانکی'],
  [225, 'کاردانی امور مالی و مالیاتی'],
  [226, 'کاردانی برق — قدرت'],
  [227, 'کاردانی بیمه'],
  [228, 'کاردانی کارهای عمومی ساختمان'],
  [229, 'کاردانی ارتباطات و فناوری اطلاعات'],
  [230, 'کاردانی نقشه‌برداری — ژئودزی']
]);
assert.strictEqual(new Set(catalog.majors.map(item => item.name.trim())).size, catalog.majors.length);
