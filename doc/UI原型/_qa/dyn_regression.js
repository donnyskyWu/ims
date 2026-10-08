// QA 交互增强回归测试 v4：最小 DOM 桩（HTML id 解析注册 + qbar 模拟）+ vm 执行页面全部 JS
const fs = require('fs');
const vm = require('vm');
const HTML = fs.readFileSync(String.raw`D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html`, 'utf-8');

let DYN_ref = null;
/* 轻量解析：带 id 的标签 → MiniEl 注册（含 value/select options/textarea 文本/span 文本） */
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
    const set = new Set();
    const self = this;
    this.classList = {
      add: (...c) => c.forEach(x => set.add(x)),
      remove: (...c) => c.forEach(x => set.delete(x)),
      toggle: c => set.has(c) ? set.delete(c) : set.add(c),
      contains: c => set.has(c)
    };
    Object.defineProperty(this, 'className', {
      get() { return self._className; },
      set(v) { self._className = String(v); set.clear(); String(v).split(/\s+/).filter(Boolean).forEach(x => set.add(x)); }
    });
  }
  set innerHTML(v) {
    this._html = String(v);
    if (DYN_ref) {
      // 真实浏览器语义：innerHTML 赋值 = 全新元素。先清除新 html 中出现的 id 的旧注册，再注册新元素
      for (const m of String(v).matchAll(/id="([^"]+)"/g)) delete DYN_ref[m[1]];
      registerIds(this._html, DYN_ref);
    }
  }
  get innerHTML() { return this._html; }
  appendChild(c) { c.parentNode = this; this.children.push(c); if (c.id && DYN_ref) DYN_ref[c.id] = c; return c; }
  remove() {
    if (this.parentNode) { const i = this.parentNode.children.indexOf(this); if (i >= 0) this.parentNode.children.splice(i, 1); this.parentNode = null; }
    if (this.id && DYN_ref && DYN_ref[this.id] === this) delete DYN_ref[this.id];
    if (BODY.children.includes(this)) BODY.children.splice(BODY.children.indexOf(this), 1);
  }
  contains() { return false; }
  closest() { return null; }
  querySelectorAll() { return []; }
  focus() {}
}

const REG = {};
['sidebar', 'topbar', 'content', 'drawer', 'dr-title', 'dr-body', 'dr-foot', 'mask', 'msgdrawer', 'mglist', 'rolemenu', 'toasts', 'gsearch']
  .forEach(id => REG[id] = new MiniEl('div'));
const DYN = {};
DYN_ref = DYN;
const BODY = new MiniEl('body');
const handlers = { click: [], keydown: [] };
const timers = [];
function mySetTimeout(fn, ms) { timers.push({ fn, ms: ms || 0 }); return timers.length; }
function fireTimers(ms) {
  let n = 0;
  for (let i = timers.length - 1; i >= 0; i--) {
    if (ms == null || timers[i].ms === ms) { const t = timers.splice(i, 1)[0]; try { t.fn(); n++; } catch (e) { console.log('TIMER_ERR ' + e.message); } }
  }
  return n;
}

/* qbar 模拟 */
const QB = {
  elements: [],
  reset() { this.elements = []; },
  setControls(list) { this.elements = list; },
  querySelectorAll(sel) {
    if (sel === 'input,select') return this.elements;
    if (sel === 'input') return this.elements.filter(e => e.tagName === 'input');
    if (sel === 'select') return this.elements.filter(e => e.tagName === 'select');
    return [];
  }
};
function qInput(value) { return { tagName: 'input', value: value || '', selectedIndex: 0 }; }
function qSelect(value, idx) { return { tagName: 'select', value: value, selectedIndex: idx || 0 }; }

