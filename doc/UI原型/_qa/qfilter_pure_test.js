// qfilter_pure_test.js — 隔离验证 qFilter 的复合状态匹配语义（不依赖完整 DOM）
// 直接从源文件提取 qFilter/qGrab/qInit 原函数，用最小桩验证 6 个模块的 select 过滤行为
const fs = require('fs');
const vm = require('vm');
const NODE = 'C:/self'.startsWith('C:') ? null : null;
const FILE = 'D:/self/sy/一体化管理/outputs/UI原型/IMS-一体化管理系统-UI原型.html';
const src = fs.readFileSync(FILE, 'utf-8');

// 提取 script 块
const scripts = [];
const re = /<script>([\s\S]*?)<\/script>/g;
let m;
while ((m = re.exec(src)) !== null) scripts.push(m[1]);

// ---- 最小 DOM 桩 ----
function El(tag) {
  this.tagName = tag; this.value = ''; this.children = [];
  this.classList = { add(){}, remove(){}, contains(){ return false; } };
}
El.prototype.querySelectorAll = function (sel) {
  // 返回直接+间接子树中匹配 input/select 的元素
  const out = [];
  (function walk(node) {
    node.children.forEach(c => {
      if (sel === 'input,select' && (c.tagName === 'INPUT' || c.tagName === 'SELECT')) out.push(c);
      else if (sel === 'input' && c.tagName === 'INPUT') out.push(c);
      else if (sel === 'select' && c.tagName === 'SELECT') out.push(c);
      walk(c);
    });
  })(this);
  return out;
};
const contentEl = new El('div');
const qbarEl = new El('div');
contentEl.children.push(qbarEl);
const document = {
  getElementById(id) { return id === 'content' ? contentEl : null; },
  querySelector(sel) { if (sel === '#content .qbar') return qbarEl; return null; }
};
const $ = function (sel) { return document.querySelector(sel); };

// ---- 从源码提取 qGrab/qInit/qFilter 原函数（脚本块 2 中） ----
// 位置：L559-595 附近，直接用正则切出函数体
function extractFn(name, code) {
  const idx = code.indexOf('function ' + name + '(');
  if (idx < 0) throw new Error('fn not found: ' + name);
  let depth = 0, i = code.indexOf('{', idx);
  for (let j = i; j < code.length; j++) {
    if (code[j] === '{') depth++;
    else if (code[j] === '}') { depth--; if (depth === 0) return code.slice(idx, j + 1); }
  }
  throw new Error('unbalanced');
}
const s1 = scripts[0]; // 第一个 script 块（L287-678）含 qGrab/qInit/qFilter 通用组件
const qGrabCode = extractFn('qGrab', s1);
const qInitCode = extractFn('qInit', s1);
const qFilterCode = extractFn('qFilter', s1);
// qGrab/qInit 使用 $ / document —— 桩里 $ 已定义

const sandbox = { $: $, document: document };
vm.createContext(sandbox);
vm.runInContext(qInitCode + '\n' + qGrabCode + '\n' + qFilterCode, sandbox);
const { qFilter } = sandbox;

// ---- 测试数据（与页面 mock 一致的精简版）----
const ACCTS = [
  { id: 'ACCT-2026-0001', plat: '抖音', nick: '神鱼体育', owner: '赵敏', st: '在用' },
  { id: 'ACCT-2026-0008', plat: '抖音', nick: '神鱼好物优选', owner: '李澈', st: '冻结' },
  { id: 'ACCT-2026-0087', plat: '抖音', nick: '神鱼夜跑频道', owner: '王野', st: '冻结' },
  { id: 'ACCT-2026-0012', plat: 'B 站', nick: '神鱼健身教室', owner: '—', st: '池可领用' }
];
const norm_acct = (a) => [a.id, a.nick, a.owner];
const status_acct = (a) => a.plat + '|' + a.st;

function setBar(vals) {
  qbarEl.children = [];
  vals.forEach(v => {
    const el = new El(v.type || 'INPUT');
    el.value = v.value;
    qbarEl.children.push(el);
  });
}

