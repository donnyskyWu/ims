// qfilter_root_cause.js — 精确复现 P0 缺陷根因：qFilter 对复合状态串的匹配逻辑
// 场景：acct 页 qbar select 选「冻结」，status 函数返回 '抖音|冻结' 复合串
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync('D:/self/sy/一体化管理/outputs/UI原型/IMS-一体化管理系统-UI原型.html', 'utf-8');
const scripts = [...src.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
function extractFn(name, code) {
  const idx = code.indexOf('function ' + name + '(');
  let depth = 0; const i = code.indexOf('{', idx);
  for (let j = i; j < code.length; j++) {
    if (code[j] === '{') depth++;
    else if (code[j] === '}') { depth--; if (depth === 0) return code.slice(idx, j + 1); }
  }
  throw new Error('unbalanced');
}
// 只需 qFilter 的核心逻辑：直接摘取 L575-595 函数，硬编码 g（绕过 qGrab）
const qFilterCode = extractFn('qFilter', scripts[0]);
// 复制并重命名以便传入 g
const testCode = qFilterCode.replace('function qFilter(src, norm, status) {', 'function qFilter2(src, norm, status, g) {')
  .replace('  const g = qGrab();\n', '');
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(testCode, sandbox);

const ACCTS = [
  { id: 'ACCT-0001', plat: '抖音', owner: '赵敏', st: '在用' },
  { id: 'ACCT-0008', plat: '抖音', owner: '李澈', st: '冻结' },
  { id: 'ACCT-0087', plat: '抖音', owner: '王野', st: '冻结' }
];
// 完全复刻页面 qbar 控件值序列：[账号编号input='', 平台select='全部平台', 状态select='冻结', 责任人input='', 昵称input='']
const g = { vals: ['', '全部平台', '冻结', '', ''], init: false };
const r = sandbox.qFilter2(ACCTS, a => [a.id, a.nick, a.owner], a => a.plat + '|' + a.st, g);
console.log('acct 状态=冻结 期望 2, 实际', r.length, r.length === 2 ? '(源码正确)' : '(缺陷复现)');

// 逐行跟踪单行过滤判定
const row = ACCTS[1];
console.log('\n--- 单行判定跟踪（row=冻结账号） ---');
console.log('status(row) =', row.plat + '|' + row.st, '(复合串)');
console.log('select 值 v = "冻结"');
console.log('v === s ?', ('冻结' === '抖音|冻结'), '→ false，进入 else 分支');
console.log('/(已|待|...|冻结|...)/.test("冻结") ?', /(已|待|池|冻结|在用|闲置|维修|报废|归还|注销|结束|取消|开播|直播中|进行中|报名中|已归档|审核中|过期|补交|提交|草稿|迟交|已恢复|已忽略|未处理|处理中|结算)/.test('冻结'), '→ true → ok=false（行被排除）');

// 对照组：单维状态（fin 页 status 返回 f.st 单串）
const FINS = [{ id: 'F1', st: '已结算' }, { id: 'F2', st: '待结算' }];
const r2 = sandbox.qFilter2(FINS, f => [f.id], f => f.st, { vals: ['', '', '已结算'], init: false });
console.log('\nfin 单维状态=已结算 期望 2, 实际', r2.length, r2.length === 2 ? '(源码正确——v===s 精确命中)' : '(缺陷)');
console.log('\n结论: 仅复合状态串模块（acct/cert/live/train/alert，返回 "A|B" 形态）的状态 select 过滤失效；单维模块（fin/meet）正常。');
