
'use strict';
/* ===================== Mock 数据 ===================== */
const TODOS = [
  { tab: '审批', icon: 'doc', title: '账号领用申请 · 罗技 C920 摄像头（赵敏申请）', from: '资产管理', time: '32 分钟前', deadline: '2026-09-12 18:00' },
  { tab: '审批', icon: 'doc', title: '费用报销单 BX20260911-02 · ¥3,260.00', from: '财务核算', time: '1 小时前', deadline: '2026-09-13 12:00' },
  { tab: '归还', icon: 'box', title: '账号归还待确认 · ACCT-2026-0071 已释放至池', from: '账号管理', time: '2 小时前', deadline: '2026-09-12 17:30' },
  { tab: '审核', icon: 'film', title: '短视频《秋季跑鞋测评》待审核（投稿：孙倩）', from: '内容生产', time: '3 小时前', deadline: '2026-09-12 20:00' },
  { tab: '确认', icon: 'check', title: '工作任务 WT-0918 待确认出任务（电竞一组 · 竞彩）', from: '内容生产', time: '40 分钟前', deadline: '2026-09-12 16:00' },
  { tab: '告警', icon: 'warn', title: '采集失败 · 抖音内部账号 Cookie 失效（3 条）', from: '数据采集', time: '55 分钟前', deadline: '2026-09-12 15:00' },
  { tab: '审批', icon: 'video', title: '开播登记待风控复核 · 风险分 82（高）', from: '直播管理', time: '4 小时前', deadline: '2026-09-12 14:00' },
  { tab: '预警', icon: 'bell', title: '证件到期预警 · 苏杳身份证剩余 26 天', from: '证件档案', time: '昨天 09:00', deadline: '2026-10-08 23:59' },
  { tab: '告警', icon: 'warn', title: '账号风险分超阈值 · ACCT-2026-0087（86 分）', from: '预警中心', time: '1 小时前', deadline: '2026-09-12 13:00' },
  { tab: '归还', icon: 'box', title: '会议室预订冲突待处理 · 3F-大会议室 16:00', from: '会议', time: '昨天 15:40', deadline: '2026-09-11 16:00' },
  { tab: '审批', icon: 'book', title: '培训学习任务 ·《直播合规与风控》待完成', from: '培训', time: '昨天 11:00', deadline: '2026-09-20 23:59' },
  { tab: '审核', icon: 'doc', title: '日报待审阅 · 赵敏 2026-09-11 直播日报', from: '日报中心', time: '昨天 22:10', deadline: '2026-09-13 10:00' }
];
function activeTodos() { return TODOS.filter(function (t) { return !t.closed; }); }
function todoTagColor(tab) {
  if (tab === '告警') return 'red';
  if (tab === '预警') return 'orange';
  if (tab === '审批') return 'blue';
  return 'green';
}
const WB_TODO_TABS = ['全部', '审批', '归还', '审核', '确认', '预警', '告警'];
function filterTodosByTab(cur, pool) {
  pool = pool || activeTodos();
  return pool.filter(function (t) { return cur === '全部' || t.tab === cur; });
}

