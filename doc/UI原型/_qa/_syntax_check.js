
'use strict';
/* ===================== 基础工具 ===================== */
const $ = (s, el) => (el || document).querySelector(s);
const state = { role: 'R1', page: 'workbench', tab: {}, gc: {}, qz: null, msgOpen: false, q: {} };

function fmtMoney(n) { return '¥' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function maskPhone(p) { return p.slice(0, 3) + '****' + p.slice(-4); }
function maskID(id) { return id.slice(0, 3) + '*'.repeat(Math.max(id.length - 7, 8)) + id.slice(-4); }
/* R9 数据分析师视角：敏感字段脱敏 */
function sens(v) { return state.role === 'R9' ? '<span class="masked">••••</span>' : v; }
function pgbar(pct, color) { return '<span class="pg" style="width:70px"><i style="width:' + Math.min(pct, 100) + '%;background:' + (color || 'var(--blue)') + '"></i></span>'; }

const TAGMAP = {
  green: ['52,199,89', '#1e8e3e'], blue: ['0,113,227', '#0071e3'], red: ['255,59,48', '#d70015'],
  orange: ['255,149,0', '#c46a00'], gray: ['142,142,147', '#6d6d72'], cyan: ['90,200,250', '#0e7fb8'],
  purple: ['175,82,218', '#8944ab'], yellow: ['255,204,0', '#a07d00']
};
function tag(t, c) {
  const m = TAGMAP[c] || TAGMAP.gray;
  return '<span class="tag" style="background:rgba(' + m[0] + ',.12);color:' + m[1] + '"><span class="dot"></span>' + t + '</span>';
}

/* ===================== 内联 SVG 图标 ===================== */
const IC = {
  star: 'M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z',
  shield: 'M12 3l7 3v6c0 4.4-2.9 7.6-7 9-4.1-1.4-7-4.6-7-9V6z',
  box: 'M3 8l9-5 9 5v8l-9 5-9-5zM3 8l9 5 9-5M12 13v8',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM5 20c1.2-3.2 3.7-5 7-5s5.8 1.8 7 5',
  id: 'M3 6h18v12H3zM7 15a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM11 12h6M11 15h4',
  video: 'M15 10l6-3.5v11L15 14zM3 7h12v10H3z',
  film: 'M4 4h16v16H4zM4 9h16M4 15h16M9 4v16M15 4v16',
  book: 'M6 3h9a3 3 0 0 1 3 3v15H9a3 3 0 0 1-3-3zM18 6v12',
  cal: 'M5 5h14v16H5zM5 9h14M9 3v4M15 3v4',
  doc: 'M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 16h6',
  flow: 'M7 4h10v4H7zM7 16h10v4H7zM12 8v4M12 12l-3 3M12 12l3 3',
  yuan: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM8.5 7l3.5 5 3.5-5M9 12.5h6M9 15.5h6',
  chart: 'M5 20V10M12 20V4M19 20v-7',
  bell: 'M18 15V10a6 6 0 1 0-12 0v5l-2 3h16zM10 21h4',
  target: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z',
  db: 'M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3',
  people: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20c1-3 3.5-4.5 6.5-4.5s5.5 1.5 6.5 4.5M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 15.8c1.5.7 2.5 2 3 4.2',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM16.5 16.5L21 21',
  help: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9a2.5 2. 5 0 1 1 4 2c-1 .8-2 1.2-2 2.5M12 17h.01',
  chev: 'M6 9l6 6 6-6',
  right: 'M9 6l6 6-6 6',
  x: 'M6 6l12 12M18 6L6 18',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2',
  check: 'M5 12l5 5 9-11',
  plus: 'M12 5v14M5 12h14',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  warn: 'M12 3l9 17H3zM12 10v4M12 17h.01'
};
function ic(n, s) {
  s = s || 16;
  return '<svg width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="' + (IC[n] || IC.doc) + '"/></svg>';
}
function av(name, bg) { return '<span class="av" style="background:' + (bg || 'var(--blue)') + '">' + name.slice(0, 1) + '</span>'; }

/* ===================== 角色体系 ===================== */
const ROLES = {
  R1: { name: '系统管理员', user: 'Donny', modules: '*' },
  R2: { name: '行政管理员', user: '林岚', modules: ['workbench', 'cert', 'asset', 'acct', 'train', 'meet', 'report'] },
  R3: { name: '财务管理员', user: '周晴', modules: ['workbench', 'fin', 'asset', 'acct', 'alert'] },
  R4: { name: '运营总监', user: '何舟', modules: ['workbench', 'live', 'content', 'perf', 'report', 'comp', 'dc', 'bi', 'eff', 'alert'] },
  R5: { name: '直播运营', user: '赵敏', modules: ['workbench', 'live', 'content', 'report'] },
  R6: { name: '短视频运营', user: '孙倩', modules: ['workbench', 'content', 'report'] },
  R7: { name: '主播/达人', user: '苏杳', modules: ['workbench', 'live', 'cert'] },
  R8: { name: '内容审核员', user: '李澈', modules: ['workbench', 'content'] },
  R9: { name: '数据分析师', user: '陈默', modules: ['workbench', 'dc', 'bi', 'comp', 'eff', 'cert', 'acct'] },
  R10: { name: '外协人员', user: '王野', modules: ['workbench'] }
};

/* ===================== 模块定义 ===================== */
const MODS = {
  workbench: { no: '', name: '工作台', code: 'HOME', icon: 'star', page: '工作台首页', desc: '一站式待办中心与快捷入口' },
  auth: { no: '01', name: '权限管理', code: 'AUTH', icon: 'shield', page: '权限管理首页', desc: '统一账号体系与钉钉组织架构同步' },
  asset: { no: '07', name: '资产管理', code: 'ASSET', icon: 'box', page: '资产台账', desc: '设备资产全生命周期登记与流转' },
  acct: { no: '08', name: '账号管理', code: 'ACCT', icon: 'user', page: '账号台账', desc: '直播/短视频账号池统一管理与领用' },
  cert: { no: '06', name: '证件档案', code: 'CERT', icon: 'id', page: '证件档案', desc: '员工证件数字化存档与水印分级查看' },
  live: { no: '10', name: '直播管理', code: 'LIVE', icon: 'video', page: '直播管理', desc: '开播风控登记与场次全量台账' },
  content: { no: '15', name: '内容生产', code: 'CONTENT', icon: 'film', page: 'SOP 模板管理', desc: '内容生产 SOP 编排与节点提示词' },
  train: { no: '02', name: '培训', code: 'TRAIN', icon: 'book', page: '培训管理', desc: '培训计划、报名与签到管理' },
  meet: { no: '03', name: '会议', code: 'MEET', icon: 'cal', page: '会议管理', desc: '会议室预约与会议纪要跟踪' },
  report: { no: '03', name: '日报', code: 'REPORT', icon: 'doc', page: '日报中心', desc: '直播/短视频/运营/行政日报统一中心' },
  flow: { no: '14', name: '工作流', code: 'FLOW', icon: 'flow', page: '流程管理', desc: '审批流程发起、流转与催办' },
  fin: { no: '11', name: '财务核算', code: 'FIN', icon: 'yuan', page: '成本核算', desc: '直播场次收入成本与主播分成结算' },
  perf: { no: '05', name: '绩效', code: 'PERF', icon: 'chart', page: '绩效考核', desc: 'KPI 考核方案、在线考试与考核结果' },
  alert: { no: '13', name: '预警', code: 'ALERT', icon: 'bell', page: '预警中心', desc: '预警规则配置与实时预警处理' },
  comp: { no: '04', name: '竞品', code: 'COMP', icon: 'target', page: '竞品库', desc: '竞品账号数据追踪与对比分析' },
  dc: { no: '12', name: '数据中心', code: 'DC', icon: 'db', page: '数据总览', desc: '账号-资产-实名人-场次-成本-利润全链穿透' },
  bi: { no: '17', name: '数据分析', code: 'BI', icon: 'chart', page: '报表中心', desc: '运营看板与经营分析报表' },
  eff: { no: '19', name: '组织人效', code: 'EFF', icon: 'people', page: '人效看板', desc: '人员主兼职归属分摊与人效分析' }
};
/* 业务域分组（用户视角）：组标题 + 模块 id 列表；可见性按角色白名单过滤 */
const GROUPS = [
  ['工作台', ['workbench']],
  ['组织与人员', ['auth', 'cert', 'train', 'perf', 'eff']],
  ['资源管理', ['asset', 'acct']],
  ['直播与内容', ['live', 'content', 'comp']],
  ['协同办公', ['meet', 'report', 'flow']],
  ['财务', ['fin']],
  ['数据与分析', ['dc', 'bi', 'alert']]
];
const PAGES = {}; /* 各模块渲染函数注册表 */

function canAccess(id) { const r = ROLES[state.role]; return r.modules === '*' || r.modules.indexOf(id) >= 0; }
function go(id) {
  if (!canAccess(id)) { toast('当前角色（' + ROLES[state.role].name + '）无权限访问该模块', 'warn'); return; }
  state.page = id;
  renderAll();
  $('#content').scrollTop = 0;
}
function setTab(pid, t) { state.tab[pid] = t; renderPage(); }
function tgGroup(g) { state.gc[g] = !state.gc[g]; renderSidebar(); }

/* ===================== 渲染骨架 ===================== */
function renderSidebar() {
  let h = '<div class="logo"><b>IMS 一体化管理系统</b><small>神鱼体育 · SHENYU SPORTS</small></div><nav class="nav">';
  GROUPS.forEach(function (g) {
    const gid = g[0], closed = state.gc[gid];
    /* 角色无权访问组内全部模块时，整组（含标题）隐藏 */
    const visible = g[1].filter(function (mid) { return canAccess(mid); });
    if (!visible.length) return;
    h += '<div class="nav-g' + (closed ? ' closed' : '') + '"><div class="nav-g-h" onclick="tgGroup(\'' + gid + '\')">' + gid +
      '<span class="caret">' + ic('chev', 12) + '</span></div>';
    visible.forEach(function (mid) {
      const m = MODS[mid];
      h += '<div class="nav-item' + (state.page === mid ? ' active' : '') + '" onclick="go(\'' + mid + '\')">' + ic(m.icon, 16) +
        '<span>' + m.name + '</span><span class="nc">' + (m.code ? m.no + ' ' + m.code : '') + '</span></div>';
    });
    h += '</div>';
  });
  h += '</nav>';
  const r = ROLES[state.role];
  h += '<div class="uCard">' + av(r.user, '#0071e3') + '<div><div class="un">' + r.user + '</div><div class="ur">' + state.role + ' · ' + r.name + '</div></div></div>';
  $('#sidebar').innerHTML = h;
}
function renderTopbar() {
  const m = MODS[state.page], r = ROLES[state.role], unread = MSGS.filter(function (x) { return !x.read; }).length;
  $('#topbar').innerHTML =
    '<div class="crumb"><b>' + m.name + '</b> / ' + m.page + '</div>' +
    '<div class="search">' + ic('search', 14) + '<input id="gsearch" placeholder="搜索模块、单据、账号…" onkeydown="if(event.key===\'Enter\'){toast(\'搜索「\'+this.value+\'」· 原型示意\',\'success\')}"><span class="kbd">⌘K</span></div>' +
    '<div class="tb-ic" onclick="openMsg()" title="消息中心">' + ic('bell', 19) + (unread ? '<span class="badge">' + unread + '</span>' : '') + '</div>' +
    '<div class="tb-ic" onclick="toast(\'帮助中心 · 原型示意\',\'success\')" title="帮助">' + ic('help', 19) + '</div>' +
    '<div class="rolebtn" onclick="toggleRoleMenu(event)">' + av(r.user, '#34c759') + '<span>' + state.role + ' ' + r.name + '</span>' + ic('chev', 13) + '</div>';
}
function renderPage() {
  const fn = PAGES[state.page] || PAGES.workbench;
  $('#content').innerHTML = '<div class="page">' + fn() + '</div>';
}
function renderAll() { renderSidebar(); renderTopbar(); renderPage(); }

/* ===================== 角色切换 ===================== */
function toggleRoleMenu(e) { e.stopPropagation(); $('#rolemenu').classList.toggle('on'); }
function renderRoleMenu() {
  let h = '<div class="rm-h">切换角色（实时生效）</div>';
  Object.keys(ROLES).forEach(function (k) {
    const r = ROLES[k];
    h += '<div class="rm-i' + (state.role === k ? ' on' : '') + '" onclick="setRole(\'' + k + '\')">' + av(r.user, state.role === k ? '#0071e3' : '#8e8e93') +
      '<div><div class="rn">' + r.user + '</div><div class="rr">' + r.name + '</div></div><span class="rc">' + k + '</span></div>';
  });
  $('#rolemenu').innerHTML = h;
}
function setRole(k) {
  state.role = k;
  $('#rolemenu').classList.remove('on');
  if (!canAccess(state.page)) { state.page = 'workbench'; toast('已切换为 ' + k + ' ' + ROLES[k].name + '，跳转至工作台', 'success'); }
  else { toast('已切换角色：' + k + ' ' + ROLES[k].name, 'success'); }
  renderRoleMenu(); renderAll();
}
document.addEventListener('click', function (e) {
  const m = $('#rolemenu');
  if (m.classList.contains('on') && !m.contains(e.target)) m.classList.remove('on');
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    if ($('#cfwrap') && $('#cfwrap').classList.contains('on')) { closeConfirm(); return; }
    closeDrawer(); closeMsg(); $('#rolemenu').classList.remove('on');
  }
});

/* ===================== 抽屉 ===================== */
function openDrawer(title, body, foot, w) {
  const d = $('#drawer');
  d.style.width = w || '720px';
  $('#dr-title').textContent = title;
  $('#dr-body').innerHTML = body;
  $('#dr-foot').innerHTML = foot || '';
  d.classList.add('on'); $('#mask').classList.add('on');
}
function closeDrawer() { $('#drawer').classList.remove('on'); $('#mask').classList.remove('on'); }
function closeAll() { closeDrawer(); closeMsg(); }

/* ===================== 消息中心 ===================== */
const MSGS = [
  { type: '系统通知', title: '系统将于今晚 02:00 进行例行维护', content: '维护期间平台暂停访问约 15 分钟，请提前保存工作内容。', time: '10 分钟前', read: false },
  { type: '审批结果', title: '资产领用申请已通过', content: '领用单 LC20260912-03（罗技 C920 摄像头 ×1）已由林岚审批通过。', time: '32 分钟前', read: false },
  { type: '预警推送', title: '高风险预警：账号风险分超阈值', content: '账号 ACCT-2026-0087 风险分 86，超过高风险阈值 85，请及时处理。', time: '1 小时前', read: false },
  { type: '审批结果', title: '开播登记待风控复核', content: '场次 IMS202609120DY0142 风险分 82，已进入人工复核队列。', time: '2 小时前', read: true },
  { type: '系统通知', title: '钉钉组织架构同步完成', content: '本次同步成功 128 人，待处理事件 3 条。', time: '昨天 18:20', read: true },
  { type: '预警推送', title: '证件到期提醒', content: '苏杳（身份证）剩余有效期 26 天，请及时跟进换证。', time: '昨天 09:00', read: true }
];
function openMsg() { renderMsgList(); $('#msgdrawer').classList.add('on'); $('#mask').classList.add('on'); }
function closeMsg() { $('#msgdrawer').classList.remove('on'); if (!$('#drawer').classList.contains('on')) $('#mask').classList.remove('on'); }
function renderMsgList() {
  const cmap = { '系统通知': 'gray', '审批结果': 'blue', '预警推送': 'red' };
  let h = '';
  MSGS.forEach(function (m, i) {
    h += '<div class="mg-i' + (m.read ? ' read' : '') + '" onclick="readMsg(' + i + ')">' +
      '<span class="mg-ud"></span><div style="flex:1;min-width:0"><div class="rowline" style="justify-content:space-between">' +
      '<span class="mt">' + m.title + '</span>' + tag(m.type, cmap[m.type]) + '</div>' +
      '<div class="mc">' + m.content + '</div><div class="md">' + m.time + '</div></div></div>';
  });
  $('#mglist').innerHTML = h || emptyState('暂无消息', '新消息将实时推送至此');
}
function readMsg(i) { MSGS[i].read = true; renderMsgList(); renderTopbar(); }
function markAllRead() { MSGS.forEach(function (m) { m.read = true; }); renderMsgList(); renderTopbar(); toast('已全部标记为已读', 'success'); }

/* ===================== Toast ===================== */
function toast(msg, type) {
  type = type || 'success';
  const t = document.createElement('div');
  t.className = 'toast t-' + type;
  t.innerHTML = ic(type === 'success' ? 'check' : type === 'warn' ? 'warn' : 'x', 16) + '<span>' + msg + '</span>';
  $('#toasts').appendChild(t);
  setTimeout(function () { t.classList.add('out'); setTimeout(function () { t.remove(); }, 320); }, 3000);
}

