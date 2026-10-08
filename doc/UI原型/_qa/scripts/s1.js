
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
  warn: 'M12 3l9 17H3zM12 10v4M12 17h.01',
  spark: 'M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z'
};
function ic(n, s) {
  s = s || 16;
  return '<svg width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="' + (IC[n] || IC.doc) + '"/></svg>';
}
function av(name, bg) { return '<span class="av" style="background:' + (bg || 'var(--blue)') + '">' + name.slice(0, 1) + '</span>'; }

/* ===================== 角色体系 ===================== */
const ROLES = {
  R1: { name: '系统管理员', user: 'Donny', modules: '*' },
  R2: { name: '行政管理员', user: '林岚', modules: ['home', 'workbench', 'cert', 'master', 'asset', 'acct', 'train', 'meet', 'report'] },
  R3: { name: '财务管理员', user: '周晴', modules: ['home', 'workbench', 'fin', 'cost', 'asset', 'acct', 'alert'] },
  R4: { name: '运营总监', user: '何舟', modules: ['home', 'workbench', 'ipg', 'live', 'content', 'collect', 'intWork', 'intAccount', 'compWork', 'compAccount', 'mon', 'cost', 'perf', 'report', 'comp', 'dc', 'bi', 'bi0', 'eff', 'alert'] },
  R5: { name: '直播运营', user: '赵敏', modules: ['home', 'workbench', 'ipg', 'live', 'content', 'collect', 'intWork', 'intAccount', 'compWork', 'compAccount', 'mon', 'acct', 'report'] },
  R6: { name: '短视频运营', user: '孙倩', modules: ['home', 'workbench', 'ipg', 'content', 'collect', 'intWork', 'intAccount', 'compWork', 'compAccount', 'mon', 'report'] },
  R7: { name: '主播/达人', user: '苏杳', modules: ['workbench', 'live', 'cert'] },
  R8: { name: '内容审核员', user: '李澈', modules: ['workbench', 'contentReview', 'contentList'] },
  R9: { name: '数据分析师', user: '陈默', modules: ['home', 'workbench', 'dc', 'bi', 'bi0', 'comp', 'eff', 'cert', 'acct', 'cost', 'intWork', 'intAccount', 'compWork', 'compAccount', 'mon'] },
  R10: { name: '外协人员', user: '王野', modules: ['workbench'] },
  R11: { name: 'AI 资产管理员', user: '唐宁', modules: ['workbench', 'airSkill', 'airExpert', 'airCfg'] }
};

