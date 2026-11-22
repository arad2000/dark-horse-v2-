'use strict';
// Browsing only: no entitlement, selection, persistence or scoring behavior.
let copy;
const content = document.getElementById('content');
const nav = document.getElementById('nav');
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(text, action, secondary) {
  const node = element('button', text, secondary ? 'secondary' : '');
  node.type = 'button'; node.addEventListener('click', action); return node;
}
function heading(text) {
  const node = element('h1', text); node.tabIndex = -1; content.append(node);
  node.focus(); window.scrollTo(0, 0);
}
function clear(back) {
  content.replaceChildren(); nav.replaceChildren();
  if (back) nav.append(button('بازگشت به محلهٔ کاوش و شناخت', home, true));
}
function card(item, meta) {
  const node = element('article', '', 'card');
  node.append(element('p', meta, 'meta'), element('h2', item.title));
  if (item.description) node.append(element('p', item.description));
  if (item.examples) {
    const list = element('ul');
    item.examples.forEach(text => list.append(element('li', text)));
    node.append(list);
  }
  return node;
}
function auditInfo(item, node) {
  const detail = element('details'); detail.append(element('summary', 'اطلاعات تطبیق متن — برای بازبین'));
  detail.append(element('code', item.id + ' | ' + item.majorCodes.join(' ')));
  node.append(detail);
}
function home() {
  clear(false); heading(copy.title); content.append(element('p', copy.description));
  content.append(element('p', 'اگر بعضی از کارهای یک گروه برایت جذاب است، می‌توانی آن را انتخاب کنی. در مرحلهٔ بعد، مسیرها را جداگانه می‌بینی.'));
  content.append(element('p', 'در این نمونه دکمه‌ها فقط متن مسیرها را باز می‌کنند؛ انتخاب واقعی ثبت نمی‌شود.', 'notice'));
  copy.groups.forEach((group, i) => {
    const node = card(group, 'گذر ' + (i + 1).toLocaleString('fa-IR') + ' از ' + copy.groups.length.toLocaleString('fa-IR'));
    node.append(button('دیدن مسیرهای این گذر', () => groupPage(i)));
    auditInfo(group, node); content.append(node);
  });
}
function groupPage(index) {
  const group = copy.groups[index]; clear(true); heading(group.title);
  content.append(element('p', group.description));
  content.append(element('p', 'لازم نیست اصطلاحات تخصصی را بدانی یا الان این کارها را بلد باشی. نمونه‌ها را بخوان و تصور کن خودت داری انجامشان می‌دهی.', 'notice'));
  group.paths.forEach((path, i) => {
    const node = card(path, 'مسیر ' + (i + 1).toLocaleString('fa-IR') + ' از ' + group.paths.length.toLocaleString('fa-IR'));
    auditInfo(path, node); content.append(node);
  });
  const actions = element('div', '', 'actions');
  if (index > 0) actions.append(button('گذر قبلی', () => groupPage(index - 1), true));
  if (index < copy.groups.length - 1) actions.append(button('گذر بعدی', () => groupPage(index + 1)));
  actions.append(button('بازگشت به محله', home, true)); content.append(actions);
}
fetch('./copy.json').then(response => {
  if (!response.ok) throw new Error('copy unavailable'); return response.json();
}).then(data => { copy = data; home(); }).catch(() => {
  content.replaceChildren(element('p', 'متن‌ها باز نشدند. صفحه را دوباره بارگذاری کنید.'));
});
