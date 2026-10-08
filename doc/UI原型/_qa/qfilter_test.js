// 隔离纯函数测试：验证 qFilter 状态枚举语义（临时替换 qGrab，直接调用页面原函数）
const fs = require('fs');
const vm = require('vm');
const HTML = fs.readFileSync(String.raw`D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html`, 'utf-8');
const scripts = [...HTML.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const code = scripts.join('\n;\n');

const INJECT = `
;(function(){
  const F = qFilter;
  // 数据与 norm/status 映射全部按页面原样
  function runAcct(vals, init) {
    const g = { vals: vals, init: !!init };
    const orig = qGrab; qGrab = function () { return g; };
    try { return F(ACCTS, function (a) { return [a.id, a.nick, a.owner]; }, function (a) { return a.plat + '|' + a.st; }); }
    finally { qGrab = orig; }
  }
  function runCert(vals, init) {
    const g = { vals: vals, init: !!init };
    const orig = qGrab; qGrab = function () { return g; };
    try { return F(CERTS, function (c) { return [c.holder, c.no]; }, function (c) { return c.type + '|' + c.st; }); }
    finally { qGrab = orig; }
  }
  function runTrain(vals, init) {
    const g = { vals: vals, init: !!init };
    const orig = qGrab; qGrab = function () { return g; };
    try { return F(TRAINS, function (t) { return [t.id, t.name, t.teacher, t.place]; }, function (t) { return t.type + '|' + t.st; }); }
    finally { qGrab = orig; }
  }
  function runAlert(vals, init) {
    const g = { vals: vals, init: !!init };
    const orig = qGrab; qGrab = function () { return g; };
    try { return F(ALERTS, function (a) { return [a.rule, a.obj]; }, function (a) { return a.lv + '|' + a.st; }); }
    finally { qGrab = orig; }
  }
  globalThis.__T__ = { runAcct, runCert, runTrain, runAlert,
    counts: {
      acctFrozen: ACCTS.filter(a => a.st === '冻结').length,
      acctReturned: ACCTS.filter(a => a.st === '已归还').length,
      acctDouyin: ACCTS.filter(a => a.plat === '抖音').length,
      certPassport: CERTS.filter(c => c.type === '护照').length,
      trainEnroll: TRAINS.filter(t => t.st === '报名中').length,
      alertRed: ALERTS.filter(a => a.lv === '红').length
    }
  };
})();
`;

// 注入非 null 的 REG 元素（占位，实际 document 桩在下方覆盖）

const sandbox = {
  console, process: { exit() { } },
  document: null,
  setTimeout: () => 0, clearTimeout: () => { },
  Math, Date, Number, String, Array, Object, JSON, Set, RegExp, Error
};
sandbox.window = sandbox; sandbox.globalThis = sandbox;

// 先注册 document 桩（覆盖式 querySelector/getElementById 返回可写元素）
const el = () => ({ innerHTML: '', textContent: '', style: {}, classList: { add() { }, remove() { }, contains: () => false, toggle() { } }, appendChild() { }, children: [], querySelectorAll: () => [] });
const ELPOOL = {};
sandbox.document = {
  querySelector: s => { if (s[0] === '#') { const id = s.slice(1).split(' ')[0]; if (!ELPOOL[id]) ELPOOL[id] = el(); return ELPOOL[id]; } return null; },
  getElementById: id => { if (!ELPOOL[id]) ELPOOL[id] = el(); return ELPOOL[id]; },
  createElement: () => el(),
  addEventListener() { }, querySelectorAll: () => [], body: { appendChild() { } }
};
try {
  vm.runInNewContext(code + INJECT, sandbox, { filename: 'qfilter-test.js' });
} catch (e) { console.log('ERR ' + e.message); process.exit(2); }

const T = sandbox.globalThis.__T__;
const C = T.counts;
// ACCT 页 qbar 控件顺序: k0=账号编号(input), k2=平台(select), k3=状态(select), k4=责任人, k1=昵称
// vals 数组对应页面 qGrab 收集顺序 = DOM 顺序
const acct = (plat, st) => T.runAcct(['', plat, st, '', ''], false);
console.log('ACCT 冻结      =>', acct('全部平台', '冻结').length, '期望', C.acctFrozen);
console.log('ACCT 已归还    =>', acct('全部平台', '已归还').length, '期望', C.acctReturned);
console.log('ACCT 抖音      =>', acct('抖音', '全部状态').length, '期望', C.acctDouyin);
console.log('ACCT 抖音+在用 =>', acct('抖音', '在用').length, '期望', ACCTS => ACCTS);
// CERT: k0=持有人, k1=类型, k2=档案状态, k3=到期状态
console.log('CERT 护照      =>', T.runCert(['', '护照', '档案状态', '到期状态'], false).length, '期望', C.certPassport);
// TRAIN: k0=编号, k1=名称, k2=类型, k4=讲师, k3=状态
console.log('TRAIN 报名中   =>', T.runTrain(['', '', '全部类型', '', '报名中'], false).length, '期望', C.trainEnroll);
// ALERT: k0=级别, k1=状态, k2=关键词
console.log('ALERT 红       =>', T.runAlert(['红', '全部状态', ''], false).length, '期望', C.alertRed);
console.log('ALERT 处理中   =>', T.runAlert(['全部级别', '处理中', ''], false).length, '期望', ALERTS => 0);
