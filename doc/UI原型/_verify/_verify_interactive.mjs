import fs from 'fs';

const FILE = 'D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html';
const html = fs.readFileSync(FILE, 'utf8');
const blocks = [];
const re = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
let m; while ((m = re.exec(html))) { if (m[1].trim()) blocks.push(m[1]); }
const body = blocks.join('\n;\n');

function mkEl() {
  const cls = new Set();
  return {
    _html: '', style: {}, children: [],
    classList: { add() { for (const c of arguments) cls.add(c); }, remove() { for (const c of arguments) cls.delete(c); },
      toggle(c, f) { const on = f === undefined ? !cls.has(c) : !!f; on ? cls.add(c) : cls.delete(c); return on; }, contains(c) { return cls.has(c); } },
    get innerHTML() { return this._html; }, set innerHTML(v) { this._html = String(v); },
    textContent: '', value: '', scrollTop: 0, checked: false, disabled: false,
    contains() { return false; }, focus() {}, blur() {}, click() {}, remove() {},
    querySelector() { return mkEl(); }, querySelectorAll() { return []; },
    getAttribute() { return null; }, setAttribute() {}, removeAttribute() {},
    addEventListener() {}, removeEventListener() {}, dispatchEvent() {},
    appendChild(c) { return c; }, removeChild() {}, insertBefore() {},
    closest() { return mkEl(); }, matches() { return false; },
    getBoundingClientRect() { return { top: 0, left: 0, width: 0, height: 0, bottom: 0, right: 0 }; },
    insertAdjacentHTML() {}, replaceChildren() {},
  };
}
const idStore = {};
const document = {
  getElementById(id) { return idStore[id] || (idStore[id] = mkEl()); },
  querySelector() { return mkEl(); }, querySelectorAll() { return []; },
  createElement() { return mkEl(); }, createDocumentFragment() { return mkEl(); },
  addEventListener() {}, removeEventListener() {}, body: mkEl(), documentElement: mkEl(), head: mkEl(),
  write() {}, execCommand() { return true; },
};
const store = {};
const localStorage = { getItem: k => (store[k] === undefined ? null : store[k]), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; }, clear: () => { for (const k in store) delete store[k]; } };
const window = { addEventListener() {}, removeEventListener() {}, matchMedia: () => ({ matches: false, addListener() {} }), localStorage, location: { href: '', hash: '', reload() {} }, scrollTo() {}, open() {}, print() {}, getComputedStyle: () => ({}), document };
const navigator = { userAgent: 'node', clipboard: { writeText() {} } };
const location = window.location;
const alert = () => {}, confirm = () => true, prompt = () => '', getComputedStyle = () => ({});

// ---- 提取源码中所有 setTab('key','label') / state.tab.X='label' 组合（供全模块 Tab 矩阵）----
const tabPairs = [];
{
  const seenTab = new Set();
  const push = (k, v) => { const key = k + '|' + v; if (!seenTab.has(key)) { seenTab.add(key); tabPairs.push([k, v]); } };
  const reTab = /setTab\(\\?'([A-Za-z0-9_]+)\\?'\s*,\s*\\?'([^'\\]+)\\?'/g;
  const reTab2 = /state\.tab\.([A-Za-z0-9_]+)\s*=\s*\\?'([^'\\]+)\\?'/g;
  let tm;
  while ((tm = reTab.exec(html))) push(tm[1], tm[2]);
  while ((tm = reTab2.exec(html))) push(tm[1], tm[2]);
}
console.log('setTab pairs extracted:', tabPairs.length);

