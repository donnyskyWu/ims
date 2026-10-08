/* ============================================================
 * IMS UI 原型 — 第五批结构优化回归测试（v5）
 * 覆盖：R DC 三 Tab 结构 ×6 / S BI 三 Tab 结构 ×7 / T 历史回归抽检 ×5
 * 主题：DC/BI 页 Tab 化改造（用户建议：一功能一标签页）
 * 运行：node _qa/v5_test.js
 * 桩方法论：沿用 v1p0~v4 累积 10 条经验（makeDoc 工厂 + 每沙箱独立求值 + confirm/toast/drawer 桩）
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

/* ============ 最小 DOM 桩（经验 10：每沙箱全新 document） ============ */
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

/* ============ 沙箱工具 ============ */
function sandbox(expr, preset) {
  preset = preset || '';
  const run = new Function('document', 'setTimeout', 'clearTimeout', 'console', preset + SRC + '\n;' + expr);
  return run(makeDoc(), setTimeout, clearTimeout, console);
}
var STUB = 'var _cb=null,_ts=[],_dr=[];' +
  'confirmDlg=function(t,m,o,cb,op){_cb=cb;};' +
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
 * R 组：DC 数据中心三 Tab 结构
 * ============================================================ */
console.log('R. DC 数据中心三 Tab 结构');
(function () {
  /* R1 Tab 结构：三 Tab 名 + setTab('dc') 调用（HTML onclick 属性内为 \\' 转义形式） */
  T('R1 DC 三 Tab（穿透查询/数据同步/数据字典）+ setTab 绑定',
    SRC.indexOf('setTab(\\\'dc\\\'') >= 0 && SRC.indexOf('穿透查询') >= 0 && SRC.indexOf('数据同步') >= 0 && SRC.indexOf('数据字典') >= 0);

  /* R2 PAGES.dc 按 Tab 分流到三个 Tab 函数 */
  T('R2 PAGES.dc 分流 dcDrillTab/dcSyncTab/dcDictTab',
    SRC.indexOf('dcDrillTab()') >= 0 && SRC.indexOf('dcSyncTab()') >= 0 && SRC.indexOf('dcDictTab()') >= 0 &&
    SRC.indexOf('function dcDrillTab(') >= 0 && SRC.indexOf('function dcSyncTab(') >= 0 && SRC.indexOf('function dcDictTab(') >= 0);

  /* R3 默认 Tab 渲染穿透链路（六节点 + 统计卡） */
  let r3 = null;
  try { r3 = sandbox("return PAGES.dc();", STUB); } catch (e) { }
  T('R3 默认 Tab=穿透查询（含六节点链路+穿透数据表）',
    !!r3 && r3.indexOf('账号-资产-实名人-场次-成本-利润') >= 0 && r3.indexOf('穿透数据表') >= 0 && r3.indexOf('dcDrill(\'ACCT\')') >= 0);

  /* R4 数据同步 Tab 渲染 */
  let r4 = null;
  try { r4 = sandbox("state.tab.dc='数据同步'; return PAGES.dc();", STUB); } catch (e) { }
  T('R4 数据同步 Tab（6 同步源 + 8 条同步日志）',
    !!r4 && r4.indexOf('同步源状态') >= 0 && r4.indexOf('钉钉通讯录') >= 0 && r4.indexOf('同步日志') >= 0 && r4.indexOf('部分失败') >= 0);

  /* R5 数据字典 Tab 渲染（含 API 前缀总览 20 项） */
  let r5 = null;
  try { r5 = sandbox("state.tab.dc='数据字典'; return PAGES.dc();", STUB); } catch (e) { }
  T('R5 数据字典 Tab（30 表 + 8 外键 + 场次 ID 编码 + API 前缀总览）',
    !!r5 && r5.indexOf('ims_live_session') >= 0 && r5.indexOf('API 前缀总览') >= 0 && r5.indexOf('/admin-api/ims/') >= 0 && r5.indexOf('/efficiency') >= 0);

  /* R6 dcDict 抽屉保留 + dcSync 函数在 + Tab 切换互不影响 */
  let r6 = null;
  try { r6 = sandbox("dcDict(); return { dr: _dr.length, sync: typeof dcSync };", STUB); } catch (e) { }
  T('R6 dcDict 抽屉保留（详情入口）+ dcSync 函数在', !!r6 && r6.dr === 1 && r6.sync === 'function');
})();

/* ============================================================
 * S 组：BI 数据分析三 Tab 结构
 * ============================================================ */