/* ===================== 模块定义 ===================== */
const MODS = {
  home: { no: '00', name: '运营看板', code: 'HOME', icon: 'chart', page: '运营仪表盘', desc: 'IP 组筛选、核心指标、待办与快捷入口（OPS 并入）' },
  workbench: { no: '', name: '个人工作台', code: 'AUTH', icon: 'star', page: '工作台首页', desc: '待办中心与消息中心（AUTH-004）' },
  workbenchTodos: { no: '', name: '个人工作台', code: 'AUTH', icon: 'star', page: '待办中心', desc: '全部待办 · 筛选与处理闭环' },
  workbenchMsgs: { no: '', name: '个人工作台', code: 'AUTH', icon: 'star', page: '消息中心', desc: '站内信 · 已读未读与来源跳转' },
  authMgmt: { no: '01', name: '权限管理', code: 'AUTH', icon: 'shield', page: '权限管理', desc: '钉钉组织同步与岗位模板（AUTH-002/003 · 走查 #15）', navParent: true },
  authOrg: { no: '01', name: '组织架构同步', code: 'AUTH', icon: 'people', page: '组织架构同步', parent: '权限管理', desc: 'AUTH-002 · 人员/事件/对账 · GET /auth/org/*' },
  authPosition: { no: '01', name: '岗位模板', code: 'AUTH', icon: 'shield', page: '岗位模板', parent: '权限管理', desc: 'AUTH-003 · 岗位-权限矩阵 · dataScope' },
  sysMgmt: { no: '01', name: '系统管理', code: 'SYS', icon: 'db', page: '系统管理', desc: 'SYS-001～007 · OPS M9 同构迁入（走查 #15）', navParent: true },
  sysUser: { no: '01', name: '用户', code: 'SYS', icon: 'user', page: '用户管理', parent: '系统管理', desc: 'SYS-001 · system_users.id 只读 · 部门树' },
  sysRole: { no: '01', name: '角色', code: 'SYS', icon: 'shield', page: '角色权限', parent: '系统管理', desc: 'SYS-002 · 角色-菜单 · 兼容 ops:*' },
  sysMenu: { no: '01', name: '菜单', code: 'SYS', icon: 'doc', page: '菜单管理', parent: '系统管理', desc: 'SYS-003 · IMS 菜单树迁入' },
  sysDict: { no: '01', name: '字典', code: 'SYS', icon: 'db', page: '字典管理', parent: '系统管理', desc: 'SYS-004 · 系统+业务字典合并' },
  sysParam: { no: '01', name: '参数', code: 'SYS', icon: 'spark', page: '系统参数', parent: '系统管理', desc: 'SYS-005 · key 不改名（jingcai/审核/AIR/钉钉）' },
  sysLog: { no: '01', name: '日志', code: 'SYS', icon: 'doc', page: '操作/登录日志', parent: '系统管理', desc: 'SYS-006 · 操作+登录 · IMS 新写' },
  sysNotify: { no: '01', name: '通知', code: 'SYS', icon: 'bell', page: '消息通知', parent: '系统管理', desc: 'SYS-007 · 站内信+钉钉 · 事件去重' },
  asset: { no: '07', name: '资产管理', code: 'ASSET', icon: 'box', page: '资产台账', desc: '设备资产全生命周期登记与流转' },
  master: { no: '06', name: '主数据', code: 'MASTER', icon: 'id', page: '主数据台账', desc: '公司 / 实名人 / 手机 / 卡，强关联选择器' },
  acct: { no: '08', name: '账号管理', code: 'ACCT', icon: 'user', page: '账号台账', desc: '直播/短视频账号池统一管理与领用' },
  cert: { no: '06', name: '证件档案', code: 'CERT', icon: 'id', page: '证件档案', desc: '员工证件数字化存档与水印分级查看（IA 遗留 · 入口见资源管理·证件）' },
  corpAcct: { no: '08', name: '账号管理', code: 'CORP-A', icon: 'user', page: '账号管理', desc: 'UX-M4 平台账号 · 按平台 L3（走查 #8）', navParent: true },
  caWechatOfficial: { no: '08', name: '公众号', code: 'CORP-A', icon: 'user', page: '公众号', parent: '账号管理', desc: 'P-M4-008 · platform=WECHAT_OFFICIAL' },
  caWechatChannels: { no: '08', name: '视频号', code: 'CORP-A', icon: 'video', page: '视频号', parent: '账号管理', desc: 'P-M4-008 · WECHAT_CHANNELS + 采集 Tab' },
  caDouyin: { no: '08', name: '抖音', code: 'CORP-A', icon: 'film', page: '抖音', parent: '账号管理', desc: 'P-M4-008 · DOUYIN + ADR-047 采集 Tab' },
  caKuaishou: { no: '08', name: '快手', code: 'CORP-A', icon: 'film', page: '快手', parent: '账号管理', desc: 'P-M4-008 · KUAISHOU' },
  caXhs: { no: '08', name: '小红书', code: 'CORP-A', icon: 'book', page: '小红书', parent: '账号管理', desc: 'P-M4-008 · XIAOHONGSHU' },
  corpRes: { no: '06', name: '资源管理', code: 'CORP-R', icon: 'id', page: '资源管理', desc: '公司/实名人/手机卡/证件（走查 #8）', navParent: true },
  crCompany: { no: '06', name: '公司管理', code: 'CORP-R', icon: 'db', page: '公司管理', parent: '资源管理', desc: 'MASTER-002 · P-M4-001' },
  crRealname: { no: '06', name: '实名人管理', code: 'CORP-R', icon: 'user', page: '实名人管理', parent: '资源管理', desc: 'MASTER-001 · P-M4-003' },
  crSim: { no: '06', name: '手机卡管理', code: 'CORP-R', icon: 'phone', page: '手机卡管理', parent: '资源管理', desc: 'MASTER-004 · P-M4-006 · ADR-074' },
  crCert: { no: '06', name: '证件管理', code: 'CORP-R', icon: 'shield', page: '证件管理', parent: '资源管理', desc: 'CERT-001 · 索引入口 P-R4' },
  corpDev: { no: '07', name: '设备管理', code: 'CORP-D', icon: 'box', page: '设备管理', desc: '办公/直播/手机设备（走查 #8）', navParent: true },
  cdOffice: { no: '07', name: '办公设备管理', code: 'CORP-D', icon: 'box', page: '办公设备管理', parent: '设备管理', desc: 'ASSET-001 · asset_type=OFFICE BLOCKED' },
  cdLive: { no: '07', name: '直播设备管理', code: 'CORP-D', icon: 'video', page: '直播设备管理', parent: '设备管理', desc: 'ASSET-001 · LIVE/SHOOT BLOCKED' },
  cdPhone: { no: '07', name: '手机设备管理', code: 'CORP-D', icon: 'phone', page: '手机设备管理', parent: '设备管理', desc: 'MASTER-003 · P-M4-005 oa_phone' },
  ipg: { no: '19a', name: 'IP 组', code: 'IPG', icon: 'people', page: 'IP 组运营', desc: '大组小组、成员岗位、作者与账号绑定' },
  live: { no: '10', name: '直播管理', code: 'LIVE', icon: 'video', page: '直播管理', desc: '场次中心：列表→详情 Tab（数据/风控/下播）' },
  content: { no: '15', name: '内容生产', code: 'CONTENT', icon: 'film', page: '内容生产', desc: 'OPS M2 主路径 · 侧栏二级目录（与 10 直播管理并列，ADR-IMS-003）', navParent: true },
  contentSop: { no: '15', name: 'SOP管理', code: 'CONTENT', icon: 'flow', page: 'SOP 管理', parent: '内容生产', desc: 'SOP 模板列表与 DAG 编排（CONTENT-100/001 · UX P-M2-001/002）' },
  contentPlan: { no: '15', name: '计划管理', code: 'CONTENT', icon: 'cal', page: '计划管理', parent: '内容生产', desc: '营销计划 1:1 SOP + 计划向导（CONTENT-101/102 · P-M2-011）' },
  contentWork: { no: '15', name: '工作任务登记', code: 'CONTENT', icon: 'doc', page: '工作任务登记', parent: '内容生产', desc: '作者×赛事矩阵 · 确认出任务/撤回（CONTENT-104/105）' },
  contentTask: { no: '15', name: '我的任务', code: 'CONTENT', icon: 'check', page: '我的任务', parent: '内容生产', desc: '默认「我的任务」· 执行/提交审核/完成门禁（CONTENT-103 · P-M2-003）' },
  contentList: { no: '15', name: '内容管理', code: 'CONTENT', icon: 'film', page: '内容管理', parent: '内容生产', desc: '内容 CRUD · 玩法区 · AI 排版 · AI 视频脚本/成片（CONTENT-106/107）' },
  contentLayout: { no: '15', name: '公推模板库', code: 'CONTENT', icon: 'book', page: '公推模板库', parent: '内容生产', desc: '版式模板导入/编辑/预览（CONTENT-107 · P-M2-013~015）' },
  contentReview: { no: '15', name: '内容审核', code: 'CONTENT', icon: 'shield', page: '内容审核', parent: '内容生产', desc: '一级/二级审核队列（CONTENT-005 · P-M2-008）' },
  collect: { no: '16', name: '数据采集', code: 'COLLECT', icon: 'search', page: '数据采集', desc: 'OPS M8/M10 · 侧栏二级（任务/日志/外部/元数据/阈值）', navParent: true },
  collectTask: { no: '16', name: '采集任务', code: 'COLLECT', icon: 'check', page: '采集任务', parent: '数据采集', desc: 'UX-M10 P-M10-001/002 · Channel-A/B/C/D' },
  collectLog: { no: '16', name: '采集日志', code: 'COLLECT', icon: 'doc', page: '采集日志', parent: '数据采集', desc: 'UX-M10 P-M10-003 · typeResults 详情' },
  collectExtAccount: { no: '16', name: '竞品账号配置', code: 'COLLECT', icon: 'user', page: '竞品账号配置', parent: '数据采集', desc: 'UX-M8 外部账号 · 行内不嵌 Cookie（ADR-052）' },
  collectExtKeyword: { no: '16', name: '竞品关键字配置', code: 'COLLECT', icon: 'search', page: '竞品关键字配置', parent: '数据采集', desc: 'UX-M8 关键词配置 · 独立路由' },
  collectMetadata: { no: '16', name: '元数据维护', code: 'COLLECT', icon: 'db', page: '元数据维护', parent: '数据采集', desc: 'UX-M8 FR-M8-008 · 供 BI0 自定义查询消费' },
  collectThreshold: { no: '16', name: '阈值规则', code: 'COLLECT', icon: 'warn', page: '阈值规则', parent: '数据采集', desc: 'UX-M8 阈值 · ALERT/内部分析/竞品分析 引用' },
  intAnalysis: { no: '18b', name: '内部分析', code: 'INT', icon: 'chart', page: '内部分析', desc: 'OPS M1 内部作品/账号 + M7 阈值标签（走查 #7）', navParent: true },
  intWork: { no: '18b', name: '内部作品', code: 'INT', icon: 'film', page: '内部作品', parent: '内部分析', desc: 'Tab：全部/爆款/低分 · internal-content' },
  intAccount: { no: '18b', name: '内部账号', code: 'INT', icon: 'user', page: '内部账号', parent: '内部分析', desc: 'Tab：全部/高粉/低粉 · account-analysis' },
  compAnalysis: { no: '18a', name: '竞品分析', code: 'COMPA', icon: 'target', page: '竞品分析', desc: 'M7 监测 + V3 竞品库（走查 #6/#9）', navParent: true },
  compWork: { no: '18a', name: '竞品作品', code: 'COMPA', icon: 'film', page: '竞品作品', parent: '竞品分析', desc: 'Tab：全部/爆款/低分 · oa_external_work' },
  compAccount: { no: '18a', name: '竞品账号', code: 'COMPA', icon: 'user', page: '竞品账号', parent: '竞品分析', desc: 'Tab：全部/高粉/低粉 · oa_external_account' },
  comp: { no: '18a', name: '竞品库', code: 'COMP', icon: 'db', page: '竞品库', parent: '竞品分析', desc: 'V3 COMP-003 · BR-202 审核入库 · /ims/comp-analysis/library' },
  mon: { no: '18', name: '作品监测', code: 'MON', icon: 'target', page: '作品监测', desc: 'IP 主题/行业（内部→内部分析 · 外部→竞品分析）' },
  trainMgmt: { no: '02', name: '培训管理', code: 'TRAIN', icon: 'book', page: '培训管理', desc: '岗位资料库 · 学习任务 · 完成率（走查 #11 · V2 TRAIN）', navParent: true },
  trainMaterial: { no: '02', name: '培训资料库', code: 'TRAIN', icon: 'db', page: '岗位资料库', parent: '培训管理', desc: 'TRAIN-001 · /ims/train/material · 按岗位维护 DOC/VIDEO/LINK' },
  trainTask: { no: '02', name: '学习任务', code: 'TRAIN', icon: 'check', page: '学习任务管理', parent: '培训管理', desc: 'TRAIN-002 · 关联资料库 · AI 生成试卷（ADR-004 BLOCKED）' },
  trainStat: { no: '02', name: '完成率统计', code: 'TRAIN', icon: 'chart', page: '培训统计看板', parent: '培训管理', desc: 'TRAIN-003 · BR-102 完成率 / 逾期督办' },
  meet: { no: '03', name: '会议', code: 'MEET', icon: 'cal', page: '会议管理', desc: '会议室预约与会议纪要（MEET-004 · 与日报中心分路由）' },
  dailyCenter: { no: '03', name: '日报中心', code: 'MEET', icon: 'doc', page: '日报中心', desc: 'MEET-001～003 工作日报 · 走查 #10 与 09 分离', navParent: true },
  dailyMine: { no: '03', name: '我的日报', code: 'MEET', icon: 'doc', page: '我的日报', parent: '日报中心', desc: 'P2 · /ims/meet/daily 本人列表' },
  dailyTeam: { no: '03', name: '团队日报', code: 'MEET', icon: 'people', page: '团队日报', parent: '日报中心', desc: 'P2 · 下属/本部门列表' },
  dailyReview: { no: '03', name: '待我审阅', code: 'MEET', icon: 'check', page: '待我审阅', parent: '日报中心', desc: 'MEET-002 审阅队列' },
  dailyStat: { no: '03', name: '提交率统计', code: 'MEET', icon: 'chart', page: '提交率统计', parent: '日报中心', desc: 'MEET-003 · BR-103/104' },
  reportOps: { no: '09', name: '数据上报', code: 'REPORT', icon: 'doc', page: '数据上报', desc: 'REPORT-001～004 模板填报 · 非 MEET 日报', navParent: true },
  reportTpl: { no: '09', name: '上报模板', code: 'REPORT', icon: 'doc', page: '上报模板', parent: '数据上报', desc: 'REPORT-001 · /admin-api/ims/report/template' },
  reportSub: { no: '09', name: '填报单管理', code: 'REPORT', icon: 'check', page: '填报单管理', parent: '数据上报', desc: 'REPORT-002/003 · AuthorSelect+AccountSelect 必填' },
  reportRate: { no: '09', name: '完成率统计', code: 'REPORT', icon: 'chart', page: '完成率统计', parent: '数据上报', desc: 'REPORT-004 · BR-106' },
  flow: { no: '14', name: '工作流', code: 'FLOW', icon: 'flow', page: '流程管理', desc: '审批流程发起、流转与催办' },
  fin: { no: '11', name: '场次财务', code: 'FIN', icon: 'yuan', page: '成本核算', desc: '直播场次收入成本与主播分成结算' },
  cost: { no: '08b', name: '账号财务', code: 'COST', icon: 'yuan', page: '账号成本与 ROI', desc: '采购/过程成本；营收来自 Football 订单 WebAPI' },
  perfCenter: { no: '05', name: '绩效考核', code: 'PERF', icon: 'chart', page: '绩效考核', desc: '考核方案 → 执行考核 → 考核结果（走查 #12 · OPS M3）', navParent: true },
  perfScheme: { no: '05', name: '考核方案', code: 'PERF', icon: 'doc', page: '考核方案', parent: '绩效考核', desc: 'FR-M3-001 · /ims/perf/scheme · OPS 考核模板' },
  perfExec: { no: '05', name: '执行考核', code: 'PERF', icon: 'check', page: '执行考核', parent: '绩效考核', desc: 'FR-M3-002 · /ims/perf/execution · 算分/调整/确认' },
  perfResult: { no: '05', name: '考核结果', code: 'PERF', icon: 'chart', page: '考核结果', parent: '绩效考核', desc: 'FR-M3-003 · /ims/perf/result · 排名与 PIP' },
  perfExam: { no: '05', name: '在线考试', code: 'PERF', icon: 'doc', page: '在线考试', parent: '绩效考核', desc: 'PERF-003 · IMS 自建考试域' },
  biReportMgmt: { no: '17b', name: '数据报表', code: 'BI', icon: 'doc', page: '数据报表', desc: '走查 #17 v2.6.13 · 侧栏 4 叶', navParent: true },
  biList: { no: '17b', name: '报表管理', code: 'BI', icon: 'doc', page: '报表管理', parent: '数据报表', desc: '原报表目录 · 订阅页内 Tab（BI-003）' },
  biDesign: { no: '17b', name: '报表设计', code: 'BI', icon: 'spark', page: '报表设计器', parent: '数据报表', desc: 'BI-001 · /ims/bi/report/designer' },
  bi0Report: { no: '17a', name: '标准报表', code: 'BI0', icon: 'doc', page: '八张标准报表', parent: '数据报表', desc: 'FR-M6-002 · bi0Standard 兼容' },
  bi0Screen: { no: '17a', name: '大屏配置', code: 'BI0', icon: 'chart', page: '大屏配置', parent: '数据报表', desc: 'FR-M6-006/007 · bi0ScreenConfig 兼容' },
  biMetricMgmt: { no: '17a', name: '数据指标', code: 'BI0', icon: 'chart', page: '数据指标', desc: 'OPS M6 指标域 · 走查 #17', navParent: true },
  bi0Metric: { no: '17a', name: '指标管理', code: 'BI0', icon: 'chart', page: '指标管理', parent: '数据指标', desc: 'FR-M6-001 · /ims/bi/metric' },
  bi0Analysis: { no: '17a', name: '指标分析', code: 'BI0', icon: 'chart', page: '指标分析', parent: '数据指标', desc: 'FR-M6-001 分析视图 · P2' },
  biAnalysisMgmt: { no: '17', name: '数据分析', code: 'BI', icon: 'chart', page: '数据分析', desc: '走查 #17/#18 · 侧栏 5 叶', navParent: true },
  queryTool: { no: '17c', name: '查询工具', code: 'QT', icon: 'search', page: '查询工具', parent: '数据分析', desc: 'QT-001 · /ims/analysis/query-tool · DRILL|TRACE' },
  biPreview: { no: '17b', name: '预览与下钻', code: 'BI', icon: 'chart', page: '预览与下钻', parent: '数据分析', desc: 'BI-002 · 单元格穿透' },
  dc: { no: '12', name: '穿透查询', code: 'DC', icon: 'db', page: '穿透查询', parent: '数据分析', desc: 'DC-001 · /ims/dc/trace · 页内无 Tab' },
  eff: { no: '19b', name: '组织人效', code: 'EFF', icon: 'people', page: '组织人效', parent: '数据分析', desc: 'EFF · 页内 Tab 归属/盘点/看板' },
  bi0Query: { no: '17a', name: '自定义查询', code: 'BI0', icon: 'search', page: '自定义查询', parent: '数据分析', desc: 'FR-M6-005 · /ims/bi/query' },
  biShare: { no: '17b', name: '订阅与分享', code: 'BI', icon: 'bell', page: '订阅与分享', desc: 'BI-003 · 无侧栏 · go(biShare)→报表管理 Tab' },
  effRelation: { no: '19b', name: '归属关系', code: 'EFF', icon: 'user', page: '归属关系', parent: '数据分析', desc: 'EFF-001 · 兼容键 → eff Tab' },
  effInventory: { no: '19b', name: '人效盘点', code: 'EFF', icon: 'check', page: '人效盘点', parent: '数据分析', desc: 'EFF-002 · 兼容键 → eff Tab' },
  effBoard: { no: '19b', name: '人效看板', code: 'EFF', icon: 'chart', page: '人效看板', parent: '数据分析', desc: 'P3 · 兼容键 → eff Tab' },
  alertMgmt: { no: '13', name: '预警中心', code: 'ALERT', icon: 'bell', page: '预警中心', desc: 'ALERT-001~004 · 走查 #17', navParent: true },
  alertRule: { no: '13', name: '预警规则', code: 'ALERT', icon: 'shield', page: '预警规则', parent: '预警中心', desc: 'ALERT-001 · 阈值只读引用 COLLECT' },
  alertLive: { no: '13', name: '实时预警', code: 'ALERT', icon: 'bell', page: '实时预警', parent: '预警中心', desc: 'ALERT-002/003 + 处置记录 Tab' },
  alertHistory: { no: '13', name: '处置记录', code: 'ALERT', icon: 'doc', page: '处置记录', parent: '预警中心', desc: '兼容键 → alertLive Tab' },
  alertDedup: { no: '13', name: '去重合并', code: 'ALERT', icon: 'warn', page: '去重合并', parent: '预警中心', desc: 'ALERT-004 · 兼容键 → alertLive Tab' },
  airSkill: { no: '20', name: '技能库', code: 'AIR', icon: 'spark', page: '技能库', desc: 'AI 技能登记、审核、版本与授权分发' },
  airExpert: { no: '20', name: '专家库', code: 'AIR', icon: 'star', page: '专家库', desc: '专家包组装（Prompt+技能+知识）与授权' },
  airKb: { no: '20', name: '知识库', code: 'AIR', icon: 'book', page: '知识库', desc: '知识入库审批、密级管理与 RAGFlow 底座' },
  airKey: { no: '20', name: 'Key 管理', code: 'AIR', icon: 'shield', page: 'Key 管理', desc: '人员 API Key 生成、生命周期与白名单' },
  airCfg: { no: '20', name: '模型与提示词', code: 'AIR', icon: 'spark', page: '模型连接 / 提示词', desc: 'OPS AI 模型与提示词收编；禁止两套 Key' },
  airLog: { no: '20', name: '审计监控', code: 'AIR', icon: 'chart', page: '审计监控', desc: 'MCP 调用审计、用量统计与 RAGFlow 健康' }
};
/* 业务域分组（用户视角）：日常作业 → 资源 → 财务 → 协同 → 决策 → 系统 */
const GROUPS = [
  ['工作台', ['home', 'workbench']],
  ['日常运营', ['ipg', 'live', { type: 'sub', id: 'content', label: '内容生产', children: ['contentSop', 'contentPlan', 'contentWork', 'contentTask', 'contentList', 'contentLayout', 'contentReview'] }, { type: 'sub', id: 'collect', label: '数据采集', children: ['collectTask', 'collectLog', 'collectExtAccount', 'collectExtKeyword', 'collectMetadata', 'collectThreshold'] }, { type: 'sub', id: 'intAnalysis', label: '内部分析', children: ['intWork', 'intAccount'] }, { type: 'sub', id: 'compAnalysis', label: '竞品分析', children: ['compWork', 'compAccount', 'comp'] }, 'mon']],
  ['公司资产', [
    { type: 'sub', id: 'corpAcct', label: '账号管理', children: ['caWechatOfficial', 'caWechatChannels', 'caDouyin', 'caKuaishou', 'caXhs'] },
    { type: 'sub', id: 'corpRes', label: '资源管理', children: ['crCompany', 'crRealname', 'crSim', 'crCert'] },
    { type: 'sub', id: 'corpDev', label: '设备管理', children: ['cdOffice', 'cdLive', 'cdPhone'] }
  ]],
  ['财务', ['cost', 'fin']],
  ['协同与成长', ['meet', { type: 'sub', id: 'dailyCenter', label: '日报中心', children: ['dailyMine', 'dailyTeam', 'dailyReview', 'dailyStat'] }, { type: 'sub', id: 'reportOps', label: '数据上报', children: ['reportTpl', 'reportSub', 'reportRate'] }, { type: 'sub', id: 'trainCenter', label: '培训管理', children: ['trainMaterial', 'trainTask', 'trainStat'] }, { type: 'sub', id: 'perfCenter', label: '绩效考核', children: ['perfScheme', 'perfExec', 'perfResult', 'perfExam'] }, 'flow']],
  ['数据决策', [
    { type: 'sub', id: 'biReportMgmt', label: '数据报表', children: ['biList', 'biDesign', 'bi0Report', 'bi0Screen'] },
    { type: 'sub', id: 'biMetricMgmt', label: '数据指标', children: ['bi0Metric', 'bi0Analysis'] },
    { type: 'sub', id: 'biAnalysisMgmt', label: '数据分析', children: ['queryTool', 'bi0Query', 'biPreview', 'dc', 'eff'] },
    { type: 'sub', id: 'alertMgmt', label: '预警中心', children: ['alertRule', 'alertLive'] }
  ]],
  ['AI 资源中心', ['airSkill', 'airExpert', 'airCfg']],
  ['系统与权限', [
    { type: 'sub', id: 'authMgmt', label: '权限管理', children: ['authOrg', 'authPosition'] },
    { type: 'sub', id: 'sysMgmt', label: '系统管理', children: ['sysUser', 'sysRole', 'sysMenu', 'sysDict', 'sysParam', 'sysLog', 'sysNotify'] }
  ]]
];
const PAGES = {}; /* 各模块渲染函数注册表 */