const probe = `
;return (function(){
  var out = { pages:[], aliases:[], tabs:[], drawers:[], errors:[] };
  var keys = Object.keys(PAGES);
  out.pageCount = keys.length;
  keys.forEach(function(k){
    if (!MODS[k]) { out.aliases.push(k); return; }
    try { state.page = k; var s = PAGES[k](); if (typeof s !== 'string') out.errors.push('PAGE ' + k + ' : returned ' + typeof s); }
    catch(e){ out.errors.push('PAGE ' + k + ' : ' + e.message); }
  });
  // ---- CONTENT tabs ----
  function T(name, fn){ try { var r = fn(); if (typeof r !== 'string') out.errors.push('TAB ' + name + ' : returned ' + typeof r); else out.tabs.push(name); } catch(e){ out.errors.push('TAB ' + name + ' : ' + e.message); } }
  state.role = 'R1';
  T('contentSopTab', function(){ return contentSopTab(); });
  T('contentPlanTab', function(){ return contentPlanTab(); });
  T('contentWtTab:register', function(){ state.tab.contentWork = 'register'; return contentWtTab(); });
  T('contentWtTab:execution', function(){ state.tab.contentWork = 'execution'; return contentWtTab(); });
  T('contentWtTab:matrix', function(){ state.tab.contentWork = 'matrix'; return contentWtTab(); });
  T('contentTaskTab:register', function(){ return contentTaskTab('register'); });
  T('contentTaskTab:execution', function(){ return contentTaskTab('execution'); });
  T('contentTaskTab:matrix', function(){ return contentTaskTab('matrix'); });
  T('contentTaskTab:all', function(){ return contentTaskTab('全部任务', true); });
  T('contentOpsLibTab', function(){ return contentOpsLibTab(); });
  T('contentReviewTab', function(){ return contentReviewTab(); });
  T('contentLayoutTab', function(){ return contentLayoutTab(); });

  // ---- 全模块 Tab 矩阵（B）：遍历源码所有 setTab(key,label) ----
  out.tabMatrix = { total: 0, ok: 0, checked: 0, skip: 0, fail: [] };
  TABPAIRS.forEach(function (tp) {
    out.tabMatrix.total++;
    var key = tp[0], label = tp[1];
    var cand = keys.filter(function (k) { return MODS[k] && (k.indexOf(key) >= 0 || key.indexOf(k) >= 0); });
    if (!cand.length) { out.tabMatrix.skip++; return; }
    out.tabMatrix.ok++;
    state.tab[key] = label;
    cand.forEach(function (p) {
      out.tabMatrix.checked++;
      try { state.page = p; var s = PAGES[p](); if (typeof s !== 'string') out.tabMatrix.fail.push(p + ' / ' + key + '=' + label + ' -> non-string'); }
      catch (e) { out.tabMatrix.fail.push(p + ' / ' + key + '=' + label + ' : ' + e.message); }
    });
  });

  // ---- CONTENT drawers/dialogs ----
  function D(name, fn){ try { fn(); out.drawers.push(name); } catch(e){ out.errors.push('DRAWER ' + name + ' : ' + e.message); } }
  D('opsContentEdit', function(){ state.opsContentEditIdx = 0; opsContentEdit(0, state.opsEditTaskId); });
  D('opsQuickTypesetDialog', function(){ opsQuickTypesetDialog(0); });
  D('opsAiTypesetDialog', function(){ opsAiTypesetDialog(0); });
  D('opsLayoutTemplateSelect', function(){ opsLayoutTemplateSelect(0); });
  D('opsContentAiDialog', function(){ opsContentAiDialog(0); });
  D('opsReviewView', function(){ opsReviewView(0); });
  D('opsReviewRejectDrawer', function(){ opsReviewRejectDrawer(0); });
  D('taskDetail', function(){ taskDetail(0); });
  D('wtAdd', function(){ wtAdd(); });
  D('opsPlanAdd', function(){ opsPlanAdd(); });
  D('opsPlanDetail', function(){ opsPlanDetail(0); });
  D('contentLayoutAdd', function(){ contentLayoutAdd(); });
  D('contentLayoutImport(三Tab)', function(){ contentLayoutImport(); });
  // v2.6.33：SOP 审核整体移除，原 sopReviewDetail/DrawerApprove/DrawerReject 探针已删

  // ---- 跨模块二级/三级页抽屉冒烟（C）----
  D('sysRoleUserList', function () { sysRoleUserList(0); });
  D('sysRolePermEdit', function () { sysRolePermEdit(0); });
  D('sysRoleScopeEdit', function () { sysRoleScopeEdit(0); });
  D('authRuleEdit', function () { authRuleEdit(0); });
  D('authRuleMembers', function () { authRuleMembers(0); });
  D('acctDetail', function () { acctDetail(0); });
  D('assetDetail', function () { assetDetail(0); });
  D('ipgAccountBind', function () { ipgAccountBind(0); });
  D('costDetail', function () { costDetail(0); });
  D('costVoucherPreview', function () { costVoucherPreview('CS-2026-0001'); });
  D('flowNodeConfig', function () { flowNodeConfig(0, 1); });
  D('flowTplVer', function () { flowTplVer(0); });
  D('perfDetail', function () { perfDetail(0); });
  D('examPaperDetail', function () { examPaperDetail(0); });
  D('examRecordDetail', function () { examRecordDetail(0); });
  D('alertRuleEdit', function () { alertRuleEdit(0); });
  D('biCatDlg', function () { biCatDlg(); });
  D('biShareDlg', function () { biShareDlg(1); });
  D('biFilterDlg', function () { biFilterDlg(); });
  D('biLinkDlg', function () { biLinkDlg(); });
  D('biJumpDlg', function () { biJumpDlg(); });
  D('biImportJson', function () { biImportJson(); });
  D('biExportJson', function () { biExportJson(1); });
  D('biSessionDetail', function () { biSessionDetail('IMS202609110DY0138'); });
  D('biSnapshotDlg', function () { biSnapshotDlg(); });
  D('airSkillDetail', function () { airSkillDetail('SK-001'); });
  D('airSkillGrant', function () { airSkillGrant('SK-001'); });
  D('liveMetricsApi', function () { liveMetricsApi('IMS202609110DY0138'); });
  D('liveCorrectionDrawer', function () { liveCorrectionDrawer('IMS202609110DY0138'); });
  D('wtMatchDetail', function () { wtMatchDetail(0); });
  D('colLogDetail', function () { colLogDetail(0); });
  D('colCfg:extAccount', function () { colCfg('extAccount'); });
  D('helpCenter', function () { helpCenter(); });
  D('bi0ResultHistoryInfo', function () { bi0ResultHistoryInfo(); });
  D('opsPlanStepMatchPick', function () { state.opsPlanSteps = [{ no: 1, matches: [], assignee: '', post: '', name: '', type: '', start: '', end: '' }]; opsPlanStepMatchPick(0); });
  D('wtPickMatch', function () { wtPickMatch(0); });
  D('wtPickAccount', function () { wtPickAccount(0); });

  // ---- amphipoda play-area state machine (U1 / U6) ----
  try {
    // 玩法态存于 state.opsEditScheme（非 OPS_CONTENTS 持久字段）
    state.opsContentEditIdx = 0;
    state.opsEditPlayTab = 1;
    state.opsEditScheme = [{ scheduleId: 'SCH-101', homeName: '曼联', awayName: '切尔西', matchType: 1 }];
    state.opsEditPlayConfirmed = true;
    out.play = { seeded: state.opsEditScheme.length };
    opsPlaySwitchTab(2);                                  // U1：切 Tab 应清空未确认玩法
    out.play.afterSwitchLen = state.opsEditScheme.length;
    out.play.confirmedAfterSwitch = state.opsEditPlayConfirmed;
    opsPlayAddMatch();                                    // 传足 Tab 加场
    out.play.afterAddLen = state.opsEditScheme.length;
    opsPlayConfirm();
    out.play.confirmedAfterConfirm = state.opsEditPlayConfirmed;
    opsPlayRemove(0);                                     // U6：删至 0 场回未确认
    out.play.afterRemoveLen = state.opsEditScheme.length;
    out.play.confirmedAfterRemove = state.opsEditPlayConfirmed;

    // 断言 U1 / U3 / U6
    var exp = { afterSwitchLen: 0, confirmedAfterSwitch: false, afterAddLen: 1, confirmedAfterConfirm: true, afterRemoveLen: 0, confirmedAfterRemove: false };
    Object.keys(exp).forEach(function(k){
      if (state.opsEditPlayConfirmed !== undefined && out.play[k] !== exp[k]) out.errors.push('PLAY-ASSERT U1/U6 ' + k + ' expected ' + exp[k] + ' got ' + out.play[k]);
    });
    if (out.play.afterSwitchLen !== 0) out.errors.push('PLAY-ASSERT U1 切Tab未清空: got ' + out.play.afterSwitchLen);
    if (out.play.afterAddLen !== 1) out.errors.push('PLAY-ASSERT 加场后应为1: got ' + out.play.afterAddLen);
    if (out.play.confirmedAfterConfirm !== true) out.errors.push('PLAY-ASSERT 确认后应为true: got ' + out.play.confirmedAfterConfirm);
    if (out.play.afterRemoveLen !== 0 || out.play.confirmedAfterRemove !== false) out.errors.push('PLAY-ASSERT U6 删至0场未回未确认态');
  } catch(e){ out.errors.push('PLAY : ' + e.message); }

  return out;
})();
`;