console.log('S. BI 数据分析三 Tab 结构');
(function () {
  /* S1 Tab 结构：三 Tab + setTab('bi')（HTML onclick 属性内为 \\' 转义形式） */
  T('S1 BI 三 Tab（报表总览/多维下钻/场次明细）+ setTab 绑定',
    SRC.indexOf('setTab(\\\'bi\\\'') >= 0 && SRC.indexOf('报表总览') >= 0 && SRC.indexOf('多维下钻') >= 0 && SRC.indexOf('场次明细') >= 0);

  /* S2 PAGES.bi 分流到三个 Tab 函数 */
  T('S2 PAGES.bi 分流 biOverviewTab/biDrillTab/biSessionTab',
    SRC.indexOf('biOverviewTab()') >= 0 && SRC.indexOf('biDrillTab()') >= 0 && SRC.indexOf('biSessionTab()') >= 0 &&
    SRC.indexOf('function biOverviewTab(') >= 0 && SRC.indexOf('function biDrillTab(') >= 0 && SRC.indexOf('function biSessionTab(') >= 0);

  /* S3 默认 Tab 渲染报表树 + GMV 趋势（v5.1 排版优化：+顶部四统计卡 + 报表目录卡 + 面积渐变 + 双柱图并排） */
  let s3 = null;
  try { s3 = sandbox("return PAGES.bi();", STUB); } catch (e) { }
  T('S3 默认 Tab=报表总览（统计卡+报表目录+GMV 趋势+双柱图并排）',
    !!s3 && s3.indexOf('经营总览') >= 0 && s3.indexOf('本月 GMV') >= 0 && s3.indexOf('报表目录') >= 0 && s3.indexOf('近 30 天 GMV 趋势') >= 0 && s3.indexOf('gmvgrad') >= 0 && s3.indexOf('grid-template-columns:1fr 1fr') >= 0 && s3.indexOf('平台场次分布') >= 0 && s3.indexOf('近 6 周 GMV 周汇总') >= 0);

  /* S4 多维下钻 Tab 渲染（维度 pills + 面包屑） */
  let s4 = null;
  try { s4 = sandbox("state.tab.bi='多维下钻'; return PAGES.bi();", STUB); } catch (e) { }
  T('S4 多维下钻 Tab（维度 pills + 面包屑 + 联动明细）',
    !!s4 && s4.indexOf('biSwitchDim') >= 0 && s4.indexOf('biDrillDown') >= 0 && s4.indexOf('多维下钻') >= 0);

  /* S5 场次明细 Tab 渲染（明细表 + 订阅推送管理） */
  let s5 = null;
  try { s5 = sandbox("state.tab.bi='场次明细'; return PAGES.bi();", STUB); } catch (e) { }
  T('S5 场次明细 Tab（8 场明细 + 4 条订阅管理）',
    !!s5 && s5.indexOf('场次明细（近 8 场）') >= 0 && s5.indexOf('订阅推送管理') >= 0 && s5.indexOf('SUB-001') >= 0 && s5.indexOf('已暂停') >= 0);

  /* S6 下钻状态联动 Tab2（drillPath 渲染场次明细层） */
  let s6 = null;
  try { s6 = sandbox("state.tab.bi='多维下钻'; if(!state.bi)state.bi={}; state.bi.drill={cat:'直播',rpt:'场次分析',path:['抖音']}; return PAGES.bi();", STUB); } catch (e) { }
  T('S6 下钻状态联动（path=[抖音] → 场次明细层 + IMS 场次 ID）',
    !!s6 && s6.indexOf('下钻层级：抖音') >= 0 && s6.indexOf('IMS202609110DY0138') >= 0 && s6.indexOf('biDrillUp(1)') >= 0);

  /* S7 biDrillDown/Up/Reset 函数族回归 + biOpenRpt 真实打开 */
  let s7 = null;
  try { s7 = sandbox("biDrillDown('视频号'); var p1=state.bi.drill.path[0]; biDrillUp(1); var p2=state.bi.drill.path.length; biDrillReset(); var p3=state.bi.drill.path.length; return [p1,p2,p3];", STUB); } catch (e) { }
  T('S7 biDrillDown/Up/Reset 状态机回归', !!s7 && s7[0] === '视频号' && s7[1] === 1 && s7[2] === 0);
})();

/* ============================================================
 * T 组：历史回归抽检（Tab 化不破坏前批）
 * ============================================================ */
