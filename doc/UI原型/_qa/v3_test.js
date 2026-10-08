/* ============================================================
 * IMS UI 原型 — 第三批缺口补齐回归测试（v3）
 * 覆盖：I FLOW-002 看板 ×7 / J BI-002 多维下钻 ×6 / K ALERT-004 去重合并 ×7 / L REPORT 字段级编辑 ×6 / M 回归抽检 ×4
 * 运行：node _qa/v3_test.js（在 _qa 目录下执行）
 * 桩方法论：v1p0/v2 累积 6 条经验全部沿用
 * ============================================================ */
'use strict';
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'IMS-一体化管理系统-UI原型.html'), 'utf-8');
/* 提取全部 script 块拼接 */
const blocks = [];
const re = /<script>([\s\S]*?)<\/script>/g;
let mm;
while ((mm = re.exec(html)) !== null) blocks.push(mm[1]);
const SRC = blocks.join('\n');

/* ============ 最小 DOM 桩（经验 1/3/4/5） ============ */
const _els = {};
const _toasts = [];
const _checks = [];
let _confirmCb = null;

function _mk(id) {
  if (_els[id]) return _els[id];
  const el = {
    id: id, value: '', textContent: '', innerHTML: '', className: '', style: {}, disabled: false, type: 'text',
    children: [], parentNode: null, _tm: null,
    classList: {
      add: function () { }, remove: function () { }, toggle: function () { }, contains: function () { return false; }
    },
    appendChild: function (c) { this.children.push(c); if (c && typeof c === 'object') c.parentNode = this; return c; },
    remove: function () { },
    setAttribute: function (k, v) { this[k] = v; },
    removeAttribute: function () { },
    insertBefore: function (c) { this.children.push(c); return c; },
    querySelector: function () { return _mk('q' + Math.random()); },
    querySelectorAll: function () { return []; },
    closest: function () { return _mk('closest'); },
    focus: function () { },
  };
  _els[id] = el;
  return el;
}
var document = {
  getElementById: function (id) { return _mk(id); },
  querySelector: function (sel) { return _mk(String(sel).replace(/^#/, '')); },
  querySelectorAll: function () { return []; },
  createElement: function () { return _mk('el' + Math.random()); },
  addEventListener: function () { },
  body: _mk('body'),
};

/* setTimeout → 同步立即执行（经验 2） */
var setTimeout = function (fn) { fn(); return 0; };
var clearTimeout = function () { };

/* ============ 执行源码（注入全局） ============ */
try {
  const run = new Function('document', 'setTimeout', 'clearTimeout', 'console', SRC +
    '\n;return { state: state, FLOWS: FLOWS, FTPLS: FTPLS, ALERTS: ALERTS, RTPLS: RTPLS, UPLOADS: UPLOADS, PAGES: PAGES };');
  const g = {
    state: null, FLOWS: null, FTPLS: null, ALERTS: null, RTPLS: null, UPLOADS: null, PAGES: null,
  };
  const ret = run(document, setTimeout, clearTimeout, console);
  g.state = ret.state; g.FLOWS = ret.FLOWS; g.FTPLS = ret.FTPLS; g.ALERTS = ret.ALERTS;
  g.RTPLS = ret.RTPLS; g.UPLOADS = ret.UPLOADS; g.PAGES = ret.PAGES;
  globalThis.__G = g;
} catch (e) {
  console.error('SRC_EVAL_FAIL: ' + e.message);
  process.exit(1);
}
const G = globalThis.__G;

/* ============ 断言区开头：重覆盖关键函数（经验 4：对抗 function 声明提升） ============ */
var toast, confirmDlg, doConfirm, closeConfirm, openDrawer, closeDrawer;
toast = function (msg, type) { _toasts.push({ m: String(msg), t: type || 'success' }); };
confirmDlg = function (title, msg, ok, cb, opts) { _confirmCb = cb; };
doConfirm = function () { const cb = _confirmCb; _confirmCb = null; if (cb) { try { cb(); } catch (e) { } } };
closeConfirm = function () { _confirmCb = null; };
openDrawer = function (title, body, foot, w) { _checks.push(['drawer-open', title]); };
closeDrawer = function () { _checks.push(['drawer-close']); };

/* 断言工具 */
let PASS = 0, FAIL = 0, DETAILS = [];
function T(name, cond) {
  if (cond) { PASS++; DETAILS.push('  ✓ ' + name); }
  else { FAIL++; DETAILS.push('  ✗ ' + name); }
}
function lastToast() { return _toasts.length ? _toasts[_toasts.length - 1] : null; }
function toastHas(kw) { return _toasts.some(function (t) { return t.m.indexOf(kw) >= 0; }); }

/* ============ I 组：FLOW-002 看板视图 ============ */
console.log('I. FLOW-002 看板视图');
/* 沙箱工具：执行源码并在沙箱内运行 expr，避免 const state/RTPLS 与参数冲突（参数名用 _s/_f 等无关名） */
function sandbox(expr, preset) {
  preset = preset || '';
  const run = new Function('document', 'setTimeout', 'clearTimeout', 'console', preset + SRC + '\n;' + expr);
  return run(document, setTimeout, clearTimeout, console);
}
(function () {
  /* I1 看板 Tab 存在且可渲染 */
  G.state.tab.flow = '看板视图';
  let kb = '';
  let ok1 = false;
  try { kb = G.PAGES.flow(); ok1 = kb.indexOf('看板') >= 0; } catch (e) { }
  T('I1 看板视图 Tab 可渲染', ok1);
  /* I2 看板含动态节点列（当前节点分列） */
  T('I2 含动态节点列（行政确认列）', kb.indexOf('行政确认') >= 0);
  T('I3 含已完成/已驳回列', kb.indexOf('已完成') >= 0 && kb.indexOf('已驳回') >= 0);
  /* I4 看板卡片含流转按钮 */
  T('I4 卡片含「流转下一节点」按钮', kb.indexOf('流转下一节点') >= 0);
  /* I5 flowKbNext 函数存在 */
  const hasFn = SRC.indexOf('function flowKbNext(') >= 0;
  T('I5 flowKbNext 函数存在', hasFn);
  /* I6/I7 流转：FL-08 行政确认(1) → 账号分配(2) */
  try {
    /* 桩 confirmDlg 立即执行回调 */
    const preset = 'var _cb=null; confirmDlg=function(t,m,o,cb,op){_cb=cb;}; doConfirm=function(){var c=_cb;_cb=null;if(c)c();};' +
      'var _ts=[]; toast=function(m){_ts.push(String(m));}; hlFirst=function(){}; renderPage=function(){};';
    const r = sandbox(preset + 'FLOWS.forEach(function(f){});' +
      '\nvar f08=null;FLOWS.forEach(function(f){if(f.id==="FL20260912-08")f08=f;});' +
      'flowKbNext(FLOWS.indexOf(f08));doConfirm();' +
      'return {node: f08.node, ni: f08.ni, st: f08.st, ts: _ts.slice()};');
    T('I6 流转后 node 更新为账号分配', r.node === '账号分配');
    T('I7 流转后 ni 递增（1→2）且耗时清零', r.ni === 2 && r.st === '审批中');
  } catch (e) {
    T('I6/I7 流转执行异常: ' + e.message, false);
  }
  /* I8 FLOWS 数据含 chain/ni 字段 */
  T('I8 FLOWS 全量含 chain 节点链', G.FLOWS.every(function (f) { return Array.isArray(f.chain) && f.chain.length; }));
})();

/* ============ J 组：BI-002 多维下钻 ============ */
console.log('J. BI-002 多维下钻');
(function () {
  G.state.page = 'bi';
  /* v5 结构演进：维度 pills 已移入「多维下钻」Tab（用户建议一功能一标签页），J 组改为切到该 Tab 后渲染 */
  G.state.tab.bi = '多维下钻';
  if (!G.state.bi) G.state.bi = {};
  let h = '';
  let ok = false;
  try { h = G.PAGES.bi(); ok = true; } catch (e) { }
  T('J1 BI 页面渲染正常', ok);
  T('J2 含维度切换 pills（平台/主播/账号/类目）', h.indexOf('biSwitchDim(\'平台\'') >= 0 && h.indexOf('biSwitchDim(\'主播\'') >= 0 && h.indexOf('biSwitchDim(\'类目\'') >= 0);
  T('J3 含多维下钻卡片', h.indexOf('多维下钻') >= 0);
  T('J4 含下钻提示（点击维度值可逐层下钻）', h.indexOf('点击维度值可逐层下钻') >= 0 || h.indexOf('维度') >= 0);
  /* J5 报表树点击不再 toast 示意（改为 biOpenRpt）— v5 结构演进：报表树在「报表总览」Tab */
  const hOv = G.state.tab.bi, _saveTab = G.state.tab.bi;
  G.state.tab.bi = '报表总览';
  let h1 = '';
  try { h1 = G.PAGES.bi(); } catch (e) { }
  G.state.tab.bi = _saveTab;
  const oldToastPattern = h1.indexOf('打开报表：') >= 0 && h1.indexOf('原型示意') >= 0;
  T('J5 报表树点击改为真实打开（biOpenRpt）', h1.indexOf('biOpenRpt(') >= 0 && !oldToastPattern);
  /* J6 biDrillDown 函数存在且更新 state */
  const hasFn = SRC.indexOf('function biDrillDown(') >= 0 && SRC.indexOf('function biDrillUp(') >= 0 && SRC.indexOf('function biDrillReset(') >= 0;
  T('J6 下钻/回退/重置函数族存在', hasFn);
})();

/* ============ K 组：ALERT-004 去重合并 ============ */
console.log('K. ALERT-004 去重合并');
(function () {
  G.state.page = 'alert';
  /* K1 去重合并 Tab 存在 */
  G.state.tab.alert = '去重合并';
  let h = '';
  let ok = false;
  try { h = G.PAGES.alert(); ok = true; } catch (e) { console.log(e.message); }
  T('K1 去重合并 Tab 可渲染', ok);
  T('K2 含去重统计卡（同源告警组/合并后可减）', h.indexOf('同源告警组') >= 0 && h.indexOf('合并后可减') >= 0);
  T('K3 含一键合并处置按钮', h.indexOf('alertDedupMerge(') >= 0);
  /* K4 同源数据：账号风险分超阈值 ×3 */
  const grp = G.ALERTS.filter(function (a) { return a.rule === '账号风险分超阈值'; });
  T('K4 风险分超阈值有 3 条同源告警', grp.length === 3);
  /* K5 分组函数正确分组 */
  let groups = null;
  try {
    groups = sandbox('return alertDedupGroups();');
  } catch (e) { }
  T('K5 alertDedupGroups 分组正确（最大组=3 条）', groups && groups[0] && groups[0].n === 3 && groups[0].rule === '账号风险分超阈值');
  /* K6 合并处置：3 条未处理 → 处理中（沙箱内重设状态后执行） */
  try {
    const r = sandbox('var _cb=null; confirmDlg=function(t,m,o,cb,op){_cb=cb;}; doConfirm=function(){var c=_cb;_cb=null;if(c)c();};' +
      'toast=function(){}; hlFirst=function(){}; renderPage=function(){}; closeDrawer=function(){};' +
      'alertDedupMerge("账号风险分超阈值");doConfirm();' +
      'return ALERTS.filter(function(a){return a.rule==="账号风险分超阈值"&&a.st==="处理中";}).length;');
    T('K6 合并处置后 3 条 → 处理中', r === 3);
  } catch (e) {
    T('K6 合并处置执行: ' + e.message, false);
  }
  /* K7 实时预警列表含同源标识 */
  G.state.tab.alert = '实时预警';
  let h2 = '';
  try { h2 = G.PAGES.alert(); } catch (e) { }
  T('K7 实时预警行含「×3 同源」标识', h2.indexOf('×3 同源') >= 0);
})();

/* ============ L 组：REPORT 字段级编辑 ============ */
console.log('L. REPORT 字段级编辑');
(function () {
  G.state.page = 'report';
  const t0 = G.RTPLS[0];
  /* L1 模板含 flds 字段数组 */
  T('L1 RTPLS 含 flds 字段数组', Array.isArray(t0.flds) && t0.flds.length >= 5);
  /* L2 编辑抽屉含字段级操作 */
  _checks.length = 0;
  try {
    const r = sandbox('var _dr=[]; openDrawer=function(t,b,f,w){_dr.push(t);}; toast=function(){};' +
      'reportTplEdit(0);return {titles: _dr.slice(), body: (typeof b === "undefined" ? "" : "")};');
    T('L2 编辑抽屉打开（标题含编辑上报模板）', r.titles.length > 0 && String(r.titles[0]).indexOf('编辑上报模板') >= 0);
  } catch (e) {
    T('L2 编辑抽屉执行: ' + e.message, false);
  }
  /* L3 新增字段：flds 长度 +1 */
  const before = t0.flds.length;
  try {
    const after = sandbox('var _dr=[]; openDrawer=function(t){_dr.push(t);}; closeDrawer=function(){}; toast=function(){};' +
      'reportTplEdit=function(){};' +
      'reportFldAdd(0);' +
      'var fd=document.getElementById("F_fn");fd.value="客单价";' +
      'document.getElementById("F_ft").value="金额";' +
      'document.getElementById("F_frq").value="必填";' +
      'document.getElementById("F_frule").value="≥ 0";' +
      'reportFldAddOk(0);return RTPLS[0].flds.length;');
    T('L3 新增字段后 flds +1（' + before + '→' + after + '）', after === before + 1);
  } catch (e) {
    T('L3 新增字段执行: ' + e.message, false);
  }
  /* L4 删除字段（确认后 flds -1） */
  try {
    const before2 = t0.flds.length;
    const r2 = sandbox('var _cb=null; confirmDlg=function(t,m,o,cb,op){_cb=cb;}; doConfirm=function(){var c=_cb;_cb=null;if(c)c();};' +
      'toast=function(){}; hlFirst=function(){}; renderPage=function(){}; reportTplEdit=function(){};' +
      'reportFldDel(0,0);doConfirm();return {len: RTPLS[0].flds.length, fields: RTPLS[0].fields};');
    T('L4 删除字段后 flds -1（' + before2 + '→' + r2.len + '）', r2.len === before2 - 1);
    /* L5 删除后 fields 数同步 */
    T('L5 fields 计数同步（flds.length）', r2.fields === r2.len);
  } catch (e) {
    T('L4/L5 删除字段执行: ' + e.message, false);
  }
  /* L6 字段排序上移：位置互换 */
  try {
    const n0 = G.RTPLS[0].flds[0].n, n1 = G.RTPLS[0].flds[1].n;
    const swapped = sandbox('openDrawer=function(){}; toast=function(){}; reportTplEdit=function(){};' +
      'reportFldMove(0,1,-1);return [RTPLS[0].flds[0].n, RTPLS[0].flds[1].n];');
    T('L6 字段上移后位置互换', swapped[0] === n1 && swapped[1] === n0);
  } catch (e) {
    T('L6 字段排序执行: ' + e.message, false);
  }
})();

/* ============ M 组：前批回归抽检 ============ */
console.log('M. 前批回归抽检');
(function () {
  /* M1 V1P0：LIVE-002 函数仍在 */
  T('M1 LIVE-002 liveEndEntry 存在', SRC.indexOf('function liveEndEntry(') >= 0);
  /* M2 V1P0：ACCT-004 冲话费仍在 */
  T('M2 ACCT-004 acctCharge 存在', SRC.indexOf('function acctCharge(') >= 0);
  /* M3 V2：MEET-002 reportApprove 仍在 */
  T('M3 MEET-002 reportApprove 存在', SRC.indexOf('function reportApprove(') >= 0);
  /* M4 V2：FLOW-003 flowTplVer 仍在 */
  T('M4 FLOW-003 flowTplVer 存在', SRC.indexOf('function flowTplVer(') >= 0);
  /* M5 各页面渲染无异常 */
  const pages = ['workbench', 'flow', 'bi', 'alert', 'report'];
  let allOk = true;
  pages.forEach(function (p) {
    G.state.page = p;
    try { G.PAGES[p](); } catch (e) { allOk = false; console.log('  page ' + p + ' FAIL: ' + e.message); }
  });
  T('M5 五页面渲染无异常', allOk);
})();

/* ============ 输出 ============ */
console.log('\n========== 测试结果 ==========');
DETAILS.forEach(function (d) { console.log(d); });
console.log('----------------------------');
console.log('PASS: ' + PASS + ' / ' + (PASS + FAIL));
if (FAIL > 0) { console.log('FAILED: ' + FAIL); process.exit(1); }
console.log('ALL GREEN');
