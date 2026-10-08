import fs from 'fs';

const FILE = 'D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html';
const html = fs.readFileSync(FILE, 'utf8');

// ---- extract script blocks ----
const blocks = [];
const re = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
let m;
while ((m = re.exec(html))) {
  if (m[1].trim()) blocks.push(m[1]);
}
console.log('script blocks:', blocks.length);

function syntaxCheck(code) {
  try { new Function(code); return true; } catch (e) { console.log('SYNTAX ERR:', e.message); return false; }
}
let allOk = true;
blocks.forEach((b, i) => { const ok = syntaxCheck(b); if (!ok) allOk = false; console.log('  block[' + i + '] syntax_ok=' + ok); });
console.log('ALL SYNTAX OK:', allOk);

// ---- DOM stub ----
function mkEl(tag) {
  const cls = new Set();
  const e = {
    tagName: (tag || 'div').toUpperCase(),
    _html: '', style: {}, children: [], dataset: {},
    classList: {
      add() { for (const c of arguments) cls.add(c); },
      remove() { for (const c of arguments) cls.delete(c); },
      toggle(c, f) { const has = cls.has(c); const on = (f === undefined) ? !has : !!f; on ? cls.add(c) : cls.delete(c); return on; },
      contains(c) { return cls.has(c); },
    },
    get innerHTML() { return this._html; },
    set innerHTML(v) { this._html = String(v); },
    get outerHTML() { return this._html; },
    textContent: '', value: '', scrollTop: 0, checked: false, disabled: false,
    contains() { return false; }, focus() {}, blur() {}, click() {}, remove() {},
    querySelector() { return mkEl(); }, querySelectorAll() { return []; },
    getAttribute() { return null; }, setAttribute() {}, removeAttribute() {},
    addEventListener() {}, removeEventListener() {}, dispatchEvent() {},
    appendChild(c) { this.children.push(c); return c; }, removeChild() {}, insertBefore() {},
    closest() { return mkEl(); }, matches() { return false; },
    getBoundingClientRect() { return { top: 0, left: 0, width: 0, height: 0, bottom: 0, right: 0 }; },
    insertAdjacentHTML() {}, replaceChildren() {},
  };
  return e;
}

const idStore = {};
const document = {
  getElementById(id) { return idStore[id] || (idStore[id] = mkEl()); },
  querySelector(sel) { return mkEl(sel); },
  querySelectorAll() { return []; },
  createElement(t) { return mkEl(t); },
  createDocumentFragment() { return mkEl(); },
  addEventListener() {}, removeEventListener() {},
  body: mkEl('body'), documentElement: mkEl('html'), head: mkEl('head'),
  write() {}, execCommand() { return true; },
};

const store = {};
const localStorage = {
  getItem(k) { return store[k] === undefined ? null : store[k]; },
  setItem(k, v) { store[k] = String(v); },
  removeItem(k) { delete store[k]; },
  clear() { for (const k in store) delete store[k]; },
};

const window = {
  addEventListener() {}, removeEventListener() {}, matchMedia: () => ({ matches: false, addListener() {} }),
  localStorage, location: { href: 'http://localhost/', hash: '', reload() {} },
  scrollTo() {}, open() {}, print() {}, getComputedStyle: () => ({}),
  document,
};
const navigator = { userAgent: 'node', clipboard: { writeText() {} } };
const location = window.location;
const alert = () => {}; const confirm = () => true; const prompt = () => '';
const getComputedStyle = () => ({});

// ---- assemble + probe ----
const body = blocks.join('\n;\n');

const probe = `
;return (function(){
  var out = { pages:[], errors:[], aliases:[] };
  var keys = Object.keys(PAGES);
  out.pageCount = keys.length;
  keys.forEach(function(k){
    // 只验证"可导航页面"（存在 MODS 定义）。别名键（如 bi0Standard）经 go()->imsPageNorm 归一后
    // 不会作为独立 page 渲染，此处单列出来，避免误判。
    if (!MODS[k]) { out.aliases.push(k); return; }
    try {
      state.page = k;
      var s = PAGES[k]();
      if (typeof s !== 'string') out.errors.push(k + ' : page fn did not return string (' + typeof s + ')');
    } catch(e){ out.errors.push(k + ' : ' + e.message); }
  });
  return out;
})();
`;

const fn = new Function(
  'document', 'window', 'localStorage', 'navigator', 'location', 'alert', 'confirm', 'prompt', 'getComputedStyle',
  body + probe
);

let results;
try {
  results = fn(document, window, localStorage, navigator, location, alert, confirm, prompt, getComputedStyle);
} catch (e) {
  console.log('BOOT ERROR:', e.message);
  console.log(e.stack.split('\n').slice(0, 6).join('\n'));
  process.exit(2);
}

console.log('PAGES count:', results.pageCount);
console.log('non-navigable alias keys:', results.aliases.join(', ') || '(none)');
console.log('page render errors:', results.errors.length);
results.errors.forEach(e => console.log('  - ' + e));
if (results.errors.length === 0) console.log('ALL PAGES RENDER OK');