// QA 动态测试 v2：最小 DOM 桩 + 单一 vm.Script 执行页面全部 JS
const fs = require('fs');
const vm = require('vm');
const HTML = fs.readFileSync(String.raw`D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html`, 'utf-8');

/* ---------- 最小 DOM 桩 ---------- */
class MiniEl {
  constructor(tag) { this.tagName = tag; this._html = ''; this.textContent = ''; this.className = ''; this.children = []; this.disabled = false; this.value = '';
    const set = new Set();
    this.classList = {
      add: (...c) => c.forEach(x => set.add(x)),
      remove: (...c) => c.forEach(x => set.delete(x)),
      toggle: c => set.has(c) ? set.delete(c) : set.add(c),
      contains: c => set.has(c)
    };
    this.style = {};
    this._classes = set;
  }
  set innerHTML(v) { this._html = String(v); }
  get innerHTML() { return this._html; }
  appendChild(c) { c.parentNode = this; this.children.push(c); this._html += (c._html || ''); return c; }
  remove() { if (this.parentNode) { const i = this.parentNode.children.indexOf(this); if (i >= 0) this.parentNode.children.splice(i, 1); } }
  contains() { return false; }
  closest() { return null; }
  querySelectorAll() { return []; }
  get scrollTop() { return 0; } set scrollTop(v) {}
  focus() {}
}
const REG = {};
['sidebar','topbar','content','drawer','dr-title','dr-body','dr-foot','mask','msgdrawer','mglist','rolemenu','toasts',
 'certView','cvInner','cvMask','cvWm','certLvTag','gsearch'].forEach(id => REG[id] = new MiniEl('div'));
const handlers = { click: [], keydown: [] };
const stubDocument = {
  querySelector: s => { if (s[0] === '#') return REG[s.slice(1)] || null; return null; },
  createElement: t => new MiniEl(t),
  addEventListener: (ev, fn) => { (handlers[ev] || (handlers[ev] = [])).push(fn); },
  getElementById: id => REG[id] || null
};