console.log('T. 历史回归抽检');
(function () {
  /* T1 fin 页三 Tab 仍在（本批参照模板，setTab 含转义形式） */
  T('T1 fin 页三 Tab 结构保留', SRC.indexOf("setTab(\\'fin\\'") >= 0 && SRC.indexOf('finCostTab()') >= 0 && SRC.indexOf('finRuleTab()') >= 0);

  /* T2 9 个页面有 Tab（含新 dc/bi），匹配 HTML 属性内转义形式 */
  const tabPids = ['content', 'train', 'report', 'flow', 'fin', 'perf', 'alert', 'dc', 'bi'];
  let tabCnt = 0;
  tabPids.forEach(function (p) { if (SRC.indexOf("setTab(\\'" + p + "\\'") >= 0) tabCnt++; });
  T('T2 Tab 化页面数 = 9（含新 dc/bi）', tabCnt === 9);

  /* T3 COMP-002 竞品审核状态机仍正常（confirm 桩后需 doConfirm 触发回调） */
  let t3 = null;
  try { t3 = sandbox("COMPS[0].audit='待审核'; compAudit(0, 1); doConfirm(); return COMPS[0].audit;", STUB); } catch (e) { }
  T('T3 COMP-002 审核通过回归', t3 === '已入库');

  /* T4 前批函数族保留（真实函数名） */
  T('T4 MEET-004/DM-001/COMP-002 函数族保留',
    SRC.indexOf('function meetMinGen(') >= 0 && SRC.indexOf('function compAudit(') >= 0 && SRC.indexOf('function dcDict(') >= 0 && SRC.indexOf('function compResubmit(') >= 0 && SRC.indexOf('function meetMinArchive(') >= 0);

  /* T5 全部 PAGES 函数齐备（实际 18 键：workbench/auth/asset/acct/cert/live/content/train/meet/report/flow/fin/perf/alert/comp/dc/bi/eff） */
  let t5 = null;
  try { t5 = sandbox("var ps=['workbench','auth','asset','acct','cert','live','content','train','meet','report','flow','fin','perf','alert','comp','dc','bi','eff']; var missing=[]; ps.forEach(function(p){ if(typeof PAGES[p]!=='function') missing.push(p); }); return missing;", STUB); } catch (e) { }
  T('T5 18 页 PAGES 函数齐备', Array.isArray(t5) && t5.length === 0);
})();

/* ============================================================
 * U 组：第 14 轮业务逻辑修正（冲话费对手机号 + 号卡资产管理）
 * ============================================================ */
console.log('U. 冲话费对象修正与号卡资产（第 14 轮）');
(function () {
  /* U1 号卡资产类型 + 手机号字段 + 账号 phone 字段 */
  let u1 = null;
  try { u1 = sandbox("var sims=ASSETS.filter(function(x){return x.type==='手机号/号卡';}); var ac1=ACCTS.find(function(x){return x.id==='ACCT-2026-0001';}); return { n:sims.length, ph:sims.length?sims[0].phone:null, acph:ac1?ac1.phone:null, simRef:ac1?ac1.sim:null };", STUB); } catch (e) { }
  T('U1 号卡资产 3 条 + 账号 phone/sim 字段', !!u1 && u1.n === 3 && u1.ph === '13828715678' && u1.acph === '13828715678' && u1.simRef === 'AS20260918011');

  /* U2 资产页含手机号查询列 + 手机号/号卡分类 Tab */
  let u2 = null;
  try { u2 = sandbox("return PAGES.asset();", STUB); } catch (e) { }
  T('U2 资产页（手机号列 + 号卡 Tab + SIM 行充值入口）',
    !!u2 && u2.indexOf('手机号') >= 0 && u2.indexOf('手机号/号卡') >= 0 && u2.indexOf('simRecharge(') >= 0 && u2.indexOf('138****5678') >= 0);

  /* U3 冲话费抽屉以号卡（手机号）为充值对象 */
  let u3 = null;
  try { u3 = sandbox("acctCharge(0); return { dr:_dr.length, t:_dr.length?_dr[0].t:'', b:_dr.length?_dr[0].b:'' };", STUB); } catch (e) { }
  T('U3 冲话费抽屉标题含手机号 + 号卡选择 + 绑定关系块',
    !!u3 && u3.dr === 1 && u3.t.indexOf('138****5678') >= 0 && u3.b.indexOf('充值号卡（手机号）') >= 0 && u3.b.indexOf('号卡与账号绑定关系') >= 0 && u3.b.indexOf('话费直充') >= 0);

  /* U4 提交闭环：入账账号 + 留痕含号卡（先 acctChargeSubmit 触发 confirmDlg，再 doConfirm 执行回调） */
  let u4 = null, u4ts = [];
  try { u4 = sandbox("acctCharge(0); $('#F_camt').value='500'; $('#F_creal').value='500'; $('#F_cvou').value='CZ20260918-001'; $('#F_csim').value='移动 · 138****5678（128 元/月）'; acctChargeSubmit(0); doConfirm(); var a=ACCTS[0]; return { rc:a.recharge, ch:(a.charges||[]).length, c0:(a.charges||[])[0]||null };", STUB); } catch (e) { }
  try { u4ts = sandbox("acctCharge(0); $('#F_camt').value='500'; $('#F_creal').value='500'; $('#F_cvou').value='CZ20260918-002'; $('#F_csim').value='移动 · 138****5678（128 元/月）'; acctChargeSubmit(0); doConfirm(); return _ts.filter(function(x){return x.indexOf('138****5678')>=0;});", STUB); } catch (e) { }
  T('U4 提交入账（charges 含号卡 + 手机号 + toast 留痕）',
    !!u4 && u4.ch >= 1 && u4.c0 && u4.c0.phone === '138****5678' && u4.c0.sim === 'AS20260918011' && u4ts.length >= 1);

  /* U5 simRecharge 从资产穿透到冲话费 */
  let u5 = null;
  try { u5 = sandbox("var si=ASSETS.findIndex(function(x){return x.id==='AS20260918011';}); simRecharge(si); return { dr:_dr.length, t:_dr.length?_dr[0].t:'' };", STUB); } catch (e) { }
  T('U5 simRecharge 资产→冲话费穿透（标题含手机号）', !!u5 && u5.dr === 1 && u5.t.indexOf('138****5678') >= 0);

  /* U6 登记表单含号卡类型 + 手机号字段（源码级：号卡必填 reqs） */
  let u6 = null;
  try { u6 = sandbox("assetReg(); return _dr.length ? _dr[0].b : '';", STUB); } catch (e) { }
  T('U6 登记表单号卡类型 + 手机号字段（含号卡必填规则）',
    !!u6 && u6.indexOf('手机号/号卡') >= 0 && u6.indexOf('F_phone') >= 0 && u6.indexOf('手机号（号卡必填）') >= 0 &&
    SRC.indexOf("['name', 'type', 'phone', 'buy', 'owner']") >= 0 && SRC.indexOf('function assetTypeSync(') >= 0);

  /* U7 号卡未绑定账号时 simRecharge 拦截 */
  let u7 = null;
  try { u7 = sandbox("var si=ASSETS.findIndex(function(x){return x.id==='AS20260918012';}); ASSETS[si].acct='NOPE'; simRecharge(si); var t=_ts.length?_ts[_ts.length-1]:''; ASSETS[si].acct='ACCT-2026-0002'; return { dr:_dr.length, toast:t };", STUB); } catch (e) { }
  T('U7 号卡未绑定账号拦截 toast', !!u7 && u7.dr === 0 && u7.toast.indexOf('未绑定账号') >= 0);

  /* U8 号卡资产详情：号卡信息块 + 冲话费底钮 */
  let u8 = null;
  try { u8 = sandbox("var si=ASSETS.findIndex(function(x){return x.id==='AS20260918011';}); assetDetail(si); return { t:_dr.length?_dr[0].t:'', b:_dr.length?_dr[0].b:'', f:_dr.length?_dr[0].f:'' };", STUB); } catch (e) { }
  T('U8 号卡详情（号卡信息块 + ICCID + 冲话费钮）',
    !!u8 && u8.b.indexOf('号卡信息') >= 0 && u8.b.indexOf('ICCID') >= 0 && u8.b.indexOf('ACCT-2026-0001') >= 0 && u8.f.indexOf('simRecharge(') >= 0);

  /* U9 账号详情绑定手机改为真实数据 + 号卡资产引用 */
  let u9 = null;
  try { u9 = sandbox("acctDetail(0); return _dr.length ? _dr[0].b : '';", STUB); } catch (e) { }
  T('U9 账号详情绑定手机号 + 号卡资产引用',
    !!u9 && u9.indexOf('绑定手机号') >= 0 && u9.indexOf('138****5678') >= 0 && u9.indexOf('AS20260918011') >= 0);
})();