/* AIR：走查 #14 主导航仅三叶；Deferred 页保留 PAGES 供专家 mock 引用，go() 重定向 */
const AIR_NAV_IDS = ['airSkill', 'airExpert', 'airCfg'];
const AIR_DEFERRED_IDS = ['airKb', 'airKey', 'airLog'];
function airNorm(id) {
  if (id === 'air') return 'airSkill';
  if (AIR_DEFERRED_IDS.indexOf(id) >= 0) return 'airSkill';
  return id;
}
/* CONTENT 子菜单（OPS M2 主路径 · ADR-IMS-003） */
const CONTENT_IDS = ['contentSop', 'contentPlan', 'contentWork', 'contentTask', 'contentList', 'contentLayout', 'contentReview'];
const CONTENT_ROUTE = {
  contentSop: '/ims/content/sop',
  contentPlan: '/ims/content/plan',
  contentWork: '/ims/content/work-task',
  contentTask: '/ims/content/task',
  contentList: '/ims/content/list',
  contentLayout: '/ims/content/layout-template',
  contentReview: '/ims/content/review'
};
function contentNorm(id) {
  if (id === 'content') return 'contentWork';
  return id;
}
function collectNorm(id) {
  if (id === 'collect') return 'collectTask';
  return id;
}
function intAnalysisNorm(id) {
  if (id === 'intAnalysis') return 'intWork';
  return id;
}
function compAnalysisNorm(id) {
  if (id === 'compAnalysis') return 'compWork';
  return id;
}
function dailyCenterNorm(id) {
  if (id === 'dailyCenter') return 'dailyMine';
  return id;
}
function reportOpsNorm(id) {
  if (id === 'reportOps') return 'reportSub';
  return id;
}
/** 走查 #11：废止单页 train Tab → 培训资料库 */
function trainNorm(id) {
  if (id === 'train' || id === 'trainMgmt' || id === 'trainCenter') return 'trainMaterial';
  return id;
}
/** 走查 #10：旧单页 id report（09 编号 + 日报 Tab）→ 我的日报 */
function legacyReportNorm(id) {
  if (id === 'report') return 'dailyMine';
  return id;
}
const TRAIN_IDS = ['trainMaterial', 'trainTask', 'trainStat'];
const TRAIN_ROUTE = {
  trainMaterial: '/ims/train/material',
  trainTask: '/ims/train/task',
  trainStat: '/ims/train/stat'
};
/** 走查 #12：废止单页 perf Tab → 考核方案 */
function perfNorm(id) {
  if (id === 'perf' || id === 'perfCenter') return 'perfScheme';
  return id;
}
/** 走查 #15：废止单页 auth Tab → 组织架构同步 */
function authNorm(id) {
  if (id === 'auth' || id === 'authMgmt') return 'authOrg';
  return id;
}
/** 走查 #15：废止单页 sys Tab → 用户 */
function sysNorm(id) {
  if (id === 'sys' || id === 'sysMgmt') return 'sysUser';
  return id;
}
const AUTH_IDS = ['authOrg', 'authPosition'];
const SYS_IDS = ['sysUser', 'sysRole', 'sysMenu', 'sysDict', 'sysParam', 'sysLog', 'sysNotify'];
const AUTH_ROUTE = { authOrg: '/ims/auth/org', authPosition: '/ims/auth/position' };
const SYS_ROUTE = {
  sysUser: '/ims/system/user',
  sysRole: '/ims/system/role',
  sysMenu: '/ims/system/menu',
  sysDict: '/ims/system/dict',
  sysParam: '/ims/system/param',
  sysLog: '/ims/system/log',
  sysNotify: '/ims/system/notify'
};
const PERF_IDS = ['perfScheme', 'perfExec', 'perfResult', 'perfExam'];
const PERF_ROUTE = {
  perfScheme: '/ims/perf/scheme',
  perfExec: '/ims/perf/execution',
  perfResult: '/ims/perf/result',
  perfExam: '/ims/perf/exam'
};
/** 走查 #17：数据决策 — 四 L2 组 · 兼容废止键 */
const BI_REPORT_NAV_IDS = ['biList', 'biDesign', 'bi0Report', 'bi0Screen'];
const BI_REPORT_ORPHAN_IDS = ['biShare'];
const BI_REPORT_IDS = BI_REPORT_NAV_IDS.concat(BI_REPORT_ORPHAN_IDS);
const BI_METRIC_IDS = ['bi0Metric', 'bi0Analysis'];
const BI0_ORPHAN_IDS = ['bi0Report', 'bi0Query', 'bi0Screen'];
const BI_ANALYSIS_NAV_IDS = ['queryTool', 'bi0Query', 'biPreview', 'dc', 'eff'];
const BI_ANALYSIS_ORPHAN_IDS = [];
const BI_ANALYSIS_IDS = BI_ANALYSIS_NAV_IDS.concat(BI_ANALYSIS_ORPHAN_IDS);
const EFF_TAB_IDS = ['effRelation', 'effInventory', 'effBoard'];
const ALERT_IDS = ['alertRule', 'alertLive', 'alertHistory', 'alertDedup'];
const BI_IDS = BI_REPORT_IDS.concat(['biPreview']);
function bi0Norm(id) {
  if (id === 'bi0Standard') return 'bi0Report';
  if (id === 'bi0ScreenConfig') return 'bi0Screen';
  if (id === 'bi0' || id === 'bi0Mgmt' || id === 'biMetricMgmt') return 'bi0Metric';
  return id;
}
function biNorm(id) {
  if (id === 'bi' || id === 'biMgmt' || id === 'biReportMgmt') return 'biList';
  if (id === 'biShare') { state.tab.biList = 'share'; return 'biList'; }
  if (id === 'biSession') return 'dc';
  if (id === 'biWorks') return 'mon';
  return id;
}
function effNorm(id) {
  if (id === 'effIpg') return 'ipg';
  if (id === 'effMgmt' || id === 'effRelation' || id === 'effInventory' || id === 'effBoard') return 'eff';
  return id;
}
function alertNorm(id) {
  if (id === 'alert' || id === 'alertMgmt') return 'alertLive';
  if (id === 'alertHistory' || id === 'alertDedup') return 'alertLive';
  return id;
}
function hasBiReportBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('bi') >= 0 || r.modules.indexOf('biMgmt') >= 0 || r.modules.indexOf('biReportMgmt') >= 0) return true;
  return BI_REPORT_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasBiMetricBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('bi0') >= 0 || r.modules.indexOf('bi0Mgmt') >= 0 || r.modules.indexOf('biMetricMgmt') >= 0) return true;
  return BI_METRIC_IDS.concat(BI0_ORPHAN_IDS).some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasBiAnalysisBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('dc') >= 0 || r.modules.indexOf('eff') >= 0 || r.modules.indexOf('effMgmt') >= 0 || r.modules.indexOf('biAnalysisMgmt') >= 0) return true;
  return BI_ANALYSIS_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; }) ||
    EFF_TAB_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasAlertBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('alert') >= 0 || r.modules.indexOf('alertMgmt') >= 0) return true;
  return ALERT_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function isPerfPage() { return PERF_IDS.indexOf(state.page) >= 0; }
