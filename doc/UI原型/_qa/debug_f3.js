// debug_f3.js — 聚焦调试 F3（解冻提交→danger 确认窗）失败原因
const fs = require('fs');
const vm = require('vm');
const HTML = fs.readFileSync(String.raw`D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html`, 'utf-8');

let DYN_ref = null;
function registerIds(html, reg) {
  if (typeof html !== 'string') return;
  const tagRe = /<(input|select|textarea|div|span|button|label)\b([^>]*)>/g;
  let m;
  while ((m = tagRe.exec(html))) {
    const attrs = m[2];
    const idM = /id="([^"]+)"/.exec(attrs);
    if (!idM) continue;
    const id = idM[1];
    if (reg[id]) continue;
    const el = new MiniEl(m[1]);
    el.id = id;
    const valM = /value="([^"]*)"/.exec(attrs);
    if (valM) el.value = valM[1];
    const typeM = /type="([^"]+)"/.exec(attrs);
    if (typeM) el.type = typeM[1];
    if (m[1] === 'textarea' || m[1] === 'span') {
      const close = html.indexOf('</' + m[1] + '>', m.index);
      if (close > m.index) el.textContent = html.slice(m.index + m[0].length, close).trim();
      if (m[1] === 'textarea') el.value = el.textContent;
    }
    if (m[1] === 'select') {
      const close = html.indexOf('</select>', m.index);
      const seg = html.slice(m.index, close > 0 ? close : m.index + 800);
      const opts = [...seg.matchAll(/<option([^>]*)>([^<]*)<\/option>/g)].map(o => ({ sel: /selected/.test(o[1]), t: o[2] }));
      el._options = opts;
      if (opts.length) {
        const s = opts.find(o => o.sel) || opts[0];
        el.value = s.t; el.selectedIndex = opts.indexOf(s);
      } else { el.value = ''; el.selectedIndex = 0; }
    }
    reg[id] = el;
  }
}
class MiniEl {
  constructor(tag) {
    this.tagName = tag; this._html = ''; this.textContent = ''; this._className = ''; this.children = [];
    this.disabled = false; this.value = ''; this.type = ''; this.style = {}; this._tm = null; this._raw = null;
    this.parentNode = null; this.id = ''; this.selectedIndex = 0; this._options = [];
    const set = new Set(); const self = this;
    this.classList = { add(...c) { c.forEach(x => set.add(x)); }, remove(...c) { c.forEach(x => set.delete(x)); }, toggle(c) { set.has(c) ? set.delete(c) : set.add(c); }, contains: c => set.has(c) };
    Object.defineProperty(this, 'className', { get() { return self._className; }, set(v) { self._className = String(v); set.clear(); String(v).split(/\s+/).filter(Boolean).forEach(x => set.add(x)); } });
  }
  set innerHTML(v) { this._html = String(v); if (DYN_ref) registerIds(this._html, DYN_ref); }
  get innerHTML() { return this._html; }
  appendChild(c) { c.parentNode = this; this.children.push(c); if (c.id && DYN_ref) DYN_ref[c.id] = c; return c; }
  remove() {
    if (this.parentNode) { const i = this.parentNode.children.indexOf(this); if (i >= 0) this.parentNode.children.splice(i, 1); this.parentNode = null; }
    if (this.id && DYN_ref && DYN_ref[this.id] === this) delete DYN_ref[this.id];
    if (BODY.children.includes(this)) BODY.children.splice(BODY.children.indexOf(this), 1);
  }
  contains() { return false; } closest() { return null; } querySelectorAll() { return []; } focus() {}
}
const REG = {};
['sidebar','topbar','content','drawer','dr-title','dr-body','dr-foot','mask','msgdrawer','mglist','rolemenu','toasts','gsearch'].forEach(id => REG[id] = new MiniEl('div'));
const DYN = {}; DYN_ref = DYN;
const BODY = new MiniEl('body');
const handlers = { click: [], keydown: [] };
const timers = [];
function mySetTimeout(fn, ms) { timers.push({ fn, ms: ms || 0 }); return timers.length; }
const stubDocument = {
  querySelector: s => {
    if (s[0] === '#' && s.indexOf(' ') < 0) { const id = s.slice(1); if (id in REG) return REG[id]; if (id in DYN) return DYN[id]; return null; }
    return null;
  },
  createElement: t => new MiniEl(t),
  addEventListener: (ev, fn) => { (handlers[ev] || (handlers[ev] = [])).push(fn); },
  getElementById: id => (id in REG) ? REG[id] : (DYN[id] || null),
  querySelectorAll: () => [],
  body: BODY
};
const scripts = [...HTML.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const DRIVER = `
;(function () {
  setRole('R1');
  go('acct');
  const fi = ACCTS.findIndex(function (a) { return a.frozen && a.st === '冻结'; });
  console.log('fi =', fi, 'id =', ACCTS[fi].id);
  acctUnfreeze(fi);
  console.log('drTitle =', REG['dr-title'].textContent);
  const reasonEl = document.getElementById('F_reason');
  console.log('F_reason el =', reasonEl ? 'EXISTS value=[' + reasonEl.value + ']' : 'NULL');
  try {
    acctUnfreezeSubmit(fi);
    console.log('acctUnfreezeSubmit returned OK');
  } catch (e) { console.log('SUBMIT EXCEPTION:', e.message); }
  const cw = DYN['cfwrap'];
  console.log('cfwrap =', cw ? 'EXISTS' : 'NULL');
  if (cw) {
    console.log('cfwrap html len =', cw._html.length);
    console.log('has btn-red =', /btn-red/.test(cw._html));
    console.log('has cf-warn =', /cf-warn/.test(cw._html));
    console.log('cfwrap html head =', cw._html.slice(0, 300));
  }
  // 对照：直接手动调 confirmDlg danger
  confirmDlg('危险测试', 'x', '删', function(){}, { danger: true, warn: '警告文案' });
  const cw2 = DYN['cfwrap'];
  console.log('manual cfwrap btn-red =', cw2 ? /btn-red/.test(cw2._html) : 'null', 'cf-warn =', cw2 ? /cf-warn/.test(cw2._html) : 'null');
})();
`;
const code = scripts.join('\n;\n') + '\n;\n' + DRIVER;
const sandbox = {
  console, process, globalThis: {},
  document: stubDocument, window: null,
  REG, DYN, HANDLERS: handlers, FULLHTML: HTML, BODY, fireTimers: () => 0, timers, QB: { elements: [], querySelectorAll: () => [] }, qInput: () => ({}), qSelect: () => ({}),
  setTimeout: mySetTimeout, clearTimeout: () => {},
  Math, Date, Number, String, Array, Object, JSON, Set, RegExp, Error, Map
};
sandbox.window = sandbox; sandbox.globalThis = sandbox;
try { vm.runInNewContext(code, sandbox, { filename: 'debug-f3.js' }); }
catch (e) { console.log('RUNTIME_ERROR = ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 10).join('\n')); }