/* ===================== 通用组件 ===================== */
function emptyState(t, s) {
  return '<div class="empty"><svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">' +
    '<path d="M4 7h16v13H4zM4 7l3-4h10l3 4M12 12a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/></svg>' +
    '<div class="et">' + t + '</div><div class="es">' + (s || '当前筛选条件下暂无数据') + '</div></div>';
}
function tbl(heads, rowsHtml) {
  if (!rowsHtml) return '<div class="tbl-wrap">' + emptyState('暂无数据') + '</div>';
  return '<div class="tbl-wrap"><table><thead><tr>' + heads.map(function (h) { return '<th>' + h + '</th>'; }).join('') + '</tr></thead><tbody>' + rowsHtml + '</tbody></table></div>';
}
function qbar(controls, onQuery) {
  return '<div class="qbar">' + controls +
    '<span class="sp"></span>' +
    '<button class="btn btn-pri btn-sm" onclick="' + (onQuery || 'qresetHint()') + '">查询</button>' +
    '<button class="btn btn-sec btn-sm" onclick="resetQ(this)">重置</button></div>';
}
function resetQ(btn) {
  const bar = btn.closest('.qbar');
  bar.querySelectorAll('input').forEach(function (i) { i.value = ''; });
  bar.querySelectorAll('select').forEach(function (s) { s.selectedIndex = 0; });
  if (state.q[state.page]) { state.q[state.page] = {}; renderPage(); }
  toast('查询条件已重置', 'success');
}
function qi(ph, w, val) { return '<input placeholder="' + ph + '" style="width:' + (w || 130) + 'px"' + (val ? ' value="' + String(val).replace(/"/g, '&quot;') + '"' : '') + '>'; }
function qs(opts, w, val) { return '<select style="width:' + (w || 108) + 'px">' + opts.map(function (o) { return '<option' + (o === val ? ' selected' : '') + '>' + o + '</option>'; }).join('') + '</select>'; }
/* 按钮短暂变为「导出中…」转圈，完成后 toast + 底部下载条（3 秒淡出） */
function dlbar(name, count) {
  let d = $('#dlbar');
  if (!d) {
    d = document.createElement('div');
    d.id = 'dlbar';
    d.className = 'dlbar';
    document.body.appendChild(d);
  }
  d.innerHTML = ic('doc', 18) + '<span class="dl-t"><b>' + name + '.xlsx</b><small>' + (count != null ? count + ' 条数据' : '导出文件') + ' · 点击查看</small></span>' +
    '<span class="dl-act" onclick="event.stopPropagation();toast(\'已打开文件（原型示意）\',\'success\')">查看</span>' +
    '<span class="dl-x" onclick="event.stopPropagation();this.parentNode.remove()">' + ic('x', 14) + '</span>';
  d.classList.remove('fadeout');
  d.style.display = 'flex';
  clearTimeout(d._tm);
  d._tm = setTimeout(function () { d.classList.add('fadeout'); setTimeout(function () { if (d.parentNode) d.remove(); }, 400); }, 3000);
}
function exportX(btn, name, count) {
  if (btn) { btn.disabled = true; const raw = btn.innerHTML; btn.innerHTML = '<span class="spin"></span>导出中…'; btn._raw = raw; }
  setTimeout(function () {
    if (btn) { btn.disabled = false; btn.innerHTML = btn._raw; }
    toast('清单已导出（' + (count != null ? count + ' 条' : '') + '）', 'success');
    dlbar(name, count);
  }, 900);
}
/* 判断当前页面 qbar 是否处于初始状态（无查询条件） */
function qInit(bar) {
  let init = true;
  bar.querySelectorAll('input').forEach(function (i) { if (i.value.trim()) init = false; });
  bar.querySelectorAll('select').forEach(function (s) { if (s.selectedIndex !== 0) init = false; });
  return init;
}
/* 采集当前页面 qbar 输入 → state.q[page]，返回值列表 */
function qGrab() {
  const bar = $('#content .qbar');
  const vals = [];
  if (!bar) return { vals: vals, init: true };
  bar.querySelectorAll('input,select').forEach(function (el) { vals.push(el.value); });
  return { vals: vals, init: qInit(bar) };
}
/* 表格通用过滤：norm(row, index)->文本数组；status(row, index)->状态字符串 */
function qFilter(src, norm, status) {
  const g = qGrab();
  if (g.init) return src;
  const list = src.filter(function (r, i) {
    let ok = true;
    g.vals.forEach(function (v, j) {
      if (!ok || !v) return;
      if (/^全部|^同步状态|^档案状态|^到期状态|^分摊状态$|^穿透/.test(v)) return;
      const n = norm(r, i, j), s = status(r, i, j);
      /* 状态字段（含复合串 '抖音|冻结'）做包含匹配：下拉选值命中任一状态分量即通过 */
      if (s) {
        const parts = String(s).split('|');
        if (parts.indexOf(v) >= 0 || v === s) return;
        if (/(已|待|池|冻结|在用|闲置|维修|报废|归还|注销|结束|取消|开播|直播中|进行中|报名中|已归档|审核中|过期|补交|提交|草稿|迟交|已恢复|已忽略|未处理|处理中|结算|红|橙|黄)/.test(v)) { ok = false; return; }
      }
      const t = (n || []).join(' ').toLowerCase();
      if (t.indexOf(String(v).toLowerCase()) < 0) ok = false;
    });
    return ok;
  });
  return list;
}
function qresetHint() { toast('暂无可过滤的数据或条件', 'warn'); }

/* ===================== 确认弹窗 ConfirmDialog ===================== */
let CF_CB = null;
function confirmDlg(title, msg, okText, cb, opts) {
  opts = opts || {};
  CF_CB = cb;
  const w = document.createElement('div');
  w.id = 'cfwrap';
  w.className = 'cfwrap on';
  w.innerHTML = '<div class="cfmask" onclick="closeConfirm()"></div>' +
    '<div class="cfcard' + (opts.danger ? ' danger' : '') + '" role="dialog">' +
    '<div class="cf-t"><span class="cf-ic">' + ic(opts.danger ? 'warn' : 'check', 20) + '</span><b>' + title + '</b></div>' +
    (opts.warn ? '<div class="cf-warn">' + ic('warn', 14) + opts.warn + '</div>' : '') +
    (msg ? '<div class="cf-m">' + msg + '</div>' : '') +
    '<div class="cf-f"><button class="btn btn-sec" onclick="closeConfirm()">取消</button>' +
    '<button class="btn ' + (opts.danger ? 'btn-red' : 'btn-pri') + '" onclick="doConfirm()">' + (okText || '确认') + '</button></div></div>';
  document.body.appendChild(w);
}
function closeConfirm() { const w = $('#cfwrap'); if (w) w.remove(); CF_CB = null; }
function doConfirm() { const cb = CF_CB; closeConfirm(); if (cb) cb(); }

/* ===================== 表单抽屉子页面 ===================== */
/* fields: [{k:字段名,label,type:(text|date|num|select|dt|file|textarea|pills),req,opts,val,ph,pre,unit,disabled}] */
function frow(fields) {
  return fields.map(function (f) {
    const pid = 'F_' + f.k;
    let inner;
    if (f.type === 'select') inner = '<select id="' + pid + '">' + f.opts.map(function (o) { return '<option' + (o === f.val ? ' selected' : '') + '>' + o + '</option>'; }).join('') + '</select>';
    else if (f.type === 'textarea') inner = '<textarea id="' + pid + '" placeholder="' + (f.ph || '') + '">' + (f.val || '') + '</textarea>';
    else if (f.type === 'pills') inner = '<div class="pills">' + f.opts.map(function (o, i) { return '<label class="pill' + (o === f.val ? ' on' : '') + '"><input type="radio" name="P_' + f.k + '" value="' + o + '"' + (o === f.val ? ' checked' : '') + ' onchange="pillSel(this)"><span>' + o + '</span></label>'; }).join('') + '</div>';
    else if (f.type === 'file') inner = '<label class="fup" id="' + pid + '" onclick="toast(\'附件上传（原型占位）\',\'success\')">' + ic('plus', 15) + '<span>' + (f.ph || '点击上传照片 / 附件') + '</span></label>';
    else if (f.type === 'pre') inner = '<input id="' + pid + '" value="' + (f.val || '') + '" oninput="' + f.pre + '" placeholder="' + (f.ph || '') + '"' + (f.disabled ? ' readonly' : '') + '>';
    else inner = '<input id="' + pid + '" type="' + (f.type === 'date' ? 'date' : f.type === 'dt' ? 'datetime-local' : f.type === 'num' ? 'number' : 'text') + '" value="' + (f.val != null ? f.val : '') + '" placeholder="' + (f.ph || '') + '" style="' + (f.unit ? 'padding-right:32px' : '') + '"' + (f.disabled ? ' readonly' : '') + '>' + (f.unit ? '<span class="unit">' + f.unit + '</span>' : '');
    return '<div class="fld' + (f.wide ? ' wide' : '') + '"><label>' + f.label + (f.req ? '<i class="req">*</i>' : '') + '</label>' + inner + '<div class="ferr" id="E_' + f.k + '"></div>' + (f.hint ? '<div class="hint">' + f.hint + '</div>' : '') + '</div>';
  }).join('');
}
function pillSel(inp) {
  const wrap = inp.closest('.pills');
  wrap.querySelectorAll('.pill').forEach(function (p) { p.classList.remove('on'); });
  inp.parentNode.classList.add('on');
}
/* 校验必填 + 聚焦第一个错误 */
function formValidate(keys) {
  let first = null;
  keys.forEach(function (k) {
    const el = $('#F_' + k), err = $('#E_' + k);
    const v = el ? String(el.value || '').trim() : '';
    const isPill = el && el.type === 'radio';
    if (!el || isPill) return;
    if (!v) {
      el.classList.add('err');
      if (err) err.textContent = '必填项，请填写';
      if (!first) first = el;
    } else { el.classList.remove('err'); if (err) err.textContent = ''; }
  });
  if (first) { first.focus(); toast('请先完成必填项', 'error'); return false; }
  return true;
}
/* 成功态：大号绿对勾 + 单号 + 继续新增 / 查看结果 */
function formOk(no, extraMsg, viewFn) {
  $('#dr-title').textContent = '提交成功';
  $('#dr-body').innerHTML = '<div class="okwrap">' +
    '<svg width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="#34c759" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" stroke="#34c759" opacity=".25" stroke-width="1.6" fill="rgba(52,199,89,.08)"/><path d="M7 12.5l3.5 3.5L17 8.5"/></svg>' +
    '<b>提交成功</b>' +
    '<div class="okno"><small>单号</small><span class="mono">' + no + '</span></div>' +
    (extraMsg ? '<div class="okex">' + extraMsg + '</div>' : '') +
    '</div>';
  $('#dr-foot').innerHTML = '<button class="btn btn-sec" onclick="closeDrawer();' + (viewFn || '') + '">关闭并查看结果</button>' +
    '<button class="btn btn-pri" onclick="closeDrawer();setTimeout(function(){' + (viewFn ? viewFn + '();' : '') + 'openFormAgain();},60)">继续新增</button>';
}
/* 新行高亮 2 秒渐隐 */
function hlFirst() {
  const tr = $('#content tbody tr');
  if (tr) { tr.classList.add('rowflash'); setTimeout(function () { tr.classList.remove('rowflash'); }, 2000); }
}
function openFormAgain() { toast('请点击页头「新建」按钮再次发起（原型示意）', 'success'); }
function pgHead(id, extraBtns) {
  const m = MODS[id];
  return '<div class="pg-h"><div><h1>' + m.page + '</h1><div class="sub">' + m.desc + ' · ' + m.no + ' ' + m.code + '</div></div>' +
    '<div class="acts">' + (extraBtns || '') + '</div></div>';
}


'use strict';
/* ===================== Mock 数据 ===================== */
const TODOS = [
  { tab: '审批', icon: 'doc', title: '账号领用申请 · 罗技 C920 摄像头（赵敏申请）', from: '资产管理', time: '32 分钟前' },
  { tab: '审批', icon: 'doc', title: '费用报销单 BX20260911-02 · ¥3,260.00', from: '财务核算', time: '1 小时前' },
  { tab: '归还', icon: 'box', title: '账号归还待确认 · ACCT-2026-0071 已释放至池', from: '账号管理', time: '2 小时前' },
  { tab: '审核', icon: 'film', title: '短视频《秋季跑鞋测评》待审核（投稿：孙倩）', from: '内容生产', time: '3 小时前' },
  { tab: '审批', icon: 'video', title: '开播登记待风控复核 · 风险分 82（高）', from: '直播管理', time: '4 小时前' },
  { tab: '预警', icon: 'bell', title: '证件到期预警 · 苏杳身份证剩余 26 天', from: '证件档案', time: '昨天 09:00' },
  { tab: '告警', icon: 'warn', title: '账号风险分超阈值 · ACCT-2026-0087（86 分）', from: '预警中心', time: '1 小时前' },
  { tab: '归还', icon: 'box', title: '会议室预订冲突待处理 · 3F-大会议室 16:00', from: '会议', time: '昨天 15:40' }
];
const QUICK = [
  { icon: 'box', name: '资产登记', act: 'assetReg()' },
  { icon: 'user', name: '账号领用', act: 'acctApply()' },
  { icon: 'video', name: '开播登记', act: 'go(\'live\')' },
  { icon: 'yuan', name: '费用报销', act: 'finReimburse()' },
  { icon: 'doc', name: '填写日报', act: 'go(\'report\')' },
  { icon: 'id', name: '证件归档', act: 'go(\'cert\')' },
  { icon: 'film', name: '新建 SOP', act: 'go(\'content\')' },
  { icon: 'chart', name: '数据看板', act: 'go(\'bi\')' },
  { icon: 'cal', name: '预约会议', act: 'go(\'meet\')' },
  { icon: 'book', name: '发起培训', act: 'go(\'train\')' }
];

/* ===================== 工作台 ===================== */
PAGES.workbench = function () {
  const hour = new Date().getHours();
  const greet = hour < 6 ? '凌晨好' : hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好';
  const r = ROLES[state.role];
  const cards = [
    { l: '资产总数', n: '128', d: '环比 <span class="pos">+6</span> 件', icon: 'box', go: 'asset' },
    { l: '在用账号', n: '86', d: '池可领用 12 个', icon: 'user', go: 'acct' },
    { l: '直播场次（本周）', n: '14', d: '今日 3 场待开播', icon: 'video', go: 'live' },
    { l: '待办事项', n: '8', d: '含 1 条高危告警', icon: 'doc', go: 'workbench' }
  ].filter(function (c) { return canAccess(c.go) || c.go === 'workbench'; });
  const cur = state.tab.workbench || '全部';
  const tabs = ['全部', '审批', '归还', '审核', '预警', '告警'];
  const list = TODOS.filter(function (t) { return cur === '全部' || t.tab === cur; });

  let h = '<div style="margin:6px 0 22px"><h1 style="font-size:30px;font-weight:700;letter-spacing:-.7px;line-height:1.07">' + greet + '，' + r.user + '</h1>' +
    '<div style="font-size:13px;color:var(--text2);margin-top:6px">2026年9月12日 星期六 · 今日 3 场直播待开播，8 条待办需要处理</div></div>';
  h += '<div class="g4">';
  cards.forEach(function (c) {
    h += '<div class="card hov stat" onclick="go(\'' + c.go + '\')"><div class="rowline" style="justify-content:space-between"><span class="l">' + c.l + '</span><span style="color:var(--blue)">' + ic(c.icon, 17) + '</span></div>' +
      '<div class="n">' + c.n + '</div><div class="d">' + c.d + '</div></div>';
  });
  h += '</div><div class="g2" style="margin-top:16px">';
  /* 待办中心 */
  h += '<div class="card" style="padding-bottom:10px"><div class="hd-row"><h3>待办中心</h3><span style="font-size:12px;color:var(--text2)">' + TODOS.length + ' 条待处理</span></div><div class="tabs">';
  tabs.forEach(function (t) { h += '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'workbench\',\'' + t + '\')">' + t + '</div>'; });
  h += '</div><div>';
  if (!list.length) h += emptyState('暂无「' + cur + '」类待办', '所有相关事项已处理完毕');
  list.forEach(function (t) {
    h += '<div class="mg-i" style="border-radius:8px"><span style="color:var(--blue);margin-top:2px">' + ic(t.icon, 17) + '</span>' +
      '<div style="flex:1;min-width:0"><div class="mt">' + t.title + '</div><div class="md">' + tag(t.tab + '待办', t.tab === '告警' ? 'red' : t.tab === '预警' ? 'orange' : t.tab === '审批' ? 'blue' : 'green') + ' · ' + t.from + ' · ' + t.time + '</div></div>' +
      '<button class="btn btn-pri btn-sm" style="flex:none" onclick="todoGo(' + TODOS.indexOf(t) + ')">去处理</button></div>';
  });
  h += '</div></div>';
  /* 快捷入口 */
  const qk = QUICK.filter(function (q) { return true; }).slice(0, 10);
  h += '<div class="card"><div class="hd-row"><h3>快捷入口</h3><span style="font-size:12px;color:var(--text2)">' + state.role + ' · ' + r.name + '</span></div>' +
    '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:9px">';
  qk.forEach(function (q) {
    h += '<div class="card hov" style="padding:13px 8px;text-align:center;box-shadow:none;border:1px solid var(--line)" onclick="' + q.act + '">' +
      '<div style="color:var(--blue);margin-bottom:6px">' + ic(q.icon, 19) + '</div><div style="font-size:12px;font-weight:500">' + q.name + '</div></div>';
  });
  h += '</div><div class="dsec" style="margin-top:16px">系统公告</div><div style="font-size:12.5px;color:var(--text2);line-height:1.6">IMS V2.3 已上线「工作流催办」与「预警规则订阅」；V3 数据智能模块按角色灰度开放中。</div></div>';
  h += '</div>';
  return h;
};
/* 待办「去处理」→ 跳转对应模块 */
function todoGo(i) {
  const map = { '资产管理': 'asset', '财务核算': 'fin', '账号管理': 'acct', '内容生产': 'content', '直播管理': 'live', '证件档案': 'cert', '预警中心': 'alert', '会议': 'meet' };
  const t = TODOS[i];
  if (!t) return;
  const m = map[t.from];
  if (m && canAccess(m)) { go(m); toast('已进入「' + t.from + '」处理：' + t.title.slice(0, 18) + '…', 'success'); }
  else toast('已进入处理流程（原型示意）', 'success');
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
PAGES.auth = function () {
  const cur = state.tab.auth || '用户权限';
  let h = pgHead('auth', '<button class="btn btn-sec" onclick="exportX(this,\'权限清单\',AUTH_USERS.length)">导出清单</button>' +
    '<button class="btn btn-pri" onclick="syncDing()">' + ic('arrow', 15) + '同步钉钉组织架构</button>');
  h += '<div class="tabs">' + ['用户权限', '组织架构同步', '岗位模板'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'auth\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  if (cur === '用户权限') {
    h += qbar(qi('搜索工号 / 姓名', 150) + qs(['全部部门', '信息中心', '行政部', '财务部', '运营中心', '内容中心', '数据中心']) + qs(['全部角色', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10']) + qs(['同步状态', '已同步', '待确认']));
    let rows = '';
    AUTH_USERS.forEach(function (u, i) {
      rows += '<tr><td class="mono num">' + u.no + '</td><td style="font-weight:500">' + sens(u.name) + '</td><td>' + u.dept + '</td><td>' + u.post + '</td>' +
        '<td>' + u.roles.map(function (r) { return '<span class="chip">' + r + '</span>'; }).join('') + '</td>' +
        '<td>' + tag(u.sync, u.sync === '已同步' ? 'green' : 'orange') + '</td><td class="num" style="color:var(--text2);font-size:12px">' + u.login + '</td>' +
        '<td><span class="btn-txt btn" onclick="toast(\'查看 ' + u.name + ' 权限明细 · 原型示意\',\'success\')">查看</span></td></tr>';
    });
    h += tbl(['工号', '姓名', '部门', '岗位', '角色标签', '钉钉同步状态', '最近登录', '操作'], rows);
  } else if (cur === '组织架构同步') {
    h += '<div class="g4"><div class="card stat"><span class="l">上次同步</span><div class="n" style="font-size:18px">今天 08:00</div><div class="d">每日定时 + 手动触发</div></div>' +
      '<div class="card stat"><span class="l">成功</span><div class="n pos">128</div><div class="d">人 · 部门 12 个</div></div>' +
      '<div class="card stat"><span class="l">失败</span><div class="n neg">0</div><div class="d">无失败记录</div></div>' +
      '<div class="card stat"><span class="l">待处理事件</span><div class="n" style="color:var(--orange)">3</div><div class="d">需人工确认</div></div></div>';
    let rows = '';
    AUTH_EVENTS.forEach(function (e) {
      rows += '<tr><td style="font-weight:500">' + e.type + '</td><td>' + sens(e.person) + '</td><td>' + e.change + '</td>' +
        '<td>' + tag(e.status, e.status === '已同步' ? 'green' : 'orange') + '</td>' +
        '<td>' + (e.status === '待处理' ? '<button class="btn btn-sec btn-sm" onclick="replayEvt(this,\'' + e.person + '\')">重放</button>' : '<span style="font-size:12px;color:var(--text2)">—</span>') + '</td></tr>';
    });
    h += '<div class="sec" style="margin-top:4px">同步事件列表</div>' + tbl(['事件类型', '人员', '变更内容', '状态', '操作'], rows);
  } else {
    h += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">';
    AUTH_TMPL.forEach(function (t) {
      h += '<div class="card hov" onclick="toast(\'模板『' + t.name + '』编辑 · 原型示意\',\'success\')"><div class="rowline" style="justify-content:space-between;margin-bottom:10px">' +
        '<span style="color:var(--blue)">' + ic('shield', 20) + '</span>' +
        '<span class="sw' + (t.on ? ' on' : '') + '" onclick="event.stopPropagation();this.classList.toggle(\'on\');toast(\'模板已' + (t.on ? '停用' : '启用') + '\',\'success\')"><i></i></span></div>' +
        '<h3 style="font-size:14.5px">' + t.name + '</h3><div class="csub">适用部门：' + t.dept + '</div>' +
        '<div class="csub" style="margin-top:8px;color:var(--blue);font-weight:600">' + t.perms + ' 项权限</div></div>';
    });
    h += '</div>';
  }
  return h;
};
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
  { id: 'AS20260823010', name: '罗技 MX Keys 键盘', type: '办公设备', spec: '无线蓝牙', status: '在用', owner: '林岚', accounts: 0, buy: '2026-01-25', price: 899 }
];
PAGES.asset = function () {
  let h = pgHead('asset', '<button class="btn btn-sec" onclick="exportX(this,\'资产台账\',ASSETS.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="assetReg()">' + ic('plus', 15) + '资产登记</button>');
  const AT = ['直播设备', '拍摄设备', '数码设备', '办公设备'];
  const ct = state.tab.asset || '全部';
  h += catTabs('asset', AT, ASSETS, function (a) { return a.type; });
  const qr = state.q.asset || {};
  h += qbar(qi('资产编号', 120, qr.k0) + qi('名称', 110, qr.k1) + qs(['全部类型', '直播设备', '拍摄设备', '数码设备', '办公设备'], 108, qr.k2) + qs(['全部状态', '在用', '闲置', '维修中', '已报废'], 108, qr.k3) + qi('责任人', 90, qr.k4) + '<input type="date" style="width:130px">' + '<span style="color:var(--text2);font-size:12px">至</span>' + '<input type="date" style="width:130px">', 'qSave(\'asset\')');
  const list = qFilter(ASSETS.filter(function (a) { return ct === '全部' || a.type === ct; }), function (a) { return [a.id, a.name, a.spec, a.owner]; }, function (a) { return a.type + '|' + a.status; });
  let rows = '';
  list.forEach(function (a) {
    const i = ASSETS.indexOf(a);
    const stc = { '在用': 'green', '闲置': 'blue', '维修中': 'orange', '已报废': 'gray' }[a.status];
    rows += '<tr><td class="mono num" style="color:var(--blue);cursor:pointer" onclick="assetDetail(' + i + ')">' + a.id + '</td><td style="font-weight:500">' + a.name + '</td><td>' + a.type + '</td><td style="color:var(--text2)">' + a.spec + '</td>' +
      '<td>' + tag(a.status, stc) + '</td><td>' + sens(a.owner) + '</td><td class="num">' + a.accounts + '</td><td class="num">' + a.buy + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="assetDetail(' + i + ')">查看</span></td></tr>';
  });
  h += tbl(['资产编号', '名称', '类型', '规格', '状态', '责任人', '绑定账号数', '采购日期', '操作'], rows);
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
    state.q[page] = { k0: vals[0] || '', k1: vals[1] || '', k2: vals[2] || '', k3: vals[3] || '', k4: vals[4] || '' };
  }
  renderPage();
  toast('查询完成 · 共 ' + $('#content tbody tr').length + ' 条结果', 'success');
}
/* ASSET：资产登记表单抽屉 */
function assetReg() {
  const body = frow([
    { k: 'name', label: '资产名称', type: 'text', req: true, ph: '如：罗技 C920 Pro 摄像头' },
    { k: 'type', label: '资产类型', type: 'select', req: true, opts: ['直播设备', '拍摄设备', '数码设备', '办公设备'] },
    { k: 'spec', label: '规格型号', type: 'text', ph: '如：1080P/30fps' },
    { k: 'sn', label: '序列号', type: 'text', ph: '机身 SN 码（选填）' },
    { k: 'buy', label: '采购日期', type: 'date', req: true, val: '2026-09-12' },
    { k: 'price', label: '采购金额', type: 'num', unit: '¥', ph: '0.00' },
    { k: 'owner', label: '责任人', type: 'select', req: true, opts: ['赵敏', '孙倩', '何舟', '林岚', '李澈', '陈默'] },
    { k: 'photo', label: '资产照片', type: 'file', ph: '点击上传资产照片', wide: true },
    { k: 'note', label: '备注', type: 'textarea', ph: '验收情况、随附配件等', wide: true }
  ]);
  openDrawer('资产登记', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="assetRegSubmit()">提交登记</button>', '480px');
}
function assetRegSubmit() {
  if (!formValidate(['name', 'type', 'buy', 'owner'])) return;
  const no = 'AS' + '20260912' + String(ASSETS.length + 1).padStart(3, '0');
  ASSETS.unshift({ id: no, name: $('#F_name').value.trim(), type: $('#F_type').value, spec: $('#F_spec').value.trim() || '—', status: '在用', owner: $('#F_owner').value, accounts: 0, buy: $('#F_buy').value || '2026-09-12', price: Number($('#F_price').value || 0) });
  if (state.page === 'asset') renderPage();
  formOk(no, '资产已登记入台账，可发起领用流转', '');
  toast('资产登记成功：' + no, 'success');
}
function assetDetail(i) {
  const a = ASSETS[i];
  const flow = [
    { t: '采购入库', d: a.buy + ' · 采购价 ' + fmtMoney(a.price), c: '' },
    { t: '领用出库', d: a.buy.replace(/-/, '/').replace(/-/, '/') + ' · 赵敏 发起领用', c: '' },
    { t: '绑定直播账号', d: 'ACCT-2026-0003（斗鱼 · 主号）', c: 'gg' },
    { t: '最近盘点', d: '2026-08-31 · 盘点人：林岚 · 结果：正常', c: 'gg' }
  ];
  const body = '<div class="photo">' + ic('box', 40) + '</div>' +
    '<div class="dsec">基本信息</div><div class="kv">' +
    '<div><div class="k">资产编号</div><div class="v mono">' + a.id + '</div></div><div><div class="k">名称</div><div class="v">' + a.name + '</div></div>' +
    '<div><div class="k">类型 / 规格</div><div class="v">' + a.type + ' · ' + a.spec + '</div></div><div><div class="k">当前状态</div><div class="v">' + tag(a.status, { '在用': 'green', '闲置': 'blue', '维修中': 'orange', '已报废': 'gray' }[a.status]) + '</div></div>' +
    '<div><div class="k">责任人</div><div class="v">' + sens(a.owner) + '</div></div><div><div class="k">采购信息</div><div class="v">' + a.buy + ' · ' + fmtMoney(a.price) + '</div></div></div>' +
    '<div class="dsec">绑定账号（' + a.accounts + '）· 正向穿透</div>' +
    (a.accounts ? '<div class="tbl-wrap"><table><thead><tr><th>账号编号</th><th>平台</th><th>昵称</th><th>操作</th></tr></thead><tbody>' +
      '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="assetToAcct(\'ACCT-2026-0003\')">ACCT-2026-0003</td><td>斗鱼</td><td>神鱼电竞直播间</td><td><span class="btn btn-sec btn-sm" onclick="assetToAcct(\'ACCT-2026-0003\')">穿透</span></td></tr>' +
      (a.accounts > 1 ? '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="assetToAcct(\'ACCT-2026-0021\')">ACCT-2026-0021</td><td>小红书</td><td>神鱼穿搭日记</td><td><span class="btn btn-sec btn-sm" onclick="assetToAcct(\'ACCT-2026-0021\')">穿透</span></td></tr>' : '') +
      '</tbody></table></div>' : emptyState('暂无绑定账号', '该资产未绑定任何平台账号')) +
    '<div class="dsec">领用流转时间线</div><div class="tl">' +
    flow.map(function (f) { return '<div class="tl-i ' + f.c + '"><div class="tt">' + f.t + '</div><div class="td">' + f.d + '</div></div>'; }).join('') + '</div>';
  openDrawer('资产详情 · ' + a.id, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="assetFlow(' + i + ')">发起流转</button>');
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
  { id: 'ACCT-2026-0001', plat: '抖音', nick: '神鱼体育', owner: '赵敏', st: '在用', frozen: false, last: '2026-09-08', recharge: 126800.00 },
  { id: 'ACCT-2026-0002', plat: '视频号', nick: '神鱼跑步研究所', owner: '孙倩', st: '在用', frozen: false, last: '2026-09-10', recharge: 36200.00 },
  { id: 'ACCT-2026-0003', plat: '斗鱼', nick: '神鱼电竞直播间', owner: '赵敏', st: '在用', frozen: false, last: '2026-09-11', recharge: 88400.00 },
  { id: 'ACCT-2026-0008', plat: '抖音', nick: '神鱼好物优选', owner: '李澈', st: '冻结', frozen: true, last: '2026-08-02', recharge: 21900.00 },
  { id: 'ACCT-2026-0012', plat: 'B 站', nick: '神鱼健身教室', owner: '—', st: '池可领用', frozen: false, last: '2026-08-30', recharge: 5600.00 },
  { id: 'ACCT-2026-0021', plat: '小红书', nick: '神鱼穿搭日记', owner: '—', st: '池可领用', frozen: false, last: '2026-09-01', recharge: 4200.00 },
  { id: 'ACCT-2026-0034', plat: '快手', nick: '神鱼运动精选', owner: '苏杳', st: '在用', frozen: false, last: '2026-09-12', recharge: 15300.00 },
  { id: 'ACCT-2026-0041', plat: '抖音', nick: '神鱼训练营（旧）', owner: '—', st: '已归还', frozen: false, last: '2026-07-15', recharge: 3100.00 },
  { id: 'ACCT-2026-0056', plat: '微博', nick: '神鱼体育官方号', owner: '—', st: '已注销', frozen: true, last: '2026-03-20', recharge: 0 },
  { id: 'ACCT-2026-0087', plat: '抖音', nick: '神鱼夜跑频道', owner: '王野', st: '冻结', frozen: true, last: '2026-09-05', recharge: 9800.00 }
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
    rows += '<tr><td class="mono num" style="color:var(--blue);cursor:pointer" onclick="acctDetail(' + i + ')">' + a.id + '</td><td>' + a.plat + '</td><td style="font-weight:500">' + a.nick + '</td>' +
      '<td>' + sens(a.owner) + '</td><td>' + tag(a.st, stc[a.st]) + (a.frozen ? ' <span style="color:var(--red)" title="已冻结">' + ic('shield', 13) + '</span>' : '') + '</td>' +
    '<td class="num" style="font-size:12px;color:var(--text2)">' + a.last + '</td><td class="num" style="font-weight:500">' + fmtMoney(a.recharge) + '</td>' +
    '<td>' + (a.st === '已注销' ? '<span style="font-size:12px;color:var(--text2)">—</span>' :
      '<button class="btn btn-sm" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="acctCharge(' + i + ')">冲话费</button>') + '</td>' +
    '<td><span class="btn btn-sec btn-sm" onclick="acctDetail(' + i + ')">查看</span></td></tr>';
  });
  h += tbl(['账号编号', '平台', '昵称', '当前责任人', '状态', '最近领用时间', '累计充值', '冲话费', '操作'], rows);
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
function acctDetail(i) {
  const a = ACCTS[i];
  const tl = [
    { t: '账号入库（池）', d: '2026-01-08 · 行政部创建账号档案', c: '' },
    { t: '领用：赵敏', d: '2026-03-02 · 领用单 LY20260302-01', c: '' },
    { t: '充值 +¥50,000.00', d: '2026-05-18 · 财务确认（BR-017 核对一致）', c: 'gg' },
    { t: '归还入池', d: '2026-08-02 · 赵敏发起归还', c: 'oo' },
    { t: '风控冻结', d: '2026-09-05 · 风险分超阈值', c: 'oo' }
  ];
  const chargeTl = (a.charges || []).map(function (c) {
    return { t: '冲话费 +' + fmtMoney(c.amt), d: c.d + ' · 凭证 ' + c.vou + ' · ' + c.way + '（BR-017 核对一致）', c: 'gg' };
  });
  if (a.id === 'ACCT-2026-0001') tl.splice(3, 0, { t: '冲话费 +¥26,800.00', d: '2026-08-15 · 凭证 CZ20260815-03 · 公司对公（BR-017 核对一致）', c: 'gg' });
  const body = '<div class="tabs" style="margin-top:0"><div class="tab on">基本信息</div><div class="tab" onclick="toast(\'领用时间线 Tab · 原型示意\',\'success\')">领用时间线</div><div class="tab" onclick="toast(\'关联资产 Tab · 原型示意\',\'success\')">关联资产</div></div>' +
    '<div class="kv">' +
    '<div><div class="k">账号编号</div><div class="v mono">' + a.id + '</div></div><div><div class="k">平台 / 昵称</div><div class="v">' + a.plat + ' · ' + a.nick + '</div></div>' +
    '<div><div class="k">当前责任人</div><div class="v">' + sens(a.owner) + '</div></div><div><div class="k">状态</div><div class="v">' + tag(a.st, { '在用': 'green', '池可领用': 'blue', '冻结': 'orange', '已归还': 'cyan', '已注销': 'gray' }[a.st]) + '</div></div>' +
    '<div><div class="k">绑定手机</div><div class="v">' + sens(maskPhone('13828715678')) + '</div></div><div><div class="k">累计充值（含冲话费）</div><div class="v">' + fmtMoney(a.recharge) + '</div></div></div>' +
    '<div class="dsec">领用 / 充值时间线</div><div class="tl">' + chargeTl.concat(tl).map(function (f) { return '<div class="tl-i ' + f.c + '"><div class="tt">' + f.t + '</div><div class="td">' + f.d + '</div></div>'; }).join('') + '</div>' +
    '<div class="dsec">关联资产（2）· 反向穿透（ASSET-002）</div><div class="tbl-wrap"><table><thead><tr><th>资产编号</th><th>名称</th><th>状态</th><th>操作</th></tr></thead><tbody>' +
    '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="acctToAsset(\'AS20260901001\')">AS20260901001</td><td>罗技 C920 Pro 摄像头</td><td>' + tag('在用', 'green') + '</td><td><span class="btn btn-sec btn-sm" onclick="acctToAsset(\'AS20260901001\')">穿透</span></td></tr>' +
    '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="acctToAsset(\'AS20260830003\')">AS20260830003</td><td>神牛 SL60W 补光灯</td><td>' + tag('在用', 'green') + '</td><td><span class="btn btn-sec btn-sm" onclick="acctToAsset(\'AS20260830003\')">穿透</span></td></tr></tbody></table></div>';
  openDrawer('账号详情 · ' + a.id, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (a.st !== '已注销' ? '<button class="btn" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="acctCharge(' + i + ')">冲话费</button>' : '') +
    (a.st === '池可领用' ? '<button class="btn btn-pri" onclick="acctApply()">申请领用</button>' :
      a.frozen ? '<button class="btn btn-pri" style="background:var(--orange)" onclick="acctUnfreeze(' + i + ')">申请解冻</button>' :
        '<button class="btn btn-pri" onclick="acctReturn(' + i + ')">发起归还</button>'));
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
/* ACCT-004：冲话费管理表单（含 BR-017 账实核对） */
function acctCharge(i) {
  const a = ACCTS[i];
  if (!a) return;
  const body = frow([
    { k: 'camt', label: '冲话费金额', type: 'num', req: true, unit: '¥', ph: '0.00', pre: 'acctChargeCalc()' },
    { k: 'cway', label: '充值渠道', type: 'pills', opts: ['公司对公', '个人垫付报销', '平台赠送'], val: '公司对公' },
    { k: 'creal', label: '平台实际到账', type: 'num', req: true, unit: '¥', ph: '0.00', pre: 'acctChargeCalc()' },
    { k: 'cvou', label: '凭证编号', type: 'text', req: true, ph: '如：CZ20260918-001' },
    { k: 'cproof', label: '充值凭证截图', type: 'file', ph: '点击上传平台后台截图', wide: true },
    { k: 'cnote', label: '备注', type: 'textarea', ph: '活动补贴、赠送口径说明（选填）', wide: true }
  ]) + '<div class="dsec">账实核对（BR-017 · 实时校验）</div>' +
    '<div class="kv" id="ccChk" style="background:var(--bg);border-radius:10px;padding:12px 14px">' +
    '<div><div class="k">申请金额</div><div class="v num" id="ccA">—</div></div>' +
    '<div><div class="k">平台到账</div><div class="v num" id="ccR">—</div></div>' +
    '<div><div class="k">核对结果</div><div class="v" id="ccD">待输入</div></div></div>';
  openDrawer('冲话费 · ' + a.id + '（' + a.nick + '）', body,
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
/* ACCT-004：提交闭环（差异拦截 + 充值入账 + 时间线留痕） */
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
  confirmDlg('确认提交冲话费？', '账号 ' + a.id + '（' + a.nick + '）冲话费 ' + fmtMoney(amt) + '，核对一致后将累计入充值台账并写入时间线。', '提交冲话费', function () {
    a.recharge += amt;
    if (!a.charges) a.charges = [];
    a.charges.unshift({ amt: amt, vou: $('#F_cvou').value.trim(), d: '2026-09-18', way: '公司对公' });
    if (state.page === 'acct') renderPage();
    closeDrawer();
    toast('冲话费已入账：' + a.id + ' · ' + fmtMoney(amt) + '（累计 ' + fmtMoney(a.recharge) + ' · 已写入时间线）', 'success');
    hlFirst();
  });
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

/* ===================== 10 LIVE 直播管理 ===================== */
const LIVES = [
  { id: 'IMS202609120DY0142', acct: 'ACCT-2026-0001', rname: '苏杳', owner: '赵敏', topic: '秋季新品跑鞋首发专场', plat: '抖音', start: '2026-09-12 19:30', risk: 82, rl: '高', st: '待开播' },
  { id: 'IMS202609120DY0141', acct: 'ACCT-2026-0003', rname: '苏杳', owner: '赵敏', topic: '晚间健身操跟练', plat: '斗鱼', start: '2026-09-12 20:00', risk: 34, rl: '低', st: '待开播' },
  { id: 'IMS202609110DY0138', acct: 'ACCT-2026-0002', rname: '李澈', owner: '孙倩', topic: '跑步装备开箱测评', plat: '视频号', start: '2026-09-11 15:00', risk: 46, rl: '中', st: '直播中' },
  { id: 'IMS202609110DY0136', acct: 'ACCT-2026-0034', rname: '苏杳', owner: '何舟', topic: '夜跑安全知识分享', plat: '快手', start: '2026-09-11 19:00', risk: 28, rl: '低', st: '已结束', gmv: 61200, orders: 86, views: 12800, peak: 3842, fans: 156, entered: true },
  { id: 'IMS202609100DY0131', acct: 'ACCT-2026-0001', rname: '赵敏', rerr: true, owner: '赵敏', topic: '大促预热：健身品类专场', plat: '抖音', start: '2026-09-10 20:00', risk: 61, rl: '中', st: '已结束', gmv: 412800, orders: 530, views: 42600, peak: 15800, fans: 1240, entered: true },
  { id: 'IMS202609090DY0127', acct: 'ACCT-2026-0003', rname: '苏杳', owner: '赵敏', topic: '周末电竞水友赛', plat: '斗鱼', start: '2026-09-09 14:00', risk: 39, rl: '低', st: '已结束', gmv: 96700, orders: 218, views: 31200, peak: 9210, fans: 420, entered: true },
  { id: 'IMS202609090DY0125', acct: 'ACCT-2026-0087', rname: '王野', owner: '何舟', topic: '运动营养科普', plat: '抖音', start: '2026-09-09 18:30', risk: 86, rl: '高', st: '已取消' },
  { id: 'IMS202609080DY0121', acct: 'ACCT-2026-0002', rname: '孙倩', owner: '孙倩', topic: '晨间瑜伽唤醒', plat: '视频号', start: '2026-09-08 07:30', risk: 22, rl: '低', st: '已结束', gmv: 0, orders: 0, views: 8600, peak: 2100, fans: 86, entered: true },
  { id: 'IMS202609070DY0118', acct: 'ACCT-2026-0034', rname: '苏杳', owner: '苏杳', topic: '达人连麦：训练日常', plat: '快手', start: '2026-09-07 21:00', risk: 53, rl: '中', st: '已结束' }
];
PAGES.live = function () {
  const cur = state.tab.live || '开播风控登记';
  let h = pgHead('live', cur === '开播风控登记' ? '<button class="btn btn-pri" onclick="liveReg()">' + ic('plus', 15) + '开播登记</button>' :
    '<button class="btn btn-sec" onclick="exportX(this,\'场次台账\',LIVES.length)">导出</button>');
  h += '<div class="tabs">' + ['开播风控登记', '场次台账'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'live\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  if (cur === '开播风控登记') {
    h += '<div class="g4"><div class="card stat"><span class="l">今日待开播</span><div class="n" style="color:var(--blue)">3</div><div class="d">最早 19:30 开播</div></div>' +
      '<div class="card stat"><span class="l">高风险场次（近 7 天）</span><div class="n neg">2</div><div class="d">均已人工复核</div></div>' +
      '<div class="card stat"><span class="l">风控拦截（本月）</span><div class="n" style="color:var(--orange)">5</div><div class="d">命中实名人异常规则</div></div>' +
      '<div class="card stat"><span class="l">平均风险分</span><div class="n">41</div><div class="d">环比 <span class="pos">-3</span></div></div></div>';
    h += '<div class="sec">今日待开播场次</div>';
    let rows = '';
    LIVES.filter(function (l) { return l.st === '待开播' || l.st === '直播中'; }).forEach(function (l) {
      rows += liveRow(l);
    });
    h += tbl(['场次ID', '直播账号', '实名人', '责任人', '主题', '平台', '计划开播', '风险分', '风险级别', '场次状态', '操作'], rows);
  } else {
    const ended = LIVES.filter(function (l) { return l.st === '已结束'; });
    const enteredN = ended.filter(function (l) { return l.entered; }).length;
    const rate = ended.length ? Math.round(enteredN / ended.length * 100) : 100;
    h += '<div class="g4"><div class="card stat"><span class="l">下播录入完整率（BR-007）</span><div class="n" style="color:' + (rate >= 90 ? 'var(--green)' : rate >= 70 ? 'var(--orange)' : 'var(--red)') + '">' + rate + '%</div><div class="d">已结束 ' + ended.length + ' 场 · 已录入 ' + enteredN + ' 场</div></div>' +
      '<div class="card stat"><span class="l">本月场次 GMV</span><div class="n">' + fmtMoney(ended.reduce(function (s, l) { return s + (l.gmv || 0); }, 0)) + '</div><div class="d">已录入场次合计</div></div>' +
      '<div class="card stat"><span class="l">待录入场次</span><div class="n" style="color:var(--orange)">' + (ended.length - enteredN) + '</div><div class="d">超过 48h 未录入将预警</div></div>' +
      '<div class="card stat"><span class="l">最高单场 GMV</span><div class="n">' + fmtMoney(Math.max.apply(null, ended.map(function (l) { return l.gmv || 0; }))) + '</div><div class="d">大促预热 · 抖音</div></div></div>';
    h += qbar(qi('场次 ID', 160, (state.q.live || {}).k0) + qs(['全部平台', '抖音', '斗鱼', '视频号', '快手'], 90, (state.q.live || {}).k1) + qs(['全部状态', '待开播', '直播中', '已结束', '已取消'], 100, (state.q.live || {}).k2) + '<input type="date" style="width:130px">', 'qSave(\'live\')');
    const list = qFilter(LIVES, function (l) { return [l.id, l.topic, l.rname, l.owner]; }, function (l) { return l.plat + '|' + l.st; });
    let rows = '';
    list.forEach(function (l) { rows += liveRow(l); });
    h += tbl(['场次ID', '直播账号', '实名人', '责任人', '主题', '平台', '计划开播', '风险分', '风险级别', '场次状态', '操作'], rows);
  }
  return h;
};
function liveRow(l) {
  const rlc = { '低': 'green', '中': 'orange', '高': 'red' }[l.rl];
  const rc = l.risk >= 80 ? 'var(--red)' : l.risk >= 60 ? 'var(--orange)' : l.risk >= 40 ? 'var(--yellow)' : 'var(--green)';
  const stc = { '待开播': 'blue', '直播中': 'green', '已结束': 'gray', '已取消': 'gray', '待复核': 'orange' }[l.st];
  const needEntry = l.st === '已结束' && !l.entered;
  return '<tr><td class="mono num" style="color:var(--blue);cursor:pointer" onclick="liveSessionDetail(\'' + l.id + '\')">' + l.id + '</td>' +
    '<td class="mono" style="font-size:12px">' + l.acct + '</td><td style="font-weight:500' + (l.rerr ? ';color:var(--red)' : '') + '">' + sens(l.rname) + (l.rerr ? ' ⚠' : '') + '</td><td>' + sens(l.owner) + '</td>' +
    '<td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">' + l.topic + '</td><td>' + l.plat + '</td><td class="num" style="font-size:12px">' + l.start + '</td>' +
    '<td><div class="rowline"><span class="pg" style="width:44px"><i style="width:' + l.risk + '%;background:' + rc + '"></i></span><span class="num" style="font-size:12px;font-weight:600">' + l.risk + '</span></div></td>' +
    '<td>' + tag(l.rl + '风险', rlc) + '</td><td>' + tag(l.st, stc) + (l.entered ? ' <span class="chip" style="font-size:10.5px;color:var(--green);border-color:var(--green)">已录入</span>' : '') + '</td>' +
    '<td>' + (needEntry ? '<button class="btn btn-sm" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="liveEndEntry(\'' + l.id + '\')">下播录入</button>' :
      '<span class="btn btn-sec btn-sm" onclick="liveSessionOp(\'' + l.id + '\')">操作</span>') + '</td></tr>';
}
/* LIVE：场次详情抽屉 */
function liveSessionDetail(id) {
  const l = LIVES.filter(function (x) { return x.id === id; })[0];
  if (!l) { toast('未找到场次：' + id, 'error'); return; }
  const body = '<div class="kv">' +
    '<div><div class="k">场次 ID</div><div class="v mono">' + l.id + '</div></div><div><div class="k">直播账号</div><div class="v mono">' + l.acct + '</div></div>' +
    '<div><div class="k">实名人</div><div class="v">' + sens(l.rname) + '</div></div><div><div class="k">责任人</div><div class="v">' + sens(l.owner) + '</div></div>' +
    '<div><div class="k">主题</div><div class="v">' + l.topic + '</div></div><div><div class="k">平台 / 开播</div><div class="v">' + l.plat + ' · ' + l.start + '</div></div>' +
    '<div><div class="k">风险分</div><div class="v">' + l.risk + '（' + l.rl + '风险）</div></div><div><div class="k">场次状态</div><div class="v">' + l.st + '</div></div></div>' +
    '<div class="dsec">风控命中时间线</div><div class="tl">' +
    '<div class="tl-i"><div class="tt">开播登记提交</div><div class="td">责任人 ' + l.owner + ' 提交开播申请</div></div>' +
    '<div class="tl-i ' + (l.risk >= 60 ? 'oo' : 'gg') + '"><div class="tt">风控引擎评估</div><div class="td">风险分 ' + l.risk + ' / 100 · ' + (l.risk >= 60 ? '触发人工复核条件' : '自动通过') + '</div></div>' +
    '<div class="tl-i ' + (l.risk >= 60 ? 'oo' : 'gg') + '"><div class="tt">' + (l.risk >= 60 ? '等待人工复核' : '确认开播') + '</div><div class="td">' + (l.risk >= 60 ? '已进入复核队列（原型示意）' : '场次已排期') + '</div></div></div>' +
    (l.entered ? '<div class="dsec">下播数据（已录入 · BR-006 留痕）</div><div class="kv">' +
      '<div><div class="k">本场 GMV</div><div class="v num" style="font-weight:600">' + fmtMoney(l.gmv || 0) + '</div></div>' +
      '<div><div class="k">成交订单</div><div class="v num">' + (l.orders || 0) + ' 单</div></div>' +
      '<div><div class="k">累计观看</div><div class="v num">' + (l.views || 0).toLocaleString() + '</div></div>' +
      '<div><div class="k">峰值在线</div><div class="v num">' + (l.peak || 0).toLocaleString() + '</div></div>' +
      '<div><div class="k">新增粉丝</div><div class="v num">+' + (l.fans || 0) + '</div></div></div>' : '');
  openDrawer('场次详情 · ' + l.id, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (l.risk >= 60 ? '<button class="btn btn-pri" style="background:var(--orange)" onclick="liveToReview(\'' + l.id + '\')">转人工复核</button>' : ''));
}
function liveSessionOp(id) {
  liveSessionDetail(id);
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
  const body = '<div class="formrow"><div class="fld"><label>直播账号</label><select><option>ACCT-2026-0001 · 抖音 · 神鱼体育</option><option>ACCT-2026-0003 · 斗鱼 · 神鱼电竞直播间</option><option>ACCT-2026-0002 · 视频号 · 神鱼跑步研究所</option></select></div>' +
    '<div class="fld"><label>实名人</label><select><option>苏杳（证件已核验 ✓）</option><option>李澈（证件已核验 ✓）</option><option>王野（证件待核验 ⚠）</option></select></div></div>' +
    '<div class="formrow"><div class="fld"><label>责任人</label><input value="赵敏" readonly></div>' +
    '<div class="fld"><label>直播平台</label><select><option>抖音</option><option>斗鱼</option><option>视频号</option><option>快手</option></select></div></div>' +
    '<div class="formrow one"><div class="fld"><label>直播主题</label><input placeholder="如：秋季新品跑鞋首发专场"></div></div>' +
    '<div class="formrow"><div class="fld"><label>计划开播时间</label><input type="datetime-local" value="2026-09-12T19:30"></div>' +
    '<div class="fld"><label>预计时长（小时）</label><input type="number" value="3" min="0.5" step="0.5"></div></div>' +
    '<div class="hint">提交后将自动执行开播风控规则引擎（账号状态 / 实名人核验 / 历史行为 / 内容合规 4 类 17 条规则）</div>';
  openDrawer('开播风控登记', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="liveRiskResult()">提交并执行风控</button>');
}
function liveRiskResult() {
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
/* LIVE-002：下播数据录入表单（场次台账 → 已结束未录入场次） */
function liveEndEntry(id) {
  const l = LIVES.filter(function (x) { return x.id === id; })[0];
  if (!l) { toast('未找到场次：' + id, 'error'); return; }
  const body = frow([
    { k: 'lgmv', label: '本场 GMV', type: 'num', req: true, unit: '¥', ph: '0.00', pre: 'liveEntryCalc()' },
    { k: 'lord', label: '成交订单数', type: 'num', unit: '单', ph: '0' },
    { k: 'lview', label: '累计观看人数', type: 'num', req: true, unit: '人', ph: '0', pre: 'liveEntryCalc()' },
    { k: 'lpeak', label: '峰值在线', type: 'num', unit: '人', ph: '0' },
    { k: 'lreal', label: '实际时长（分钟）', type: 'num', req: true, unit: 'min', ph: '0' },
    { k: 'lfans', label: '新增粉丝', type: 'num', unit: '人', ph: '0' },
    { k: 'lpay', label: '打赏/礼物收益', type: 'num', unit: '¥', ph: '0.00' },
    { k: 'lsrcc', label: '数据来源', type: 'pills', opts: ['平台后台截图', '场控记录', '投流投放报表'], val: '平台后台截图' },
    { k: 'lnote', label: '备注', type: 'textarea', ph: '特殊口径说明、退单核销等（选填）', wide: true }
  ]) + '<div class="dsec">录入汇总（实时）</div>' +
    '<div class="kv" style="background:var(--bg);border-radius:10px;padding:12px 14px">' +
    '<div><div class="k">场均客单价</div><div class="v num" id="leA">—</div></div>' +
    '<div><div class="k">千次观看成交（GPM）</div><div class="v num" id="leG">—</div></div>' +
    '<div><div class="k">互动峰值/累计</div><div class="v num" id="leP">—</div></div></div>' +
    '<div class="hint" style="margin-top:8px">提交后写入场次台账（BR-006 留痕），并推送财务核算与数据分析模块。</div>';
  openDrawer('下播数据录入 · ' + l.id, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="liveEndEntrySubmit(\'' + l.id + '\')">提交录入</button>', '560px');
  state.qz = { entryId: l.id };
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
    closeDrawer();
    toast('下播数据已录入：' + l.id + ' · GMV ' + fmtMoney(gmv) + '（已同步财务/数据模块）', 'success');
    hlFirst();
  });
}

/* ===================== 15 CONTENT 内容生产 ===================== */
const SOPS = [
  { name: '跑鞋测评短视频 SOP', plat: '抖音 / 视频号', nodes: 8, ver: 'v2.3', on: true, g: 'linear-gradient(135deg,#ff9500,#ff3b30)' },
  { name: '健身跟练直播预热 SOP', plat: '抖音', nodes: 6, ver: 'v1.8', on: true, g: 'linear-gradient(135deg,#0071e3,#5ac8fa)' },
  { name: '好物种草图文 SOP', plat: '小红书', nodes: 10, ver: 'v3.1', on: true, g: 'linear-gradient(135deg,#af52da,#ff3b30)' },
  { name: '电竞赛事集锦 SOP', plat: 'B 站 / 斗鱼', nodes: 7, ver: 'v1.2', on: false, g: 'linear-gradient(135deg,#34c759,#5ac8fa)' },
  { name: '跑步知识科普 SOP', plat: '视频号', nodes: 5, ver: 'v2.0', on: true, g: 'linear-gradient(135deg,#5ac8fa,#0071e3)' },
  { name: '夜跑安全专题 SOP', plat: '快手', nodes: 6, ver: 'v1.5', on: true, g: 'linear-gradient(135deg,#1d1d1f,#8e8e93)' },
  { name: '新品首发大促 SOP', plat: '全平台', nodes: 12, ver: 'v4.0', on: true, g: 'linear-gradient(135deg,#ffcc00,#ff9500)' },
  { name: '达人连麦脚本 SOP', plat: '抖音 / 快手', nodes: 9, ver: 'v1.1', on: false, g: 'linear-gradient(135deg,#0071e3,#af52da)' }
];
PAGES.content = function () {
  const cur = state.tab.content || 'SOP 模板';
  const CT = ['SOP 模板', '选题计划', 'AI 脚本', 'AI 生产链', '在线审核', '发布归档'];
  let h = pgHead('content',
    cur === 'SOP 模板' ? '<button class="btn btn-sec" onclick="toast(\'导入 SOP 模板 · 原型示意\',\'success\')">导入模板</button><button class="btn btn-pri" onclick="sopEdit()">' + ic('plus', 15) + '新建 SOP</button>' :
    cur === '选题计划' ? '<button class="btn btn-pri" onclick="topicAdd()">' + ic('plus', 15) + '提报选题</button>' :
    cur === 'AI 脚本' ? '<button class="btn btn-sec" onclick="exportX(this,\'脚本清单\',SCRIPTS.length)">导出</button><button class="btn btn-pri" style="background:var(--purple)" onclick="scriptGen()">' + ic('spark', 15) + 'AI 生成脚本</button>' :
    cur === 'AI 生产链' ? '<button class="btn btn-sec" onclick="exportX(this,\'生产任务\',AITASKS.length)">导出</button><button class="btn btn-pri" style="background:var(--purple)" onclick="aiTaskCreate()">' + ic('spark', 15) + '创建生产任务</button>' :
    cur === '在线审核' ? '<span class="csub">审核 SLA 12h · 一次通过率 74%（目标 70%+）</span>' :
    '<button class="btn btn-pri" onclick="pubAdd()">' + ic('plus', 15) + '创建发布单</button>');
  h += '<div class="tabs">' + CT.map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'content\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  if (cur === 'SOP 模板') h += contentSopTab();
  else if (cur === '选题计划') h += contentTopicTab();
  else if (cur === 'AI 脚本') h += contentScriptTab();
  else if (cur === 'AI 生产链') h += contentAiTab();
  else if (cur === '在线审核') h += contentReviewTab();
  else h += contentPublishTab();
  return h;
};
/* ---- CONTENT Tab1：SOP 模板管理（原卡片网格） ---- */
function contentSopTab() {
  let h = '';
  SOPS.forEach(function (s, i) {
    h += '<div class="card hov" style="padding:0;overflow:hidden" onclick="sopEdit()">' +
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
  let h = '<div class="g4"><div class="card stat"><span class="l">一次通过率</span><div class="n" style="color:var(--green)">74%</div><div class="d">目标 > 70% · 已达标</div></div>' +
    '<div class="card stat"><span class="l">待审队列</span><div class="n" style="color:var(--blue)">2</div><div class="d">最早排期 09-19</div></div>' +
    '<div class="card stat"><span class="l">平均审核时长</span><div class="n">4.2h</div><div class="d">SLA 12h 内</div></div>' +
    '<div class="card stat"><span class="l">超时率</span><div class="n neg">1</div><div class="d">已超 12h · 待督办</div></div></div>';
  const clc = { '未审': 'blue', '通过': 'green', '打回': 'yellow', '驳回': 'red' };
  let rows = '';
  REVIEWS.forEach(function (r, i) {
    rows += '<tr><td class="mono num">' + r.no + '</td><td style="font-weight:500">' + r.proj + '</td><td>' + r.by + '</td>' +
      '<td class="num"><span style="' + (r.round >= 3 ? 'color:var(--purple);font-weight:600' : '') + '">' + r.round + '</span></td>' +
      '<td class="num">' + r.plan + '</td>' +
      '<td>' + (r.overdue ? '<span style="color:var(--red);font-weight:600">超 12h</span>' : '<span style="color:var(--text2)">—</span>') + '</td>' +
      '<td>' + tag(r.cl, clc[r.cl]) + '</td>' +
      '<td>' + (r.cl === '未审' ? '<button class="btn btn-pri btn-sm" onclick="reviewDo(' + i + ')">审核</button>' :
        '<span class="btn btn-sec btn-sm" onclick="toast(\'审核详情 · 原型示意\',\'success\')">详情</span>') + '</td></tr>';
  });
  h += tbl(['审核单号', '内容项目', '提交人', '轮次', '排期日', '超期', '结论', '操作'], rows);
  return h;
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
function sopEdit() {
  const nodes = [
    ['选题立项', '明确选题方向、对标竞品、预估数据目标'],
    ['脚本撰写', '结构：钩子 3s → 痛点 → 产品 → 行动号召'],
    ['拍摄执行', '设备清单核对、分镜脚本拍摄'],
    ['后期剪辑', '节奏卡点、字幕规范、封面制作'],
    ['合规审核', '广告法敏感词检测、资质核对'],
    ['发布分发', '多平台定时发布、标题 A/B 测试'],
    ['数据复盘', '48h 数据回收、进入竞品对比库']
  ];
  let nl = '';
  nodes.forEach(function (n, i) {
    nl += '<div class="mg-i" style="border-radius:8px;' + (i === 1 ? 'background:var(--blue-bg)' : '') + '" onclick="toast(\'已选中节点：' + n[0] + '\',\'success\')">' +
      '<span class="lv" style="background:rgba(0,113,227,.12);color:var(--blue)">' + (i + 1) + '</span><div style="flex:1;min-width:0"><div class="mt" style="font-size:12.5px;' + (i === 1 ? 'color:var(--blue);font-weight:600' : '') + '">' + n[0] + '</div></div>' +
      (i < nodes.length - 1 ? '<span style="color:var(--text2)">' + ic('chev', 12) + '</span>' : '') + '</div>';
  });
  const body = '<div class="formrow one"><div class="fld"><label>SOP 名称</label><input value="跑鞋测评短视频 SOP"></div></div>' +
    '<div class="formrow"><div class="fld"><label>适用平台</label><select><option>抖音 / 视频号</option><option>全平台</option><option>小红书</option></select></div>' +
    '<div class="fld"><label>版本</label><input value="v2.4（编辑中）"></div></div>' +
    '<div style="display:grid;grid-template-columns:230px 1fr;gap:14px;margin-top:4px">' +
    '<div class="card" style="padding:10px;box-shadow:none;border:1px solid var(--line)"><div class="rowline" style="justify-content:space-between;padding:4px 6px 8px"><b style="font-size:12.5px">节点列表</b><span class="btn-txt btn" onclick="toast(\'新增节点 · 原型示意\',\'success\')">' + ic('plus', 13) + '</span></div>' + nl + '</div>' +
    '<div class="card" style="box-shadow:none;border:1px solid var(--line)"><b style="font-size:12.5px;display:block;margin-bottom:8px">节点详情 · 2 脚本撰写</b>' +
    '<div class="fld"><label>节点说明</label><textarea>结构：钩子 3s → 痛点场景 → 产品卖点 → 行动号召。口播控制在 180~220 字/分钟。</textarea></div>' +
    '<div class="fld" style="margin-top:10px"><label>交付物清单</label><textarea style="min-height:56px">脚本文档（飞书）/ 口播录音 / 分镜表</textarea></div>' +
    '<div class="fld" style="margin-top:10px"><label>负责人岗位</label><select><option>短视频编导</option><option>主播/达人</option><option>内容审核员</option></select></div>' +
    '<div class="rowline" style="margin-top:12px"><span class="csub" style="font-size:12px">预计耗时</span><span style="font-weight:600">2.5h</span><span class="chip" style="margin-left:auto">可被 AI 辅助</span></div></div></div>';
  openDrawer('节点编辑 · 跑鞋测评短视频 SOP', body,
    '<button class="btn btn-sec" onclick="toast(\'AI 正在生成节点提示词…\',\'success\')">AI 生成提示词</button><span style="flex:1"></span>' +
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="toast(\'SOP 已保存为 v2.4\',\'success\');closeDrawer()">保存</button>', '90%');
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
  if (state.page === 'content') renderPage();
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
  if (state.page === 'content') renderPage();
  toast('已立项：挂接「' + t.sop + '」，自动创建内容项目进入生产流转', 'success');
  hlFirst();
}
function topicReject(i) {
  if (!$('#F_op') || !$('#F_op').value.trim()) { toast('落选请填写评审意见', 'warn'); return; }
  const t = TOPICS[i];
  t.st = '落选';
  closeDrawer();
  if (state.page === 'content') renderPage();
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
  if (state.page === 'content') renderPage();
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
    if (state.page === 'content') renderPage();
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
  if (state.page === 'content') renderPage();
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
  if (state.page === 'content') renderPage();
  toast('终审通过：成片已解锁，移交发布（P6 可建发布单）', 'success');
  hlFirst();
}
function aiReviewReject(i) {
  if (!$('#F_op') || !$('#F_op').value.trim()) { toast('打回必填终审意见', 'warn'); return; }
  const t = AITASKS[i];
  t.st = '终审打回'; t.rev = 'Donny';
  closeDrawer();
  if (state.page === 'content') renderPage();
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
  if (state.page === 'content') renderPage();
  toast('审核通过：内容进入发布准备（可创建发布单 · PUB-R1）', 'success');
  hlFirst();
}
function reviewReject(i) {
  if (!$('#RV_op') || !$('#RV_op').value.trim()) { toast('打回/终止必须填写说明（REV-R2）', 'warn'); return; }
  const r = REVIEWS[i];
  r.cl = r.round >= 2 ? '驳回' : '打回';
  r.round += 1;
  closeDrawer();
  if (state.page === 'content') renderPage();
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
  if (state.page === 'content') renderPage();
  formOk(no, '发布单已创建，等待计划发布时间执行', '');
  toast('发布单创建成功：' + no, 'success');
}
function pubExec(i) {
  confirmDlg('执行发布确认', '将按计划时间把成片发布到目标账号平台（原型示意）。', '确认发布', function () {
    PUBS[i].st = '已发布';
    if (state.page === 'content') renderPage();
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
  if (state.page === 'content') renderPage();
  toast('链接已回填，归档包自动打包（源片+脚本+审核单+回执）', 'success');
  hlFirst();
}
/* scriptFinalize 辅助：确认弹窗是否已打开（防误触发 SCR-R1 提示后直接通过） */
function confirmOpened() { return !!document.querySelector('.cfwrap'); }


'use strict';
/* ===================== 02 TRAIN 培训 ===================== */
const TRAINS = [
  { id: 'TR20260910-01', name: '新主播开播规范培训', type: '直播规范', teacher: '赵敏', time: '2026-09-15 14:00', place: '3F 培训室', quota: 30, signed: 24, st: '报名中' },
  { id: 'TR20260908-02', name: '短视频脚本写作工作坊', type: '内容技能', teacher: '孙倩', time: '2026-09-13 10:00', place: '线上（腾讯会议）', quota: 25, signed: 25, st: '进行中' },
  { id: 'TR20260905-03', name: '财务报销制度宣讲', type: '制度合规', teacher: '周晴', time: '2026-09-11 16:00', place: '2F 会议室 A', quota: 40, signed: 32, st: '已结束' },
  { id: 'TR20260902-04', name: '运动品类知识（第 3 期）', type: '产品知识', teacher: '何舟', time: '2026-09-10 09:30', place: '3F 培训室', quota: 20, signed: 18, st: '已结束' },
  { id: 'TR20260828-05', name: '消防与应急演练', type: '安全', teacher: '林岚', time: '2026-09-08 15:00', place: '园区操场', quota: 60, signed: 54, st: '已结束' },
  { id: 'TR20260826-06', name: '数据分析入门（Excel→BI）', type: '数据技能', teacher: '陈默', time: '2026-09-17 19:00', place: '线上（腾讯会议）', quota: 30, signed: 11, st: '报名中' },
  { id: 'TR20260820-07', name: '外协人员保密培训', type: '制度合规', teacher: '林岚', time: '2026-09-05 10:00', place: '2F 会议室 B', quota: 15, signed: 6, st: '已取消' },
  { id: 'TR20260815-08', name: '直播间话术进阶', type: '直播技能', teacher: '苏杳', time: '2026-09-04 14:00', place: '3F 培训室', quota: 16, signed: 16, st: '已结束' }
];
PAGES.train = function () {
  const cur = state.tab.train || '培训计划';
  let h = pgHead('train', cur === '培训计划' ? '<button class="btn btn-sec" onclick="exportX(this,\'培训记录\',TRAINS.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="trainAdd()">' + ic('plus', 15) + '新建培训</button>' :
    '<button class="btn btn-pri" onclick="taskAdd()">' + ic('plus', 15) + '下达学习任务</button>');
  h += '<div class="tabs">' + ['培训计划', '学习任务'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'train\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  h += cur === '培训计划' ? trainPlanTab() : trainTaskTab();
  return h;
};
/* ---- TRAIN Tab1：培训计划 ---- */
function trainPlanTab() {
  const qr = state.q.train || {};
  let h = qbar(qi('培训编号', 130, qr.k0) + qi('名称', 130, qr.k1) + qs(['全部类型', '直播规范', '直播技能', '内容技能', '产品知识', '制度合规', '数据技能', '安全'], 100, qr.k2) + qi('讲师', 90, qr.k4) + qs(['全部状态', '报名中', '进行中', '已结束', '已取消'], 100, qr.k3), 'qSave(\'train\')');
  const stc = { '报名中': 'blue', '进行中': 'green', '已结束': 'gray', '已取消': 'red' };
  const list = qFilter(TRAINS, function (t) { return [t.id, t.name, t.teacher, t.place]; }, function (t) { return t.type + '|' + t.st; });
  let rows = '';
  list.forEach(function (t) {
    const i = TRAINS.indexOf(t);
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + t.id + '</td><td style="font-weight:500">' + t.name + '</td><td>' + t.type + '</td><td>' + sens(t.teacher) + '</td>' +
      '<td class="num" style="font-size:12px">' + t.time + '</td><td style="font-size:12px">' + t.place + '</td>' +
      '<td class="num">' + t.quota + '</td><td class="num"><span style="font-weight:600;' + (t.signed >= t.quota ? 'color:var(--red)' : '') + '">' + t.signed + '</span></td>' +
      '<td>' + tag(t.st, stc[t.st]) + '</td>' +
      '<td>' + (t.st === '报名中' && t.signed < t.quota ? '<button class="btn btn-pri btn-sm" onclick="trainEnroll(' + i + ')">报名</button>' :
        t.st === '报名中' ? '<button class="btn btn-sec btn-sm" disabled style="opacity:.5">已满员</button>' :
          '<span class="btn btn-sec btn-sm" onclick="toast(\'培训详情 · 原型示意\',\'success\')">查看</span>') + '</td></tr>';
  });
  h += tbl(['培训编号', '名称', '类型', '讲师', '时间', '地点', '名额', '报名数', '状态', '操作'], rows);
  return h;
};
/* ---- TRAIN Tab2：学习任务（ConfirmType = DURATION 学时达标 / QUIZ 自测问卷） ---- */
const TASKS = [
  { no: 'LT20260918-01', title: '新主播开播规范 · 学习任务', mats: 3, scope: '按岗位', ct: 'DURATION', need: 4, hrs: 3.5, ppl: 24, done: 19, st: '进行中', dl: '2026-09-25 18:00' },
  { no: 'LT20260917-02', title: '短视频脚本写作 · 课后测验', mats: 2, scope: '按人', ct: 'QUIZ', quiz: 0, pass: 80, ppl: 25, done: 21, avg: 86.4, st: '进行中', dl: '2026-09-24 18:00' },
  { no: 'LT20260914-03', title: '财务报销制度 · 合规自测', mats: 4, scope: '按岗位', ct: 'QUIZ', quiz: 1, pass: 90, ppl: 32, done: 32, avg: 93.1, st: '已完成', dl: '2026-09-18 18:00' },
  { no: 'LT20260912-04', title: '运动品类知识 · 第 3 期测验', mats: 5, scope: '按人', ct: 'QUIZ', quiz: 2, pass: 80, ppl: 18, done: 18, avg: 78.9, st: '已完成', dl: '2026-09-15 18:00' },
  { no: 'LT20260910-05', title: '消防与应急 · 学习任务', mats: 1, scope: '按岗位', ct: 'DURATION', need: 2, hrs: 2, ppl: 54, done: 51, st: '已完成', dl: '2026-09-12 18:00' },
  { no: 'LT20260908-06', title: '数据分析入门 · 预习任务', mats: 2, scope: '按人', ct: 'DURATION', need: 1, hrs: 0.5, ppl: 11, done: 6, st: '进行中', dl: '2026-09-28 18:00' }
];
/* QUIZ 问卷题库（自测问卷：题目+选项+答案+解析） */
const QUIZZES = [
  {
    title: '短视频脚本写作 · 课后测验', pass: 80, total: 100,
    qs: [
      { t: '短视频开场 3 秒的核心目标是什么？', sc: 20, opts: ['完整介绍产品参数', '留住观众（钩子）', '展示品牌 LOGO', '交代视频时长'], ans: 1, ana: '开场即钩子：3 秒内给出「看下去的理由」，参数与品牌信息应后置。' },
      { t: '口播脚本中「痛点前置」的正确做法是？', sc: 30, opts: ['先讲品牌历史再讲痛点', '先抛用户痛点场景，再给解决方案', '痛点放在结尾升华', '不提痛点只讲卖点'], ans: 1, ana: '痛点前置 → 方案承接 → 证明 → 行动号召，是种草脚本的黄金结构。' },
      { t: '以下哪个脚本结构更适合「好物种草」类短视频？', sc: 30, opts: ['参数罗列式', '痛点-方案-证明-行动式', '剧情反转式', '纯口播念稿式'], ans: 1, ana: '种草类核心是建立信任与购买动机，痛点-方案-证明-行动结构转化率最高。' },
      { t: '视频时长超过多久，完播率通常会显著下降（抖音信息流）？', sc: 20, opts: ['15 秒', '30 秒', '60 秒', '3 分钟'], ans: 2, ana: '信息流场景 60 秒是完播率的显著衰减点，核心内容应尽量前置。' }
    ]
  },
  {
    title: '财务报销制度 · 合规自测', pass: 90, total: 100,
    qs: [
      { t: '单张发票金额超过多少元需要提前走事前审批流程？', sc: 25, opts: ['1,000 元', '2,000 元', '5,000 元', '10,000 元'], ans: 2, ana: '依据《差旅与报销制度》5.2：单笔超 5,000 元须事前审批（OA 发起）。' },
      { t: '报销单提交后，发票影像件的保存期限要求是？', sc: 25, opts: ['1 年', '3 年', '5 年', '10 年'], ans: 2, ana: '财务凭证保存期限为 5 年，影像件与纸质单据同步归档。' },
      { t: '以下哪类发票不可以用于报销？', sc: 25, opts: ['增值税专用发票', '增值税普通发票', '定额发票（手写抬头）', '电子发票（区块链）'], ans: 2, ana: '定额发票抬头须机打，手写抬头视为不合规票据。' },
      { t: '月度报销的截止时间是每月几号前？', sc: 25, opts: ['25 号', '28 号', '30 号', '次月 5 号'], ans: 0, ana: '每月 25 日前提交当月费用，逾期顺延至下月批次。' }
    ]
  },
  {
    title: '运动品类知识 · 第 3 期测验', pass: 80, total: 100,
    qs: [
      { t: '缓震跑鞋与支撑跑鞋的核心区别在于？', sc: 25, opts: ['鞋面材质', '中底密度与足弓支撑结构', '鞋重', '外底耐磨度'], ans: 1, ana: '支撑系通过中底密度差与足弓结构纠正过度内旋，缓震系主打冲击吸收。' },
      { t: '适合大体重跑者（85kg+）的首选鞋型是？', sc: 25, opts: ['竞速碳板鞋', '缓震训练鞋', '赤足鞋', '越野鞋'], ans: 1, ana: '大体重跑者需高缓震保护，竞速碳板鞋刚性大易受伤。' },
      { t: '跑步鞋一般建议跑量达到多少公里更换？', sc: 25, opts: ['300~500 km', '800~1000 km', '1500 km', '鞋底磨穿再换'], ans: 0, ana: '中底材料疲劳周期约 300~500 km，超出后缓震性能显著衰减。' },
      { t: '「顶级支撑系」跑鞋的典型代表是哪一双？', sc: 25, opts: ['Nike Vaporfly', 'ASICS GT-2000', 'Saucony Kinvara', 'Hoka Clifton'], ans: 1, ana: 'GT-2000 系为 ASICS 经典支撑系训练鞋。' }
    ]
  }
];
function trainTaskTab() {
  let h = qbar(qi('任务编号', 130) + qi('任务名称', 130) + qs(['全部确认方式', '学时达标', '自测问卷'], 110) + qs(['全部状态', '进行中', '已结束'], 90), 'qSave(\'train\')');
  const stc = { '进行中': 'blue', '已结束': 'green', '已完成': 'green' };
  const list = qFilter(TASKS, function (t) { return [t.no, t.title]; }, function (t) { return (t.ct === 'DURATION' ? '学时达标' : '自测问卷') + '|' + t.st; });
  let rows = '';
  list.forEach(function (t) {
    const i = TASKS.indexOf(t);
    const progress = Math.round(t.done / t.ppl * 100);
    const rateColor = progress > 90 ? 'var(--green)' : progress >= 70 ? 'var(--yellow)' : 'var(--red)';
    const ctCell = t.ct === 'DURATION'
      ? tag('学时达标', 'cyan') + (t.hrs != null ? '<div class="csub" style="margin-top:3px">需学满 ' + t.need + 'h · 已学 ' + t.hrs + 'h</div>' : '<div class="csub" style="margin-top:3px">需学满 ' + t.need + 'h</div>')
      : tag('自测问卷', 'purple') + '<div class="csub" style="margin-top:3px">及格 ' + t.pass + ' 分' + (t.avg != null ? ' · 平均 ' + t.avg + ' 分' : '') + '</div>';
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + t.no + '</td><td style="font-weight:500">' + t.title + '</td>' +
      '<td class="num">' + (t.mats != null ? t.mats : 3) + '</td><td>' + tag(t.scope || '按人', 'gray') + '</td>' +
      '<td class="num">' + t.ppl + '</td><td class="num">' + t.done + '</td>' +
      '<td><div class="rowline"><span class="pg" style="width:64px"><i style="width:' + progress + '%;background:' + rateColor + '"></i></span><span class="num" style="font-size:12px">' + progress + '%</span></div></td>' +
      '<td>' + ctCell + '</td>' +
      '<td class="num" style="font-size:12px;' + (t.st !== '进行中' ? '' : '') + '">' + (t.dl || '2026-09-30 18:00') + '</td>' +
      '<td>' + tag(t.st, stc[t.st]) + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="taskRecords(' + i + ')">学习记录</span>' +
      (t.ct === 'QUIZ' && t.st === '进行中' ? '<button class="btn btn-pri btn-sm" style="margin-left:6px" onclick="quizDo(' + (t.quiz != null ? t.quiz : -1) + ',' + i + ')">进入作答</button>' : '') +
      '</td></tr>';
  });
  h += tbl(['任务编号', '任务名称', '资料数', '指派范围', '应完成', '已完成', '完成率', '确认方式', '截止时间', '状态', '操作'], rows);
  h += '<div class="card" style="margin-top:14px;padding:12px 16px;display:flex;gap:10px;align-items:center">' + ic('help', 16) +
    '<span style="font-size:12px;color:var(--text2);line-height:1.6">学习任务两种确认方式：<b style="color:var(--text)">学时达标（DURATION）</b>——累计观看学时达标即完成；<b style="color:var(--text)">自测问卷（QUIZ）</b>——在线作答、系统判分，达到及格分即完成，未及格可重答（记录最新成绩）。完成率 >90% 绿 / 70~90% 黄 / <70% 红（BR-102）。逾期仍可补学补确认，计入完成率分母（对应 PRD 5.7 TRAIN-002 学习任务管理）。</span></div>';
  return h;
};
/* TRAIN：QUIZ 问卷作答（学习中心内嵌问卷 → 判分 → 未及格可重答） */
function quizDo(qi_, ti) {
  const q = qi_ >= 0 ? QUIZZES[qi_] : (TASKS[ti] ? TASKS[ti].quizObj : null);
  if (!q) { toast('该任务未配置问卷（原型数据缺失）', 'warn'); return; }
  state.qz = { qi: qi_, ti: ti, sel: {}, graded: false };
  renderQuizDrawer(q);
}
function renderQuizDrawer(q, sel, graded) {
  const st = state.qz || { sel: {} };
  sel = sel || st.sel; graded = graded || st.graded;
  let body = '<div class="qz-head"><div class="qz-meta">' + tag('自测问卷', 'purple') + tag('及格 ' + q.pass + ' 分', 'blue') +
    '<span class="csub">共 ' + q.qs.length + ' 题 · 满分 ' + q.total + ' 分</span></div>' +
    (graded ? '' : '<span class="qz-timer">' + ic('clock', 14) + '不限时 · 可回改</span>') + '</div>';
  q.qs.forEach(function (it, n) {
    const pick = sel[n];
    body += '<div class="qz-item"><div class="qz-q"><span class="qno">' + (n + 1) + '</span>' + it.t + '<span class="qscore">' + it.sc + ' 分</span></div>';
    it.opts.forEach(function (o, oi) {
      const on = pick === oi;
      let cls = 'qz-opt';
      if (graded) {
        if (oi === it.ans) cls += ' right';
        else if (on && oi !== it.ans) cls += ' wrong';
      } else if (on) cls += ' on';
      body += '<div class="' + cls + '"' + (graded ? '' : ' onclick="quizPick(' + n + ',' + oi + ')"') + '><span class="ol">' + 'ABCD'[oi] + '</span><span>' + o + '</span></div>';
    });
    if (graded && pick !== it.ans) body += '<div class="qz-ana">' + ic('check', 13) + ' 正确答案 ' + 'ABCD'[it.ans] + ' · ' + it.ana + '</div>';
    body += '</div>';
  });
  const foot = graded
    ? '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>'
    : '<button class="btn btn-sec" onclick="closeDrawer()">暂存退出</button><button class="btn btn-pri" onclick="quizSubmit()">提交问卷</button>';
  openDrawer('自测问卷 · ' + q.title, body, foot, '640px');
  return body;
}
function quizPick(n, oi) {
  state.qz.sel[n] = oi;
  const items = document.querySelectorAll('#dr-body .qz-item');
  const item = items && items[n];
  if (!item) return;
  const opts = item.querySelectorAll('.qz-opt');
  if (!opts) return;
  opts.forEach(function (o, i) { o.classList.toggle('on', i === oi); });
}
function quizSubmit() {
  const q = QUIZZES[state.qz.qi] || (state.qz.ti >= 0 && TASKS[state.qz.ti] ? TASKS[state.qz.ti].quizObj : null);
  if (!q) return;
  const sel = state.qz.sel;
  const unanswered = q.qs.filter(function (_, n) { return sel[n] == null; }).length;
  if (unanswered > 0) { toast('还有 ' + unanswered + ' 题未作答，请完成后再提交', 'warn'); return; }
  let score = 0;
  q.qs.forEach(function (it, n) { if (sel[n] === it.ans) score += it.sc; });
  state.qz.graded = true; state.qz.score = score;
  renderQuizDrawer(q, sel, true);
  const passed = score >= q.pass;
  const t = state.qz.ti >= 0 ? TASKS[state.qz.ti] : (TASKS.filter(function (t2) { return t2.quiz === state.qz.qi; })[0]);
  if (t && t.st === '进行中') { t.done = Math.min(t.ppl, t.done + 1); if (t.done >= t.ppl) t.st = '已完成'; }
  if (state.page === 'train' && (state.tab.train || '培训计划') === '学习任务') renderPage();
  setTimeout(function () { toast(passed ? '得分 ' + score + ' 分，已通过（及格 ' + q.pass + ' 分）' : '得分 ' + score + ' 分，未达到及格分 ' + q.pass + ' 分，可重新作答', passed ? 'success' : 'error'); }, 120);
  if (passed) hlFirst();
}
/* TRAIN：未及格重答 */
function quizRetake() {
  const q = QUIZZES[state.qz.qi];
  state.qz = { qi: state.qz.qi, sel: {}, graded: false };
  renderQuizDrawer(q);
  toast('已重置答卷，可重新作答', 'success');
}
/* TRAIN：下达学习任务表单（P2 §7 创建任务抽屉：资料多选 + 指派范围 + ConfirmType + QUIZ 问卷编辑器） */
const TMATS = [
  { no: 'MT-301', title: '开播规范手册 V3.2', tp: '文档', ver: 'v3.2', pos: '主播组' },
  { no: 'MT-302', title: '直播间违规红线案例集', tp: '文档', ver: 'v2.0', pos: '全员' },
  { no: 'MT-303', title: '开场话术与留存技巧（视频）', tp: '视频', ver: 'v1.5', pos: '主播组' },
  { no: 'MT-304', title: '平台违规判例 9 月更新', tp: '文档', ver: 'v9.0', pos: '全员' },
  { no: 'MT-305', title: '短视频脚本结构模板', tp: '文档', ver: 'v2.4', pos: '内容中心' }
];
function taskAdd() {
  const body = '<div style="padding:2px 4px">' +
    frow([
      { k: 'title', label: '任务名称', type: 'text', req: true, ph: '如：新主播开播规范 · 学习任务（≤128 字）' },
      { k: 'scope', label: '指派范围', type: 'pills', req: true, val: '按人', opts: ['按人', '按岗位'] },
      { k: 'deadline', label: '截止时间', type: 'dt', req: true, val: '2026-10-02T18:00', hint: '不得早于当前时间（1102 拦截）' }
    ]) +
    '<div class="fld wide"><label>学习资料（多选，仅已发布资料）<i class="req">*</i></label>' +
    '<div id="tmats" style="max-height:150px;overflow:auto;border:1px solid var(--line2);border-radius:var(--r-s);padding:4px 10px">' +
    TMATS.map(function (m, i) {
      return '<label style="display:flex;align-items:center;gap:9px;padding:7px 2px;border-bottom:1px solid var(--line);font-size:12.5px;cursor:pointer">' +
        '<input type="checkbox" value="' + i + '" style="accent-color:var(--blue)">' +
        '<span class="mono" style="color:var(--text2);font-size:11px">' + m.no + '</span><span style="flex:1">' + m.title + '</span>' +
        '<span style="color:var(--text2);font-size:11px">' + m.tp + ' · ' + m.ver + ' · ' + m.pos + '</span></label>';
    }).join('') + '</div><div class="ferr" id="E_mats"></div></div>' +
    '<div class="fld wide"><label>指派对象<i class="req">*</i></label>' +
    '<div id="ttargets" style="display:flex;gap:7px;flex-wrap:wrap">' +
    (function () {
      const all = ['苏杳', '赵敏', '孙倩', '何舟', '李澈', '陈默', '王野'];
      return all.map(function (c) { return '<label class="pill" style="cursor:pointer"><input type="checkbox" value="' + c + '" onchange="pillChk(this)" style="accent-color:var(--blue)"><span>' + c + '</span></label>'; }).join('');
    })() +
    '</div><div class="hint" style="margin-top:6px" id="tscopehint">按人指派：勾选人员（切换「按岗位」后变为岗位多选并预览目标人数）</div><div class="ferr" id="E_targets"></div></div>' +
    '<div class="fld wide"><label>确认方式<i class="req">*</i></label>' +
    '<div class="pills" id="ctsel">' +
    '<label class="pill on"><input type="radio" name="P_ct2" value="学时达标" checked onchange="ctSel(this)"><span>学时达标（DURATION）</span></label>' +
    '<label class="pill"><input type="radio" name="P_ct2" value="自测问卷" onchange="ctSel(this)"><span>自测问卷（QUIZ）</span></label>' +
    '</div></div>' +
    '<div id="ct_dur" class="fld"><label>要求学时</label><input id="F_need" type="number" value="4" min="0.5" step="0.5" style="width:100%"></div>' +
    '<div id="ct_quiz" style="display:none">' +
    '<div class="fld wide"><label>及格分<i class="req">*</i></label><input id="F_pass" type="number" value="80" min="1" style="width:130px"> <span class="csub">满分 100 分，未及格可重答（记录最新成绩）</span></div>' +
    '<div class="fld wide"><label>问卷题目编辑器（题目 ≥1，每题选项 ≥2）<i class="req">*</i></label>' +
    '<div id="quizEd" style="border:1px solid var(--line2);border-radius:var(--r-s);padding:10px 12px"></div>' +
    '<button class="btn btn-sec btn-sm" style="margin-top:8px" onclick="quizQAdd()">' + ic('plus', 13) + '添加题目</button>' +
    '<div class="ferr" id="E_quiz"></div></div>' +
    '</div></div>';
  state.qzEd = [{ q: '', opts: ['', ''], ans: 0 }];
  openDrawer('创建学习任务（Drawer 720px）', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="taskAddSubmit()">提交任务</button>', '720px');
  setTimeout(renderQuizEd, 0);
}
/* 确认方式切换：DURATION/QUIZ 分区显隐 */
function ctSel(inp) {
  const v = inp.value;
  const p = document.querySelectorAll('#ctsel .pill');
  p.forEach(function (pp) { pp.classList.remove('on'); });
  inp.parentNode.classList.add('on');
  const dur = document.getElementById('ct_dur'), qz = document.getElementById('ct_quiz');
  if (dur) dur.style.display = v === '学时达标' ? '' : 'none';
  if (qz) qz.style.display = v === '自测问卷' ? '' : 'none';
}
/* 问卷编辑器渲染：动态增删题/选项、设答案 */
function renderQuizEd() {
  const ed = state.qzEd || [];
  let h = '';
  ed.forEach(function (it, n) {
    h += '<div class="qz-gradeitem" style="padding-left:0;padding-right:0">' +
      '<div class="rowline" style="justify-content:space-between;margin-bottom:6px"><b style="font-size:12.5px">第 ' + (n + 1) + ' 题</b>' +
      (ed.length > 1 ? '<span class="btn-txt btn-sm" style="color:var(--red)" onclick="quizQDel(' + n + ')">删除本题</span>' : '') + '</div>' +
      '<input id="QZQ_' + n + '" placeholder="题干（≤256 字）" value="' + String(it.q || '').replace(/"/g, '&quot;') + '" oninput="state.qzEd[' + n + '].q=this.value" style="width:100%;height:34px;border:1px solid var(--line2);border-radius:var(--r-s);padding:0 10px;font-size:13px;font-family:var(--font);outline:none">' +
      '<div style="margin-top:8px;display:flex;flex-direction:column;gap:6px">' +
      it.opts.map(function (o, oi) {
        return '<div class="rowline" style="gap:8px"><label class="rowline" style="gap:6px;font-size:12px;color:var(--text2);cursor:pointer;flex:none">' +
          '<input type="radio" name="QZA_' + n + '"' + (it.ans === oi ? ' checked' : '') + ' onchange="quizAnsSet(' + n + ',' + oi + ')" style="accent-color:var(--blue)"> 设为答案</label>' +
          '<input placeholder="选项 ' + 'ABCD'[oi] + '" value="' + String(o || '').replace(/"/g, '&quot;') + '" oninput="state.qzEd[' + n + '].opts[' + oi + ']=this.value" style="flex:1;height:30px;border:1px solid var(--line2);border-radius:var(--r-s);padding:0 10px;font-size:12.5px;font-family:var(--font);outline:none">' +
          (it.opts.length > 2 ? '<span class="btn-txt btn-sm" style="color:var(--red)" onclick="quizODel(' + n + ',' + oi + ')">删</span>' : '') +
          '</div>';
      }).join('') + '</div>' +
      (it.opts.length < 4 ? '<span class="btn-txt btn-sm" style="margin-top:6px" onclick="quizOAdd(' + n + ')">+ 添加选项</span>' : '') +
      '</div>';
  });
  const el = document.getElementById('quizEd');
  if (el) el.innerHTML = h;
}
function quizQAdd() { state.qzEd.push({ q: '', opts: ['', ''], ans: 0 }); renderQuizEd(); }
function quizQDel(n) { state.qzEd.splice(n, 1); state.qzEd.forEach(function (it, i) { it.ans = Math.min(it.ans, it.opts.length - 1); }); renderQuizEd(); }
function quizOAdd(n) { state.qzEd[n].opts.push(''); if (state.qzEd[n].opts.length > 4) return; renderQuizEd(); }
function quizODel(n, oi) { state.qzEd[n].opts.splice(oi, 1); if (state.qzEd[n].ans >= state.qzEd[n].opts.length) state.qzEd[n].ans = 0; renderQuizEd(); }
function quizAnsSet(n, oi) { state.qzEd[n].ans = oi; }
/* 提交：校验 + 汇总确认 + 建任务 */
function taskAddSubmit() {
  if (!formValidate(['title', 'deadline'])) return;
  const mats = document.querySelectorAll('#tmats input:checked');
  if (!mats.length) { const e = document.getElementById('E_mats'); if (e) e.textContent = '请至少勾选 1 份学习资料'; toast('请选择学习资料', 'error'); return; }
  const targets = document.querySelectorAll('#ttargets input:checked');
  if (!targets.length) { const e = document.getElementById('E_targets'); if (e) e.textContent = '请勾选指派对象'; toast('请选择指派对象', 'error'); return; }
  const ctEl = document.querySelector('input[name="P_ct2"]:checked');
  const ct = ctEl ? ctEl.value : '学时达标';
  let quiz = null;
  if (ct === '自测问卷') {
    const ed = state.qzEd;
    if (!ed.length || ed.some(function (it) { return !it.q.trim(); })) { const e = document.getElementById('E_quiz'); if (e) e.textContent = '每道题目均需填写题干'; toast('问卷题目不完整', 'error'); return; }
    if (ed.some(function (it) { return it.opts.length < 2 || it.opts.some(function (o) { return !o.trim(); }); })) { const e = document.getElementById('E_quiz'); if (e) e.textContent = '每题至少 2 个非空选项'; toast('问卷选项不完整', 'error'); return; }
    const ps = Number(document.getElementById('F_pass') ? document.getElementById('F_pass').value : 80);
    if (!ps || ps < 1 || ps > 100) { toast('及格分须在 1~100 之间', 'error'); return; }
    quiz = { qs: ed, pass: ps };
  }
  const sum = '<b>' + $('#F_title').value.trim() + '</b><br>资料 ' + mats.length + ' 份 · 指派 ' + targets.length + ' 人 · 截止 ' + ($('#F_deadline').value || '').replace('T', ' ') +
    '<br>确认方式：' + (ct === '学时达标' ? '学时达标（需学满 ' + (document.getElementById('F_need') ? document.getElementById('F_need').value : 4) + 'h）' : '自测问卷（' + state.qzEd.length + ' 题 · 及格 ' + quiz.pass + ' 分）');
  confirmDlg('确认下达学习任务？', sum, '确认下达', function () {
    const no = 'LT20260918-' + String(TASKS.length + 1).padStart(2, '0');
    const t = { no: no, title: $('#F_title').value.trim(), mats: mats.length, scope: '按人', ppl: targets.length, done: 0, st: '进行中', dl: ($('#F_deadline').value || '').replace('T', ' '), ct: ct === '学时达标' ? 'DURATION' : 'QUIZ' };
    if (t.ct === 'DURATION') { t.need = Number(document.getElementById('F_need') ? document.getElementById('F_need').value : 4); }
    else {
      t.quizQs = quiz.qs; t.pass = quiz.pass;
      /* 同步生成可作答 QUIZ：均分 100 分 */
      const n = quiz.qs.length;
      const per = Math.floor(100 / n); let rem = 100 - per * n;
      t.quizObj = { title: t.title, pass: quiz.pass, total: 100, qs: quiz.qs.map(function (it) { const sc = per + (rem-- > 0 ? 1 : 0); return { t: it.q, sc: sc, opts: it.opts.slice(), ans: it.ans, ana: '以学习资料为准作答即可。' }; }) };
      t.avg = '—';
    }
    TASKS.unshift(t);
    closeDrawer();
    if (state.page === 'train') { state.tab.train = '学习任务'; renderPage(); }
    formOk(no, '学习任务已下达，指派 ' + t.ppl + ' 人（工作台已推送学习待办）', '');
    toast('学习任务下达成功：' + no, 'success');
  });
}
/* TRAIN：学习记录抽屉（P2 §7：用户/部门/进度/确认状态/得分/逾期） */
const TRECORDS = [
  { who: '苏杳', dept: '主播组', prog: 100, cf: '已确认', score: 95, start: '09-17 09:12', fin: '09-17 10:40', over: false },
  { who: '赵敏', dept: '运营中心', prog: 100, cf: '已确认', score: 88, start: '09-17 09:30', fin: '09-17 11:02', over: false },
  { who: '孙倩', dept: '内容中心', prog: 80, cf: '未确认', score: null, start: '09-17 14:20', fin: '—', over: false },
  { who: '何舟', dept: '运营中心', prog: 100, cf: '已确认', score: 72, start: '09-17 10:00', fin: '09-17 10:55', over: false },
  { who: '李澈', dept: '内容中心', prog: 60, cf: '未确认', score: null, start: '09-18 09:00', fin: '—', over: false },
  { who: '陈默', dept: '数据中心', prog: 100, cf: '已确认', score: 90, start: '09-16 20:10', fin: '09-16 21:00', over: true }
];
function taskRecords(i) {
  const t = TASKS[i];
  const body = '<div class="qz-head"><div class="qz-meta">' + tag('学习记录', 'blue') +
    '<span class="csub">' + t.no + ' · ' + t.title + ' · 指派 ' + t.ppl + ' 人</span></div>' +
    '<span class="csub">逾期仍可补学，计入完成率分母</span></div>' +
    '<table class="tb"><thead><tr><th>用户</th><th>部门</th><th>进度</th><th>确认状态</th><th>得分</th><th>开始</th><th>完成</th><th>逾期</th></tr></thead><tbody>' +
    TRECORDS.map(function (r) {
      const cfc = r.cf === '已确认' ? 'green' : 'gray';
      return '<tr><td style="font-weight:500">' + sens(r.who) + '</td><td>' + r.dept + '</td>' +
        '<td><div class="rowline"><span class="pg" style="width:52px"><i style="width:' + r.prog + '%;background:' + (r.prog >= 100 ? 'var(--green)' : 'var(--blue)') + '"></i></span><span class="num" style="font-size:12px">' + r.prog + '%</span></div></td>' +
        '<td>' + tag(r.cf, cfc) + '</td>' +
        '<td class="num" style="font-weight:600;' + (r.score != null ? (r.score >= (t.pass || 80) ? 'color:var(--green)' : 'color:var(--red)') : 'color:var(--text2)') + '">' + (r.score != null ? r.score : '—') + '</td>' +
        '<td class="num" style="font-size:12px">' + r.start + '</td><td class="num" style="font-size:12px">' + r.fin + '</td>' +
        '<td>' + (r.over ? tag('逾期 2 天', 'red') : '<span class="csub">—</span>') + '</td></tr>';
    }).join('') + '</tbody></table>';
  openDrawer('学习记录 · ' + t.no, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '760px');
}
/* TRAIN：报名（确认 → 报名数+1 → 满员禁用） */
function trainEnroll(i) {
  const t = TRAINS[i];
  if (t.signed >= t.quota) { toast('该培训已满员', 'warn'); return; }
  confirmDlg('确认报名？', '培训「' + t.name + '」（' + t.time + ' · ' + t.place + '），当前 ' + t.signed + '/' + t.quota + ' 人，确认后报名成功。', '确认报名', function () {
    t.signed += 1;
    if (state.page === 'train') renderPage();
    toast('报名成功：' + t.name + '（' + t.signed + '/' + t.quota + '）', 'success');
    hlFirst();
  });
}
/* TRAIN：新建培训表单 */
function trainAdd() {
  const body = frow([
    { k: 'name', label: '培训名称', type: 'text', req: true, ph: '如：新主播开播规范培训' },
    { k: 'type', label: '培训类型', type: 'select', opts: ['直播规范', '直播技能', '内容技能', '产品知识', '制度合规', '数据技能', '安全'] },
    { k: 'teacher', label: '讲师', type: 'select', req: true, opts: ['赵敏', '孙倩', '何舟', '林岚', '周晴', '陈默', '苏杳'] },
    { k: 'time', label: '培训时间', type: 'dt', req: true, val: '2026-09-18T14:00' },
    { k: 'place', label: '地点', type: 'select', opts: ['3F 培训室', '2F 会议室 A', '2F 会议室 B', '线上（腾讯会议）', '园区操场'] },
    { k: 'quota', label: '名额', type: 'num', req: true, unit: '人', val: 30, min: 1 },
    { k: 'brief', label: '培训简介', type: 'textarea', ph: '培训目标、面向人群、考核方式', wide: true }
  ]);
  openDrawer('新建培训', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="trainAddSubmit()">创建培训</button>', '480px');
}
function trainAddSubmit() {
  if (!formValidate(['name', 'teacher', 'time', 'quota'])) return;
  const no = 'TR20260912-' + String(TRAINS.length + 1).padStart(2, '0');
  TRAINS.unshift({ id: no, name: $('#F_name').value.trim(), type: $('#F_type').value, teacher: $('#F_teacher').value, time: ($('#F_time').value || '').replace('T', ' '), place: $('#F_place').value, quota: Number($('#F_quota').value || 30), signed: 0, st: '报名中' });
  if (state.page === 'train') renderPage();
  formOk(no, '培训已创建，进入「报名中」状态并开放报名', '');
  toast('培训创建成功：' + no, 'success');
}

/* ===================== 03 MEET 会议 ===================== */
const MEETS = [
  { id: 'MT20260912-03', topic: '秋季大促直播动员会', org: '何舟', time: '今天 16:00', dur: '1.5h', room: '3F-大会议室', ppl: 12, min: '待生成' },
  { id: 'MT20260912-02', topic: '跑鞋新品选品评审', org: '何舟', time: '今天 10:00', dur: '1h', room: '2F-会议室 A', ppl: 8, min: 'AI 转写中' },
  { id: 'MT20260911-05', topic: '周度经营复盘会', org: 'Donny', time: '昨天 19:00', dur: '2h', room: '3F-大会议室', ppl: 15, min: '已生成' },
  { id: 'MT20260911-04', topic: '短视频选题周会', org: '孙倩', time: '昨天 14:00', dur: '1h', room: '线上（钉闪会）', ppl: 6, min: '已生成' },
  { id: 'MT20260910-08', topic: '财务月度结算对齐', org: '周晴', time: '09-10 15:00', dur: '1.5h', room: '2F-会议室 B', ppl: 5, min: '已生成' },
  { id: 'MT20260910-07', topic: '主播排期协调会', org: '赵敏', time: '09-10 09:30', dur: '0.5h', room: '线上（钉闪会）', ppl: 9, min: '待生成' },
  { id: 'MT20260909-11', topic: '竞品数据月度分析', org: '陈默', time: '09-09 16:00', dur: '1h', room: '3F-培训室', ppl: 7, min: '已生成' },
  { id: 'MT20260908-02', topic: '资产盘点启动会', org: '林岚', time: '09-08 10:00', dur: '1h', room: '2F-会议室 A', ppl: 10, min: '已归档' },
  { id: 'MT20260907-01', topic: '外协合作协议评审', org: 'Donny', time: '09-07 14:00', dur: '1h', room: '2F-会议室 B', ppl: 4, min: '已生成' }
];
PAGES.meet = function () {
  let h = pgHead('meet', '<button class="btn btn-pri" onclick="meetAdd()">' + ic('plus', 15) + '预约会议</button>');
  h += qbar(qi('会议编号', 130, (state.q.meet || {}).k0) + qi('主题', 130, (state.q.meet || {}).k1) + qs(['全部状态', '今天', '本周', '已结束'], 90, (state.q.meet || {}).k2) + qi('会议室', 110, (state.q.meet || {}).k3), 'qSave(\'meet\')');
  const timeline = [
    ['09:30', '主播排期协调会（续）', '线上', 'blue'],
    ['10:00', '跑鞋新品选品评审 · 2F-A', '何舟', 'blue'],
    ['12:00', '— 午休 —', '', 'gray'],
    ['14:00', '短视频选题评审（新增）', '孙倩', 'blue'],
    ['16:00', '秋季大促直播动员会 · 3F-大会议室', '何舟', 'green'],
    ['19:00', '夜场直播值守（非会议）', '赵敏', 'gray']
  ];
  const minc = { '已生成': 'green', 'AI 转写中': 'blue', '待生成': 'orange', '已归档': 'gray' };
  const list = qFilter(MEETS, function (m) { return [m.id, m.topic, m.org, m.room]; }, function (m) { return m.st || '今天'; });
  let rows = '';
  list.forEach(function (m) {
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + m.id + '</td><td style="font-weight:500">' + m.topic + '</td><td>' + sens(m.org) + '</td>' +
      '<td class="num" style="font-size:12px">' + m.time + '</td><td class="num">' + m.dur + '</td><td style="font-size:12px">' + m.room + '</td><td class="num">' + m.ppl + ' 人</td>' +
      '<td>' + tag(m.min, minc[m.min]) + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="toast(\'会议详情 / 纪要 · 原型示意\',\'success\')">查看</span></td></tr>';
  });
  const tblEl = tbl(['会议编号', '主题', '组织者', '时间', '时长', '会议室', '参会人数', '纪要状态', '操作'], rows);
  h += '<div class="g2r"><div><div class="sec" style="margin-top:0">今日时间轴</div><div class="card"><div class="tl">' +
    timeline.map(function (t) {
      const c = t[3] === 'green' ? 'gg' : t[3] === 'blue' ? '' : 'oo';
      return '<div class="tl-i ' + (t[3] === 'gray' ? 'oo' : c) + '"><div class="tt" style="font-size:12px">' + t[0] + ' · ' + t[1] + '</div>' + (t[2] ? '<div class="td">组织：' + t[2] + '</div>' : '') + '</div>';
    }).join('') + '</div></div></div>' +
    '<div><div class="sec" style="margin-top:0">会议列表</div>' + tblEl + '</div></div>';
  return h;
};
/* MEET：预约会议表单 */
function meetAdd() {
  const body = frow([
    { k: 'topic', label: '会议主题', type: 'text', req: true, ph: '如：秋季大促直播动员会' },
    { k: 'org', label: '组织者', type: 'text', val: ROLES[state.role].user, disabled: true },
    { k: 'time', label: '会议时间', type: 'dt', req: true, val: '2026-09-15T14:00' },
    { k: 'dur', label: '时长', type: 'select', opts: ['0.5h', '1h', '1.5h', '2h', '3h'] },
    { k: 'room', label: '会议室', type: 'select', req: true, opts: ['3F-大会议室', '2F-会议室 A', '2F-会议室 B', '3F-培训室', '线上（钉闪会）'] },
    { k: 'ppl', label: '参会人', type: 'text', ph: '多个姓名以顿号分隔' },
    { k: 'agenda', label: '议程', type: 'textarea', ph: '会议议程与预期产出（选填）', wide: true }
  ]);
  openDrawer('预约会议', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="meetAddSubmit()">提交预约</button>', '480px');
}
function meetAddSubmit() {
  if (!formValidate(['topic', 'time', 'room'])) return;
  const no = 'MT20260912-' + String(MEETS.length + 1).padStart(2, '0');
  MEETS.unshift({ id: no, topic: $('#F_topic').value.trim(), org: ROLES[state.role].user, time: '09-15 ' + (($('#F_time').value || '').split('T')[1] || '14:00'), dur: $('#F_dur').value, room: $('#F_room').value, ppl: Math.max(2, ($('#F_ppl').value || '赵敏、孙倩').split(/[、,，]/).filter(Boolean).length), min: '待生成' });
  if (state.page === 'meet') renderPage();
  formOk(no, '会议室已锁定，纪要将在会议结束后由 AI 自动生成', '');
  toast('会议预约成功：' + no, 'success');
}

/* ===================== 03 REPORT 日报 ===================== */
const REPORTS = [
  { date: '2026-09-11', user: '赵敏', type: '直播', pct: 100, at: '09-11 21:40', st: '已提交', rvw: '已审阅' },
  { date: '2026-09-11', user: '孙倩', type: '短视频', pct: 100, at: '09-11 22:15', st: '已提交', rvw: '待审阅' },
  { date: '2026-09-11', user: '林岚', type: '行政', pct: 92, at: '09-11 18:30', st: '已提交', rvw: '已审阅' },
  { date: '2026-09-11', user: '何舟', type: '运营', pct: 100, at: '09-12 08:02', st: '迟交', rvw: '待审阅' },
  { date: '2026-09-11', user: '苏杳', type: '直播', pct: 68, at: '09-11 23:50', st: '已提交', rvw: '已退回' },
  { date: '2026-09-10', user: '赵敏', type: '直播', pct: 100, at: '09-10 21:20', st: '已提交', rvw: '已审阅' },
  { date: '2026-09-10', user: '王野', type: '短视频', pct: 45, at: '—', st: '草稿', rvw: '—' },
  { date: '2026-09-09', user: '李澈', type: '短视频', pct: 88, at: '09-10 09:12', st: '已补交', rvw: '已审阅' },
  { date: '2026-09-09', user: '周晴', type: '运营', pct: 100, at: '09-09 18:05', st: '已提交', rvw: '已审阅' },
  { date: '2026-09-08', user: '陈默', type: '运营', pct: 96, at: '09-08 19:44', st: '已提交', rvw: '已审阅' }
];
PAGES.report = function () {
  const cur = state.tab.report || '我的日报';
  const pendRvw = REPORTS.filter(function (r) { return r.rvw === '待审阅'; }).length;
  let h = pgHead('report', cur === '待我审阅' ? '<button class="btn btn-sec" onclick="reportRvwBatch()">批量通过</button>' :
    cur === '数据上报' ? '<button class="btn btn-sec" onclick="reportTplAdd()">新建模板</button><button class="btn btn-pri" onclick="reportSubmitData()">' + ic('plus', 15) + '提交上报数据</button>' :
      '<button class="btn btn-pri" onclick="reportWrite()">' + ic('plus', 15) + '填写今日日报</button>');
  h += '<div class="tabs">' + ['我的日报', '团队日报', '待我审阅', '数据上报', '统计'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'report\',\'' + t + '\')">' + t + (t === '待我审阅' && pendRvw ? ' <span class="cbadge" style="background:var(--red)">' + pendRvw + '</span>' : '') + '</div>';
  }).join('') + '</div>';
  if (cur === '数据上报') return h + reportUploadTab();
  if (cur === '统计') {
    const rvwRate = Math.round(REPORTS.filter(function (r) { return r.rvw === '已审阅' || r.rvw === '已退回'; }).length / Math.max(REPORTS.filter(function (r) { return r.st !== '草稿'; }).length, 1) * 100);
    h += '<div class="g4"><div class="card stat"><span class="l">本周提交率</span><div class="n">93%</div><div class="d">42 / 45 人次</div></div>' +
      '<div class="card stat"><span class="l">准时率</span><div class="n" style="color:var(--green)">88%</div><div class="d">环比 <span class="pos">+5%</span></div></div>' +
      '<div class="card stat"><span class="l">字段完成度均值</span><div class="n">94%</div><div class="d">直播类日报最低 86%</div></div>' +
      '<div class="card stat"><span class="l">审阅完成率（MEET-002）</span><div class="n" style="color:var(--blue)">' + rvwRate + '%</div><div class="d">待审 ' + pendRvw + ' · 退回 ' + REPORTS.filter(function (r) { return r.rvw === '已退回'; }).length + ' 份</div></div></div>' +
      '<div class="sec">近 7 天提交趋势</div><div class="card">' + barsChart([39, 41, 44, 38, 45, 42, 43], 'i') + '</div>';
    return h;
  }
  if (cur === '待我审阅') {
    const pend = REPORTS.filter(function (r) { return r.rvw === '待审阅'; });
    if (!pend.length) return h + emptyState('暂无待审阅日报', '所有提交的日报均已逐级审阅完成');
    const rvc = { '待审阅': 'orange', '已审阅': 'green', '已退回': 'red', '—': 'gray' };
    let rows = '';
    pend.forEach(function (r) {
      const i = REPORTS.indexOf(r);
      rows += '<tr><td class="num">' + r.date + '</td><td style="font-weight:500">' + sens(r.user) + '</td><td>' + tag(r.type + '日报', 'blue') + '</td>' +
        '<td><div class="rowline">' + pgbar(r.pct, r.pct >= 90 ? 'var(--green)' : r.pct >= 70 ? 'var(--orange)' : 'var(--red)') + '<span class="num" style="font-size:12px">' + r.pct + '%</span></div></td>' +
        '<td class="num" style="font-size:12px;color:var(--text2)">' + r.at + '</td>' +
        '<td><button class="btn btn-pri btn-sm" onclick="reportApprove(' + i + ')">通过</button> <button class="btn btn-sm" style="color:var(--red);border-color:rgba(255,59,48,.35)" onclick="reportReject(' + i + ')">退回</button></td></tr>';
    });
    h += '<div class="hint" style="margin-bottom:10px">逐级审阅（MEET-002）：直属主管审阅通过后逐级向上汇总；退回需填写原因，提交人将收到修改提醒。</div>';
    return h + tbl(['日期', '提交人', '类型', '字段完成度', '提交时间', '操作'], rows);
  }
  h += qbar(qs(['全部类型', '直播', '短视频', '运营', '行政']) + qs(['全部状态', '已提交', '草稿', '已补交', '迟交']) + qs(['全部审阅', '待审阅', '已审阅', '已退回'], 90) + '<input type="date" style="width:130px">');
  const stc = { '草稿': 'gray', '已提交': 'blue', '已补交': 'orange', '迟交': 'red' };
  const rvc = { '待审阅': 'orange', '已审阅': 'green', '已退回': 'red', '—': 'gray' };
  const list = qFilter(REPORTS, function (r) { return [r.user, r.type, r.date]; }, function (r) { return r.st + '|' + (r.rvw || '—'); });
  let rows = '';
  list.forEach(function (r) {
    const i = REPORTS.indexOf(r);
    rows += '<tr><td class="num">' + r.date + '</td><td style="font-weight:500">' + sens(r.user) + '</td><td>' + tag(r.type + '日报', 'blue') + '</td>' +
      '<td><div class="rowline">' + pgbar(r.pct, r.pct >= 90 ? 'var(--green)' : r.pct >= 70 ? 'var(--orange)' : 'var(--red)') + '<span class="num" style="font-size:12px">' + r.pct + '%</span></div></td>' +
      '<td class="num" style="font-size:12px;color:var(--text2)">' + r.at + '</td><td>' + tag(r.st, stc[r.st]) + '</td>' +
      '<td>' + tag(r.rvw || '—', rvc[r.rvw || '—']) + '</td>' +
      '<td>' + (r.rvw === '待审阅' ? '<button class="btn btn-pri btn-sm" onclick="reportApprove(' + i + ')">通过</button> <button class="btn btn-sm" style="color:var(--red);border-color:rgba(255,59,48,.35)" onclick="reportReject(' + i + ')">退回</button>' :
        '<span class="btn btn-sec btn-sm" onclick="reportDetail(' + i + ')">查看</span>') + '</td></tr>';
  });
  h += tbl(['日期', '提交人', '类型', '字段完成度', '提交时间', '状态', '审阅状态', '操作'], rows);
  return h;
};
function barsChart(vals) {
  const max = Math.max.apply(null, vals);
  let h = '<div class="bars">';
  vals.forEach(function (v) {
    h += '<div class="b" style="height:' + Math.max(8, Math.round(v / max * 100)) + '%" title="' + v + '"></div>';
  });
  return h + '</div>';
}
/* REPORT：填写今日日报表单 */
function reportWrite() {
  const body = frow([
    { k: 'date', label: '日报日期', type: 'date', val: '2026-09-12' },
    { k: 'type', label: '日报类型', type: 'select', opts: ['直播', '短视频', '运营', '行政'] },
    { k: 'done', label: '今日完成', type: 'textarea', req: true, ph: '按条目列出今日完成事项与关键数据', wide: true },
    { k: 'plan', label: '明日计划', type: 'textarea', ph: '明日重点工作安排', wide: true },
    { k: 'risk', label: '问题与风险', type: 'textarea', ph: '需要协调的资源、暴露的风险', wide: true }
  ]);
  openDrawer('填写今日日报', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="reportWriteSubmit()">保存并提交</button>', '480px');
}
function reportWriteSubmit() {
  if (!formValidate(['done'])) return;
  const user = ROLES[state.role].user;
  const done = $('#F_done').value.trim();
  const plan = $('#F_plan').value.trim() || '';
  const risk = $('#F_risk').value.trim() || '';
  const filled = ['done', 'plan', 'risk'].filter(function (k) { return $('#F_' + k).value.trim(); }).length;
  const pct = Math.round(filled / 3 * 100);
  const no = 'RP20260912-' + String(REPORTS.length + 1).padStart(2, '0');
  REPORTS.unshift({ date: $('#F_date').value || '2026-09-12', user: user, type: $('#F_type').value, pct: pct, at: '09-12 22:30', st: '已提交', rvw: '待审阅' });
  if (state.page === 'report') renderPage();
  formOk(no, '日报已提交 · 字段完成度 ' + pct + '%，已进入直属主管审阅队列', '');
  toast('日报提交成功（完成度 ' + pct + '%）· 已推送主管审阅', 'success');
}
/* MEET-002：日报审阅通过（逐级向上汇总） */
function reportApprove(i) {
  const r = REPORTS[i];
  if (!r) return;
  confirmDlg('确认审阅通过？', r.user + ' 的 ' + r.date + ' ' + r.type + '日报（完成度 ' + r.pct + '%）将通过审阅，并逐级向上汇总至部门负责人。', '通过审阅', function () {
    r.rvw = '已审阅';
    if (state.page === 'report') renderPage();
    toast('日报审阅通过：' + r.user + ' · ' + r.date + '（已逐级汇总）', 'success');
    hlFirst();
  });
}
/* MEET-002：日报审阅退回（需填原因，提交人收到修改提醒） */
function reportReject(i) {
  const r = REPORTS[i];
  if (!r) return;
  const body = frow([
    { k: 'rjreason', label: '退回原因', type: 'select', req: true, opts: ['字段完成度不足（<70%）', '关键数据缺失', '内容与当日工作不符', '格式不规范', '其他'] },
    { k: 'rjnote', label: '退回说明', type: 'textarea', req: true, ph: '具体指出需补充或修改的内容', wide: true }
  ]);
  CF_CB = function () {
    if (!formValidate(['rjreason', 'rjnote'])) return;
    r.rvw = '已退回'; r.st = '已退回';
    if (state.page === 'report') renderPage();
    closeConfirm();
    toast('日报已退回：' + r.user + '（原因：' + $('#F_rjreason').value + '· 已发送修改提醒）', 'warn');
    hlFirst();
  };
  const w = document.createElement('div');
  w.className = 'cfwrap on';
  w.innerHTML = '<div class="cfmask" onclick="closeConfirm()"></div>' +
    '<div class="cfcard" style="width:480px" role="dialog">' +
    '<div class="cf-t"><span class="cf-ic" style="color:var(--red)">' + ic('x', 20) + '</span><b>退回日报 · ' + r.user + ' ' + r.date + '</b></div>' +
    '<div class="cf-m">' + body + '</div>' +
    '<div class="cf-f"><button class="btn btn-sec" onclick="closeConfirm()">取消</button>' +
    '<button class="btn btn-pri" style="background:var(--red)" onclick="doConfirm()">确认退回</button></div></div>';
  document.body.appendChild(w);
}
/* MEET-002：批量通过（待审阅 Tab 页头） */
function reportRvwBatch() {
  const pend = REPORTS.filter(function (r) { return r.rvw === '待审阅'; });
  if (!pend.length) { toast('当前无待审阅日报', 'warn'); return; }
  confirmDlg('批量通过 ' + pend.length + ' 份日报？', '将一次性通过所有待审阅日报（' + pend.map(function (r) { return r.user; }).join('、') + '），并逐级向上汇总。', '批量通过', function () {
    pend.forEach(function (r) { r.rvw = '已审阅'; });
    if (state.page === 'report') renderPage();
    toast('批量审阅通过：' + pend.length + ' 份日报已逐级汇总', 'success');
    hlFirst();
  });
}
/* MEET-002：日报详情抽屉（含审阅流时间线） */
function reportDetail(i) {
  const r = REPORTS[i];
  if (!r) return;
  const rvwc = { '待审阅': 'oo', '已审阅': 'gg', '已退回': 'oo', '—': '' }[r.rvw || '—'];
  const body = '<div class="kv">' +
    '<div><div class="k">提交人</div><div class="v">' + sens(r.user) + '</div></div><div><div class="k">日期 / 类型</div><div class="v">' + r.date + ' · ' + r.type + '日报</div></div>' +
    '<div><div class="k">字段完成度</div><div class="v">' + r.pct + '%</div></div><div><div class="k">提交时间</div><div class="v">' + r.at + '</div></div></div>' +
    '<div class="dsec">审阅流（逐级）</div><div class="tl">' +
    '<div class="tl-i"><div class="tt">提交日报</div><div class="td">' + r.at + ' · ' + r.user + '</div></div>' +
    '<div class="tl-i ' + rvwc + '"><div class="tt">直属主管审阅</div><div class="td">' + (r.rvw === '已退回' ? '已退回 · 原因：字段完成度不足（需补充数据）' : r.rvw === '已审阅' ? '已通过 · 09-12 09:30' : '待审阅') + '</div></div>' +
    '<div class="tl-i ' + (r.rvw === '已审阅' ? 'gg' : '') + '"><div class="tt">部门负责人汇总</div><div class="td">' + (r.rvw === '已审阅' ? '已汇总至部门周报' : '待前级完成') + '</div></div></div>';
  openDrawer('日报详情 · ' + r.user + ' ' + r.date, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (r.rvw === '待审阅' ? '<button class="btn btn-pri" onclick="reportApprove(' + i + ')">通过</button><button class="btn btn-pri" style="background:var(--red)" onclick="reportReject(' + i + ')">退回</button>' : ''));
}

/* ===================== REPORT-001/002/003 数据上报体系 ===================== */
const RTPLS = [
  { no: 'RT-003', name: '抖音电商日度经营数据', fields: 12, freq: '每日 18:00 前', owner: '运营中心', on: true, use: 36, flds: [
    { n: '统计日期', ty: '日期', req: true, rule: '不可晚于当日' },
    { n: 'GMV', ty: '金额', req: true, rule: '≥ 0' },
    { n: '订单数', ty: '整数', req: true, rule: '≥ 0' },
    { n: '退款率', ty: '百分比', req: true, rule: '0~100%' },
    { n: '投放消耗', ty: '金额', req: false, rule: '≥ 0' },
    { n: '备注', ty: '文本', req: false, rule: '≤ 200 字' }
  ] },
  { no: 'RT-002', name: '直播场次复盘数据包', fields: 9, freq: '场次结束 2h 内', owner: '直播运营', on: true, use: 28, flds: [
    { n: '场次 ID', ty: '文本', req: true, rule: 'IMS 编码校验' },
    { n: 'GMV', ty: '金额', req: true, rule: '≥ 0' },
    { n: '峰值在线', ty: '整数', req: true, rule: '≥ 0' },
    { n: '新增粉丝', ty: '整数', req: false, rule: '≥ 0' },
    { n: '复盘结论', ty: '文本', req: true, rule: '≤ 500 字' }
  ] },
  { no: 'RT-001', name: '短视频矩阵周度数据', fields: 15, freq: '每周一 12:00 前', owner: '内容中心', on: true, use: 18, flds: [
    { n: '统计周期', ty: '日期', req: true, rule: '周一校验' },
    { n: '发布条数', ty: '整数', req: true, rule: '≥ 0' },
    { n: '总播放', ty: '整数', req: true, rule: '≥ 0' },
    { n: '完播率', ty: '百分比', req: true, rule: '0~100%' },
    { n: '备注', ty: '文本', req: false, rule: '≤ 200 字' }
  ] },
  { no: 'RT-004', name: '竞品动向采集表', fields: 8, freq: '每周五 18:00 前', owner: '数据中心', on: true, use: 7, flds: [
    { n: '竞品名称', ty: '文本', req: true, rule: '非空' },
    { n: '动态类型', ty: '枚举', req: true, rule: '预置枚举值' },
    { n: '影响评估', ty: '文本', req: true, rule: '≤ 300 字' },
    { n: '信息来源', ty: '文本', req: false, rule: 'URL 格式' }
  ] },
  { no: 'RT-005', name: '达人合作效果追踪', fields: 11, freq: '活动结束 24h 内', owner: '商务外协', on: false, use: 4, flds: [
    { n: '达人昵称', ty: '文本', req: true, rule: '非空' },
    { n: '合作场次', ty: '文本', req: true, rule: 'IMS 编码校验' },
    { n: '带货 GMV', ty: '金额', req: true, rule: '≥ 0' },
    { n: '佣金结算', ty: '金额', req: false, rule: '≥ 0' }
  ] }
];
const UPLOADS = [
  { no: 'UP20260918-012', tpl: 'RT-003 抖音日度经营', by: '赵敏', ct: '2026-09-18 17:20', rows: 86, st: '待审核' },
  { no: 'UP20260918-011', tpl: 'RT-002 直播复盘', by: '孙倩', ct: '2026-09-18 15:40', rows: 14, st: '待审核' },
  { no: 'UP20260917-010', tpl: 'RT-003 抖音日度经营', by: '赵敏', ct: '2026-09-17 17:55', rows: 84, st: '已通过' },
  { no: 'UP20260916-009', tpl: 'RT-003 抖音日度经营', by: '陈默', ct: '2026-09-16 19:12', rows: 82, st: '已退回' },
  { no: 'UP20260915-008', tpl: 'RT-001 短视频周度', by: '孙倩', ct: '2026-09-15 11:30', rows: 55, st: '已通过' },
  { no: 'UP20260914-007', tpl: 'RT-004 竞品动向', by: '陈默', ct: '2026-09-14 17:48', rows: 22, st: '已通过' },
  { no: 'UP20260913-006', tpl: 'RT-002 直播复盘', by: '何舟', ct: '2026-09-13 22:05', rows: 11, st: '已通过' }
];
function reportUploadTab() {
  const cur = state.gc.rpttab || '上报模板';
  let h = '';
  h += '<div class="cattabs">' + ['上报模板', '上报记录', '完成率'].map(function (t) {
    const pend = UPLOADS.filter(function (u) { return u.st === '待审核'; }).length;
    return '<div class="cattab' + (cur === t ? ' on' : '') + '" onclick="setGc(\'rpttab\',\'' + t + '\')">' + t + (t === '上报记录' && pend ? ' <span class="cbadge" style="background:var(--orange)">' + pend + '</span>' : '') + '</div>';
  }).join('') + '</div>';
  if (cur === '上报模板') return h + reportTplTab();
  if (cur === '完成率') return h + reportRateTab();
  return h + reportUploadListTab();
}
/* REPORT-001：上报模板配置 */
function reportTplTab() {
  const tsc = { '每日 18:00 前': 'blue', '场次结束 2h 内': 'orange', '每周一 12:00 前': 'cyan', '每周五 18:00 前': 'cyan', '活动结束 24h 内': 'purple' };
  let rows = '';
  RTPLS.forEach(function (t, i) {
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + t.no + '</td><td style="font-weight:500">' + t.name + '</td>' +
      '<td class="num">' + t.fields + ' 字段</td>' +
      '<td>' + tag(t.freq, tsc[t.freq] || 'gray') + '</td><td>' + t.owner + '</td><td class="num">' + t.use + ' 次</td>' +
      '<td><span class="sw' + (t.on ? ' on' : '') + '" onclick="this.classList.toggle(\'on\');toast(\'模板已' + (t.on ? '停用' : '启用') + '\',\'success\')"><i></i></span></td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="reportTplEdit(' + i + ')">编辑</span></td></tr>';
  });
  return '<div class="hint" style="margin-bottom:10px">模板字段配置后，上报人按模板逐项填报（REPORT-001）；提交进入审核流，审核不通过将被退回补充（REPORT-003）。</div>' +
    tbl(['模板编号', '模板名称', '字段数', '上报频率', '责任部门', '累计使用', '启停', '操作'], rows);
}
function reportTplEdit(i) {
  const t = RTPLS[i];
  const fldRows = t.flds.map(function (f, j) {
    return '<tr><td style="font-weight:500"><span class="mono" style="font-size:10.5px;color:var(--text2)">F' + String(j + 1).padStart(2, '0') + '</span> ' + f.n + '</td>' +
      '<td>' + f.ty + '</td>' +
      '<td><span class="sw' + (f.req ? ' on' : '') + '" onclick="reportFldToggle(' + i + ',' + j + ',this)"><i></i></span></td>' +
      '<td style="font-size:11.5px;color:var(--text2)">' + f.rule + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="reportFldEdit(' + i + ',' + j + ')">编辑</span></td>' +
      '<td>' + (j > 0 ? '<span class="btn btn-sec btn-sm" style="padding:2px 8px" onclick="reportFldMove(' + i + ',' + j + ',-1)" title="上移">↑</span> ' : '') +
      (j < t.flds.length - 1 ? '<span class="btn btn-sec btn-sm" style="padding:2px 8px" onclick="reportFldMove(' + i + ',' + j + ',1)" title="下移">↓</span>' : '') + '</td>' +
      '<td><span class="btn btn-sm" style="color:var(--red);border-color:rgba(255,59,48,.35)" onclick="reportFldDel(' + i + ',' + j + ')">删除</span></td></tr>';
  }).join('');
  const body = frow([
    { k: 'tname', label: '模板名称', type: 'text', req: true, val: t.name },
    { k: 'tfreq', label: '上报频率', type: 'select', req: true, opts: ['每日 18:00 前', '场次结束 2h 内', '每周一 12:00 前', '每周五 18:00 前', '活动结束 24h 内'] },
    { k: 'towner', label: '责任部门', type: 'select', opts: ['运营中心', '直播运营', '内容中心', '数据中心', '商务外协'] }
  ]) + '<div class="dsec">字段列表（' + t.flds.length + ' 个 · 字段级编辑：增删改 / 必填切换 / 排序）</div>' +
    '<div class="tbl-wrap"><table><thead><tr><th>字段名</th><th>类型</th><th>必填</th><th>校验规则</th><th>操作</th><th>排序</th><th></th></tr></thead><tbody>' +
    fldRows +
    '<tr><td colspan="7" style="padding:6px"><span class="btn btn-sec btn-sm" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="reportFldAdd(' + i + ')">' + ic('plus', 13) + '新增字段</span></td></tr></tbody></table></div>' +
    '<div class="hint" style="margin-top:6px">字段修改保存后立即对后续上报生效；已提交的上报单仍按提交时模板校验。</div>';
  openDrawer('编辑上报模板 · ' + t.no, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="reportTplSave(' + i + ')">保存模板</button>', '640px');
}
/* REPORT：字段必填切换 */
function reportFldToggle(i, j, sw) {
  const f = RTPLS[i].flds[j];
  if (!f) return;
  sw.classList.toggle('on');
  f.req = !f.req;
  toast('字段「' + f.n + '」已切换为' + (f.req ? '必填' : '选填'), 'success');
}
/* REPORT：字段排序（上移/下移） */
function reportFldMove(i, j, dir) {
  const flds = RTPLS[i].flds;
  const k = j + dir;
  if (k < 0 || k >= flds.length) return;
  const tmp = flds[j]; flds[j] = flds[k]; flds[k] = tmp;
  reportTplEdit(i);
  toast('字段已' + (dir < 0 ? '上移' : '下移') + '：' + flds[k].n, 'success');
}
/* REPORT：删除字段（确认） */
function reportFldDel(i, j) {
  const t = RTPLS[i];
  const f = t.flds[j];
  if (!f) return;
  confirmDlg('删除字段「' + f.n + '」？', '模板 ' + t.no + ' 将移除该字段（' + f.ty + (f.req ? ' · 必填' : '') + '），已提交的上报单不受影响。', '确认删除', function () {
    t.flds.splice(j, 1);
    t.fields = t.flds.length;
    if (state.page === 'report') renderPage();
    reportTplEdit(i);
    toast('字段已删除：' + f.n + '（剩余 ' + t.flds.length + ' 个字段）', 'success');
  }, { danger: true });
}
/* REPORT：新增字段表单 */
function reportFldAdd(i) {
  const t = RTPLS[i];
  const body = frow([
    { k: 'fn', label: '字段名', type: 'text', req: true, ph: '如：客单价' },
    { k: 'ft', label: '字段类型', type: 'select', req: true, opts: ['文本', '整数', '金额', '百分比', '日期', '枚举'] },
    { k: 'frq', label: '是否必填', type: 'pills', opts: ['必填', '选填'], val: '必填' },
    { k: 'frule', label: '校验规则', type: 'text', ph: '如：≥ 0 或 0~100%（选填）', wide: true }
  ]);
  openDrawer('新增字段 · ' + t.no, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="reportFldAddOk(' + i + ')">添加字段</button>', '440px');
}
function reportFldAddOk(i) {
  const t = RTPLS[i];
  if (!formValidate(['fn', 'ft'])) return;
  t.flds.push({ n: $('#F_fn').value.trim(), ty: $('#F_ft').value, req: $('#F_frq') ? ($('#F_frq').value === '必填') : true, rule: ($('#F_frule').value || '').trim() || '无特殊校验' });
  t.fields = t.flds.length;
  if (state.page === 'report') renderPage();
  closeDrawer();
  reportTplEdit(i);
  toast('字段已添加：' + t.flds[t.flds.length - 1].n + '（共 ' + t.flds.length + ' 个字段）', 'success');
}
/* REPORT：编辑单个字段 */
function reportFldEdit(i, j) {
  const t = RTPLS[i];
  const f = t.flds[j];
  if (!f) return;
  const body = frow([
    { k: 'fn', label: '字段名', type: 'text', req: true, val: f.n },
    { k: 'ft', label: '字段类型', type: 'select', req: true, opts: ['文本', '整数', '金额', '百分比', '日期', '枚举'], val: f.ty },
    { k: 'frq', label: '是否必填', type: 'pills', opts: ['必填', '选填'], val: f.req ? '必填' : '选填' },
    { k: 'frule', label: '校验规则', type: 'text', val: f.rule === '无特殊校验' ? '' : f.rule, ph: '如：≥ 0 或 0~100%（选填）', wide: true }
  ]);
  openDrawer('编辑字段 F' + String(j + 1).padStart(2, '0') + ' · ' + t.no, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="reportFldEditOk(' + i + ',' + j + ')">保存字段</button>', '440px');
}
function reportFldEditOk(i, j) {
  const t = RTPLS[i];
  const f = t.flds[j];
  if (!f) return;
  if (!formValidate(['fn', 'ft'])) return;
  const old = f.n;
  f.n = $('#F_fn').value.trim();
  f.ty = $('#F_ft').value;
  f.req = $('#F_frq') ? ($('#F_frq').value === '必填') : f.req;
  f.rule = ($('#F_frule').value || '').trim() || '无特殊校验';
  closeDrawer();
  reportTplEdit(i);
  toast('字段已更新：' + old + (old !== f.n ? ' → ' + f.n : '') + '（' + f.ty + (f.req ? ' · 必填' : '') + '）', 'success');
}
function reportTplSave(i) {
  if (!formValidate(['tname'])) return;
  closeDrawer();
  toast('模板已保存：' + RTPLS[i].no + ' · ' + $('#F_tname').value.trim() + '（字段校验规则同步生效）', 'success');
}
function reportTplAdd() {
  const body = frow([
    { k: 'nname', label: '模板名称', type: 'text', req: true, ph: '如：私域转化追踪表' },
    { k: 'nfreq', label: '上报频率', type: 'select', req: true, opts: ['每日 18:00 前', '场次结束 2h 内', '每周一 12:00 前', '每周五 18:00 前', '活动结束 24h 内'] },
    { k: 'nowner', label: '责任部门', type: 'select', req: true, opts: ['运营中心', '直播运营', '内容中心', '数据中心', '商务外协'] },
    { k: 'nfields', label: '初始字段数', type: 'num', unit: '个', val: 8 }
  ]);
  openDrawer('新建上报模板', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="reportTplAddSubmit()">创建模板</button>', '480px');
}
function reportTplAddSubmit() {
  if (!formValidate(['nname', 'nfreq', 'nowner'])) return;
  const no = 'RT-' + String(RTPLS.length + 1).padStart(3, '0');
  RTPLS.unshift({ no: no, name: $('#F_nname').value.trim(), fields: Number($('#F_nfields').value || 8), freq: $('#F_nfreq').value, owner: $('#F_nowner').value, on: true, use: 0 });
  if (state.page === 'report') renderPage();
  formOk(no, '上报模板已创建并启用，上报人将按模板字段逐项填报', '');
  toast('上报模板创建成功：' + no, 'success');
}
/* REPORT-002：数据提交 + REPORT-003：审核退回 */
function reportSubmitData() {
  const tOpts = RTPLS.filter(function (t) { return t.on; }).map(function (t) { return t.no + ' · ' + t.name; });
  const body = frow([
    { k: 'utpl', label: '选择模板', type: 'select', req: true, opts: tOpts.length ? tOpts : ['（暂无启用模板）'] },
    { k: 'udate', label: '数据日期', type: 'date', req: true, val: '2026-09-18' },
    { k: 'ufile', label: '数据附件', type: 'file', ph: '点击上传 CSV / Excel（可选，支持在线填报）', wide: true },
    { k: 'urows', label: '数据行数', type: 'num', unit: '行', val: 86 },
    { k: 'unote', label: '数据说明', type: 'textarea', ph: '口径变化、异常波动说明（选填）', wide: true }
  ]) + '<div class="hint" style="margin-top:4px">提交后进入数据审核流：校验字段完整性与口径 → 通过入仓数据中心 → 不通过将退回并要求补充（REPORT-003）。</div>';
  openDrawer('提交上报数据', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="reportSubmitDataOk()">提交并送审</button>', '520px');
}
function reportSubmitDataOk() {
  if (!formValidate(['utpl', 'udate', 'urows'])) return;
  const no = 'UP20260918-' + String(UPLOADS.length + 1).padStart(3, '0');
  UPLOADS.unshift({ no: no, tpl: $('#F_utpl').value.split(' · ')[1] || $('#F_utpl').value, by: ROLES[state.role].user, ct: '2026-09-18 17:30', rows: Number($('#F_urows').value || 0), st: '待审核' });
  if (state.page === 'report') renderPage();
  formOk(no, '上报数据已提交（待审核），审核通过后将写入数据中心', '');
  toast('数据上报成功：' + no + ' · ' + UPLOADS[0].rows + ' 行', 'success');
}
function reportUploadListTab() {
  const stc = { '待审核': 'orange', '已通过': 'green', '已退回': 'red' };
  let rows = '';
  UPLOADS.forEach(function (u, i) {
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + u.no + '</td><td style="font-weight:500">' + u.tpl + '</td><td>' + sens(u.by) + '</td>' +
      '<td class="num" style="font-size:12px;color:var(--text2)">' + u.ct + '</td><td class="num">' + u.rows + ' 行</td>' +
      '<td>' + tag(u.st, stc[u.st]) + '</td>' +
      '<td>' + (u.st === '待审核' ? '<button class="btn btn-pri btn-sm" onclick="reportUplAudit(' + i + ',1)">通过</button> <button class="btn btn-sm" style="color:var(--red);border-color:rgba(255,59,48,.35)" onclick="reportUplAudit(' + i + ',0)">退回</button>' :
        '<span class="btn btn-sec btn-sm" onclick="reportUplDetail(' + i + ')">查看</span>') + '</td></tr>';
  });
  return qbar(qi('上报单号', 130) + qi('提交人', 100) + qs(['全部状态', '待审核', '已通过', '已退回'], 90)) +
    tbl(['上报单号', '模板', '提交人', '提交时间', '数据量', '状态', '操作'], rows);
}
function reportUplAudit(i, pass) {
  const u = UPLOADS[i];
  if (!u) return;
  if (pass) {
    confirmDlg('确认审核通过？', '上报单 ' + u.no + '（' + u.tpl + ' · ' + u.rows + ' 行）字段校验全部通过，数据将写入数据中心并同步 BI 报表。', '通过入仓', function () {
      u.st = '已通过';
      if (state.page === 'report') renderPage();
      toast('上报审核通过：' + u.no + '（已写入数据中心）', 'success');
      hlFirst();
    });
  } else {
    const body = frow([
      { k: 'ureason', label: '退回原因', type: 'select', req: true, opts: ['关键字段缺失', '数据口径不一致', '数值异常（超出阈值）', '附件格式错误', '其他'] },
      { k: 'unote2', label: '退回说明', type: 'textarea', req: true, ph: '具体指出需修正的字段与期望值', wide: true }
    ]);
    CF_CB = function () {
      if (!formValidate(['ureason', 'unote2'])) return;
      u.st = '已退回';
      if (state.page === 'report') renderPage();
      closeConfirm();
      toast('上报已退回：' + u.no + '（原因：' + $('#F_ureason').value + '），提交人需在 24h 内补充重报', 'warn');
      hlFirst();
    };
    const w = document.createElement('div');
    w.className = 'cfwrap on';
    w.innerHTML = '<div class="cfmask" onclick="closeConfirm()"></div>' +
      '<div class="cfcard" style="width:480px" role="dialog">' +
      '<div class="cf-t"><span class="cf-ic" style="color:var(--red)">' + ic('x', 20) + '</span><b>退回上报 · ' + u.no + '</b></div>' +
      '<div class="cf-m">' + body + '</div>' +
      '<div class="cf-f"><button class="btn btn-sec" onclick="closeConfirm()">取消</button>' +
      '<button class="btn btn-pri" style="background:var(--red)" onclick="doConfirm()">确认退回</button></div></div>';
    document.body.appendChild(w);
  }
}
function reportUplDetail(i) {
  const u = UPLOADS[i];
  if (!u) return;
  const body = '<div class="kv">' +
    '<div><div class="k">上报单号</div><div class="v mono">' + u.no + '</div></div><div><div class="k">模板</div><div class="v">' + u.tpl + '</div></div>' +
    '<div><div class="k">提交人</div><div class="v">' + sens(u.by) + '</div></div><div><div class="k">提交时间</div><div class="v">' + u.ct + '</div></div>' +
    '<div><div class="k">数据量</div><div class="v">' + u.rows + ' 行</div></div><div><div class="k">状态</div><div class="v">' + u.st + '</div></div></div>' +
    '<div class="dsec">字段抽检（前 5 项）</div><div class="tbl-wrap"><table><thead><tr><th>字段</th><th>样本值</th><th>校验</th></tr></thead><tbody>' +
    '<tr><td>统计日期</td><td>2026-09-18</td><td>' + tag('通过', 'green') + '</td></tr>' +
    '<tr><td>GMV</td><td>¥186,400.00</td><td>' + tag('通过', 'green') + '</td></tr>' +
    '<tr><td>订单数</td><td>1,226</td><td>' + tag('通过', 'green') + '</td></tr>' +
    '<tr><td>退款率</td><td>4.2%</td><td>' + tag('通过', 'green') + '</td></tr>' +
    '<tr><td>投放消耗</td><td>¥12,000.00</td><td>' + tag('通过', 'green') + '</td></tr></tbody></table></div>';
  openDrawer('上报详情 · ' + u.no, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>');
}
/* REPORT-004：上报完成率统计 */
function reportRateTab() {
  const today = UPLOADS.filter(function (u) { return u.no.indexOf('20260918') >= 0; }).length;
  const passed = UPLOADS.filter(function (u) { return u.st === '已通过'; }).length;
  const rate = Math.round(passed / Math.max(UPLOADS.length, 1) * 100);
  return '<div class="g4"><div class="card stat"><span class="l">今日上报</span><div class="n" style="color:var(--blue)">' + today + ' 单</div><div class="d">BR-106 每日上报完成</div></div>' +
    '<div class="card stat"><span class="l">通过率</span><div class="n" style="color:var(--green)">' + rate + '%</div><div class="d">退回 ' + UPLOADS.filter(function (u) { return u.st === '已退回'; }).length + ' 单</div></div>' +
    '<div class="card stat"><span class="l">字段校验命中率</span><div class="n">96.8%</div><div class="d">口径校验 + 阈值校验</div></div>' +
    '<div class="card stat"><span class="l">平均审核时长</span><div class="n">1.8h</div><div class="d">超 4h 自动催办</div></div></div>' +
    '<div class="sec">近 7 天上报量与通过量</div><div class="card">' + barsChart([22, 25, 24, 26, 23, 28, 27]) + barsChart([20, 24, 22, 25, 23, 27, 26]) + '</div>' +
    '<div class="rowline" style="gap:14px;margin-top:6px"><span style="font-size:11.5px;color:var(--blue)">■ 上报量</span><span style="font-size:11.5px;color:var(--green)">■ 通过量</span></div>';
}

/* ===================== 14 FLOW 工作流 ===================== */
const FLOWS = [
  { id: 'FL20260912-08', type: '账号领用', from: '赵敏', node: '行政确认', approver: '林岚', cost: '4h', st: '审批中', chain: ['发起申请', '行政确认', '账号分配', '归档'], ni: 1 },
  { id: 'FL20260912-07', type: '报销', from: '孙倩', node: '财务复核', approver: '周晴', cost: '26h', st: '超时', chain: ['提交报销', '财务复核', '出纳付款', '归档'], ni: 1 },
  { id: 'FL20260911-15', type: '开播审批', from: '赵敏', node: '风控复核', approver: '何舟', cost: '2h', st: '审批中', chain: ['开播登记', '风控复核', '总监审批', '确认开播'], ni: 1 },
  { id: 'FL20260911-12', type: '内容审核', from: '孙倩', node: '一审通过', approver: '李澈', cost: '1h', st: '已完成', chain: ['提交审核', '一审', '合规复检', '发布'], ni: 3 },
  { id: 'FL20260910-21', type: '请假', from: '李澈', node: '主管审批', approver: '孙倩', cost: '5h', st: '已完成', chain: ['提交申请', '主管审批', 'HR 备案'], ni: 2 },
  { id: 'FL20260910-18', type: '报销', from: '何舟', node: '出纳付款', approver: '周晴', cost: '48h', st: '超时', chain: ['提交报销', '财务复核', '出纳付款', '归档'], ni: 2 },
  { id: 'FL20260909-33', type: '账号领用', from: '苏杳', node: '已领用', approver: '林岚', cost: '3h', st: '已完成', chain: ['发起申请', '行政确认', '账号分配', '归档'], ni: 3 },
  { id: 'FL20260909-30', type: '开播审批', from: '何舟', node: '总监审批', approver: 'Donny', cost: '6h', st: '已完成', chain: ['开播登记', '风控复核', '总监审批', '确认开播'], ni: 2 },
  { id: 'FL20260908-41', type: '内容审核', from: '王野', node: '合规复检', approver: '李澈', cost: '18h', st: '已驳回', chain: ['提交审核', '一审', '合规复检', '发布'], ni: 2 }
];
PAGES.flow = function () {
  const cur = state.tab.flow || '全部';
  const isTpl = cur === '模板管理';
  const isKb = cur === '看板视图';
  let h = pgHead('flow', isTpl ? '<button class="btn btn-pri" onclick="flowTplNew()">' + ic('plus', 15) + '新建流程模板</button>' :
    '<button class="btn btn-sec" onclick="flowUrgeBatch()">批量催办</button>' +
    '<button class="btn btn-pri" onclick="flowAdd()">' + ic('plus', 15) + '发起流程</button>');
  h += '<div class="tabs">' + ['全部', '请假', '领用', '报销', '开播审批', '内容审核', '看板视图', '模板管理'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'flow\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  if (isTpl) return h + flowTplTab();
  if (isKb) return h + flowKanbanTab();
  const cats = ['全部', '请假', '领用', '报销', '开播审批', '内容审核'];
  const cmap = { '请假': 'cal', '领用': 'user', '报销': 'yuan', '开播审批': 'video', '内容审核': 'film' };
  const ctag = { '请假': 'blue', '领用': 'cyan', '报销': 'green', '开播审批': 'purple', '内容审核': 'orange' };
  h += '<div class="g2r"><div><div class="card" style="padding:12px">';
  cats.forEach(function (c) {
    const n = c === '全部' ? FLOWS.length : FLOWS.filter(function (f) { return f.type === (c === '领用' ? '账号领用' : c); }).length;
    h += '<div class="mg-i" style="border-radius:8px;' + (cur === c ? 'background:var(--blue-bg);color:var(--blue)' : '') + '" onclick="setTab(\'flow\',\'' + c + '\')">' +
      '<span style="margin-top:1px">' + ic(c === '全部' ? 'flow' : cmap[c], 16) + '</span><div style="flex:1" class="' + (cur === c ? 'mt' : '') + '" style="font-size:13px' + (cur === c ? ';color:var(--blue);font-weight:600' : '') + '"><span style="font-size:13px' + (cur === c ? ';color:var(--blue);font-weight:600' : '') + '">' + c + '</span></div><span style="font-size:11.5px;color:var(--text2)">' + n + '</span></div>';
  });
  h += '</div><div class="card" style="margin-top:14px;box-shadow:none;border:1px dashed var(--line2)"><div class="rowline" style="gap:8px"><span style="color:var(--orange)">' + ic('clock', 16) + '</span><b style="font-size:12.5px">超时流程 2 条</b></div><div class="hint">超 24h 未流转自动升级提醒至上级</div></div></div>';
  h += '<div><div style="display:flex;gap:8px;margin-bottom:12px;align-items:center"><b style="font-size:13px">流程列表' + (cur !== '全部' ? ' · ' + cur : '') + '</b><span class="sp" style="flex:1"></span>' + qbar(qi('流程编号', 130) + qs(['全部状态', '审批中', '超时', '已完成', '已驳回'])) + '</div>';
  const stc = { '审批中': 'blue', '超时': 'red', '已完成': 'green', '已驳回': 'gray' };
  let rows = '';
  FLOWS.filter(function (f) { return cur === '全部' || f.type === (cur === '领用' ? '账号领用' : cur); }).forEach(function (f) {
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + f.id + '</td><td>' + tag(f.type, ctag[f.type]) + '</td><td style="font-weight:500">' + sens(f.from) + '</td><td>' + f.node + '</td><td>' + sens(f.approver) + '</td>' +
      '<td class="num"><span class="' + (f.st === '超时' ? 'neg' : '') + '" style="' + (f.st === '超时' ? '' : 'color:var(--text2)') + '">' + f.cost + '</span></td>' +
      '<td>' + tag(f.st, stc[f.st]) + '</td>' +
      '<td>' + (f.st === '审批中' || f.st === '超时' ? '<button class="btn btn-sec btn-sm" onclick="urge(\'' + f.id + '\',\'' + f.approver + '\')"><span style="color:var(--orange)">' + ic('bell', 13) + '</span>催办</button>' : '<span style="font-size:12px;color:var(--text2)">—</span>') + '</td></tr>';
  });
  h += tbl(['流程编号', '类型', '发起人', '当前节点', '审批人', '耗时', '状态', '操作'], rows) + '</div></div>';
  return h;
};
function urge(id, who) {
  confirmDlg('确认发送催办？', '将向当前审批人 <b>' + who + '</b> 发送流程 ' + id + ' 的催办提醒（站内 + 钉钉）。', '发送催办', function () {
    toast('催办已发送：' + id + ' → ' + who, 'success');
  });
}
/* FLOW：批量催办（勾选列表确认弹窗） */
function flowUrgeBatch() {
  const pend = FLOWS.filter(function (f) { return f.st === '审批中' || f.st === '超时'; }).slice(0, 5);
  if (!pend.length) { toast('当前无待催办流程', 'warn'); return; }
  CF_CB = function () {
    const sel = document.querySelectorAll('#cfwrap .urgei input:checked').length;
    toast('批量催办已发送：' + (sel || pend.length) + ' 条流程已提醒对应审批人', 'success');
  };
  const w = document.createElement('div');
  w.id = 'cfwrap';
  w.className = 'cfwrap on';
  w.innerHTML = '<div class="cfmask" onclick="closeConfirm()"></div>' +
    '<div class="cfcard" style="width:480px" role="dialog">' +
    '<div class="cf-t"><span class="cf-ic">' + ic('bell', 20) + '</span><b>批量催办（' + pend.length + ' 条）</b></div>' +
    '<div class="cf-m" style="margin-top:10px;padding:0">将向以下流程的当前审批人发送催办提醒：</div>' +
    '<div class="urgets">' + pend.map(function (f) {
      return '<label class="urgei"><input type="checkbox" checked onchange="flowUrgeCount()"><span class="mono" style="font-size:12px">' + f.id + '</span><span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + f.type + ' · ' + f.node + '</span>' + tag(f.approver, 'blue') + '</label>';
    }).join('') + '</div>' +
    '<div class="cf-f"><button class="btn btn-sec" onclick="closeConfirm()">取消</button>' +
    '<button class="btn btn-pri" onclick="doConfirm()">发送催办</button></div></div>';
  document.body.appendChild(w);
}
function flowUrgeCount() {
  const n = document.querySelectorAll('#cfwrap .urgei input:checked').length;
  const b = document.querySelector('#cfwrap .cf-f .btn-pri');
  if (b) b.textContent = '发送催办（' + n + '）';
  CF_CB = function () {
    const sel = document.querySelectorAll('#cfwrap .urgei input:checked').length;
    toast('批量催办已发送：' + sel + ' 条流程已提醒对应审批人', 'success');
  };
}
/* FLOW：发起流程表单 */
function flowAdd() {
  const body = frow([
    { k: 'type', label: '流程类型', type: 'select', opts: ['请假', '领用', '报销', '开播审批', '内容审核'] },
    { k: 'note', label: '发起说明', type: 'textarea', req: true, ph: '说明事由、金额、时长等关键信息', wide: true },
    { k: 'file', label: '附件', type: 'file', ph: '点击上传附件（凭证 / 证明材料）', wide: true }
  ]) + '<div class="hint" style="margin-top:4px">提交后将按流程类型自动路由至对应审批链（主管 → 职能 → 归档）</div>';
  openDrawer('发起流程', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="flowAddSubmit()">提交并进入审批</button>', '480px');
}
function flowAddSubmit() {
  if (!formValidate(['note'])) return;
  const no = 'FL20260912-' + String(FLOWS.length + 1).padStart(2, '0');
  const type = $('#F_type').value;
  const chainMap = { '请假': ['提交申请', '主管审批', 'HR 备案'], '账号领用': ['发起申请', '行政确认', '账号分配', '归档'], '报销': ['提交报销', '财务复核', '出纳付款', '归档'], '开播审批': ['开播登记', '风控复核', '总监审批', '确认开播'], '内容审核': ['提交审核', '一审', '合规复检', '发布'] };
  FLOWS.unshift({ id: no, type: type === '领用' ? '账号领用' : type, from: ROLES[state.role].user, node: '主管审批', approver: '何舟', cost: '0h', st: '审批中', chain: chainMap[type === '领用' ? '账号领用' : type] || ['提交', '审批', '归档'], ni: 1 });
  if (state.page === 'flow') renderPage();
  formOk(no, '流程已进入「主管审批」节点（审批人：何舟），可在流程列表跟踪进度', '');
  toast('流程发起成功：' + no, 'success');
}

/* ===================== FLOW-001/003 工作流模板设计器与版本管理 ===================== */
const FTPLS = [
  { no: 'FT-001', name: '账号领用审批流', nodes: ['发起申请', '行政确认', '账号分配', '归档'], timeout: '24h/节点', ver: 'v3', vers: 3, on: true, use: 46 },
  { no: 'FT-002', name: '开播审批流', nodes: ['开播登记', '风控复核', '总监审批', '确认开播'], timeout: '2h/节点', ver: 'v2', vers: 2, on: true, use: 38 },
  { no: 'FT-003', name: '费用报销流', nodes: ['提交报销', '财务复核', '出纳付款', '归档'], timeout: '48h/节点', ver: 'v4', vers: 4, on: true, use: 62 },
  { no: 'FT-004', name: '内容审核流', nodes: ['提交审核', '一审', '合规复检', '发布'], timeout: '12h/节点', ver: 'v2', vers: 2, on: true, use: 55 },
  { no: 'FT-005', name: '请假审批流', nodes: ['提交申请', '主管审批', 'HR 备案'], timeout: '24h/节点', ver: 'v1', vers: 1, on: true, use: 29 },
  { no: 'FT-006', name: '外协合作协议流', nodes: ['提交协议', '法务审核', '总监会签', '盖章归档'], timeout: '72h/节点', ver: 'v1', vers: 1, on: false, use: 3 }
];
/* FLOW-001：模板管理 Tab */
function flowTplTab() {
  let rows = '';
  FTPLS.forEach(function (t, i) {
    const chain = t.nodes.map(function (n, j) {
      return '<span style="font-size:11px;padding:2px 8px;border:1px solid var(--line2);border-radius:10px;white-space:nowrap' + (j === t.nodes.length - 1 ? ';color:var(--green)' : '') + '">' + n + '</span>' + (j < t.nodes.length - 1 ? '<span style="color:var(--text2);font-size:10px">→</span>' : '');
    }).join('');
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + t.no + '</td><td style="font-weight:500">' + t.name + '</td>' +
      '<td style="max-width:230px"><div class="rowline" style="gap:3px;flex-wrap:wrap">' + chain + '</div></td>' +
      '<td class="num" style="font-size:12px">' + t.timeout + '</td>' +
      '<td><span class="chip" style="cursor:pointer" onclick="flowTplVer(' + i + ')">' + t.ver + '</span><span style="font-size:11px;color:var(--text2)">（' + t.vers + ' 版）</span></td>' +
      '<td class="num">' + t.use + '</td>' +
      '<td><span class="sw' + (t.on ? ' on' : '') + '" onclick="this.classList.toggle(\'on\');toast(\'模板已' + (t.on ? '停用' : '启用') + '\',\'success\')"><i></i></span></td>' +
      '<td><span class="btn btn-pri btn-sm" onclick="flowTplDesign(' + i + ')">设计器</span></td></tr>';
  });
  return '<div class="hint" style="margin-bottom:10px">流程模板由节点编排器设计（FLOW-001），每次保存自动生成新版本并可回滚（FLOW-003）；在用模板修改后，进行中的流程仍按旧版本执行完毕。</div>' +
    tbl(['模板编号', '模板名称', '节点链（点击版本号查历史）', '超时规则', '版本', '累计发起', '启停', '操作'], rows);
}
/* FLOW-001：模板设计器抽屉（节点编排） */
function flowTplDesign(i) {
  const t = FTPLS[i];
  const nodeHtml = t.nodes.map(function (n, j) {
    return '<div style="position:relative">' +
      '<div class="card" style="box-shadow:none;border:1.5px solid var(--blue);padding:10px 12px;margin:0 0 4px;cursor:pointer" onclick="toast(\'节点配置：' + n + '（审批人/表单/条件分支）· 原型示意\',\'success\')">' +
      '<div class="rowline" style="justify-content:space-between"><b style="font-size:13px">' + (j + 1) + '. ' + n + '</b>' + ic('gear', 14) + '</div>' +
      '<div class="hint" style="margin-top:2px">' + (j === 0 ? '发起节点 · 填写表单' : j === t.nodes.length - 1 ? '结束节点 · 自动归档' : '审批节点 · ' + t.timeout + ' 超时升级') + '</div></div>' +
      (j < t.nodes.length - 1 ? '<div style="text-align:center;color:var(--blue);font-size:13px;line-height:1">↓</div>' : '') + '</div>';
  }).join('');
  const body = frow([
    { k: 'fname', label: '模板名称', type: 'text', req: true, val: t.name },
    { k: 'ftimeout', label: '节点超时', type: 'select', opts: ['2h/节点', '12h/节点', '24h/节点', '48h/节点', '72h/节点'] }
  ]) + '<div class="dsec">节点编排（点击节点配置 · FLOW-001）</div>' +
    '<div style="max-height:300px;overflow-y:auto;padding:4px 2px">' + nodeHtml + '</div>' +
    '<div class="rowline" style="gap:8px;margin-top:6px">' +
    '<span class="btn btn-sec btn-sm" onclick="toast(\'新增节点（原型示意）：将插入「条件分支/并行会签」节点\',\'success\')">+ 新增节点</span>' +
    '<span class="btn btn-sec btn-sm" onclick="toast(\'调整顺序（原型示意）：拖拽节点上下移动\',\'success\')">调整顺序</span></div>' +
    '<div class="hint" style="margin-top:8px">保存将生成新版本 ' + t.ver.replace(/v(\d+)/, function (m, d) { return 'v' + (Number(d) + 1); }) + '（FLOW-003），历史版本可回滚。</div>';
  openDrawer('流程模板设计器 · ' + t.no + ' ' + t.name, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button>' +
    '<button class="btn btn-sec" onclick="flowTplVer(' + i + ')">版本历史</button>' +
    '<button class="btn btn-pri" onclick="flowTplSave(' + i + ')">保存为新版本</button>', '560px');
}
function flowTplSave(i) {
  const t = FTPLS[i];
  if (!formValidate(['fname'])) return;
  const newVer = t.ver.replace(/v(\d+)/, function (m, d) { return 'v' + (Number(d) + 1); });
  t.name = $('#F_fname').value.trim();
  t.ver = newVer; t.vers += 1;
  if (state.page === 'flow') renderPage();
  closeDrawer();
  toast('模板已保存：' + t.no + ' · ' + t.name + ' ' + newVer + '（第 ' + t.vers + ' 版 · 进行中流程按旧版执行）', 'success');
  hlFirst();
}
/* FLOW-003：版本管理抽屉（历史版本 + 回滚 + 差异） */
function flowTplVer(i) {
  const t = FTPLS[i];
  const hist = [];
  for (let v = t.vers; v >= 1; v--) {
    hist.push({ v: 'v' + v, d: v === t.vers ? '当前版本' : '历史版本', on: v === t.vers, chg: v === t.vers ? '节点超时 ' + t.timeout + '；新增「合规复检」节点' : v === 1 ? '初始版本' : '优化审批链（减少 1 个冗余节点）' });
  }
  const body = '<div class="dsec">' + t.no + ' · ' + t.name + ' 版本历史（共 ' + t.vers + ' 版）</div>' +
    '<div class="tl">' + hist.map(function (hh) {
      return '<div class="tl-i ' + (hh.on ? 'gg' : '') + '"><div class="tt">' + hh.v + ' <span style="font-weight:400;font-size:11px;color:var(--text2)">· ' + hh.d + '</span></div>' +
        '<div class="td">' + hh.chg + '</div>' +
        (hh.on ? '' : '<div class="td" style="margin-top:4px"><span class="btn btn-sec btn-sm" onclick="flowTplRollback(' + i + ',\'' + hh.v + '\')">回滚到此版本</span> <span class="btn btn-sec btn-sm" onclick="toast(\'版本差异对比 · ' + hh.v + ' vs ' + t.ver + ' · 原型示意\',\'success\')">差异对比</span></div>') + '</div>';
    }).join('') + '</div>' +
    '<div class="hint" style="margin-top:8px">回滚立即对新发起的流程生效；进行中的流程继续按其发起时版本执行完毕（FLOW-003）。</div>';
  openDrawer('版本管理 · ' + t.no, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '480px');
}
function flowTplRollback(i, ver) {
  const t = FTPLS[i];
  confirmDlg('确认回滚到 ' + ver + '？', '模板 ' + t.no + '（' + t.name + '）当前为 ' + t.ver + '，回滚后新发起的流程将按 ' + ver + ' 执行，进行中的流程不受影响。', '确认回滚', function () {
    t.ver = ver;
    closeDrawer();
    if (state.page === 'flow') renderPage();
    toast('已回滚：' + t.no + ' → ' + ver + '（新流程生效 · 进行中流程按原版本执行）', 'success');
    hlFirst();
  }, { warn: '回滚后需重新验证节点审批人配置是否完整' });
}
/* FLOW-001：新建流程模板 */
function flowTplNew() {
  const body = frow([
    { k: 'tname2', label: '模板名称', type: 'text', req: true, ph: '如：直播场次报备流' },
    { k: 'ttimeout', label: '节点超时', type: 'select', opts: ['2h/节点', '12h/节点', '24h/节点', '48h/节点', '72h/节点'] },
    { k: 'tnodes', label: '节点链（顿号分隔）', type: 'text', req: true, ph: '如：提交报备、运营初审、总监确认、归档', wide: true }
  ]) + '<div class="hint" style="margin-top:4px">创建后为 v1 版本，可在设计器中编排条件分支与并行会签节点。</div>';
  openDrawer('新建流程模板', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="flowTplNewSubmit()">创建模板</button>', '480px');
}
function flowTplNewSubmit() {
  if (!formValidate(['tname2', 'tnodes'])) return;
  const nodes = $('#F_tnodes').value.split(/[、,，]/).map(function (s) { return s.trim(); }).filter(Boolean);
  const no = 'FT-' + String(FTPLS.length + 1).padStart(3, '0');
  FTPLS.unshift({ no: no, name: $('#F_tname2').value.trim(), nodes: nodes.length ? nodes : ['提交', '审批', '归档'], timeout: $('#F_ttimeout').value, ver: 'v1', vers: 1, on: true, use: 0 });
  if (state.page === 'flow') renderPage();
  formOk(no, '流程模板已创建（v1 · 启用中），可在设计器中继续编排节点', '');
  toast('流程模板创建成功：' + no + '（' + FTPLS[0].nodes.length + ' 节点）', 'success');
}

/* ===================== FLOW-002 流程看板视图 ===================== */
/* 看板：进行中流程按当前节点分列，支持节点流转（审批中→下一节点） */
function flowKanbanTab() {
  const act = FLOWS.filter(function (f) { return f.st === '审批中' || f.st === '超时'; });
  const done = FLOWS.filter(function (f) { return f.st === '已完成'; });
  const rej = FLOWS.filter(function (f) { return f.st === '已驳回'; });
  /* 收集进行中流程的当前节点（去重保序）作为动态列 */
  const cols = [];
  act.forEach(function (f) { if (f.node && cols.indexOf(f.node) < 0) cols.push(f.node); });
  if (!cols.length) cols.push('主管审批');
  let h = '<div class="g4">' +
    '<div class="card stat"><span class="l">进行中</span><div class="n" style="color:var(--blue)">' + act.length + '</div><div class="d">审批中 + 超时</div></div>' +
    '<div class="card stat"><span class="l">超时流程</span><div class="n" style="color:var(--red)">' + act.filter(function (f) { return f.st === '超时'; }).length + '</div><div class="d">节点停留 > 24h</div></div>' +
    '<div class="card stat"><span class="l">本月已完成</span><div class="n" style="color:var(--green)">' + done.length + '</div><div class="d">全链路归档</div></div>' +
    '<div class="card stat"><span class="l">已驳回</span><div class="n">' + rej.length + '</div><div class="d">需修改后重新发起</div></div></div>';
  h += '<div class="hint" style="margin-bottom:10px">看板按流程当前节点动态分列（FLOW-002）：点击卡片「流转至下一节点」完成当前节点审批；到达链尾自动归档为已完成。</div>';
  /* 看板列：动态节点列 + 已完成 + 已驳回 */
  const allCols = cols.map(function (c) { return { name: c, kind: 'node' }; })
    .concat([{ name: '已完成', kind: 'done' }, { name: '已驳回', kind: 'rej' }]);
  h += '<div style="display:grid;grid-template-columns:repeat(' + allCols.length + ',minmax(190px,1fr));gap:12px;overflow-x:auto">';
  allCols.forEach(function (col) {
    const list = col.kind === 'node' ? act.filter(function (f) { return f.node === col.name; })
      : col.kind === 'done' ? done : rej;
    const headColor = col.kind === 'node' ? 'var(--blue)' : col.kind === 'done' ? 'var(--green)' : 'var(--text2)';
    h += '<div class="card" style="padding:10px;min-height:220px;background:' + (col.kind === 'node' ? 'var(--blue-bg)' : col.kind === 'done' ? 'rgba(52,199,89,.06)' : 'var(--bg)') + '">' +
      '<div class="rowline" style="justify-content:space-between;margin-bottom:8px">' +
      '<b style="font-size:12.5px;color:' + headColor + '">' + col.name + '</b>' +
      '<span style="font-size:11px;color:var(--text2)">' + list.length + '</span></div>';
    list.forEach(function (f) {
      const i = FLOWS.indexOf(f);
      const isTimeout = f.st === '超时';
      const stTag = f.st === '审批中' ? tag('审批中', 'blue') : isTimeout ? tag('超时', 'red') : tag(f.st, f.st === '已完成' ? 'green' : 'gray');
      /* 节点进度点 */
      const dots = (f.chain || []).map(function (n, j) {
        const passed = col.kind !== 'node' || j <= (f.ni || 0);
        return '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:3px;background:' + (passed ? 'var(--blue)' : 'var(--line2)') + '"></span>';
      }).join('');
      h += '<div style="background:#fff;border:1px solid var(--line2);border-radius:10px;padding:9px 10px;margin-bottom:8px' + (isTimeout ? ';border-color:rgba(255,59,48,.4)' : '') + '">' +
        '<div class="rowline" style="justify-content:space-between"><span class="mono" style="font-size:10.5px;color:var(--blue)">' + f.id + '</span>' + stTag + '</div>' +
        '<div style="font-size:12px;font-weight:600;margin-top:3px">' + tag(f.type, f.type === '报销' ? 'green' : f.type === '账号领用' ? 'cyan' : f.type === '开播审批' ? 'purple' : f.type === '内容审核' ? 'orange' : 'blue') + ' ' + sens(f.from) + '</div>' +
        '<div style="font-size:11px;color:var(--text2);margin-top:3px">审批人 ' + f.approver + ' · 耗时 ' + (isTimeout ? '<span class="neg">' + f.cost + '</span>' : f.cost) + '</div>' +
        '<div style="margin-top:5px">' + dots + '</div>' +
        (col.kind === 'node' ? '<div style="margin-top:6px;display:flex;gap:6px">' +
          '<span class="btn btn-pri btn-sm" style="background:var(--orange)" onclick="flowKbNext(' + i + ')">流转下一节点</span>' +
          '<span class="btn btn-sec btn-sm" onclick="urge(\'' + f.id + '\',\'' + f.approver + '\')">催办</span></div>' : '') +
        '</div>';
    });
    if (!list.length) h += '<div style="font-size:11px;color:var(--text2);text-align:center;padding:18px 0">—</div>';
    h += '</div>';
  });
  h += '</div>';
  return h;
}
/* FLOW-002：看板节点流转（当前节点审批通过 → 下一节点；到链尾归档） */
function flowKbNext(i) {
  const f = FLOWS[i];
  if (!f) return;
  const chain = f.chain || [];
  const ni = f.ni != null ? f.ni : chain.indexOf(f.node);
  const nextIdx = ni + 1;
  if (!chain.length || nextIdx >= chain.length) {
    confirmDlg('确认完成流程？', '流程 ' + f.id + '（' + f.type + ' · ' + f.from + '）已到达链尾节点，确认后归档为「已完成」。', '确认归档', function () {
      f.st = '已完成'; f.node = chain.length ? chain[chain.length - 1] : f.node;
      if (state.page === 'flow') renderPage();
      toast('流程已归档：' + f.id + '（' + f.type + ' · 全链路完成）', 'success');
      hlFirst();
    });
    return;
  }
  confirmDlg('确认流转至下一节点？', '流程 ' + f.id + '（' + f.type + '）当前节点「' + chain[ni] + '」审批通过，将流转至「<b>' + chain[nextIdx] + '</b>」并通知下一节点审批人。', '确认流转', function () {
    f.ni = nextIdx; f.node = chain[nextIdx]; f.st = '审批中'; f.cost = '0h';
    if (state.page === 'flow') renderPage();
    toast('已流转：' + f.id + ' → ' + chain[nextIdx] + '（已通知审批人）', 'success');
    hlFirst();
  }, { warn: '流转后当前审批人不再收到该流程的提醒' });
}

/* ===================== 11 FIN 财务核算 ===================== */
const FINS = [
  { id: 'FI202609-031', sid: 'IMS202609110DY0138', acct: 'ACCT-2026-0002', rev: 186400.00, cost: 82300.00, ratio: 30, st: '待结算' },
  { id: 'FI202609-030', sid: 'IMS202609100DY0131', acct: 'ACCT-2026-0001', rev: 412800.00, cost: 156400.00, ratio: 35, st: '结算中' },
  { id: 'FI202609-029', sid: 'IMS202609090DY0127', acct: 'ACCT-2026-0003', rev: 96700.00, cost: 54100.00, ratio: 25, st: '已结算' },
  { id: 'FI202609-028', sid: 'IMS202609080DY0121', acct: 'ACCT-2026-0002', rev: 43800.00, cost: 21500.00, ratio: 20, st: '已结算' },
  { id: 'FI202609-027', sid: 'IMS202609070DY0118', acct: 'ACCT-2026-0034', rev: 61200.00, cost: 44600.00, ratio: 22, st: '待结算' },
  { id: 'FI202609-026', sid: 'IMS202609060DY0112', acct: 'ACCT-2026-0001', rev: 128600.00, cost: 139200.00, ratio: 28, st: '已结算' },
  { id: 'FI202609-025', sid: 'IMS202609050DY0108', acct: 'ACCT-2026-0003', rev: 152300.00, cost: 67800.00, ratio: 30, st: '结算中' },
  { id: 'FI202609-024', sid: 'IMS202609040DY0105', acct: 'ACCT-2026-0002', rev: 38200.00, cost: 26900.00, ratio: 18, st: '已结算' },
  { id: 'FI202609-023', sid: 'IMS202609030DY0101', acct: 'ACCT-2026-0001', rev: 289400.00, cost: 102600.00, ratio: 35, st: '已结算' },
  { id: 'FI202609-022', sid: 'IMS202609020DY0096', acct: 'ACCT-2026-0034', rev: 55100.00, cost: 48700.00, ratio: 20, st: '待结算' }
];
PAGES.fin = function () {
  let h = pgHead('fin', '<button class="btn btn-sec" onclick="exportX(this,\'核算明细\',FINS.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="finAdd()">' + ic('plus', 15) + '发起结算</button>');
  let totRev = 0, totCost = 0, totShare = 0, settled = 0;
  FINS.forEach(function (f) {
    const profit = f.rev - f.cost;
    const share = profit > 0 ? profit * f.ratio / 100 : 0;
    const net = profit - share;
    totRev += f.rev; totCost += f.cost; totShare += share;
    if (f.st === '已结算') settled += net;
  });
  const pending = FINS.filter(function (f) { return f.st !== '已结算'; }).length;
  h += '<div class="g4"><div class="card stat"><span class="l">本月总成本</span><div class="n" style="font-size:22px">' + fmtMoney(totCost) + '</div><div class="d">10 场次合计</div></div>' +
    '<div class="card stat"><span class="l">直播分成总额</span><div class="n" style="font-size:22px;color:var(--blue)">' + fmtMoney(totShare) + '</div><div class="d">主播 + 团队分成</div></div>' +
    '<div class="card stat"><span class="l">待结算</span><div class="n" style="font-size:22px;color:var(--orange)">' + pending + ' 单</div><div class="d">含结算中 2 单</div></div>' +
    '<div class="card stat"><span class="l">已结算净利润</span><div class="n" style="font-size:22px;color:var(--green)">' + fmtMoney(settled) + '</div><div class="d">本月已入账</div></div></div>';
  const qr = state.q.fin || {};
  h += qbar(qi('核算单号', 130, qr.k0) + qi('场次 ID', 150, qr.k1) + qs(['全部状态', '待结算', '结算中', '已结算'], 100, qr.k2) + '<input type="month" style="width:118px" value="2026-09">', 'qSave(\'fin\')');
  const stc = { '待结算': 'orange', '结算中': 'blue', '已结算': 'green' };
  const list = qFilter(FINS, function (f) { return [f.id, f.sid, f.acct]; }, function (f) { return f.st; });
  let rows = '';
  list.forEach(function (f) {
    const i = FINS.indexOf(f);
    const profit = f.rev - f.cost;
    const share = profit > 0 ? profit * f.ratio / 100 : 0;
    const net = profit - share;
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + f.id + '</td><td class="mono num" style="font-size:11.5px">' + f.sid + '</td><td class="mono" style="font-size:12px">' + f.acct + '</td>' +
      '<td class="num" style="font-weight:500">' + fmtMoney(f.rev) + '</td><td class="num">' + fmtMoney(f.cost) + '</td>' +
      '<td class="num ' + (profit < 0 ? 'neg' : '') + '">' + fmtMoney(profit) + '</td>' +
      '<td class="num">' + f.ratio + '%</td><td class="num" style="color:var(--blue)">' + fmtMoney(share) + '</td>' +
      '<td class="num ' + (net < 0 ? 'neg' : 'pos') + '" style="font-weight:600">' + fmtMoney(net) + '</td>' +
      '<td>' + tag(f.st, stc[f.st]) + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="toast(\'核算单详情 · ' + f.id + ' · 原型示意\',\'success\')">查看</span></td></tr>';
  });
  h += tbl(['核算单号', '场次 ID', '直播账号', '总收入', '总成本', '毛利', '主播分成比例', '分成金额', '净利润', '结算状态', '操作'], rows);
  return h;
};
/* FIN：发起结算表单（自动算净利润） */
function finAdd() {
  const body = frow([
    { k: 'sid', label: '选择场次', type: 'select', req: true, opts: ['IMS202609120DY0142 · 抖音 · 秋季新品首发', 'IMS202609120DY0141 · 斗鱼 · 晚间健身操', 'IMS202609110DY0138 · 视频号 · 装备开箱'] },
    { k: 'rev', label: '总收入', type: 'num', req: true, unit: '¥', ph: '0.00', pre: 'finCalc()' },
    { k: 'cost', label: '总成本', type: 'num', req: true, unit: '¥', ph: '0.00', pre: 'finCalc()' },
    { k: 'ratio', label: '分成比例', type: 'num', req: true, unit: '%', val: 30, pre: 'finCalc()' },
    { k: 'note', label: '备注', type: 'textarea', ph: '结算口径、特殊分成约定（选填）', wide: true }
  ]) + '<div class="dsec">净利润测算（自动计算）</div>' +
    '<div class="kv" style="background:var(--bg);border-radius:10px;padding:12px 14px">' +
    '<div><div class="k">毛利</div><div class="v num" id="finP">¥0.00</div></div>' +
    '<div><div class="k">主播分成</div><div class="v num" style="color:var(--blue)" id="finS">¥0.00</div></div>' +
    '<div><div class="k">净利润</div><div class="v num pos" style="font-weight:700" id="finN">¥0.00</div></div></div>';
  openDrawer('发起结算', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="finAddSubmit()">提交结算单</button>', '480px');
}
function finCalc() {
  const rev = Number($('#F_rev').value || 0), cost = Number($('#F_cost').value || 0), ratio = Number($('#F_ratio').value || 0);
  const profit = rev - cost;
  const share = profit > 0 ? profit * ratio / 100 : 0;
  const net = profit - share;
  $('#finP').textContent = fmtMoney(profit);
  $('#finP').className = 'v num' + (profit < 0 ? ' neg' : '');
  $('#finS').textContent = fmtMoney(share);
  const n = $('#finN');
  n.textContent = fmtMoney(net);
  n.className = 'v num ' + (net < 0 ? 'neg' : 'pos');
}
function finAddSubmit() {
  if (!formValidate(['sid', 'rev', 'cost', 'ratio'])) return;
  finCalc();
  const rev = Number($('#F_rev').value || 0), cost = Number($('#F_cost').value || 0), ratio = Number($('#F_ratio').value || 0);
  const no = 'FI202609-' + String(FINS.length + 21).padStart(3, '0');
  FINS.unshift({ id: no, sid: $('#F_sid').value.split(' ')[0], acct: 'ACCT-2026-0001', rev: rev, cost: cost, ratio: ratio, st: '待结算' });
  if (state.page === 'fin') renderPage();
  formOk(no, '结算单已创建（待结算），净利润 ' + fmtMoney(rev - cost - (rev - cost > 0 ? (rev - cost) * ratio / 100 : 0)), '');
  toast('结算单发起成功：' + no, 'success');
}

/* ===================== 05 PERF 绩效 ===================== */
const PERFS = [
  { name: '苏杳', dept: '主播组', period: '2026 Q3', kpi: 88, adj: '+8 大促超额', score: 92, g: 'A' },
  { name: '赵敏', dept: '运营中心', period: '2026 Q3', kpi: 92, adj: '+5 满勤', score: 95, g: 'S' },
  { name: '孙倩', dept: '内容中心', period: '2026 Q3', kpi: 81, adj: '0', score: 81, g: 'B' },
  { name: '李澈', dept: '内容中心', period: '2026 Q3', kpi: 76, adj: '-3 审核超时 1 次', score: 73, g: 'B' },
  { name: '何舟', dept: '运营中心', period: '2026 Q3', kpi: 94, adj: '+6 增长贡献', score: 96, g: 'S' },
  { name: '陈默', dept: '数据中心', period: '2026 Q3', kpi: 85, adj: '0', score: 85, g: 'A' },
  { name: '王野', dept: '外协', period: '2026 Q3', kpi: 58, adj: '-5 SOP 违规', score: 51, g: 'D' },
  { name: '林岚', dept: '行政部', period: '2026 Q3', kpi: 90, adj: '+2 盘点零误差', score: 92, g: 'A' },
  { name: '周晴', dept: '财务部', period: '2026 Q3', kpi: 64, adj: '-4 结算超时 2 次', score: 60, g: 'C' }
];
PAGES.perf = function () {
  const cur = state.tab.perf || '考核方案';
  let h = pgHead('perf', cur === '考核结果' ? '<button class="btn btn-sec" onclick="exportX(this,\'考核结果\',PERFS.length)">导出</button>' :
    cur === '在线考试' ? '<button class="btn btn-pri" onclick="examPaperAdd()">' + ic('plus', 15) + '创建试卷</button>' :
      '<button class="btn btn-pri" onclick="perfAdd()">' + ic('plus', 15) + '新建方案</button>');
  h += '<div class="tabs">' + ['考核方案', '考核结果', '在线考试'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'perf\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  if (cur === '在线考试') return h + perfExamTab();
  if (cur === '考核方案') {
    const plans = [
      { name: '主播/达人考核方案（直播）', cycle: '季度', target: 36, on: true, d: '开播场次 · GMV · 观看时长 · 粉丝增长' },
      { name: '直播运营考核方案', cycle: '季度', target: 18, on: true, d: '场次风控通过率 · 直播 GMV · 复盘质量' },
      { name: '短视频运营考核方案', cycle: '月度', target: 24, on: true, d: '作品数量 · 播放/互动率 · SOP 合规' },
      { name: '行政/财务考核方案', cycle: '半年度', target: 14, on: false, d: '流程时效 · 差错率 · 满意度' }
    ];
    h += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:14px">';
    plans.forEach(function (p) {
      h += '<div class="card hov" onclick="toast(\'方案编辑 · ' + p.name + ' · 原型示意\',\'success\')"><div class="rowline" style="justify-content:space-between;margin-bottom:8px">' +
        '<span style="color:var(--blue)">' + ic('chart', 19) + '</span><span class="sw' + (p.on ? ' on' : '') + '" onclick="event.stopPropagation();this.classList.toggle(\'on\');toast(\'方案已' + (p.on ? '停用' : '启用') + '\',\'success\')"><i></i></span></div>' +
        '<h3 style="font-size:15px">' + p.name + '</h3><div class="csub">' + p.d + '</div>' +
        '<div class="rowline" style="margin-top:12px">' + tag(p.cycle, 'blue') + '<span class="csub">' + p.target + ' 名被考核人</span><span class="chip" style="margin-left:auto">' + (p.on ? '生效中' : '已停用') + '</span></div></div>';
    });
    h += '</div>';
    return h;
  }
  h += qbar(qi('被考核人', 110) + qs(['全部部门', '主播组', '运营中心', '内容中心', '数据中心', '行政部', '财务部', '外协']) + qs(['全部周期', '2026 Q3', '2026 Q2']));
  /* PERF-004：按综合得分排名 */
  const ranked = PERFS.slice().sort(function (a, b) { return b.score - a.score; });
  const rankMap = {};
  ranked.forEach(function (p, idx) { rankMap[p.name] = idx + 1; });
  const top3 = ranked.slice(0, 3);
  const bottom = ranked.slice(-2);
  h += '<div class="g3">' +
    '<div class="card stat" style="border-left:3px solid var(--green)"><span class="l">绩效红榜 TOP3（PERF-004）</span><div class="d" style="margin-top:6px">' +
    top3.map(function (p, i) { return '<span class="chip" style="margin-right:6px;color:var(--green);border-color:var(--green)">' + (i + 1) + '. ' + p.name + ' ' + p.score + '</span>'; }).join('') + '</div></div>' +
    '<div class="card stat" style="border-left:3px solid var(--red)"><span class="l">末位预警（连续 2 期 D 级）</span><div class="d" style="margin-top:6px">' +
    bottom.map(function (p) { return '<span class="chip" style="margin-right:6px;color:var(--red);border-color:var(--red)">' + p.name + ' ' + p.score + '（' + p.g + ' 级）</span>'; }).join('') + '<div class="hint" style="margin-top:4px">将触发绩效改进计划（PIP）并通知直属主管</div></div></div>' +
    '<div class="card stat"><span class="l">部门均分</span><div class="n">82.6</div><div class="d">环比 <span class="pos">+2.3</span></div></div></div>';
  const gc = { S: 'green', A: 'blue', B: 'yellow', C: 'orange', D: 'red' };
  let rows = '';
  PERFS.forEach(function (p) {
    const rk = rankMap[p.name];
    const kpic = p.kpi >= 90 ? 'var(--green)' : p.kpi >= 75 ? 'var(--blue)' : p.kpi >= 60 ? 'var(--orange)' : 'var(--red)';
    rows += '<tr><td style="font-weight:' + (rk <= 3 ? 700 : 500) + ';color:' + (rk <= 3 ? 'var(--green)' : rk >= PERFS.length - 1 ? 'var(--red)' : 'inherit') + '">' + (rk <= 3 ? '🏆 ' : '') + rk + '</td>' +
      '<td style="font-weight:500">' + sens(p.name) + '</td><td>' + p.dept + '</td><td class="num">' + p.period + '</td>' +
      '<td><div class="rowline"><span class="pg" style="width:60px"><i style="width:' + p.kpi + '%;background:' + kpic + '"></i></span><span class="num" style="font-size:12px">' + p.kpi + '</span></div></td>' +
      '<td style="font-size:12px;' + (p.adj.indexOf('-') === 0 ? 'color:var(--red)' : p.adj === '0' ? 'color:var(--text2)' : 'color:var(--green)') + '">' + p.adj + '</td>' +
      '<td style="font-size:20px;font-weight:700;letter-spacing:-.5px" class="num">' + p.score + '</td>' +
      '<td><span class="tag" style="background:rgba(' + TAGMAP[gc[p.g]][0] + ',.13);color:' + TAGMAP[gc[p.g]][1] + '"><span class="dot"></span>' + p.g + ' 级</span></td>' +
      '<td>' + (p.g === 'D' ? '<span class="btn btn-sm" style="color:var(--red);border-color:rgba(255,59,48,.35)" onclick="perfPIP(\'' + p.name + '\')">改进预警</span>' :
        '<span class="btn btn-sec btn-sm" onclick="toast(\'考核明细 · ' + p.name + ' · 原型示意\',\'success\')">查看</span>') + '</td></tr>';
  });
  h += tbl(['排名', '被考核人', '部门', '考核周期', 'KPI 得分', '加减分项', '综合得分', '评级', '操作'], rows);
  return h;
};
/* PERF-004：末位改进预警（PIP） */
function perfPIP(name) {
  const p = PERFS.filter(function (x) { return x.name === name; })[0];
  if (!p) return;
  confirmDlg('发起绩效改进计划（PIP）？', p.name + '（' + p.dept + '）综合得分 ' + p.score + '（' + p.g + ' 级），连续 2 期处于末位区间，将按 BR-117 绩效排名规则发起改进计划并通知直属主管与 HR。', '发起 PIP', function () {
    toast('绩效改进计划已发起：' + p.name + '（已通知 ' + p.dept + ' 负责人与 HR · 考核周期 30 天）', 'success');
  }, { warn: 'PIP 期间将安排辅导与阶段复评，连续 3 期 D 级触发岗位调整评估' });
}
/* ---- PERF Tab3：在线考试（PERF-003，题库/试卷/成绩三胶囊） ---- */
const EXAMQ = [
  { no: 'EQ-001', t: '直播开场 15 分钟的留存红线是？', dom: '直播规范', tp: '单选', sc: 10, use: 6 },
  { no: 'EQ-002', t: '以下哪些行为属于平台高危违规（多选）？', dom: '直播规范', tp: '多选', sc: 10, use: 5 },
  { no: 'EQ-003', t: '直播间挂「福利品」时可以直接改价上链接。（判断）', dom: '直播规范', tp: '判断', sc: 5, use: 8 },
  { no: 'EQ-004', t: '短视频完播率显著衰减的时间点是？', dom: '内容技能', tp: '单选', sc: 10, use: 4 },
  { no: 'EQ-005', t: '口播脚本「痛点前置」的正确做法是？', dom: '内容技能', tp: '单选', sc: 10, use: 7 },
  { no: 'EQ-006', t: '请简述一个你操盘过的直播间起号思路。（简答）', dom: '直播技能', tp: '简答', sc: 20, use: 2 },
  { no: 'EQ-007', t: '投流 ROI 的计算公式是？', dom: '数据技能', tp: '单选', sc: 10, use: 6 },
  { no: 'EQ-008', t: '口径「GMV」与「净 GMV」的区别是什么？（简答）', dom: '数据技能', tp: '简答', sc: 15, use: 1 },
  { no: 'EQ-009', t: '数据上报的截止时间是每日几点前？', dom: '制度合规', tp: '单选', sc: 10, use: 9 },
  { no: 'EQ-010', t: '外协人员可以访问公司数据看板。（判断）', dom: '制度合规', tp: '判断', sc: 5, use: 3 }
];
const PAPERS = [
  { no: 'PE20260916-01', name: '9 月主播合规月考', qs: 12, total: 100, win: '09-16 09:00 ~ 09-16 18:00', assign: 36, submitted: 31, st: '进行中' },
  { no: 'PE20260910-02', name: '短视频运营季度认证', qs: 15, total: 100, win: '09-10 10:00 ~ 09-11 22:00', assign: 24, submitted: 24, st: '已判分' },
  { no: 'PE20260904-03', name: '新人入职摸底考', qs: 10, total: 50, win: '09-04 09:00 ~ 09-04 12:00', assign: 18, submitted: 15, st: '待阅卷' },
  { no: 'PE20260828-04', name: '数据口径专项测试', qs: 8, total: 60, win: '08-28 14:00 ~ 08-29 14:00', assign: 12, submitted: 12, st: '已判分' }
];
const RECORDS = [
  { no: 'PR20260916-011', paper: 'PE20260916-01', who: '苏杳', obj: 62, sub: '待阅', final: '—', st: '已交卷' },
  { no: 'PR20260916-010', paper: 'PE20260916-01', who: '赵敏', obj: 78, sub: '待阅', final: '—', st: '已交卷' },
  { no: 'PR20260916-009', paper: 'PE20260916-01', who: '孙倩', obj: 85, sub: '待阅', final: '—', st: '已交卷' },
  { no: 'PR20260916-008', paper: 'PE20260916-01', who: '何舟', obj: 90, sub: '待阅', final: '—', st: '已交卷' },
  { no: 'PR20260910-024', paper: 'PE20260910-02', who: '李澈', obj: 88, sub: 8, final: 96, st: '已判分' },
  { no: 'PR20260910-023', paper: 'PE20260910-02', who: '孙倩', obj: 72, sub: 6, final: 78, st: '已判分' },
  { no: 'PR20260910-022', paper: 'PE20260910-02', who: '王野', obj: 41, sub: 2, final: 43, st: '已判分' },
  { no: 'PR20260904-015', paper: 'PE20260904-03', who: '新员工 · 张一鸣', obj: 35, sub: '待阅', final: '—', st: '已交卷' },
  { no: 'PR20260904-012', paper: 'PE20260904-03', who: '新员工 · 李思', obj: 0, sub: 0, final: '—', st: '未开始' }
];
function perfExamTab() {
  const cur = state.gc.perfexam || '题库管理';
  let h = '';
  h += '<div class="cattabs">' + ['题库管理', '试卷管理', '成绩管理'].map(function (t) {
    return '<div class="cattab' + (cur === t ? ' on' : '') + '" onclick="setGc(\'perfexam\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  if (cur === '题库管理') h += examBankTab();
  else if (cur === '试卷管理') h += examPaperTab();
  else h += examRecordTab();
  return h;
}
function examBankTab() {
  let h = qbar(qi('题目编号', 110) + qi('题干关键词', 150) + qs(['全部知识域', '直播规范', '内容技能', '直播技能', '数据技能', '制度合规'], 110) + qs(['全部题型', '单选', '多选', '判断', '简答'], 90), 'qSave(\'perf\')');
  const tpc = { '单选': 'blue', '多选': 'purple', '判断': 'cyan', '简答': 'orange' };
  const list = qFilter(EXAMQ, function (q) { return [q.no, q.t]; }, function (q) { return q.dom + '|' + q.tp; });
  let rows = '';
  list.forEach(function (q) {
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + q.no + '</td><td style="font-weight:500;max-width:340px">' + q.t + '</td><td>' + tag(q.dom, 'gray') + '</td>' +
      '<td>' + tag(q.tp, tpc[q.tp]) + '</td><td class="num">' + q.sc + ' 分</td><td class="num">' + q.use + ' 卷</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="toast(\'题目编辑 · ' + q.no + ' · 原型示意\',\'success\')">编辑</span></td></tr>';
  });
  h += tbl(['题目编号', '题干', '知识域', '题型', '分值', '被引用', '操作'], rows);
  return h;
}
function examPaperTab() {
  const stc = { '进行中': 'blue', '已判分': 'green', '待阅卷': 'orange' };
  let rows = '';
  PAPERS.forEach(function (p, i) {
    const pct = Math.round(p.submitted / p.assign * 100);
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + p.no + '</td><td style="font-weight:500">' + p.name + '</td><td class="num">' + p.qs + ' 题</td><td class="num">' + p.total + ' 分</td>' +
      '<td class="num" style="font-size:12px">' + p.win + '</td>' +
      '<td><div class="rowline"><span class="pg" style="width:64px"><i style="width:' + pct + '%"></i></span><span class="num" style="font-size:12px">' + p.submitted + '/' + p.assign + '</span></div></td>' +
      '<td>' + tag(p.st, stc[p.st]) + '</td>' +
      '<td>' + (p.st === '进行中' ? '<button class="btn btn-sec btn-sm" onclick="examAssign(' + i + ')">指派</button><button class="btn btn-pri btn-sm" onclick="examTake(' + i + ')">考生作答</button>' :
        '<span class="btn btn-sec btn-sm" onclick="toast(\'试卷详情 · ' + p.no + ' · 原型示意\',\'success\')">查看</span>') + '</td></tr>';
  });
  return tbl(['试卷编号', '试卷名称', '题量', '总分', '考试窗口', '交卷进度', '状态', '操作'], rows);
}
function examRecordTab() {
  let h = qbar(qi('成绩单号', 130) + qi('考生', 100) + qs(['全部试卷', 'PE20260916-01 · 9 月主播合规月考', 'PE20260910-02 · 短视频运营季度认证', 'PE20260904-03 · 新人入职摸底考'], 210) + qs(['全部状态', '未开始', '已交卷', '已判分', '补考'], 90), 'qSave(\'perf\')');
  const stc = { '未开始': 'gray', '已交卷': 'blue', '已判分': 'green' };
  const list = qFilter(RECORDS, function (r) { return [r.no, r.who, r.paper]; }, function (r) { return r.st; });
  let rows = '';
  list.forEach(function (r) {
    const i = RECORDS.indexOf(r);
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + r.no + '</td><td class="mono num" style="font-size:12px">' + r.paper + '</td><td style="font-weight:500">' + sens(r.who) + '</td>' +
      '<td class="num">' + (typeof r.obj === 'number' ? r.obj + ' 分' : '—') + '</td>' +
      '<td class="num">' + (typeof r.sub === 'number' ? r.sub + ' 分' : tag(r.sub, 'orange')) + '</td>' +
      '<td class="num" style="font-weight:600;' + (typeof r.final === 'number' ? (r.final >= 60 ? 'color:var(--green)' : 'color:var(--red)') : '') + '">' + (typeof r.final === 'number' ? r.final + ' 分' : '—') + '</td>' +
      '<td>' + tag(r.st, stc[r.st]) + '</td>' +
      '<td>' + (r.st === '已交卷' ? '<button class="btn btn-pri btn-sm" onclick="examGrade(' + i + ')">阅卷</button>' :
        r.st === '已判分' ? '<span class="btn btn-sec btn-sm" onclick="toast(\'成绩单 · ' + r.no + ' · 原型示意\',\'success\')">查看</span>' :
          '<span class="btn btn-sec btn-sm" style="opacity:.5">—</span>') + '</td></tr>';
  });
  h += tbl(['成绩单号', '试卷', '考生', '客观题得分', '简答题得分', '最终得分', '状态', '操作'], rows);
  h += '<div class="card" style="margin-top:14px;padding:12px 16px;display:flex;gap:10px;align-items:center">' + ic('help', 16) +
    '<span style="font-size:12px;color:var(--text2);line-height:1.6">客观题交卷即自动判分（PER-E-R2）；简答题须 <b style="color:var(--text)">48 小时内</b>完成人工阅卷，超时待阅置顶提示；阅卷成绩自动计入「考试成绩」类绩效指标取数（PER-E-R4，对应 PRD 5.22 PERF-003）。</span></div>';
  return h;
}
function setGc(k, v) { state.gc[k] = v; renderPage(); }
/* PERF：组卷抽屉（FIXED 模式 · Σ 分数实时校验 1159） */
function examPaperAdd() {
  const body = '<div style="padding:2px 4px">' +
    frow([
      { k: 'pname', label: '试卷名称', type: 'text', req: true, ph: '如：10 月主播合规月考' },
      { k: 'pmode', label: '组卷方式', type: 'pills', val: '固定选题', opts: ['固定选题', '随机抽题'] },
      { k: 'pwin', label: '考试窗口', type: 'dt', req: true, val: '2026-10-16T09:00', hint: '仅窗口内可进入作答（1161 窗口外拦截）' }
    ]) +
    '<div class="fld wide"><label>选题（勾选计入试卷）<i class="req">*</i></label>' +
    '<div id="picks" style="max-height:260px;overflow:auto;border:1px solid var(--line2);border-radius:var(--r-s);padding:4px 10px">' +
    EXAMQ.map(function (q, i) {
      return '<label style="display:flex;align-items:center;gap:9px;padding:8px 2px;border-bottom:1px solid var(--line);font-size:12.5px;cursor:pointer">' +
        '<input type="checkbox" value="' + i + '" onchange="paperSum()" style="accent-color:var(--blue)">' +
        '<span class="mono" style="color:var(--text2);font-size:11px">' + q.no + '</span><span style="flex:1">' + q.t + '</span>' +
        '<span style="color:var(--text2);font-size:11px">' + q.dom + ' · ' + q.tp + ' · ' + q.sc + ' 分</span></label>';
    }).join('') + '</div>' +
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;padding:0 2px">' +
    '<span class="csub" id="pickhint">已选 0 题 · Σ = 0 分</span>' +
    '<span style="font-size:13px;font-weight:600">合计 <span class="num" id="picksum" style="color:var(--text2)">0</span> 分</span></div>' +
    '<div class="ferr" id="E_picks"></div></div></div>';
  openDrawer('创建试卷（组卷）', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="examPaperSubmit()">保存试卷</button>', '560px');
}
function paperSum() {
  const cks = document.querySelectorAll('#picks input:checked');
  let sum = 0;
  cks.forEach(function (c) { sum += EXAMQ[Number(c.value)].sc; });
  const sp = $('#picksum'), hint = $('#pickhint'), err = $('#E_picks');
  if (sp) sp.textContent = sum;
  if (hint) hint.textContent = '已选 ' + cks.length + ' 题 · Σ = ' + sum + ' 分';
  if (err) {
    if (sum !== 100) { err.textContent = 'Σ 题目分须等于 100 分（当前 ' + sum + '，错误码 1159 前端预校验）'; err.style.color = 'var(--red)'; }
    else { err.textContent = '✓ Σ = 100 分，满足组卷校验'; err.style.color = 'var(--green)'; }
  }
}
function examPaperSubmit() {
  const cks = document.querySelectorAll('#picks input:checked');
  if (!cks.length) { toast('请至少勾选 1 道题目', 'error'); return; }
  let sum = 0; cks.forEach(function (c) { sum += EXAMQ[Number(c.value)].sc; });
  if (sum !== 100) { toast('Σ 题目分 ' + sum + ' 分 ≠ 100 分，无法保存（1159）', 'error'); return; }
  if (!formValidate(['pname', 'pwin'])) return;
  const no = 'PE20260918-' + String(PAPERS.length + 1).padStart(2, '0');
  PAPERS.unshift({ no: no, name: $('#F_pname').value.trim(), qs: cks.length, total: 100, win: ($('#F_pwin').value || '').replace('T', ' ') + ' ~ 开放 9h', assign: 0, submitted: 0, st: '进行中' });
  if (state.page === 'perf') renderPage();
  formOk(no, '试卷已保存（' + cks.length + ' 题 · 满分 100 分），下一步：指派考生', '');
  toast('试卷创建成功：' + no, 'success');
}
/* PERF：指派考生 */
function examAssign(i) {
  const p = PAPERS[i];
  const cands = ['苏杳', '赵敏', '孙倩', '何舟', '李澈', '陈默', '王野'];
  const body = '<div style="padding:2px 4px">' +
    '<div class="card" style="padding:10px 14px;margin-bottom:12px;display:flex;gap:10px;align-items:center;background:rgba(0,113,227,.05)">' + ic('doc', 15) +
    '<span style="font-size:12.5px;line-height:1.5"><b>' + p.name + '</b> · ' + p.qs + ' 题 · ' + p.total + ' 分<br><span class="csub">' + p.win + '</span></span></div>' +
    '<div class="fld wide"><label>指派考生（多选）<i class="req">*</i></label>' +
    '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
    cands.map(function (c, ci) { return '<label class="pill" style="cursor:pointer"><input type="checkbox" value="' + ci + '" onchange="pillChk(this)" style="accent-color:var(--blue)"><span>' + c + '</span></label>'; }).join('') +
    '</div><div class="hint" style="margin-top:8px">指派后考生工作台将收到「考试待办」卡片</div></div></div>';
  openDrawer('指派考生 · ' + p.no, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="examAssignSubmit(' + i + ')">确认指派</button>', '440px');
}
function pillChk(inp) {
  const sp = inp.nextElementSibling;
  inp.parentNode.classList.toggle('on', inp.checked);
}
function examAssignSubmit(i) {
  const p = PAPERS[i];
  const cks = document.querySelectorAll('#dr-body input:checked');
  if (!cks.length) { toast('请至少勾选 1 名考生', 'error'); return; }
  p.assign += cks.length;
  cks.forEach(function (c) {
    RECORDS.unshift({ no: 'PR20260918-' + String(RECORDS.length + 1).padStart(3, '0'), paper: p.no, who: c.parentNode.querySelector ? c.parentNode.textContent.trim() : '考生', obj: 0, sub: 0, final: '—', st: '未开始' });
  });
  if (state.page === 'perf') renderPage();
  formOk(p.no, '已指派 ' + cks.length + ' 人，考生工作台已收到考试待办', '');
  toast('指派成功：' + cks.length + ' 人', 'success');
}
/* PERF：考生作答（H5 同构演示 · 客观题即时判分） */
const EXAMTK = {
  title: '9 月主播合规月考', pass: 60, total: 100,
  qs: [
    { t: '直播开场 15 分钟的留存红线是？', sc: 20, opts: ['观众数不低于开播前预告的 50%', '在线人数不低于峰值 30%', '没有硬性红线', '达到 1,000 人'], ans: 1, ana: '开场 15 分钟在线人数跌破峰值 30% 将触发流量降权，须即时调整话术与福袋节奏。' },
    { t: '以下哪些行为属于平台高危违规？', sc: 20, opts: ['引导线下交易', '口播极限词（最、第一）', '未报备更换直播场地', '挂小黄车'], ans: 0, ana: '引导线下交易属于一级违规（封号级）；极限词为二级；场地变更须报备为合规要求。' },
    { t: '直播间挂「福利品」时可以直接改价上链接。', sc: 20, opts: ['对', '错'], ans: 1, ana: '福利品价格变动须提前报备运营与风控，直接改价涉嫌虚假福利，属高危违规。' },
    { t: '数据上报的截止时间是每日几点前？', sc: 20, opts: ['20:00', '22:00', '23:00', '次日 09:00'], ans: 1, ana: '依据数据上报制度：每日 22:00 前完成当日场次数据上报。' },
    { t: '请简述你的直播间起号思路（不少于 100 字）。', sc: 20, opts: null, ans: -1, sa: true }
  ]
};
function examTake(i) {
  state.qz = { mode: 'exam', sel: {}, graded: false };
  renderExamTake();
}
function renderExamTake() {
  const q = EXAMTK, st = state.qz;
  let body = '<div class="qz-head"><div class="qz-meta">' + tag('在线考试', 'blue') + tag('及格 ' + q.pass + ' 分', 'blue') +
    '<span class="csub">共 ' + q.qs.length + ' 题 · 满分 ' + q.total + ' 分</span></div>' +
    (st.graded ? '' : '<span class="qz-timer">' + ic('clock', 14) + '剩 47:32</span>') + '</div>';
  q.qs.forEach(function (it, n) {
    if (it.sa) {
      const v = (st.ansTxt || {})[n] || '';
      body += '<div class="qz-item"><div class="qz-q"><span class="qno">' + (n + 1) + '</span>' + it.t + '<span class="qscore">' + it.sc + ' 分</span></div>' +
        (st.graded ? '<div class="qz-ana" style="margin-top:0">' + (v ? v.slice(0, 80) : '（未作答）') + '…<br><span style="color:var(--orange)">' + ic('clock', 12) + ' 简答题 · 待人工阅卷（48h 内）</span></div>' :
          '<textarea id="QZ_SA" placeholder="请输入你的答案（不少于 100 字）" style="width:100%;min-height:90px;border:1px solid var(--line2);border-radius:var(--r-s);padding:8px 10px;font-size:13px;font-family:var(--font);outline:none" oninput="examSa(' + n + ',this.value)">' + v + '</textarea>');
      body += '</div>';
      return;
    }
    const pick = st.sel[n];
    body += '<div class="qz-item"><div class="qz-q"><span class="qno">' + (n + 1) + '</span>' + it.t + '<span class="qscore">' + it.sc + ' 分</span></div>';
    it.opts.forEach(function (o, oi) {
      const on = pick === oi;
      let cls = 'qz-opt';
      if (st.graded) {
        if (oi === it.ans) cls += ' right';
        else if (on && oi !== it.ans) cls += ' wrong';
      } else if (on) cls += ' on';
      body += '<div class="' + cls + '"' + (st.graded ? '' : ' onclick="examPick(' + n + ',' + oi + ')"') + '><span class="ol">' + 'ABCD'[oi] + '</span><span>' + o + '</span></div>';
    });
    if (st.graded && pick !== it.ans) body += '<div class="qz-ana">' + ic('check', 13) + ' 正确答案 ' + 'ABCD'[it.ans] + ' · ' + it.ana + '</div>';
    body += '</div>';
  });
  const foot = st.graded
    ? '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>'
    : '<button class="btn btn-sec" onclick="closeDrawer()">暂存退出</button><button class="btn btn-pri" onclick="examSubmit()">交卷</button>';
  openDrawer('在线考试 · ' + q.title, body, foot, '640px');
  return body;
}
function examPick(n, oi) {
  state.qz.sel[n] = oi;
  const items = document.querySelectorAll('#dr-body .qz-item');
  const item = items && items[n];
  if (!item) return;
  const opts = item.querySelectorAll('.qz-opt');
  if (!opts) return;
  opts.forEach(function (o, i) { o.classList.toggle('on', i === oi); });
}
function examSa(n, v) { state.qz.ansTxt = state.qz.ansTxt || {}; state.qz.ansTxt[n] = v; }
function examSubmit() {
  const q = EXAMTK, st = state.qz;
  let miss = 0;
  q.qs.forEach(function (it, n) { if (!it.sa && st.sel[n] == null) miss++; });
  if (miss > 0) { toast('客观题还有 ' + miss + ' 题未作答', 'warn'); return; }
  let score = 0;
  q.qs.forEach(function (it, n) { if (!it.sa && st.sel[n] === it.ans) score += it.sc; });
  st.graded = true; st.score = score;
  renderExamTake();
  const passed = score >= q.pass;
  setTimeout(function () { toast(passed ? '客观题即时得分 ' + score + ' 分（及格线 60）· 简答题待阅卷后计最终成绩' : '客观题即时得分 ' + score + ' 分（低于及格线）· 简答题待阅卷', passed ? 'success' : 'error'); }, 120);
}
/* PERF：阅卷抽屉（简答题打分） */
function examGrade(i) {
  const r = RECORDS[i];
  const body = '<div style="padding:2px 4px">' +
    '<div class="card" style="padding:12px 14px;margin-bottom:12px;display:flex;gap:10px;align-items:center;background:rgba(0,113,227,.05)">' + ic('doc', 15) +
    '<span style="font-size:12.5px;line-height:1.5"><b>' + r.who + '</b> · ' + r.paper + '<br><span class="csub">客观题得分（自动判分）：<b style="color:var(--blue)">' + r.obj + ' / 80 分</b></span></span></div>' +
    '<div class="fld wide"><label>简答题作答内容</label>' +
    '<div class="qz-ana" style="margin-top:0;font-size:13px;color:var(--text)">' + (r.who === '苏杳' ? '起号思路：先用福利品 + 话术钩子拉停留，前 3 天集中投流测爆款，第七天根据人群标签复投放大……（省略）' : '围绕「人群 - 钩子 - 福利 - 投流」四步起号：先测试视频引流素材，直播间用高频福利品拉互动权重……（省略）') + '</div></div>' +
    frow([{ k: 'subscore', label: '简答题评分（0 ~ 20 分）', type: 'num', req: true, unit: '分', val: 15, ph: '0 ~ 20' }]) +
    '<div class="hint" style="display:flex;gap:8px;align-items:center;margin-top:4px">' + ic('warn', 13) + ' 阅卷成绩将自动计入「考试成绩」类绩效指标取数（PER-E-R4）；主观题须 48 小时内完成（PER-E-R2）。</div></div>';
  openDrawer('阅卷 · ' + r.no, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="examGradeSubmit(' + i + ')">提交成绩</button>', '480px');
}
function examGradeSubmit(i) {
  const r = RECORDS[i];
  if (!formValidate(['subscore'])) return;
  const v = Number($('#F_subscore').value);
  if (isNaN(v) || v < 0 || v > 20) { toast('简答题评分须在 0 ~ 20 分之间', 'error'); return; }
  r.sub = v; r.final = r.obj + v; r.st = '已判分';
  closeDrawer();
  if (state.page === 'perf') renderPage();
  toast('阅卷完成：' + r.who + ' 最终成绩 ' + r.final + ' 分，已计入绩效指标取数', 'success');
  hlFirst();
}
function perfAdd() {
  const body = frow([
    { k: 'name', label: '方案名称', type: 'text', req: true, ph: '如：主播/达人考核方案（直播）' },
    { k: 'cycle', label: '考核周期', type: 'select', opts: ['月度', '季度', '半年度', '年度'] },
    { k: 'dept', label: '适用部门', type: 'select', req: true, opts: ['主播组', '运营中心', '内容中心', '数据中心', '行政部', '财务部', '外协', '全公司'] },
    { k: 'weight', label: '指标权重说明', type: 'textarea', ph: '如：开播场次 30% · GMV 40% · 观看时长 20% · 粉丝增长 10%', wide: true }
  ]);
  openDrawer('新建考核方案', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="perfAddSubmit()">创建方案</button>', '480px');
}
function perfAddSubmit() {
  if (!formValidate(['name', 'dept'])) return;
  const no = 'PF202609-' + String(Math.floor(Math.random() * 90) + 10);
  formOk(no, '方案已创建并进入「草稿」状态，配置指标后可启用', '');
  toast('考核方案创建成功：' + $('#F_name').value.trim(), 'success');
}

/* ===================== 13 ALERT 预警 ===================== */
const ALERTS = [
  { lv: '红', rule: '账号风险分超阈值', obj: 'ACCT-2026-0087 · 抖音', t: '今天 13:05', dur: '2h 12m', st: '未处理' },
  { lv: '红', rule: '账号风险分超阈值', obj: 'ACCT-2026-0088 · 抖音', t: '今天 13:12', dur: '2h 05m', st: '未处理' },
  { lv: '红', rule: '账号风险分超阈值', obj: 'ACCT-2026-0091 · 快手', t: '今天 13:26', dur: '1h 51m', st: '未处理' },
  { lv: '红', rule: '证件到期 30 天', obj: '苏杳 · 居民身份证', t: '昨天 09:00', dur: '1d 5h', st: '处理中' },
  { lv: '橙', rule: '流程超时未流转', obj: 'FL20260912-07 · 报销', t: '今天 08:00', dur: '9h', st: '处理中' },
  { lv: '橙', rule: '账号充值异常', obj: 'ACCT-2026-0001 · 抖音', t: '昨天 16:40', dur: '21h', st: '已恢复' },
  { lv: '黄', rule: '日报提交率低于 85%', obj: '内容中心 · 周维度', t: '昨天 20:00', dur: '17h', st: '已忽略' },
  { lv: '黄', rule: '会议室冲突', obj: '3F-大会议室 16:00', t: '昨天 15:40', dur: '21h', st: '已恢复' },
  { lv: '橙', rule: '证件到期 90 天', obj: '孙倩 · 居民身份证', t: '09-10 09:00', dur: '2d 14h', st: '已恢复' },
  { lv: '红', rule: '风险分超阈值', obj: 'IMS202609090DY0125 · 场次', t: '09-09 10:12', dur: '已处置', st: '已恢复' }
];
PAGES.alert = function () {
  const cur = state.tab.alert || '实时预警';
  let h = pgHead('alert', '<button class="btn btn-pri" onclick="alertRuleAdd()">' + ic('plus', 15) + '新建规则</button>');
  const cnt = { 红: 0, 橙: 0, 黄: 0 };
  ALERTS.forEach(function (a) { cnt[a.lv]++; });
  /* ALERT-004 去重统计：同规则未处理告警分组，≥2 条的组可一键合并 */
  const groups = alertDedupGroups();
  const dupGroups = groups.filter(function (g) { return g.n >= 2; });
  const dupAlerts = dupGroups.reduce(function (s, g) { return s + g.n; }, 0);
  h += '<div class="g3"><div class="card stat" style="border-left:3px solid var(--red)"><span class="l">红色预警（高危）</span><div class="n neg">' + cnt['红'] + '</div><div class="d">需立即处理</div></div>' +
    '<div class="card stat" style="border-left:3px solid var(--orange)"><span class="l">橙色预警（重要）</span><div class="n" style="color:var(--orange)">' + cnt['橙'] + '</div><div class="d">24h 内处理</div></div>' +
    '<div class="card stat" style="border-left:3px solid var(--yellow)"><span class="l">黄色预警（提示）</span><div class="n" style="color:#a07d00">' + cnt['黄'] + '</div><div class="d">纳入周报跟踪</div></div></div>';
  h += '<div class="tabs">' + ['预警规则', '实时预警', '处理记录', '去重合并'].map(function (t) {
    const dg = groups.filter(function (g) { return g.n >= 2; }).length;
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'alert\',\'' + t + '\')">' + t + (t === '去重合并' && dg ? ' <span class="cbadge" style="background:var(--orange)">' + dg + '</span>' : '') + '</div>';
  }).join('') + '</div>';
  if (cur === '预警规则') {
    const rules = [
      { n: '账号风险分超阈值', c: '账号管理', d: '风险分 ≥ 85 触发', lv: '红', on: true },
      { n: '证件到期 30 天', c: '证件档案', d: '剩余有效期 ≤ 30 天', lv: '红', on: true },
      { n: '流程超时未流转', c: '工作流', d: '节点停留 > 24h', lv: '橙', on: true },
      { n: '账号充值异常', c: '账号管理', d: '7 天充值超 P95 分位', lv: '橙', on: true },
      { n: '日报提交率低于 85%', c: '日报', d: '部门周维度统计', lv: '黄', on: true },
      { n: '会议室冲突', c: '会议', d: '同会议室时段重叠', lv: '黄', on: true },
      { n: '毛利率低于 10%', c: '财务核算', d: '单场次毛利/收入 < 10%', lv: '橙', on: false },
      { n: '分摊合计超 120%', c: '组织人效', d: '人员主兼职分摊超标', lv: '黄', on: true }
    ];
    const lvc = { 红: 'red', 橙: 'orange', 黄: 'yellow' };
    let rows = '';
    rules.forEach(function (r) {
      rows += '<tr><td style="font-weight:500">' + r.n + '</td><td>' + r.c + '</td><td style="color:var(--text2);font-size:12px">' + r.d + '</td>' +
        '<td>' + tag(r.lv + '级', lvc[r.lv]) + '</td>' +
        '<td style="font-size:11.5px;color:var(--text2)">' + (r.lv === '红' ? '1h/4h/12h' : '2h/8h/24h') + ' <span style="color:var(--blue)">三级升级</span></td>' +
        '<td><span class="sw' + (r.on ? ' on' : '') + '" onclick="this.classList.toggle(\'on\');toast(\'规则已' + (r.on ? '停用' : '启用') + '\',\'success\')"><i></i></span></td>' +
        '<td><span class="btn btn-sec btn-sm" onclick="toast(\'规则编辑 · ' + r.n + ' · 原型示意\',\'success\')">编辑</span></td></tr>';
    });
    h += tbl(['规则名', '所属模块', '触发条件', '级别', '升级链（ALERT-003）', '启停', '操作'], rows);
    return h;
  }
  if (cur === '去重合并') return h + alertDedupTab();
  const isHist = cur === '处理记录';
  const list0 = isHist ? ALERTS.filter(function (a) { return a.st === '已恢复' || a.st === '已忽略'; }) : ALERTS;
  const lvc = { 红: 'red', 橙: 'orange', 黄: 'yellow' };
  const dotc = { 红: 'var(--red)', 橙: 'var(--orange)', 黄: 'var(--yellow)' };
  const stc = { '未处理': 'red', '处理中': 'blue', '已恢复': 'green', '已忽略': 'gray' };
  let rows = '';
  const list = qFilter(list0, function (a) { return [a.rule, a.obj]; }, function (a) { return a.lv + '|' + a.st; });
  /* ALERT-004：同规则分组计数（仅实时预警页） */
  const gcnt = {};
  if (!isHist) list.forEach(function (a) { gcnt[a.rule] = (gcnt[a.rule] || 0) + 1; });
  list.forEach(function (a) {
    const dup = !isHist && gcnt[a.rule] >= 2;
    rows += '<tr><td><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:' + dotc[a.lv] + '"></span> <b style="font-size:12.5px">' + a.lv + '</b></td>' +
      '<td style="font-weight:500">' + a.rule + (dup ? ' <span class="chip" style="background:rgba(255,159,10,.12);color:var(--orange);cursor:pointer" title="ALERT-004 同源告警" onclick="alertDedupView(\'' + a.rule + '\')">×' + gcnt[a.rule] + ' 同源</span>' : '') + '</td>' +
      '<td>' + a.obj + '</td><td class="num" style="font-size:12px">' + a.t + '</td><td class="num" style="color:var(--text2);font-size:12px">' + a.dur + '</td>' +
      '<td>' + tag(a.st, stc[a.st]) + '</td>' +
      '<td>' + (a.st === '未处理' ? '<button class="btn btn-pri btn-sm" onclick="alertHandle(' + ALERTS.indexOf(a) + ')">处理</button>' :
        a.st === '处理中' ? '<button class="btn btn-sec btn-sm" onclick="alertRecover(' + ALERTS.indexOf(a) + ')">标记恢复</button>' :
          '<span class="btn btn-sec btn-sm" onclick="toast(\'处理记录详情 · 原型示意\',\'success\')">记录</span>') + '</td></tr>';
  });
  h += qbar(qs(['全部级别', '红', '橙', '黄'], 90, (state.q.alert || {}).k0) + qs(['全部状态', '未处理', '处理中', '已恢复', '已忽略'], 100, (state.q.alert || {}).k1) + qi('对象关键词', 120, (state.q.alert || {}).k2), 'qSave(\'alert\')');
  h += tbl(['级别', '规则名', '对象', '触发时间', '持续', '状态', '操作'], rows);
  return h;
};
/* ALERT：处理（未处理 → 处理中；ALERT-003 三级升级时间线） */
function alertHandle(i) {
  const a = ALERTS[i];
  if (!a) return;
  const hour = Number((a.dur || '0h').replace(/h$/, '')) || 0;
  const chain = a.lv === '红' ? [[1, '直属主管'], [4, '部门负责人'], [12, '总监 + 短信']] : [[2, '直属主管'], [8, '部门负责人'], [24, '总监 + 短信']];
  const lvNow = chain.filter(function (c) { return hour >= c[0]; }).length;
  const tlHtml = chain.map(function (c, j) {
    const hit = hour >= c[0];
    return '<div class="tl-i ' + (hit ? (j === 2 ? 'oo' : 'oo') : '') + '"><div class="tt">' + (j + 1) + 'h 前'.replace('1h', c[0] + 'h') + '</div><div class="td">L' + (j + 1) + ' · ' + (hit ? '已升级至 ' + c[1] : c[0] + 'h 未处理时升级至 ' + c[1]) + '</div></div>';
  }).join('');
  const body = '<div class="kv">' +
    '<div><div class="k">规则</div><div class="v">' + a.rule + '</div></div><div><div class="k">对象</div><div class="v">' + a.obj + '</div></div>' +
    '<div><div class="k">级别</div><div class="v">' + a.lv + ' · 持续 ' + a.dur + '</div></div><div><div class="k">当前升级层级</div><div class="v">' + (lvNow ? 'L' + lvNow : '未升级') + '</div></div></div>' +
    '<div class="dsec">三级升级链（ALERT-003）</div><div class="tl">' + tlHtml + '</div>';
  openDrawer('预警处理 · ' + a.rule, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="alertHandleGo(' + i + ')">开始处理</button>', '480px');
}
function alertHandleGo(i) {
  const a = ALERTS[i];
  if (!a) return;
  confirmDlg('确认开始处理？', '预警「' + a.rule + '」（' + a.obj + '）将进入「处理中」状态，并指派给当前处理人，升级链停止。', '开始处理', function () {
    a.st = '处理中';
    if (state.page === 'alert') renderPage();
    closeDrawer();
    toast('已进入处理流程：' + a.rule + ' · ' + a.obj + '（升级链已停止）', 'success');
    hlFirst();
  }, { danger: a.lv === '红', warn: a.lv === '红' ? '红色高危预警，需 2 小时内完成处置' : '' });
}
/* ALERT：标记恢复（处理中 → 已恢复） */
function alertRecover(i) {
  const a = ALERTS[i];
  if (!a) return;
  confirmDlg('确认标记恢复？', '预警「' + a.rule + '」（' + a.obj + '）将标记为「已恢复」，并写入处理记录。', '标记恢复', function () {
    a.st = '已恢复';
    if (state.page === 'alert') renderPage();
    toast('已标记恢复：' + a.rule + ' · ' + a.obj, 'success');
    hlFirst();
  });
}

/* ===================== ALERT-004 去重合并与统计 ===================== */
/* 同规则分组（去重口径：规则名相同即视为同源；返回 [{rule, n, list, lvs}] 按数量降序） */
function alertDedupGroups() {
  const map = {};
  const order = [];
  ALERTS.forEach(function (a) {
    if (!map[a.rule]) { map[a.rule] = { rule: a.rule, list: [] }; order.push(a.rule); }
    map[a.rule].list.push(a);
  });
  const groups = order.map(function (r) { return map[r]; });
  groups.forEach(function (g) { g.n = g.list.length; });
  groups.sort(function (x, y) { return y.n - x.n; });
  return groups;
}
/* ALERT-004：去重合并 Tab（分组卡 + 统计 + 一键合并） */
function alertDedupTab() {
  const groups = alertDedupGroups();
  const dup = groups.filter(function (g) { return g.n >= 2; });
  const dupAlerts = dup.reduce(function (s, g) { return s + g.n; }, 0);
  const saved = dup.reduce(function (s, g) { return s + g.n - 1; }, 0);
  let h = '<div class="g4">' +
    '<div class="card stat"><span class="l">同源告警组</span><div class="n" style="color:var(--orange)">' + dup.length + '</div><div class="d">同规则 ≥2 条</div></div>' +
    '<div class="card stat"><span class="l">涉及告警</span><div class="n">' + dupAlerts + '</div><div class="d">合并前总条数</div></div>' +
    '<div class="card stat"><span class="l">合并后可减</span><div class="n" style="color:var(--green)">' + saved + ' 条</div><div class="d">ALERT-004 去重收益</div></div>' +
    '<div class="card stat"><span class="l">去重规则</span><div class="n" style="font-size:16px">规则名 + 时间窗</div><div class="d">5 分钟窗口内合并</div></div></div>' +
    '<div class="hint" style="margin-bottom:10px">同规则告警在 5 分钟时间窗内自动合并为一条主告警（保留计数与对象清单），避免风暴式重复推送；合并后一键处置全部同源对象（ALERT-004）。</div>';
  h += qbar(qs(['去重阈值', '全部', '≥2 条', '≥3 条'], 100) + qi('规则关键词', 130) + qs(['状态', '未处理', '处理中', '全部状态']));
  if (!dup.length) return h + tbl(['规则', '条数', '级别', '对象', '操作'], '');
  let rows = '';
  dup.forEach(function (g) {
    const i = ALERTS.indexOf(g.list[0]);
    const open = g.list.filter(function (a) { return a.st === '未处理'; }).length;
    rows += '<tr><td style="font-weight:500">' + g.rule + '</td>' +
      '<td class="num"><span class="chip" style="background:rgba(255,159,10,.12);color:var(--orange)">×' + g.n + '</span></td>' +
      '<td>' + g.list[0].lv + (g.list.some(function (a) { return a.lv !== g.list[0].lv; }) ? '<span style="font-size:11px;color:var(--text2)">（混合）</span>' : '') + '</td>' +
      '<td style="max-width:260px"><div class="rowline" style="gap:3px;flex-wrap:wrap">' + g.list.map(function (a) { return '<span class="chip" style="font-size:10.5px">' + a.obj + '</span>'; }).join('') + '</div></td>' +
      '<td>' + (open ? '<button class="btn btn-pri btn-sm" style="background:var(--orange)" onclick="alertDedupMerge(\'' + g.rule + '\')">合并处置（' + open + '）</button> ' : '') +
      '<span class="btn btn-sec btn-sm" onclick="alertDedupView(\'' + g.rule + '\')">明细</span></td></tr>';
  });
  h += tbl(['规则（同源）', '条数', '级别', '对象清单', '操作'], rows);
  return h;
}
/* ALERT-004：同源告警明细抽屉 */
function alertDedupView(rule) {
  const g = alertDedupGroups().filter(function (x) { return x.rule === rule; })[0];
  if (!g) return;
  const stc = { '未处理': 'red', '处理中': 'blue', '已恢复': 'green', '已忽略': 'gray' };
  let listHtml = '';
  g.list.forEach(function (a) {
    const i = ALERTS.indexOf(a);
    listHtml += '<tr><td>' + a.lv + '</td><td>' + a.obj + '</td><td class="num" style="font-size:11.5px">' + a.t + '</td><td>' + tag(a.st, stc[a.st]) + '</td>' +
      '<td>' + (a.st === '未处理' ? '<span class="btn btn-pri btn-sm" onclick="alertHandle(' + i + ')">处理</span>' : '—') + '</td></tr>';
  });
  const body = '<div class="kv"><div><div class="k">同源规则</div><div class="v">' + g.rule + '</div></div>' +
    '<div><div class="k">合并条数</div><div class="v">×' + g.n + '</div></div>' +
    '<div><div class="k">未处理</div><div class="v">' + g.list.filter(function (a) { return a.st === '未处理'; }).length + ' 条</div></div>' +
    '<div><div class="k">时间窗</div><div class="v">5 分钟内自动合并</div></div></div>' +
    '<div class="dsec">同源告警清单</div>' +
    '<div class="tbl-wrap"><table><thead><tr><th>级别</th><th>对象</th><th>触发时间</th><th>状态</th><th>操作</th></tr></thead><tbody>' + listHtml + '</tbody></table></div>';
  openDrawer('同源告警 · ' + g.rule, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (g.list.some(function (a) { return a.st === '未处理'; }) ? '<button class="btn btn-pri" style="background:var(--orange)" onclick="alertDedupMerge(\'' + g.rule + '\')">合并处置全部</button>' : ''), '640px');
}
/* ALERT-004：一键合并处置（同规则全部未处理 → 处理中） */
function alertDedupMerge(rule) {
  const g = alertDedupGroups().filter(function (x) { return x.rule === rule; })[0];
  if (!g) return;
  const open = g.list.filter(function (a) { return a.st === '未处理'; });
  if (!open.length) { toast('该规则下无未处理告警', 'warn'); return; }
  confirmDlg('合并处置 ' + open.length + ' 条同源告警？', '规则「' + rule + '」的 ' + g.n + ' 条告警将合并为一条工单统一处置（涉及 ' + open.map(function (a) { return a.obj; }).join('、') + '），处理结果同步至全部同源对象。', '合并处置', function () {
    open.forEach(function (a) { a.st = '处理中'; a.merged = true; });
    if (state.page === 'alert') renderPage();
    closeDrawer();
    toast('已合并处置：' + rule + ' · ' + open.length + ' 条同源告警进入处理流程', 'success');
    hlFirst();
  }, { warn: '合并处置将向全部 ' + open.length + ' 个同源对象的处理人发送通知' });
}
/* ALERT：新建预警规则表单 */
function alertRuleAdd() {
  const body = frow([
    { k: 'name', label: '规则名称', type: 'text', req: true, ph: '如：账号风险分超阈值' },
    { k: 'lv', label: '预警级别', type: 'pills', opts: ['高（红）', '中（橙）', '低（黄）'], val: '中（橙）' },
    { k: 'obj', label: '监控对象', type: 'select', req: true, opts: ['账号管理', '证件档案', '工作流', '日报', '会议', '财务核算', '组织人效', '直播管理'] },
    { k: 'cond', label: '触发条件', type: 'select', req: true, opts: ['风险分 ≥ 85 触发', '剩余有效期 ≤ 30 天', '节点停留 > 24h', '7 天充值超 P95 分位', '提交率 < 85%', '自定义表达式'] },
    { k: 'notify', label: '通知方式', type: 'pills', opts: ['站内', '钉钉', '站内 + 钉钉'], val: '站内 + 钉钉' },
    { k: 'note', label: '规则说明', type: 'textarea', ph: '处置建议、值班分组等（选填）', wide: true }
  ]) + '<div class="dsec">三级升级链（ALERT-003 · 未处理自动升级）</div>' +
    '<div class="kv" style="background:var(--bg);border-radius:10px;padding:12px 14px">' +
    '<div><div class="k">L1 · 2h 未处理</div><div class="v">升级至责任人直属主管</div></div>' +
    '<div><div class="k">L2 · 8h 未处理</div><div class="v">升级至部门负责人</div></div>' +
    '<div><div class="k">L3 · 24h 未处理</div><div class="v">升级至总监（Donny）+ 短信</div></div></div>' +
    '<div class="hint" style="margin-top:6px">红色高危预警升级时间减半（1h / 4h / 12h）；每级升级均记录处理时间线并计入响应率统计（BR-112/113）。</div>';
  openDrawer('新建预警规则', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="alertRuleAddSubmit()">创建规则</button>', '520px');
}
function alertRuleAddSubmit() {
  if (!formValidate(['name', 'obj', 'cond'])) return;
  const no = 'ALR202609-' + String(Math.floor(Math.random() * 90) + 10);
  formOk(no, '规则已创建并默认启用，触发后按通知方式推送', '');
  toast('预警规则创建成功：' + $('#F_name').value.trim(), 'success');
}


'use strict';
/* ===================== 04 COMP 竞品库 ===================== */
const COMPS = [
  { name: 'Keep 官方', plat: '抖音', fans: '486 万', works: 62, rate: '4.8%', trend: [12, 18, 15, 22, 19, 25, 21, 28, 24, 30], hot: '《21 天燃脂跟练》播放 1240 万' },
  { name: '刘畊宏', plat: '抖音', fans: '6123 万', works: 28, rate: '6.2%', trend: [30, 26, 22, 25, 19, 16, 14, 15, 12, 11], hot: '《本草纲目毽子操》二创季' },
  { name: '咕咚运动', plat: '视频号', fans: '132 万', works: 45, rate: '3.1%', trend: [8, 9, 11, 10, 12, 13, 12, 14, 15, 16], hot: '马拉松备赛系列' },
  { name: '悦跑圈', plat: '小红书', fans: '86 万', works: 55, rate: '5.4%', trend: [10, 12, 14, 13, 16, 18, 17, 19, 21, 23], hot: '跑鞋真香榜（月更）' },
  { name: '超级猩猩', plat: 'B 站', fans: '98 万', works: 38, rate: '2.9%', trend: [6, 7, 7, 8, 9, 8, 10, 9, 11, 10], hot: '团课教练 vlog' },
  { name: '帕梅拉 Pam', plat: 'B 站', fans: '1120 万', works: 41, rate: '5.8%', trend: [20, 22, 21, 23, 22, 24, 25, 23, 24, 26], hot: '10 分钟腹部训练' },
  { name: '跑者小站', plat: '快手', fans: '54 万', works: 51, rate: '3.6%', trend: [7, 8, 9, 9, 10, 11, 10, 12, 13, 12], hot: '晨跑打卡挑战' },
  { name: '健身教练艾伦', plat: '抖音', fans: '320 万', works: 58, rate: '4.2%', trend: [14, 16, 15, 17, 18, 17, 19, 20, 19, 21], hot: '哑铃全身循环' }
];
PAGES.comp = function () {
  let h = pgHead('comp', '<button class="btn btn-sec" onclick="exportX(this,\'竞品对比报告\',COMPS.length)">导出对比</button>' +
    '<button class="btn btn-pri" onclick="compAdd()">' + ic('plus', 15) + '新增竞品</button>');
  h += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">';
  COMPS.forEach(function (c, i) {
    h += '<div class="card hov" onclick="compDetail(' + i + ')"><div class="rowline" style="margin-bottom:10px">' +
      '<span class="av" style="background:linear-gradient(135deg,#0071e3,#5ac8fa)">' + c.name.slice(0, 1) + '</span>' +
      '<div style="min-width:0"><b style="font-size:14px;display:block;line-height:1.3">' + c.name + '</b><span style="font-size:11.5px;color:var(--text2)">' + c.plat + ' · 竞品</span></div></div>' +
      '<div class="kv" style="grid-template-columns:1fr 1fr 1fr;gap:8px;margin:0">' +
      '<div><div class="k">粉丝数</div><div class="v" style="font-size:14px">' + c.fans + '</div></div>' +
      '<div><div class="k">近30天作品</div><div class="v" style="font-size:14px">' + c.works + '</div></div>' +
      '<div><div class="k">互动率</div><div class="v" style="font-size:14px;color:var(--blue)">' + c.rate + '</div></div></div>' +
      '<div class="rowline" style="margin-top:12px;justify-content:space-between"><span style="font-size:11.5px;color:var(--text2)">代表作品已收录</span>' + ic('right', 13) + '</span></div></div>';
  });
  h += '</div>';
  return h;
};
function compDetail(i) {
  const c = COMPS[i];
  const max = Math.max.apply(null, c.trend);
  let bars = '';
  c.trend.forEach(function (v) { bars += '<div class="b" style="height:' + Math.max(8, Math.round(v / max * 100)) + '%;background:var(--purple)"></div>'; });
  const body = '<div class="rowline" style="margin-bottom:4px"><span class="av" style="width:44px;height:44px;font-size:18px;background:linear-gradient(135deg,#0071e3,#5ac8fa)">' + c.name.slice(0, 1) + '</span>' +
    '<div><b style="font-size:17px">' + c.name + '</b><div style="font-size:12px;color:var(--text2)">' + c.plat + ' · 竞品账号</div></div>' +
    '<span class="chip pp" style="margin-left:auto">已订阅监控</span></div>' +
    '<div class="dsec">基础信息</div><div class="kv">' +
    '<div><div class="k">粉丝数</div><div class="v">' + c.fans + '</div></div><div><div class="k">近 30 天作品数</div><div class="v">' + c.works + '</div></div>' +
    '<div><div class="k">互动率</div><div class="v" style="color:var(--blue)">' + c.rate + '</div></div><div><div class="k">更新频率</div><div class="v">约 ' + Math.round(c.works / 30 * 10) / 10 + ' 条/天</div></div></div>' +
    '<div class="dsec">近 30 天互动量趋势</div><div class="card" style="box-shadow:none;border:1px solid var(--line)"><div class="bars">' + bars + '</div><div class="rowline" style="justify-content:space-between;margin-top:6px"><span style="font-size:11px;color:var(--text2)">30 天前</span><span style="font-size:11px;color:var(--text2)">今天</span></div></div>' +
    '<div class="dsec">代表作品（Top 3）</div><div class="tbl-wrap"><table><thead><tr><th>作品</th><th>播放</th><th>发布</th></tr></thead><tbody>' +
    '<tr><td>' + c.hot + '</td><td class="num">1240 万</td><td class="num">09-02</td></tr>' +
    '<tr><td>品类知识合集（第 4 期）</td><td class="num">486 万</td><td class="num">09-08</td></tr>' +
    '<tr><td>新品开箱：秋季装备</td><td class="num">312 万</td><td class="num">09-11</td></tr></tbody></table></div>';
  openDrawer('竞品详情 · ' + c.name, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="compCompare(' + i + ')">加入对比</button>');
}
/* COMP：加入对比（确认 → 对比篮） */
let COMP_BASKET = [];
function compCompare(i) {
  const c = COMPS[i];
  if (COMP_BASKET.indexOf(c.name) >= 0) { toast('「' + c.name + '」已在对比篮中', 'warn'); return; }
  confirmDlg('加入对比篮？', '竞品「' + c.name + '」（' + c.plat + ' · 粉丝 ' + c.fans + '）将加入对比篮，当前对比篮 ' + COMP_BASKET.length + ' 个竞品。', '加入对比', function () {
    COMP_BASKET.push(c.name);
    toast('已加入对比篮（共 ' + COMP_BASKET.length + ' 个）：' + c.name, 'success');
  });
}
/* COMP：新增竞品表单 */
function compAdd() {
  const body = frow([
    { k: 'name', label: '竞品名称', type: 'text', req: true, ph: '如：Keep 官方' },
    { k: 'plat', label: '平台', type: 'select', opts: ['抖音', '视频号', '斗鱼', 'B 站', '小红书', '快手'] },
    { k: 'link', label: '主页链接', type: 'text', ph: 'https://…（选填）' },
    { k: 'fans', label: '粉丝数', type: 'text', ph: '如：486 万' },
    { k: 'note', label: '备注', type: 'textarea', ph: '监控重点、对标维度（选填）', wide: true }
  ]);
  openDrawer('新增竞品', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="compAddSubmit()">加入竞品库</button>', '480px');
}
function compAddSubmit() {
  if (!formValidate(['name'])) return;
  const no = 'CP202609-' + String(Math.floor(Math.random() * 90) + 10);
  COMPS.unshift({ name: $('#F_name').value.trim(), plat: $('#F_plat').value, fans: $('#F_fans').value.trim() || '—', works: 0, rate: '—', trend: [5, 6, 6, 7, 8, 8, 9, 10, 10, 11], hot: '待采集（监控已订阅）' });
  if (state.page === 'comp') renderPage();
  formOk(no, '竞品已加入竞品库，数据监控已自动订阅（次日生效）', '');
  toast('新增竞品成功：' + COMPS[0].name, 'success');
}

/* ===================== 12 DC 数据中心 ===================== */
PAGES.dc = function () {
  let h = pgHead('dc', '<button class="btn btn-sec" onclick="toast(\'数据字典 · 原型示意\',\'success\')">数据字典</button>' +
    '<button class="btn btn-pri" onclick="dcSync(this)">' + ic('db', 15) + '触发同步</button>');
  const stats = [
    { l: '账号实体', n: '56', d: '7 平台 · 86 在用' },
    { l: '资产实体', n: '128', d: '含 12 待盘点' },
    { l: '实名关系', n: '34', d: '人-账号绑定' },
    { l: '直播场次', n: '1,246', d: '累计入仓' },
    { l: '成本单据', n: '1,102', d: '关联率 99.3%' },
    { l: '利润记录', n: '1,098', d: '双口径核算' }
  ];
  h += '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px">';
  stats.forEach(function (s) {
    h += '<div class="card stat" style="padding:14px 14px"><span class="l">' + s.l + '</span><div class="n" style="font-size:20px">' + s.n + '</div><div class="d" style="font-size:11px">' + s.d + '</div></div>';
  });
  h += '</div>';
  /* 穿透链路 */
  const nodes = [
    ['账号', 'ACCT', '#0071e3'], ['资产', 'ASSET', '#34c759'], ['实名人', 'PERSON', '#af52da'],
    ['场次', 'LIVE', '#ff9500'], ['成本', 'COST', '#ff3b30'], ['利润', 'PROFIT', '#1e8e3e']
  ];
  const bw = 150, gap = 18;
  h += '<div class="sec">账号-资产-实名人-场次-成本-利润 · 双向穿透链路</div>' +
    '<div class="card" style="overflow-x:auto"><svg width="' + (nodes.length * bw + (nodes.length - 1) * gap + 8) + '" height="120" style="display:block;margin:auto">' +
    '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#86868b"/></marker></defs>';
  nodes.forEach(function (n, i) {
    const x = i * (bw + gap) + 4;
    if (i < nodes.length - 1) {
      h += '<line x1="' + (x + bw - 18) + '" y1="52" x2="' + (x + bw + gap - 20) + '" y2="52" stroke="#c7c7cc" stroke-width="1.6" marker-end="url(#ar)"/>';
    }
    h += '<g style="cursor:pointer" onclick="dcDrill(\'' + n[1] + '\')">' +
      '<rect x="' + x + '" y="26" width="' + (bw - 24) + '" height="52" rx="10" fill="' + n[2] + '" opacity="0.12"/>' +
      '<rect x="' + x + '" y="26" width="' + (bw - 24) + '" height="52" rx="10" fill="none" stroke="' + n[2] + '" stroke-width="1.2" opacity="0.5"/>' +
      '<text x="' + (x + (bw - 24) / 2) + '" y="50" text-anchor="middle" font-size="14" font-weight="600" fill="' + n[2] + '">' + n[0] + '</text>' +
      '<text x="' + (x + (bw - 24) / 2) + '" y="68" text-anchor="middle" font-size="10" fill="#86868b">' + n[1] + ' · 点击穿透</text></g>';
  });
  h += '</svg><div class="hint" style="text-align:center">点击任一节点即可沿链路双向穿透查询（账号 → 场次 → 成本 → 利润，或反向）</div></div>';
  /* 数据查询表 */
  h += '<div class="sec">穿透数据表</div>' + qbar(qs(['穿透起点：账号', '资产', '实名人', '场次', '成本', '利润']) + qi('编号 / 姓名', 130) + qs(['穿透深度', '1 层', '2 层', '全链路']));
  let rows = '';
  const dcData = [
    ['ACCT-2026-0001', '抖音 · 神鱼体育', 'AS20260901001', '苏杳', 'IMS202609100DY0131', fmtMoney(412800), fmtMoney(163620)],
    ['ACCT-2026-0002', '视频号 · 跑步研究所', 'AS20260902002', '李澈', 'IMS202609110DY0138', fmtMoney(186400), fmtMoney(72994)],
    ['ACCT-2026-0003', '斗鱼 · 电竞直播间', 'AS20260829004', '苏杳', 'IMS202609090DY0127', fmtMoney(96700), fmtMoney(31900)],
    ['ACCT-2026-0034', '快手 · 运动精选', '—', '苏杳', 'IMS202609070DY0118', fmtMoney(61200), fmtMoney(12898)]
  ];
  dcData.forEach(function (d) {
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + d[0] + '</td><td>' + d[1] + '</td><td class="mono" style="font-size:11.5px">' + d[2] + '</td><td>' + sens(d[3]) + '</td>' +
      '<td class="mono num" style="font-size:11.5px">' + d[4] + '</td><td class="num">' + d[5] + '</td><td class="num pos" style="font-weight:600">' + d[6] + '</td></tr>';
  });
  h += tbl(['账号编号', '平台 · 昵称', '绑定资产', '实名人', '代表场次', '场次收入', '净利润'], rows);
  return h;
};
function dcDrill(n) {
  const names = { ACCT: '账号', ASSET: '资产', PERSON: '实名人', LIVE: '场次', COST: '成本', PROFIT: '利润' };
  confirmDlg('发起「' + (names[n] || n) + '」节点穿透查询？', '将以 ' + n + ' 为起点沿链路双向穿透（账号 → 场次 → 成本 → 利润），查询结果将刷新下方穿透数据表。', '立即穿透', function () {
    toast('穿透查询完成：' + (names[n] || n) + ' 节点 · 返回 4 条链路记录', 'success');
  });
}
/* DC：触发同步（按钮转圈 → 结果反馈） */
function dcSync(btn) {
  btn.disabled = true;
  const raw = btn.innerHTML;
  btn.innerHTML = '<span class="spin"></span>同步中…';
  setTimeout(function () {
    btn.disabled = false;
    btn.innerHTML = raw;
    toast('数据同步完成：账号 56 · 资产 128 · 场次 1,246 · 失败 0', 'success');
  }, 1400);
}

/* ===================== 17 BI 数据分析 ===================== */
/* BI-002 多维下钻状态：state.bi.drill = { cat: '直播', rpt: '场次分析', path: ['全部平台','抖音'] } */
PAGES.bi = function () {
  let h = pgHead('bi', '<button class="btn btn-sec" onclick="biSubscribe()">订阅推送</button>' +
    '<button class="btn btn-pri" onclick="biAdd()">' + ic('plus', 15) + '新建报表</button>');
  const cats = { '运营': ['经营总览', '转化漏斗', '渠道对比'], '直播': ['场次分析', '主播榜', '风控看板'], '内容': ['作品表现', 'SOP 合规'], '财务': ['成本结构', '分成结算'], '绩效': ['人效总览', '评级分布'] };
  const dr = state.bi && state.bi.drill ? state.bi.drill : { cat: '直播', rpt: '场次分析', path: [] };
  let tree = '';
  Object.keys(cats).forEach(function (c, i) {
    tree += '<div class="nav-g' + (i === 0 ? '' : ' closed') + '"><div class="nav-g-h" style="padding:8px 6px" onclick="this.parentNode.classList.toggle(\'closed\')">' + c +
      '<span class="caret">' + ic('chev', 12) + '</span></div>';
    cats[c].forEach(function (r) {
      tree += '<div class="nav-item" style="padding:5px 8px;font-size:12px' + (dr.cat === c && dr.rpt === r ? ';background:var(--blue-bg);color:var(--blue);font-weight:500' : '') + '" onclick="biOpenRpt(\'' + c + '\',\'' + r + '\')">' + r + '</div>';
    });
    tree += '</div>';
  });
  /* GMV 折线（SVG） */
  const pts = [42, 55, 48, 63, 58, 72, 66, 80, 75, 88, 82, 96, 90, 104, 98, 112, 108, 122, 118, 132, 126, 140, 136, 148, 142, 156, 150, 164, 158, 172];
  const w = 640, hh = 150, max = 180;
  let path = '', dots = '';
  pts.forEach(function (v, i) {
    const x = 8 + i * ((w - 24) / (pts.length - 1));
    const y = hh - 14 - (v / max) * (hh - 34);
    path += (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1);
    dots += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="2.2" fill="#0071e3"/>';
  });
  const plat = [['抖音', 58], ['视频号', 18], ['斗鱼', 14], ['快手', 10]];
  const gmv = [['W1', 42], ['W2', 48], ['W3', 55], ['W4', 63], ['W5', 71], ['W6', 78]];
  /* BI-002：维度切换 + 面包屑下钻路径 + 明细表（按维度联动） */
  const dims = ['平台', '主播', '账号', '类目'];
  const curDim = state.bi && state.bi.dim ? state.bi.dim : '平台';
  const dimData = {
    '平台': [['抖音', 186400, 530, 42600], ['视频号', 412800, 3482, 88600], ['斗鱼', 96700, 744, 24500], ['快手', 61200, 512, 16800]],
    '主播': [['苏杳', 268300, 1980, 61200], ['李澈', 186400, 1226, 42600], ['王野', 128600, 990, 33400], ['赵敏', 96700, 744, 24500]],
    '账号': [['ACCT-2026-0001 · 抖音', 412800, 3482, 88600], ['ACCT-2026-0002 · 视频号', 186400, 1226, 42600], ['ACCT-2026-0003 · 斗鱼', 96700, 744, 24500], ['ACCT-2026-0034 · 快手', 61200, 512, 16800]],
    '类目': [['跑步鞋', 322400, 2680, 51200], ['健身器材', 218600, 1940, 42800], ['运动服饰', 168200, 1520, 38600], ['营养补给', 96400, 880, 24600]]
  };
  const drillPath = (state.bi && state.bi.drill && state.bi.drill.path) || [];
  let crumbs = '<div class="rowline" style="gap:4px;flex-wrap:wrap;align-items:center">' +
    '<span style="font-size:12px;color:var(--text2)">' + dr.cat + ' / ' + dr.rpt + '</span>';
  if (drillPath.length) {
    drillPath.forEach(function (p, j) {
      crumbs += '<span style="color:var(--text2);font-size:11px">›</span>' +
        '<span class="chip" style="cursor:pointer' + (j === drillPath.length - 1 ? ';background:var(--blue-bg);color:var(--blue)' : '') + '" onclick="biDrillUp(' + (j + 1) + ')">' + p + '</span>';
    });
    crumbs += '<span class="btn btn-sec btn-sm" style="margin-left:4px" onclick="biDrillReset()">重置</span>';
  } else {
    crumbs += '<span style="font-size:11.5px;color:var(--text2)">· 点击维度值可逐层下钻（全部 → 维度值 → 明细场次）</span>';
  }
  crumbs += '</div>';
  const drillLv = drillPath.length;
  let dimRows = '';
  if (drillLv === 0) {
    dimData[curDim].forEach(function (d) {
      dimRows += '<tr><td style="font-weight:500;cursor:pointer;color:var(--blue)" onclick="biDrillDown(\'' + d[0] + '\')">' + d[0] + ' <span style="font-size:10px">▾</span></td>' +
        '<td class="num" style="font-weight:500">' + fmtMoney(d[1]) + '</td><td class="num">' + d[2].toLocaleString() + '</td><td class="num">' + d[3].toLocaleString() + '</td>' +
        '<td><span class="btn btn-sec btn-sm" onclick="biDrillDown(\'' + d[0] + '\')">下钻</span></td></tr>';
    });
  } else {
    const val = drillPath[0];
    [['09-12', 'IMS202609110DY0138', 186400, 4.8, 1226], ['09-11', 'IMS202609100DY0131', 412800, 6.1, 3482], ['09-10', 'IMS202609090DY0127', 96700, 3.9, 744]].forEach(function (d) {
      dimRows += '<tr><td class="num">' + d[0] + '</td><td class="mono num" style="font-size:11.5px;color:var(--blue);cursor:pointer" onclick="toast(\'场次穿透：' + d[1] + '（联动直播管理）· 原型示意\',\'success\')">' + d[1] + '</td>' +
        '<td class="num" style="font-weight:500">' + fmtMoney(d[2]) + '</td><td class="num">' + d[3] + '%</td><td class="num">' + d[4].toLocaleString() + '</td></tr>';
    });
    dimRows = '<tr style="background:var(--blue-bg)"><td colspan="5" style="font-size:11.5px;padding:6px 10px;color:var(--blue)">下钻层级：' + val + ' · 场次明细（点击面包屑可回退）</td></tr>' + dimRows;
  }
  let rows = '';
  [['09-12', '抖音', 'IMS202609110DY0138', 186400, 4.8, 1226],
   ['09-11', '视频号', 'IMS202609100DY0131', 412800, 6.1, 3482],
   ['09-10', '斗鱼', 'IMS202609090DY0127', 96700, 3.9, 744],
   ['09-09', '快手', 'IMS202609070DY0118', 61200, 3.2, 512],
   ['09-08', '抖音', 'IMS202609080DY0121', 43800, 2.8, 388],
   ['09-07', '视频号', 'IMS202609060DY0112', 128600, 5.2, 1520],
   ['09-06', '抖音', 'IMS202609050DY0108', 152300, 4.4, 1826],
   ['09-05', '斗鱼', 'IMS202609040DY0105', 38200, 2.5, 298]].forEach(function (d) {
    rows += '<tr><td class="num">' + d[0] + '</td><td>' + d[1] + '</td><td class="mono num" style="font-size:11.5px;color:var(--blue)">' + d[2] + '</td>' +
      '<td class="num" style="font-weight:500">' + fmtMoney(d[3]) + '</td><td class="num">' + d[4] + '%</td><td class="num">' + d[5].toLocaleString() + '</td></tr>';
  });
  h += '<div class="g2r"><div><div class="card" style="padding:12px">' + tree + '</div></div>' +
    '<div><div class="card"><div class="hd-row"><h3>近 30 天 GMV 趋势</h3><span class="chip">直播 + 短视频</span></div>' +
    '<svg width="100%" viewBox="0 0 ' + w + ' ' + hh + '" style="display:block">' +
    '<line x1="0" y1="' + (hh - 14) + '" x2="' + w + '" y2="' + (hh - 14) + '" stroke="rgba(0,0,0,.08)"/>' +
    '<line x1="0" y1="' + ((hh - 14) / 2) + '" x2="' + w + '" y2="' + ((hh - 14) / 2) + '" stroke="rgba(0,0,0,.05)" stroke-dasharray="3 4"/>' +
    '<path d="' + path + '" fill="none" stroke="#0071e3" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>' + dots + '</svg>' +
    '<div class="rowline" style="justify-content:space-between;margin-top:4px"><span style="font-size:11px;color:var(--text2)">08-14</span><span style="font-size:11px;color:var(--text2)">09-12</span><span style="font-size:11px;color:var(--text2);font-weight:600;color:var(--blue)">累计 ¥412.8 万 · 环比 +18.6%</span></div></div>' +
    '<div class="card" style="margin-top:14px"><div class="hd-row"><h3>平台场次分布（本月）</h3><span style="font-size:12px;color:var(--text2)">共 14 场</span></div><div class="bars">' +
    plat.map(function (p) { return '<div class="b" style="height:' + Math.max(10, p[1] * 1.5) + '%;background:var(--blue)" title="' + p[0] + ' ' + p[1] + '%"></div>'; }).join('') + '</div>' +
    '<div class="rowline" style="justify-content:space-between;margin-top:6px">' + plat.map(function (p) { return '<span style="font-size:11.5px;color:var(--text2)">' + p[0] + ' ' + p[1] + '%</span>'; }).join('') + '</div></div>' +
    '<div class="card" style="margin-top:14px"><div class="hd-row"><h3>' + dr.rpt + ' · 多维下钻</h3>' +
    '<div class="pills" style="gap:4px">' + dims.map(function (dm) { return '<label class="pill' + (dm === curDim ? ' on' : '') + '" style="padding:2px 9px;font-size:11px"><input type="radio" name="P_bidim" value="' + dm + '"' + (dm === curDim ? ' checked' : '') + ' onchange="biSwitchDim(\'' + dm + '\')"><span>' + dm + '</span></label>'; }).join('') + '</div></div>' +
    '<div style="margin:6px 0 10px">' + crumbs + '</div>' +
    (drillLv === 0 ? tbl(['维度（' + curDim + '）· 点击下钻', 'GMV', '订单数', '观看人数', '操作'], dimRows) :
      tbl(['日期', '场次 ID · ' + (drillPath[0] || ''), 'GMV', '互动率', '观看人数'], dimRows)) + '</div>' +
    '<div class="card" style="margin-top:14px"><div class="hd-row"><h3>场次明细</h3></div>' +
    tbl(['日期', '平台', '场次 ID', 'GMV', '互动率', '观看人数'], rows) + '</div></div></div>';
  return h;
};
/* BI-002：打开报表（报表树点击） */
function biOpenRpt(cat, rpt) {
  if (!state.bi) state.bi = {};
  state.bi.drill = { cat: cat, rpt: rpt, path: [] };
  if (state.page === 'bi') renderPage();
  toast('已打开报表：' + cat + ' / ' + rpt + '（默认维度汇总 · 可下钻）', 'success');
}
/* BI-002：切换分析维度（平台/主播/账号/类目） */
function biSwitchDim(dim) {
  if (!state.bi) state.bi = {};
  state.bi.dim = dim;
  if (state.bi.drill) state.bi.drill.path = [];
  if (state.page === 'bi') renderPage();
  toast('已切换分析维度：' + dim + '（BI-002）', 'success');
}
/* BI-002：下钻（维度值 → 场次明细） */
function biDrillDown(val) {
  if (!state.bi) state.bi = {};
  if (!state.bi.drill) state.bi.drill = { cat: '直播', rpt: '场次分析', path: [] };
  state.bi.drill.path = [val];
  if (state.page === 'bi') renderPage();
  toast('下钻：' + (state.bi.dim || '平台') + ' → ' + val + '（显示场次明细）', 'success');
}
/* BI-002：面包屑回退（保留前 keep 层） */
function biDrillUp(keep) {
  if (state.bi && state.bi.drill) state.bi.drill.path = state.bi.drill.path.slice(0, keep);
  if (state.page === 'bi') renderPage();
  toast('已回退至第 ' + keep + ' 层下钻路径', 'success');
}
/* BI-002：重置下钻路径 */
function biDrillReset() {
  if (state.bi && state.bi.drill) state.bi.drill.path = [];
  if (state.page === 'bi') renderPage();
  toast('下钻路径已重置（返回维度汇总）', 'success');
}

/* BI：订阅推送（确认） */
function biSubscribe() {
  confirmDlg('订阅经营日报推送？', '每个工作日 09:00 将通过站内 + 钉钉推送「经营总览」日报（含 GMV、场次、成本、人效核心指标）。', '确认订阅', function () {
    toast('已订阅经营日报推送：每工作日 09:00', 'success');
  });
}
/* BI：新建报表表单 */
function biAdd() {
  const body = frow([
    { k: 'name', label: '报表名称', type: 'text', req: true, ph: '如：达人带货月度专题看板' },
    { k: 'dom', label: '数据域', type: 'select', req: true, opts: ['运营', '直播', '内容', '财务', '绩效'] },
    { k: 'chart', label: '图表类型', type: 'select', opts: ['折线图', '柱状图', '饼图', '漏斗图', '指标卡', '组合大屏'] },
    { k: 'freq', label: '刷新频率', type: 'pills', opts: ['实时', '日', '周'], val: '日' },
    { k: 'note', label: '指标口径说明', type: 'textarea', ph: '包含指标、口径定义、筛选维度（选填）', wide: true }
  ]);
  openDrawer('新建自定义报表', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="biAddSubmit()">创建报表</button>', '480px');
}
function biAddSubmit() {
  if (!formValidate(['name', 'dom'])) return;
  const no = 'BI202609-' + String(Math.floor(Math.random() * 90) + 10);
  formOk(no, '报表已创建，可在左侧报表树中打开并编辑图表', '');
  toast('报表创建成功：' + $('#F_name').value.trim(), 'success');
}

/* ===================== 19 EFF 组织人效 ===================== */
const EFFS = [
  { name: '苏杳', dept: '主播组', main: '主播组', part: ['内容中心', '运营中心'], mpct: 60, total: 135, score: 88 },
  { name: '赵敏', dept: '运营中心', main: '直播运营', part: [], mpct: 100, total: 100, score: 94 },
  { name: '孙倩', dept: '内容中心', main: '短视频', part: ['运营中心'], mpct: 70, total: 100, score: 85 },
  { name: '李澈', dept: '内容中心', main: '内容审核', part: [], mpct: 100, total: 100, score: 76 },
  { name: '何舟', dept: '运营中心', main: '运营总监', part: ['主播组'], mpct: 80, total: 110, score: 91 },
  { name: '陈默', dept: '数据中心', main: '数据分析', part: ['运营中心'], mpct: 75, total: 105, score: 86 },
  { name: '林岚', dept: '行政部', main: '行政支持', part: ['HR 共享'], mpct: 85, total: 115, score: 90 },
  { name: '周晴', dept: '财务部', main: '财务核算', part: [], mpct: 100, total: 100, score: 62 }
];
PAGES.eff = function () {
  let h = pgHead('eff', '<button class="btn btn-sec" onclick="exportX(this,\'人效月报\',EFFS.length)">导出月报</button>');
  const cards = [
    { l: '人均 GMV', n: '¥28.6 万', d: '环比 +9.2%' },
    { l: '人均场次 / 月', n: '4.8', d: '直播人员口径' },
    { l: '人均作品 / 月', n: '9.6', d: '短视频人员口径' },
    { l: '产能利用率', n: '87%', d: '分摊 >100% 共 4 人' }
  ];
  h += '<div class="g4">' + cards.map(function (c) {
    return '<div class="card stat"><span class="l">' + c.l + '</span><div class="n" style="font-size:21px">' + c.n + '</div><div class="d">' + c.d + '</div></div>';
  }).join('') + '</div>';
  h += qbar(qi('姓名', 100) + qs(['全部部门', '主播组', '运营中心', '内容中心', '数据中心', '行政部', '财务部']) + qs(['分摊状态', '全部', '正常', '超 100%']));
  let rows = '';
  EFFS.forEach(function (e) {
    const sc = e.score >= 90 ? 'var(--green)' : e.score >= 80 ? 'var(--blue)' : e.score >= 70 ? 'var(--orange)' : 'var(--red)';
    rows += '<tr><td style="font-weight:500">' + sens(e.name) + '</td><td>' + e.dept + '</td>' +
      '<td><span class="chip">' + e.main + '</span></td>' +
      '<td>' + (e.part.length ? e.part.map(function (p) { return '<span class="chip pp">' + p + '</span>'; }).join('') : '<span style="font-size:12px;color:var(--text2)">—</span>') + '</td>' +
      '<td><div class="rowline">' + pgbar(e.mpct) + '<span class="num" style="font-size:12px">' + e.mpct + '%</span></div></td>' +
      '<td class="num" style="font-weight:600;' + (e.total > 100 ? 'color:var(--red)' : '') + '">' + e.total + '%' + (e.total > 100 ? ' ⚠' : '') + '</td>' +
      '<td><div class="rowline"><span class="pg" style="width:52px"><i style="width:' + e.score + '%;background:' + sc + '"></i></span><span class="num" style="font-size:12px;font-weight:600">' + e.score + '</span></div></td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="toast(\'' + e.name + ' 人效详情 · 原型示意\',\'success\')">查看</span></td></tr>';
  });
  h += tbl(['姓名', '部门', '主归属', '兼职归属', '主归属工时占比', '分摊合计', '人效得分', '操作'], rows);
  return h;
};

/* ===================== 报销表单（工作台快捷入口） ===================== */
function finReimburse() {
  const body = frow([
    { k: 'type', label: '报销类型', type: 'select', opts: ['差旅费', '业务招待费', '设备采购', '推广投放', '办公费用', '其他'] },
    { k: 'amt', label: '报销金额', type: 'num', req: true, unit: '¥', ph: '0.00' },
    { k: 'reason', label: '事由', type: 'text', req: true, ph: '如：9 月大促直播间设备租赁' },
    { k: 'inv', label: '发票张数', type: 'num', unit: '张', val: 1, min: 1 },
    { k: 'file', label: '发票附件', type: 'file', ph: '点击上传发票扫描件（占位）', wide: true },
    { k: 'note', label: '备注', type: 'textarea', ph: '补充说明（选填）', wide: true }
  ]);
  openDrawer('费用报销申请', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="finReimburseSubmit()">提交报销单</button>', '480px');
}
function finReimburseSubmit() {
  if (!formValidate(['amt', 'reason'])) return;
  const no = 'BX20260912-' + String(Math.floor(Math.random() * 90) + 10);
  FLOWS.unshift({ id: 'FL20260912-' + String(FLOWS.length + 1).padStart(2, '0'), type: '报销', from: ROLES[state.role].user, node: '财务复核', approver: '周晴', cost: '0h', st: '审批中', chain: ['提交报销', '财务复核', '出纳付款', '归档'], ni: 1 });
  formOk(no, '报销单已提交，进入「财务复核」审批节点（审批人：周晴）', '');
  toast('报销单提交成功：' + no + ' · ' + fmtMoney(Number($('#F_amt').value || 0)), 'success');
}

/* ===================== 应用初始化 ===================== */
document.addEventListener('keydown', function (e) {
  if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault();
    const s = $('#gsearch');
    if (s) { s.focus(); toast('已聚焦全局搜索 · ⌘K', 'success'); }
  }
});
renderRoleMenu();
renderAll();