let pass = 0, fail = 0;
function T(name, cond, detail) {
  if (cond) { pass++; console.log('PASS |', name); }
  else { fail++; console.log('FAIL |', name, detail || ''); }
}

// T1: 账号状态 select「冻结」→ 期望 2 行（ACCT-0008/0087）
setBar([{ value: '' }, { value: '全部平台' }, { value: '冻结' }, { value: '' }, { value: '' }]);
let r = qFilter(ACCTS, norm_acct, status_acct);
T('T1 acct 状态=冻结 → 2 行', r.length === 2, '实际 ' + r.length);

// T2: 平台 select「抖音」→ 期望 3 行
setBar([{ value: '' }, { value: '抖音' }, { value: '全部状态' }, { value: '' }, { value: '' }]);
r = qFilter(ACCTS, norm_acct, status_acct);
T('T2 acct 平台=抖音 → 3 行', r.length === 3, '实际 ' + r.length);

// T3: 文本搜索「神鱼体育」→ 期望 1 行（norm 命中）
setBar([{ value: '神鱼体育' }, { value: '全部平台' }, { value: '全部状态' }, { value: '' }, { value: '' }]);
r = qFilter(ACCTS, norm_acct, status_acct);
T('T3 acct 文本=神鱼体育 → 1 行', r.length === 1, '实际 ' + r.length);

// T4: 单维状态模块（fin 风格 status=st）「已结算」语义 → 验证 v===s 精确匹配可用
const FINS = [
  { id: 'FI-01', st: '已结算' }, { id: 'FI-02', st: '待结算' }, { id: 'FI-03', st: '已结算' }
];
setBar([{ value: '' }, { value: '' }, { value: '已结算' }]);
r = qFilter(FINS, (f) => [f.id], (f) => f.st);
T('T4 fin 单维状态=已结算 → 2 行', r.length === 2, '实际 ' + r.length);

// T5: cert 复合 type|st「护照」→ 期望 1 行（何舟护照）
const CERTS = [
  { holder: '苏杳', type: '居民身份证', st: '已归档' },
  { holder: '何舟', type: '护照', st: '已归档' }
];
setBar([{ value: '' }, { value: '护照' }, { value: '档案状态' }]);
r = qFilter(CERTS, (c) => [c.holder, c.no], (c) => c.type + '|' + c.st);
T('T5 cert 类型=护照 → 1 行', r.length === 1, '实际 ' + r.length);

// T6: alert 复合 lv|st「红」→ 期望 3 行
const ALERTS = [
  { lv: '红', rule: 'A', st: '未处理' }, { lv: '红', rule: 'B', st: '处理中' },
  { lv: '橙', rule: 'C', st: '已恢复' }, { lv: '红', rule: 'D', st: '已恢复' }
];
setBar([{ value: '红' }, { value: '全部状态' }, { value: '' }]);
r = qFilter(ALERTS, (a) => [a.rule, a.obj], (a) => a.lv + '|' + a.st);
T('T6 alert 级别=红 → 3 行', r.length === 3, '实际 ' + r.length);

// T7: train 复合 type|st「报名中」→ 期望 2 行
const TRAINS = [
  { id: 'T1', type: '直播规范', st: '报名中' }, { id: 'T2', type: '数据技能', st: '报名中' }, { id: 'T3', type: '安全', st: '已结束' }
];
setBar([{ value: '' }, { value: '' }, { value: '全部类型' }, { value: '' }, { value: '报名中' }]);
r = qFilter(TRAINS, (t) => [t.id, t.name, t.teacher, t.place], (t) => t.type + '|' + t.st);
T('T7 train 状态=报名中 → 2 行', r.length === 2, '实际 ' + r.length);

// T8: 全部条件初始（init）→ 原样返回
setBar([{ value: '' }, { value: '全部平台' }, { value: '全部状态' }, { value: '' }, { value: '' }]);
r = qFilter(ACCTS, norm_acct, status_acct);
T('T8 初始状态不过滤 → 4 行', r.length === 4, '实际 ' + r.length);

console.log('\n==== RESULT: ' + pass + ' PASS / ' + fail + ' FAIL ====');