const fakeTr = { length: 0, classList: { add() { }, remove() { } } };
const stubDocument = {
  querySelector: s => {
    if (s[0] === '#' && s.indexOf(' ') < 0) { const id = s.slice(1); if (id in REG) return REG[id]; if (id in DYN) return DYN[id]; return null; }
    if (s === '#content .qbar') return QB;
    if (s === '#content tbody tr') { fakeTr.length = (REG.content._html.match(/<tr><td/g) || []).length; return fakeTr; }
    return null;
  },
  createElement: t => new MiniEl(t),
  addEventListener: (ev, fn) => { (handlers[ev] || (handlers[ev] = [])).push(fn); },
  getElementById: id => (id in REG) ? REG[id] : (DYN[id] || null),
  querySelectorAll: (s) => {
    if (s === '#cfwrap .urgei input:checked') {
      const w = DYN['cfwrap']; if (!w) return [];
      const n = (w._html.match(/class="urgei"/g) || []).length;
      return Array.from({ length: n }, () => ({ checked: true }));
    }
    if (s === '#cfwrap .cf-f .btn-pri') return [new MiniEl('button')];
    return [];
  },
  body: BODY
};

const scripts = [...HTML.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

const DRIVER = `
;(function () {
  const R = [], F = [];
  function assert(name, cond, detail) { (cond ? R : F).push(name + (detail ? ' | ' + detail : '')); }
  function lastToast() { const c = REG.toasts.children[REG.toasts.children.length - 1]; return c ? (c._html || '').replace(/<[^>]+>/g, '') : ''; }
  function navCount() { return (REG.sidebar._html.match(/class="nav-item/g) || []).length; }
  function content() { return REG.content._html; }
  function drBody() { return REG['dr-body']._html; }
  function drTitle() { return REG['dr-title'].textContent; }
  function drFoot() { return REG['dr-foot']._html; }
  function fill(k, v) { const el = document.getElementById('F_' + k); if (!el) throw new Error('no #F_' + k); el.value = v; }
  function getF(k) { return document.getElementById('F_' + k); }
  function cfwrap() { return DYN['cfwrap']; }
  function dlbar() { return DYN['dlbar']; }
  function rowCount() { return (content().match(/<tr><td/g) || []).length; }
  function setControls(list) { QB.setControls(list); }

  setRole('R1');

  /* ============ A. assetReg 表单系统 ============ */
  go('asset');
  assetReg();
  assert('A1 资产登记抽屉 480px', REG.drawer.classList.contains('on') && REG.drawer.style.width === '480px', 'w=' + REG.drawer.style.width);
  assert('A2 表单 10 字段 + 10 个 ferr', (drBody().match(/id="F_/g) || []).length === 10 && (drBody().match(/class="ferr"/g) || []).length === 10);
  assert('A3 必填星号', drBody().indexOf('<i class="req">*</i>') >= 0);
  assetRegSubmit();
  assert('A4 空提交拦截 toast', /请先完成必填项/.test(lastToast()), lastToast());
  assert('A5 空名称错误提示写入 E_name', DYN['E_name'] && DYN['E_name'].textContent === '必填项，请填写', DYN['E_name'] ? DYN['E_name'].textContent : 'no el');
  assert('A6 空名称红框 err', getF('name').classList.contains('err'));
  assert('A7 数据未写入', ASSETS.length === 13, 'len=' + ASSETS.length);
  fill('name', '大疆 Osmo Pocket 3'); fill('type', '拍摄设备'); fill('spec', '4K/120fps'); fill('buy', '2026-09-10'); fill('price', '3499'); fill('owner', '孙倩');
  assetRegSubmit();
  assert('A8 formOk 成功态 AS20260912014', drTitle() === '提交成功' && /AS20260912014/.test(drBody()), drTitle());
  assert('A9 ASSETS unshift', ASSETS[0].name === '大疆 Osmo Pocket 3' && ASSETS.length === 14);
  assert('A10 表格重渲染含新行', content().indexOf('大疆 Osmo Pocket 3') >= 0);
  assert('A11 toast 登记成功', /资产登记成功/.test(lastToast()), lastToast());
  assert('A12 formOk 底钮', /关闭并查看结果/.test(drFoot()) && /继续新增/.test(drFoot()));
  closeDrawer();

  /* ============ B. finCalc ============ */
  go('fin');
  finAdd();
  assert('B1 结算表单 rev/cost/ratio', REG.drawer.classList.contains('on') && !!getF('rev') && !!getF('cost') && !!getF('ratio'));
  fill('rev', '100000'); fill('cost', '40000'); fill('ratio', '30');
  finCalc();
  assert('B2 毛利 ¥60,000.00', DYN['finP'].textContent === '¥60,000.00', DYN['finP'].textContent);
  assert('B3 分成 ¥18,000.00', DYN['finS'].textContent === '¥18,000.00', DYN['finS'].textContent);
  assert('B4 净利 ¥42,000.00', DYN['finN'].textContent === '¥42,000.00', DYN['finN'].textContent);
  fill('rev', '10000'); fill('cost', '40000');
  finCalc();
  assert('B5 负毛利：分成¥0.00/净利¥-30,000.00/neg', DYN['finS'].textContent === '¥0.00' && DYN['finN'].textContent === '¥-30,000.00' && DYN['finN'].className.indexOf('neg') >= 0, DYN['finN'].textContent + '|' + DYN['finN'].className);
  fill('rev', '100000');
  const fins0 = FINS.length;
  finAddSubmit();
  assert('B6 FINS unshift 待结算', FINS.length === fins0 + 1 && FINS[0].st === '待结算' && FINS[0].rev === 100000);
  assert('B7 formOk 净利润', /提交成功/.test(drTitle()) && /¥42,000\\.00/.test(drBody()));
  closeDrawer();

  /* ============ C. certNoPreview ============ */
  go('cert');
  certAdd();
  assert('C1 证件归档表单', REG.drawer.classList.contains('on') && !!getF('no'));
  assert('C2 预览初始「待输入…」', DYN['certPrev'] && DYN['certPrev'].textContent === '待输入…', DYN['certPrev'] ? DYN['certPrev'].textContent : 'no el');
  const inp = getF('no');
  inp.value = '1101051999032861234';
  certNoPreview(inp);
  const pv = DYN['certPrev'].textContent;
  assert('C3 预览前3+星+后4', pv.indexOf('110') === 0 && pv.indexOf('1234') > 0 && pv.indexOf('（归档后仅授权角色') >= 0, pv);
  assert('C4 预览不含完整明文', pv.indexOf('1101051999032861234') < 0, pv);
  fill('holder', '苏杳'); fill('type', '居民身份证'); fill('exp', '2027-06-01'); fill('issue', '2026-01-01');
  const cert0 = CERTS.length;
  certAddSubmit();
  assert('C5 CERTS unshift 审核中', CERTS.length === cert0 + 1 && CERTS[0].st === '审核中' && CERTS[0].holder === '苏杳');
  closeDrawer();

  /* ============ D. 日报完成度 ============ */
  go('report');
  reportWrite();
  assert('E1 日报 5 字段', (drBody().match(/id="F_/g) || []).length === 5);
  fill('done', '完成直播 2 场');
  const rep0 = REPORTS.length;
  reportWriteSubmit();
  assert('E2 仅done→33%', REPORTS.length === rep0 + 1 && REPORTS[0].pct === 33 && REPORTS[0].st === '已提交', 'pct=' + (REPORTS[0] || {}).pct);
  assert('E3 formOk 33%', /33%/.test(drBody()));
  closeDrawer();
  reportWrite(); fill('done', 'x'); fill('plan', 'y'); fill('risk', 'z');
  reportWriteSubmit();
  assert('E4 三字段→100%', REPORTS[0].pct === 100);
  closeDrawer();

  /* ============ F. 表单抽屉冒烟（15 个全部） ============ */
  const formFns = [
    ['acctApply()', 'acct', '账号领用申请'], ['trainAdd()', 'train', '新建培训'], ['meetAdd()', 'meet', '预约会议'],
    ['flowAdd()', 'flow', '发起流程'], ['perfAdd()', 'perf', '新建考核方案'], ['alertRuleAdd()', 'alert', '新建预警规则'],
    ['compAdd()', 'comp', '新增竞品'], ['biAdd()', 'bi', '新建自定义报表'], ['finReimburse()', 'workbench', '费用报销申请']
  ];
  formFns.forEach(function (f) {
    try {
      go(f[1]); closeDrawer(); eval(f[0]);
      assert('F1 ' + f[2], drTitle().indexOf(f[2]) >= 0 && (drBody().match(/id="F_/g) || []).length >= 3, drTitle());
      closeDrawer();
    } catch (e) { assert('F1 ' + f[2], false, 'EXCEPTION ' + e.message); }
  });
  go('acct');
  const fi = ACCTS.findIndex(function (a) { return a.frozen && a.st === '冻结'; });
  acctDetail(fi); acctUnfreeze(fi);
  assert('F2 申请解冻表单（冻结账号）', /申请解冻/.test(drTitle()) && !!getF('reason'), drTitle());
  acctUnfreezeSubmit(fi);
  assert('F3 解冻提交→danger 确认（btn-red+warn）', !!cfwrap() && /btn-red/.test(cfwrap()._html) && /cf-warn/.test(cfwrap()._html));
  closeConfirm(); closeDrawer(); closeDrawer();
  go('asset'); assetDetail(0); assetFlow(0);
  assert('F4 发起流转表单', /发起流转/.test(drTitle()) && !!getF('to'));
  closeDrawer(); closeDrawer();

  /* ============ G. confirmDlg / doConfirm ============ */
  globalThis.__CF_HIT__ = 0;
  confirmDlg('测试标题', '测试正文', '确定', function () { globalThis.__CF_HIT__++; });
  const cw = cfwrap();
  assert('G1 confirmDlg 渲染 on', !!cw && cw.classList.contains('on'), cw ? cw.className : 'null');
  assert('G2 cfcard+标题+双钮', /class="cfcard/.test(cw._html) && /测试标题/.test(cw._html) && /取消/.test(cw._html) && /确定/.test(cw._html));
  doConfirm();
  assert('G3 回调执行+移除', globalThis.__CF_HIT__ === 1 && !cfwrap());

  /* ============ H. alert 状态机（alertHandle 两段式：抽屉 → alertHandleGo 确认窗 → 状态翻转） ============ */
  go('alert'); setTab('alert', '实时预警');
  assert('H0 ALERTS[0] 未处理/红', ALERTS[0].st === '未处理' && ALERTS[0].lv === '红');
  alertHandle(0);
  assert('H1 处理抽屉（预警处理 + 开始处理钮）', /预警处理/.test(drTitle()) && /alertHandleGo\\(0\\)/.test(drFoot()));
  alertHandleGo(0);
  assert('H1b danger 确认窗', !!cfwrap() && /btn-red/.test(cfwrap()._html) && /开始处理/.test(cfwrap()._html));
  doConfirm();
  assert('H2 未处理→处理中', ALERTS[0].st === '处理中', ALERTS[0].st);
  alertRecover(0);
  assert('H3 恢复确认窗', !!cfwrap() && /标记恢复/.test(cfwrap()._html));
  doConfirm();
  assert('H4 处理中→已恢复', ALERTS[0].st === '已恢复', ALERTS[0].st);
  assert('H5 表格渲染已恢复', /已恢复/.test(content()));
  closeConfirm();

  /* ============ I. acctReturn ============ */
  go('acct');
  const ti_ = ACCTS.findIndex(function (a) { return a.st === '在用' && !a.frozen; });
  acctReturn(ti_);
  assert('I1 归还确认窗+warn', !!cfwrap() && /确认发起归还/.test(cfwrap()._html) && /cf-warn/.test(cfwrap()._html));
  doConfirm();
  assert('I2 →已归还/责任人清空', ACCTS[ti_].st === '已归还' && ACCTS[ti_].owner === '—', ACCTS[ti_].st + '/' + ACCTS[ti_].owner);
  assert('I3 toast 释放至池', /已释放至池/.test(lastToast()), lastToast());

  /* ============ J. trainEnroll ============ */
  go('train');
  const ti = TRAINS.findIndex(function (t) { return t.st === '报名中' && t.signed < t.quota; });
  const s0 = TRAINS[ti].signed;
  trainEnroll(ti);
  assert('J1 报名确认窗 n/quota', !!cfwrap() && new RegExp(s0 + '/' + TRAINS[ti].quota).test(cfwrap()._html));
  doConfirm();
  assert('J2 signed+1', TRAINS[ti].signed === s0 + 1);
  TRAINS[ti].signed = TRAINS[ti].quota; renderPage();
  assert('J3 满员禁用按钮', /已满员/.test(content()) && /disabled/.test(content()));
  trainEnroll(ti);
  assert('J4 满员拦截', /已满员/.test(lastToast()), lastToast());
  assert('J5 signed 不变', TRAINS[ti].signed === TRAINS[ti].quota);

  /* ============ K. exportX / dlbar ============ */
  go('asset');
  const btn = document.createElement('button'); btn.innerHTML = '原始导出按钮'; btn._html = '原始导出按钮';
  exportX(btn, '资产台账', 11);
  assert('K1 转圈态', btn.disabled === true && /spin/.test(btn.innerHTML) && /导出中/.test(btn.innerHTML));
  fireTimers(900);
  assert('K2 900ms toast', /已导出/.test(lastToast()), lastToast());
  const dlb = dlbar();
  assert('K3 dlbar 文件名+条数', !!dlb && /资产台账\\.xlsx/.test(dlb._html) && /11 条数据/.test(dlb._html), dlb ? '' : 'null');
  assert('K4 3s 淡出定时器', timers.some(function (t) { return t.ms === 3000; }), 'ms=' + timers.map(t => t.ms).join(','));
  assert('K5 按钮恢复', btn.disabled === false && btn.innerHTML === '原始导出按钮');
  fireTimers(3000);
  assert('K6 fadeout', dlb.classList.contains('fadeout'));
  fireTimers(400);
  assert('K7 移除', !dlbar());

  /* ============ L. 查询过滤（qbar 模拟 + qSave 驱动） ============ */
  go('asset');
  setControls([qInput(''), qInput('罗技'), qSelect('全部类型', 0), qSelect('全部状态', 0), qInput(''), qInput(''), qInput('')]);
  qSave('asset');
  assert('L1 资产「罗技」命中 2 行', rowCount() === 2, 'n=' + rowCount());
  assert('L1b toast 查询完成计数', /查询完成 · 共 2 条/.test(lastToast()), lastToast());
  setControls([qInput(''), qInput('不存在关键词XYZ'), qSelect('全部类型', 0), qSelect('全部状态', 0), qInput(''), qInput(''), qInput('')]);
  qSave('asset');
  assert('L2 不存在关键词→空态', /class="empty"/.test(content()) && /暂无数据/.test(content()));
  setControls([qInput(''), qInput(''), qSelect('全部类型', 0), qSelect('全部状态', 0), qInput(''), qInput(''), qInput('')]);
  qSave('asset');
  assert('L3 重置恢复全量', rowCount() === 14, 'n=' + rowCount());

  go('acct');
  setControls([qInput(''), qSelect('全部平台', 0), qSelect('全部状态', 0), qInput('孙倩'), qInput('')]);
  qSave('acct');
  const expSun = ACCTS.filter(function (a) { return a.owner === '孙倩'; }).length;
  assert('L4 账号「孙倩」=' + expSun + ' 行', rowCount() === expSun, 'n=' + rowCount());

  const expFrozen = ACCTS.filter(function (a) { return a.st === '冻结'; }).length;
  setControls([qInput(''), qSelect('全部平台', 0), qSelect('冻结', 2), qInput(''), qInput('')]);
  qSave('acct');
  assert('L5 账号状态「冻结」应命中 ' + expFrozen + ' 行', rowCount() === expFrozen, '实际 n=' + rowCount());

  go('cert');
  setControls([qInput('苏杳'), qSelect('全部类型', 0), qSelect('档案状态', 0), qSelect('到期状态', 0)]);
  qSave('cert');
  const expSu = CERTS.filter(function (c) { return c.holder === '苏杳'; }).length;
  assert('L6 证件「苏杳」=' + expSu + ' 行', rowCount() === expSu, 'n=' + rowCount());

  const expPassport = CERTS.filter(function (c) { return c.type === '护照'; }).length;
  setControls([qInput(''), qSelect('护照', 2), qSelect('档案状态', 0), qSelect('到期状态', 0)]);
  qSave('cert');
  assert('L7 证件类型「护照」应命中 ' + expPassport + ' 行', rowCount() === expPassport, '实际 n=' + rowCount());

  go('train');
  const expEnroll = TRAINS.filter(function (t) { return t.st === '报名中'; }).length;
  setControls([qInput(''), qInput(''), qSelect('全部类型', 0), qInput(''), qSelect('报名中', 1)]);
  qSave('train');
  assert('L8 培训状态「报名中」应命中 ' + expEnroll + ' 行', rowCount() === expEnroll, '实际 n=' + rowCount());

  go('alert'); setTab('alert', '实时预警');
  const expRed = ALERTS.filter(function (a) { return a.lv === '红'; }).length;
  setControls([qSelect('红', 1), qSelect('全部状态', 0), qInput('')]);
  qSave('alert');
  assert('L9 预警级别「红」应命中 ' + expRed + ' 行', rowCount() === expRed, '实际 n=' + rowCount());

  go('acct');
  setControls([qInput('神鱼'), qSelect('全部平台', 0), qSelect('全部状态', 0), qInput(''), qInput('')]);
  const rbtn = { closest: function () { return QB; } };
  resetQ(rbtn);
  assert('L10 resetQ 清空+toast', QB.elements[0].value === '' && /查询条件已重置/.test(lastToast()), lastToast());
  qSave('acct');
  assert('L11 resetQ 后全量 ACCTS.length 行', rowCount() === ACCTS.length, 'n=' + rowCount() + ' exp=' + ACCTS.length);
  setControls([]);

  /* ============ M. 行操作链路 ============ */
  go('live'); setTab('live', '场次台账');
  const lh = LIVES.find(function (l) { return l.risk >= 60 && l.st !== '已取消'; });
  liveToReview(lh.id);
  assert('M1 liveToReview 确认窗', !!cfwrap() && /转人工复核/.test(cfwrap()._html));
  doConfirm();
  assert('M2 →待复核', lh.st === '待复核', lh.st);
  go('flow');
  urge('FL20260912-07', '周晴');
  assert('M3 urge 确认窗', !!cfwrap() && /催办/.test(cfwrap()._html));
  doConfirm();
  assert('M4 urge toast', /催办已发送/.test(lastToast()), lastToast());
  flowUrgeBatch();
  assert('M5 批量催办列表', !!cfwrap() && /urgets/.test(cfwrap()._html) && /checkbox/.test(cfwrap()._html));
  doConfirm();
  assert('M6 批量催办 toast', /批量催办已发送/.test(lastToast()), lastToast());
  go('comp');
  const b0 = COMP_BASKET.length;
  compCompare(0);
  assert('M7 compCompare 确认窗', !!cfwrap() && /加入对比篮/.test(cfwrap()._html));
  doConfirm();
  assert('M8 对比篮+1', COMP_BASKET.length === b0 + 1);
  compCompare(0);
  assert('M9 重复拦截', /已在对比篮/.test(lastToast()));
  go('dc');
  dcDrill('ACCT');
  assert('M10 dcDrill 确认窗', !!cfwrap() && /穿透/.test(cfwrap()._html));
  doConfirm();
  assert('M11 dcDrill toast', /穿透查询完成/.test(lastToast()), lastToast());
  const sbtn = document.createElement('button'); sbtn.innerHTML = '同步'; sbtn._html = '同步';
  dcSync(sbtn);
  assert('M12 dcSync 转圈', sbtn.disabled === true && /同步中/.test(sbtn.innerHTML));
  fireTimers(1400);
  assert('M13 dcSync 完成', sbtn.disabled === false && sbtn.innerHTML === '同步' && /数据同步完成/.test(lastToast()), lastToast());
  go('bi');
  biSubscribe();
  assert('M14 biSubscribe 确认窗', !!cfwrap() && /订阅/.test(cfwrap()._html));
  doConfirm();
  assert('M15 已订阅 toast', /已订阅/.test(lastToast()));
  go('live');
  liveSessionDetail('IMS202609120DY0142');
  assert('M16 场次详情抽屉', /场次详情/.test(drTitle()) && /82/.test(drBody()));
  liveSessionDetail('NOT_EXIST');
  assert('M17 未知场次 error toast', /未找到场次/.test(lastToast()), lastToast());
  closeDrawer();
  go('alert');
  alertRuleAdd();
  fill('name', '新规则X'); fill('obj', '账号管理'); fill('cond', '风险分 ≥ 85 触发');
  alertRuleAddSubmit();
  assert('N1 pills 不阻断提交', /提交成功/.test(drTitle()), drTitle());
  closeDrawer();

  /* ============ P. 既有功能回归 ============ */
  MODORDER.forEach(function (id) {
    try {
      go(id);
      const marker = id === 'workbench' ? '待办中心' : MODS[id].page;
      const c = content();
      assert('P1 渲染 ' + id, state.page === id && c.length > 500 && c.indexOf(marker) >= 0 && !/undefined/.test(c) && !/NaN/.test(c), 'len=' + c.length);
    } catch (e) { assert('P1 渲染 ' + id, false, 'EXCEPTION ' + e.message); }
  });
  assert('P2 R1 侧边栏 23 项（含 AIR 5 子菜单）', navCount() === 23, 'n=' + navCount());

  setRole('R9');
  assert('P3 R9 侧边栏含证件/账号', /证件档案/.test(REG.sidebar._html) && /账号管理/.test(REG.sidebar._html));
  go('cert');
  assert('P4 R9 CERT 脱敏', /class="masked"/.test(content()) && !/>苏杳</.test(content()));
  go('acct');
  assert('P5 R9 ACCT 脱敏', /class="masked"/.test(content()) && !/>赵敏</.test(content()));
  go('dc');
  assert('P6 R9 DC 脱敏', /class="masked"/.test(content()) && !/>苏杳</.test(content()));
  setRole('R1'); go('cert');
  assert('P7 R1 明文恢复', />苏杳</.test(content()) && !/class="masked"/.test(content()));

  const expect = { R1: 23, R2: 7, R3: 5, R4: 10, R5: 4, R6: 3, R7: 3, R8: 2, R9: 7, R10: 1, R11: 6 };
  Object.keys(ROLES).forEach(function (k) {
    setRole(k);
    assert('P8 ' + k + ' 侧边栏', navCount() === expect[k], 'exp=' + expect[k] + ' got=' + navCount());
  });
  setRole('R7'); go('live');
  assert('P9 R7 主播访问 live', state.page === 'live');
  setRole('R1');

  go('asset'); assetDetail(0);
  assert('P10 资产详情 720px', REG.drawer.style.width === '720px' && /资产详情/.test(drTitle()));
  closeDrawer();
  go('cert'); certDetail(0);
  assert('P11a 证件抽屉 L1 遮罩', /L1 · 遮罩预览/.test(drBody()));
  setCertLv('L2');
  assert('P11b L2 水印 opacity=1', DYN['cvWm'] && DYN['cvWm'].style.opacity === 1, DYN['cvWm'] ? String(DYN['cvWm'].style.opacity) : 'no el');
  assert('P11c L2 遮罩隐藏', DYN['cvMask'] && DYN['cvMask'].style.display === 'none');
  setRole('R9'); certDetail(0); setCertLv('L3');
  assert('P12 R9 L3 拒绝', /无 L3/.test(lastToast()), lastToast());
  setRole('R1'); closeDrawer();
  go('live'); liveReg();
  assert('P13 开播登记抽屉', /开播风控登记/.test(drTitle()));
  liveRiskResult();
  assert('P14 风控结果 82', /风控结果/.test(drTitle()) && /82/.test(drBody()));
  closeDrawer();
  go('content'); sopEdit();
  assert('P15 SOP 编辑 90%', REG.drawer.style.width === '90%');
  closeDrawer();

  go('workbench');
  setTab('workbench', '告警');
  assert('P16 告警 Tab 1 条', (content().match(/class="mg-i"/g) || []).length === 1 && /ACCT-2026-0087/.test(content()));
  setTab('workbench', '全部');
  go('perf'); setTab('perf', '考核结果');
  assert('P17 PERF 考核结果', /被考核人/.test(content()));
  setTab('perf', '考核方案');
  go('auth'); setTab('auth', '岗位模板');
  assert('P18 AUTH 模板', /直播运营岗模板/.test(content()));
  setTab('auth', '用户权限');

  go('asset'); assetDetail(0);
  confirmDlg('x', 'y', 'ok', function () { });
  HANDLERS.keydown.forEach(fn => fn({ key: 'Escape', metaKey: false, ctrlKey: false, preventDefault() { }, target: null }));
  assert('P19 ESC 优先关确认窗', !cfwrap() && REG.drawer.classList.contains('on'));
  HANDLERS.keydown.forEach(fn => fn({ key: 'Escape', metaKey: false, ctrlKey: false, preventDefault() { }, target: null }));
  assert('P20 ESC 关抽屉', !REG.drawer.classList.contains('on'));

  go('workbench');
  const quickActs = QUICK.map(function (q) { return q.act; });
  assert('P21 快捷入口含 assetReg/acctApply/finReimburse', quickActs.indexOf('assetReg()') >= 0 && quickActs.indexOf('acctApply()') >= 0 && quickActs.indexOf('finReimburse()') >= 0);
  try { assetReg(); assert('P22 快捷入口资产登记表单', /资产登记/.test(drTitle())); closeDrawer(); } catch (e) { assert('P22', false, e.message); }
  try { finReimburse(); assert('P23 快捷入口费用报销表单', /费用报销申请/.test(drTitle())); closeDrawer(); } catch (e) { assert('P23', false, e.message); }

  /* ============ Q. 事件绑定函数全定义 ============ */
  (function () {
    const names = new Set();
    let m;
    const re = /on(?:click|input|change|keydown)="([^"]*)"/g;
    while ((m = re.exec(FULLHTML))) {
      const body = m[1];
      const fnRe = /(^|[;(,\\s])([A-Za-z_$][\\w$]*)\\s*\\(/g;
      let m2;
      while ((m2 = fnRe.exec(body))) names.add(m2[2]);
    }
    const kw = new Set(['if', 'this', 'event', 'return', 'setTimeout', 'confirmDlg', 'stopPropagation', 'preventDefault', 'toggle', 'remove', 'focus', 'toast', 'function']);
    const missing = [];
    names.forEach(n => {
      if (kw.has(n)) return;
      try { if (eval('typeof ' + n) !== 'function') missing.push(n + ':' + eval('typeof ' + n)); }
      catch (e) { missing.push(n + ':undef'); }
    });
    assert('Q1 事件函数全定义（' + names.size + ' 个）', missing.length === 0, 'missing=' + missing.join(','));
  })();

  console.log('=== REGRESSION RESULTS ===');
  console.log('PASS_COUNT = ' + R.length);
  console.log('FAIL_COUNT = ' + F.length);
  F.forEach(x => console.log('FAIL | ' + x));
  globalThis.__OUT__ = { pass: R.length, fail: F.length };
  process.exit(F.length ? 1 : 0);
})();
`;

const code = scripts.join('\n;\n')
  + '\n;\nvar MODORDER=' + JSON.stringify(['workbench', 'auth', 'asset', 'acct', 'cert', 'live', 'content', 'train', 'meet', 'report', 'flow', 'fin', 'perf', 'alert', 'comp', 'dc', 'bi', 'eff']) + ';\n'
  + DRIVER;

const sandbox = {
  console, process, globalThis: {},
  document: stubDocument, window: null, event: { stopPropagation() { }, key: '', metaKey: false, ctrlKey: false, preventDefault() { }, target: null },
  REG, DYN, HANDLERS: handlers, FULLHTML: HTML, BODY, fireTimers, timers, QB, qInput, qSelect,
  setTimeout: mySetTimeout, clearTimeout: () => { },
  Math, Date, Number, String, Array, Object, JSON, Set, RegExp, Error, Map
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
try {
  vm.runInNewContext(code, sandbox, { filename: 'ims-regression-combined.js' });
} catch (e) {
  console.log('=== REGRESSION RESULTS ===');
  console.log('RUNTIME_ERROR = ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 8).join('\n'));
  process.exit(2);
}