const fn = new Function('document', 'window', 'localStorage', 'navigator', 'location', 'alert', 'confirm', 'prompt', 'getComputedStyle', 'TABPAIRS', body + probe);
let r;
try { r = fn(document, window, localStorage, navigator, location, alert, confirm, prompt, getComputedStyle, tabPairs); }
catch (e) { console.log('BOOT ERROR:', e.message); console.log(e.stack.split('\n').slice(0, 8).join('\n')); process.exit(2); }

console.log('PAGES count:', r.pageCount, '| non-navigable aliases:', r.aliases.length);
console.log('tabs rendered OK:', r.tabs.length, '->', r.tabs.join(', '));
console.log('drawers opened OK:', r.drawers.length, '->', r.drawers.join(', '));
console.log('play-area:', JSON.stringify(r.play || {}));
console.log('tab matrix: total ' + r.tabMatrix.total + ' | mapped ' + r.tabMatrix.ok + ' | skipped ' + r.tabMatrix.skip + ' | rendered ' + r.tabMatrix.checked + ' | fail ' + r.tabMatrix.fail.length);
r.tabMatrix.fail.forEach(f => console.log('  TABFAIL ' + f));

// ---- 静态死按钮检测：onclick/onchange 内引用的函数是否已定义 ----
const builtins = new Set(('function if else for while switch catch return typeof new void delete in of do this event confirm alert prompt ' +
  'Number String Boolean Array Object JSON Math Date parseInt parseFloat isNaN setTimeout setInterval clearTimeout encodeURIComponent decodeURIComponent ' +
  'filter map forEach getElementById querySelector querySelectorAll indexOf remove replace stopPropagation toggle classList closest split join slice splice push concat ' +
  'trim toLowerCase toUpperCase charAt substring substr includes find reduce some every sort reverse keys values entries assign from isArray stringify parse toFixed ' +
  'toLocaleString padStart padEnd repeat startsWith endsWith valueOf toString hasOwnProperty focus blur click removeChild appendChild insertBefore setAttribute getAttribute ' +
  'removeAttribute scrollTo open print reload simTask copyText downloadText setTxt showEl toggleDisp qs qi qsv qbar tbl').split(/\s+/));