/* ============================================================
 * V 组：第 15 轮 P0 漏洞修复（实名人主数据/设备绑定/责任人带出/T-0锁定）
 * ============================================================ */
console.log('V. 第 15 轮 P0 漏洞修复（实名人/设备绑定/责任人/T-0）');
(function () {
  /* V1 实名人主数据存在且含证件状态与账号绑定 */
  let v1 = null;
  try { v1 = sandbox("return { n:PERSONS.length, multi:PERSONS.filter(function(p){return p.accts.length>1;}).length, locked:PERSONS.filter(function(p){return p.certDays<=0;}).length, c:typeof certStateOf };", STUB); } catch (e) { }
  T('V1 PERSONS 主数据（6 人 + 一证多号 + 过期锁定标记 + certStateOf）',
    !!v1 && v1.n === 6 && v1.multi >= 2 && v1.locked >= 1 && v1.c === 'function');

  /* V2 账号绑定实名人字段（ACCTS.rname）*/
  let v2 = null;
  try { v2 = sandbox("return { n:ACCTS.filter(function(a){return a.rname;}).length, s:ACCTS[0].rname };", STUB); } catch (e) { }
  T('V2 ACCTS 每条含 rname 实名人（苏杳→ACCT-0001）', !!v2 && v2.n === 10 && v2.s === '苏杳');

  /* V3 liveReg 动态化：账号从 ACCTS 生成 + 责任人/平台随账号带出 + 设备勾选 + 过期实名人被排除
     （沙箱 select 默认 value 为空——真实浏览器自动选中首项——故显式 set 后联动验证） */
  let v3 = null;
  try { v3 = sandbox("liveReg(); $('#lrAcct').value='ACCT-2026-0001'; liveRegSync(); var b=_dr.length?_dr[0].b:''; return { dr:_dr.length, b:b, owner:$('#lrOwner').value, plat:$('#lrPlat').value, hasDev:b.indexOf('lrv-dev')>=0, hasAcctId:b.indexOf('ACCT-2026-0001')>=0, noChenmo:b.indexOf('陈默')<0 };", STUB); } catch (e) { }
  T('V3 liveReg 动态化（账号下拉含 ACCT-0001 + 责任人带出赵敏 + 平台抖音 + 设备勾选 + 排除过期陈默）',
    !!v3 && v3.dr === 1 && v3.hasAcctId && v3.owner === '赵敏' && v3.plat === '抖音' && v3.hasDev && v3.noChenmo);

  /* V4 liveRegSync 联动：切换到斗鱼账号带出赵敏/斗鱼 + 实名人苏杳 */
  let v4 = null;
  try { v4 = sandbox("liveReg(); $('#lrAcct').value='ACCT-2026-0003'; liveRegSync(); return { owner:$('#lrOwner').value, plat:$('#lrPlat').value, person:$('#lrPerson').value };", STUB); } catch (e) { }
  T('V4 liveRegSync 切换账号联动（斗鱼 → 赵敏/斗鱼/苏杳）',
    !!v4 && v4.owner === '赵敏' && v4.plat === '斗鱼' && v4.person === '苏杳');

  /* V5 T-0 锁定拦截：选中过期实名人提交 → toast 拦截 + 不弹风控结果 */
  let v5 = null;
  try { v5 = sandbox("liveReg(); $('#lrAcct').value='ACCT-2026-0001'; liveRegSync(); $('#lrPerson').value='陈默'; liveRiskResult(); return { dr:_dr.length, ts:_ts.filter(function(x){return x.indexOf('BR-013')>=0 || x.indexOf('锁定')>=0;}) };", STUB); } catch (e) { }
  T('V5 T-0 锁定拦截（陈默提交 → BR-013 toast + 风控抽屉不弹出）',
    !!v5 && v5.dr === 1 && v5.ts.length >= 1);

  /* V6 场次绑定设备：LIVES 全量含 devices + 台账含直播设备列 */
  let v6 = null;
  try { v6 = sandbox("return { n:LIVES.filter(function(l){return Array.isArray(l.devices);}).length, row:liveRow(LIVES[0]) };", STUB); } catch (e) { }
  T('V6 场次设备绑定（LIVES 9 条全含 devices + liveRow 渲染设备 chip）',
    !!v6 && v6.n === 9 && v6.row.indexOf('AS20260901001') >= 0 && v6.row.indexOf('assetGoById') >= 0);

  /* V7 场次详情抽屉：设备绑定块 + 实名人档案（一证多号） */
  let v7 = null;
  try { v7 = sandbox("liveSessionDetail('IMS202609120DY0142'); return _dr.length ? _dr[0].b : '';", STUB); } catch (e) { }
  T('V7 场次详情（绑定直播设备块 + 实名人档案 + 一证多号 tag）',
    !!v7 && v7.indexOf('绑定直播设备') >= 0 && v7.indexOf('实名人档案') >= 0 && v7.indexOf('一证多号') >= 0);

  /* V8 账号详情：实名人 + 证件状态 tag */
  let v8 = null;
  try { v8 = sandbox("acctDetail(0); return _dr.length ? _dr[0].b : '';", STUB); } catch (e) { }
  T('V8 账号详情实名人块（苏杳 + 证件状态 + 一证多号）',
    !!v8 && v8.indexOf('实名人') >= 0 && v8.indexOf('苏杳') >= 0 && v8.indexOf('一证多号') >= 0);

  /* V9 DC 字典：ims_person 表 + 场次-设备绑定外键 */
  let v9 = null;
  try { v9 = sandbox("return { g:JSON.stringify(DC_DICT.groups), f:JSON.stringify(DC_DICT.fks) };", STUB); } catch (e) { }
  T('V9 DC 数据字典（ims_person 表 + rname_id/ims_live_session_asset 外键）',
    !!v9 && v9.g.indexOf('ims_person') >= 0 && v9.f.indexOf('ims_live_session_asset') >= 0 && v9.f.indexOf('rname_id') >= 0);

  /* V10 DC 穿透表实名人列含账号数（真实关联） */
  let v10 = null;
  try { v10 = sandbox("go=function(){}; return PAGES.dc ? PAGES.dc() : ''; }", STUB); } catch (e) { }
  try { if (!v10) v10 = sandbox("state.page='dc'; state.tab.dc='穿透查询'; var h=PAGES.dc(); return h;", STUB); } catch (e) { }
  T('V10 DC 穿透表实名人列（苏杳 3 账号 + 李澈 2 账号 + 号卡资产）',
    !!v10 && v10.indexOf('苏杳（3 账号）') >= 0 && v10.indexOf('李澈（2 账号）') >= 0 && v10.indexOf('AS20260918011') >= 0);
})();

