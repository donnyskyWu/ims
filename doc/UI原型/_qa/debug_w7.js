// 调试 W7
const fs = require('fs'), vm = require('vm');
const HTML = fs.readFileSync(String.raw`D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html`, 'utf-8');
class E {
  constructor() { this._html = ''; this.textContent = ''; this.children = []; this.style = {}; const s = new Set();
    this.classList = { add: c => s.add(c), remove: c => s.delete(c), toggle: c => s.has(c) ? s.delete(c) : s.add(c), contains: c => s.has(c) }; }
  set innerHTML(v) { this._html = String(v); } get innerHTML() { return this._html; }
  appendChild(c) { this.children.push(c); return c; } remove() {} contains() { return false; } closest() { return null; }
  querySelectorAll() { return []; } get scrollTop() { return 0; } set scrollTop(v) {} focus() {}
}
const REG = {};
['sidebar','topbar','content','drawer','dr-title','dr-body','dr-foot','mask','msgdrawer','mglist','rolemenu','toasts'].forEach(i => REG[i] = new E());
const H = { keydown: [] };
const doc = { querySelector: s => s[0] === '#' ? (REG[s.slice(1)] || null) : null, createElement: t => new E(), addEventListener: (e, f) => { (H[e] || (H[e] = [])).push(f); }, getElementById: i => REG[i] || null };
const scripts = [...HTML.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const sb = { console, process: { exit: () => {} }, document: doc, event: { stopPropagation() {}, key: '', metaKey: false, ctrlKey: false, preventDefault() {} }, REG, setTimeout: () => 0 };
sb.window = sb; sb.globalThis = sb;
const tail = `
;setTab('workbench','告警');
const c = REG.content._html;
console.log('has 0087:', c.indexOf('ACCT-2026-0087') >= 0);
console.log('idx 账号领用申请:', c.indexOf('账号领用申请'));
console.log('mg-i count:', (c.match(/class="mg-i/g) || []).length);
const i = c.indexOf('账号领用申请');
if (i >= 0) console.log('context:', c.slice(Math.max(0, i - 260), i + 60).replace(/\\n/g, ' '));
console.log('tabs on:', (c.match(/class="tab on"[^>]*>([^<]+)/g) || []).join(' | '));
`;
vm.runInNewContext(scripts.join('\n;\n') + tail, sb);