const defined = new Set();
{
  const reDef = /(?:function\s+([A-Za-z_$][\w$]*))|(?:var\s+([A-Za-z_$][\w$]*)\s*=\s*function)|(?:const\s+([A-Za-z_$][\w$]*)\s*=\s*function)|(?:window\.([A-Za-z_$][\w$]*)\s*=)|(?:PAGES\.([A-Za-z_$][\w$]*)\s*=)/g;
  let dm;
  while ((dm = reDef.exec(body))) { const n = dm[1] || dm[2] || dm[3] || dm[4] || dm[5]; if (n) defined.add(n); }
}
const missing = new Map();
{
  const reH = /on(?:click|change|input)="([^"]*)"/g;
  let hm;
  while ((hm = reH.exec(html))) {
    const code = hm[1];
    const reFn = /\b([A-Za-z_$][\w$]*)\s*\(/g;
    let fm;
    while ((fm = reFn.exec(code))) {
      const n = fm[1];
      if (builtins.has(n) || defined.has(n)) continue;
      missing.set(n, (missing.get(n) || 0) + 1);
    }
  }
}
console.log('undefined handler fns (dead buttons):', missing.size, missing.size ? Array.from(missing.entries()).map(x => x[0] + '×' + x[1]).join(', ') : '');

console.log('ERRORS:', r.errors.length);
r.errors.forEach(e => console.log('  - ' + e));
const bad = r.errors.length + r.tabMatrix.fail.length + missing.size;
if (bad === 0) console.log('\n>>> ALL INTERACTIVE PROBES PASSED');
else console.log('\n>>> PROBE FAILURES: ' + bad);