/* ---------- 页面脚本提取 ---------- */
const scripts = [...HTML.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

/* ---------- 驱动（与页面脚本同作用域，可访问 const state/ROLES 等） ---------- */
const DRIVER = `
;(function () {
  const R = [], F = [];
  function assert(name, cond, detail) { (cond ? R : F).push(name + (detail ? ' | ' + detail : '')); }
  function toastTexts() { return REG.toasts.children.map(c => (c._html || '').replace(/<[^>]+>/g, '')); }
  function toastCount() { return REG.toasts.children.length; }
  function lastToast() { const t = toastTexts(); return t[t.length - 1] || ''; }
  function navCount() { return (REG.sidebar._html.match(/class="nav-item/g) || []).length; }
  function content() { return REG.content._html; }

  /* ===== 验收2：18 模块路由逐一渲染 ===== */
  MODORDER.forEach(function (id) {
    try {
      go(id);
      const marker = id === 'workbench' ? '待办中心' : MODS[id].page;
      const ok = state.page === id && content().length > 500 && content().indexOf(marker) >= 0;
      assert('N1 路由渲染 ' + id + '(' + MODS[id].code + ')', ok, 'len=' + content().length);
    } catch (e) { assert('N1 路由渲染 ' + id, false, 'EXCEPTION ' + e.message); }
  });
  assert('N2 R1 侧边栏 18 项', navCount() === 18, 'count=' + navCount());
  assert('N3 侧边栏分组标题存在', REG.sidebar._html.indexOf('V1 基础管理') >= 0 && REG.sidebar._html.indexOf('V2 运营流程') >= 0 && REG.sidebar._html.indexOf('V3 数据智能') >= 0);

  /* ===== 验收3：工作台 ===== */
  go('workbench');
  const wb = content();
  const greetOK = (wb.indexOf('凌晨好') >= 0 || wb.indexOf('上午好') >= 0 || wb.indexOf('下午好') >= 0 || wb.indexOf('晚上好') >= 0) && wb.indexOf(ROLES[state.role].user) >= 0;
  assert('W1 问候区', greetOK);
  assert('W2 4 数据卡', (wb.match(/class="card hov stat"/g) || []).length === 4, 'n=' + (wb.match(/class="card hov stat"/g) || []).length);
  ['全部','审批','归还','审核','预警','告警'].forEach(t => assert('W3 待办Tab ' + t, wb.indexOf('>' + t + '</div>') >= 0));
  assert('W4 快捷入口 10 项', (wb.match(/class="card hov" style="padding:13px/g) || []).length === 10);
  assert('W5 待办 8 条', wb.indexOf('8 条待处理') >= 0);
  setTab('workbench', '审批');
  const c1 = content();
  assert('W6 Tab过滤：审批保留', c1.indexOf('账号领用申请') >= 0 && c1.indexOf('证件到期预警') < 0);
  setTab('workbench', '告警');
  const w7 = content();
  assert('W7 Tab过滤：仅告警待办', (w7.match(/class="mg-i"/g) || []).length === 1 && w7.indexOf('ACCT-2026-0087') >= 0);
  const t0 = toastCount();
  openMsg();
  assert('M1 消息抽屉打开', REG.msgdrawer.classList.contains('on') && REG.mask.classList.contains('on'));
  assert('M2 消息 6 条渲染', (REG.mglist._html.match(/class="mg-i/g) || []).length === 6);
  markAllRead();
  assert('M3 全部已读 toast', toastCount() > t0 && /已读/.test(lastToast()));
  closeMsg();
  assert('M4 消息抽屉关闭', !REG.msgdrawer.classList.contains('on'));

  /* ===== 验收4：角色切换 R1~R10 ===== */
  const expect = { R1: 18, R2: 7, R3: 5, R4: 10, R5: 4, R6: 3, R7: 3, R8: 2, R9: 5, R10: 1 };
  Object.keys(ROLES).forEach(function (k) {
    try {
      setRole(k);
      assert('C1 ' + k + ' 侧边栏数量', navCount() === expect[k], 'expect=' + expect[k] + ' got=' + navCount());
      assert('C2 ' + k + ' 用户卡角色名', REG.sidebar._html.indexOf(k + ' · ' + ROLES[k].name) >= 0 && REG.sidebar._html.indexOf(ROLES[k].user) >= 0);
      assert('C3 ' + k + ' 顶栏角色', REG.topbar._html.indexOf(k + ' ' + ROLES[k].name) >= 0);
    } catch (e) { assert('C* ' + k, false, 'EXCEPTION ' + e.message); }
  });
  setRole('R10');
  go('auth');
  assert('C4 R10 无权限模块拦截', state.page === 'workbench' && /无权限/.test(lastToast()), lastToast());
  setRole('R5'); go('auth');
  assert('C5 R5 跨权限拦截+提示', state.page === 'workbench' && /无权限/.test(lastToast()));
  setRole('R1'); go('fin'); setRole('R3');
  assert('C6 R3 有 fin 权限页面保持', state.page === 'fin');
  setRole('R1'); go('fin'); setRole('R7');
  assert('C7 无权页面切角色跳工作台', state.page === 'workbench' && /跳转至工作台/.test(lastToast()));

  /* ===== 验收4重点：R9 脱敏 ===== */
  /* 注意：R9 模块白名单不含 cert/acct，证件页/账号页对 R9 不可达 —— 用 sens() 所在的 R9 可见页面(DC)验证，
     并单独验证 cert/acct 在 R9 侧边栏确实隐藏（脱敏设计本身存在于渲染函数中，但 R9 视角看不到这两个页面） */
  setRole('R9');
  assert('D0a R9 侧边栏无 CERT/ACCT 入口', REG.sidebar._html.indexOf('证件档案') < 0 && REG.sidebar._html.indexOf('账号管理') < 0);
  go('dc');
  const r9d = content();
  assert('D1 R9 DC 穿透表实名人脱敏 ••••', r9d.indexOf('class="masked"') >= 0 && r9d.indexOf('••••') >= 0 && r9d.indexOf('>苏杳<') < 0 && r9d.indexOf('>李澈<') < 0);
  go('eff');
  assert('D2 R9 EFF 姓名脱敏', content().indexOf('class="masked"') >= 0 && content().indexOf('>苏杳<') < 0);
  assert('D3 证件号 前3+后4+星号', (function () { const m = maskID('1101051999032861234'); return m.slice(0,3) === '110' && m.slice(-4) === '1234' && m.slice(3,-4).split('').every(ch => ch === '*'); })(), maskID('1101051999032861234'));
  assert('D3b sens() R9 返回脱敏串', (function () { return sens('赵敏') === '<span class="masked">••••</span>'; })());
  (function () { go('bi'); })();
  assert('D4 R9 BI 页面可用且姓名列均脱敏', (function () { const h = content(); return h.indexOf('>陈默<') < 0 && h.indexOf('>王野<') < 0; })());
  setRole('R1'); go('cert');
  assert('D5 R1 明文恢复', content().indexOf('>苏杳<') >= 0 && content().indexOf('class="masked"') < 0);
  assert('D6 maskPhone 138****5678', maskPhone('13828715678') === '138****5678', maskPhone('13828715678'));

  /* ===== 验收5：抽屉交互 ===== */
  setRole('R1'); go('asset'); assetDetail(0);
  assert('I1 资产详情抽屉打开', REG.drawer.classList.contains('on') && REG['dr-title'].textContent.indexOf('资产详情') >= 0);
  assert('I2 资产抽屉宽度 720px', REG.drawer.style.width === '720px', 'w=' + REG.drawer.style.width);
  closeDrawer();
  assert('I3 抽屉关闭', !REG.drawer.classList.contains('on') && !REG.mask.classList.contains('on'));
  go('acct'); acctDetail(4);
  assert('I4 账号详情抽屉(池可领用)', REG['dr-title'].textContent.indexOf('账号详情') >= 0 && REG['dr-foot']._html.indexOf('申请领用') >= 0);
  assert('I5 账号详情三 Tab', REG['dr-body']._html.indexOf('基本信息') >= 0 && REG['dr-body']._html.indexOf('领用时间线') >= 0 && REG['dr-body']._html.indexOf('关联资产') >= 0);
  closeDrawer();
  go('cert'); certDetail(0);
  assert('I6 证件抽屉 L1 默认', REG['dr-body']._html.indexOf('L1 · 遮罩预览') >= 0);
  setCertLv('L2');
  assert('I7 L2 水印', REG.cvWm.style.opacity === 1 && REG.cvMask.style.display === 'none');
  setRole('R9'); certDetail(0); setCertLv('L3');
  assert('I8 R9 请求 L3 被拒', /无 L3/.test(lastToast()));
  setRole('R1'); certDetail(0); setCertLv('L3');
  assert('I9 R1 可 L3 留痕', /留痕/.test(lastToast()));
  closeDrawer();
  go('live'); liveReg();
  assert('I10 开播登记抽屉', REG['dr-title'].textContent.indexOf('开播风控登记') >= 0);
  liveRiskResult();
  assert('I11 风控结果抽屉(82分)', REG['dr-title'].textContent.indexOf('风控结果') >= 0 && REG['dr-body']._html.indexOf('82') >= 0 && REG['dr-body']._html.indexOf('R-07') >= 0);
  closeDrawer();
  go('content'); sopEdit();
  assert('I12 SOP 编辑抽屉 90% 宽', REG.drawer.style.width === '90%', 'w=' + REG.drawer.style.width);
  closeDrawer();
  go('comp'); compDetail(0);
  assert('I13 竞品详情抽屉', REG['dr-title'].textContent.indexOf('竞品详情') >= 0);
  openMsg(); assetDetail(0);
  HANDLERS.keydown.forEach(fn => fn({ key: 'Escape' }));
  assert('I14 ESC 关闭抽屉+消息', !REG.drawer.classList.contains('on') && !REG.msgdrawer.classList.contains('on') && !REG.rolemenu.classList.contains('on'));

  /* ===== 验收6：规格符合性 ===== */
  go('live');
  assert('G1 场次 ID IMS202609120DY0142', content().indexOf('IMS202609120DY0142') >= 0);
  assert('G2 fmtMoney(126800)=¥126,800.00', fmtMoney(126800) === '¥126,800.00', fmtMoney(126800));
  go('fin');
  const fin = content();
  assert('G3 FIN 金额格式（千分位+两位小数）', (function () {
    const ms = fin.match(/¥[0-9,]+[.][0-9]{2}/g) || [];
    return ms.length >= 10 && ms.every(s => /^¥[0-9]{1,3}(,[0-9]{3})*[.][0-9]{2}$/.test(s)) && fin.indexOf('¥186,400.00') >= 0;
  })(), (fin.match(/¥[0-9,]+[.][0-9]{2}/g) || []).slice(0, 4).join(' '));
  go('acct');
  const ac = content();
  assert('G4 ACCT 五态语义色文本(在用/池可领用/冻结/已归还/已注销)', ac.indexOf('在用') >= 0 && ac.indexOf('池可领用') >= 0 && ac.indexOf('冻结') >= 0 && ac.indexOf('已归还') >= 0 && ac.indexOf('已注销') >= 0);
  acctDetail(0);
  assert('G5 账号详情绑定手机 138****5678', REG['dr-body']._html.indexOf('138****5678') >= 0);
  closeDrawer();

  /* ===== 验收5补充：onclick 引用的函数全部已定义（无死按钮）===== */
  (function () {
    const re = /on(?:click|keydown)="([^"]*)"/g;
    const names = new Set();
    let m;
    while ((m = re.exec(FULLHTML))) {
      const name = m[1].replace(/[^A-Za-z0-9_$].*/, '');
      if (name) names.add(name);
    }
    const kw = new Set(['if', 'this', 'event', 'return']);
    let missing = [];
    names.forEach(n => {
      if (kw.has(n)) return;
      try { if (eval('typeof ' + n) !== 'function') missing.push(n + '(' + eval('typeof ' + n) + ')'); }
      catch (e) { missing.push(n + '(undefined)'); }
    });
    assert('B1 onclick 引用函数全部定义(' + names.size + ' 个)', missing.length === 0, 'missing=' + missing.join(','));
  })();

  /* ===== 输出 ===== */
  console.log('=== DYNAMIC RESULTS ===');
  console.log('PASS_COUNT = ' + R.length);
  console.log('FAIL_COUNT = ' + F.length);
  F.forEach(x => console.log('FAIL | ' + x));
  globalThis.__OUT__ = { pass: R.length, fail: F.length };
  process.exit(F.length ? 1 : 0);
})();
`;

/* 执行：单脚本 + 共享作用域 */
const code = scripts.join('\n;\n')
  + '\n;\nvar MODORDER=' + JSON.stringify(['workbench','auth','asset','acct','cert','live','content','train','meet','report','flow','fin','perf','alert','comp','dc','bi','eff']) + ';\n'
  + DRIVER;

const sandbox = {
  console, process, globalThis: {},
  document: stubDocument, window: null, event: { stopPropagation() {}, key: '', metaKey: false, ctrlKey: false, preventDefault() {}, target: null },
  REG, HANDLERS: handlers, FULLHTML: HTML,
  setTimeout: () => 0, Math, Date, Number, String, Array, Object, JSON, Set, RegExp, Error
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
try {
  vm.runInNewContext(code, sandbox, { filename: 'ims-prototype-combined.js' });
} catch (e) {
  console.log('=== DYNAMIC RESULTS ===');
  console.log('RUNTIME_ERROR = ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 5).join('\n'));
  process.exit(2);
}