function isTrainPage() { return TRAIN_IDS.indexOf(state.page) >= 0; }
function isContentPage() { return CONTENT_IDS.indexOf(state.page) >= 0; }
const COLLECT_IDS = ['collectTask', 'collectLog', 'collectExtAccount', 'collectExtKeyword', 'collectMetadata', 'collectThreshold'];
const INT_ANALYSIS_IDS = ['intWork', 'intAccount'];
const COMP_ANALYSIS_IDS = ['compWork', 'compAccount', 'comp'];
const DAILY_IDS = ['dailyMine', 'dailyTeam', 'dailyReview', 'dailyStat'];
const REPORT_DATA_IDS = ['reportTpl', 'reportSub', 'reportRate'];
const DAILY_ROUTE = {
  dailyMine: '/ims/meet/daily',
  dailyTeam: '/ims/meet/daily',
  dailyReview: '/ims/meet/daily',
  dailyStat: '/ims/meet/stat'
};
const REPORT_ROUTE = {
  reportTpl: '/ims/report/template',
  reportSub: '/ims/report/submission',
  reportRate: '/ims/report/stat'
};
function isDailyPage() { return DAILY_IDS.indexOf(state.page) >= 0; }
function isReportDataPage() { return REPORT_DATA_IDS.indexOf(state.page) >= 0; }
function refreshDailyOrReportPage() { if (isDailyPage() || isReportDataPage()) renderPage(); }
const CORP_ACCT_IDS = ['caWechatOfficial', 'caWechatChannels', 'caDouyin', 'caKuaishou', 'caXhs'];
const CORP_RES_IDS = ['crCompany', 'crRealname', 'crSim', 'crCert'];
const CORP_DEV_IDS = ['cdOffice', 'cdLive', 'cdPhone'];
const CORP_PLAT = {
  caWechatOfficial: { plat: '公众号', dict: 'WECHAT_OFFICIAL', collect: false },
  caWechatChannels: { plat: '视频号', dict: 'WECHAT_CHANNELS', collect: true },
  caDouyin: { plat: '抖音', dict: 'DOUYIN', collect: true },
  caKuaishou: { plat: '快手', dict: 'KUAISHOU', collect: true },
  caXhs: { plat: '小红书', dict: 'XIAOHONGSHU', collect: false }
};
function corpAcctNorm(id) {
  if (id === 'corpAcct' || id === 'acct') return 'caDouyin';
  return id;
}
function corpResNorm(id) {
  if (id === 'corpRes' || id === 'master') return 'crCompany';
  if (id === 'cert') return 'crCert';
  return id;
}
function corpDevNorm(id) {
  if (id === 'corpDev' || id === 'asset') return 'cdLive';
  return id;
}
function isCollectPage() { return COLLECT_IDS.indexOf(state.page) >= 0; }
function isIntAnalysisPage() { return INT_ANALYSIS_IDS.indexOf(state.page) >= 0; }
function isCompAnalysisPage() { return COMP_ANALYSIS_IDS.indexOf(state.page) >= 0; }
function isNavSub(entry) { return entry && typeof entry === 'object' && entry.type === 'sub'; }
function contentSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function collectSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function intAnalysisSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function compAnalysisSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function corpAcctSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function corpResSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function corpDevSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function dailySubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function reportOpsSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function navSubVisible(sub) {
  if (sub.id === 'content') return contentSubVisible(sub.children);
  if (sub.id === 'collect') return collectSubVisible(sub.children);
  if (sub.id === 'intAnalysis') return intAnalysisSubVisible(sub.children);
  if (sub.id === 'compAnalysis') return compAnalysisSubVisible(sub.children);
  if (sub.id === 'corpAcct') return corpAcctSubVisible(sub.children);
  if (sub.id === 'corpRes') return corpResSubVisible(sub.children);
  if (sub.id === 'corpDev') return corpDevSubVisible(sub.children);
  if (sub.id === 'dailyCenter') return dailySubVisible(sub.children);
  if (sub.id === 'reportOps') return reportOpsSubVisible(sub.children);
  if (sub.id === 'trainMgmt' || sub.id === 'trainCenter') return trainSubVisible(sub.children);
  if (sub.id === 'perfCenter') return perfSubVisible(sub.children);
  if (sub.id === 'biReportMgmt') return sub.children.filter(function (cid) { return canAccess(cid); });
  if (sub.id === 'biMetricMgmt') return sub.children.filter(function (cid) { return canAccess(cid); });
  if (sub.id === 'biAnalysisMgmt') return sub.children.filter(function (cid) { return canAccess(cid); });
  if (sub.id === 'alertMgmt') return sub.children.filter(function (cid) { return canAccess(cid); });
  if (sub.id === 'authMgmt') return authSubVisible(sub.children);
  if (sub.id === 'sysMgmt') return sysSubVisible(sub.children);
  return sub.children.filter(function (cid) { return canAccess(cid); });
}
function trainSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function perfSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function authSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function sysSubVisible(children) {
  return children.filter(function (cid) { return canAccess(cid); });
}
function hasAuthBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('auth') >= 0 || r.modules.indexOf('authMgmt') >= 0) return true;
  return AUTH_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasSysBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('sys') >= 0 || r.modules.indexOf('sysMgmt') >= 0) return true;
  return SYS_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasTrainBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('trainMgmt') >= 0 || r.modules.indexOf('trainCenter') >= 0 || r.modules.indexOf('train') >= 0) return true;
  return TRAIN_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasPerfBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('perf') >= 0 || r.modules.indexOf('perfCenter') >= 0) return true;
  return PERF_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasDailyBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('dailyCenter') >= 0) return true;
  return DAILY_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; }) || r.modules.indexOf('report') >= 0;
}
function hasReportDataBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('reportOps') >= 0) return true;
  return REPORT_DATA_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; }) || r.modules.indexOf('report') >= 0;
}
function hasContentBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('content') >= 0) return true;
  return CONTENT_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasCollectBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('collect') >= 0) return true;
  return COLLECT_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasIntAnalysisBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('intAnalysis') >= 0) return true;
  return INT_ANALYSIS_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasCompAnalysisBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('compAnalysis') >= 0) return true;
  if (r.modules.indexOf('comp') >= 0) return true;
  return COMP_ANALYSIS_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasCorpAcctBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('corpAcct') >= 0 || r.modules.indexOf('acct') >= 0) return true;
  return CORP_ACCT_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasCorpResBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('corpRes') >= 0 || r.modules.indexOf('master') >= 0 || r.modules.indexOf('cert') >= 0) return true;
  return CORP_RES_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function hasCorpDevBundle(r) {
  if (r.modules === '*') return true;
  if (r.modules.indexOf('corpDev') >= 0 || r.modules.indexOf('asset') >= 0) return true;
  return CORP_DEV_IDS.some(function (cid) { return r.modules.indexOf(cid) >= 0; });
}
function canAccess(id) {
  const r = ROLES[state.role];
  id = alertNorm(effNorm(biNorm(bi0Norm(trainNorm(legacyReportNorm(sysNorm(authNorm(corpDevNorm(corpResNorm(corpAcctNorm(compAnalysisNorm(intAnalysisNorm(collectNorm(contentNorm(airNorm(id))))))))))))))));
  if (id === 'workbenchTodos' || id === 'workbenchMsgs') {
    return r.modules === '*' || r.modules.indexOf('workbench') >= 0;
  }
  if (id === 'content') return hasContentBundle(r);
  if (CONTENT_IDS.indexOf(id) >= 0) return hasContentBundle(r) && (r.modules === '*' || r.modules.indexOf('content') >= 0 || r.modules.indexOf(id) >= 0);
  if (id === 'collect') return hasCollectBundle(r);
  if (COLLECT_IDS.indexOf(id) >= 0) return hasCollectBundle(r) && (r.modules === '*' || r.modules.indexOf('collect') >= 0 || r.modules.indexOf(id) >= 0);
  if (id === 'intAnalysis') return hasIntAnalysisBundle(r);
  if (INT_ANALYSIS_IDS.indexOf(id) >= 0) return hasIntAnalysisBundle(r) && (r.modules === '*' || r.modules.indexOf('intAnalysis') >= 0 || r.modules.indexOf(id) >= 0);
  if (id === 'compAnalysis') return hasCompAnalysisBundle(r);
  if (COMP_ANALYSIS_IDS.indexOf(id) >= 0) return hasCompAnalysisBundle(r) && (r.modules === '*' || r.modules.indexOf('compAnalysis') >= 0 || r.modules.indexOf('comp') >= 0 || r.modules.indexOf(id) >= 0);
  if (id === 'corpAcct') return hasCorpAcctBundle(r);
  if (CORP_ACCT_IDS.indexOf(id) >= 0) return hasCorpAcctBundle(r) && (r.modules === '*' || r.modules.indexOf('corpAcct') >= 0 || r.modules.indexOf('acct') >= 0 || r.modules.indexOf(id) >= 0);
  if (id === 'corpRes') return hasCorpResBundle(r);
  if (CORP_RES_IDS.indexOf(id) >= 0) return hasCorpResBundle(r) && (r.modules === '*' || r.modules.indexOf('corpRes') >= 0 || r.modules.indexOf('master') >= 0 || r.modules.indexOf('cert') >= 0 || r.modules.indexOf(id) >= 0);
  if (id === 'corpDev') return hasCorpDevBundle(r);
  if (CORP_DEV_IDS.indexOf(id) >= 0) return hasCorpDevBundle(r) && (r.modules === '*' || r.modules.indexOf('corpDev') >= 0 || r.modules.indexOf('asset') >= 0 || r.modules.indexOf(id) >= 0);
  if (id === 'master' || id === 'cert') return hasCorpResBundle(r);
  if (id === 'acct') return hasCorpAcctBundle(r);
  if (id === 'asset') return hasCorpDevBundle(r);
  if (id === 'dailyCenter') return hasDailyBundle(r);
  if (DAILY_IDS.indexOf(id) >= 0) return hasDailyBundle(r);
  if (id === 'reportOps') return hasReportDataBundle(r);
  if (REPORT_DATA_IDS.indexOf(id) >= 0) return hasReportDataBundle(r);
  if (id === 'trainMgmt' || id === 'trainCenter') return hasTrainBundle(r);
  if (TRAIN_IDS.indexOf(id) >= 0) return hasTrainBundle(r);
  if (id === 'authMgmt') return hasAuthBundle(r);
  if (AUTH_IDS.indexOf(id) >= 0) return hasAuthBundle(r) && (r.modules === '*' || r.modules.indexOf('auth') >= 0 || r.modules.indexOf('authMgmt') >= 0 || r.modules.indexOf(id) >= 0);
  if (id === 'sysMgmt') return hasSysBundle(r);
  if (SYS_IDS.indexOf(id) >= 0) return hasSysBundle(r) && (r.modules === '*' || r.modules.indexOf('sys') >= 0 || r.modules.indexOf('sysMgmt') >= 0 || r.modules.indexOf(id) >= 0);
  if (id === 'biReportMgmt') return hasBiReportBundle(r);
  if (BI_REPORT_NAV_IDS.indexOf(id) >= 0) return hasBiReportBundle(r);
  if (id === 'bi0Report' || id === 'bi0Screen' || id === 'biShare') return hasBiReportBundle(r) || hasBiMetricBundle(r);
  if (id === 'biMetricMgmt') return hasBiMetricBundle(r);
  if (BI_METRIC_IDS.indexOf(id) >= 0) return hasBiMetricBundle(r);
  if (id === 'biAnalysisMgmt') return hasBiAnalysisBundle(r);
  if (BI_ANALYSIS_NAV_IDS.indexOf(id) >= 0) return hasBiAnalysisBundle(r);
  if (id === 'bi0Query') return hasBiAnalysisBundle(r) || hasBiMetricBundle(r);
  if (EFF_TAB_IDS.indexOf(id) >= 0) return hasBiAnalysisBundle(r);
  if (id === 'alertMgmt') return hasAlertBundle(r);
  if (ALERT_IDS.indexOf(id) >= 0) return hasAlertBundle(r);
  return r.modules === '*' || r.modules.indexOf(id) >= 0;
}
function go(id) {
  const raw = id;
  if (raw === 'effRelation') state.tab.eff = 'relation';
  else if (raw === 'effInventory') state.tab.eff = 'inventory';
  else if (raw === 'effBoard' || raw === 'eff' || raw === 'effMgmt') state.tab.eff = 'board';
  if (raw === 'alertHistory') state.tab.alertLive = 'history';
  else if (raw === 'alertDedup') state.tab.alertLive = 'dedup';
  else if (raw === 'alert' || raw === 'alertMgmt' || raw === 'alertLive') state.tab.alertLive = state.tab.alertLive || 'live';
  if (raw === 'biShare') state.tab.biList = 'share';
  id = alertNorm(effNorm(biNorm(bi0Norm(trainNorm(legacyReportNorm(sysNorm(authNorm(reportOpsNorm(dailyCenterNorm(corpDevNorm(corpResNorm(corpAcctNorm(compAnalysisNorm(intAnalysisNorm(collectNorm(contentNorm(airNorm(id))))))))))))))))));
  if (!canAccess(id)) { toast('当前角色（' + ROLES[state.role].name + '）无权限访问该模块', 'warn'); return; }
  state.page = id;
  renderAll();
}
function setTab(pid, t) { state.tab[pid] = t; renderPage(); }
function tgGroup(g) { state.gc[g] = !state.gc[g]; renderSidebar(); }