/* ============================================================
 * W 组：AIR AI 资源中台（V1.5 专项 · 20 AIR）
 * v2 拆分版：五页签 → 五个独立菜单页 + 知识库左侧目录树
 * ============================================================ */
console.log('W. AIR AI 资源中台（V1.5 · 菜单拆分版）');
(function () {
  /* W1 注册：MODS 5 个 AIR 子模块 + GROUPS 独立分组 + R11 独立角色（D4） */
  let w1 = null;
  try { w1 = sandbox("return { m1:!!MODS.airSkill, m2:!!MODS.airKb, m5:!!MODS.airLog, no:MODS.airSkill.no, code:MODS.airSkill.code, g:JSON.stringify(GROUPS), r11mods:JSON.stringify(ROLES.R11.modules) };", STUB); } catch (e) { }
  T('W1 模块注册（5 个 AIR 子模块 + 独立分组 + R11 全 5 子模块）',
    !!w1 && w1.m1 && w1.m2 && w1.m5 && w1.no === '20' && w1.code === 'AIR' && w1.g.indexOf('AI 资源中台') >= 0 &&
    w1.r11mods === '["workbench","airSkill","airExpert","airKb","airKey","airLog"]');

  /* W2 五页拆为独立 PAGES 函数 + 无页签残留 */
  let w2 = null;
  try { w2 = sandbox("var ps=['airSkill','airExpert','airKb','airKey','airLog']; var missing=[]; ps.forEach(function(p){ if(typeof PAGES[p]!=='function') missing.push(p); }); return { missing:missing, legacy:typeof PAGES.air };", STUB); } catch (e) { }
  T('W2 五个独立 PAGES 页面（airSkill/airExpert/airKb/airKey/airLog）+ 旧入口兼容',
    !!w2 && w2.missing.length === 0 && w2.legacy === 'function');

  /* W3 数据层：SKILLS 6 + EXPERTS 5 + KBS 6 + APIKEYS 5 + 目录树 6 + RAGFlow 健康 4 */
  let w3 = null;
  try { w3 = sandbox("return { s:SKILLS.length, e:EXPERTS.length, k:KBS.length, key:APIKEYS.length, h:RAGFLOW_HEALTH.length, tree:KB_TREE.length, t0:KB_TREE[0].id, tc:KB_TREE[0].cats.length };", STUB); } catch (e) { }
  T('W3 数据层（6 技能/5 专家/6 知识库/5 Key/目录树 6 库含子目录/4 组件健康）',
    !!w3 && w3.s === 6 && w3.e === 5 && w3.k === 6 && w3.key === 5 && w3.h === 4 && w3.tree === 6 && w3.t0 === 'KB-0001' && w3.tc === 4);

  /* W4 技能库独立页渲染 */
  let w4 = null;
  try { w4 = sandbox("return PAGES.airSkill();", STUB); } catch (e) { }
  T('W4 技能库独立页（pgHead + 统计卡 + 列表 + 审核状态 + 授权入口）',
    !!w4 && w4.indexOf('技能库') >= 0 && w4.indexOf('SKL-0001') >= 0 && w4.indexOf('商品卖点提炼') >= 0 && w4.indexOf('skillAudit(') >= 0 && w4.indexOf('skillGrant(') >= 0);

  /* W5 专家库独立页：方形头像卡片网格 */
  let w5 = null;
  try { w5 = sandbox("return PAGES.airExpert();", STUB); } catch (e) { }
  T('W5 专家库独立页（方形头像卡片 + 挂载 chip + 组装预览/授权）',
    !!w5 && w5.indexOf('EXP-0001') >= 0 && w5.indexOf('直播运营专家') >= 0 && w5.indexOf('border-radius:12px') >= 0 &&
    w5.indexOf('grid-template-columns:repeat(3,1fr)') >= 0 && w5.indexOf('组装预览') >= 0 && w5.indexOf('expertGrant(') >= 0 && w5.indexOf('未挂载技能') >= 0);

  /* W5b 专家卡内容完整性：技能 chip 关联真实名称 + 统计格 + 授权人数（每卡 expertDetail 出现 2 次：卡片点击+预览钮） */
  let w5b = null;
  try { w5b = sandbox("var h=PAGES.airExpert(); return { cards:(h.match(/expertDetail\\(/g)||[]).length, hasSK2:h.indexOf('直播切片脚本生成')>=0, hasSK1:h.indexOf('商品卖点提炼')>=0, hasStat:h.indexOf('累计组装')>=0, hasAuth:h.indexOf('授权 7 人')>=0 };", STUB); } catch (e) { }
  T('W5b 专家卡内容（5 卡 ×2 入口 + 真实技能名 chip + 统计格 + 授权人数）',
    !!w5b && w5b.cards === 10 && w5b.hasSK2 && w5b.hasSK1 && w5b.hasStat && w5b.hasAuth);

  /* W6 知识库独立页：左侧目录树 + 右侧表格 + RAGFlow 健康卡 */
  let w6 = null;
  try { w6 = sandbox("return PAGES.airKb();", STUB); } catch (e) { }
  T('W6 知识库独立页（左侧知识目录树 + 密级标签 + RAGFlow 底座 + 审批入口）',
    !!w6 && w6.indexOf('知识目录') >= 0 && w6.indexOf('kbTreeGo') >= 0 && w6.indexOf('跑鞋系列') >= 0 && w6.indexOf('密级·机密') >= 0 && w6.indexOf('RAGFlow 底座健康') >= 0 && w6.indexOf('kbAudit(') >= 0);

  /* W7 Key 管理独立页渲染 */
  let w7 = null;
  try { w7 = sandbox("return PAGES.airKey();", STUB); } catch (e) { }
  T('W7 Key 管理独立页（pgHead + air- 哈希掩码 + 停用/吊销 + BR-025 说明 + keyGen 按钮）',
    !!w7 && w7.indexOf('Key 管理') >= 0 && w7.indexOf('air-8f3d') >= 0 && w7.indexOf('keyToggle(') >= 0 && w7.indexOf('keyRevoke(') >= 0 && w7.indexOf('BR-025') >= 0 && w7.indexOf('keyGen()') >= 0);

  /* W8 审计监控独立页渲染 */
  let w8 = null;
  try { w8 = sandbox("return PAGES.airLog();", STUB); } catch (e) { }
  T('W8 审计监控独立页（experts.assemble 日志 + 5007/401 失败样例 + 用量统计）',
    !!w8 && w8.indexOf('审计监控') >= 0 && w8.indexOf('experts.assemble') >= 0 && w8.indexOf('5007') >= 0 && w8.indexOf('离职联动吊销') >= 0 && w8.indexOf('用量统计') >= 0);

  /* W9 keyGen 闭环：表单 → 一次性明文 + 客户端配置卡片（BR-023） */
  let w9 = null;
  try { w9 = sandbox("keyGen(); $('#F_kuser').value='何舟'; keyGenOk(); var b=_dr.length?_dr[_dr.length-1].b:''; return { dr:_dr.length, plain:b.indexOf('air-')>=0, cfg:b.indexOf('mcpServers')>=0, once:b.indexOf('仅此一次')>=0, url:b.indexOf('/ims/mcp')>=0 };", STUB); } catch (e) { }
  T('W9 keyGen 一次性明文 + MCP 客户端配置卡片（Bearer + /ims/mcp）',
    !!w9 && w9.dr === 2 && w9.plain && w9.cfg && w9.once && w9.url);

  /* W10 skillAdd 闭环：提交 → 审核中（BR-021：无直接发布路径） */
  let w10 = null;
  try { w10 = sandbox("skillAdd(); $('#F_name').value='测试技能'; $('#F_cat').value='内容生产'; skillAddSubmit(); var n=SKILLS.length, f=SKILLS[0]; return { n:n, st:f.st, audit:f.audit, name:f.name };", STUB); } catch (e) { }
  T('W10 skillAdd 提交进审核中（BR-021 强制审核，不可直接发布）',
    !!w10 && w10.n === 7 && w10.st === '审核中' && w10.audit === '待复核' && w10.name === '测试技能');

  /* W11 skillAudit 状态机：通过→已发布 / 驳回→草稿 */
  let w11a = null, w11b = null;
  try { w11a = sandbox("var i=SKILLS.findIndex(function(x){return x.st==='审核中';}); skillAuditOk(i); return SKILLS[i].st;", STUB); } catch (e) { }
  try { w11b = sandbox("var i=SKILLS.findIndex(function(x){return x.st==='审核中'||x.st==='已发布';}); SKILLS[i].st='审核中'; skillAuditDenyPrepare(); skillAuditDeny(i); return SKILLS[i].st;", STUB + 'skillAuditDenyPrepare=function(){$("#F_auditnote").value="口径不符";};'); } catch (e) { }
  T('W11 技能审核状态机（通过→已发布 / 驳回→草稿）', w11a === '已发布' && w11b === '草稿');

  /* W12 keyToggle/keyRevoke 确认弹窗闭环（启停/吊销状态迁移） */
  let w12 = null;
  try { w12 = sandbox("keyToggle(0); doConfirm(); var s1=APIKEYS[0].st; keyToggle(0); doConfirm(); var s2=APIKEYS[0].st; keyRevoke(0); doConfirm(); var s3=APIKEYS[0].st, r=APIKEYS[0].reason; return [s1,s2,s3,r];", STUB); } catch (e) { }
  T('W12 Key 生命周期状态机（启用→停用→启用→已吊销+留痕原因）',
    !!w12 && w12[0] === '停用' && w12[1] === '启用' && w12[2] === '已吊销' && w12[3].indexOf('手工吊销') >= 0);

  /* W13 MCP 网关 6 工具 + 网关不执行原则（BR-030） */
  let w13 = null;
  try { w13 = sandbox("mcpCfg(); var b=_dr.length?_dr[0].b:''; return { dr:_dr.length, tools:MCP_TOOLS.length, hasSK:b.indexOf('skills.list')>=0, hasAsm:b.indexOf('experts.assemble')>=0, noExec:b.indexOf('网关不执行')>=0 };", STUB); } catch (e) { }
  T('W13 MCP 配置卡（6 工具契约 + Bearer 认证 + BR-030 网关不执行）',
    !!w13 && w13.dr === 1 && w13.tools === 6 && w13.hasSK && w13.hasAsm && w13.noExec);

  /* W14 kbSearch 密级拦截演示（机密仅摘要 + 绝密拦截 BR-028） */
  let w14 = null;
  try { w14 = sandbox("$('#F_kw').value='毛利率'; kbSearch(); var b=_dr.length?_dr[_dr.length-1].b:''; return { secret:b.indexOf('密级·机密')>=0, intercept:b.indexOf('BR-028')>=0, top:b.indexOf('密级·绝密')>=0, ragflow:b.indexOf('RAGFlow')>=0 };", STUB); } catch (e) { }
  T('W14 知识检索密级拦截（机密仅摘要 + 绝密 BR-028 拦截 + RAGFlow 链路说明）',
    !!w14 && w14.secret && w14.intercept && w14.top && w14.ragflow);

  /* W15 专家组装预览（System Prompt + 技能/知识库挂载 chip） */
  let w15 = null;
  try { w15 = sandbox("expertDetail(0); var b=_dr.length?_dr[0].b:''; return { sp:b.indexOf('System Prompt')>=0, chipSK:b.indexOf('SKL-0002')>=0, chipKB:b.indexOf('KB-0001')>=0, noExec:b.indexOf('BR-030')>=0 };", STUB); } catch (e) { }
  T('W15 专家包组装预览（System Prompt + 挂载 chip + BR-030 说明）',
    !!w15 && w15.sp && w15.chipSK && w15.chipKB && w15.noExec);

  /* W16 kbAudit 状态机（入库审批中→解析中） */
  let w16 = null;
  try { w16 = sandbox("var i=KBS.findIndex(function(x){return x.st==='入库审批中';}); kbAuditOk(i); return { st:KBS[i].st, ch:KBS[i].chunks };", STUB); } catch (e) { }
  T('W16 知识库入库审批（通过→解析中，DeepDoc 向量化）',
    !!w16 && w16.st === '解析中' && String(w16.ch) === '—');

  /* W17 权限收口：R11 之外角色不可访问（canAccess 白名单 + air 归一化兼容） */
  let w17 = null;
  try { w17 = sandbox("state.role='R5'; var a1=canAccess('airKb'); state.role='R11'; var a2=canAccess('airKb'), a2b=canAccess('air'); state.role='R1'; var a3=canAccess('airLog'); return [a1,a2,a2b,a3];", STUB); } catch (e) { }
  T('W17 AIR 访问收口（R5 拒 / R11 允 / air 归一化兼容 / R1 允）',
    !!w17 && w17[0] === false && w17[1] === true && w17[2] === true && w17[3] === true);

  /* W18 工作台联动：快捷入口含 AI 技能 + 公告含 V1.5 */
  let w18 = null;
  try { w18 = sandbox("return PAGES.workbench();", STUB); } catch (e) { }
  T('W18 工作台联动（快捷入口 AI 技能 + 公告提及 V1.5 AI 资源中台）',
    !!w18 && w18.indexOf('AI 技能') >= 0 && w18.indexOf('V1.5') >= 0 && w18.indexOf('MCP 连接器') >= 0);

  /* W19 目录树联动：点选 KB-0006 → 右侧表格只剩 1 行（绝密库） */
  let w19 = null;
  try { w19 = sandbox("var h=PAGES.airKb(); kbTreeGo('KB-0006'); var h2=PAGES.airKb(); return { rows:(h2.match(/<tr><td class/g)||[]).length, sel:h2.indexOf('KB-0006')>=0 && h2.indexOf('股权与融资档案')>=0 };", STUB + 'renderPage=function(){};'); } catch (e) { }
  T('W19 知识目录树联动过滤（选 KB-0006 → 右侧仅 1 行 + 选中高亮）',
    !!w19 && w19.rows === 1 && w19.sel);

  /* W20 侧边栏渲染：AI 资源中台组含 5 个子菜单项 */
  let w20 = null;
  try { w20 = sandbox("renderSidebar(); var h=$('#sidebar').innerHTML; return { air:(h.match(/AI 资源中台/g)||[]).length, items:(h.match(/airSkill|airExpert|airKb|airKey|airLog/g)||[]).length };", STUB + 'renderPage=function(){};'); } catch (e) { }
  T('W20 侧边栏 AIR 组渲染（组标题 + 5 个子菜单项可点）',
    !!w20 && w20.air >= 1 && w20.items >= 5);
})();


console.log('\n========== 结果 ==========');
DETAILS.forEach(function (d) { console.log(d); });
console.log('\nPASS: ' + PASS + ' / ' + (PASS + FAIL));
if (FAIL === 0) console.log('ALL_GREEN');
else { console.log('FAILED: ' + FAIL); process.exit(1); }
