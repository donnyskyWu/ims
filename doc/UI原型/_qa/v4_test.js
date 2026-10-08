/* ============================================================
 * IMS UI 原型 — 第四批部分实现深化回归测试（v4）
 * 覆盖：N MEET-004 会议纪要 ×6 / O FIN-001+003 成本拆分+分成规则 ×8 / P COMP-002 竞品审核入库 ×8 / Q DM-001 数据字典 ×5 / M 前批回归抽检 ×6
 * 运行：node _qa/v4_test.js
 * 桩方法论：v1p0/v2/v3 累积 7 条经验 + v4 新增：
 *   经验 8：$ 走 document.querySelector（非 getElementById），元素桩须挂 querySelector；返回 null 可让 finRuleGrab 跳过抓取
 *   经验 9：每个 sandbox 独立求值 SRC，数据不跨沙箱——前置数据（待审核/已驳回项）必须在同一沙箱 expr 内先行构造
 * ============================================================ */
'use strict';
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'IMS-一体化管理系统-UI原型.html'), 'utf-8');
const blocks = [];
const re = /<script>([\s\S]*?)<\/script>/g;
let mm;
while ((mm = re.exec(html)) !== null) blocks.push(mm[1]);
const SRC = blocks.join('\n');

/* ============ 最小 DOM 桩（经验 10：每个沙箱用全新 document，防止 expr 内覆盖 querySelector 污染共享桩） ============ */
function makeDoc() {
  const _els = {};
  function _mk(id) {
    if (_els[id]) return _els[id];
    const el = {
      id: id, value: '', textContent: '', innerHTML: '', className: '', style: {}, disabled: false, type: 'text',
      children: [], parentNode: null,
      classList: { add: function () { }, remove: function () { }, toggle: function () { }, contains: function () { return false; } },
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
  return {
    getElementById: function (id) { return _mk(id); },
    querySelector: function (sel) { return _mk(String(sel).replace(/^#/, '')); },
    querySelectorAll: function () { return []; },
    createElement: function () { return _mk('el' + Math.random()); },
    addEventListener: function () { },
    body: _mk('body'),
  };
}
var setTimeout = function (fn) { fn(); return 0; };
var clearTimeout = function () { };

/* ============ 沙箱工具（经验 7/8/9/10） ============ */
function sandbox(expr, preset) {
  preset = preset || '';
  const run = new Function('document', 'setTimeout', 'clearTimeout', 'console', preset + SRC + '\n;' + expr);
  return run(makeDoc(), setTimeout, clearTimeout, console);
}
/* 通用桩包：confirm 立即回调 + toast 收集 + 抽屉收集 */
var STUB = 'var _cb=null,_ts=[],_dr=[];' +
  'confirmDlg=function(t,m,o,cb,op){_cb=cb; if(op&&op.onInput&&op.inputPh===undefined){}};' +
  'doConfirm=function(){var c=_cb;_cb=null;if(c){try{c();}catch(e){}}};' +
  'closeConfirm=function(){_cb=null;};' +
  'toast=function(m,t){_ts.push(String(m));};' +
  'openDrawer=function(t,b,f,w){_dr.push({t:t,b:b,f:f});};' +
  'closeDrawer=function(){};renderPage=function(){};hlFirst=function(){};formOk=function(){};formValidate=function(){return true;};';

/* ============ 断言工具 ============ */
let PASS = 0, FAIL = 0, DETAILS = [];
function T(name, cond) {
  if (cond) { PASS++; DETAILS.push('  ✓ ' + name); }
  else { FAIL++; DETAILS.push('  ✗ ' + name); }
}

/* ============================================================
 * N 组：MEET-004 会议纪要管理（MEETS 实际 9 条，id 形如 MT20260912-03）
 * ============================================================ */
console.log('N. MEET-004 会议纪要管理');
(function () {
  /* N1 函数族齐备 */
  const fns = ['meetDetail', 'meetMinGen', 'meetMinDone', 'meetMinManual', 'meetMinManualOk', 'meetMinArchive'];
  T('N1 MEET-004 函数族 6 个齐备', fns.every(function (f) { return SRC.indexOf('function ' + f + '(') >= 0; }));

  /* N2 已生成会议详情：纪要正文 + 决议时间线（MT20260911-05 为已生成） */
  let r2 = null;
  try {
    r2 = sandbox("meetDetail('MT20260911-05'); return { n: _dr.length, b: _dr.length ? _dr[0].b : '', t: _dr.length ? _dr[0].t : '' };", STUB);
  } catch (e) { }
  T('N2 已生成详情含纪要正文+决议', r2 && r2.n === 1 && r2.b.indexOf('纪要正文') >= 0 && r2.b.indexOf('决议事项') >= 0 && r2.t.indexOf('会议纪要') >= 0);

  /* N3 AI 转写中分支：模拟转写完成按钮（MT20260912-02 为 AI 转写中） */
  let r3 = null;
  try {
    r3 = sandbox("meetDetail('MT20260912-02'); return { b: _dr.length ? _dr[0].b : '', f: _dr.length ? _dr[0].f : '' };", STUB);
  } catch (e) { }
  T('N3 AI 转写中分支含模拟转写完成', r3 && (r3.b + r3.f).indexOf('模拟转写完成') >= 0 && r3.b.indexOf('转写中') >= 0);

  /* N4 转写完成 → 已生成 + minBody + 决议 1 项（MT20260912-03 为待生成） */
  let r4 = null;
  try {
    r4 = sandbox("meetMinGen('MT20260912-03'); doConfirm(); meetMinDone('MT20260912-03');" +
      "var m=MEETS.filter(function(x){return x.id==='MT20260912-03';})[0];" +
      "return { min:m.min, hasBody:!!(m.minBody&&m.minBody.length>10), dn:(m.decisions||[]).length };", STUB);
  } catch (e) { }
  T('N4 转写完成 → 已生成+minBody+决议', r4 && r4.min === '已生成' && r4.hasBody && r4.dn >= 1);

  /* N5 手动录入解析：事项；责任人；截止日（MT20260910-07 为待生成） */
  let r5 = null;
  try {
    r5 = sandbox("document.querySelector=function(s){var k=String(s).replace(/^#/,'');var v={value:''};if(k==='F_minbody')v={value:'会议结论：测试正文'};if(k==='F_mindec')v={value:'第一条决议；张三；09-30\\n第二条决议；李四；10-15'};return v;};" +
      "meetMinManualOk('MT20260910-07'); var m=MEETS.filter(function(x){return x.id==='MT20260910-07';})[0];" +
      "return { min:m.min, dn:(m.decisions||[]).length, d0:(m.decisions||[])[0]?m.decisions[0].d:'' };", STUB);
  } catch (e) { }
  T('N5 手动录入解析两条决议', r5 && r5.min === '已生成' && r5.dn === 2 && r5.d0.indexOf('第一条决议') >= 0);

  /* N6 归档 → 已归档只读（MT20260911-05 已生成） */
  let r6 = null;
  try {
    r6 = sandbox("meetMinArchive('MT20260911-05'); doConfirm(); var m=MEETS.filter(function(x){return x.id==='MT20260911-05';})[0]; return m.min;", STUB);
  } catch (e) { }
  T('N6 归档 → 已归档（只读）', r6 === '已归档');

  /* N6b 数据基线：MEETS 9 条 + 状态机三态齐备 */
  let r6b = null;
  try { r6b = sandbox("return { n: MEETS.length, st: MEETS.map(function(m){return m.min;}) };", ''); } catch (e) { }
  T('N6b MEETS 9 条三态齐备', r6b && r6b.n === 9 && ['待生成', 'AI 转写中', '已生成', '已归档'].every(function (s) { return r6b.st.indexOf(s) >= 0; }));
})();

/* ============================================================
 * O 组：FIN-001 成本拆分 + FIN-003 分成规则（finCostTab/finRuleTab 返回字符串）
 * ============================================================ */
console.log('O. FIN-001 成本拆分 + FIN-003 分成规则');
(function () {
  /* O1 FINCOSTS 6 条 + finCostTab 渲染（返回字符串） */
  let r1 = null;
  try {
    r1 = sandbox("var h = finCostTab(); return { n: FINCOSTS.length, h: h };", STUB);
  } catch (e) { }
  T('O1 FINCOSTS 6 条 + 成本单据 Tab 渲染', r1 && r1.n === 6 && r1.h.indexOf('FIN-001') >= 0 && r1.h.indexOf('已审核') >= 0 && r1.h.indexOf('CB20260918-012') >= 0);

  /* O2 成本审核（索引 5 为待审核）→ 全部已审核（BR-017） */
  let r2 = null;
  try {
    r2 = sandbox("finCostAudit(5); doConfirm(); return FINCOSTS.filter(function(c){return c.st==='已审核';}).length;", STUB);
  } catch (e) { }
  T('O2 成本审核 → 全部已审核', r2 === 6);

  /* O3 finCostAttach 计入本单联动（$ 闭包捕获沙箱 document 参数，覆盖其 querySelector 即可；finCalc 须桩掉避免 F_rev 空引用） */
  let r3 = null;
  try {
    r3 = sandbox("var _cost={value:'1000'}; document.querySelector=function(s){return String(s).indexOf('F_cost')>=0?_cost:{value:''};};" +
      "finCalc=function(){}; finCostAttach(0); return { v: _cost.value, ts: _ts.join('|') };", STUB);
  } catch (e) { }
  T('O3 计入本单联动累加', r3 && Number(r3.v) === 39000 && r3.ts.indexOf('已计入') >= 0);

  /* O4 成本录入 → FINCOSTS.unshift 待审核 */
  let r4 = null;
  try {
    r4 = sandbox("document.querySelector=function(s){var k=String(s).replace(/^#/,'');var v={value:''};if(k==='F_ctype')v={value:'坑位费'};if(k==='F_csid')v={value:'IMS202609100DY0131'};if(k==='F_camt')v={value:'5000'};if(k==='F_cnote')v={value:'测试说明'};return v;};" +
      "finCostAddSubmit(); return { st: FINCOSTS[0].st, type: FINCOSTS[0].type, amt: FINCOSTS[0].amt };", STUB);
  } catch (e) { }
  T('O4 成本录入 → 待审核入库', r4 && r4.st === '待审核' && r4.type === '坑位费' && r4.amt === 5000);

  /* O5 FINRULES 4 条三模式 + finRuleTab 渲染 */
  let r5 = null;
  try {
    r5 = sandbox("var h = finRuleTab(); return { n: FINRULES.length, modes: FINRULES.map(function(r){return r.mode;}), h: h };", STUB);
  } catch (e) { }
  T('O5 FINRULES 4 条三模式齐备', r5 && r5.n === 4 && r5.modes.indexOf('多方') >= 0 && r5.modes.indexOf('阶梯') >= 0 && r5.h.indexOf('SR-003') >= 0);

  /* O6 多方合计 >100% 拦截（querySelector 返回 null 让 grab 跳过，经验 8） */
  let r6 = null;
  try {
    r6 = sandbox("document.querySelector=function(){return null;};" +
      "var r=FINRULES.filter(function(x){return x.mode==='多方';})[0]; r.body=[{role:'主播',pct:60},{role:'运营',pct:50}]; var i=FINRULES.indexOf(r);" +
      "finRuleSave(i); return _ts.join('|');", STUB);
  } catch (e) { }
  T('O6 多方合计 >100% 拦截', r6 && r6.indexOf('超 100%') >= 0);

  /* O7 分成项删除至少保留 1 项 */
  let r7 = null;
  try {
    r7 = sandbox("document.querySelector=function(){return null;};" +
      "var r=FINRULES.filter(function(x){return x.mode==='多方';})[0]; var i=FINRULES.indexOf(r);" +
      "finRuleEdit(i); var n0=r.body.length; finRuleItemDel(i, r.body.length-1); finRuleItemDel(i, 0); finRuleItemDel(i, 0);" +
      "return { n0: n0, n: r.body.length, ts: _ts.join('|') };", STUB);
  } catch (e) { }
  T('O7 删除分成项至少保留 1 项', r7 && r7.n === 1 && r7.ts.indexOf('至少保留') >= 0);

  /* O8 新建规则 textarea 解析（主播，60 / 运营，40） */
  let r8 = null;
  try {
    r8 = sandbox("document.querySelector=function(s){var k=String(s).replace(/^#/,'');var v={value:''};if(k==='F_nrname')v={value:'新规则'};if(k==='F_nrbody')v={value:'主播，60\\n运营，40'};if(k==='F_nrmode')v={value:'固定比例'};return v;};" +
      "finRuleAddSubmit(); return { n: FINRULES.length, body: FINRULES[0].body, no: FINRULES[0].no };", STUB);
  } catch (e) { }
  T('O8 新建规则解析分成结构', r8 && r8.n === 5 && r8.body && r8.body.length === 2 && r8.body[0].pct === 60 && r8.body[0].role === '主播');
})();

/* ============================================================
 * P 组：COMP-002 竞品审核入库（沙箱独立，前置数据同沙箱构造，经验 9）
 * ============================================================ */
console.log('P. COMP-002 竞品审核入库');
(function () {
  const MKPEND = "COMPS.unshift({name:'审核测试',plat:'抖音',fans:'10 万',works:0,rate:'—',trend:[1,2,3,4,5,6,7,8,9,10],hot:'x',audit:'待审核'});";

  /* P1 存量 8 家默认已入库 */
  let r1 = null;
  try { r1 = sandbox("return COMPS.filter(function(c){return c.audit==='已入库';}).length;", ''); } catch (e) { }
  T('P1 存量 8 家默认已入库', r1 === 8);

  /* P2 compAddSubmit → 待审核（不直接入库） */
  let r2 = null;
  try {
    r2 = sandbox("document.querySelector=function(s){var k=String(s).replace(/^#/,'');var v={value:''};if(k==='F_name')v={value:'测试竞品A'};if(k==='F_plat')v={value:'抖音'};if(k==='F_fans')v={value:'10 万'};return v;};" +
      "compAddSubmit(); return { st: COMPS[0].audit, n: COMPS.length, hot: COMPS[0].hot };", STUB);
  } catch (e) { }
  T('P2 新增 → 待审核不直接入库', r2 && r2.st === '待审核' && r2.n === 9 && r2.hot.indexOf('审核通过后') >= 0);

  /* P3 卡片渲染含待审核标识 + 审核/驳回按钮 + BR-202 提示条 */
  let r3 = null;
  try {
    r3 = sandbox(MKPEND + "return PAGES.comp();", STUB);
  } catch (e) { }
  T('P3 卡片含待审核标识+审核/驳回按钮', r3 && r3.indexOf('待审核') >= 0 && r3.indexOf('审核通过') >= 0 && r3.indexOf('驳回') >= 0 && r3.indexOf('BR-202') >= 0);

  /* P4 审核通过 → 已入库 + 订阅监控 */
  let r4 = null;
  try {
    r4 = sandbox(MKPEND + "compAudit(0, 1); doConfirm(); return { st: COMPS[0].audit, hot: COMPS[0].hot, ts: _ts.join('|') };", STUB);
  } catch (e) { }
  T('P4 审核通过 → 已入库+监控已订阅', r4 && r4.st === '已入库' && r4.hot.indexOf('监控已订阅') >= 0 && r4.ts.indexOf('已入库') >= 0);

  /* P5 驳回 → 已驳回 + 驳回原因（withInput 输入框） */
  let r5 = null;
  try {
    r5 = sandbox("var _rej={value:'  账号非竞品  '}; confirmDlg=function(t,m,o,cb,op){_cb=cb; if(op&&op.onInput)op.onInput(_rej);};" +
      MKPEND + "compAudit(0, 0); doConfirm(); return { st: COMPS[0].audit, rejBy: COMPS[0].rejBy, ts: _ts.join('|') };", STUB);
  } catch (e) { }
  T('P5 驳回 → 已驳回+原因（trim）', r5 && r5.st === '已驳回' && r5.rejBy === '账号非竞品' && r5.ts.indexOf('驳回原因') >= 0);

  /* P6 已驳回卡片含「修改重新提交」+ 驳回原因展示 */
  let r6 = null;
  try {
    r6 = sandbox("COMPS.unshift({name:'驳回测试',plat:'抖音',fans:'1 万',works:0,rate:'—',trend:[1,2,3],hot:'x',audit:'已驳回',rejBy:'账号非竞品'}); return PAGES.comp();", STUB);
  } catch (e) { }
  T('P6 已驳回卡片含修改重新提交', r6 && r6.indexOf('修改重新提交') >= 0 && r6.indexOf('已驳回') >= 0 && r6.indexOf('账号非竞品') >= 0);

  /* P7 compResubmit → 重新进入待审核 + 清除驳回原因 */
  let r7 = null;
  try {
    r7 = sandbox("COMPS.unshift({name:'驳回测试',plat:'抖音',fans:'1 万',works:0,rate:'—',trend:[1,2,3],hot:'x',audit:'已驳回',rejBy:'账号非竞品'});" +
      "compResubmit(0); doConfirm(); return { st: COMPS[0].audit, hasRejBy: COMPS[0].rejBy === undefined };", STUB);
  } catch (e) { }
  T('P7 重新提交 → 待审核+清除驳回原因', r7 && r7.st === '待审核' && r7.hasRejBy);

  /* P8 confirmDlg 支持 withInput（cf_input 输入框） */
  T('P8 confirmDlg 支持 withInput 驳回原因输入', SRC.indexOf('withInput') >= 0 && SRC.indexOf('cf_input') >= 0 && SRC.indexOf('onInput') >= 0);
})();

/* ============================================================
 * Q 组：DM-001 数据字典抽屉
 * ============================================================ */
console.log('Q. DM-001 数据字典抽屉');
(function () {
  /* Q1 dcDict 函数 + DC 页按钮真实调用（toast 占位已移除） */
  T('Q1 dcDict 函数+按钮真实调用', SRC.indexOf('function dcDict(') >= 0 && SRC.indexOf("onclick=\"dcDict()\"") >= 0 && SRC.indexOf('数据字典 · 原型示意') < 0);

  /* Q2~Q4 抽屉内容 */
  let r = null;
  try {
    r = sandbox("dcDict(); return _dr[0];", STUB);
  } catch (e) { }
  T('Q2 抽屉标题+实体表分组', r && r.t === '数据字典' && r.b.indexOf('实体表清单') >= 0 && r.b.indexOf('ims_live_session') >= 0 && r.b.indexOf('ims_tenant') >= 0);
  T('Q3 主外键字典含穿透链路', r && r.b.indexOf('主外键字典') >= 0 && r.b.indexOf('ims_account.owner_id') >= 0 && r.b.indexOf('tenant_id') >= 0 && r.b.indexOf('ims_cost_bill.session_id') >= 0);
  T('Q4 场次 ID 编码规则（DM-003）', r && r.b.indexOf('场次 ID 编码规则') >= 0 && r.b.indexOf('IMS202609100DY0131') >= 0 && r.b.indexOf('3 位平台码') >= 0 && r.b.indexOf('4 位序列') >= 0);

  /* Q5 DC_DICT 结构（7 组 + 8 条外键） */
  let r5 = null;
  try { r5 = sandbox("return { g: DC_DICT.groups.length, fk: DC_DICT.fks.length, tbls: DC_DICT.groups.reduce(function(s,g){return s+g.tbls.length;},0) };", ''); } catch (e) { }
  T('Q5 DC_DICT 7 组 30 表 + 8 条外键', r5 && r5.g === 7 && r5.fk === 8 && r5.tbls === 30);
})();

/* ============================================================
 * M 组：前批回归抽检
 * ============================================================ */
console.log('M. 前批回归抽检');
(function () {
  /* M1 FLOW-002 看板仍可渲染（同沙箱设 tab） */
  let m1 = null;
  try {
    m1 = sandbox("state.tab.flow='看板视图'; return PAGES.flow();", STUB);
  } catch (e) { }
  T('M1 FLOW-002 看板回归', m1 && m1.indexOf('流转下一节点') >= 0);

  /* M2 BI-002 下钻状态机仍在 */
  T('M2 BI-002 biDrillDown/Up 函数在', SRC.indexOf('function biDrillDown(') >= 0 && SRC.indexOf('function biDrillUp(') >= 0);

  /* M3 ALERT-004 去重合并仍在 */
  T('M3 ALERT-004 去重函数在', SRC.indexOf('function alertDedupMerge(') >= 0);

  /* M4 REPORT flds 字段级编辑仍在 */
  let m4 = null;
  try { m4 = sandbox("return RTPLS.filter(function(t){return Array.isArray(t.flds);}).length;", ''); } catch (e) { }
  T('M4 REPORT flds 字段数组在', m4 !== null && m4 >= 3);

  /* M5 MEETS 数据基线 9 条 */
  let m5 = null;
  try { m5 = sandbox("return MEETS.length;", ''); } catch (e) { }
  T('M5 MEETS 9 条数据', m5 === 9);

  /* M6 dcDrill confirm 仍正常（无 opts 的标准调用不受 withInput 扩展影响） */
  let m6 = null;
  try {
    m6 = sandbox("dcDrill('ACCT'); return typeof _cb;", STUB);
  } catch (e) { }
  T('M6 dcDrill confirm 仍正常', m6 === 'function');
})();

/* ============ 输出结果 ============ */
console.log('\n========== 结果 ==========');
DETAILS.forEach(function (d) { console.log(d); });
console.log('\nPASS: ' + PASS + ' / ' + (PASS + FAIL));
if (FAIL > 0) { console.log('FAILED: ' + FAIL); process.exit(1); }
console.log('ALL_GREEN');