/* ===================== 渲染骨架 ===================== */
function renderSidebar() {
  const prevNav = document.querySelector('#sidebar .nav');
  const navScroll = prevNav ? prevNav.scrollTop : 0;
  let h = '<div class="logo"><b>IMS 一体化管理系统</b><small>神鱼体育 · 完整系统</small></div><nav class="nav">';
  GROUPS.forEach(function (g) {
    const gid = g[0], closed = state.gc[gid];
    /* 角色无权访问组内全部模块时，整组（含标题）隐藏 */
    const visible = g[1].filter(function (mid) {
      if (isNavSub(mid)) return navSubVisible(mid).length > 0;
      return canAccess(mid);
    });
    if (!visible.length) return;
    h += '<div class="nav-g' + (closed ? ' closed' : '') + '"><div class="nav-g-h" onclick="tgGroup(\'' + gid + '\')">' + gid +
      '<span class="caret">' + ic('chev', 12) + '</span></div>';
    visible.forEach(function (mid) {
      if (isNavSub(mid)) {
        const subIds = navSubVisible(mid);
        const subKey = 'sub:' + mid.id;
        const subActive = subIds.indexOf(state.page) >= 0;
        const subClosed = state.gc[subKey] && !subActive;
        const pm = MODS[mid.id] || { icon: mid.id === 'collect' ? 'search' : mid.id === 'intAnalysis' ? 'chart' : mid.id === 'compAnalysis' ? 'target' : mid.id === 'corpAcct' ? 'user' : mid.id === 'corpRes' ? 'id' : mid.id === 'corpDev' ? 'box' : mid.id === 'authMgmt' ? 'shield' : mid.id === 'sysMgmt' ? 'db' : mid.id === 'trainMgmt' || mid.id === 'trainMgmt' || mid.id === 'trainMgmt' || mid.id === 'trainCenter' ? 'book' : mid.id === 'dailyCenter' ? 'doc' : mid.id === 'reportOps' ? 'doc' : 'film', no: mid.id === 'collect' ? '16' : mid.id === 'intAnalysis' ? '18b' : mid.id === 'compAnalysis' ? '18a' : mid.id === 'corpAcct' ? '08' : mid.id === 'corpRes' ? '06' : mid.id === 'corpDev' ? '07' : mid.id === 'authMgmt' || mid.id === 'sysMgmt' ? '01' : mid.id === 'trainMgmt' || mid.id === 'trainMgmt' || mid.id === 'trainMgmt' || mid.id === 'trainCenter' ? '02' : mid.id === 'dailyCenter' ? '03' : mid.id === 'reportOps' ? '09' : '15', code: mid.id === 'collect' ? 'COLLECT' : mid.id === 'intAnalysis' ? 'INT' : mid.id === 'compAnalysis' ? 'COMPA' : mid.id === 'corpAcct' ? 'CORP-A' : mid.id === 'corpRes' ? 'CORP-R' : mid.id === 'corpDev' ? 'CORP-D' : mid.id === 'authMgmt' ? 'AUTH' : mid.id === 'sysMgmt' ? 'SYS' : mid.id === 'trainMgmt' || mid.id === 'trainCenter' ? 'TRAIN' : mid.id === 'dailyCenter' ? 'MEET' : mid.id === 'reportOps' ? 'REPORT' : 'CONTENT' };
        h += '<div class="nav-sub-g' + (subClosed ? ' closed' : '') + '">';
        h += '<div class="nav-item nav-parent' + (subActive ? ' active' : '') + '" onclick="tgGroup(\'' + subKey + '\')">' + ic(pm.icon, 16) +
          '<span>' + mid.label + '</span><span class="nc">' + pm.no + ' ' + pm.code + '</span><span class="caret">' + ic('chev', 12) + '</span></div>';
        subIds.forEach(function (cid) {
          const m = MODS[cid];
          h += '<div class="nav-item sub' + (state.page === cid ? ' active' : '') + '" onclick="go(\'' + cid + '\')">' + ic(m.icon, 14) +
            '<span>' + m.name + '</span></div>';
        });
        h += '</div>';
        return;
      }
      const m = MODS[mid];
      const wbSub = mid === 'workbench' && (state.page === 'workbenchTodos' || state.page === 'workbenchMsgs');
      const sub = !!m.parent;
      h += '<div class="nav-item' + (sub ? ' sub' : '') + (state.page === mid || wbSub ? ' active' : '') + '" onclick="go(\'' + mid + '\')">' + ic(m.icon, sub ? 14 : 16) +
        '<span>' + m.name + '</span><span class="nc">' + (m.code && !sub ? m.no + ' ' + m.code : '') + '</span></div>';
    });
    h += '</div>';
  });
  h += '</nav>';
  const r = ROLES[state.role];
  h += '<div class="uCard">' + av(r.user, '#0071e3') + '<div><div class="un">' + r.user + '</div><div class="ur">' + state.role + ' · ' + r.name + '</div></div></div>';
  $('#sidebar').innerHTML = h;
  const nextNav = document.querySelector('#sidebar .nav');
  if (nextNav) nextNav.scrollTop = navScroll;
}
function renderTopbar() {
  const m = MODS[state.page], r = ROLES[state.role], unread = MSGS.filter(function (x) { return !x.read; }).length;
  const crumb = m && m.parent ? '<b>' + m.parent + '</b> / ' + m.page : '<b>' + (m ? m.name : '') + '</b> / ' + (m ? m.page : '');
  $('#topbar').innerHTML =
    '<div class="crumb">' + crumb + '</div>' +
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
  { type: '系统通知', title: '系统将于今晚 02:00 进行例行维护', content: '维护期间平台暂停访问约 15 分钟，请提前保存工作内容。', time: '10 分钟前', read: false, refGo: '' },
  { type: '审批结果', title: '资产领用申请已通过', content: '领用单 LC20260912-03（罗技 C920 摄像头 ×1）已由林岚审批通过。', time: '32 分钟前', read: false, refGo: 'asset' },
  { type: '预警推送', title: '高风险预警：账号风险分超阈值', content: '账号 ACCT-2026-0087 风险分 86，超过高风险阈值 85，请及时处理。', time: '1 小时前', read: false, refGo: 'alert' },
  { type: '审批结果', title: '开播登记待风控复核', content: '场次 IMS202609120DY0142 风险分 82，已进入人工复核队列。', time: '2 小时前', read: true, refGo: 'live' },
  { type: '系统通知', title: '钉钉组织架构同步完成', content: '本次同步成功 128 人，待处理事件 3 条。', time: '昨天 18:20', read: true, refGo: 'authOrg' },
  { type: '预警推送', title: '证件到期提醒', content: '苏杳（身份证）剩余有效期 26 天，请及时跟进换证。', time: '昨天 09:00', read: true, refGo: 'cert' },
  { type: '审批结果', title: '费用报销单已通过出纳付款', content: 'BX20260911-02 · ¥3,260.00 已付款，可在财务模块查看回单。', time: '昨天 14:10', read: false, refGo: 'fin' },
  { type: '系统通知', title: '培训学习任务已下达', content: '《直播合规与风控》已指派给你，截止 2026-09-20，请在工作台待办中完成。', time: '昨天 11:00', read: false, refGo: 'train' },
  { type: '预警推送', title: '采集任务连续失败', content: '抖音内部账号 Cookie 失效，已影响 3 条采集任务，请进入采集模块更新凭证。', time: '2 天前', read: true, refGo: 'collect' },
  { type: '审批结果', title: '内容二审已通过', content: '短视频《秋季跑鞋测评》已发布至排期队列。', time: '2 天前', read: true, refGo: 'contentReview' },
  { type: '系统通知', title: 'AIR 技能审核通过', content: '「竞彩内容质检」已通过安全审核并发布；可在技能库查看授权。', time: '3 天前', read: false, refGo: 'airSkill' },
  { type: '预警推送', title: '会议室预订冲突已解除', content: '3F-大会议室 16:00 冲突已由行政协调至 17:00。', time: '3 天前', read: true, refGo: 'meet' }
];
const MSG_TYPE_COLOR = { '系统通知': 'gray', '审批结果': 'blue', '预警推送': 'red' };
function msgRowsHtml(items, startIdx) {
  startIdx = startIdx || 0;
  let h = '';
  items.forEach(function (m, j) {
    const i = startIdx + j;
    h += '<div class="mg-i' + (m.read ? ' read' : '') + '" onclick="openMsgDetail(' + i + ')">' +
      '<span class="mg-ud"></span><div style="flex:1;min-width:0"><div class="rowline" style="justify-content:space-between">' +
      '<span class="mt">' + m.title + '</span>' + tag(m.type, MSG_TYPE_COLOR[m.type] || 'gray') + '</div>' +
      '<div class="mc">' + m.content + '</div><div class="md">' + m.time + '</div></div></div>';
  });
  return h;
}
function refreshMsgSurfaces() {
  renderTopbar();
  if (state.page === 'workbench' || state.page === 'workbenchMsgs') renderPage();
  if ($('#msgdrawer').classList.contains('on')) renderMsgList();
}
function openMsg() { renderMsgList(); $('#msgdrawer').classList.add('on'); $('#mask').classList.add('on'); }
function closeMsg() { $('#msgdrawer').classList.remove('on'); if (!$('#drawer').classList.contains('on')) $('#mask').classList.remove('on'); }
function renderMsgList() {
  $('#mglist').innerHTML = msgRowsHtml(MSGS) || emptyState('暂无消息', '新消息将实时推送至此');
}
function openMsgDetail(i) {
  const m = MSGS[i];
  if (!m) return;
  m.read = true;
  refreshMsgSurfaces();
  const body = '<div class="rowline" style="margin-bottom:14px">' + tag(m.type, MSG_TYPE_COLOR[m.type] || 'gray') +
    '<span class="md">' + m.time + '</span></div>' +
    '<div style="font-size:14px;line-height:1.75;color:var(--text)">' + m.content + '</div>' +
    (m.refGo ? '<div class="hint" style="margin-top:14px">来源模块：' + (MODS[m.refGo] ? MODS[m.refGo].name : m.refGo) + '</div>' : '');
  const foot = '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (m.refGo ? '<button class="btn btn-pri" onclick="closeDrawer();msgGoRef(' + i + ')">查看来源</button>' : '');
  openDrawer('消息详情', body, foot, '520px');
}
function readMsg(i) { openMsgDetail(i); }
function msgGoRef(i) {
  const m = MSGS[i];
  if (m && m.refGo && canAccess(m.refGo)) { go(m.refGo); toast('已跳转至「' + MODS[m.refGo].name + '」', 'success'); }
  else toast('来源单据已打开（原型示意）', 'success');
}
function markAllRead() { MSGS.forEach(function (m) { m.read = true; }); refreshMsgSurfaces(); toast('已全部标记为已读', 'success'); }

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
function qsv(opts, w, val, onchg) {
  var h = '<select style="width:' + (w || 108) + 'px"';
  if (onchg) h += ' onchange="' + onchg + '"';
  h += '>';
  opts.forEach(function (o) {
    var v = o && o.v != null ? o.v : o;
    var l = o && o.l != null ? o.l : o;
    h += '<option value="' + String(v).replace(/"/g, '&quot;') + '"' + (String(v) === String(val) ? ' selected' : '') + '>' + l + '</option>';
  });
  return h + '</select>';
}
function qsvQ(opts, w, val, onchg) {
  return qsv(opts, w, val, onchg).replace('<select ', '<select class="qt-qctl" ');
}
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
    (opts.withInput ? '<div style="margin:10px 0 2px"><input id="cf_input" placeholder="' + (opts.inputPh || '请输入…') + '" style="width:100%;border:1px solid var(--line2);border-radius:var(--r-s);padding:8px 10px;font-size:13px;font-family:var(--font);outline:none"></div>' : '') +
    '<div class="cf-f"><button class="btn btn-sec" onclick="closeConfirm()">取消</button>' +
    '<button class="btn ' + (opts.danger ? 'btn-red' : 'btn-pri') + '" onclick="doConfirm()">' + (okText || '确认') + '</button></div></div>';
  document.body.appendChild(w);
  if (opts.withInput && opts.onInput) opts.onInput($('#cf_input'));
}
function closeConfirm() { const w = $('#cfwrap'); if (w) w.remove(); CF_CB = null; }
function doConfirm() { const cb = CF_CB; closeConfirm(); if (cb) cb(); }

/* ===================== 表单抽屉子页面 ===================== */
/* fields: [{k:字段名,label,type:(text|date|num|select|dt|file|textarea|pills),req,opts,val,ph,pre,unit,disabled}] */
function frow(fields) {
  return fields.map(function (f) {
    const pid = 'F_' + f.k;
    let inner;
    if (f.type === 'select') inner = '<select id="' + pid + '"' + (f.chg ? ' onchange="' + f.chg + '"' : '') + (f.disabled ? ' disabled' : '') + '>' + f.opts.map(function (o) { return '<option' + (o === f.val ? ' selected' : '') + '>' + o + '</option>'; }).join('') + '</select>';
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