/* ===================== 工作台 ===================== */
PAGES.workbench = function () {
  const hour = new Date().getHours();
  const greet = hour < 6 ? '凌晨好' : hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好';
  const r = ROLES[state.role];
  const pending = activeTodos();
  const unreadMsg = MSGS.filter(function (x) { return !x.read; }).length;
  const cards = [
    { l: '资产总数', n: '128', d: '环比 <span class="pos">+6</span> 件', icon: 'box', go: 'cdLive' },
    { l: '在用账号', n: '86', d: '池可领用 12 个', icon: 'user', go: 'caDouyin' },
    { l: '直播场次（本周）', n: '14', d: '今日 3 场待开播', icon: 'video', go: 'live' },
    { l: '待办事项', n: String(pending.length), d: '含 1 条高危告警', icon: 'doc', go: 'workbenchTodos' }
  ].filter(function (c) { return canAccess(c.go) || c.go === 'workbenchTodos'; });
  const cur = state.tab.workbench || '全部';
  const list = filterTodosByTab(cur).slice(0, 10);
  const msgPreview = MSGS.slice(0, 10);

  let h = '<div style="margin:6px 0 22px"><h1 style="font-size:30px;font-weight:700;letter-spacing:-.7px;line-height:1.07">' + greet + '，' + r.user + '</h1>' +
    '<div style="font-size:13px;color:var(--text2);margin-top:6px">2026年9月12日 星期六 · 今日 3 场直播待开播，' + pending.length + ' 条待办' +
    (unreadMsg ? ' · ' + unreadMsg + ' 条未读消息' : '') + '</div></div>';
  h += '<div class="g4">';
  cards.forEach(function (c) {
    h += '<div class="card hov stat" onclick="go(\'' + c.go + '\')"><div class="rowline" style="justify-content:space-between"><span class="l">' + c.l + '</span><span style="color:var(--blue)">' + ic(c.icon, 17) + '</span></div>' +
      '<div class="n">' + c.n + '</div><div class="d">' + c.d + '</div></div>';
  });
  h += '</div><div class="g2" style="margin-top:16px">';
  /* 待办中心 */
  h += '<div class="card" style="padding-bottom:10px"><div class="hd-row"><h3>待办中心</h3><div class="rowline" style="gap:8px">' +
    '<span style="font-size:12px;color:var(--text2)">' + pending.length + ' 条待处理</span>' +
    '<button class="btn btn-txt btn-sm" onclick="go(\'workbenchTodos\')">查看更多</button></div></div><div class="tabs">';
  WB_TODO_TABS.forEach(function (t) { h += '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'workbench\',\'' + t + '\')">' + t + '</div>'; });
  h += '</div><div>';
  if (!list.length) h += emptyState('暂无「' + cur + '」类待办', '所有相关事项已处理完毕');
  list.forEach(function (t) {
    const idx = TODOS.indexOf(t);
    h += '<div class="mg-i" style="border-radius:8px"><span style="color:var(--blue);margin-top:2px">' + ic(t.icon, 17) + '</span>' +
      '<div style="flex:1;min-width:0"><div class="mt">' + t.title + '</div><div class="md">' + tag(t.tab + '待办', todoTagColor(t.tab)) + ' · ' + t.from + ' · ' + t.time + '</div></div>' +
      '<button class="btn btn-pri btn-sm" style="flex:none" onclick="event.stopPropagation();todoGo(' + idx + ')">去处理</button></div>';
  });
  h += '</div></div>';
  /* 消息中心（工作台内嵌） */
  h += '<div class="card" style="padding-bottom:10px"><div class="hd-row"><h3>消息中心</h3><div class="rowline" style="gap:8px">' +
    (unreadMsg ? tag(unreadMsg + ' 未读', 'red') : tag('全部已读', 'green')) +
    '<button class="btn btn-txt btn-sm" onclick="markAllRead()">全部已读</button>' +
    '<button class="btn btn-txt btn-sm" onclick="go(\'workbenchMsgs\')">查看更多</button></div></div><div>';
  if (!msgPreview.length) h += emptyState('暂无消息', '审批结果与预警将推送至此');
  else h += msgRowsHtml(msgPreview);
  h += '</div><div class="dsec" style="margin-top:16px">系统公告</div><div style="font-size:12.5px;color:var(--text2);line-height:1.6">走查 #14：侧栏「AI 资源中心」本期为技能库 / 专家库 / 模型与提示词；知识库、Key 管理、审计监控延后交付。V2.3「工作流催办」与「预警规则订阅」已全量。</div></div>';
  h += '</div>';
  return h;
};
PAGES.workbenchTodos = function () {
  const cur = state.tab.workbenchTodos || state.tab.workbench || '全部';
  const pool = activeTodos();
  const list = filterTodosByTab(cur, pool);
  let h = pgHead('workbenchTodos', '<button class="btn btn-sec btn-sm" onclick="go(\'workbench\')">' + ic('arrow', 15) + '返回工作台</button>');
  h += '<div class="tabs">' + WB_TODO_TABS.map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'workbenchTodos\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  h += qbar(qi('搜索待办标题', 180) + qs(['全部状态', '待处理', '已过期'], 108), 'toast(\'已按条件筛选待办（原型示意）\',\'success\')');
  let rows = '';
  list.forEach(function (t) {
    const idx = TODOS.indexOf(t);
    rows += '<tr><td>' + tag(t.tab + '待办', todoTagColor(t.tab)) + '</td><td style="font-weight:500;max-width:360px">' + t.title + '</td>' +
      '<td class="num" style="font-size:12px;color:var(--text2)">' + (t.deadline || '—') + '</td><td>' + tag('待处理', 'blue') + '</td>' +
      '<td><span class="btn-txt btn" onclick="todoGo(' + idx + ')">去处理</span> · <span class="btn-txt btn" onclick="todoClose(' + idx + ')">关闭</span></td></tr>';
  });
  h += tbl(['类型', '标题', '截止时间', '状态', '操作'], rows);
  h += '<div class="hint" style="margin-top:10px">对接 GET /auth/workbench/todos · pageSize=20 · 首页预览默认 10 条</div>';
  return h;
};
PAGES.workbenchMsgs = function () {
  const cur = state.tab.workbenchMsgs || '全部';
  let pool = MSGS.slice();
  if (cur === '未读') pool = pool.filter(function (m) { return !m.read; });
  else if (cur === '已读') pool = pool.filter(function (m) { return m.read; });
  const kw = (state.q.workbenchMsgs && state.q.workbenchMsgs.kw) || '';
  if (kw) pool = pool.filter(function (m) { return m.title.indexOf(kw) >= 0 || m.content.indexOf(kw) >= 0; });
  let h = pgHead('workbenchMsgs', '<button class="btn btn-sec btn-sm" onclick="markAllRead()">全部已读</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'workbench\')">' + ic('arrow', 15) + '返回工作台</button>');
  h += '<div class="tabs">' + ['全部', '未读', '已读'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'workbenchMsgs\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  h += qbar(qi('搜索标题 / 摘要', 200, kw), 'wbMsgQuery()');
  if (!pool.length) h += emptyState('暂无消息', '切换 Tab 或重置查询条件');
  else {
    h += '<div class="card" style="padding:8px 12px 4px;margin-top:12px">';
    pool.forEach(function (m) {
      const i = MSGS.indexOf(m);
      h += msgRowsHtml([m], i);
    });
    h += '</div>';
  }
  h += '<div class="hint" style="margin-top:10px">对接 GET /auth/workbench/messages · 点击条目打开详情抽屉并标记已读</div>';
  return h;
};
function wbMsgQuery() {
  const inp = $('#content .qbar input');
  if (!state.q.workbenchMsgs) state.q.workbenchMsgs = {};
  state.q.workbenchMsgs.kw = inp ? inp.value.trim() : '';
  renderPage();
  toast('消息列表已筛选', 'success');
}
/* 待办「去处理」→ 跳转对应模块 */
function todoGo(i) {
  const map = { '资产管理': 'cdLive', '财务核算': 'fin', '账号管理': 'caDouyin', '内容生产': 'contentWork', '直播管理': 'live', '证件档案': 'crCert', '预警中心': 'alert', '会议': 'meet', '数据采集': 'collectTask', '培训': 'trainMaterial', '日报中心': 'dailyReview', '数据上报': 'reportSub', '公司资产': 'caDouyin' };
  const t = TODOS[i];
  if (!t || t.closed) return;
  const m = map[t.from];
  if (m && canAccess(m)) { go(m); toast('已进入「' + t.from + '」处理：' + t.title.slice(0, 18) + '…', 'success'); }
  else toast('已进入处理流程（原型示意）', 'success');
}
function todoClose(i) {
  const t = TODOS[i];
  if (!t || t.closed) return;
  confirmDlg('确认关闭该待办？', '关闭后不再提醒（PUT /auth/workbench/todos/{id} · action=CLOSE）', '确认关闭', function () {
    t.closed = true;
    toast('待办已关闭', 'success');
    if (state.page === 'workbench' || state.page === 'workbenchTodos') renderPage();
  });
}

/* ===================== 01 AUTH 权限管理 ===================== */
const AUTH_USERS = [
  { no: 'SF0001', name: 'Donny', dept: '信息中心', post: '系统架构师', roles: ['R1 系统管理员', 'R9'], sync: '已同步', login: '2026-09-12 14:02' },
  { no: 'SF0012', name: '林岚', dept: '行政部', post: '行政主管', roles: ['R2 行政管理员'], sync: '已同步', login: '2026-09-12 09:31' },
  { no: 'SF0023', name: '周晴', dept: '财务部', post: '财务经理', roles: ['R3 财务管理员'], sync: '已同步', login: '2026-09-11 18:44' },
  { no: 'SF0034', name: '何舟', dept: '运营中心', post: '运营总监', roles: ['R4 运营总监', 'R9'], sync: '已同步', login: '2026-09-12 10:15' },
  { no: 'SF0045', name: '赵敏', dept: '运营中心', post: '直播运营专员', roles: ['R5 直播运营'], sync: '待确认', login: '2026-09-12 08:12' },
  { no: 'SF0056', name: '孙倩', dept: '内容中心', post: '短视频编导', roles: ['R6 短视频运营'], sync: '已同步', login: '2026-09-10 21:03' },
  { no: 'SF0067', name: '苏杳', dept: '主播组', post: '主播/达人', roles: ['R7 主播/达人'], sync: '已同步', login: '2026-09-11 16:20' },
  { no: 'SF0078', name: '陈默', dept: '数据中心', post: '数据分析师', roles: ['R9 数据分析师'], sync: '已同步', login: '2026-09-12 11:48' }
];
const AUTH_EVENTS = [
  { type: '人员入职', person: '王小满（SF0099）', change: '新增 · 运营中心 / 直播运营专员', status: '待处理' },
  { type: '部门调整', person: '李澄（SF0088）', change: '内容中心 → 运营中心', status: '待处理' },
  { type: '岗位变更', person: '赵敏（SF0045）', change: '直播运营专员 → 高级直播运营', status: '已同步' },
  { type: '人员离职', person: '钱宇（SF0062）', change: '账号冻结 · 资产清退完成', status: '已同步' },
  { type: '角色变更', person: '孙倩（SF0056）', change: '追加 R8 内容审核员（兼）', status: '待处理' },
  { type: '部门调整', person: '周晴（SF0023）', change: '财务部 二组 → 一组', status: '已同步' },
  { type: '人员入职', person: '王野（外协）', change: '新增 · 外协人员（受限权限）', status: '已同步' },
  { type: '岗位变更', person: '陈默（SF0078）', change: '助理分析师 → 数据分析师', status: '已同步' }
];
const AUTH_TMPL = [
  { name: '直播运营岗模板', dept: '运营中心', perms: 42, on: true },
  { name: '短视频编导岗模板', dept: '内容中心', perms: 36, on: true },
  { name: '财务核算岗模板', dept: '财务部', perms: 28, on: true },
  { name: '行政综合岗模板', dept: '行政部', perms: 31, on: true },
  { name: '数据分析岗模板（脱敏）', dept: '数据中心', perms: 24, on: true },
  { name: '主播达人岗模板', dept: '主播组', perms: 12, on: false },
  { name: '内容审核岗模板', dept: '内容中心', perms: 18, on: true },
  { name: '外协受限模板', dept: '外协', perms: 6, on: true }
];
PAGES.authOrg = function () {
  const cur = state.tab.authOrg || '人员列表';
  let h = pgHead('authOrg', '<button class="btn btn-sec" onclick="exportX(this,\'组织人员\',AUTH_USERS.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="syncDing()">' + ic('arrow', 15) + '手动对账</button>');
  h += '<div class="hint" style="margin-bottom:8px">AUTH-002 · BR-001 同步延迟 &lt; 5min · 人员主键对齐 <code>system_users.id</code> · 用户 IMS 角色在 <span class="btn-txt btn" onclick="go(\'sysUser\')">系统管理→用户</span> 维护。</div>';
  h += '<div class="g4" style="margin-bottom:12px"><div class="card stat"><span class="l">人员总数</span><div class="n">' + AUTH_USERS.length + '</div><div class="d">GET /auth/org/users</div></div>' +
    '<div class="card stat"><span class="l">昨日事件</span><div class="n pos">12</div><div class="d">hire/transfer/resign</div></div>' +
    '<div class="card stat"><span class="l">待处理</span><div class="n" style="color:var(--orange)">3</div><div class="d">需 R1 重放/对账</div></div>' +
    '<div class="card stat"><span class="l">平均延迟</span><div class="n pos">2.4</div><div class="d">分钟 · sync-metrics</div></div></div>';
  h += '<div class="tabs">' + ['人员列表', '同步事件', '对账报告'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'authOrg\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  if (cur === '人员列表') {
    h += qbar(qi('姓名/工号', 150) + qs(['全部部门', '信息中心', '行政部', '财务部', '运营中心', '内容中心', '数据中心']) + qs(['同步状态', '已同步', '待确认', '失败重试', '死信']));
    let rows = '';
    AUTH_USERS.forEach(function (u) {
      rows += '<tr><td style="font-weight:500;cursor:pointer" onclick="toast(\'人员详情抽屉 · 生效岗位模板+权限概要\',\'success\')">' + sens(u.name) + '</td><td class="mono num">' + u.no + '</td><td>' + u.dept + '</td><td>' + u.post + '</td>' +
        '<td>' + tag(u.sync, u.sync === '已同步' ? 'green' : 'orange') + '</td><td class="num" style="color:var(--text2);font-size:12px">' + u.login + '</td>' +
        '<td><span class="btn-txt btn" onclick="toast(\'同步事件轨迹\',\'success\')">事件</span></td></tr>';
    });
    h += tbl(['姓名', '工号', '部门', '岗位', '同步状态', '最近同步', '操作'], rows);
  } else if (cur === '同步事件') {
    let rows = '';
    AUTH_EVENTS.forEach(function (e) {
      rows += '<tr><td style="font-weight:500">' + e.type + '</td><td>' + sens(e.person) + '</td><td>' + e.change + '</td>' +
        '<td>' + tag(e.status, e.status === '已同步' ? 'green' : 'orange') + '</td>' +
        '<td>' + (e.status === '待处理' ? '<button class="btn btn-sec btn-sm" onclick="replayEvt(this,\'' + e.person + '\')">重放</button>' : '<span style="font-size:12px;color:var(--text2)">—</span>') + '</td></tr>';
    });
    h += tbl(['事件类型', '人员', '变更内容', '状态', '操作'], rows);
  } else {
    h += tbl(['对账时间', '差异数', '修正数', '失败明细', '操作'], '<tr><td class="num">2026-09-30 08:00</td><td class="num">2</td><td class="num pos">2</td><td>—</td><td><span class="btn-txt btn" onclick="toast(\'下载对账报告 CSV\',\'success\')">下载</span></td></tr>');
    h += '<div class="hint">POST /auth/org/reconcile · clientToken 幂等 · 仅 R1。</div>';
  }
  return h;
};
PAGES.authPosition = function () {
  let h = pgHead('authPosition', '<button class="btn btn-sec" onclick="exportX(this,\'岗位模板\',AUTH_TMPL.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="toast(\'新建模板 · POST /auth/position/template\',\'success\')">' + ic('plus', 15) + '新建模板</button>');
  h += '<div class="hint" style="margin-bottom:10px">AUTH-003 · 数据范围 dataScope（全部/本部门/IP组/本人 · 本部门不含下级）在此维护 · <b>非</b>独立「数据权限」菜单。</div>';
  h += qbar(qi('模板名称', 140) + qs(['全部钉钉岗位', '直播运营专员', '数据分析师', '行政主管'], 140) + qs(['状态', '启用', '停用'], 90));
  let rows = '';
  AUTH_TMPL.forEach(function (t) {
    rows += '<tr><td style="font-weight:500">' + t.name + '</td><td>' + t.dept + '</td><td class="num">' + t.perms + '</td>' +
      '<td>' + tag(t.on ? '启用' : '停用', t.on ? 'green' : 'gray') + '</td>' +
      '<td><span class="btn-txt btn" onclick="toast(\'权限 Diff 预览 · POST /auth/position/preview\',\'success\')">Diff</span> ' +
      '<span class="btn-txt btn" onclick="toast(\'编辑生成新版本\',\'success\')">编辑</span></td></tr>';
  });
  h += tbl(['模板名称', '钉钉岗位', '权限概要', '状态', '操作'], rows);
  return h;
};
PAGES.auth = PAGES.authOrg;
function syncDing() {
  toast('已触发钉钉组织架构同步…', 'success');
  setTimeout(function () { toast('同步完成：成功 128 · 失败 0 · 待处理 3', 'success'); }, 1600);
}
function replayEvt(btn, person) {
  btn.disabled = true; btn.textContent = '重放中…';
  setTimeout(function () { toast('事件已重放并同步：' + person, 'success'); }, 900);
}

/* ===================== 07 ASSET 资产管理 ===================== */
const ASSETS = [
  { id: 'AS20260901001', name: '罗技 C920 Pro 摄像头', type: '直播设备', spec: '1080P/30fps', status: '在用', owner: '赵敏', accounts: 1, buy: '2026-06-15', price: 699 },
  { id: 'AS20260831002', name: '索尼 ZV-E10 相机', type: '拍摄设备', spec: '16-50mm 套机', status: '在用', owner: '孙倩', accounts: 2, buy: '2026-05-20', price: 5499 },
  { id: 'AS20260830003', name: '神牛 SL60W 补光灯', type: '直播设备', spec: '60W BI 双色温', status: '在用', owner: '赵敏', accounts: 0, buy: '2026-06-15', price: 459 },
  { id: 'AS20260829004', name: 'iPhone 15 Pro（工作机）', type: '数码设备', spec: '256GB 原色钛', status: '在用', owner: '何舟', accounts: 3, buy: '2026-03-10', price: 8999 },
  { id: 'AS20260828005', name: '声卡 雅马哈 AG03', type: '直播设备', spec: '3 通道调音', status: '闲置', owner: '—', accounts: 0, buy: '2026-04-02', price: 1080 },
  { id: 'AS20260827006', name: '戴尔 U2723QE 显示器', type: '办公设备', spec: '27" 4K IPS', status: '在用', owner: '陈默', accounts: 0, buy: '2026-02-18', price: 3799 },
  { id: 'AS20260826007', name: '大疆 RS3 Mini 稳定器', type: '拍摄设备', spec: '承重 2kg', status: '维修中', owner: '孙倩', accounts: 0, buy: '2025-12-30', price: 1799 },
  { id: 'AS20260825008', name: '绿幕背景架（3m）', type: '直播设备', spec: '折叠式', status: '已报废', owner: '—', accounts: 0, buy: '2025-08-11', price: 320 },
  { id: 'AS20260824009', name: 'MacBook Air M3', type: '数码设备', spec: '16G/512G', status: '在用', owner: '李澈', accounts: 2, buy: '2026-07-08', price: 9499 },
  { id: 'AS20260823010', name: '罗技 MX Keys 键盘', type: '办公设备', spec: '无线蓝牙', status: '在用', owner: '林岚', accounts: 0, buy: '2026-01-25', price: 899 },
  { id: 'AS20260918011', name: '号卡 · 移动 138****5678', type: '手机号/号卡', spec: '全球通商旅 128 元/月', status: '在用', owner: '赵敏', accounts: 1, buy: '2026-01-08', price: 0, phone: '13828715678', carrier: '移动', plan: '128 元/月', acct: 'ACCT-2026-0001', sim: '8986001A2345678901' },
  { id: 'AS20260918012', name: '号卡 · 联通 186****2345', type: '手机号/号卡', spec: '冰淇淋套餐 99 元/月', status: '在用', owner: '孙倩', accounts: 1, buy: '2026-02-15', price: 0, phone: '18666172345', carrier: '联通', plan: '99 元/月', acct: 'ACCT-2026-0002', sim: '8986011B2345678902' },
  { id: 'AS20260918013', name: '号卡 · 电信 189****6789', type: '手机号/号卡', spec: '星卡 39 元/月', status: '在用', owner: '苏杳', accounts: 1, buy: '2026-03-20', price: 0, phone: '18925786789', carrier: '电信', plan: '39 元/月', acct: 'ACCT-2026-0034', sim: '8986031C2345678903' }
];
PAGES.asset = function () {
  let h = pgHead('asset', '<button class="btn btn-sec" onclick="exportX(this,\'资产台账\',ASSETS.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="assetReg()">' + ic('plus', 15) + '资产登记</button>');
  const AT = ['直播设备', '拍摄设备', '数码设备', '办公设备', '手机号/号卡'];
  const ct = state.tab.asset || '全部';
  h += catTabs('asset', AT, ASSETS, function (a) { return a.type; });
  const qr = state.q.asset || {};
  h += qbar(qi('资产编号', 120, qr.k0) + qi('名称', 110, qr.k1) + qs(['全部类型', '直播设备', '拍摄设备', '数码设备', '办公设备', '手机号/号卡'], 108, qr.k2) + qs(['全部状态', '在用', '闲置', '维修中', '已报废'], 108, qr.k3) + qi('责任人', 90, qr.k4) + qi('手机号', 110, qr.k5) + '<input type="date" style="width:130px">' + '<span style="color:var(--text2);font-size:12px">至</span>' + '<input type="date" style="width:130px">', 'qSave(\'asset\')');
  const list = qFilter(ASSETS.filter(function (a) { return ct === '全部' || a.type === ct; }), function (a) { return [a.id, a.name, a.spec, a.owner, a.phone]; }, function (a) { return a.type + '|' + a.status; });
  let rows = '';
  list.forEach(function (a) {
    const i = ASSETS.indexOf(a);
    const stc = { '在用': 'green', '闲置': 'blue', '维修中': 'orange', '已报废': 'gray' }[a.status];
    const isSim = a.type === '手机号/号卡';
    rows += '<tr><td class="mono num" style="color:var(--blue);cursor:pointer" onclick="assetDetail(' + i + ')">' + a.id + '</td><td style="font-weight:500">' + a.name + '</td><td>' + a.type + '</td><td style="color:var(--text2)">' + a.spec + '</td>' +
      (isSim ? '<td class="mono">' + sens(maskPhone(a.phone)) + '</td>' : '<td style="color:var(--text2)">—</td>') +
      '<td>' + tag(a.status, stc) + '</td><td>' + sens(a.owner) + '</td><td class="num">' + a.accounts + '</td><td class="num">' + a.buy + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="assetDetail(' + i + ')">查看</span>' + (isSim ? ' <span class="btn btn-sec btn-sm" style="color:var(--orange);border-color:var(--orange)" onclick="simRecharge(' + i + ')">充值</span>' : '') + '</td></tr>';
  });
  h += tbl(['资产编号', '名称', '类型', '规格', '手机号', '状态', '责任人', '绑定账号数', '采购日期', '操作'], rows);
  return h;
};
/* 分类 Tab（带计数徽标）：catTabs(页面id, 分类数组, 数据源, 取分类值函数) */
function catTabs(pid, cats, data, getCat) {
  const cur = state.tab[pid] || '全部';
  const cnt = function (v) { return v === '全部' ? data.length : data.filter(function (r) { return getCat(r) === v; }).length; };
  let h = '<div class="cattabs">';
  h += '<div class="cattab' + (cur === '全部' ? ' on' : '') + '" onclick="setTab(\'' + pid + '\',\'全部\')">全部 <span class="cbadge">' + cnt('全部') + '</span></div>';
  cats.forEach(function (v) {
    h += '<div class="cattab' + (cur === v ? ' on' : '') + '" onclick="setTab(\'' + pid + '\',\'' + v + '\')">' + v + ' <span class="cbadge">' + cnt(v) + '</span></div>';
  });
  h += '</div>';
  return h;
}
/* 查询条件回存（查询按钮触发） */
function qSave(page) {
  const bar = $('#content .qbar');
  if (bar) {
    const vals = [];
    bar.querySelectorAll('input,select').forEach(function (el) { vals.push(el.value); });
    state.q[page] = { k0: vals[0] || '', k1: vals[1] || '', k2: vals[2] || '', k3: vals[3] || '', k4: vals[4] || '', k5: vals[5] || '', k6: vals[6] || '' };
  }
  renderPage();
  toast('查询完成 · 共 ' + $('#content tbody tr').length + ' 条结果', 'success');
}
/* ASSET：资产登记表单抽屉 */
function assetReg() {
  const body = frow([
    { k: 'name', label: '资产名称', type: 'text', req: true, ph: '如：罗技 C920 Pro 摄像头 / 号卡 · 移动 138****5678' },
    { k: 'type', label: '资产类型', type: 'select', req: true, opts: ['直播设备', '拍摄设备', '数码设备', '办公设备', '手机号/号卡'] },
    { k: 'phone', label: '手机号（号卡必填）', type: 'text', ph: '11 位手机号，仅「手机号/号卡」类型填写', pre: 'assetTypeSync()' },
    { k: 'spec', label: '规格型号', type: 'text', ph: '如：1080P/30fps 或 套餐名' },
    { k: 'sn', label: '序列号', type: 'text', ph: '机身 SN / SIM 卡 ICCID（选填）' },
    { k: 'buy', label: '采购日期', type: 'date', req: true, val: '2026-09-12' },
    { k: 'price', label: '采购金额', type: 'num', unit: '¥', ph: '0.00' },
    { k: 'owner', label: '责任人', type: 'select', req: true, opts: ['赵敏', '孙倩', '何舟', '林岚', '李澈', '陈默', '苏杳'] },
    { k: 'photo', label: '资产照片', type: 'file', ph: '点击上传资产照片', wide: true },
    { k: 'note', label: '备注', type: 'textarea', ph: '验收情况、随附配件等', wide: true }
  ]);
  openDrawer('资产登记', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="assetRegSubmit()">提交登记</button>', '480px');
}
/* 登记表单：选「手机号/号卡」时手机号字段转必填并高亮 */
function assetTypeSync() {
  const tp = $('#F_type'), ph = $('#F_phone');
  if (!tp || !ph) return;
  if (tp.value === '手机号/号卡') {
    ph.placeholder = '11 位手机号（号卡必填）';
    ph.style.borderColor = 'var(--orange)';
  } else {
    ph.placeholder = '仅「手机号/号卡」类型填写';
    ph.style.borderColor = '';
  }
}
function assetRegSubmit() {
  const tp = $('#F_type') ? $('#F_type').value : '';
  const isSim = tp === '手机号/号卡';
  const reqs = isSim ? ['name', 'type', 'phone', 'buy', 'owner'] : ['name', 'type', 'buy', 'owner'];
  if (!formValidate(reqs)) return;
  const no = 'AS' + '20260912' + String(ASSETS.length + 1).padStart(3, '0');
  const rec = { id: no, name: $('#F_name').value.trim(), type: tp, spec: $('#F_spec').value.trim() || '—', status: '在用', owner: $('#F_owner').value, accounts: 0, buy: $('#F_buy').value || '2026-09-12', price: Number($('#F_price').value || 0) };
  if (isSim) rec.phone = $('#F_phone').value.trim();
  ASSETS.unshift(rec);
  if (state.page === 'asset') renderPage();
  formOk(no, isSim ? '号卡已登记入台账，可绑定账号并发起话费充值' : '资产已登记入台账，可发起领用流转', '');
  toast((isSim ? '号卡登记成功：' : '资产登记成功：') + no, 'success');
}
function assetDetail(i) {
  const a = ASSETS[i];
  const isSim = a.type === '手机号/号卡';
  const flow = isSim ? [
    { t: '开卡入库', d: a.buy + ' · ' + a.carrier + ' · ' + a.plan, c: '' },
    { t: '绑定账号', d: (a.acct || '—') + ' · 平台注册绑定', c: 'gg' },
    { t: '最近充值', d: '2026-08-15 · ¥26,800.00 · 公司对公（BR-017 核对一致）', c: 'gg' },
    { t: '最近盘点', d: '2026-08-31 · 盘点人：林岚 · 结果：正常', c: 'gg' }
  ] : [
    { t: '采购入库', d: a.buy + ' · 采购价 ' + fmtMoney(a.price), c: '' },
    { t: '领用出库', d: a.buy.replace(/-/, '/').replace(/-/, '/') + ' · 赵敏 发起领用', c: '' },
    { t: '绑定直播账号', d: 'ACCT-2026-0003（斗鱼 · 主号）', c: 'gg' },
    { t: '最近盘点', d: '2026-08-31 · 盘点人：林岚 · 结果：正常', c: 'gg' }
  ];
  const simInfo = isSim ? '<div class="dsec">号卡信息</div><div class="kv">' +
    '<div><div class="k">手机号</div><div class="v mono">' + sens(maskPhone(a.phone)) + '</div></div>' +
    '<div><div class="k">运营商</div><div class="v">' + (a.carrier || '—') + '</div></div>' +
    '<div><div class="k">套餐 / 月费</div><div class="v">' + (a.plan || '—') + '</div></div>' +
    '<div><div class="k">ICCID（SIM 序列）</div><div class="v mono">' + sens(a.sim || '—') + '</div></div></div>' : '';
  const bindAcct = isSim && a.acct ? '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="assetToAcct(\'' + a.acct + '\')">' + a.acct + '</td><td>' + ((ACCTS.find(function (x) { return x.id === a.acct; }) || {}).plat || '—') + '</td><td>' + ((ACCTS.find(function (x) { return x.id === a.acct; }) || {}).nick || '—') + '</td><td><span class="btn btn-sec btn-sm" onclick="assetToAcct(\'' + a.acct + '\')">穿透</span></td></tr>' : '';
  const body = '<div class="photo">' + ic('box', 40) + '</div>' +
    '<div class="dsec">基本信息</div><div class="kv">' +
    '<div><div class="k">资产编号</div><div class="v mono">' + a.id + '</div></div><div><div class="k">名称</div><div class="v">' + a.name + '</div></div>' +
    '<div><div class="k">类型 / 规格</div><div class="v">' + a.type + ' · ' + a.spec + '</div></div><div><div class="k">当前状态</div><div class="v">' + tag(a.status, { '在用': 'green', '闲置': 'blue', '维修中': 'orange', '已报废': 'gray' }[a.status]) + '</div></div>' +
    '<div><div class="k">责任人</div><div class="v">' + sens(a.owner) + '</div></div><div><div class="k">采购信息</div><div class="v">' + a.buy + ' · ' + fmtMoney(a.price) + '</div></div></div>' + simInfo +
    '<div class="dsec">绑定账号（' + a.accounts + '）· 正向穿透</div>' +
    (a.accounts ? '<div class="tbl-wrap"><table><thead><tr><th>账号编号</th><th>平台</th><th>昵称</th><th>操作</th></tr></thead><tbody>' + bindAcct +
      (bindAcct && a.accounts > 1 ? '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="assetToAcct(\'ACCT-2026-0003\')">ACCT-2026-0003</td><td>斗鱼</td><td>神鱼电竞直播间</td><td><span class="btn btn-sec btn-sm" onclick="assetToAcct(\'ACCT-2026-0003\')">穿透</span></td></tr>' : '') +
      (!bindAcct ? '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="assetToAcct(\'ACCT-2026-0003\')">ACCT-2026-0003</td><td>斗鱼</td><td>神鱼电竞直播间</td><td><span class="btn btn-sec btn-sm" onclick="assetToAcct(\'ACCT-2026-0003\')">穿透</span></td></tr>' +
        (a.accounts > 1 ? '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="assetToAcct(\'ACCT-2026-0021\')">ACCT-2026-0021</td><td>小红书</td><td>神鱼穿搭日记</td><td><span class="btn btn-sec btn-sm" onclick="assetToAcct(\'ACCT-2026-0021\')">穿透</span></td></tr>' : '') : '') +
      '</tbody></table></div>' : emptyState('暂无绑定账号', '该资产未绑定任何平台账号')) +
    '<div class="dsec">领用流转时间线</div><div class="tl">' +
    flow.map(function (f) { return '<div class="tl-i ' + f.c + '"><div class="tt">' + f.t + '</div><div class="td">' + f.d + '</div></div>'; }).join('') + '</div>';
  openDrawer('资产详情 · ' + a.id, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (isSim ? '<button class="btn" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="simRecharge(' + i + ')">冲话费</button>' : '') +
    '<button class="btn btn-pri" onclick="assetFlow(' + i + ')">发起流转</button>');
}
/* SIM 号卡充值（从资产维度发起，转发到 acctCharge） */
function simRecharge(i) {
  const a = ASSETS[i];
  if (!a || a.type !== '手机号/号卡') return;
  const ai = ACCTS.findIndex(function (x) { return x.id === a.acct; });
  if (ai < 0) { toast('号卡 ' + a.id + ' 未绑定账号，请先在账号管理完成绑定', 'error'); return; }
  closeDrawer();
  acctCharge(ai, i);
}
/* ASSET：发起流转表单 */
function assetFlow(i) {
  const a = ASSETS[i];
  const body = frow([
    { k: 'from', label: '当前责任人', type: 'text', val: a.owner === '—' ? '（无人持有）' : a.owner, disabled: true },
    { k: 'to', label: '目标责任人', type: 'select', req: true, opts: ['赵敏', '孙倩', '何舟', '林岚', '李澈', '陈默'].filter(function (n) { return n !== a.owner; }) },
    { k: 'reason', label: '流转原因', type: 'select', req: true, opts: ['工作调整', '项目需求', '设备维修转移', '离职交接', '其他'] },
    { k: 'note', label: '备注', type: 'textarea', ph: '补充流转说明（选填）', wide: true }
  ]);
  openDrawer('发起流转 · ' + a.id, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="assetFlowSubmit(' + i + ')">提交流转</button>', '480px');
}
function assetFlowSubmit(i) {
  if (!formValidate(['to', 'reason'])) return;
  const a = ASSETS[i];
  const to = $('#F_to').value;
  confirmDlg('确认发起流转？', '资产「' + a.name + '」（' + a.id + '）责任人将由 ' + (a.owner === '—' ? '池内' : a.owner) + ' 变更为 ' + to + '，流转记录将写入资产时间线。', '确认流转', function () {
    a.owner = to;
    if (state.page === 'asset') renderPage();
    closeDrawer();
    toast('流转单已发起：' + a.id + ' → ' + to, 'success');
    hlFirst();
  });
}

/* ===================== 08 ACCT 账号管理 ===================== */
/* ASSET-002 双向穿透：资产 → 账号（正向） */
function assetToAcct(acctId) {
  const i = ACCTS.findIndex(function (a) { return a.id === acctId; });
  if (i < 0) { toast('账号不存在：' + acctId, 'error'); return; }
  toast('穿透跳转：资产 → ' + acctId, 'success');
  acctDetail(i);
}
/* ASSET-002 双向穿透：账号 → 资产（反向） */
function acctToAsset(assetId) {
  const i = ASSETS.findIndex(function (a) { return a.id === assetId; });
  if (i < 0) { toast('资产不存在：' + assetId, 'error'); return; }
  toast('穿透跳转：账号 → ' + assetId, 'success');
  assetDetail(i);
}
const ACCTS = [
  { id: 'ACCT-2026-0001', plat: '抖音', nick: '神鱼体育', owner: '赵敏', rname: '苏杳', st: '在用', frozen: false, last: '2026-09-08', recharge: 126800.00, phone: '13828715678', sim: 'AS20260918011', collectBind: '已绑定', collectorId: 'acc_douyin_88001', collectProbe: '2026-09-29 08:00 成功' },
  { id: 'ACCT-2026-0002', plat: '视频号', nick: '神鱼跑步研究所', owner: '孙倩', rname: '李澈', st: '在用', frozen: false, last: '2026-09-10', recharge: 36200.00, phone: '18666172345', sim: 'AS20260918012', collectBind: '未绑定', collectorId: '', collectProbe: '—' },
  { id: 'ACCT-2026-0003', plat: '斗鱼', nick: '神鱼电竞直播间', owner: '赵敏', rname: '苏杳', st: '在用', frozen: false, last: '2026-09-11', recharge: 88400.00, phone: '13828715678', sim: 'AS20260918011' },
  { id: 'ACCT-2026-0008', plat: '抖音', nick: '神鱼好物优选', owner: '李澈', rname: '李澈', st: '冻结', frozen: true, last: '2026-08-02', recharge: 21900.00, phone: '13592671234', sim: '', collectBind: 'Cookie 失效', collectorId: 'acc_douyin_88014', collectProbe: '2026-09-29 08:02 失败' },
  { id: 'ACCT-2026-0012', plat: 'B 站', nick: '神鱼健身教室', owner: '—', rname: '—', st: '池可领用', frozen: false, last: '2026-08-30', recharge: 5600.00, phone: '13625309876', sim: '' },
  { id: 'ACCT-2026-0021', plat: '小红书', nick: '神鱼穿搭日记', owner: '—', rname: '—', st: '池可领用', frozen: false, last: '2026-09-01', recharge: 4200.00, phone: '13750812364', sim: '' },
  { id: 'ACCT-2026-0034', plat: '快手', nick: '神鱼运动精选', owner: '苏杳', rname: '苏杳', st: '在用', frozen: false, last: '2026-09-12', recharge: 15300.00, phone: '18925786789', sim: 'AS20260918013' },
  { id: 'ACCT-2026-0041', plat: '抖音', nick: '神鱼训练营（旧）', owner: '—', rname: '—', st: '已归还', frozen: false, last: '2026-07-15', recharge: 3100.00, phone: '13567823410', sim: '' },
  { id: 'ACCT-2026-0056', plat: '微博', nick: '神鱼体育官方号', owner: '—', rname: '—', st: '已注销', frozen: true, last: '2026-03-20', recharge: 0, phone: '', sim: '' },
  { id: 'ACCT-2026-0087', plat: '抖音', nick: '神鱼夜跑频道', owner: '王野', rname: '王野', st: '冻结', frozen: true, last: '2026-09-05', recharge: 9800.00, phone: '15827496305', sim: '' }
];
PAGES.acct = function () {
  let h = pgHead('acct', '<button class="btn btn-sec" onclick="exportX(this,\'账号台账\',ACCTS.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="acctApply()">' + ic('plus', 15) + '账号领用</button>');
  h += '<div class="g4"><div class="card stat"><span class="l">账号总数</span><div class="n">56</div><div class="d">覆盖 7 个平台</div></div>' +
    '<div class="card stat"><span class="l">在用</span><div class="n" style="color:var(--green)">86</div><div class="d">占比 61%</div></div>' +
    '<div class="card stat"><span class="l">池可领用</span><div class="n" style="color:var(--blue)">12</div><div class="d">随时可分配</div></div>' +
    '<div class="card stat"><span class="l">本月充值/冲话费</span><div class="n" style="font-size:22px">' + fmtMoney(52600) + '</div><div class="d">账实核对一致率 <span class="pos">98.4%（BR-017）</span></div></div></div>';
  const AP = ['抖音', '视频号', '斗鱼', 'B 站', '小红书', '快手', '微博'];
  const pt = state.tab.acct || '全部';
  h += catTabs('acct', AP, ACCTS, function (a) { return a.plat; });
  const qr = state.q.acct || {};
  h += qbar(qi('账号编号', 120, qr.k0) + qs(['全部平台', '抖音', '视频号', '斗鱼', 'B 站', '小红书', '快手', '微博'], 90, qr.k2) + qs(['全部状态', '在用', '池可领用', '冻结', '已归还', '已注销'], 100, qr.k3) + qi('责任人', 90, qr.k4) + qi('昵称', 110, qr.k1), 'qSave(\'acct\')');
  const stc = { '在用': 'green', '池可领用': 'blue', '冻结': 'orange', '已归还': 'cyan', '已注销': 'gray' };
  const list = qFilter(ACCTS.filter(function (a) { return pt === '全部' || a.plat === pt; }), function (a) { return [a.id, a.nick, a.owner]; }, function (a) { return a.plat + '|' + a.st; });
  let rows = '';
  list.forEach(function (a) {
    const i = ACCTS.indexOf(a);
    const cb = a.collectBind || '—';
    const cbt = cb === '已绑定' ? 'green' : cb.indexOf('失效') >= 0 ? 'red' : cb === '未绑定' ? 'orange' : 'gray';
    rows += '<tr><td class="mono num" style="color:var(--blue);cursor:pointer" onclick="acctDetail(' + i + ')">' + a.id + '</td><td>' + a.plat + '</td><td style="font-weight:500">' + a.nick + '</td>' +
      '<td>' + sens(a.owner) + '</td><td>' + tag(a.st, stc[a.st]) + (a.frozen ? ' <span style="color:var(--red)" title="已冻结">' + ic('shield', 13) + '</span>' : '') + '</td>' +
      '<td>' + tag(cb, cbt) + '</td>' +
    '<td class="num" style="font-size:12px;color:var(--text2)">' + a.last + '</td><td class="num" style="font-weight:500">' + fmtMoney(a.recharge) + '</td>' +
    '<td>' + (a.st === '已注销' ? '<span style="font-size:12px;color:var(--text2)">—</span>' :
      '<button class="btn btn-sm" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="acctCharge(' + i + ')">冲话费</button>') + '</td>' +
    '<td><span class="btn btn-sec btn-sm" onclick="acctDetail(' + i + ')">查看</span></td></tr>';
  });
  h += tbl(['账号编号', '平台', '昵称', '当前责任人', '状态', '采集绑定', '最近领用时间', '累计充值', '冲话费', '操作'], rows);
  h += '<div class="hint">抖音/快手 Cookie 与 Collector bind 在详情 · <b>采集</b> Tab（ADR-047）；不在「数据采集 · 内部配置」维护。</div>';
  return h;
};
/* ACCT：账号领用表单抽屉 */
function acctApply() {
  const pool = ACCTS.filter(function (a) { return a.st === '池可领用'; }).map(function (a) { return a.id + ' · ' + a.plat + ' · ' + a.nick; });
  const body = frow([
    { k: 'acct', label: '选择池中账号', type: 'select', req: true, opts: pool.length ? pool : ['（当前池内暂无可领用账号）'] },
    { k: 'user', label: '领用人', type: 'select', req: true, opts: ['赵敏', '孙倩', '何舟', '李澈', '苏杳'] },
    { k: 'purpose', label: '用途说明', type: 'text', req: true, ph: '如：秋季大促直播使用' },
    { k: 'term', label: '预计使用期限', type: 'select', opts: ['30 天', '90 天', '180 天', '长期（项目制）'] },
    { k: 'urgt', label: '紧急程度', type: 'pills', opts: ['常规', '紧急'], val: '常规' },
    { k: 'note', label: '备注', type: 'textarea', ph: '补充说明（选填）', wide: true }
  ]);
  openDrawer('账号领用申请', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="acctApplySubmit()">提交领用申请</button>', '480px');
}
function acctApplySubmit() {
  if (!formValidate(['acct', 'user', 'purpose'])) return;
  const sel = $('#F_acct').value;
  const no = 'LY20260912-' + String(Math.floor(Math.random() * 90) + 10);
  formOk(no, '领用单已进入「行政确认」审批节点（审批人：林岚）', '');
  toast('领用申请已提交：' + sel, 'success');
}
function acctDetail(i, tab) {
  tab = tab || 'basic';
  const a = ACCTS[i];
  const tl = [
    { t: '账号入库（池）', d: '2026-01-08 · 行政部创建账号档案', c: '' },
    { t: '领用：赵敏', d: '2026-03-02 · 领用单 LY20260302-01', c: '' },
    { t: '充值 +¥50,000.00', d: '2026-05-18 · 财务确认（BR-017 核对一致）', c: 'gg' },
    { t: '归还入池', d: '2026-08-02 · 赵敏发起归还', c: 'oo' },
    { t: '风控冻结', d: '2026-09-05 · 风险分超阈值', c: 'oo' }
  ];
  const chargeTl = (a.charges || []).map(function (c) {
    return { t: '冲话费 +' + fmtMoney(c.amt), d: c.d + ' · 号卡 ' + (c.phone || '—') + ' · 凭证 ' + c.vou + ' · ' + c.way + '（BR-017 核对一致）', c: 'gg' };
  });
  if (a.id === 'ACCT-2026-0001') tl.splice(3, 0, { t: '冲话费 +¥26,800.00', d: '2026-08-15 · 凭证 CZ20260815-03 · 公司对公（BR-017 核对一致）', c: 'gg' });
  const tabHtml = ['basic', 'collect', 'flow', 'asset'].map(function (t) {
    const lbl = { basic: '基本信息', collect: '采集', flow: '领用时间线', asset: '关联资产' }[t];
    return '<div class="tab' + (tab === t ? ' on' : '') + '" onclick="acctDetail(' + i + ',\'' + t + '\')">' + lbl + '</div>';
  }).join('');
  let pane = '';
  if (tab === 'collect') {
    const cb = a.collectBind || '未绑定';
    pane = '<div class="hint" style="margin-bottom:12px">凭证 SSOT 在本 Tab；保存后须「导入 Collector」完成 bind（ADR-047）。</div>' +
      '<div class="kv"><div><div class="k">绑定状态</div><div class="v">' + tag(cb, cb === '已绑定' ? 'green' : cb.indexOf('失效') >= 0 ? 'red' : 'orange') + '</div></div>' +
      '<div><div class="k">Collector ID</div><div class="v mono">' + (a.collectorId || '—') + '</div></div>' +
      '<div><div class="k">最近探活</div><div class="v">' + (a.collectProbe || '—') + '</div></div></div>' +
      '<div class="dsec">凭证（AES 脱敏）</div>' +
      frow([{ k: 'ck', label: 'Cookie / Token', type: 'text', ph: '留空表示不更新', val: '' }]) +
      '<div class="rowline" style="gap:8px;margin-top:12px;flex-wrap:wrap">' +
      '<button class="btn btn-sec btn-sm" onclick="toast(\'扫码登录 QR（ADR-050）\',\'success\')">扫码登录</button>' +
      '<button class="btn btn-sec btn-sm" onclick="toast(\'探活成功\',\'success\')">测试连接</button>' +
      '<button class="btn btn-pri btn-sm" onclick="acctCollectorBind(' + i + ')">导入 Collector</button>' +
      '<button class="btn btn-sec btn-sm" onclick="go(\'collectLog\');toast(\'已带账号筛选打开日志\',\'success\')">查看采集日志</button></div>';
  } else if (tab === 'flow') {
    pane = '<div class="dsec">领用 / 充值时间线</div><div class="tl">' + chargeTl.concat(tl).map(function (f) { return '<div class="tl-i ' + f.c + '"><div class="tt">' + f.t + '</div><div class="td">' + f.d + '</div></div>'; }).join('') + '</div>';
  } else if (tab === 'asset') {
    pane = '<div class="dsec">关联资产（2）· 反向穿透（ASSET-002）</div><div class="tbl-wrap"><table><thead><tr><th>资产编号</th><th>名称</th><th>状态</th><th>操作</th></tr></thead><tbody>' +
      '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="acctToAsset(\'AS20260901001\')">AS20260901001</td><td>罗技 C920 Pro 摄像头</td><td>' + tag('在用', 'green') + '</td><td><span class="btn btn-sec btn-sm" onclick="acctToAsset(\'AS20260901001\')">穿透</span></td></tr>' +
      '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="acctToAsset(\'AS20260830003\')">AS20260830003</td><td>神牛 SL60W 补光灯</td><td>' + tag('在用', 'green') + '</td><td><span class="btn btn-sec btn-sm" onclick="acctToAsset(\'AS20260830003\')">穿透</span></td></tr></tbody></table></div>';
  } else {
    pane = '<div class="kv">' +
      '<div><div class="k">账号编号</div><div class="v mono">' + a.id + '</div></div><div><div class="k">平台 / 昵称</div><div class="v">' + a.plat + ' · ' + a.nick + '</div></div>' +
      '<div><div class="k">当前责任人</div><div class="v">' + sens(a.owner) + '</div></div><div><div class="k">状态</div><div class="v">' + tag(a.st, { '在用': 'green', '池可领用': 'blue', '冻结': 'orange', '已归还': 'cyan', '已注销': 'gray' }[a.st]) + '</div></div>' +
      '<div><div class="k">实名人</div><div class="v">' + (a.rname && a.rname !== '—' ? sens(a.rname) : '—') + '</div></div>' +
      '<div><div class="k">绑定手机号</div><div class="v mono">' + (a.phone ? sens(maskPhone(a.phone)) : '—') + '</div></div><div><div class="k">累计充值</div><div class="v">' + fmtMoney(a.recharge) + '</div></div></div>';
  }
  const body = '<div class="tabs" style="margin-top:0">' + tabHtml + '</div>' + pane;
  openDrawer('账号详情 · ' + a.id, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (a.st !== '已注销' ? '<button class="btn" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="acctCharge(' + i + ')">冲话费</button>' : '') +
    (a.st === '池可领用' ? '<button class="btn btn-pri" onclick="acctApply()">申请领用</button>' :
      a.frozen ? '<button class="btn btn-pri" style="background:var(--orange)" onclick="acctUnfreeze(' + i + ')">申请解冻</button>' :
        '<button class="btn btn-pri" onclick="acctReturn(' + i + ')">发起归还</button>'));
}
function acctCollectorBind(i) {
  const a = ACCTS[i];
  a.collectBind = '已绑定';
  a.collectorId = a.collectorId || ('acc_' + (a.plat === '快手' ? 'kuaishou' : 'douyin') + '_bind');
  a.collectProbe = '2026-09-29 ' + (new Date().toTimeString().slice(0, 5)) + ' 成功';
  toast('已导入 Collector：' + a.collectorId, 'success');
  acctDetail(i, 'collect');
}
/* ACCT：申请解冻（红色警示确认） */
function acctUnfreeze(i) {
  const a = ACCTS[i];
  const body = frow([
    { k: 'reason', label: '解冻原因', type: 'select', req: true, opts: ['风险复核通过', '误报解除', '投诉已处理完毕', '其他'] },
    { k: 'term', label: '预计解冻期限', type: 'select', opts: ['立即解冻', '24 小时后', '72 小时后'] },
    { k: 'note', label: '补充说明', type: 'textarea', ph: '提供复核证据或说明（选填）', wide: true }
  ]);
  openDrawer('申请解冻 · ' + a.id, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" style="background:var(--orange)" onclick="acctUnfreezeSubmit(' + i + ')">提交解冻申请</button>', '480px');
}
function acctUnfreezeSubmit(i) {
  if (!formValidate(['reason'])) return;
  const a = ACCTS[i];
  confirmDlg('确认提交解冻申请？', '账号 ' + a.id + '（' + a.nick + '）当前为「冻结」状态，解冻申请将提交风控复核。', '确认提交',
    function () {
      closeDrawer();
      toast('解冻申请已提交，待风控复核：' + a.id, 'success');
    }, { danger: true, warn: '解冻后账号将恢复使用，请确认已核实冻结原因' });
}
/* ACCT：发起归还 */
function acctReturn(i) {
  const a = ACCTS[i];
  confirmDlg('确认发起归还？', '账号 ' + a.id + '（' + a.plat + ' · ' + a.nick + '）归还后将释放至「池可领用」，当前责任人 ' + a.owner + ' 的绑定关系将被解除。', '确认归还', function () {
    a.st = '已归还'; a.owner = '—'; a.last = '2026-09-12';
    if (state.page === 'acct') renderPage();
    closeDrawer();
    toast('归还单已发起，账号已释放至池：' + a.id, 'success');
    hlFirst();
  }, { warn: '归还前请确认账号内未结算收入与粉丝资产已交接完毕' });
}
/* ACCT-004：冲话费管理表单（对手机号充值 · 含 BR-017 账实核对） */
function acctCharge(i, fromSim) {
  const a = ACCTS[i];
  if (!a) return;
  /* 找到该账号绑定的号卡资产（优先 ACCTS.sim 引用，兜底按 phone 匹配） */
  const simIdx = a.sim ? ASSETS.findIndex(function (x) { return x.id === a.sim; }) :
    ASSETS.findIndex(function (x) { return x.type === '手机号/号卡' && x.phone === a.phone; });
  const sim = simIdx >= 0 ? ASSETS[simIdx] : null;
  const sims = ASSETS.filter(function (x) { return x.type === '手机号/号卡'; });
  const simOpts = sims.map(function (s, idx) {
    const si = ASSETS.indexOf(s);
    return { v: si, t: s.carrier + ' · ' + maskPhone(s.phone) + '（' + s.plan + '）' };
  });
  const body = frow([
    { k: 'csim', label: '充值号卡（手机号）', type: 'select', req: true, opts: simOpts.length ? simOpts.map(function (o) { return o.t; }) : ['（暂无在册号卡，请先登记号卡资产）'], val: sim ? sim.carrier + ' · ' + maskPhone(sim.phone) + '（' + sim.plan + '）' : '' },
    { k: 'camt', label: '冲话费金额', type: 'num', req: true, unit: '¥', ph: '0.00', pre: 'acctChargeCalc()' },
    { k: 'cway', label: '充值渠道', type: 'pills', opts: ['公司对公', '个人垫付报销', '平台赠送', '话费直充'], val: '公司对公' },
    { k: 'creal', label: '平台实际到账', type: 'num', req: true, unit: '¥', ph: '0.00', pre: 'acctChargeCalc()' },
    { k: 'cvou', label: '凭证编号', type: 'text', req: true, ph: '如：CZ20260918-001' },
    { k: 'cproof', label: '充值凭证截图', type: 'file', ph: '点击上传平台后台截图', wide: true },
    { k: 'cnote', label: '备注', type: 'textarea', ph: '活动补贴、赠送口径说明（选填）', wide: true }
  ]) + '<div class="dsec">号卡与账号绑定关系</div>' +
    '<div class="kv" style="background:var(--bg);border-radius:10px;padding:12px 14px">' +
    '<div><div class="k">充值手机号</div><div class="v mono" id="ccSim">' + (sim ? sens(maskPhone(sim.phone)) : sens(maskPhone(a.phone || '')) || '—') + '</div></div>' +
    '<div><div class="k">入账账号（聚合根）</div><div class="v mono">' + a.id + '</div></div>' +
    '<div><div class="k">充值后归属</div><div class="v">话费余额计入账号 ' + a.id + '，物理充值落在号卡 SIM</div></div></div>' +
    '<div class="dsec">账实核对（BR-017 · 实时校验）</div>' +
    '<div class="kv" id="ccChk" style="background:var(--bg);border-radius:10px;padding:12px 14px">' +
    '<div><div class="k">申请金额</div><div class="v num" id="ccA">—</div></div>' +
    '<div><div class="k">平台到账</div><div class="v num" id="ccR">—</div></div>' +
    '<div><div class="k">核对结果</div><div class="v" id="ccD">待输入</div></div></div>';
  openDrawer('冲话费 · ' + (sim ? maskPhone(sim.phone) : a.id) + '（' + a.nick + '）', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" style="background:var(--orange)" onclick="acctChargeSubmit(' + i + ')">提交冲话费</button>', '520px');
}
/* 冲话费账实核对实时计算 */
function acctChargeCalc() {
  const amt = Number($('#F_camt').value || 0), real = Number($('#F_creal').value || 0);
  if ($('#ccA')) $('#ccA').textContent = amt ? fmtMoney(amt) : '—';
  if ($('#ccR')) $('#ccR').textContent = real ? fmtMoney(real) : '—';
  const d = $('#ccD');
  if (d) {
    if (!amt || !real) { d.textContent = '待输入'; d.style.color = ''; }
    else if (amt === real) { d.textContent = '✓ 账实一致'; d.style.color = 'var(--green)'; }
    else { d.textContent = '⚠ 差异 ' + fmtMoney(Math.abs(amt - real)) + '，需说明原因'; d.style.color = 'var(--red)'; }
  }
}
/* ACCT-004：提交闭环（差异拦截 + 充值入账 + 时间线留痕 + 号卡关联） */
function acctChargeSubmit(i) {
  const a = ACCTS[i];
  if (!a) return;
  if (!formValidate(['camt', 'creal', 'cvou'])) return;
  acctChargeCalc();
  const amt = Number($('#F_camt').value || 0), real = Number($('#F_creal').value || 0);
  if (amt !== real) {
    toast('账实核对不通过（BR-017）：申请 ' + fmtMoney(amt) + ' ≠ 到账 ' + fmtMoney(real) + '，请在备注说明差异原因后由财务复核', 'error');
    return;
  }
  /* 解析所选号卡（充值对象：手机号） */
  const selTxt = $('#F_csim') ? $('#F_csim').value : '';
  const sims = ASSETS.filter(function (x) { return x.type === '手机号/号卡'; });
  let sim = sims.find(function (s) { return s.carrier + ' · ' + maskPhone(s.phone) + '（' + s.plan + '）' === selTxt; });
  if (!sim && sims.length === 1) sim = sims[0];
  const phone = sim ? maskPhone(sim.phone) : (a.phone ? maskPhone(a.phone) : '—');
  const simId = sim ? sim.id : '';
  const way = ($('#F_cway') && $('#F_cway').value) ? $('#F_cway').value : '公司对公';
  confirmDlg('确认提交冲话费？', '号卡 ' + phone + '（' + simId + '）为账号 ' + a.id + '（' + a.nick + '）充值 ' + fmtMoney(amt) + '，核对一致后将累计入充值台账并写入时间线。', '提交冲话费', function () {
    a.recharge += amt;
    if (!a.charges) a.charges = [];
    a.charges.unshift({ amt: amt, vou: $('#F_cvou').value.trim(), d: '2026-09-18', way: way, phone: phone, sim: simId });
    if (state.page === 'acct') renderPage();
    closeDrawer();
    toast('冲话费已入账：' + phone + ' → 账号 ' + a.id + ' · ' + fmtMoney(amt) + '（累计 ' + fmtMoney(a.recharge) + ' · 已写入时间线）', 'success');
    hlFirst();
  });
}

/* ===================== CORP 公司资产（走查 #8） ===================== */
const CORP_CO = [{ id: 'c01', name: '神鱼互娱', cap: '12 / 20', st: '启用' }, { id: 'c02', name: '神鱼传媒', cap: '4 / 10', st: '启用' }];
const CORP_PS = [{ id: '9001', name: '苏杳', idn: '320***********1234', agent: '—', st: '在职' }, { id: '9002', name: '赵敏', idn: '310***********5566', agent: '中介A', st: '在职' }];
const CORP_PH = [{ id: 'p01', model: 'iPhone 15 Pro', person: '苏杳', st: '在用', devNo: 'PH-2026-001' }, { id: 'p02', model: 'Android 采集机', person: '赵敏', st: '在用', devNo: 'PH-2026-002' }];
const CORP_SIM = [{ id: 's01', no: '138****5678', person: '苏杳', fee: 128, op: '移动' }, { id: 's02', no: '139****2211', person: '赵敏', fee: 59, op: '联通' }];
function corpAcctList(pageId) {
  const meta = CORP_PLAT[pageId];
  if (!meta) return [];
  if (meta.plat === '公众号') return [];
  return ACCTS.filter(function (a) { return a.plat === meta.plat; });
}
function corpAcctPage(pageId) {
  const meta = CORP_PLAT[pageId];
  const list = corpAcctList(pageId);
  let h = pgHead(pageId, '<button class="btn btn-sec" onclick="exportX(this,\'' + meta.plat + '账号\',' + list.length + ')">导出</button>' +
    '<button class="btn btn-pri" onclick="masterAcctAdd()">' + ic('plus', 15) + '登记账号</button>');
  h += '<div class="hint" style="margin-bottom:8px">UX-M4 P-M4-008 · <code>platformType=' + meta.dict + '</code> · 采集 Tab 见 ADR-047 · <b>≠</b> 数据采集·竞品账号配置。</div>';
  h += qbar(qi('账号编号/昵称', 130) + qi('IP 组', 100) + qs(['全部状态', '在用', '池可领用', '冻结', '已归还'], 100) + qi('实名人', 90), 'qSave(\'' + pageId + '\')');
  let rows = '';
  const cols = meta.collect ? 7 : 6;
  if (!list.length) {
    rows = '<tr><td colspan="' + cols + '" style="text-align:center;padding:28px;color:var(--text2)">暂无「' + meta.plat + '」平台账号 · 请先完成资源管理主数据后登记</td></tr>';
  } else {
    list.forEach(function (a) {
      const i = ACCTS.indexOf(a);
      const cb = a.collectBind || '—';
      const cbt = cb === '已绑定' ? 'green' : cb.indexOf('失效') >= 0 ? 'red' : cb === '未绑定' ? 'orange' : 'gray';
      rows += '<tr><td class="mono num" style="color:var(--blue);cursor:pointer" onclick="corpAcctOpen(' + i + ',\'' + pageId + '\')">' + a.id + '</td><td style="font-weight:500">' + a.nick + '</td><td>' + sens(a.owner) + '</td><td>' + sens(a.rname) + '</td><td>' + tag(a.st, a.st === '在用' ? 'green' : 'blue') + '</td>' +
        (meta.collect ? '<td>' + tag(cb, cbt) + '</td>' : '') +
        '<td><span class="btn btn-sec btn-sm" onclick="corpAcctOpen(' + i + ',\'' + pageId + '\')">详情</span></td></tr>';
    });
  }
  h += tbl(meta.collect ? ['账号编号', '昵称', '责任人', '实名人', '状态', '采集', '操作'] : ['账号编号', '昵称', '责任人', '实名人', '状态', '操作'], rows);
  h += '<div class="hint">GET /corp/account/page?platformType=' + meta.dict + ' → OPS platform list · 领用流程入口 BLOCKED（见 PRD Q3）。</div>';
  return h;
}
function corpAcctOpen(i, pageId) {
  const meta = CORP_PLAT[pageId] || CORP_PLAT.caDouyin;
  const a = ACCTS[i];
  if (!a) return;
  if (meta.collect) {
    acctDetail(i, 'basic');
    return;
  }
  openDrawer(meta.plat + ' · ' + a.nick, '<div class="kv"><div><div class="k">账号编号</div><div class="v mono">' + a.id + '</div></div><div><div class="k">实名人</div><div class="v">' + sens(a.rname) + '</div></div>' +
    '<div><div class="k">责任人</div><div class="v">' + sens(a.owner) + '</div></div><div><div class="k">状态</div><div class="v">' + a.st + '</div></div></div>' +
    '<div class="hint">详情 Tab 对齐 P-M4-009；采集 Tab 仅 DOUYIN/KUAISHOU/CHANNELS 等平台。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri btn-sm" onclick="acctDetail(' + i + ',\'collect\');closeDrawer()">采集 Tab</button>', '720px');
}
CORP_ACCT_IDS.forEach(function (pid) {
  PAGES[pid] = (function (id) { return function () { return corpAcctPage(id); }; })(pid);
});
PAGES.corpAcct = PAGES.caDouyin;
function corpResCompany() {
  let h = pgHead('crCompany', '<button class="btn btn-sec" onclick="exportX(this,\'公司\',' + CORP_CO.length + ')">导出</button><button class="btn btn-pri" onclick="toast(\'新建公司 · 公众号容量\',\'success\')">' + ic('plus', 15) + '新建公司</button>');
  h += '<div class="hint" style="margin-bottom:8px">P-M4-001 · 公众号容量/扩容 · VA 扩展字段 BLOCKED 至 API-VA-MAINT。</div>';
  h += qbar(qi('公司名称', 140) + qi('信用代码', 140) + qs(['全部状态', '启用', '停用'], 90));
  let rows = '';
  CORP_CO.forEach(function (r, idx) {
    rows += '<tr><td class="mono">' + r.id + '</td><td style="font-weight:500">' + r.name + '</td><td class="num">' + r.cap + '</td><td>' + tag(r.st, 'green') + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="corpCoDetail(' + idx + ')">详情</span></td></tr>';
  });
  h += tbl(['公司 ID', '名称', '公众号容量', '状态', '操作'], rows);
  return h;
}
function corpCoDetail(i) {
  const r = CORP_CO[i];
  openDrawer('公司 · ' + r.name, '<div class="kv"><div><div class="k">容量</div><div class="v">' + r.cap + '</div></div><div><div class="k">状态</div><div class="v">' + r.st + '</div></div></div>' +
    '<div class="hint">详情含扩容记录、关联账号表 · GET /corp/resource/company/{id}</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-sec btn-sm" onclick="go(\'caWechatOfficial\');closeDrawer()">关联公众号</button>', '560px');
}
PAGES.crCompany = corpResCompany;
PAGES.crRealname = function () {
  let h = pgHead('crRealname', '<button class="btn btn-sec" onclick="exportX(this,\'实名人\',' + CORP_PS.length + ')">导出</button><button class="btn btn-pri" onclick="toast(\'新增实名人 · 证件 AES\',\'success\')">' + ic('plus', 15) + '新增实名人</button>');
  h += qbar(qi('姓名', 120) + qs(['全部状态', '在职', '离职'], 90));
  let rows = '';
  CORP_PS.forEach(function (r, idx) {
    rows += '<tr><td class="mono">' + r.id + '</td><td>' + sens(r.name) + '</td><td class="mono">' + r.idn + '</td><td>' + r.agent + '</td><td>' + tag(r.st, 'green') + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="corpRnDetail(' + idx + ')">详情</span></td></tr>';
  });
  h += tbl(['实名人 ID', '姓名', '证件号', '中介人', '状态', '操作'], rows);
  h += '<div class="hint">P-M4-003/004 · 证件影像扩展见 CERT / VA P-VA-M-008 Tab。</div>';
  return h;
};
function corpRnDetail(i) {
  const r = CORP_PS[i];
  openDrawer('实名人 · ' + sens(r.name), '<div class="kv"><div><div class="k">证件号</div><div class="v mono">' + r.idn + '</div></div><div><div class="k">中介人</div><div class="v">' + r.agent + '</div></div></div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-sec btn-sm" onclick="go(\'crCert\');closeDrawer()">证件索引</button>', '480px');
}
PAGES.crSim = function () {
  let h = pgHead('crSim', '<button class="btn btn-sec" onclick="exportX(this,\'手机卡\',' + CORP_SIM.length + ')">导出</button><button class="btn btn-pri" onclick="toast(\'新增 SIM · PhoneSelect 强关联\',\'success\')">' + ic('plus', 15) + '新增手机卡</button>');
  h += qbar(qi('号码', 120) + qs(['运营商', '移动', '联通', '电信'], 90) + qi('实名人', 90));
  let rows = '';
  CORP_SIM.forEach(function (r, idx) {
    rows += '<tr><td class="mono">' + r.id + '</td><td>' + r.no + '</td><td>' + r.op + '</td><td>' + r.person + '</td><td class="num">' + fmtMoney(r.fee) + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="corpSimDetail(' + idx + ')">详情</span></td></tr>';
  });
  h += tbl(['卡 ID', '号码', '运营商', '实名人', '月租', '操作'], rows);
  h += '<div class="hint">P-M4-006 · 卡级实名人 ADR-074 · 跨平台账号侧滑 P-M4-007。</div>';
  return h;
};
function corpSimDetail(i) {
  const r = CORP_SIM[i];
  openDrawer('手机卡 · ' + r.no, '<div class="kv"><div><div class="k">实名人</div><div class="v">' + r.person + '</div></div><div><div class="k">月租</div><div class="v num">' + fmtMoney(r.fee) + '</div></div></div>' +
    '<p style="margin-top:12px;font-size:13px;color:var(--text2)">关联平台账号（dedupe）</p><table class="tbl"><thead><tr><th>账号</th><th>平台</th></tr></thead><tbody><tr><td>ACCT-2026-0001</td><td>抖音</td></tr></tbody></table>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '520px');
}
PAGES.crCert = function () {
  let h = pgHead('crCert', '<button class="btn btn-pri" onclick="certAdd()">' + ic('plus', 15) + '上传证件</button>');
  h += '<div class="hint" style="margin-bottom:8px">CERT-001 索引入口 · 水印分级查看 · 原顶级 cert 页为 IA 遗留。</div>';
  h += qbar(qi('持有人', 110) + qs(['证件类型', '居民身份证', '护照', '健康证'], 120) + qs(['状态', '已归档', '待补交', '已过期'], 100));
  let rows = '';
  CERTS.slice(0, 6).forEach(function (c, idx) {
    rows += '<tr><td>' + c.holder + '</td><td>' + c.type + '</td><td class="mono">' + maskId(c.no) + '</td><td>' + c.exp + '</td><td>' + tag(c.st, c.st === '已归档' ? 'green' : 'orange') + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="certDetail(' + idx + ')">分级查看</span></td></tr>';
  });
  h += tbl(['持有人', '类型', '证件号', '有效期至', '状态', '操作'], rows);
  return h;
};
PAGES.corpRes = PAGES.crCompany;
function corpAssetPage(pageId, types, blockedNote) {
  const list = ASSETS.filter(function (a) { return types.indexOf(a.type) >= 0; });
  let h = pgHead(pageId, '<button class="btn btn-sec" onclick="exportX(this,\'设备\',' + list.length + ')">导出</button><button class="btn btn-pri" onclick="assetReg()">' + ic('plus', 15) + '资产登记</button>');
  h += '<div class="hint" style="margin-bottom:8px">' + blockedNote + '</div>';
  h += qbar(qi('资产编号', 120) + qi('名称', 110) + qs(['全部状态', '在用', '闲置', '维修中', '已报废'], 108) + qi('责任人', 90));
  let rows = '';
  if (!list.length) {
    rows = '<tr><td colspan="6" style="text-align:center;padding:28px;color:var(--text2)">无匹配设备 · 确认 asset_type 字典后灌数</td></tr>';
  } else {
    list.forEach(function (a) {
      const i = ASSETS.indexOf(a);
      rows += '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="assetDetail(' + i + ')">' + a.id + '</td><td style="font-weight:500">' + a.name + '</td><td>' + a.type + '</td><td>' + tag(a.status, a.status === '在用' ? 'green' : 'gray') + '</td><td>' + sens(a.owner) + '</td>' +
        '<td><span class="btn btn-sec btn-sm" onclick="assetDetail(' + i + ')">穿透</span></td></tr>';
    });
  }
  h += tbl(['资产编号', '名称', '类型', '状态', '责任人', '操作'], rows);
  h += '<div class="hint">GET /corp/device/*/page · ASSET-001 正向穿透 · API BLOCKED 直至 dict_asset_type 确认。</div>';
  return h;
}
PAGES.cdOffice = function () { return corpAssetPage('cdOffice', ['办公设备'], 'ASSET-001 · 候选 filter <code>asset_type=OFFICE</code>（BLOCKED）'); };
PAGES.cdLive = function () { return corpAssetPage('cdLive', ['直播设备', '拍摄设备'], 'ASSET-001 · 直播+拍摄合并候选（BLOCKED · PRD Q2）'); };
PAGES.cdPhone = function () {
  let h = pgHead('cdPhone', '<button class="btn btn-sec" onclick="exportX(this,\'手机设备\',' + CORP_PH.length + ')">导出</button><button class="btn btn-pri" onclick="toast(\'登记手机 · UserSelect 保管人\',\'success\')">' + ic('plus', 15) + '登记手机</button>');
  h += '<div class="hint" style="margin-bottom:8px">P-M4-005 · <code>oa_phone</code> · ADR-011 不挂实名人列（关联经账号）。</div>';
  h += qbar(qi('设备编号', 120) + qs(['类型', 'Android', 'iPhone'], 100) + qi('保管人', 90));
  let rows = '';
  CORP_PH.forEach(function (r, idx) {
    rows += '<tr><td class="mono">' + r.devNo + '</td><td>' + r.model + '</td><td>' + r.person + '</td><td>' + tag(r.st, 'green') + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="corpPhoneDetail(' + idx + ')">详情</span></td></tr>';
  });
  h += tbl(['设备编号', '型号', '保管人', '状态', '操作'], rows);
  return h;
};
function corpPhoneDetail(i) {
  const r = CORP_PH[i];
  openDrawer('手机设备 · ' + r.model, '<div class="kv"><div><div class="k">编号</div><div class="v mono">' + r.devNo + '</div></div><div><div class="k">保管人</div><div class="v">' + r.person + '</div></div></div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-sec btn-sm" onclick="go(\'caDouyin\');closeDrawer()">绑定账号</button>', '480px');
}
PAGES.corpDev = PAGES.cdPhone;
function maskId(s) {
  if (!s || s.length < 8) return s;
  return s.slice(0, 3) + '***********' + s.slice(-4);
}

/* ===================== 06 CERT 证件档案 ===================== */
const CERTS = [
  { holder: '苏杳', type: '居民身份证', no: '1101051999032861234', issue: '2019-04-12', exp: '2026-10-08', days: 26, st: '已归档' },
  { holder: '赵敏', type: '居民身份证', no: '4403011992071556234', issue: '2020-07-20', exp: '2030-07-20', days: 1412, st: '已归档' },
  { holder: '孙倩', type: '居民身份证', no: '3301021995110828234', issue: '2021-11-15', exp: '2026-12-04', days: 83, st: '已归档' },
  { holder: '何舟', type: '护照', no: 'E83456123', issue: '2024-02-01', exp: '2029-02-01', days: 867, st: '已归档' },
  { holder: '苏杳', type: '主播资质证', no: 'ZB2026-04172', issue: '2026-01-10', exp: '2028-01-10', days: 485, st: '已归档' },
  { holder: '李澈', type: '居民身份证', no: '5101041998052334234', issue: '2019-05-30', exp: '2029-05-30', days: 991, st: '待补交' },
  { holder: '周晴', type: '会计从业资格证', no: 'KJ2021-33421', issue: '2021-06-18', exp: '2027-06-18', days: 649, st: '已归档' },
  { holder: '陈默', type: '居民身份证', no: '4201061994021178234', issue: '2020-02-25', exp: '2025-06-08', days: -96, st: '已过期' },
  { holder: '王野', type: '居民身份证', no: '3201051996123045234', issue: '2021-12-05', exp: '2031-12-05', days: 1897, st: '审核中' },
  { holder: '苏杳', type: '健康证', no: 'JK2026-11892', issue: '2026-03-01', exp: '2027-03-01', days: 170, st: '已归档' }
];
PAGES.cert = function () {
  let h = pgHead('cert', '<button class="btn btn-pri" onclick="certAdd()">' + ic('plus', 15) + '证件归档</button>');
  h += '<div class="card" style="margin-bottom:16px"><div class="rowline" style="justify-content:space-between;margin-bottom:8px">' +
    '<div class="rowline"><span style="color:var(--blue)">' + ic('id', 18) + '</span><b style="font-size:15px">档案数字化率 92%</b><span style="font-size:12px;color:var(--text2)">142 / 154 份证件已完成扫描归档</span></div>' +
    '<span style="font-size:12px;color:var(--blue);font-weight:600">目标 100% · 2026 Q4</span></div>' +
    '<div class="pg" style="height:8px;width:100%"><i style="width:92%"></i></div></div>';
  h += qbar(qi('持有人', 110, (state.q.cert || {}).k0) + qs(['全部类型', '居民身份证', '护照', '主播资质证', '健康证', '会计从业资格证'], 130, (state.q.cert || {}).k1) + qs(['档案状态', '已归档', '待补交', '审核中', '已过期'], 100, (state.q.cert || {}).k2) + qs(['到期状态', '全部', '30 天内', '90 天内'], 100), 'qSave(\'cert\')');
  const stc = { '已归档': 'green', '待补交': 'orange', '审核中': 'blue', '已过期': 'red' };
  const list = qFilter(CERTS, function (c) { return [c.holder, c.no]; }, function (c) { return c.type + '|' + c.st; });
  let rows = '';
  list.forEach(function (c) {
    const i = CERTS.indexOf(c);
    const d = c.days <= 0 ? tag('已过期', 'red') : c.days <= 30 ? '<span class="neg">' + c.days + ' 天</span>' : c.days <= 90 ? '<span style="color:var(--orange);font-weight:600">' + c.days + ' 天</span>' : '<span class="pos">' + c.days + ' 天</span>';
    rows += '<tr><td style="font-weight:500">' + sens(c.holder) + '</td><td>' + c.type + '</td><td class="mono num">' + sens(maskID(c.no)) + '</td><td class="num">' + c.issue + '</td><td class="num">' + c.exp + '</td><td class="num">' + d + '</td><td>' + tag(c.st, stc[c.st]) + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="certDetail(' + i + ')">查看</span></td></tr>';
  });
  h += tbl(['持有人', '证件类型', '证件号', '签发日期', '有效期至', '剩余天数', '档案状态', '操作'], rows);
  return h;
};
/* CERT：证件归档表单（证件号实时脱敏预览） */
function certAdd() {
  const body = frow([
    { k: 'holder', label: '持有人', type: 'select', req: true, opts: ['苏杳', '赵敏', '孙倩', '李澈', '周晴', '王野'] },
    { k: 'type', label: '证件类型', type: 'select', req: true, opts: ['居民身份证', '护照', '主播资质证', '健康证', '会计从业资格证'] },
    { k: 'no', label: '证件号', type: 'pre', req: true, ph: '请输入证件号码', pre: 'certNoPreview(this)' },
    { k: 'issue', label: '签发日期', type: 'date', val: '2026-01-01' },
    { k: 'exp', label: '有效期至', type: 'date', req: true, val: '2031-12-31' },
    { k: 'remind', label: '到期提醒', type: 'select', opts: ['到期前 90 天', '到期前 60 天', '到期前 30 天', '不提醒'], val: '到期前 90 天' },
    { k: 'file', label: '证件扫描件', type: 'file', ph: '点击上传扫描件（JPG/PDF）', wide: true }
  ]) + '<div class="dsec">证件号脱敏预览</div><div class="card" style="box-shadow:none;border:1px dashed var(--line2);padding:10px 14px;font-size:13px"><span class="mono" id="certPrev" style="color:var(--text2)">待输入…</span></div>';
  openDrawer('证件归档', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="certAddSubmit()">提交归档</button>', '480px');
}
function certNoPreview(inp) {
  const v = inp.value.trim();
  const p = $('#certPrev');
  if (p) p.textContent = v ? maskID(v) + '（归档后仅授权角色可查看完整号码）' : '待输入…';
}
function certAddSubmit() {
  if (!formValidate(['holder', 'type', 'no', 'exp'])) return;
  const no = 'CE20260912-' + String(CERTS.length + 1).padStart(3, '0');
  const holder = $('#F_holder').value, type = $('#F_type').value, cno = $('#F_no').value.trim();
  const days = Math.round((new Date($('#F_exp').value) - new Date('2026-09-12')) / 86400000);
  CERTS.unshift({ holder: holder, type: type, no: cno, issue: $('#F_issue').value || '—', exp: $('#F_exp').value, days: isNaN(days) ? 0 : days, st: '审核中' });
  if (state.page === 'cert') renderPage();
  formOk(no, '证件已提交归档，进入审核流程（当前 L1 遮罩预览）', '');
  toast('证件归档成功：' + holder + ' · ' + type, 'success');
}
function certDetail(i) {
  const c = CERTS[i];
  const body = '<div id="certView" style="border-radius:12px;border:1px solid var(--line);height:240px;position:relative;overflow:hidden;background:linear-gradient(160deg,#f2f6fa,#e6edf5);display:flex;align-items:center;justify-content:center">' +
    '<div id="cvInner" style="color:#8aa4bd;text-align:center">' + ic('id', 44) + '<div style="font-size:12px;margin-top:8px">' + c.type + ' · 扫描件预览</div></div>' +
    '<div id="cvMask" style="position:absolute;inset:0;background:rgba(255,255,255,.88);backdrop-filter:blur(6px);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:6px;color:var(--text2);font-size:13px">' +
    ic('shield', 22) + '<b>L1 · 遮罩预览</b><span style="font-size:11px">仅可见证件类型，不展示任何号码信息</span></div>' +
    '<div id="cvWm" style="position:absolute;inset:0;pointer-events:none;opacity:0;transition:opacity .25s;display:flex;flex-wrap:wrap;align-content:space-around;justify-content:space-around;padding:14px">' +
    Array(12).fill('<span style="font-size:13px;color:rgba(0,113,227,.30);transform:rotate(-18deg);font-weight:600">神鱼体育·内部</span>').join('') + '</div></div>' +
    '<div class="hint" style="margin:12px 0">水印分级：L1 遮罩预览（默认）· L2 半透明水印 · L3 完整查看（需 R1/R2 权限，操作留痕）</div>' +
    '<div class="rowline">' + ['L1', 'L2', 'L3'].map(function (lv) {
      return '<button class="btn btn-sec btn-sm' + (lv === 'L1' ? '' : '') + '" onclick="setCertLv(\'' + lv + '\')">' + lv + (lv === 'L1' ? ' 遮罩' : lv === 'L2' ? ' 水印' : ' 完整') + '</button>';
    }).join('') + '<span class="hint" style="margin-left:auto" id="certLvTag">' + tag('当前 L1', 'gray') + '</span></div>' +
    '<div class="dsec">证件信息</div><div class="kv">' +
    '<div><div class="k">持有人</div><div class="v">' + sens(c.holder) + '</div></div><div><div class="k">证件类型</div><div class="v">' + c.type + '</div></div>' +
    '<div><div class="k">证件号</div><div class="v mono">' + sens(maskID(c.no)) + '</div></div><div><div class="k">有效期至</div><div class="v">' + c.exp + '（剩余 ' + c.days + ' 天）</div></div></div>';
  openDrawer('证件档案 · ' + c.type, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="certApplyDownload(' + i + ')">申请下载</button>');
}
function certApplyDownload(i) {
  const c = CERTS[i];
  confirmDlg('确认申请下载扫描件？', '将向权限管理员申请「' + c.type + ' · ' + c.holder + '」的扫描件下载权限，申请通过后 24 小时内有效。', '申请下载', function () {
    toast('下载已申请 · 权限留痕已记录', 'success');
  }, { warn: '下载操作将记录审计日志：申请人、时间、证件与用途全量留痕' });
}
function setCertLv(lv) {
  const mask = $('#cvMask'), wm = $('#cvWm');
  if (lv === 'L1') { mask.style.display = 'flex'; wm.style.opacity = 0; }
  if (lv === 'L2') { mask.style.display = 'none'; wm.style.opacity = 1; }
  if (lv === 'L3') {
    if (state.role === 'R1' || state.role === 'R2') { mask.style.display = 'none'; wm.style.opacity = 0; toast('L3 完整查看 · 本次访问已留痕', 'success'); }
    else { toast('当前角色（' + ROLES[state.role].name + '）无 L3 完整查看权限', 'error'); return; }
  }
  $('#certLvTag').innerHTML = tag('当前 ' + lv, lv === 'L1' ? 'gray' : lv === 'L2' ? 'blue' : 'green');
}

/* 实名人主数据（穿透链 PERSON 节点）：与 CERTS 证件、ACCTS 账号动态关联 */
const PERSONS = [
  { name: '苏杳', no: 'SF0067', dept: '主播组', cert: '已核验', certDays: 26, certs: 3, accts: ['ACCT-2026-0001', 'ACCT-2026-0003', 'ACCT-2026-0034'], phone: '18925786789' },
  { name: '李澈', no: 'SF0089', dept: '运营中心', cert: '已核验', certDays: 991, certs: 1, accts: ['ACCT-2026-0002', 'ACCT-2026-0008'], phone: '13592671234' },
  { name: '王野', no: 'SF0090', dept: '外协', cert: '待核验', certDays: 1897, certs: 1, accts: ['ACCT-2026-0087'], phone: '15827496305' },
  { name: '孙倩', no: 'SF0056', dept: '内容中心', cert: '已核验', certDays: 83, certs: 1, accts: [], phone: '18666172345' },
  { name: '赵敏', no: 'SF0045', dept: '运营中心', cert: '已核验', certDays: 1412, certs: 1, accts: [], phone: '13828715678' },
  { name: '陈默', no: 'SF0078', dept: '数据中心', cert: '已过期', certDays: -96, certs: 1, accts: [], phone: '13625309876', locked: true }
];
/* 实名人证件状态（BR-013）：T-30 黄 / T-7 红 / T-0 已过期锁定，不可用于新场次登记 */
function certStateOf(days) {
  if (days <= 0) return { s: '已过期·锁定', c: 'red' };
  if (days <= 7) return { s: '临期·红色预警', c: 'red' };
  if (days <= 30) return { s: '临期·黄色预警', c: 'orange' };
  return { s: '正常', c: 'green' };
}

/* ===================== 10 LIVE 直播管理 ===================== */
const LIVES = [
  { id: 'IMS202609120DY0142', acct: 'ACCT-2026-0001', rname: '苏杳', owner: '赵敏', topic: '秋季新品跑鞋首发专场', plat: '抖音', start: '2026-09-12 19:30', risk: 82, rl: '高', st: '待开播', devices: ['AS20260901001', 'AS20260830003', 'AS20260825005'], fbRoom: '', fbSync: 'UNLINKED', riskChecks: [{ n: '证件有效性', r: 'WARN' }, { n: '账号状态', r: 'PASS' }, { n: '话费余额', r: 'FAIL' }, { n: '黑名单词', r: 'PASS' }, { n: '设备归属', r: 'PASS' }] },
  { id: 'IMS202609120DY0141', acct: 'ACCT-2026-0003', rname: '苏杳', owner: '赵敏', topic: '晚间健身操跟练', plat: '斗鱼', start: '2026-09-12 20:00', risk: 34, rl: '低', st: '待开播', devices: ['AS20260901001'], fbRoom: 'FR-DY-8821', fbSync: 'BLOCKED_NO_API', riskChecks: [{ n: '证件有效性', r: 'PASS' }, { n: '账号状态', r: 'PASS' }, { n: '话费余额', r: 'PASS' }, { n: '黑名单词', r: 'PASS' }, { n: '设备归属', r: 'PASS' }] },
  { id: 'IMS202609110DY0138', acct: 'ACCT-2026-0002', rname: '李澈', owner: '孙倩', topic: '跑步装备开箱测评', plat: '视频号', start: '2026-09-11 15:00', risk: 46, rl: '中', st: '直播中', devices: ['AS20260831002', 'AS20260827006'], fbRoom: 'FR-WX-44102', fbSync: 'PENDING', fbViews: 6200, fbPeak: 890, fbDur: 95, riskChecks: [{ n: '证件有效性', r: 'PASS' }, { n: '账号状态', r: 'PASS' }, { n: '话费余额', r: 'PASS' }, { n: '黑名单词', r: 'PASS' }, { n: '设备归属', r: 'PASS' }] },
  { id: 'IMS202609110DY0136', acct: 'ACCT-2026-0034', rname: '苏杳', owner: '何舟', topic: '夜跑安全知识分享', plat: '快手', start: '2026-09-11 19:00', risk: 28, rl: '低', st: '已结束', devices: ['AS20260901001', 'AS20260825005'], gmv: 61200, orders: 86, views: 12800, peak: 3842, fans: 156, entered: true, fbRoom: 'FR-KS-3309', fbSync: 'SYNCED', fbSyncAt: '2026-09-12 09:15', riskChecks: [{ n: '证件有效性', r: 'PASS' }, { n: '账号状态', r: 'PASS' }, { n: '话费余额', r: 'PASS' }, { n: '黑名单词', r: 'PASS' }, { n: '设备归属', r: 'PASS' }] },
  { id: 'IMS202609100DY0131', acct: 'ACCT-2026-0001', rname: '赵敏', rerr: true, owner: '赵敏', topic: '大促预热：健身品类专场', plat: '抖音', start: '2026-09-10 20:00', risk: 61, rl: '中', st: '已结束', devices: ['AS20260901001', 'AS20260830003'], gmv: 412800, orders: 530, views: 42600, peak: 15800, fans: 1240, entered: true, fbRoom: 'FR-DY-8801', fbSync: 'SYNCED', fbSyncAt: '2026-09-11 08:40', riskChecks: [{ n: '证件有效性', r: 'WARN' }, { n: '账号状态', r: 'PASS' }, { n: '话费余额', r: 'PASS' }, { n: '黑名单词', r: 'PASS' }, { n: '设备归属', r: 'PASS' }] },
  { id: 'IMS202609090DY0127', acct: 'ACCT-2026-0003', rname: '苏杳', owner: '赵敏', topic: '周末电竞水友赛', plat: '斗鱼', start: '2026-09-09 14:00', risk: 39, rl: '低', st: '已结束', devices: ['AS20260901001'], gmv: 96700, orders: 218, views: 31200, peak: 9210, fans: 420, entered: true, fbRoom: '', fbSync: 'UNLINKED', riskChecks: [{ n: '证件有效性', r: 'PASS' }, { n: '账号状态', r: 'PASS' }, { n: '话费余额', r: 'PASS' }, { n: '黑名单词', r: 'PASS' }, { n: '设备归属', r: 'PASS' }] },
  { id: 'IMS202609090DY0125', acct: 'ACCT-2026-0087', rname: '王野', owner: '何舟', topic: '运动营养科普', plat: '抖音', start: '2026-09-09 18:30', risk: 86, rl: '高', st: '已取消', devices: [], fbSync: 'UNLINKED', riskChecks: [{ n: '证件有效性', r: 'FAIL' }, { n: '账号状态', r: 'PASS' }, { n: '话费余额', r: 'FAIL' }, { n: '黑名单词', r: 'PASS' }, { n: '设备归属', r: 'PASS' }] },
  { id: 'IMS202609080DY0121', acct: 'ACCT-2026-0002', rname: '孙倩', owner: '孙倩', topic: '晨间瑜伽唤醒', plat: '视频号', start: '2026-09-08 07:30', risk: 22, rl: '低', st: '已结束', devices: ['AS20260831002'], gmv: 0, orders: 0, views: 8600, peak: 2100, fans: 86, entered: true, fbRoom: 'FR-WX-44001', fbSync: 'FAILED', fbSyncAt: '2026-09-08 10:02', riskChecks: [{ n: '证件有效性', r: 'PASS' }, { n: '账号状态', r: 'PASS' }, { n: '话费余额', r: 'PASS' }, { n: '黑名单词', r: 'PASS' }, { n: '设备归属', r: 'PASS' }] },
  { id: 'IMS202609070DY0118', acct: 'ACCT-2026-0034', rname: '苏杳', owner: '苏杳', topic: '达人连麦：训练日常', plat: '快手', start: '2026-09-07 21:00', risk: 53, rl: '中', st: '已结束', devices: ['AS20260901001', 'AS20260824009'], entered: false, fbRoom: 'FR-KS-3301', fbSync: 'BLOCKED_NO_API', riskChecks: [{ n: '证件有效性', r: 'PASS' }, { n: '账号状态', r: 'PASS' }, { n: '话费余额', r: 'WARN' }, { n: '黑名单词', r: 'PASS' }, { n: '设备归属', r: 'PASS' }] }
];
function liveSyncLabel(s) {
  const m = { UNLINKED: ['未关联 Football', 'gray'], PENDING: ['待同步', 'orange'], SYNCED: ['已同步', 'green'], FAILED: ['同步失败', 'red'], BLOCKED_NO_API: ['API 未就绪', 'red'] };
  const x = m[s] || m.UNLINKED;
  return tag(x[0], x[1]);
}
PAGES.live = function () {
  const cur = state.tab.live || '场次列表';
  const headBtn = cur === '场次列表' ? '<button class="btn btn-pri" onclick="liveReg()">' + ic('plus', 15) + '新建场次登记</button><button class="btn btn-sec" onclick="exportX(this,\'直播场次\',LIVES.length)">导出</button>' :
    cur === '待录入督办' ? '<button class="btn btn-sec" onclick="exportX(this,\'待录入督办\',LIVES.filter(function(l){return l.st===\'已结束\'&&!l.entered}).length)">导出</button>' :
      '<button class="btn btn-sec" onclick="liveAlarmRuleEdit(-1)">' + ic('plus', 15) + '新建告警规则</button>';
  let h = pgHead('live', headBtn);
  h += '<div class="tabs">' + ['场次列表', '待录入督办', '风险告警'].map(function (t) {
    const badge = t === '待录入督办' ? LIVES.filter(function (l) { return l.st === '已结束' && !l.entered; }).length : 0;
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'live\',\'' + t + '\')">' + t + (badge ? ' <span style="color:var(--red);font-size:11px">(' + badge + ')</span>' : '') + '</div>';
  }).join('') + '</div>';
  if (cur === '待录入督办') {
    const pending = LIVES.filter(function (l) { return l.st === '已结束' && !l.entered; });
    h += '<div class="hint" style="margin-bottom:10px">LIVE-002 督办队列 · 下播 24h 未提交标红（BR-007）</div>';
    let rows = '';
    pending.forEach(function (l) { rows += liveRow(l, true); });
    if (!rows) rows = '<tr><td colspan="12" style="text-align:center;color:var(--text2);padding:24px">暂无待录入场次</td></tr>';
    h += tbl(['场次ID', '直播账号', '实名人', '责任人', '主题', '平台', '计划开播', '风险分', '风险级别', '场次状态', 'Football', '操作'], rows);
    return h;
  }
  if (cur === '风险告警') {
    h += qbar(qi('场次 ID', 160) + qs(['全部级别', 'L1 提示', 'L2 警告', 'L3 严重'], 100), 'toast(\'筛选告警\',\'success\')');
    const alr = [
      { id: 'AL-9021', sid: 'IMS202609110DY0138', rule: '场观骤降', lv: 'L2', txt: '5 分钟内在线下降 38%', st: '未处理' },
      { id: 'AL-9018', sid: 'IMS202609100DY0131', rule: 'GMV 波动', lv: 'L1', txt: 'GMV 较均值 +22%', st: '已确认' }
    ];
    let rows = '';
    alr.forEach(function (a) {
      rows += '<tr><td class="mono">' + a.id + '</td><td class="mono" style="color:var(--blue);cursor:pointer" onclick="liveSessionDetail(\'' + a.sid + '\',\'link\')">' + a.sid + '</td><td>' + a.rule + '</td><td>' + tag(a.lv, a.lv === 'L3' ? 'red' : a.lv === 'L2' ? 'orange' : 'blue') + '</td><td>' + a.txt + '</td><td>' + tag(a.st, a.st === '未处理' ? 'red' : 'blue') + '</td><td><span class="btn btn-sec btn-sm" onclick="liveAlarmHandle(\'' + a.id + '\',\'' + a.sid + '\')">处置</span></td></tr>';
    });
    h += tbl(['告警ID', '场次ID', '规则', '级别', '内容', '状态', '操作'], rows);
    return h;
  }
  const ended = LIVES.filter(function (l) { return l.st === '已结束'; });
  const enteredN = ended.filter(function (l) { return l.entered; }).length;
  const rate = ended.length ? Math.round(enteredN / ended.length * 100) : 100;
  h += '<div class="g4"><div class="card stat"><span class="l">今日待开播 / 直播中</span><div class="n" style="color:var(--blue)">' + LIVES.filter(function (l) { return l.st === '待开播' || l.st === '直播中'; }).length + '</div><div class="d">场次中心主列表</div></div>' +
    '<div class="card stat"><span class="l">下播录入完整率</span><div class="n" style="color:' + (rate >= 90 ? 'var(--green)' : 'var(--orange)') + '">' + rate + '%</div><div class="d">BR-007 · 已结束 ' + ended.length + ' 场</div></div>' +
    '<div class="card stat"><span class="l">Football 同步</span><div class="n" style="font-size:22px">' + LIVES.filter(function (l) { return l.fbSync === 'SYNCED'; }).length + '/' + LIVES.length + '</div><div class="d">单场 HTTP API 未就绪项标红</div></div>' +
    '<div class="card stat"><span class="l">本月已录 GMV</span><div class="n">' + fmtMoney(ended.reduce(function (s, l) { return s + (l.gmv || 0); }, 0)) + '</div><div class="d">下播 Tab 核准后入 FIN</div></div></div>';
  h += qbar(qi('场次 ID', 160, (state.q.live || {}).k0) + qs(['全部平台', '抖音', '斗鱼', '视频号', '快手'], 90, (state.q.live || {}).k1) + qs(['全部状态', '待开播', '直播中', '已结束', '已取消'], 100, (state.q.live || {}).k2) + '<input type="date" style="width:130px">', 'qSave(\'live\')');
  const list = qFilter(LIVES, function (l) { return [l.id, l.topic, l.rname, l.owner]; }, function (l) { return l.plat + '|' + l.st; });
  let rows = '';
  list.forEach(function (l) { rows += liveRow(l); });
  h += tbl(['场次ID', '直播账号', '实名人', '责任人', '主题', '平台', '计划开播', '风险分', '风险级别', '场次状态', 'Football', '操作'], rows);
  return h;
};
function liveRow(l, pendingOnly) {
  const rlc = { '低': 'green', '中': 'orange', '高': 'red' }[l.rl];
  const rc = l.risk >= 80 ? 'var(--red)' : l.risk >= 60 ? 'var(--orange)' : l.risk >= 40 ? 'var(--yellow)' : 'var(--green)';
  const stc = { '待开播': 'blue', '直播中': 'green', '已结束': 'gray', '已取消': 'gray', '待复核': 'orange' }[l.st];
  const needEntry = l.st === '已结束' && !l.entered;
  const acts = '<span class="btn btn-sec btn-sm" onclick="liveSessionDetail(\'' + l.id + '\',\'basic\')">详情</span> ' +
    (l.st === '待开播' ? '<span class="btn btn-sm" onclick="liveSessionDetail(\'' + l.id + '\',\'risk\')">风控</span> ' : '') +
    (needEntry ? '<button class="btn btn-sm" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="liveSessionDetail(\'' + l.id + '\',\'report\')">下播录入</button>' : '');
  return '<tr><td class="mono num" style="color:var(--blue);cursor:pointer" onclick="liveSessionDetail(\'' + l.id + '\',\'basic\')">' + l.id + '</td>' +
    '<td class="mono" style="font-size:12px">' + l.acct + '</td><td style="font-weight:500' + (l.rerr ? ';color:var(--red)' : '') + '">' + sens(l.rname) + (l.rerr ? ' ⚠' : '') + '</td><td>' + sens(l.owner) + '</td>' +
    '<td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">' + l.topic + '</td><td>' + l.plat + '</td><td class="num" style="font-size:12px">' + l.start + '</td>' +
    '<td><div class="rowline"><span class="pg" style="width:44px"><i style="width:' + l.risk + '%;background:' + rc + '"></i></span><span class="num" style="font-size:12px;font-weight:600">' + l.risk + '</span></div></td>' +
    '<td>' + tag(l.rl + '风险', rlc) + '</td><td>' + tag(l.st, stc) + (l.entered ? ' <span class="chip" style="font-size:10.5px;color:var(--green);border-color:var(--green)">已录入</span>' : '') + '</td>' +
    '<td>' + liveSyncLabel(l.fbSync || 'UNLINKED') + '</td><td>' + acts + '</td></tr>';
}
/* LIVE：场次设备编号 → 跳资产详情（穿透） */
function assetGoById(id) {
  const i = ASSETS.findIndex(function (x) { return x.id === id; });
  if (i < 0) { toast('未找到资产：' + id, 'error'); return; }
  closeDrawer();
  go('asset');
  assetDetail(i);
}
/* LIVE：场次详情（P0-D · Tab：基本/直播数据/风控/下播/关联） */
function liveSessionDetail(id, tab) {
  tab = tab === 'link' ? 'basic' : (tab || 'basic');
  const l = LIVES.filter(function (x) { return x.id === id; })[0];
  if (!l) { toast('未找到场次：' + id, 'error'); return; }
  const tabs = ['basic', 'metrics', 'risk', 'report', 'link'];
  const tabHtml = tabs.map(function (t) {
    const lbl = { basic: '基本信息', metrics: '直播数据', risk: '风控登记', report: '下播与 GMV', link: '关联' }[t];
    return '<div class="tab' + (tab === t ? ' on' : '') + '" onclick="liveSessionDetail(\'' + id + '\',\'' + t + '\')">' + lbl + '</div>';
  }).join('');
  let pane = '';
  if (tab === 'metrics') {
    const blocked = l.fbSync === 'BLOCKED_NO_API';
    pane = '<div class="hint" style="margin-bottom:10px">IR-02 FootballWebApiClient 只读 · 快照表 <span class="mono">ims_live_data_snapshot</span></div>' +
      '<div class="kv"><div><div class="k">football_room_id</div><div class="v mono">' + (l.fbRoom || '—') + '</div></div>' +
      '<div><div class="k">同步态</div><div class="v">' + liveSyncLabel(l.fbSync || 'UNLINKED') + '</div></div>' +
      '<div><div class="k">上次同步</div><div class="v">' + (l.fbSyncAt || '—') + '</div></div></div>' +
      (blocked ? '<div class="card" style="border:1px solid rgba(255,59,48,.35);padding:12px 14px;margin:10px 0;background:rgba(255,59,48,.04)"><b style="color:var(--red)">阻塞 · 1050</b><div class="hint" style="margin-top:6px">Football 单场 live room HTTP 契约未发布（见 FB-Football-WebAPI适配 §2）。M6 仅有作者×日期 Feign 聚合，不能替代本场指标。</div></div>' : '') +
      '<div class="dsec">Football 快照 / 平台对照</div><div class="kv">' +
      '<div><div class="k">观看（Football/IMS）</div><div class="v num">' + (l.fbViews != null ? l.fbViews.toLocaleString() : '—') + ' / ' + (l.views != null ? l.views.toLocaleString() : '—') + '</div></div>' +
      '<div><div class="k">峰值在线</div><div class="v num">' + (l.fbPeak != null ? l.fbPeak.toLocaleString() : '—') + ' / ' + (l.peak != null ? l.peak.toLocaleString() : '—') + '</div></div>' +
      '<div><div class="k">时长（分钟）</div><div class="v num">' + (l.fbDur != null ? l.fbDur : '—') + ' / ' + (l.entered && l.views ? '已录入' : '—') + '</div></div></div>' +
      '<div class="rowline" style="gap:8px;margin-top:12px;flex-wrap:wrap">' +
      '<button class="btn btn-sec btn-sm" onclick="liveBindRoom(\'' + id + '\')">绑定 roomId</button>' +
      '<button class="btn btn-pri btn-sm"' + (blocked ? ' disabled style="opacity:.45;cursor:not-allowed"' : '') + ' onclick="liveFootballSync(\'' + id + '\')">从 Football 同步</button>' +
      '<button class="btn btn-sec btn-sm" onclick="toast(\'POST /ims/live/sessions/' + id + '/football-sync\',\'success\')">查看 API</button></div>';
  } else if (tab === 'risk') {
    const checks = l.riskChecks || [];
    pane = '<div class="rowline" style="justify-content:space-between;margin-bottom:8px"><span>风险分 <b style="font-size:22px">' + l.risk + '</b> / 100</span>' + tag(l.rl + '风险', l.rl === '高' ? 'red' : l.rl === '中' ? 'orange' : 'green') + '</div>' +
      '<div class="dsec">LIVE-001 五类检查（BR-014）</div>' +
      checks.map(function (c) {
        const tc = c.r === 'FAIL' ? 'red' : c.r === 'WARN' ? 'orange' : 'green';
        return '<div class="rowline" style="justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px"><span>' + c.n + '</span>' + tag(c.r, tc) + '</div>';
      }).join('') +
      '<div class="rowline" style="gap:8px;margin-top:14px;flex-wrap:wrap">' +
      '<button class="btn btn-sec btn-sm" onclick="liveRiskResultDrawer(\'' + id + '\')">重新执行风控</button>' +
      (l.risk >= 40 && l.risk < 70 ? '<button class="btn btn-pri btn-sm" onclick="liveApprovePass(\'' + id + '\')">黄级审批放行</button>' : '') +
      (l.st === '待开播' && l.risk < 70 ? '<button class="btn btn-pri btn-sm" onclick="liveConfirmStart(\'' + id + '\')">确认开播</button>' : '') +
      (l.risk >= 60 ? '<button class="btn btn-sm" style="background:var(--orange);color:#fff" onclick="liveToReview(\'' + id + '\')">转人工复核</button>' : '') + '</div>';
  } else if (tab === 'report') {
    if (l.st !== '已结束' && l.st !== '直播中') {
      pane = '<div class="hint">场次未结束，下播录入将在状态=已结束后开放（LIVE-002）。</div>';
    } else if (l.entered) {
      pane = '<div class="kv"><div><div class="k">GMV</div><div class="v num" style="font-weight:600">' + fmtMoney(l.gmv || 0) + '</div></div>' +
        '<div><div class="k">订单</div><div class="v num">' + (l.orders || 0) + '</div></div>' +
        '<div><div class="k">观看 / 峰值</div><div class="v num">' + (l.views || 0).toLocaleString() + ' / ' + (l.peak || 0).toLocaleString() + '</div></div>' +
        '<div><div class="k">涨粉</div><div class="v num">+' + (l.fans || 0) + '</div></div></div>' +
        '<div class="rowline" style="gap:8px;margin-top:12px"><button class="btn btn-sec btn-sm" onclick="toast(\'更正单留痕（LIVE-D-R3）\',\'success\')">提交更正</button>' +
        '<button class="btn btn-pri btn-sm" onclick="liveReportConfirm(\'' + id + '\')">核准（R4）</button></div>';
    } else {
      pane = '<div class="hint" style="margin-bottom:8px">LIVE-002 · 九项必填 · 24h 督办</div><div id="liveReportFormHost"></div>';
      setTimeout(function () { liveEndEntryForm(id); }, 0);
    }
  } else if (tab === 'link') {
    pane = '<div class="dsec">绑定设备（BR-003）</div>' + ((l.devices || []).length ? (l.devices || []).map(function (d) {
      const a = ASSETS.filter(function (x) { return x.id === d; })[0];
      return a ? '<div class="rowline" style="justify-content:space-between;padding:4px 0"><span style="cursor:pointer;color:var(--blue)" onclick="assetGoById(\'' + d + '\')">' + a.name + '</span>' + tag(a.status, 'green') + '</div>' : '';
    }).join('') : '<div class="hint">无设备</div>') +
      '<div class="dsec">告警摘要（LIVE-003）</div><div class="hint">直播中监控 GMV/场观/余额 · <span class="btn-txt btn" onclick="setTab(\'live\',\'风险告警\');closeDrawer()">打开告警 Tab</span></div>';
  } else {
    pane = '<div class="kv">' +
      '<div><div class="k">场次 ID</div><div class="v mono">' + l.id + '</div></div><div><div class="k">直播账号</div><div class="v mono">' + l.acct + '</div></div>' +
      '<div><div class="k">实名人</div><div class="v">' + sens(l.rname) + '</div></div><div><div class="k">责任人</div><div class="v">' + sens(l.owner) + '</div></div>' +
      '<div><div class="k">主题</div><div class="v">' + l.topic + '</div></div><div><div class="k">平台 / 计划开播</div><div class="v">' + l.plat + ' · ' + l.start + '</div></div>' +
      '<div><div class="k">场次状态</div><div class="v">' + tag(l.st, { '待开播': 'blue', '直播中': 'green', '已结束': 'gray' }[l.st] || 'gray') + '</div></div></div>' +
      '<div class="dsec">实名人档案</div><div class="kv">' + (function () {
        const p = PERSONS.filter(function (x) { return x.name === l.rname; })[0];
        if (!p) return '<div class="hint">暂无实名人</div>';
        const st = certStateOf(p.certDays);
        return '<div><div class="k">证件</div><div class="v">' + st.s + '</div></div><div><div class="k">部门</div><div class="v">' + p.dept + '</div></div>';
      })() + '</div>';
  }
  const body = '<div class="tabs" style="margin-top:0">' + tabHtml + '</div>' + pane;
  openDrawer('场次详情 · ' + l.id, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (tab === 'risk' && l.st === '待开播' ? '<button class="btn btn-sec" onclick="liveRegEdit(\'' + id + '\')">编辑登记</button>' : ''), '720px');
}
function liveSessionOp(id) { liveSessionDetail(id, 'basic'); }
function liveBindRoom(id) {
  const l = LIVES.filter(function (x) { return x.id === id; })[0];
  const body = frow([{ k: 'fbroom', label: 'Football roomId', type: 'text', ph: '如 FR-DY-8821', val: l.fbRoom || '' }]);
  openDrawer('绑定 Football 房间 · ' + id, body,
    '<button class="btn btn-sec" onclick="liveSessionDetail(\'' + id + '\',\'metrics\')">取消</button><button class="btn btn-pri" onclick="liveBindRoomSave(\'' + id + '\')">保存</button>', '420px');
}
function liveBindRoomSave(id) {
  const l = LIVES.filter(function (x) { return x.id === id; })[0];
  l.fbRoom = ($('#F_fbroom') && $('#F_fbroom').value) || '';
  l.fbSync = l.fbRoom ? (l.fbSync === 'BLOCKED_NO_API' ? 'BLOCKED_NO_API' : 'PENDING') : 'UNLINKED';
  toast('已保存 football_room_id：' + (l.fbRoom || '（空）'), 'success');
  liveSessionDetail(id, 'metrics');
}
function liveFootballSync(id) {
  const l = LIVES.filter(function (x) { return x.id === id; })[0];
  if (!l || l.fbSync === 'BLOCKED_NO_API') {
    confirmDlg('无法同步', 'Football 单场 live room HTTP 未发布（错误码 1050）。请先在 Football 侧发布 OpenAPI，或仅维护 IMS 手工录入。', '知道了', function () {}, { warn: '禁止臆造 /rpc-api/live/* 路径' });
    return;
  }
  if (!l.fbRoom) { toast('请先绑定 football_room_id', 'error'); liveBindRoom(id); return; }
  confirmDlg('从 Football 拉取本场指标？', '调用 POST /admin-api/ims/live/sessions/' + id + '/football-sync，成功写入 ims_live_data_snapshot（失败走 outbox，不回滚场次主数据）。', '开始同步', function () {
    l.fbSync = 'SYNCED';
    l.fbSyncAt = '2026-09-29 ' + new Date().toTimeString().slice(0, 5);
    l.fbViews = l.fbViews || Math.round((l.views || 8000) * 0.97);
    l.fbPeak = l.fbPeak || Math.round((l.peak || 2000) * 0.95);
    l.fbDur = l.fbDur || 118;
    if (state.page === 'live') renderPage();
    liveSessionDetail(id, 'metrics');
    toast('Football 同步完成 · 已写快照', 'success');
  });
}
function liveRiskResultDrawer(id) {
  const l = LIVES.filter(function (x) { return x.id === id; })[0];
  if (!l) return;
  const body = '<div class="hint">POST /live/register/' + id + '/risk-check · 五类检查清单</div><div class="tl">' +
    (l.riskChecks || []).map(function (c) {
      return '<div class="tl-i"><div class="tt">' + c.n + '</div><div class="td">结果 ' + c.r + '</div></div>';
    }).join('') + '</div>';
  openDrawer('风控结果 · ' + id, body, '<button class="btn btn-sec" onclick="liveSessionDetail(\'' + id + '\',\'risk\')">返回</button>', '480px');
}
function liveApprovePass(id) {
  confirmDlg('黄级审批放行？', '场次 ' + id + ' 风险分在中档，确认后将状态置为「已放行」并留痕审批意见。', '通过放行', function () {
    toast('已放行：' + id + ' · PUT …/approve', 'success');
    liveSessionDetail(id, 'risk');
  }, { withInput: true, inputPh: '审批意见（必填）' });
}
function liveConfirmStart(id) {
  confirmDlg('确认开播？', 'PUT /live/register/' + id + '/start · 未放行场次不可开播（LIVE-R1）', '确认开播', function () {
    const l = LIVES.filter(function (x) { return x.id === id; })[0];
    if (l) l.st = '直播中';
    if (state.page === 'live') renderPage();
    closeDrawer();
    toast('场次已进入直播中：' + id, 'success');
  });
}
function liveReportConfirm(id) {
  confirmDlg('核准下播数据？', 'PUT /live/report/' + id + '/confirm · 数据进入 FIN 利润模型', '核准', function () {
    toast('已核准：' + id, 'success');
  });
}
function liveAlarmHandle(aid, sid) {
  const body = frow([{ k: 'hact', label: '处置动作', type: 'select', req: true, opts: ['已确认', '已处理', '误报'] }, { k: 'hnote', label: '说明', type: 'textarea', wide: true }]);
  openDrawer('告警处置 · ' + aid, body, '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="liveAlarmHandleSubmit(\'' + aid + '\')">提交</button>', '480px');
  state.qz = { alarmSid: sid };
}
function liveAlarmHandleSubmit(aid) {
  if (!formValidate(['hact'])) return;
  closeDrawer();
  toast('告警 ' + aid + ' 已处置', 'success');
  if (state.page === 'live') renderPage();
}
function liveAlarmRuleEdit() {
  openDrawer('新建告警规则', frow([{ k: 'rname', label: '规则名', req: true }, { k: 'rmet', label: '指标', type: 'select', opts: ['GMV 骤降', '场观骤降', '话费余额'] }]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="toast(\'规则热更新 ALM-R4\',\'success\');closeDrawer()">保存</button>', '480px');
}
function liveRegEdit(id) { toast('编辑登记 · PUT /live/register/' + id, 'success'); }
function liveEndEntryForm(id) {
  const host = $('#liveReportFormHost');
  if (!host) return;
  host.innerHTML = frow([
    { k: 'lgmv', label: '本场 GMV', type: 'num', req: true, unit: '¥', pre: 'liveEntryCalc()' },
    { k: 'lord', label: '成交订单数', type: 'num', unit: '单' },
    { k: 'lview', label: '累计观看', type: 'num', req: true, pre: 'liveEntryCalc()' },
    { k: 'lpeak', label: '峰值在线', type: 'num' },
    { k: 'lreal', label: '实际时长(min)', type: 'num', req: true },
    { k: 'lfans', label: '新增粉丝', type: 'num' }
  ]) + '<div class="kv" style="margin-top:8px"><div><div class="k">客单价</div><div class="v num" id="leA">—</div></div></div>' +
    '<div class="rowline" style="margin-top:10px"><button class="btn btn-sec btn-sm" onclick="toast(\'草稿已保存\',\'success\')">保存草稿</button>' +
    '<button class="btn btn-pri btn-sm" onclick="liveEndEntrySubmit(\'' + id + '\')">提交录入</button></div>';
  state.qz = { entryId: id };
}
/* LIVE：转人工复核（确认 → 场次状态/队列变更） */
function liveToReview(id) {
  const l = LIVES.filter(function (x) { return x.id === id; })[0];
  if (!l) return;
  confirmDlg('确认转人工复核？', '场次 ' + l.id + '（' + l.topic + '）风险分 ' + l.risk + '，转入人工复核后将暂缓开播并通知风控值守人员。', '转人工复核', function () {
    l.st = '待复核';
    if (state.page === 'live') renderPage();
    closeDrawer();
    toast('已转人工复核队列：' + l.id, 'success');
    hlFirst();
  }, { warn: '复核期间场次不可开播，超 2 小时未复核将自动升级提醒', danger: l.risk >= 80 });
}
function liveReg() {
  const avail = ACCTS.filter(function (a) { return a.st === '在用'; });
  const acctOpts = avail.map(function (a) {
    return '<option value="' + a.id + '">' + a.id + ' · ' + a.plat + ' · ' + a.nick + (a.frozen ? '（已冻结）' : '') + '</option>';
  }).join('');
  const personOpts = PERSONS.filter(function (p) { return p.cert !== '已过期'; }).map(function (p) {
    const st = certStateOf(p.certDays);
    return '<option value="' + p.name + '">' + p.name + '（' + (p.cert === '已核验' ? '证件已核验 ✓' : '证件待核验 ⚠') + ' · ' + st.s + '）</option>';
  }).join('');
  const devChks = ASSETS.filter(function (a) { return (a.type === '直播设备' || a.type === '拍摄设备') && a.status === '在用'; }).map(function (a) {
    return '<label style="display:inline-flex;align-items:center;gap:5px;margin:3px 10px 3px 0;font-size:12.5px;cursor:pointer"><input type="checkbox" class="lrv-dev" value="' + a.id + '" onchange="liveRegDevCalc(this)">' + a.name + '<span style="color:var(--text2);font-size:11px">' + a.id.slice(-6) + '</span></label>';
  }).join('');
  const body = '<div class="formrow"><div class="fld"><label>直播账号</label><select id="lrAcct" onchange="liveRegSync()">' + acctOpts + '</select></div>' +
    '<div class="fld"><label>实名人</label><select id="lrPerson">' + personOpts + '</select></div></div>' +
    '<div class="formrow"><div class="fld"><label>责任人（随账号带出）</label><input id="lrOwner" readonly></div>' +
    '<div class="fld"><label>直播平台（随账号带出）</label><input id="lrPlat" readonly></div></div>' +
    '<div class="formrow one"><div class="fld"><label>直播主题</label><input placeholder="如：秋季新品跑鞋首发专场"></div></div>' +
    '<div class="formrow one"><div class="fld"><label>直播设备（绑定本场资产 · BR-003 关联校验）</label><div class="card" style="box-shadow:none;border:1px solid var(--line);padding:8px 12px">' + devChks + '</div>' +
    '<div class="hint" style="margin-top:4px" id="lrDevCnt">已选 0 件 · 设备与场次绑定后写入资产流转链（ims_asset_flow）</div></div></div>' +
    '<div class="formrow"><div class="fld"><label>计划开播时间</label><input type="datetime-local" value="2026-09-12T19:30"></div>' +
    '<div class="fld"><label>预计时长（小时）</label><input type="number" value="3" min="0.5" step="0.5"></div></div>' +
    '<div class="hint">提交后将自动执行开播风控规则引擎（账号状态 / 实名人核验 / 历史行为 / 内容合规 4 类 17 条规则）；实名人证件 T-0 已过期将被强制锁定拦截（BR-013）</div>';
  openDrawer('开播风控登记', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="liveRiskResult()">提交并执行风控</button>');
  liveRegSync();
}
/* LIVE：账号选择联动（带出平台/责任人，同步实名人默认值与号卡提示） */
function liveRegSync() {
  const id = $('#lrAcct') && $('#lrAcct').value;
  const a = ACCTS.filter(function (x) { return x.id === id; })[0];
  if (!a) return;
  if ($('#lrOwner')) $('#lrOwner').value = a.owner;
  if ($('#lrPlat')) $('#lrPlat').value = a.plat;
  if ($('#lrPerson')) {
    const p = PERSONS.filter(function (x) { return x.name === a.rname; })[0];
    if (p && p.cert !== '已过期') $('#lrPerson').value = p.name;
  }
}
/* LIVE：设备勾选计数 */
function liveRegDevCalc() {
  const n = document.querySelectorAll('.lrv-dev:checked').length;
  if ($('#lrDevCnt')) $('#lrDevCnt').textContent = '已选 ' + n + ' 件 · 设备与场次绑定后写入资产流转链（ims_asset_flow）';
}
function liveRiskResult() {
  /* BR-013：实名人证件 T-0 已过期 → 锁定拦截，不可用于新场次登记 */
  const pn = $('#lrPerson') && $('#lrPerson').value;
  if (pn) {
    const p = PERSONS.filter(function (x) { return x.name === pn; })[0];
    if (p && p.certDays <= 0) {
      toast('实名人 ' + pn + ' 证件已过期（BR-013 T-0 锁定）：不可用于新场次登记，请更换实名人或先完成证件换证', 'error');
      return;
    }
  }
  const score = 82;
  const arc = 2 * Math.PI * 52 * (score / 100);
  const body = '<div style="text-align:center;margin:6px 0 14px">' +
    '<svg width="140" height="140" viewBox="0 0 140 140"><circle cx="70" cy="70" r="52" fill="none" stroke="rgba(0,0,0,.07)" stroke-width="11"/>' +
    '<circle cx="70" cy="70" r="52" fill="none" stroke="var(--red)" stroke-width="11" stroke-linecap="round" stroke-dasharray="' + arc + ' 999" transform="rotate(-90 70 70)"/>' +
    '<text x="70" y="66" text-anchor="middle" font-size="30" font-weight="700" fill="#1d1d1f">82</text><text x="70" y="88" text-anchor="middle" font-size="11" fill="#86868b">风险分 / 100</text></svg>' +
    '<div>' + tag('高风险 · 建议人工复核', 'red') + '</div></div>' +
    '<div class="dsec">命中规则（2 / 17）</div>' +
    '<div class="card" style="box-shadow:none;border:1px solid rgba(255,59,48,.25);margin-bottom:9px;padding:13px 15px"><div class="rowline" style="justify-content:space-between"><b style="font-size:13px">R-07 实名人证件临期</b>' + tag('-18 分', 'red') + '</div><div class="hint" style="margin-top:3px">实名人苏杳身份证剩余有效期 26 天（阈值 30 天）</div></div>' +
    '<div class="card" style="box-shadow:none;border:1px solid rgba(255,149,0,.3);padding:13px 15px"><div class="rowline" style="justify-content:space-between"><b style="font-size:13px">R-12 账号近 7 天充值异常</b>' + tag('-12 分', 'orange') + '</div><div class="hint" style="margin-top:3px">账号近 7 天累计充值 ¥12,600，超同类账号 P95 分位</div></div>' +
    '<div class="hint">其余 15 条规则未命中。结果已推送至审核队列，并同步至预警中心。</div>';
  openDrawer('风控结果 · 风险分 ' + score, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" style="background:var(--orange)" onclick="liveRiskReview()">转人工复核</button>');
}
function liveRiskReview() {
  confirmDlg('确认转人工复核？', '本场次风险分 82（高），转入人工复核队列后将暂缓开播，并通知风控值守人员复核实名人证件与账号充值情况。', '转人工复核', function () {
    closeDrawer();
    toast('已转人工复核队列，复核结果将推送消息中心', 'success');
  }, { warn: '复核期间场次不可开播，超 2 小时未复核将自动升级提醒' });
}
/* LIVE-002：下播数据录入（入口 → 场次详情·下播 Tab） */
function liveEndEntry(id) {
  liveSessionDetail(id, 'report');
}
/* 下播录入实时测算 */
function liveEntryCalc() {
  const g = Number($('#F_lgmv').value || 0), o = Number($('#F_lord').value || 0), v = Number($('#F_lview').value || 0), p = Number($('#F_lpeak').value || 0);
  if ($('#leA')) $('#leA').textContent = o > 0 ? '¥' + (g / o).toFixed(1) : '—';
  if ($('#leG')) $('#leG').textContent = v > 0 ? '¥' + (g / v * 1000).toFixed(1) : '—';
  if ($('#leP')) $('#leP').textContent = v > 0 ? ((p / v) * 100).toFixed(1) + '%' : '—';
}
/* LIVE-002：提交闭环（写入 LIVES 数据 + 状态刷新） */
function liveEndEntrySubmit(id) {
  const l = LIVES.filter(function (x) { return x.id === id; })[0];
  if (!l) return;
  if (!formValidate(['lgmv', 'lview', 'lreal'])) return;
  liveEntryCalc();
  const gmv = Number($('#F_lgmv').value || 0), ord = Number($('#F_lord').value || 0);
  const views = Number($('#F_lview').value || 0), peak = Number($('#F_lpeak').value || 0);
  confirmDlg('确认提交下播数据？', '场次 ' + l.id + '（' + l.topic + '）GMV ' + fmtMoney(gmv) + ' · 观看 ' + views.toLocaleString() + ' 人，提交后将写入台账留痕（BR-006）并同步财务核算。', '提交录入', function () {
    l.gmv = gmv; l.orders = ord; l.views = views; l.peak = peak;
    l.fans = Number($('#F_lfans').value || 0);
    l.entered = true;
    if (state.page === 'live') renderPage();
    liveSessionDetail(id, 'report');
    toast('下播数据已录入：' + l.id + ' · GMV ' + fmtMoney(gmv) + '（已同步财务/数据模块）', 'success');
    hlFirst();
  });
}

/* ===================== 15 CONTENT 内容生产 ===================== */
const SOPS = [
  { name: '标准内容生产运营流程', plat: '全平台', nodes: 14, ver: 'v1.0', on: true, preset: true, mkt: '免费公推', typ: '文章', g: 'linear-gradient(135deg,#0071e3,#34c759)' },
  { name: '跑鞋测评短视频 SOP', plat: '抖音 / 视频号', nodes: 8, ver: 'v2.3', on: true, mkt: '公司平台付费', typ: '短视频', g: 'linear-gradient(135deg,#ff9500,#ff3b30)' },
  { name: '健身跟练直播预热 SOP', plat: '抖音', nodes: 6, ver: 'v1.8', on: true, mkt: '快手付费课程', typ: '视频', g: 'linear-gradient(135deg,#0071e3,#5ac8fa)' },
  { name: '好物种草图文 SOP', plat: '小红书', nodes: 10, ver: 'v3.1', on: true, mkt: '免费公推', typ: '文章', g: 'linear-gradient(135deg,#af52da,#ff3b30)' },
  { name: '电竞赛事集锦 SOP', plat: 'B 站 / 斗鱼', nodes: 7, ver: 'v1.2', on: false, mkt: '公司平台付费', typ: '短视频', g: 'linear-gradient(135deg,#34c759,#5ac8fa)' },
  { name: '跑步知识科普 SOP', plat: '视频号', nodes: 5, ver: 'v2.0', on: true, mkt: '免费公推', typ: '文章', g: 'linear-gradient(135deg,#5ac8fa,#0071e3)' },
  { name: '夜跑安全专题 SOP', plat: '快手', nodes: 6, ver: 'v1.5', on: true, mkt: '免费公推', typ: '短视频', g: 'linear-gradient(135deg,#1d1d1f,#8e8e93)' },
  { name: '新品首发大促 SOP', plat: '全平台', nodes: 12, ver: 'v4.0', on: true, mkt: '公司平台付费', typ: '短视频', g: 'linear-gradient(135deg,#ffcc00,#ff9500)' },
  { name: '达人连麦脚本 SOP', plat: '抖音 / 快手', nodes: 9, ver: 'v1.1', on: false, mkt: '快手付费课程', typ: '视频', g: 'linear-gradient(135deg,#0071e3,#af52da)' }
];
PAGES.contentSop = function () {
  let h = pgHead('contentSop',
    '<button class="btn btn-sec" onclick="toast(\'导入预置 SOP（14 节点 4 路并行）\',\'success\')">导入预置</button>' +
    '<button class="btn btn-pri" onclick="sopEdit(-1)">' + ic('plus', 15) + '新建 SOP</button>');
  h += contentSopTab();
  return h;
};
PAGES.contentPlan = function () {
  let h = pgHead('contentPlan',
    '<button class="btn btn-sec" onclick="mktPlanAdd()">' + ic('plus', 15) + '新建营销计划</button>' +
    '<button class="btn btn-pri" onclick="opsPlanAdd()">' + ic('plus', 15) + '新建计划</button>');
  h += '<div class="dsec">营销计划（1:1 启用 SOP · CONTENT-101）</div>' + contentMktTab();
  h += '<div class="dsec" style="margin-top:18px">计划管理（CONTENT-102 · UX P-M2-011）</div>' + contentPlanTab();
  return h;
};
PAGES.contentWork = function () {
  let h = pgHead('contentWork', '<button class="btn btn-pri" onclick="wtAdd()">' + ic('plus', 15) + '登记工作任务</button>');
  h += contentWtTab();
  h += '<div class="hint" style="margin-top:10px">OPS 主路径：营销计划 → 本页矩阵确认 → <span class="btn-txt btn" onclick="go(\'contentTask\')">我的任务</span> → <span class="btn-txt btn" onclick="go(\'contentList\')">内容管理</span> → 审核 → Football 同步</div>';
  return h;
};
PAGES.contentTask = function () {
  const taskTab = state.tab.contentTask || '我的任务';
  let h = pgHead('contentTask',
    '<button class="btn btn-sec" onclick="exportX(this,\'任务清单\',' + OPS_TASKS.length + ')">导出</button>');
  h += '<div class="tabs"><div class="tab' + (taskTab === '我的任务' ? ' on' : '') + '" onclick="setTab(\'contentTask\',\'我的任务\');renderPage()">我的任务</div>' +
    '<div class="tab' + (taskTab === '全部任务' ? ' on' : '') + '" onclick="setTab(\'contentTask\',\'全部任务\');renderPage()">全部任务</div></div>';
  h += contentTaskTab(taskTab);
  return h;
};
PAGES.contentList = function () {
  let h = pgHead('contentList',
    '<button class="btn btn-sec" onclick="exportX(this,\'内容清单\',' + OPS_CONTENTS.length + ')">导出 CSV</button>' +
    '<button class="btn btn-pri" onclick="opsContentEdit(-1)">' + ic('plus', 15) + '新建内容</button>');
  h += contentOpsLibTab();
  return h;
};
PAGES.contentLayout = function () {
  let h = pgHead('contentLayout',
    '<button class="btn btn-sec" onclick="toast(\'导入向导 · 链接/Word/粘贴 HTML\',\'success\')">导入模板</button>' +
    '<button class="btn btn-pri" onclick="toast(\'新建公推模板 · 原型示意\',\'success\')">' + ic('plus', 15) + '新建模板</button>');
  h += contentLayoutTab();
  return h;
};
PAGES.contentReview = function () {
  let h = pgHead('contentReview', '<span class="csub">审核 SLA 12h · 一次通过率 74%（目标 70%+）</span>');
  h += contentReviewTab();
  return h;
};
/* ---- CONTENT Tab1：SOP 模板管理（原卡片网格） ---- */
function contentSopTab() {
  let h = '';
  SOPS.forEach(function (s, i) {
    h += '<div class="card hov" style="padding:0;overflow:hidden" onclick="sopEdit(' + i + ')">' +
      '<div style="height:96px;background:' + s.g + ';position:relative;display:flex;align-items:flex-end;padding:12px 14px">' +
      '<span style="color:rgba(255,255,255,.9);font-size:11px;font-weight:600;letter-spacing:.5px">CONTENT SOP</span>' +
      '<span class="sw' + (s.on ? ' on' : '') + '" style="position:absolute;top:10px;right:10px" onclick="event.stopPropagation();this.classList.toggle(\'on\');toast(\'SOP 已' + (s.on ? '停用' : '启用') + '\',\'success\')"><i></i></span></div>' +
      '<div style="padding:13px 14px"><b style="font-size:14px;font-weight:600;display:block;line-height:1.3">' + s.name + '</b>' +
      '<div class="csub" style="margin-top:5px">' + s.plat + '</div>' +
      '<div class="rowline" style="margin-top:10px;justify-content:space-between"><span class="csub">' + s.nodes + ' 个节点 · ' + s.ver + '</span>' + tag(s.on ? '启用中' : '已停用', s.on ? 'green' : 'gray') + '</div></div></div>';
  });
  return '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">' + h + '</div>';
}
/* ---- CONTENT Tab2：选题计划 ---- */
const TOPICS = [
  { no: 'TP20260918-01', title: '秋季跑鞋矩阵横评（6 双）', src: '热点', by: '孙倩', plan: '2026-09-25', sop: '跑鞋测评短视频 SOP', st: '已立项' },
  { no: 'TP20260917-02', title: '马拉松备赛 30 天训练计划', src: '自主', by: '何舟', plan: '2026-10-08', sop: '跑步知识科普 SOP', st: '已立项' },
  { no: 'TP20260916-03', title: '竞品新品首发拆解（AI 视角）', src: '热点', by: '陈默', plan: '2026-09-28', sop: '—', st: '待评审' },
  { no: 'TP20260915-04', title: '健身房穿搭好物种草', src: '品牌', by: '苏杳', plan: '2026-10-12', sop: '好物种草图文 SOP', st: '已立项' },
  { no: 'TP20260912-05', title: '夜跑装备红黑榜', src: '自主', by: '李澈', plan: '2026-09-30', sop: '夜跑安全专题 SOP', st: '待评审' },
  { no: 'TP20260910-06', title: '直播切片二创玩法测试', src: '达人', by: '赵敏', plan: '2026-09-22', sop: '—', st: '落选' },
  { no: 'TP20260908-07', title: '运动员饮食科普系列', src: '自主', by: '孙倩', plan: '2026-10-15', sop: '跑步知识科普 SOP', st: '已立项' }
];
function contentTopicTab() {
  const qr = state.q.content || {};
  let h = qbar(qi('选题编号', 130, qr.k0) + qi('标题关键词', 130, qr.k1) + qs(['全部来源', '热点', '达人', '品牌', '自主'], 90, qr.k2) + qs(['全部状态', '待评审', '已立项', '落选', '已取消'], 90, qr.k3) + qi('提报人', 90, qr.k4), 'qSave(\'content\')');
  const stc = { '待评审': 'blue', '已立项': 'green', '落选': 'gray', '已取消': 'gray' };
  const srcc = { '热点': 'orange', '达人': 'blue', '品牌': 'purple', '自主': 'green' };
  let rows = '';
  TOPICS.forEach(function (t, i) {
    rows += '<tr><td class="mono num">' + t.no + '</td><td style="font-weight:500">' + t.title + '</td><td>' + tag(t.src, srcc[t.src]) + '</td><td>' + t.by + '</td>' +
      '<td class="num">' + t.plan + '</td><td>' + (t.sop === '—' ? '<span style="color:var(--text2)">—</span>' : t.sop) + '</td>' +
      '<td>' + tag(t.st, stc[t.st]) + '</td>' +
      '<td>' + (t.st === '待评审' ? '<button class="btn btn-pri btn-sm" onclick="topicReview(' + i + ')">评审</button>' :
        t.st === '落选' ? '<span class="btn btn-sec btn-sm" onclick="toast(\'选题已复活重启 · 原型示意\',\'success\')">复活</span>' :
          '<span class="btn btn-sec btn-sm" onclick="toast(\'选题详情 · 原型示意\',\'success\')">详情</span>') + '</td></tr>';
  });
  h += tbl(['选题编号', '标题', '来源', '提报人', '计划发布日', '挂接 SOP', '状态', '操作'], rows);
  return h;
}
/* ---- CONTENT Tab3：AI 辅助脚本 ---- */
const SCRIPTS = [
  { no: 'SC20260918-01', title: '秋季跑鞋横评 · 开场钩子', topic: 'TP20260918-01', type: '带货话术', ver: 'v3', ai: true, st: '定稿', by: '孙倩', up: '2026-09-18 09:12' },
  { no: 'SC20260917-02', title: '马拉松备赛 · 30 天叙事线', topic: 'TP20260917-02', type: '口播', ver: 'v2', ai: true, st: '草稿', by: '何舟', up: '2026-09-17 16:40' },
  { no: 'SC20260916-03', title: '健身房穿搭 · 3 套 look 切换', topic: 'TP20260915-04', type: '剧情', ver: 'v4', ai: false, st: '定稿', by: '苏杳', up: '2026-09-16 11:25' },
  { no: 'SC20260915-04', title: '夜跑装备红黑榜 · 吐槽向', topic: 'TP20260912-05', type: '口播', ver: 'v1', ai: true, st: '草稿', by: '李澈', up: '2026-09-15 20:08' },
  { no: 'SC20260914-05', title: '饮食科普 · 碳水循环怎么吃', topic: 'TP20260908-07', type: '口播', ver: 'v5', ai: true, st: '定稿', by: '孙倩', up: '2026-09-14 15:33' },
  { no: 'SC20260913-06', title: '新品首发 · 悬念预告脚本', topic: '—', type: '带货话术', ver: 'v2', ai: false, st: '草稿', by: '赵敏', up: '2026-09-13 10:05' }
];
function contentScriptTab() {
  const qr = state.q.content || {};
  let h = qbar(qi('脚本编号 / 标题', 150, qr.k0) + qi('关联选题', 130, qr.k1) + qs(['全部类型', '口播', '剧情', '带货话术'], 100, qr.k2) + qs(['全部状态', '草稿', '定稿'], 90, qr.k3) + qs(['AI 生成', 'AI 生成', '人工撰写'], 100, qr.k4), 'qSave(\'content\')');
  const stc = { '草稿': 'blue', '定稿': 'green' };
  const tyc = { '口播': 'blue', '剧情': 'purple', '带货话术': 'orange' };
  let rows = '';
  SCRIPTS.forEach(function (s, i) {
    rows += '<tr><td class="mono num">' + s.no + '</td><td style="font-weight:500">' + s.title + '</td><td class="mono num" style="font-size:11px;color:var(--blue)">' + s.topic + '</td>' +
      '<td>' + tag(s.type, tyc[s.type]) + '</td><td class="num">' + s.ver + '</td>' +
      '<td>' + (s.ai ? '<span style="color:var(--purple);font-weight:500">' + ic('spark', 12) + ' AI 生成</span>' : '<span style="color:var(--text2)">人工撰写</span>') + '</td>' +
      '<td>' + tag(s.st, stc[s.st]) + '</td><td>' + s.by + '</td><td class="num" style="font-size:12px">' + s.up + '</td>' +
      '<td>' + (s.st === '草稿' ? '<span class="btn btn-pri btn-sm" onclick="scriptEdit(' + i + ')">编辑</span> <span class="btn btn-sec btn-sm" onclick="scriptFinalize(' + i + ')">定稿</span>' :
        '<span class="btn btn-sec btn-sm" onclick="toast(\'版本历史 · 原型示意\',\'success\')">版本历史</span>') + '</td></tr>';
  });
  h += tbl(['脚本编号', '标题', '关联选题', '类型', '版本', '来源', '状态', '作者', '更新时间', '操作'], rows);
  return h;
}
/* ---- CONTENT Tab4：AI 生产链（ComfyUI DAG） ---- */
const AITASKS = [
  { no: 'AIP20260918-01', topic: 'TP20260918-01', wf: '带货短视频·数字人+混剪 v5', prompt: '秋季跑鞋横评开场，数字人口播+实拍混剪，节奏快剪卡点…', st: '生成中', node: '视频合成', rev: '—', by: '孙倩', at: '2026-09-18 08:30' },
  { no: 'AIP20260918-02', topic: 'TP20260915-04', wf: '图文种草·封面生成 v2', prompt: '健身房场景，3 套穿搭 look 分格封面，小红书竖版…', st: '待终审', node: '成片', rev: '—', by: '苏杳', at: '2026-09-18 09:05' },
  { no: 'AIP20260917-03', topic: 'TP20260917-02', wf: '知识科普·动画图表 v3', prompt: '30 天备赛时间轴动画，蓝橙配色，数据图表逐项出现…', st: '队列中', node: '—', rev: '—', by: '何舟', at: '2026-09-17 18:22' },
  { no: 'AIP20260916-04', topic: 'TP20260912-05', wf: '带货短视频·数字人+混剪 v5', prompt: '夜跑装备红黑榜，红黑分屏对比，吐槽向字幕…', st: '终审通过', node: '成片', rev: '陈默', by: '李澈', at: '2026-09-16 14:10' },
  { no: 'AIP20260915-05', topic: 'TP20260908-07', wf: '知识科普·动画图表 v3', prompt: '碳水循环饮食金字塔动画，一日三餐场景切换…', st: '终审打回', node: '配音字幕', rev: '陈默', by: '孙倩', at: '2026-09-15 11:00' },
  { no: 'AIP20260914-06', topic: 'TP20260915-04', wf: '图文种草·封面生成 v2', prompt: '穿搭 look 全身图生成，模特姿态 3 选 1…', st: '失败', node: '分镜生成', rev: '—', by: '苏杳', at: '2026-09-14 16:45' }
];
function contentAiTab() {
  let h = '<div class="g4"><div class="card stat"><span class="l">队列等待</span><div class="n" style="color:var(--blue)">3</div><div class="d">P1 优先级 · 预计 12 分钟内调度</div></div>' +
    '<div class="card stat"><span class="l">执行中</span><div class="n" style="color:var(--cyan)">2</div><div class="d">GPU 占用 68%</div></div>' +
    '<div class="card stat"><span class="l">今日完成</span><div class="n" style="color:var(--green)">9</div><div class="d">平均耗时 14 分钟</div></div>' +
    '<div class="card stat"><span class="l">GPU 状态</span><div class="n" style="color:var(--green)">OK</div><div class="d">自建 2×4090 + 云端弹性</div></div></div>';
  const qr = state.q.content || {};
  h += qbar(qi('任务编号', 140, qr.k0) + qi('关联选题', 130, qr.k1) + qs(['全部状态', '队列中', '生成中', '待终审', '终审通过', '终审打回', '失败'], 100, qr.k2), 'qSave(\'content\')');
  const stc = { '队列中': 'blue', '生成中': 'cyan', '待终审': 'orange', '终审通过': 'green', '终审打回': 'yellow', '失败': 'red' };
  let rows = '';
  AITASKS.forEach(function (t, i) {
    rows += '<tr><td class="mono num" style="color:var(--blue);cursor:pointer" onclick="aiTaskDetail(' + i + ')">' + t.no + '</td><td class="mono num" style="font-size:11px">' + t.topic + '</td><td style="font-weight:500">' + t.wf + '</td>' +
      '<td style="color:var(--text2);font-size:12px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + t.prompt + '</td>' +
      '<td>' + tag(t.st, stc[t.st]) + '</td><td style="font-size:12px">' + t.node + '</td><td style="font-size:12px">' + t.rev + '</td><td>' + t.by + '</td><td class="num" style="font-size:12px">' + t.at + '</td>' +
      '<td>' + (t.st === '待终审' ? '<button class="btn btn-pri btn-sm" onclick="aiTaskReview(' + i + ')">终审</button>' :
        t.st === '失败' ? '<span class="btn btn-sec btn-sm" onclick="toast(\'节点重试已提交（自动重试 ≤2）\',\'success\')">重试节点</span>' :
          '<span class="btn btn-sec btn-sm" onclick="aiTaskDetail(' + i + ')">详情</span>') + '</td></tr>';
  });
  h += tbl(['任务编号', '关联选题', 'ComfyUI 工作流', '提示词摘要', '状态', '当前节点', '终审人', '创建人', '创建时间', '操作'], rows);
  return h;
}
/* ---- CONTENT Tab5：在线审核 ---- */
const REVIEWS = [
  { no: 'RV20260918-01', proj: '健身房穿搭好物种草（图文）', by: '苏杳', round: 1, plan: '2026-09-20', overdue: false, cl: '未审' },
  { no: 'RV20260918-02', proj: '秋季跑鞋横评 · 数字人成片', by: '孙倩', round: 2, plan: '2026-09-19', overdue: false, cl: '未审' },
  { no: 'RV20260917-03', proj: '碳水循环饮食动画', by: '孙倩', round: 3, plan: '2026-09-18', overdue: true, cl: '打回' },
  { no: 'RV20260916-04', proj: '夜跑装备红黑榜成片', by: '李澈', round: 1, plan: '2026-09-17', overdue: false, cl: '通过' },
  { no: 'RV20260915-05', proj: '马拉松备赛预告片', by: '何舟', round: 2, plan: '2026-09-16', overdue: false, cl: '通过' },
  { no: 'RV20260914-06', proj: '直播切片二创（测试）', by: '赵敏', round: 1, plan: '2026-09-15', overdue: false, cl: '驳回' }
];
function contentReviewTab() {
  const rvTab = state.tab.contentReview || '一级审核';
  let h = '<div class="tabs"><div class="tab' + (rvTab === '一级审核' ? ' on' : '') + '" onclick="state.tab.contentReview=\'一级审核\';renderPage()">一级审核</div>' +
    '<div class="tab' + (rvTab === '二级审核' ? ' on' : '') + '" onclick="state.tab.contentReview=\'二级审核\';renderPage()">二级审核</div></div>';
  let orows = '';
  OPS_CONTENTS.filter(function (c) { return c.st === '待审'; }).forEach(function (c) {
    const lvl = rvTab === '二级审核' ? '二级待审' : '一级待审';
    orows += '<tr><td class="mono">' + c.id + '</td><td style="font-weight:500">' + c.title + '</td><td>' + c.play + '</td><td>' + tag(lvl, rvTab === '二级审核' ? 'purple' : 'blue') + '</td>' +
      '<td><button class="btn btn-pri btn-sm" onclick="opsReviewPass(' + OPS_CONTENTS.indexOf(c) + ')">通过</button> <button class="btn btn-sec btn-sm" onclick="toast(\'打回至内容编辑\',\'warn\')">打回</button></td></tr>';
  });
  h += tbl(['内容 ID', '标题', '玩法 / matchScheme', '审核阶段', '操作'], orows || '<tr><td colspan="5" style="color:var(--text2)">暂无待审内容</td></tr>');
  h += '<div class="hint">对齐 UX P-M2-008：只读抽屉 + LayoutViewer 正文 · 通过后任务可完成（ADR-079）· 与内容管理同一 ID。</div>';
  return h;
}
function opsReviewPass(i) {
  OPS_CONTENTS[i].st = '已发布';
  OPS_CONTENTS[i].sync = '补偿中';
  const tk = OPS_TASKS.findIndex(function (t) { return t.cid === OPS_CONTENTS[i].id || t.no === OPS_CONTENTS[i].taskId; });
  if (tk >= 0) { OPS_TASKS[tk].gate = '通过'; OPS_TASKS[tk].st = '已完成'; }
  toast('审核通过 · ' + OPS_CONTENTS[i].id + ' · Football 同步已入队', 'success');
  renderPage();
}
/* ---- CONTENT Tab6：发布归档 ---- */
const PUBS = [
  { no: 'PB20260918-01', proj: '夜跑装备红黑榜成片', acct: '神鱼体育', plat: '抖音', at: '2026-09-19 19:00', cap: '#夜跑装备红黑榜 避雷向', st: '待发布', url: '—' },
  { no: 'PB20260917-02', proj: '马拉松备赛预告片', acct: '神鱼跑步研究所', plat: '视频号', at: '2026-09-18 20:00', cap: '30 天备赛全记录', st: '已发布', url: '待回填' },
  { no: 'PB20260916-03', proj: '健身房穿搭 look 1', acct: '神鱼好物优选', plat: '小红书', at: '2026-09-16 12:00', cap: '#健身房穿搭 三套 look', st: '已回填', url: 'xhs.link/a8f3d2' },
  { no: 'PB20260915-04', proj: '碳水循环饮食动画', acct: '神鱼体育', plat: '抖音', at: '2026-09-15 18:00', cap: '碳水循环到底怎么吃', st: '已归档', url: 'v.douyin.com/c2k9' },
  { no: 'PB20260914-05', proj: '饮食科普 · 碳水循环', acct: '神鱼跑步研究所', plat: '视频号', at: '2026-09-14 21:00', cap: '一日三餐科学配比', st: '已归档', url: 'channels.qq.com/9d1' }
];
function contentPublishTab() {
  let h = '<div class="card" style="margin-bottom:16px;padding:12px 16px" class="rowline"><div class="rowline" style="gap:24px"><span style="font-size:13px">待发布 <b style="color:var(--blue)">1</b></span><span style="font-size:13px">已发布待回填 <b style="color:var(--orange)">1</b> <span style="color:var(--red);font-size:12px">（超 24h 红标督办）</span></span><span style="font-size:13px">已归档 <b>2</b></span><span class="csub">回填后自动打包归档（源片+脚本+审核单+回执）</span></div></div>';
  const stc = { '待发布': 'blue', '已发布': 'cyan', '已回填': 'green', '已归档': 'gray' };
  let rows = '';
  PUBS.forEach(function (p, i) {
    rows += '<tr><td class="mono num">' + p.no + '</td><td style="font-weight:500">' + p.proj + '</td><td>' + p.acct + '</td><td>' + p.plat + '</td>' +
      '<td class="num" style="font-size:12px">' + p.at + '</td><td style="color:var(--text2);font-size:12px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + p.cap + '</td>' +
      '<td>' + tag(p.st, stc[p.st]) + '</td><td class="mono num" style="font-size:11px">' + p.url + '</td>' +
      '<td>' + (p.st === '待发布' ? '<button class="btn btn-pri btn-sm" onclick="pubExec(' + i + ')">执行发布</button>' :
        p.st === '已发布' ? '<button class="btn btn-pri btn-sm" style="background:var(--orange)" onclick="pubReceipt(' + i + ')">回填链接</button>' :
          '<span class="btn btn-sec btn-sm" onclick="toast(\'归档包下载 · 原型示意\',\'success\')">归档包</span>') + '</td></tr>';
  });
  h += tbl(['发布单号', '内容项目', '发布账号', '平台', '计划发布时间', '文案摘要', '发布状态', '链接回执', '操作'], rows);
  return h;
}
function sopEdit(idx) {
  sopDagInit(idx);
  const s = sopDag.idx < 0 ? { name: '', plat: '抖音', ver: 'v1.0', mkt: '免费公推', typ: '短视频' } : SOPS[sopDag.idx];
  const body = '<div class="formrow">' +
    '<div class="fld"><label>SOP 名称<i class="req">*</i></label><input id="SOP_name" value="' + (s.name || '') + '" placeholder="如：标准内容生产运营流程"></div>' +
    '<div class="fld"><label>适用内容类型</label><select id="SOP_typ"><option' + (s.typ === '文章' ? ' selected' : '') + '>文章</option><option' + (s.typ === '短视频' ? ' selected' : '') + '>短视频</option><option' + (s.typ === '视频' ? ' selected' : '') + '>视频</option></select></div>' +
    '<div class="fld"><label>适用平台</label><select id="SOP_plat"><option>抖音</option><option>快手</option><option>视频号</option><option>微信公众号</option><option>全平台</option></select></div>' +
    '<div class="fld"><label>营销计划（启用 1:1）</label><select id="SOP_mkt"><option>免费公推</option><option>公司平台付费</option><option>快手付费课程</option></select></div></div>' +
    '<div class="dag-tb">' +
    '<span class="btn btn-sec btn-sm" onclick="sopDagAuto()">自动布局</span>' +
    '<span class="btn btn-sec btn-sm" onclick="sopDagFit()">适配视图</span>' +
    '<span class="btn btn-sec btn-sm" onclick="sopDagValidate()">校验 DAG</span>' +
    '<span class="csub" style="margin-left:auto">CONTENT-100 · 从左侧拖入节点 · 画布内拖拽排位 · 右侧配依赖/并行组</span></div>' +
    sopDagHtml();
  openDrawer((sopDag.idx < 0 ? '新建 SOP · DAG 编排' : '编辑 SOP · ') + (s.name || '未命名'), body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button>' +
    '<button class="btn btn-pri" onclick="sopDagSave()">保存为新版本</button>', '96%');
  setTimeout(sopDagBind, 30);
}
const SOP_PALETTE = [
  { type: 'CONTENT_GENERATION', label: '内容生成', hint: '出草稿，须文档类型' },
  { type: 'CONTENT_PUBLISH', label: '内容发布', hint: '平台发布门禁' },
  { type: 'NORMAL', label: '普通节点', hint: '无内容联动' }
];
const SOP_ROLES = ['运营', '编辑', '主播', '运营组长', '直播运营', '销售'];
const SOP_DOCS = ['短视频文案', '新号引流', '赛后复盘', '正式方案', '预热前瞻'];
let sopDag = { idx: -1, nodes: [], sel: null, drag: null, nid: 1 };
function sopNid() { return 'N' + (sopDag.nid++); }
function sopStdNodes() {
  const g = function (id, name, type, x, y, pred, pg, doc, review) {
    return { id: id, name: name, type: type, x: x, y: y, pred: pred || [], pg: pg || '', role: type === 'CONTENT_GENERATION' ? '编辑' : (type === 'CONTENT_PUBLISH' ? '运营' : '运营组长'), review: !!review, rrole: review ? '运营组长' : '', doc: doc || '', sla: 8, std: '按节点交付物与质量清单执行（CONTENT-001）', qa: '交付物齐全；needReview 节点须审核通过' };
  };
  return [
    g('N1', '选题确认', 'NORMAL', 40, 220, [], '', '', false),
    g('N2', '推文生成', 'CONTENT_GENERATION', 240, 40, ['N1'], 'GROUP_A', '正式方案', false),
    g('N3', '方案生成', 'CONTENT_GENERATION', 240, 160, ['N1'], 'GROUP_A', '正式方案', false),
    g('N4', '视频脚本', 'CONTENT_GENERATION', 240, 280, ['N1'], 'GROUP_A', '短视频文案', false),
    g('N5', '直播预案', 'CONTENT_GENERATION', 240, 400, ['N1'], 'GROUP_A', '预热前瞻', false),
    g('N6', '合规审核', 'NORMAL', 460, 220, ['N2', 'N3', 'N4', 'N5'], '', '', true),
    g('N7', '推文排版', 'NORMAL', 680, 40, ['N6'], 'GROUP_B', '', false),
    g('N8', '方案定稿', 'NORMAL', 680, 160, ['N6'], 'GROUP_B', '', false),
    g('N9', '视频成片', 'NORMAL', 680, 280, ['N6'], 'GROUP_B', '', false),
    g('N10', '直播彩排', 'NORMAL', 680, 400, ['N6'], 'GROUP_B', '', false),
    g('N11', '平台发布', 'CONTENT_PUBLISH', 900, 160, ['N7', 'N8', 'N9', 'N10'], '', '', true),
    g('N12', '服务号推送', 'CONTENT_PUBLISH', 900, 280, ['N7', 'N8', 'N9', 'N10'], '', '', false),
    g('N13', '客户跟进', 'NORMAL', 1120, 220, ['N11', 'N12'], '', '', false),
    g('N14', '数据复盘', 'NORMAL', 1320, 220, ['N13'], '', '', false)
  ];
}
function sopSimpleNodes() {
  const seq = [
    ['选题立项', 'NORMAL', ''],
    ['脚本撰写', 'CONTENT_GENERATION', '短视频文案'],
    ['拍摄执行', 'NORMAL', ''],
    ['后期剪辑', 'NORMAL', ''],
    ['合规审核', 'NORMAL', ''],
    ['发布分发', 'CONTENT_PUBLISH', ''],
    ['数据复盘', 'NORMAL', '']
  ];
  return seq.map(function (n, i) {
    return { id: 'N' + (i + 1), name: n[0], type: n[1], x: 48 + i * 188, y: 210, pred: i ? ['N' + i] : [], pg: '', role: n[1] === 'CONTENT_GENERATION' ? '编辑' : '运营', review: n[0] === '合规审核', rrole: n[0] === '合规审核' ? '运营组长' : '', doc: n[2], sla: 8, std: '执行标准说明', qa: '交付物 + 质量清单全通过' };
  });
}
function sopDagInit(idx) {
  sopDag.idx = idx;
  sopDag.sel = null;
  sopDag.nid = 20;
  if (idx < 0) { sopDag.nodes = []; return; }
  const s = SOPS[idx];
  sopDag.nodes = (s && s.preset) ? sopStdNodes() : sopSimpleNodes().slice(0, Math.min(s.nodes || 7, 8));
}
function sopTypeLabel(t) {
  return t === 'CONTENT_GENERATION' ? '内容生成' : (t === 'CONTENT_PUBLISH' ? '内容发布' : '普通节点');
}
function sopDagHtml() {
  let pal = '';
  SOP_PALETTE.forEach(function (p) {
    pal += '<div class="dag-item" draggable="true" data-type="' + p.type + '"><b>' + p.label + '</b><small>' + p.hint + '</small></div>';
  });
  return '<div class="dag-wrap"><div class="dag-pal"><h4>节点库</h4>' + pal +
    '<div class="hint" style="margin-top:8px">拖到画布添加；同并行组节点可同时推进。</div></div>' +
    '<div class="dag-canvas" id="sopCanvas">' + sopDagSvg() + sopDagNodesHtml() + '</div>' +
    '<div class="dag-prop" id="sopProp">' + sopPropHtml() + '</div></div>';
}
function sopDagSvg() {
  let lines = '';
  const map = {};
  sopDag.nodes.forEach(function (n) { map[n.id] = n; });
  sopDag.nodes.forEach(function (n) {
    (n.pred || []).forEach(function (pid) {
      const p = map[pid]; if (!p) return;
      const x1 = p.x + 156, y1 = p.y + 28, x2 = n.x, y2 = n.y + 28;
      const mx = (x1 + x2) / 2;
      lines += '<path d="M' + x1 + ' ' + y1 + ' C' + mx + ' ' + y1 + ',' + mx + ' ' + y2 + ',' + x2 + ' ' + y2 + '" fill="none" stroke="#0071e3" stroke-width="1.6" opacity=".55"/>';
    });
  });
  const w = Math.max(1600, sopDag.nodes.reduce(function (m, n) { return Math.max(m, n.x + 180); }, 800));
  const h = Math.max(520, sopDag.nodes.reduce(function (m, n) { return Math.max(m, n.y + 90); }, 520));
  return '<svg class="dag-svg" width="' + w + '" height="' + h + '">' + lines + '</svg>';
}
function sopDagNodesHtml() {
  let h = '';
  sopDag.nodes.forEach(function (n) {
    const on = sopDag.sel === n.id ? ' on' : '';
    const tc = n.type === 'CONTENT_GENERATION' ? 'blue' : (n.type === 'CONTENT_PUBLISH' ? 'orange' : 'gray');
    h += '<div class="dag-node' + on + '" data-id="' + n.id + '" style="left:' + n.x + 'px;top:' + n.y + 'px">' +
      '<div class="dn">' + n.name + '</div><div class="dt">' + tag(sopTypeLabel(n.type), tc) + (n.pg ? ' <span class="chip">' + n.pg + '</span>' : '') + '</div></div>';
  });
  return h;
}
function sopPropHtml() {
  const n = sopDag.nodes.filter(function (x) { return x.id === sopDag.sel; })[0];
  if (!n) return '<h4>节点属性</h4><div class="csub">点选画布节点，或从左侧拖入。</div>';
  const roleOpts = SOP_ROLES.map(function (r) { return '<option' + (n.role === r ? ' selected' : '') + '>' + r + '</option>'; }).join('');
  const predOpts = sopDag.nodes.filter(function (x) { return x.id !== n.id; }).map(function (x) {
    return '<option value="' + x.id + '"' + ((n.pred || []).indexOf(x.id) >= 0 ? ' selected' : '') + '>' + x.name + '</option>';
  }).join('');
  const docRow = n.type === 'CONTENT_GENERATION'
    ? '<div class="fld"><label>文档类型（dict_document_type）<i class="req">*</i></label><select id="DN_doc">' + SOP_DOCS.map(function (d) { return '<option' + (n.doc === d ? ' selected' : '') + '>' + d + '</option>'; }).join('') + '</select></div>'
    : '';
  return '<h4>节点属性 · ' + n.id + '</h4>' +
    '<div class="fld"><label>节点名称</label><input id="DN_name" value="' + n.name + '"></div>' +
    '<div class="fld" style="margin-top:8px"><label>节点类型</label><select id="DN_type"><option value="CONTENT_GENERATION"' + (n.type === 'CONTENT_GENERATION' ? ' selected' : '') + '>内容生成</option><option value="CONTENT_PUBLISH"' + (n.type === 'CONTENT_PUBLISH' ? ' selected' : '') + '>内容发布</option><option value="NORMAL"' + (n.type === 'NORMAL' ? ' selected' : '') + '>普通节点</option></select></div>' +
    '<div class="fld" style="margin-top:8px"><label>执行岗位（dict_position）</label><select id="DN_role">' + roleOpts + '</select></div>' +
    '<div class="fld" style="margin-top:8px"><label>任务级审核 needReview</label><select id="DN_rev"><option value="0"' + (n.review ? '' : ' selected') + '>关闭</option><option value="1"' + (n.review ? ' selected' : '') + '>开启</option></select></div>' +
    (n.review ? '<div class="fld" style="margin-top:8px"><label>审核岗位</label><select id="DN_rrole">' + SOP_ROLES.map(function (r) { return '<option' + (n.rrole === r ? ' selected' : '') + '>' + r + '</option>'; }).join('') + '</select></div>' : '') +
    docRow +
    '<div class="fld" style="margin-top:8px"><label>前置依赖（多选）</label><select id="DN_pred" multiple size="4">' + predOpts + '</select></div>' +
    '<div class="fld" style="margin-top:8px"><label>并行组</label><input id="DN_pg" value="' + (n.pg || '') + '" placeholder="如 GROUP_A"></div>' +
    '<div class="fld" style="margin-top:8px"><label>SLA（小时）</label><input id="DN_sla" type="number" value="' + (n.sla || 8) + '"></div>' +
    '<div class="fld" style="margin-top:8px"><label>执行标准 / 质量清单</label><textarea id="DN_qa" style="min-height:64px">' + (n.qa || '') + '</textarea></div>' +
    '<div class="rowline" style="margin-top:10px"><span class="btn btn-sec btn-sm" onclick="sopPropApply()">应用属性</span><span class="btn btn-sec btn-sm" style="color:var(--red)" onclick="sopNodeDel()">删除节点</span></div>';
}
function sopDagPaint() {
  const c = $('#sopCanvas'); if (!c) return;
  c.innerHTML = sopDagSvg() + sopDagNodesHtml();
  const p = $('#sopProp'); if (p) p.innerHTML = sopPropHtml();
  sopDagBind();
}
function sopDagBind() {
  const c = $('#sopCanvas'); if (!c) return;
  c.ondragover = function (e) { e.preventDefault(); };
  c.ondrop = function (e) {
    e.preventDefault();
    const t = e.dataTransfer.getData('text/sop-type');
    if (!t) return;
    const r = c.getBoundingClientRect();
    const id = sopNid();
    sopDag.nodes.push({ id: id, name: sopTypeLabel(t) + ' ' + id, type: t, x: Math.max(16, e.clientX - r.left - 78), y: Math.max(16, e.clientY - r.top - 24), pred: [], pg: '', role: '编辑', review: false, rrole: '', doc: t === 'CONTENT_GENERATION' ? SOP_DOCS[0] : '', sla: 8, std: '', qa: '交付物齐全' });
    sopDag.sel = id;
    sopDagPaint();
  };
  Array.prototype.forEach.call(document.querySelectorAll('.dag-item'), function (el) {
    el.ondragstart = function (e) { e.dataTransfer.setData('text/sop-type', el.getAttribute('data-type')); };
  });
  Array.prototype.forEach.call(c.querySelectorAll('.dag-node'), function (el) {
    el.onmousedown = function (e) {
      if (e.button !== 0) return;
      e.stopPropagation();
      const id = el.getAttribute('data-id');
      const n = sopDag.nodes.filter(function (x) { return x.id === id; })[0];
      sopDag.sel = id;
      sopDag.drag = { id: id, dx: e.clientX - n.x, dy: e.clientY - n.y };
      sopDagPaint();
    };
  });
  document.onmousemove = function (e) {
    if (!sopDag.drag) return;
    const n = sopDag.nodes.filter(function (x) { return x.id === sopDag.drag.id; })[0];
    if (!n) return;
    n.x = Math.max(8, e.clientX - sopDag.drag.dx);
    n.y = Math.max(8, e.clientY - sopDag.drag.dy);
    const el = document.querySelector('.dag-node[data-id="' + n.id + '"]');
    if (el) { el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; }
    const svg = $('#sopCanvas .dag-svg');
    if (svg) svg.outerHTML = sopDagSvg();
  };
  document.onmouseup = function () {
    if (sopDag.drag) { sopDag.drag = null; sopDagPaint(); }
  };
}
function sopPropApply() {
  const n = sopDag.nodes.filter(function (x) { return x.id === sopDag.sel; })[0];
  if (!n) return;
  n.name = ($('#DN_name') || {}).value || n.name;
  n.type = ($('#DN_type') || {}).value || n.type;
  n.role = ($('#DN_role') || {}).value || n.role;
  n.review = ($('#DN_rev') || {}).value === '1';
  n.rrole = n.review ? (($('#DN_rrole') || {}).value || n.role) : '';
  n.doc = n.type === 'CONTENT_GENERATION' ? (($('#DN_doc') || {}).value || '') : '';
  n.pg = ($('#DN_pg') || {}).value || '';
  n.sla = Number(($('#DN_sla') || {}).value || 8);
  n.qa = ($('#DN_qa') || {}).value || '';
  const sel = $('#DN_pred');
  n.pred = sel ? Array.prototype.map.call(sel.selectedOptions, function (o) { return o.value; }) : n.pred;
  sopDagPaint();
  toast('节点属性已应用', 'success');
}
function sopNodeDel() {
  if (!sopDag.sel) return;
  const id = sopDag.sel;
  sopDag.nodes = sopDag.nodes.filter(function (n) { return n.id !== id; });
  sopDag.nodes.forEach(function (n) { n.pred = (n.pred || []).filter(function (p) { return p !== id; }); });
  sopDag.sel = null;
  sopDagPaint();
}
function sopHasCycle() {
  const map = {};
  sopDag.nodes.forEach(function (n) { map[n.id] = n.pred || []; });
  const st = {};
  function dfs(id) {
    if (st[id] === 1) return id;
    if (st[id] === 2) return null;
    st[id] = 1;
    const ps = map[id] || [];
    for (let i = 0; i < ps.length; i++) { const hit = dfs(ps[i]); if (hit) return hit; }
    st[id] = 2;
    return null;
  }
  for (let i = 0; i < sopDag.nodes.length; i++) { const hit = dfs(sopDag.nodes[i].id); if (hit) return hit; }
  return null;
}
function sopDagValidate() {
  if (!sopDag.nodes.length) { toast('模板至少包含 1 个节点', 'warn'); return false; }
  const missRole = sopDag.nodes.filter(function (n) { return !n.role; })[0];
  if (missRole) { toast('请选择执行岗位：' + missRole.name, 'warn'); return false; }
  const missDoc = sopDag.nodes.filter(function (n) { return n.type === 'CONTENT_GENERATION' && !n.doc; })[0];
  if (missDoc) { toast('内容生成节点须选文档类型（1503）：' + missDoc.name, 'warn'); return false; }
  const missRev = sopDag.nodes.filter(function (n) { return n.review && !n.rrole; })[0];
  if (missRev) { toast('开启审核时审核岗位必填：' + missRev.name, 'warn'); return false; }
  const cyc = sopHasCycle();
  if (cyc) { toast('节点 ' + cyc + ' 形成环，请重新设置前置关系', 'error'); return false; }
  toast('DAG 校验通过（无环 · 岗位/文档类型完备）', 'success');
  return true;
}
function sopDagAuto() {
  const lv = {};
  function level(id, guard) {
    if (lv[id] != null) return lv[id];
    if (guard > 40) return 0;
    const n = sopDag.nodes.filter(function (x) { return x.id === id; })[0];
    if (!n || !(n.pred || []).length) { lv[id] = 0; return 0; }
    let m = 0;
    (n.pred || []).forEach(function (p) { m = Math.max(m, level(p, guard + 1) + 1); });
    lv[id] = m; return m;
  }
  const buckets = {};
  sopDag.nodes.forEach(function (n) {
    const l = level(n.id, 0);
    (buckets[l] = buckets[l] || []).push(n);
  });
  Object.keys(buckets).forEach(function (k) {
    buckets[k].forEach(function (n, i) { n.x = 40 + Number(k) * 220; n.y = 36 + i * 120; });
  });
  sopDagPaint();
  toast('已按依赖层级自动布局', 'success');
}
function sopDagFit() {
  const c = $('#sopCanvas'); if (c) c.scrollLeft = 0;
  toast('已适配视图', 'success');
}
function sopDagSave() {
  const name = (($('#SOP_name') || {}).value || '').trim();
  if (!name) { toast('请填写 SOP 名称', 'warn'); return; }
  if (!sopDagValidate()) return;
  if (sopDag.idx < 0) {
    SOPS.unshift({ name: name, plat: ($('#SOP_plat') || {}).value, nodes: sopDag.nodes.length, ver: 'v1.0', on: false, mkt: ($('#SOP_mkt') || {}).value, typ: ($('#SOP_typ') || {}).value, g: 'linear-gradient(135deg,#0071e3,#5ac8fa)' });
  } else {
    const s = SOPS[sopDag.idx];
    const nv = 'v' + (Number(String(s.ver).replace(/[^\d.]/g, '').split('.')[0] || '1') + 1) + '.0';
    s.name = name; s.nodes = sopDag.nodes.length; s.ver = nv;
  }
  closeDrawer();
  if (isContentPage()) renderPage();
  toast('SOP 已保存为新版本（进行中项目沿用旧版本）', 'success');
}
/* ===================== CONTENT：选题/AI 脚本/AI 生产链/审核/发布 交互 ===================== */
/* 选题提报表单 */
function topicAdd() {
  const body = frow([
    { k: 'title', label: '选题标题', type: 'text', req: true, ph: '如：秋季跑鞋矩阵横评（6 双）' },
    { k: 'src', label: '来源类型', type: 'select', req: true, opts: ['热点', '达人', '品牌', '自主'] },
    { k: 'plan', label: '计划发布日', type: 'date', req: true, val: '2026-10-01' },
    { k: 'desc', label: '选题描述', type: 'textarea', req: true, ph: '选题背景、对标参考、预期数据目标', wide: true }
  ]);
  openDrawer('提报选题', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="topicAddSubmit()">提交提报</button>', '520px');
}
function topicAddSubmit() {
  if (!formValidate(['title', 'src', 'plan', 'desc'])) return;
  const no = 'TP20260918-' + String(TOPICS.length + 1).padStart(2, '0');
  TOPICS.unshift({ no: no, title: $('#F_title').value.trim(), src: $('#F_src').value, by: 'Donny', plan: $('#F_plan').value, sop: '—', st: '待评审' });
  if (isContentPage()) renderPage();
  formOk(no, '选题已提交，等待运营总监评审（R4）', '');
  toast('选题提报成功：' + no, 'success');
}
/* 选题评审立项（R4） */
function topicReview(i) {
  const t = TOPICS[i];
  const body = frow([
    { k: 'sop', label: '挂接 SOP（立项必选）', type: 'select', req: true, opts: SOPS.filter(function (s) { return s.on; }).map(function (s) { return s.name; }) },
    { k: 'plan', label: '确认计划发布日', type: 'date', req: true, val: t.plan },
    { k: 'op', label: '评审意见（落选时必填）', type: 'textarea', ph: '立项则留空；落选请说明原因', wide: true }
  ]);
  openDrawer('评审立项 · ' + t.no, '<div class="kv" style="margin-bottom:12px"><div><div class="k">选题标题</div><div class="v">' + t.title + '</div></div><div><div class="k">提报人 / 来源</div><div class="v">' + t.by + ' · ' + t.src + '</div></div></div>' + body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button>' +
    '<button class="btn btn-sec" style="color:var(--red)" onclick="topicReject(' + i + ')">落选</button>' +
    '<button class="btn btn-pri" onclick="topicApprove(' + i + ')">立项</button>', '560px');
}
function topicApprove(i) {
  if (!formValidate(['sop', 'plan'])) return;
  const t = TOPICS[i];
  t.st = '已立项'; t.sop = $('#F_sop').value; t.plan = $('#F_plan').value;
  closeDrawer();
  if (isContentPage()) renderPage();
  toast('已立项：挂接「' + t.sop + '」，自动创建内容项目进入生产流转', 'success');
  hlFirst();
}
function topicReject(i) {
  if (!$('#F_op') || !$('#F_op').value.trim()) { toast('落选请填写评审意见', 'warn'); return; }
  const t = TOPICS[i];
  t.st = '落选';
  closeDrawer();
  if (isContentPage()) renderPage();
  toast('已落选归档（可复活重启）', 'warn');
}
/* AI 生成脚本（生成候选 → 采用并编辑） */
function scriptGen() {
  const topics = TOPICS.filter(function (t) { return t.st === '已立项'; }).map(function (t) { return t.no + ' · ' + t.title; });
  const body = frow([
    { k: 'topic', label: '关联选题', type: 'select', req: true, opts: topics },
    { k: 'type', label: '脚本类型', type: 'select', req: true, opts: ['口播', '剧情', '带货话术'] },
    { k: 'req', label: '内容要求', type: 'textarea', req: true, ph: '如：开场 3 秒钩子，突出缓震对比，结尾行动号召', wide: true },
    { k: 'cnt', label: '生成候选数', type: 'pills', opts: ['2', '3'], val: '3' }
  ]);
  openDrawer('AI 生成脚本', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" style="background:var(--purple)" onclick="scriptGenRun()">开始生成</button>', '600px');
}
function scriptGenRun() {
  if (!formValidate(['topic', 'type', 'req'])) return;
  const cands = [
    '【钩子型开场】\n你花 899 买的跑鞋，可能缓震还不如这双 399 的……\n（痛点 → 双鞋对比实测 → 数据结论 → 点击购物车）',
    '【悬念型开场】\n我劝你先别买秋季新款跑鞋，看完这 3 组数据再说……\n（悬念 → 逐组拆解 → 避雷结论 → 关注看下期）',
    '【场景型开场】\n每天夜跑 5 公里的我，脚底板终于不疼了……\n（场景代入 → 产品出现 → 上脚实测 → 优惠行动号召）'
  ].slice(0, Number(($('#F_cnt') || {}).value || 3));
  let cl = '';
  cands.forEach(function (c2, n) {
    cl += '<div class="card" style="box-shadow:none;border:1px solid var(--line);padding:12px;margin-bottom:10px">' +
      '<div class="rowline" style="margin-bottom:6px"><b style="font-size:12.5px">候选 ' + (n + 1) + '</b><span style="margin-left:auto;color:var(--text2);font-size:11px">提示词快照已留痕 · 可复现</span></div>' +
      '<div style="font-size:12px;color:var(--text2);line-height:1.6;white-space:pre-wrap">' + c2 + '</div>' +
      '<div style="margin-top:8px"><span class="btn btn-pri btn-sm" onclick="scriptAdopt(' + n + ')">采用并编辑</span></div></div>';
  });
  openDrawer('AI 生成结果 · 候选 ' + cands.length + ' 版', cl,
    '<button class="btn btn-sec" onclick="scriptGen()">重新生成</button><span style="flex:1"></span><button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '640px');
  toast('AI 已生成 ' + cands.length + ' 版候选脚本（LLM 提示词快照留痕）', 'success');
}
function scriptAdopt(n) {
  closeDrawer();
  const no = 'SC20260918-' + String(SCRIPTS.length + 1).padStart(2, '0');
  SCRIPTS.unshift({ no: no, title: 'AI 脚本 · 候选 ' + (n + 1), topic: 'TP20260918-01', type: '口播', ver: 'v1', ai: true, st: '草稿', by: 'Donny', up: '2026-09-18 ' + new Date().getHours() + ':' + String(new Date().getMinutes()).padStart(2, '0') });
  if (isContentPage()) renderPage();
  toast('候选已采用，脚本进入编辑器（需人工润色后方可定稿）', 'success');
  hlFirst();
}
/* 脚本编辑器（Markdown）与定稿（SCR-R1 人工编辑校验） */
function scriptEdit(i) {
  const s = SCRIPTS[i];
  const body = '<div class="fld"><label>脚本内容（Markdown）</label><textarea id="SC_content" style="min-height:220px;font-family:ui-monospace,Menlo,monospace;font-size:12.5px">' + (s.ai ? '【钩子型开场】\n你花 899 买的跑鞋，可能缓震还不如这双 399 的……\n（痛点 → 双鞋对比实测 → 数据结论 → 点击购物车）' : s.title + ' 正文内容……') + '</textarea></div>' +
    '<div class="rowline" style="margin-top:10px;gap:8px"><span class="chip">' + (s.ai ? 'AI 生成 · 需人工润色' : '人工撰写') + '</span><span class="chip">版本 ' + s.ver + '</span><span class="chip" style="background:rgba(175,82,218,.12);color:var(--purple)">提示词快照可回溯</span></div>';
  openDrawer('脚本编辑 · ' + s.no + ' ' + s.title, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button>' +
    '<button class="btn btn-sec" onclick="toast(\'已保存新版本（历史可回溯）\',\'success\');closeDrawer()">保存新版本</button>' +
    '<button class="btn btn-pri" onclick="scriptFinalize(' + i + ')">定稿锁定</button>', '720px');
}
function scriptFinalize(i) {
  const s = SCRIPTS[i];
  if (s.ai && !confirmOpened()) { toast('AI 生成脚本必须人工编辑后方可定稿（SCR-R1）', 'warn'); return; }
  confirmDlg('定稿确认', '定稿后内容锁定只读，将作为下游 AI 生产任务的输入。确认定稿「' + s.title + '」？', '确认定稿', function () {
    s.st = '定稿'; s.ver = 'v' + (Number(s.ver.slice(1)) + 1);
    if (isContentPage()) renderPage();
    toast('脚本已定稿锁定：' + s.no + '（可挂接到 AI 生产任务）', 'success');
    hlFirst();
  });
}
/* AI 生产任务创建（生成提示词 → 提交队列） */
function aiTaskCreate() {
  const body = frow([
    { k: 'topic', label: '关联选题', type: 'select', req: true, opts: TOPICS.filter(function (t) { return t.st === '已立项'; }).map(function (t) { return t.no + ' · ' + t.title; }) },
    { k: 'script', label: '挂接定稿脚本（可选）', type: 'select', opts: ['不挂接', 'SC20260918-01 · 秋季跑鞋横评（定稿）', 'SC20260914-05 · 碳水循环（定稿）'] },
    { k: 'wf', label: 'ComfyUI 工作流', type: 'select', req: true, opts: ['带货短视频·数字人+混剪 v5', '知识科普·动画图表 v3', '图文种草·封面生成 v2'] },
    { k: 'style', label: '风格参数', type: 'pills', opts: ['快节奏', '中速', '舒缓'], val: '快节奏' },
    { k: 'req', label: '内容要求', type: 'textarea', req: true, ph: '如：开场 3 秒钩子 + 数字人 + 实拍混剪 + 卡点字幕', wide: true }
  ]);
  openDrawer('创建 AI 生产任务', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button>' +
    '<button class="btn btn-sec" style="color:var(--purple)" onclick="aiPromptPreview()">生成提示词</button>' +
    '<button class="btn btn-pri" style="background:var(--purple)" onclick="aiTaskSubmit()">创建并提交队列</button>', '640px');
}
function aiPromptPreview() {
  if (!formValidate(['topic', 'wf', 'req'])) return;
  toast('提示词已生成（可人工调整，调整留版本）· 原型示意', 'success');
}
function aiTaskSubmit() {
  if (!formValidate(['topic', 'wf', 'req'])) return;
  const no = 'AIP20260918-' + String(AITASKS.length + 1).padStart(2, '0');
  AITASKS.unshift({ no: no, topic: 'TP20260918-01', wf: $('#F_wf').value, prompt: $('#F_req').value.slice(0, 40) + '…', st: '队列中', node: '—', rev: '—', by: 'Donny', at: '2026-09-18 ' + new Date().getHours() + ':' + String(new Date().getMinutes()).padStart(2, '0') });
  if (isContentPage()) renderPage();
  formOk(no, '任务已提交优先级队列（P1），等待 GPU 调度；DAG：分镜生成→视频合成→配音字幕→成片', '');
  toast('生产任务已提交队列：' + no, 'success');
}
/* AI 任务详情（DAG 执行视图） */
function aiTaskDetail(i) {
  const t = AITASKS[i];
  const dag = [
    { n: '分镜生成', s: 'SUCCESS', d: '2m 14s', r: 0 },
    { n: '视频合成', s: t.st === '生成中' ? 'RUNNING' : 'SUCCESS', d: '5m 32s', r: 0 },
    { n: '配音字幕', s: t.st === '终审打回' ? 'FAILED' : (t.st === '队列中' ? 'WAITING' : 'SUCCESS'), d: '1m 48s', r: t.st === '终审打回' ? 2 : 0 },
    { n: '成片', s: t.st === '队列中' ? 'WAITING' : 'SUCCESS', d: '0m 40s', r: 0 }
  ];
  const ds = { WAITING: ['gray', '等待'], RUNNING: ['cyan', '执行中'], SUCCESS: ['green', '成功'], FAILED: ['red', '失败'], TIMEOUT: ['orange', '超时'] };
  let dl = '';
  dag.forEach(function (d2, n) {
    dl += '<div class="mg-i" style="border-radius:8px;' + (d2.s === 'RUNNING' ? 'background:var(--blue-bg)' : d2.s === 'FAILED' ? 'background:rgba(255,59,48,.08)' : '') + '">' +
      '<span class="lv" style="background:rgba(0,113,227,.12);color:var(--blue)">' + (n + 1) + '</span>' +
      '<div style="flex:1;min-width:0"><div class="mt" style="font-size:12.5px;font-weight:600">' + d2.n + '</div><div class="csub" style="font-size:11px">' + d2.d + (d2.r > 0 ? ' · 重试 ' + d2.r + ' 次' : '') + '</div></div>' +
      tag(ds[d2.s][1], ds[d2.s][0]) + '</div>';
    if (n < dag.length - 1) dl += '<div style="padding:2px 0 2px 22px;color:var(--text2)">' + ic('chev', 12) + '</div>';
  });
  const stc = { '队列中': 'blue', '生成中': 'cyan', '待终审': 'orange', '终审通过': 'green', '终审打回': 'yellow', '失败': 'red' };
  const body = '<div class="kv" style="margin-bottom:12px">' +
    '<div><div class="k">任务编号 / 状态</div><div class="v">' + t.no + ' ' + tag(t.st, stc[t.st]) + '</div></div>' +
    '<div><div class="k">ComfyUI 工作流</div><div class="v">' + t.wf + '</div></div>' +
    '<div><div class="k">提示词（可调整 · 留版本）</div><div class="v" style="font-size:12px">' + t.prompt + '</div></div></div>' +
    '<div class="dsec">DAG 执行视图（生成中 10s 自动刷新）</div>' + dl +
    '<div class="dsec">产物预览</div><div class="card" style="box-shadow:none;border:1px dashed var(--line2);padding:24px;text-align:center"><div style="color:var(--text2);font-size:13px">' + ic('play', 22) + ' 成片在线预览位（60s 签名 URL · 终审通过前禁止下载）</div></div>';
  openDrawer('AI 生产任务 · ' + t.no, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (t.st === '待终审' ? '<button class="btn btn-pri btn-sm" onclick="aiTaskReview(' + i + ')">人工终审</button>' : '') +
    (t.st === '失败' || t.st === '终审打回' ? '<button class="btn btn-sec btn-sm" onclick="toast(\'定向重生成已提交（AIP-R3 非全链重跑）\',\'success\')">打回节点重生成</button>' : ''), '90%');
}
/* AI 任务人工终审（通过/打回到指定 DAG 节点） */
function aiTaskReview(i) {
  const t = AITASKS[i];
  const body = frow([
    { k: 'op', label: '终审意见', type: 'textarea', ph: '通过可留空；打回必填', wide: true },
    { k: 'node', label: '打回指定节点（打回时必选）', type: 'select', opts: ['分镜生成', '视频合成', '配音字幕'] }
  ]);
  openDrawer('人工终审 · ' + t.no, '<div class="card" style="box-shadow:none;border:1px dashed var(--line2);padding:18px;text-align:center;margin-bottom:12px;color:var(--text2)">' + ic('play', 20) + ' 成片预览（通过前禁止下载 · AIP-R5）</div>' + body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button>' +
    '<button class="btn btn-sec" style="color:var(--red)" onclick="aiReviewReject(' + i + ')">打回</button>' +
    '<button class="btn btn-pri" onclick="aiReviewPass(' + i + ')">终审通过</button>', '640px');
}
function aiReviewPass(i) {
  const t = AITASKS[i];
  t.st = '终审通过'; t.rev = 'Donny'; t.node = '成片';
  closeDrawer();
  if (isContentPage()) renderPage();
  toast('终审通过：成片已解锁，移交发布（P6 可建发布单）', 'success');
  hlFirst();
}
function aiReviewReject(i) {
  if (!$('#F_op') || !$('#F_op').value.trim()) { toast('打回必填终审意见', 'warn'); return; }
  const t = AITASKS[i];
  t.st = '终审打回'; t.rev = 'Donny';
  closeDrawer();
  if (isContentPage()) renderPage();
  toast('已打回到「' + (($('#F_node') || {}).value || '配音字幕') + '」节点定向重生成（AIP-R3）', 'warn');
}
/* 在线审核（三维度清单） */
function reviewDo(i) {
  const r = REVIEWS[i];
  const items = [
    ['合规', '无广告法禁用词（最/第一/国家级）'],
    ['合规', '产品资质与检测报告齐备'],
    ['质量', '对照 SOP 清单逐项达标'],
    ['质量', '字幕规范与封面质量达标'],
    ['品牌', '品牌露出与口径一致']
  ];
  let cl = '';
  items.forEach(function (it, n) {
    cl += '<div class="rowline" style="padding:7px 0;border-bottom:1px solid var(--line)"><span class="chip" style="flex:none">' + it[0] + '</span><span style="font-size:12.5px;flex:1">' + it[1] + '</span><span class="sw" style="transform:scale(.8)" onclick="this.classList.toggle(\'on\')"><i></i></span></div>';
  });
  const body = '<div class="rowline" style="gap:14px;margin-bottom:12px"><div class="card" style="flex:1.2;box-shadow:none;border:1px solid var(--line);padding:18px;text-align:center;color:var(--text2)">' + ic('play', 20) + '<div style="font-size:12px;margin-top:6px">内容在线预览（禁止下载）</div></div>' +
    '<div class="card" style="flex:1;box-shadow:none;border:1px solid var(--line);padding:10px 14px"><b style="font-size:12.5px;display:block;margin-bottom:4px">审核检查清单（三维度）</b>' + cl + '</div></div>' +
    '<div class="fld"><label>审核备注 / 打回说明（打回必填）</label><textarea id="RV_op" style="min-height:60px"></textarea></div>';
  openDrawer('在线审核 · ' + r.no + '（第 ' + r.round + ' 轮）', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button>' +
    '<button class="btn btn-sec" style="color:var(--red)" onclick="reviewReject(' + i + ')">打回 / 终止</button>' +
    '<button class="btn btn-pri" onclick="reviewPass(' + i + ')">通过</button>', '90%');
}
function reviewPass(i) {
  const r = REVIEWS[i];
  r.cl = '通过';
  closeDrawer();
  if (isContentPage()) renderPage();
  toast('审核通过：内容进入发布准备（可创建发布单 · PUB-R1）', 'success');
  hlFirst();
}
function reviewReject(i) {
  if (!$('#RV_op') || !$('#RV_op').value.trim()) { toast('打回/终止必须填写说明（REV-R2）', 'warn'); return; }
  const r = REVIEWS[i];
  r.cl = r.round >= 2 ? '驳回' : '打回';
  r.round += 1;
  closeDrawer();
  if (isContentPage()) renderPage();
  toast(r.round >= 3 ? '第 3 轮打回：已升级运营总监裁决（REV-R3）' : '已打回指定节点重做，轮次 +1', 'warn');
}
/* 发布：创建发布单 / 执行发布 / 回填链接 */
function pubAdd() {
  const body = frow([
    { k: 'proj', label: '内容项目（仅审核通过）', type: 'select', req: true, opts: ['秋季跑鞋横评 · 数字人成片（终审通过）', '健身房穿搭 look 2（审核通过）'] },
    { k: 'acct', label: '发布账号（使用中）', type: 'select', req: true, opts: ['神鱼体育（抖音）', '神鱼跑步研究所（视频号）', '神鱼好物优选（小红书）'] },
    { k: 'at', label: '计划发布时间', type: 'dt', req: true, val: '2026-09-20T19:00' },
    { k: 'cap', label: '文案 / 话题', type: 'textarea', req: true, ph: '如：#秋季跑鞋横评 点击购物车', wide: true }
  ]);
  openDrawer('创建发布单', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="pubAddSubmit()">创建发布单</button>', '520px');
}
function pubAddSubmit() {
  if (!formValidate(['proj', 'acct', 'at', 'cap'])) return;
  const no = 'PB20260918-' + String(PUBS.length + 1).padStart(2, '0');
  PUBS.unshift({ no: no, proj: $('#F_proj').value, acct: '神鱼体育', plat: '抖音', at: '2026-09-20 19:00', cap: $('#F_cap').value, st: '待发布', url: '—' });
  if (isContentPage()) renderPage();
  formOk(no, '发布单已创建，等待计划发布时间执行', '');
  toast('发布单创建成功：' + no, 'success');
}
function pubExec(i) {
  confirmDlg('执行发布确认', '将按计划时间把成片发布到目标账号平台（原型示意）。', '确认发布', function () {
    PUBS[i].st = '已发布';
    if (isContentPage()) renderPage();
    toast('已执行发布，请 24h 内回填发布链接', 'success');
  });
}
function pubReceipt(i) {
  const body = frow([
    { k: 'url', label: '发布链接', type: 'text', req: true, ph: '粘贴平台发布后的作品链接（URL）' }
  ]);
  openDrawer('回填发布链接 · ' + PUBS[i].no, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="pubReceiptSubmit(' + i + ')">保存并归档</button>', '480px');
}
function pubReceiptSubmit(i) {
  if (!formValidate(['url'])) return;
  const p = PUBS[i];
  p.url = $('#F_url').value.trim(); p.st = '已回填';
  closeDrawer();
  if (isContentPage()) renderPage();
  toast('链接已回填，归档包自动打包（源片+脚本+审核单+回执）', 'success');
  hlFirst();
}
/* scriptFinalize 辅助：确认弹窗是否已打开（防误触发 SCR-R1 提示后直接通过） */
function confirmOpened() { return !!document.querySelector('.cfwrap'); }
