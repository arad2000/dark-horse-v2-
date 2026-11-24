'use strict';
const fs = require('fs');
const assert = require('assert');
const crypto = require('crypto');
const app = fs.readFileSync('docs/app.js', 'utf8');
const hints = [
  "لازم نیست اصطلاحات تخصصی را بدانی یا الان این کارها را بلد باشی. نمونه‌ها را بخوان و تصور کن خودت داری انجامشان می‌دهی. اینجا هنوز رشته‌ات را انتخاب نمی‌کنی.</p>\n        <p class=\"dh-stage-hint\">اگر بعضی از کارهای یک گروه برایت جذاب است، می‌توانی آن را انتخاب کنی؛ لازم نیست همهٔ آن‌ها را دوست داشته باشی.</p>\n        <p class=\"dh-stage-hint\">۱ تا ${dhFaNum(maxSelect)} محله را برای بررسی بیشتر انتخاب کن.",
  "گذرها بر اساس محله دسته‌بندی شده‌اند. توضیح هر گروه را بخوان و کارهایی را که برایت جذاب‌اند تصور کن.</p>\n      <p class=\"dh-stage-hint\">اگر بعضی از کارهای یک گروه برایت جذاب است، می‌توانی آن را انتخاب کنی؛ لازم نیست همهٔ آن‌ها را دوست داشته باشی.",
  "لازم نیست الان این کارها را بلد باشی. نمونه‌ها را بخوان و تصور کن خودت داری انجامشان می‌دهی.</p>\n      <p class=\"dh-stage-hint\">اگر بعضی از کارهای یک گروه برایت جذاب است، می‌توانی آن را انتخاب کنی؛ لازم نیست همهٔ آن‌ها را دوست داشته باشی."
];
let normalized = app;
hints.forEach((hint, i) => {
  assert.equal(app.split(hint).length - 1, 1, 'Each approved stage hint appears once');
  normalized = normalized.replace(hint, 'COMMON_HINT_' + i);
});
// Full app fingerprint excludes ONLY the three authorized guidance blocks.
// Baseline includes separately tested, authorized S/V result integration.
// Locks the surrounding application and the unchanged shared guidance.
assert.equal(crypto.createHash('sha256').update(normalized).digest('hex'), '44aff14078ec6b08c977912e15199888ef6f7d157c37e32179c7168f7d53ba9c');
assert(fs.readFileSync('docs/index.html', 'utf8').includes('&r=281&next-step='));
console.log('PASS: approved common guidance; every other byte of app.js unchanged');
