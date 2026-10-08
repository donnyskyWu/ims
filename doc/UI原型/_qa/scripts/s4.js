
'use strict';
/* ===================== 04 COMP 竞品库 ===================== */
const COMPS = [
  { name: 'Keep 官方', plat: '抖音', fans: '486 万', works: 62, rate: '4.8%', trend: [12, 18, 15, 22, 19, 25, 21, 28, 24, 30], hot: '《21 天燃脂跟练》播放 1240 万', audit: '已入库' },
  { name: '刘畊宏', plat: '抖音', fans: '6123 万', works: 28, rate: '6.2%', trend: [30, 26, 22, 25, 19, 16, 14, 15, 12, 11], hot: '《本草纲目毽子操》二创季', audit: '已入库' },
  { name: '咕咚运动', plat: '视频号', fans: '132 万', works: 45, rate: '3.1%', trend: [8, 9, 11, 10, 12, 13, 12, 14, 15, 16], hot: '马拉松备赛系列', audit: '已入库' },
  { name: '悦跑圈', plat: '小红书', fans: '86 万', works: 55, rate: '5.4%', trend: [10, 12, 14, 13, 16, 18, 17, 19, 21, 23], hot: '跑鞋真香榜（月更）', audit: '已入库' },
  { name: '超级猩猩', plat: 'B 站', fans: '98 万', works: 38, rate: '2.9%', trend: [6, 7, 7, 8, 9, 8, 10, 9, 11, 10], hot: '团课教练 vlog', audit: '已入库' },
  { name: '帕梅拉 Pam', plat: 'B 站', fans: '1120 万', works: 41, rate: '5.8%', trend: [20, 22, 21, 23, 22, 24, 25, 23, 24, 26], hot: '10 分钟腹部训练', audit: '已入库' },
  { name: '跑者小站', plat: '快手', fans: '54 万', works: 51, rate: '3.6%', trend: [7, 8, 9, 9, 10, 11, 10, 12, 13, 12], hot: '晨跑打卡挑战', audit: '已入库' },
  { name: '健身教练艾伦', plat: '抖音', fans: '320 万', works: 58, rate: '4.2%', trend: [14, 16, 15, 17, 18, 17, 19, 20, 19, 21], hot: '哑铃全身循环', audit: '已入库' }
];
PAGES.comp = function () {
  const pend = COMPS.filter(function (c) { return c.audit === '待审核'; }).length;
  const rejected = COMPS.filter(function (c) { return c.audit === '已驳回'; }).length;
  let h = pgHead('comp', '<button class="btn btn-sec btn-sm" onclick="go(\'compWork\')">竞品作品监测</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'compAccount\')">竞品账号监测</button>' +
    '<button class="btn btn-sec" onclick="exportX(this,\'竞品对比报告\',COMPS.length)">导出对比</button>' +
    '<button class="btn btn-pri" onclick="compAdd()">' + ic('plus', 15) + '新增竞品</button>');
  h += '<div class="hint" style="margin-bottom:8px">V3 COMP-003 · 路由 <code>/ims/comp-analysis/library</code> · API <code>/admin-api/comp/asset/*</code>（与 M7 监测 BFF 分离 · 走查 #9）。</div>';
  if (pend > 0 || rejected > 0) h += '<div class="card" style="padding:10px 14px;margin-bottom:12px;display:flex;gap:10px;align-items:center;background:rgba(255,149,0,.06);border-color:rgba(255,149,0,.25)">' + ic('warn', 15) +
    '<span style="font-size:12.5px">待审核 <b style="color:var(--orange)">' + pend + '</b> 家 · 已驳回 ' + rejected + ' 家 · 依据 BR-202 竞品入库审核：通过后入库存并订阅监控，驳回后录入人可修改重新提交</span></div>';
  h += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">';
  COMPS.forEach(function (c, i) {
    const isPend = c.audit === '待审核';
    const isRej = c.audit === '已驳回';
    const isNotIn = isPend || isRej;
    h += '<div class="card hov" onclick="compDetail(' + i + ')"><div class="rowline" style="margin-bottom:10px">' +
      '<span class="av" style="background:linear-gradient(135deg,#0071e3,#5ac8fa)' + (isNotIn ? ';filter:grayscale(.4);opacity:.7' : '') + '">' + c.name.slice(0, 1) + '</span>' +
      '<div style="min-width:0"><b style="font-size:14px;display:block;line-height:1.3">' + c.name + '</b><span style="font-size:11.5px;color:var(--text2)">' + c.plat + ' · 竞品</span></div>' +
      (isPend ? '<span class="chip pp" style="margin-left:auto;background:rgba(255,149,0,.12);color:var(--orange)">待审核</span>' : '') +
      (isRej ? '<span class="chip pp" style="margin-left:auto;background:rgba(255,59,48,.1);color:var(--red)">已驳回</span>' : '') + '</div>' +
      (isRej && c.rejBy ? '<div style="font-size:11.5px;color:var(--red);margin:-4px 0 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + ic('warn', 11) + ' ' + c.rejBy + '</div>' : '') +
      '<div class="kv" style="grid-template-columns:1fr 1fr 1fr;gap:8px;margin:0">' +
      '<div><div class="k">粉丝数</div><div class="v" style="font-size:14px">' + c.fans + '</div></div>' +
      '<div><div class="k">近30天作品</div><div class="v" style="font-size:14px">' + (isNotIn ? '—' : c.works) + '</div></div>' +
      '<div><div class="k">互动率</div><div class="v" style="font-size:14px;color:' + (isNotIn ? 'var(--text2)' : 'var(--blue)') + '">' + (isNotIn ? '—' : c.rate) + '</div></div></div>' +
      (isPend
        ? '<div class="rowline" style="margin-top:12px;gap:8px"><button class="btn btn-pri" style="flex:1" onclick="event.stopPropagation();compAudit(' + i + ',1)">审核通过</button><button class="btn btn-sec" style="flex:1" onclick="event.stopPropagation();compAudit(' + i + ',0)">驳回</button></div>'
        : isRej
          ? '<div class="rowline" style="margin-top:12px;gap:8px"><button class="btn btn-pri" style="flex:1" onclick="event.stopPropagation();compResubmit(' + i + ')">修改重新提交</button></div>'
          : '<div class="rowline" style="margin-top:12px;justify-content:space-between"><span style="font-size:11.5px;color:var(--text2)">代表作品已收录</span>' + ic('right', 13) + '</span></div>') + '</div>';
  });
  h += '</div>';
  return h;
};
function compDetail(i) {
  const c = COMPS[i];
  const max = Math.max.apply(null, c.trend);
  let bars = '';
  c.trend.forEach(function (v) { bars += '<div class="b" style="height:' + Math.max(8, Math.round(v / max * 100)) + '%;background:var(--purple)"></div>'; });
  const isPend = c.audit === '待审核';
  const isRej = c.audit === '已驳回';
  const body = '<div class="rowline" style="margin-bottom:4px"><span class="av" style="width:44px;height:44px;font-size:18px;background:linear-gradient(135deg,#0071e3,#5ac8fa)">' + c.name.slice(0, 1) + '</span>' +
    '<div><b style="font-size:17px">' + c.name + '</b><div style="font-size:12px;color:var(--text2)">' + c.plat + ' · 竞品账号</div></div>' +
    (isPend ? '<span class="chip pp" style="margin-left:auto;background:rgba(255,149,0,.12);color:var(--orange)">待审核</span>' : isRej ? '<span class="chip pp" style="margin-left:auto;background:rgba(255,59,48,.1);color:var(--red)">已驳回</span>' : '<span class="chip pp" style="margin-left:auto">已订阅监控</span>') + '</div>' +
    (isPend || isRej ? '<div class="dsec">审核信息（BR-202）</div><div class="card" style="padding:10px 14px;box-shadow:none;border:1px solid ' + (isRej ? 'rgba(255,59,48,.25);background:rgba(255,59,48,.04)' : 'rgba(255,149,0,.25);background:rgba(255,149,0,.05)') + '">' +
      '<div style="font-size:12.5px;line-height:1.7">当前状态：<b style="color:' + (isRej ? 'var(--red)' : 'var(--orange)') + '">' + c.audit + '</b> · 尚未入库存<br>' +
      (isRej && c.rejBy ? '<span style="color:var(--red)">驳回原因：' + c.rejBy + '</span><br>' : '') +
      '<span class="csub">' + (isRej ? '录入人修改信息后可重新提交审核；通过后方正式入库并订阅监控。' : '审核通过 → 正式入竞品库 + 自动订阅数据监控（次日生效）；驳回 → 退回录入人修改后重新提交。') + '</span></div></div>' +
      '<div class="dsec">基础信息（录入值）</div><div class="kv">' +
      '<div><div class="k">粉丝数</div><div class="v">' + c.fans + '</div></div><div><div class="k">近 30 天作品数</div><div class="v">—（待采集）</div></div>' +
      '<div><div class="k">互动率</div><div class="v">—（待采集）</div></div><div><div class="k">更新频率</div><div class="v">—（待采集）</div></div></div>'
      : '<div class="dsec">基础信息</div><div class="kv">' +
        '<div><div class="k">粉丝数</div><div class="v">' + c.fans + '</div></div><div><div class="k">近 30 天作品数</div><div class="v">' + c.works + '</div></div>' +
        '<div><div class="k">互动率</div><div class="v" style="color:var(--blue)">' + c.rate + '</div></div><div><div class="k">更新频率</div><div class="v">约 ' + Math.round(c.works / 30 * 10) / 10 + ' 条/天</div></div></div>' +
        '<div class="dsec">近 30 天互动量趋势</div><div class="card" style="box-shadow:none;border:1px solid var(--line)"><div class="bars">' + bars + '</div><div class="rowline" style="justify-content:space-between;margin-top:6px"><span style="font-size:11px;color:var(--text2)">30 天前</span><span style="font-size:11px;color:var(--text2)">今天</span></div></div>' +
        '<div class="dsec">代表作品（Top 3）</div><div class="tbl-wrap"><table><thead><tr><th>作品</th><th>播放</th><th>发布</th></tr></thead><tbody>' +
        '<tr><td>' + c.hot + '</td><td class="num">1240 万</td><td class="num">09-02</td></tr>' +
        '<tr><td>品类知识合集（第 4 期）</td><td class="num">486 万</td><td class="num">09-08</td></tr>' +
        '<tr><td>新品开箱：秋季装备</td><td class="num">312 万</td><td class="num">09-11</td></tr></tbody></table></div>');
  openDrawer('竞品详情 · ' + c.name, body,
    isPend
      ? '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-sec" style="color:var(--red)" onclick="compAudit(' + i + ',0)">驳回</button><button class="btn btn-pri" onclick="compAudit(' + i + ',1)">审核通过</button>'
      : isRej
        ? '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="compResubmit(' + i + ')">修改重新提交</button>'
        : '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="compCompare(' + i + ')">加入对比</button>');
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
/* COMP：新增竞品表单（提交后进入 BR-202 审核流，不直接入库存） */
function compAdd() {
  const body = frow([
    { k: 'name', label: '竞品名称', type: 'text', req: true, ph: '如：Keep 官方' },
    { k: 'plat', label: '平台', type: 'select', opts: ['抖音', '视频号', '斗鱼', 'B 站', '小红书', '快手'] },
    { k: 'link', label: '主页链接', type: 'text', ph: 'https://…（选填）' },
    { k: 'fans', label: '粉丝数', type: 'text', ph: '如：486 万' },
    { k: 'note', label: '备注', type: 'textarea', ph: '监控重点、对标维度（选填）', wide: true }
  ]) + '<div class="hint" style="display:flex;gap:8px;align-items:center">' + ic('warn', 13) + ' 依据 BR-202 竞品入库审核：提交后状态为「待审核」，审核通过方正式入库并订阅数据监控。</div>';
  openDrawer('新增竞品', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="compAddSubmit()">提交审核</button>', '480px');
}
function compAddSubmit() {
  if (!formValidate(['name'])) return;
  const no = 'CP202609-' + String(Math.floor(Math.random() * 90) + 10);
  COMPS.unshift({ name: $('#F_name').value.trim(), plat: $('#F_plat').value, fans: $('#F_fans').value.trim() || '—', works: 0, rate: '—', trend: [5, 6, 6, 7, 8, 8, 9, 10, 10, 11], hot: '待采集（审核通过后订阅监控）', audit: '待审核' });
  if (state.page === 'comp') renderPage();
  closeDrawer();
  formOk(no, '竞品已提交审核（BR-202）：审核通过后入库存并自动订阅监控', '');
  toast('已提交审核：' + COMPS[0].name + '（待审核）', 'warn');
}
/* COMP：审核入库（BR-202 · pass=1 通过 / pass=0 驳回） */
function compAudit(i, pass) {
  const c = COMPS[i];
  if (pass) {
    confirmDlg('审核通过并入库？', '竞品「' + c.name + '」（' + c.plat + ' · 粉丝 ' + c.fans + '）将通过 BR-202 审核：正式入竞品库，数据监控自动订阅（次日生效）。', '审核通过', function () {
      c.audit = '已入库';
      c.hot = '待采集（监控已订阅）';
      closeDrawer();
      if (state.page === 'comp') renderPage();
      toast('审核通过：「' + c.name + '」已入库，数据监控订阅已生效（次日开始采集）', 'success');
    }, { warn: '通过后该竞品将进入对比/分析取数范围' });
  } else {
    let rej = null;
    confirmDlg('驳回该竞品申请？', '竞品「' + c.name + '」（' + c.plat + ' · 粉丝 ' + c.fans + '）将被驳回退回，录入人可修改后重新提交。', '确认驳回', function () {
      c.audit = '已驳回';
      c.rejBy = (rej && rej.value.trim()) ? rej.value.trim() : '信息不全，请补充主页链接与监控重点';
      closeDrawer();
      if (state.page === 'comp') renderPage();
      toast('已驳回：「' + c.name + '」退回录入人修改，驳回原因：' + c.rejBy, 'warn');
    }, { danger: true, withInput: true, inputPh: '驳回原因（如：账号非竞品 / 信息不全 / 重复录入）', onInput: function (el) { rej = el; } });
  }
}
/* COMP：驳回后修改重新提交（BR-202） */
function compResubmit(i) {
  const c = COMPS[i];
  confirmDlg('修改后重新提交审核？', '竞品「' + c.name + '」将按驳回原因修改信息并重新进入 BR-202 审核流。', '重新提交', function () {
    c.audit = '待审核';
    delete c.rejBy;
    if (state.page === 'comp') renderPage();
    toast('已重新提交审核：' + c.name + '（待审核）', 'success');
  });
}

/* ===================== 12 DC 穿透查询（走查 #13 · DC-001 单列 · POST /dc/trace/query mock） ===================== */
const DC_ENTRY_TYPES = [
  { k: 'PERSON', l: '实名人' }, { k: 'ACCOUNT', l: '账号' }, { k: 'ASSET', l: '资产' },
  { k: 'SESSION', l: '场次' }, { k: 'RESPONSIBLE', l: '责任人' }, { k: 'IP_GROUP', l: 'IP 组' }
];
const DC_SOURCES = [
  { entryType: 'PERSON', entryId: 'pers_sf0068', entryLabel: '苏杳', hint: '实名人 · 华东 · 3 账号' },
  { entryType: 'ACCOUNT', entryId: 'ACCT-2026-0001', entryLabel: '神鱼体育', hint: '抖音 · 在用' },
  { entryType: 'ASSET', entryId: 'AS20260901001', entryLabel: '罗技 C920 Pro', hint: '直播设备 · 绑定 2 账号' },
  { entryType: 'SESSION', entryId: 'IMS202609100DY0131', entryLabel: 'IMS202609100DY0131', hint: '2026-09-10 抖音场次' },
  { entryType: 'RESPONSIBLE', entryId: 'u_zhao', entryLabel: '赵敏', hint: '运营负责人 · 8 账号' },
  { entryType: 'IP_GROUP', entryId: 'g_sy', entryLabel: '神鱼体育 IP 组', hint: '大组 · 42 场/月' }
];
const DC_NODE_COL = { PERSON: '#af52de', ACCOUNT: '#0071e3', ASSET: '#34c759', SESSION: '#ff9500', COST: '#ff3b30', PROFIT: '#1e8e3e' };
const DC_DETAIL_ROWS = [
  { sessionCode: 'IMS202609100DY0131', sessionTitle: '神鱼体育 · 晚场', platform: '抖音', accountNo: 'ACCT-2026-0001', gmv: 412800, netProfit: 163620, nodeId: 'sess_131' },
  { sessionCode: 'IMS202609110DY0138', sessionTitle: '跑步研究所 · 午场', platform: '视频号', accountNo: 'ACCT-2026-0002', gmv: 186400, netProfit: 72994, nodeId: 'sess_138' },
  { sessionCode: 'IMS202609090DY0127', sessionTitle: '电竞直播间 · 夜场', platform: '斗鱼', accountNo: 'ACCT-2026-0003', gmv: 96700, netProfit: 31900, nodeId: 'sess_127' },
  { sessionCode: 'IMS202609070DY0118', sessionTitle: '运动精选 · 早场', platform: '快手', accountNo: 'ACCT-2026-0034', gmv: 61200, netProfit: 12898, nodeId: 'sess_118' }
];
function dcTraceEnsure() {
  if (!state.dcTrace) {
    state.dcTrace = { view: 'split', filterType: '', sourceIdx: null, path: [], focusNodeId: 'n_acct1', queryCostMs: 286, dataAsOf: '2026-09-29 15:00' };
  }
  return state.dcTrace;
}
function dcTraceGraphPack(focusId) {
  const nodes = [
    { nodeId: 'n_person', nodeType: 'PERSON', nodeLabel: '苏杳', sub: '实名人', metrics: '3 账号' },
    { nodeId: 'n_acct1', nodeType: 'ACCOUNT', nodeLabel: '神鱼体育', sub: 'ACCT-2026-0001', metrics: '42 场' },
    { nodeId: 'n_asset1', nodeType: 'ASSET', nodeLabel: 'C920 摄像头', sub: 'AS20260901001', metrics: '2 绑定' },
    { nodeId: 'n_asset2', nodeType: 'ASSET', nodeLabel: '号卡', sub: 'AS20260918011', metrics: '1 绑定' },
    { nodeId: 'n_sess', nodeType: 'SESSION', nodeLabel: 'IMS…0131', sub: '代表场次', metrics: 'GMV ¥412,800' },
    { nodeId: 'n_cost', nodeType: 'COST', nodeLabel: '场次成本', sub: 'FIN-001', metrics: '¥249,180' },
    { nodeId: 'n_profit', nodeType: 'PROFIT', nodeLabel: '净利润', sub: 'FIN-002', metrics: '¥163,620' }
  ];
  const edges = [
    ['n_person', 'n_acct1'], ['n_acct1', 'n_asset1'], ['n_acct1', 'n_asset2'], ['n_acct1', 'n_sess'],
    ['n_sess', 'n_cost'], ['n_cost', 'n_profit']
  ];
  const rels = {
    n_person: [{ id: 'r_pa', label: '持有账号', targetId: 'n_acct1', crumb: '关联：持有账号 → 神鱼体育' }],
    n_acct1: [
      { id: 'r_ab', label: '绑定资产', targetId: 'n_asset1', crumb: '关联：绑定资产 → C920' },
      { id: 'r_as', label: '参与场次', targetId: 'n_sess', crumb: '关联：参与场次 → IMS…0131' }
    ],
    n_asset1: [{ id: 'r_sa', label: '归属账号', targetId: 'n_acct1', crumb: '关联：归属账号 → 神鱼体育' }],
    n_sess: [
      { id: 'r_sc', label: '归集成本', targetId: 'n_cost', crumb: '关联：归集成本 → 场次成本' },
      { id: 'r_sd', label: '场次明细', targetId: 'n_sess', crumb: '明细：IMS202609100DY0131', detail: true }
    ],
    n_cost: [{ id: 'r_cp', label: '核算利润', targetId: 'n_profit', crumb: '关联：核算利润 → 净利润' }]
  };
  return { nodes: nodes, edges: edges, rels: rels, focusId: focusId || 'n_acct1' };
}
PAGES.dc = function () {
  const tr = dcTraceEnsure();
  let h = pgHead('dc',
    '<button class="btn btn-sec' + (tr.view === 'split' ? ' btn-pri' : '') + '" onclick="dcTraceSetView(\'split\')">分栏</button>' +
    '<button class="btn btn-sec' + (tr.view === 'graph' ? ' btn-pri' : '') + '" onclick="dcTraceSetView(\'graph\')">关系图</button>' +
    '<button class="btn btn-sec' + (tr.view === 'list' ? ' btn-pri' : '') + '" onclick="dcTraceSetView(\'list\')">明细表</button>' +
    '<button class="btn btn-pri" onclick="dcTraceExport()">' + ic('doc', 15) + '导出链路</button>');
  h += dcTraceBody(tr);
  return h;
};
function dcTraceBody(tr) {
  const costCls = tr.queryCostMs > 3000 ? ' style="color:var(--orange);font-weight:600"' : '';
  let h = '<div class="hint" style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:10px">' +
    ic('db', 13) + ' 数据截至 <b>' + tr.dataAsOf + '</b>（BR-210 &lt;1h ✓）' +
    '<span class="csub">· API mock：<code>POST /admin-api/ims/dc/trace/query</code></span>' +
    '<span' + costCls + '>耗时 ' + tr.queryCostMs + 'ms</span></div>';
  h += '<div class="card" style="padding:14px 16px;margin-bottom:12px"><div class="dsec" style="margin-top:0">① 选源头（GET /dc/trace/entry）</div>';
  h += '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px">';
  DC_ENTRY_TYPES.forEach(function (t) {
    const on = tr.filterType === t.k;
    h += '<span class="chip' + (on ? '" style="cursor:pointer;background:var(--blue-bg)' : '" style="cursor:pointer') + '" onclick="dcTraceFilterType(\'' + t.k + '\')">' + t.l + '</span>';
  });
  if (tr.filterType) h += '<span class="chip pp" style="cursor:pointer" onclick="dcTraceFilterType(\'\')">全部</span>';
  h += '</div><div class="tbl-wrap"><table><thead><tr><th>类型</th><th>标签</th><th>提示</th><th>操作</th></tr></thead><tbody>';
  DC_SOURCES.forEach(function (s, i) {
    if (tr.filterType && s.entryType !== tr.filterType) return;
    const sel = tr.sourceIdx === i;
    h += '<tr' + (sel ? ' style="background:var(--blue-bg)"' : '') + '><td>' + tag(s.entryType, 'blue') + '</td><td style="font-weight:500">' + s.entryLabel + '</td><td class="csub">' + s.hint + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="dcTracePickSource(' + i + ')">' + (sel ? '已选源头' : '设为源头') + '</span></td></tr>';
  });
  h += '</tbody></table></div></div>';
  if (tr.sourceIdx == null) {
    h += '<div class="card" style="padding:40px;text-align:center;color:var(--text2)">请选择上方源头，系统将加载关联关系图与场次明细（非 toast 占位）。</div>';
    return h;
  }
  const src = DC_SOURCES[tr.sourceIdx];
  h += '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:4px 0 10px;font-size:12.5px">';
  h += '<span class="csub">路径：</span><span class="chip" style="cursor:pointer" onclick="dcTraceBreadcrumb(0)">源头：' + src.entryLabel + '</span>';
  tr.path.forEach(function (p, j) {
    h += '<span class="csub">›</span><span class="chip" style="cursor:pointer' + (j === tr.path.length - 1 ? ';background:var(--blue-bg)' : '') + '" onclick="dcTraceBreadcrumb(' + (j + 1) + ')">' + p + '</span>';
  });
  h += '</div>';
  const pack = dcTraceGraphPack(tr.focusNodeId);
  const rels = pack.rels[tr.focusNodeId] || [];
  if (rels.length) {
    h += '<div class="dc-rel-bar"><span class="lbl">② 下一层关联：</span>';
    rels.forEach(function (r) {
      h += '<span class="btn btn-sec btn-sm" onclick="dcTraceFollowRel(\'' + r.id + '\')">' + r.label + '</span>';
    });
    h += '</div>';
  }
  const splitCls = 'dc-trace-split' + (tr.view === 'graph' ? ' single-graph' : tr.view === 'list' ? ' single-list' : '');
  h += '<div class="' + splitCls + '">';
  if (tr.view !== 'list') h += '<div class="card dc-graph-panel">' + dcTraceGraphSvg(pack, tr.focusNodeId) + '</div>';
  if (tr.view !== 'graph') h += '<div class="card dc-list-panel"><div class="dsec" style="margin:12px 12px 0">③ 明细（mode=DETAIL）</div><div style="padding:0 12px 12px">' + dcTraceListHtml(tr.focusNodeId) + '</div></div>';
  h += '</div>';
  return h;
}
function dcTraceGraphSvg(pack, focusId) {
  const pos = {
    n_person: [20, 30], n_acct1: [160, 30], n_asset1: [300, 10], n_asset2: [300, 70],
    n_sess: [440, 30], n_cost: [580, 30], n_profit: [720, 30]
  };
  let svg = '<div class="dc-graph-svg-wrap"><svg width="860" height="130" viewBox="0 0 860 130"><defs><marker id="dc_ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="#86868b"/></marker></defs>';
  pack.edges.forEach(function (e) {
    const a = pos[e[0]], b = pos[e[1]];
    if (!a || !b) return;
    svg += '<line x1="' + (a[0] + 88) + '" y1="' + (a[1] + 28) + '" x2="' + b[0] + '" y2="' + (b[1] + 28) + '" stroke="#c7c7cc" stroke-width="1.4" marker-end="url(#dc_ar)"/>';
  });
  pack.nodes.forEach(function (n) {
    const p = pos[n.nodeId];
    if (!p) return;
    const col = DC_NODE_COL[n.nodeType] || '#666';
    const hl = n.nodeId === focusId ? ' dc-node-hl' : '';
    svg += '<g class="dc-node-g' + hl + '" style="cursor:pointer" onclick="dcTraceNodeClick(\'' + n.nodeId + '\')">' +
      '<rect x="' + p[0] + '" y="' + p[1] + '" width="92" height="56" rx="8" fill="' + col + '" opacity="0.14"/>' +
      '<rect x="' + p[0] + '" y="' + p[1] + '" width="92" height="56" rx="8" fill="none" stroke="' + col + '" stroke-width="1.2"/>' +
      '<text x="' + (p[0] + 46) + '" y="' + (p[1] + 22) + '" text-anchor="middle" font-size="11" font-weight="600" fill="' + col + '">' + n.nodeLabel + '</text>' +
      '<text x="' + (p[0] + 46) + '" y="' + (p[1] + 38) + '" text-anchor="middle" font-size="9" fill="#86868b">' + n.sub + '</text>' +
      '<text x="' + (p[0] + 46) + '" y="' + (p[1] + 50) + '" text-anchor="middle" font-size="9" fill="#86868b">' + n.metrics + '</text></g>';
  });
  svg += '</svg><div class="hint" style="text-align:center;padding:0 8px 8px">点击节点切换焦点；关联 chip 模拟再次 POST /dc/trace/query（走查 #13）</div></div>';
  return svg;
}
function dcTraceListHtml(focusNodeId) {
  let rows = '';
  DC_DETAIL_ROWS.forEach(function (d) {
    const hl = d.nodeId === focusNodeId || focusNodeId === 'n_sess' || focusNodeId === 'n_acct1';
    rows += '<tr' + (hl ? ' style="background:rgba(0,113,227,.06)"' : '') + '>' +
      '<td class="mono num" style="font-size:11px;color:var(--blue);cursor:pointer" onclick="dcTraceSessionDetail(\'' + d.sessionCode + '\')">' + d.sessionCode + '</td>' +
      '<td>' + d.sessionTitle + '</td><td>' + tag(d.platform, 'blue') + '</td><td class="mono" style="font-size:11px">' + d.accountNo + '</td>' +
      '<td class="num">' + fmtMoney(d.gmv) + '</td><td class="num pos">' + fmtMoney(d.netProfit) + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="dcTraceNodeClick(\'' + d.nodeId + '\')">聚焦</span></td></tr>';
  });
  return tbl(['场次 ID', '名称', '平台', '账号', 'GMV', '净利润', '操作'], rows);
}
function dcTraceFilterType(k) {
  dcTraceEnsure().filterType = k;
  renderPage();
}
function dcTracePickSource(i) {
  const tr = dcTraceEnsure();
  tr.sourceIdx = i;
  tr.path = [];
  tr.focusNodeId = 'n_acct1';
  tr.queryCostMs = 240 + Math.floor(Math.random() * 120);
  renderPage();
}
function dcTraceNodeClick(nodeId) {
  dcTraceEnsure().focusNodeId = nodeId;
  dcTraceRefreshCost();
  renderPage();
}
function dcTraceFollowRel(relId) {
  const tr = dcTraceEnsure();
  const pack = dcTraceGraphPack(tr.focusNodeId);
  const rels = pack.rels[tr.focusNodeId] || [];
  const r = rels.find(function (x) { return x.id === relId; });
  if (!r) return;
  if (r.detail) {
    dcTraceSessionDetail('IMS202609100DY0131');
    return;
  }
  tr.path.push(r.crumb);
  tr.focusNodeId = r.targetId;
  dcTraceRefreshCost();
  renderPage();
}
function dcTraceBreadcrumb(keep) {
  const tr = dcTraceEnsure();
  tr.path = tr.path.slice(0, keep);
  dcTraceRefreshCost();
  renderPage();
}
function dcTraceSetView(v) {
  dcTraceEnsure().view = v;
  renderPage();
}
function dcTraceRefreshCost() {
  dcTraceEnsure().queryCostMs = 220 + Math.floor(Math.random() * 200);
}
function dcTraceExport() {
  const tr = dcTraceEnsure();
  if (tr.sourceIdx == null) { toast('请先选择穿透源头', 'warn'); return; }
  toast('GET /dc/trace/export · XLSX 已生成（mock OSS 60s URL）', 'success');
}
function dcTraceSessionDetail(code) {
  openDrawer('场次明细 · ' + code, '<div class="hint">GET /admin-api/ims/dc/trace/detail/{sessionCode}</div>' +
    '<div class="dsec">下播数据</div><div class="card" style="padding:10px">GMV ' + fmtMoney(412800) + ' · 退款 ¥12,400 · UV 18,200 · 时长 186 min</div>' +
    '<div class="dsec">三级利润（FIN-002）</div><div class="card" style="padding:10px">毛利 ¥198,400 · 经营利润 ¥172,100 · 净利润 ¥163,620 · 净利率 39.6%</div>' +
    '<div class="dsec">链路人员</div><div class="card" style="padding:10px">苏杳（实名人）· 赵敏（运营）· 账号 神鱼体育</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '720px');
}
/* ===================== 17b BI 数据分析叶（走查 #17 · 废止场次/作品 Tab） ===================== */
/* BI-002 多维下钻状态：state.bi.drill = { cat: '直播', rpt: '场次分析', path: ['全部平台','抖音'] } */
function biPageKind() {
  if (state.page === 'biShare') return 'share';
  if (state.page === 'biList' && state.tab.biList === 'share') return 'share';
  const m = { biList: 'list', biDesign: 'design', biPreview: 'preview' };
  return m[state.page] || 'list';
}
PAGES.biList = PAGES.biDesign = PAGES.biPreview = PAGES.biShare = function () {
  const kind = biPageKind();
  let h = pgHead(state.page,
    kind === 'preview' ? '<button class="btn btn-sec" onclick="biDrillReset()">' + ic('clock', 15) + '重置路径</button>' :
      kind === 'share' ? '<button class="btn btn-sec" onclick="biSubscribe()">' + ic('bell', 15) + '订阅推送</button>' :
        kind === 'design' ? '<button class="btn btn-pri" onclick="biAdd()">' + ic('plus', 15) + '新建报表</button>' :
          '<button class="btn btn-sec" onclick="biSubscribe()">' + ic('bell', 15) + '订阅推送</button><button class="btn btn-pri" onclick="go(\'biDesign\')">' + ic('plus', 15) + '新建报表</button>');
  h += '<div class="hint" style="margin-bottom:8px">M6 八张标准报表 → <span class="btn-txt btn" onclick="go(\'bi0Report\')">数据报表 · 标准报表</span>；场次链路 → <span class="btn-txt btn" onclick="go(\'dc\')">数据分析 · 穿透查询</span>；作品监测 → <span class="btn-txt btn" onclick="go(\'mon\')">作品监测</span>。</div>';
  if (kind === 'preview') return h + biDrillTab();
  if (kind === 'share') return h + biSubscribeTab();
  if (kind === 'design') return h + biDesignerTab();
  return h + biOverviewTab();
};
function biSubscribeTab() {
  return tbl(['订阅', '周期', '报表', '状态', '操作'],
    '<tr><td>直播周报</td><td>每周一</td><td>场次分析</td><td>' + tag('生效', 'green') + '</td><td><span class="btn btn-sec btn-sm" onclick="toast(\'编辑订阅\',\'success\')">编辑</span></td></tr>' +
    '<tr><td>GMV 日报</td><td>每日 09:00</td><td>经营总览</td><td>' + tag('暂停', 'gray') + '</td><td><span class="btn btn-sec btn-sm" onclick="toast(\'编辑订阅\',\'success\')">编辑</span></td></tr>');
}
function biDesignerTab() {
  const ds = state.tab.biDesignDs || 'METRIC_LIB';
  let h = '<div class="card" style="padding:12px 14px;margin-bottom:10px"><div class="rowline" style="justify-content:space-between;flex-wrap:wrap;gap:8px">' +
    '<div><b style="font-size:14px">报表设计器</b> <span class="chip">草稿</span> <span class="csub">· 对标 DW <code>bi-designer</code> · 17b BI-001</span></div>' +
    '<div class="rowline" style="gap:6px">' +
    '<button class="btn btn-sec btn-sm" onclick="toast(\'撤销\',\'info\')">撤销</button>' +
    '<button class="btn btn-sec btn-sm" onclick="toast(\'已保存草稿\',\'success\')">保存</button>' +
    '<button class="btn btn-sec btn-sm" onclick="toast(\'预览\',\'success\')">预览</button>' +
    '<button class="btn btn-pri btn-sm" onclick="toast(\'发布版本\',\'success\')">发布</button></div></div></div>';
  h += '<div class="bi-dsn"><div class="panel"><div class="csub" style="margin-bottom:8px">数据集</div>' +
    ['METRIC_LIB', 'CUSTOM_QUERY', 'DWS_AGGREGATION'].map(function (d) {
      const on = ds === d;
      const lbl = d === 'METRIC_LIB' ? '指标库' : d === 'CUSTOM_QUERY' ? '已发布查询' : '宽表聚合';
      const dis = d === 'DWS_AGGREGATION';
      return '<div class="pill' + (on ? ' on' : '') + '" style="display:block;margin-bottom:6px;padding:6px 10px;font-size:12px;cursor:' + (dis ? 'not-allowed' : 'pointer') + ';opacity:' + (dis ? '.55' : '1') + '" onclick="' + (dis ? 'toast(\'DWS 字段 BLOCKED\',\'info\')' : 'state.tab.biDesignDs=\'' + d + '\';renderPage()') + '">' + lbl + '</div>';
    }).join('') +
    '<div class="dsec" style="margin-top:10px">字段</div>' +
    '<label class="pill on" style="display:block;margin:4px 0;padding:4px 8px;font-size:11px"><input type="checkbox" checked disabled> metricCode</label>' +
    '<label class="pill" style="display:block;margin:4px 0;padding:4px 8px;font-size:11px"><input type="checkbox"> ipGroupName</label>' +
    '<label class="pill" style="display:block;margin:4px 0;padding:4px 8px;font-size:11px"><input type="checkbox"> platformCode</label></div>';
  h += '<div class="panel" style="padding:8px"><div class="csub" style="margin-bottom:6px">画布 · 行/列/值/筛选（V3 拖拽占位）</div><div class="bi-canvas">' +
    '<div class="bi-wgt" style="width:46%"><b>KPI</b><div class="num" style="font-size:18px;margin-top:4px">¥412.8万</div><div class="csub">GMV · 本月</div></div>' +
    '<div class="bi-wgt" style="width:48%"><b>柱状图</b><div style="height:48px;margin-top:6px;background:linear-gradient(90deg,var(--blue) 60%,var(--green) 40%);opacity:.35;border-radius:4px"></div></div>' +
    '<div class="bi-wgt" style="width:96%"><b>明细表</b><div class="csub" style="margin-top:4px">维度 × 指标 · POST /admin-api/ims/bi/report/query 预览</div></div></div></div>';
  h += '<div class="panel"><div class="csub">属性（对标 DW 右栏）</div>' +
    '<label style="display:block;margin:8px 0 4px;font-size:11px;color:var(--text2)">报表名称</label><input class="form-input" style="width:100%;height:30px" value="运营自助周报">' +
    '<label style="display:block;margin:10px 0 4px;font-size:11px;color:var(--text2)">数据源</label><select class="form-input" style="width:100%;height:30px"><option>指标库 · 播放量</option><option>已发布查询 · IP 组周产出</option></select>' +
    '<button class="btn btn-pri btn-sm" style="width:100%;margin-top:12px" onclick="toast(\'预览查询已提交\',\'success\')">运行预览</button></div></div>';
  h += '<div class="hint">M6 八张固定 slug 无设计器入口；大屏模板在 <span class="btn-txt btn" onclick="go(\'bi0Screen\')">数据报表 · 大屏配置</span>。</div>';
  return h;
}
/* BI Tab1：报表总览（报表树 + GMV 趋势 + 平台分布） */
function biOverviewTab() {
  let h = '';
  const cats = { '运营': ['经营总览', '转化漏斗', '渠道对比'], '直播': ['场次分析', '主播榜', '风控看板'], '内容': ['作品表现', 'SOP 合规'], '财务': ['成本结构', '分成结算'] };
  const dr = state.bi && state.bi.drill ? state.bi.drill : { cat: '直播', rpt: '场次分析', path: [] };
  /* 顶部四统计卡（与 fin/dc 页风格一致） */
  h += '<div class="g4"><div class="card stat"><span class="l">本月 GMV</span><div class="n" style="font-size:22px">¥412.8 万</div><div class="d"><span style="color:var(--green);font-weight:600">环比 +18.6%</span> · 直播 + 短视频</div></div>' +
    '<div class="card stat"><span class="l">直播场次</span><div class="n" style="font-size:22px">14 <span style="font-size:13px;color:var(--text2);font-weight:500">场</span></div><div class="d">覆盖 4 平台 · 互动率均值 4.7%</div></div>' +
    '<div class="card stat"><span class="l">可分析报表</span><div class="n" style="font-size:22px">10 <span style="font-size:13px;color:var(--text2);font-weight:500">张</span></div><div class="d">运营 / 直播 / 内容 / 财务 · 人效见组织人效</div></div>' +
    '<div class="card stat"><span class="l">订阅推送</span><div class="n" style="font-size:22px">4 <span style="font-size:13px;color:var(--text2);font-weight:500">条</span></div><div class="d">3 条生效中 · 1 条已暂停</div></div></div>';
  let tree = '';
  Object.keys(cats).forEach(function (c, i) {
    tree += '<div class="nav-g' + (i === 0 ? '' : ' closed') + '"><div class="nav-g-h" style="padding:8px 6px" onclick="this.parentNode.classList.toggle(\'closed\')">' + c +
      '<span class="caret">' + ic('chev', 12) + '</span></div>';
    cats[c].forEach(function (r) {
      tree += '<div class="nav-item" style="padding:5px 8px;font-size:12px' + (dr.cat === c && dr.rpt === r ? ';background:var(--blue-bg);color:var(--blue);font-weight:500' : '') + '" onclick="biOpenRpt(\'' + c + '\',\'' + r + '\')">' + r + '</div>';
    });
    tree += '</div>';
  });
  /* GMV 折线（SVG + 渐变面积填充） */
  const pts = [42, 55, 48, 63, 58, 72, 66, 80, 75, 88, 82, 96, 90, 104, 98, 112, 108, 122, 118, 132, 126, 140, 136, 148, 142, 156, 150, 164, 158, 172];
  const w = 640, hh = 160, max = 180;
  let path = '', area = '', dots = '';
  const px = [], py = [];
  pts.forEach(function (v, i) {
    const x = 8 + i * ((w - 24) / (pts.length - 1));
    const y = hh - 18 - (v / max) * (hh - 40);
    px.push(x); py.push(y);
    path += (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1);
    dots += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="2.2" fill="#0071e3"/>';
  });
  area = 'M' + px[0].toFixed(1) + ' ' + (hh - 18) + ' ' + path.replace(/^M/, 'L') + ' L' + px[px.length - 1].toFixed(1) + ' ' + (hh - 18) + ' Z';
  const plat = [['抖音', 58], ['视频号', 18], ['斗鱼', 14], ['快手', 10]];
  const gmv = [['W1', 42], ['W2', 48], ['W3', 55], ['W4', 63], ['W5', 71], ['W6', 78]];
  h += '<div class="g2r"><div><div class="card" style="padding:16px 14px">' +
    '<div class="hd-row" style="margin-bottom:8px"><h3 style="font-size:14px">报表目录</h3><span class="chip">5 域 · 12 张</span></div>' +
    tree +
    '<div class="dsec" style="margin-top:12px">当前报表</div>' +
    '<div style="padding:4px 6px 2px"><span style="font-size:11px;color:var(--text2)">正在查看</span>' +
    '<div style="font-size:14px;font-weight:600;margin-top:3px">' + dr.cat + ' <span style="color:var(--text2);font-weight:400">/</span> ' + dr.rpt + '</div>' +
    '<div class="rowline" style="gap:8px;margin-top:10px">' +
    '<span class="btn btn-pri btn-sm" onclick="setTab(\'bi\',\'多维下钻\')">进入多维下钻 →</span>' +
    '<span class="btn btn-sec btn-sm" onclick="setTab(\'bi\',\'场次明细\')">场次明细</span></div>' +
    '<div class="hint" style="margin-top:8px">点击目录中任一报表即可切换，下钻与明细将联动当前报表。</div></div></div></div>' +
    '<div><div class="card"><div class="hd-row"><h3>近 30 天 GMV 趋势</h3><span class="chip">直播 + 短视频</span></div>' +
    '<svg width="100%" viewBox="0 0 ' + w + ' ' + hh + '" style="display:block">' +
    '<defs><linearGradient id="gmvgrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0071e3" stop-opacity=".22"/><stop offset="1" stop-color="#0071e3" stop-opacity=".02"/></linearGradient></defs>' +
    '<line x1="0" y1="' + (hh - 18) + '" x2="' + w + '" y2="' + (hh - 18) + '" stroke="rgba(0,0,0,.08)"/>' +
    '<line x1="0" y1="' + ((hh - 18) / 2 + 9) + '" x2="' + w + '" y2="' + ((hh - 18) / 2 + 9) + '" stroke="rgba(0,0,0,.05)" stroke-dasharray="3 4"/>' +
    '<path d="' + area + '" fill="url(#gmvgrad)"/>' +
    '<path d="' + path + '" fill="none" stroke="#0071e3" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>' + dots + '</svg>' +
    '<div class="rowline" style="justify-content:space-between;margin-top:4px"><span style="font-size:11px;color:var(--text2)">08-14</span><span style="font-size:11px;color:var(--text2)">09-12</span><span style="font-size:11px;color:var(--text2);font-weight:600;color:var(--blue)">累计 ¥412.8 万 · 环比 +18.6%</span></div></div>' +
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px">' +
    '<div class="card"><div class="hd-row"><h3 style="font-size:15px">平台场次分布（本月）</h3><span style="font-size:11.5px;color:var(--text2)">14 场</span></div><div class="bars" style="height:96px">' +
    plat.map(function (p) { return '<div class="b" style="height:' + Math.max(10, p[1] * 1.5) + '%;background:var(--blue)" title="' + p[0] + ' ' + p[1] + '%"></div>'; }).join('') + '</div>' +
    '<div class="rowline" style="justify-content:space-between;margin-top:6px">' + plat.map(function (p) { return '<span style="font-size:11px;color:var(--text2)">' + p[0] + ' <b style="color:var(--text);font-weight:600">' + p[1] + '%</b></span>'; }).join('') + '</div></div>' +
    '<div class="card"><div class="hd-row"><h3 style="font-size:15px">近 6 周 GMV 周汇总</h3><span style="font-size:11.5px;color:var(--text2)">周 GMV</span></div>' +
    '<div class="bars" style="height:96px">' + gmv.map(function (g) { return '<div class="b" style="height:' + Math.max(12, g[1] / 0.9) + '%;background:var(--green)" title="' + g[0] + ' ¥' + (g[1] / 100).toFixed(2) + ' 万"></div>'; }).join('') + '</div>' +
    '<div class="rowline" style="justify-content:space-between;margin-top:6px">' + gmv.map(function (g) { return '<span style="font-size:11px;color:var(--text2)">' + g[0] + ' <b style="color:var(--text);font-weight:600">' + g[1] / 100 + '万</b></span>'; }).join('') + '</div></div>' +
    '</div></div>';
  return h;
}
/* BI Tab2：多维下钻（BI-002 维度切换 + 面包屑 + 联动明细） */
function biDrillTab() {
  const dr = state.bi && state.bi.drill ? state.bi.drill : { cat: '直播', rpt: '场次分析', path: [] };
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
  let h = '<div class="hint" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">' + ic('search', 13) +
    ' BI-002 多维查询下钻：当前报表「' + dr.rpt + '」，支持 平台 / 主播 / 账号 / 类目 四个维度逐层下钻至场次明细。</div>';
  h += '<div class="card"><div class="hd-row"><h3>' + dr.rpt + ' · 多维下钻</h3>' +
    '<div class="pills" style="gap:4px">' + dims.map(function (dm) { return '<label class="pill' + (dm === curDim ? ' on' : '') + '" style="padding:2px 9px;font-size:11px"><input type="radio" name="P_bidim" value="' + dm + '"' + (dm === curDim ? ' checked' : '') + ' onchange="biSwitchDim(\'' + dm + '\')"><span>' + dm + '</span></label>'; }).join('') + '</div></div>' +
    '<div style="margin:6px 0 10px">' + crumbs + '</div>' +
    (drillLv === 0 ? tbl(['维度（' + curDim + '）· 点击下钻', 'GMV', '订单数', '观看人数', '操作'], dimRows) :
      tbl(['日期', '场次 ID · ' + (drillPath[0] || ''), 'GMV', '互动率', '观看人数'], dimRows)) + '</div>';
  return h;
}
/* BI Tab3：场次明细（完整明细表 + 订阅推送管理） */
function biSessionTab() {
  let rows = '';
  [['09-12', '抖音', 'IMS202609110DY0138', 186400, 4.8, 1226],
   ['09-11', '视频号', 'IMS202609100DY0131', 412800, 6.1, 3482],
   ['09-10', '斗鱼', 'IMS202609090DY0127', 96700, 3.9, 744],
   ['09-09', '快手', 'IMS202609070DY0118', 61200, 3.2, 512],
   ['09-08', '抖音', 'IMS202609080DY0121', 43800, 2.8, 388],
   ['09-07', '视频号', 'IMS202609060DY0112', 128600, 5.2, 1520],
   ['09-06', '抖音', 'IMS202609050DY0108', 152300, 4.4, 1826],
   ['09-05', '斗鱼', 'IMS202609040DY0105', 38200, 2.5, 298]].forEach(function (d) {
    rows += '<tr><td class="num">' + d[0] + '</td><td>' + d[1] + '</td><td class="mono num" style="font-size:11.5px;color:var(--blue);cursor:pointer" onclick="toast(\'场次穿透：' + d[2] + '（联动直播管理）· 原型示意\',\'success\')">' + d[2] + '</td>' +
      '<td class="num" style="font-weight:500">' + fmtMoney(d[3]) + '</td><td class="num">' + d[4] + '%</td><td class="num">' + d[5].toLocaleString() + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="toast(\'场次全量数据：' + d[2] + ' · 下播数据回流 + 成本/利润联动 · 原型示意\',\'success\')">详情</span></td></tr>';
  });
  const subs = [
    ['SUB-001', '经营总览日报', '每工作日 09:00', '站内 + 钉钉', '齐活林、陈楚龙', '生效中'],
    ['SUB-002', '直播场次周报', '每周一 10:00', '钉钉群', '研发一部AI提效沟通群', '生效中'],
    ['SUB-003', '成本结构月报', '每月 1 日 09:00', '邮件', '财务核算组', '生效中'],
    ['SUB-004', '主播榜实时榜', '实时（变更推送）', '站内', '运营组', '已暂停']
  ];
  const sc = { '生效中': 'green', '已暂停': 'orange' };
  let sRows = '';
  subs.forEach(function (s) {
    sRows += '<tr><td class="mono num" style="color:var(--blue)">' + s[0] + '</td><td style="font-weight:500">' + s[1] + '</td><td>' + s[2] + '</td><td>' + s[3] + '</td><td style="font-size:12px">' + s[4] + '</td>' +
      '<td>' + tag(s[5], sc[s[5]]) + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="toast(\'' + (s[5] === '生效中' ? '已暂停订阅：' : '已恢复订阅：') + s[1] + '\',\'success\')">' + (s[5] === '生效中' ? '暂停' : '恢复') + '</span></td></tr>';
  });
  return '<div class="hint" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">' + ic('doc', 13) +
    ' 场次明细为多维下钻的最细粒度（场次 ID 与 10 直播管理、11 财务核算、12 数据中心三处联动）。</div>' +
    '<div class="sec">场次明细（近 8 场）</div>' +
    qbar(qs(['全部平台', '抖音', '视频号', '斗鱼', '快手']) + qi('场次 ID', 140) + '<input type="month" style="width:118px" value="2026-09">') +
    tbl(['日期', '平台', '场次 ID', 'GMV', '互动率', '观看人数', '操作'], rows) +
    '<div class="sec">订阅推送管理（BI-003）</div>' +
    tbl(['订阅编号', '报表名称', '推送频率', '推送渠道', '接收人', '状态', '操作'], sRows) +
    '<div class="hint" style="margin-top:10px">点击右上「订阅推送」可新增订阅；本表管理已有 4 条订阅的暂停 / 恢复。</div>';
}
/* BI Tab4：作品监测（18 作品监测入口 · 账号/平台/发布日期/监测状态查询 + 作品表 + 详情抽屉） */
const WORKS = [
  { id: 'W-2026-0091', title: '秋季新品跑鞋首发实测', acct: 'ACCT-2026-0001 · 抖音', plat: '抖音', pub: '2026-09-24 19:30', plays: 286400, likes: 18400, cmts: 1266, st: '监测中' },
  { id: 'W-2026-0090', title: '直播间高光切片 · 3 分钟燃脂训练', acct: 'ACCT-2026-0002 · 视频号', plat: '视频号', pub: '2026-09-23 21:00', plays: 96700, likes: 6240, cmts: 488, st: '监测中' },
  { id: 'W-2026-0089', title: '跑步鞋中底材料对比（EVA/TPU/Pebax）', acct: 'ACCT-2026-0001 · 抖音', plat: '抖音', pub: '2026-09-21 12:00', plays: 412800, likes: 32600, cmts: 2044, st: '正常' },
  { id: 'W-2026-0088', title: '健身器材选购避坑指南', acct: 'ACCT-2026-0034 · 快手', plat: '快手', pub: '2026-09-20 18:00', plays: 61200, likes: 3980, cmts: 312, st: '正常' },
  { id: 'W-2026-0087', title: '运动服饰穿搭 · 秋季通勤两件套', acct: 'ACCT-2026-0002 · 视频号', plat: '视频号', pub: '2026-09-18 20:00', plays: 128600, likes: 9860, cmts: 756, st: '正常' },
  { id: 'W-2026-0086', title: '缓震跑鞋实测 · 5 公里挑战', acct: 'ACCT-2026-0003 · 斗鱼', plat: '斗鱼', pub: '2026-09-16 17:30', plays: 38200, likes: 2140, cmts: 168, st: '限流预警' },
  { id: 'W-2026-0085', title: '营养补给怎么选 · 蛋白粉横评', acct: 'ACCT-2026-0001 · 抖音', plat: '抖音', pub: '2026-09-14 11:00', plays: 152300, likes: 11800, cmts: 942, st: '正常' },
  { id: 'W-2026-0084', title: '直播间违禁词避雷合集', acct: 'ACCT-2026-0034 · 快手', plat: '快手', pub: '2026-09-12 15:00', plays: 43800, likes: 2260, cmts: 176, st: '下架' }
];
function biWorksTab() {
  const wsc = { '正常': 'green', '监测中': 'blue', '限流预警': 'orange', '下架': 'red' };
  let rows = '';
  WORKS.forEach(function (w, i) {
    rows += '<tr><td style="font-weight:500;cursor:pointer;color:var(--blue)" onclick="biWorkDetail(' + i + ')">' + w.title + '</td>' +
      '<td class="mono" style="font-size:11.5px;color:var(--text2)">' + w.acct + '</td>' +
      '<td>' + w.plat + '</td><td class="num" style="font-size:12px">' + w.pub + '</td>' +
      '<td class="num" style="font-weight:600">' + w.plays.toLocaleString() + '</td>' +
      '<td class="num">' + w.likes.toLocaleString() + '</td><td class="num">' + w.cmts.toLocaleString() + '</td>' +
      '<td>' + tag(w.st, wsc[w.st]) + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="biWorkDetail(' + i + ')">详情</span></td></tr>';
  });
  let h = '<div class="hint" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">' + ic('film', 13) +
    ' 18 作品监测：作品发布后自动纳入监测（数据回流 + 状态预警），点击行可查看各平台数据趋势与状态说明。</div>';
  h += qbar(qi('账号/作品名', 140) + qs(['全部平台', '抖音', '视频号', '斗鱼', '快手']) +
    '<input type="date" style="width:112px" value="2026-09-01">' + '<span style="font-size:12px;color:var(--text2);align-self:center">至</span>' +
    '<input type="date" style="width:112px" value="2026-09-30">' + qs(['全部状态', '正常', '监测中', '限流预警', '下架'], 100));
  h += tbl(['作品名', '账号', '平台', '发布时间', '播放', '点赞', '评论', '监测状态', '操作'], rows);
  return h;
}
/* 18 作品监测：作品详情抽屉（各平台数据趋势占位 + 状态说明） */
function biWorkDetail(i) {
  const w = WORKS[i];
  const wsc = { '正常': 'green', '监测中': 'blue', '限流预警': 'orange', '下架': 'red' };
  const stDesc = {
    '正常': '监测数据平稳，各项指标处于账号历史均值区间内，无需干预。',
    '监测中': '作品新发布，处于重点监测窗口期，数据回流频率为每 2 小时一次。',
    '限流预警': '播放量增长显著低于同类作品均值，疑似平台限流，建议检查标题/封面合规性并联系平台对接人。',
    '下架': '作品已被平台下架或自行删除，监测终止，需排查违规原因并留档。'
  };
  const body = '<div class="kv"><div><div class="k">作品编号</div><div class="v mono" style="color:var(--blue)">' + w.id + '</div></div>' +
    '<div><div class="k">账号 / 平台</div><div class="v">' + w.acct + ' · ' + w.plat + '</div></div></div>' +
    '<div class="dsec">作品名称</div><div style="font-size:13px;font-weight:600">' + w.title + '</div>' +
    '<div class="dsec">核心数据（截至 2026-09-28）</div>' +
    '<div class="kv"><div><div class="k">播放</div><div class="v" style="font-weight:600">' + w.plays.toLocaleString() + '</div></div>' +
    '<div><div class="k">点赞</div><div class="v">' + w.likes.toLocaleString() + '</div></div>' +
    '<div><div class="k">评论</div><div class="v">' + w.cmts.toLocaleString() + '</div></div></div>' +
    '<div class="dsec">各平台数据趋势</div>' +
    ['播放量趋势', '点赞趋势', '评论趋势'].map(function (t) {
      return '<div class="hint" style="margin:4px 0">' + ic('chart', 12) + ' ' + t + '（' + w.plat + ' · 近 7 天）：原型占位 —— 上线后展示分平台数据回流曲线。</div>';
    }).join('') +
    '<div class="dsec">监测状态说明</div>' +
    '<div style="font-size:12.5px;line-height:1.7">' + tag(w.st, wsc[w.st]) + ' ' + stDesc[w.st] + '</div>' +
    '<div class="hint">作品数据与 08 账号管理（账号池）、19 IP 组（作品归属口径）联动；限流/下架事件将推送 13 预警中心。</div>';
  openDrawer('作品详情 · ' + w.title, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '600px');
}
/* BI-002：打开报表（报表树点击） */
function biOpenRpt(cat, rpt) {
  if (!state.bi) state.bi = {};
  state.bi.drill = { cat: cat, rpt: rpt, path: [] };
  if (BI_IDS.indexOf(state.page) >= 0) renderPage();
  toast('已打开报表：' + cat + ' / ' + rpt + '（默认维度汇总 · 可下钻）', 'success');
}
/* BI-002：切换分析维度（平台/主播/账号/类目） */
function biSwitchDim(dim) {
  if (!state.bi) state.bi = {};
  state.bi.dim = dim;
  if (state.bi.drill) state.bi.drill.path = [];
  if (BI_IDS.indexOf(state.page) >= 0) renderPage();
  toast('已切换分析维度：' + dim + '（BI-002）', 'success');
}
/* BI-002：下钻（维度值 → 场次明细） */
function biDrillDown(val) {
  if (!state.bi) state.bi = {};
  if (!state.bi.drill) state.bi.drill = { cat: '直播', rpt: '场次分析', path: [] };
  state.bi.drill.path = [val];
  if (BI_IDS.indexOf(state.page) >= 0) renderPage();
  toast('下钻：' + (state.bi.dim || '平台') + ' → ' + val + '（显示场次明细）', 'success');
}
/* BI-002：面包屑回退（保留前 keep 层） */
function biDrillUp(keep) {
  if (state.bi && state.bi.drill) state.bi.drill.path = state.bi.drill.path.slice(0, keep);
  if (BI_IDS.indexOf(state.page) >= 0) renderPage();
  toast('已回退至第 ' + keep + ' 层下钻路径', 'success');
}
/* BI-002：重置下钻路径 */
function biDrillReset() {
  if (state.bi && state.bi.drill) state.bi.drill.path = [];
  if (BI_IDS.indexOf(state.page) >= 0) renderPage();
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

/* ===================== 19 EFF 组织人效（19 = IP 组与组织人效合并口径 · 含 IP 组管理 Tab） ===================== */
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
function effPageKind() {
  const tab = state.tab.eff || 'board';
  if (tab === 'relation') return 'relation';
  if (tab === 'inventory') return 'inventory';
  return 'board';
}
function effTabsHtml() {
  const tab = state.tab.eff || 'board';
  return '<div class="tabs"><div class="tab' + (tab === 'relation' ? ' on' : '') + '" onclick="state.tab.eff=\'relation\';renderPage()">归属关系</div>' +
    '<div class="tab' + (tab === 'inventory' ? ' on' : '') + '" onclick="state.tab.eff=\'inventory\';renderPage()">人效盘点</div>' +
    '<div class="tab' + (tab === 'board' ? ' on' : '') + '" onclick="state.tab.eff=\'board\';renderPage()">人效看板</div></div>';
}
function effPageBody() {
  const kind = effPageKind();
  let h = effTabsHtml();
  h += '<div class="hint" style="margin-bottom:8px">IP 组 CRUD → <span class="btn-txt btn" onclick="go(\'ipg\')">日常运营 · IP 组</span>（走查 #17 废止 eff 内 IP 组 Tab）。</div>';
  if (kind === 'relation') {
    return h + tbl(['人员', '类型', '归属目标', '分摊', '状态', '操作'],
      '<tr><td>苏杳</td><td>' + tag('主归属', 'blue') + '</td><td>主播组</td><td class="num">100%</td><td>' + tag('生效', 'green') + '</td><td><span class="btn btn-sec btn-sm" onclick="toast(\'变更归属\',\'success\')">变更</span></td></tr>' +
      '<tr><td>苏杳</td><td>' + tag('兼职', 'orange') + '</td><td>内容中心</td><td class="num">20%</td><td>' + tag('生效', 'green') + '</td><td><span class="btn btn-sec btn-sm" onclick="toast(\'变更归属\',\'success\')">变更</span></td></tr>');
  }
  if (kind === 'inventory') {
    return h + '<div class="card" style="padding:14px"><div class="csub">EFF-002 · 每月 2 日自动触发 · 覆盖率 100% 方可发布（BR-207）</div>' +
      tbl(['周期', '状态', '未覆盖', '操作'], '<tr><td>2026-09</td><td>' + tag('待发布', 'orange') + '</td><td class="num">3 人</td><td><span class="btn btn-pri btn-sm" onclick="go(\'effRelation\')">补归属</span></td></tr>') + '</div>';
  }
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
}
PAGES.eff = PAGES.effRelation = PAGES.effInventory = PAGES.effBoard = function () {
  const kind = effPageKind();
  let acts = kind === 'relation' ? '<button class="btn btn-pri" onclick="toast(\'建立归属 · R2/R1\',\'success\')">' + ic('plus', 15) + '建立归属</button>' :
    kind === 'inventory' ? '<button class="btn btn-pri" onclick="toast(\'触发月度盘点\',\'success\')">发起盘点</button>' :
      '<button class="btn btn-sec" onclick="exportX(this,\'人效月报\',EFFS.length)">导出月报</button>';
  return pgHead('eff', acts) + effPageBody();
};
/* 19 IP 组管理 Tab：IP 组与组织人效合并口径（复用 19 IP 组已完成能力，目标选择复用既有 pill 多选交互） */
const EFF_GROUPS = [
  { g: 'IPG-001', name: '跑步垂类 IP 组', lead: '苏杳', members: ['苏杳', '赵敏', '孙倩'], accts: 3, works: 46, gmv: 128.6, st: '运作中' },
  { g: 'IPG-002', name: '健身器材 IP 组', lead: '李澈', members: ['李澈', '何舟'], accts: 2, works: 28, gmv: 86.4, st: '运作中' },
  { g: 'IPG-003', name: '运动服饰 IP 组', lead: '陈默', members: ['陈默', '林岚', '王野'], accts: 2, works: 19, gmv: 42.2, st: '筹备中' }
];
function effGroupTab() {
  const sc = { '运作中': 'green', '筹备中': 'orange' };
  let rows = '';
  EFF_GROUPS.forEach(function (g, i) {
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + g.g + '</td><td style="font-weight:500">' + g.name + '</td>' +
      '<td>' + g.lead + '</td>' +
      '<td>' + g.members.map(function (m) { return '<span class="chip">' + m + '</span>'; }).join('') + '</td>' +
      '<td class="num">' + g.accts + '</td><td class="num">' + g.works + '</td><td class="num" style="font-weight:500">¥' + g.gmv + ' 万</td>' +
      '<td>' + tag(g.st, sc[g.st]) + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="effGroupDetail(' + i + ')">详情</span></td></tr>';
  });
  let h = '<div class="hint" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">' + ic('people', 13) +
    ' IP 组与组织人效为 19 号模块统一口径（复用 19 IP 组已完成能力）：组内成员人效自动并入 19 人效分摊与看板。</div>';
  h += qbar(qi('组名/组长', 120) + qs(['全部状态', '运作中', '筹备中'], 90) + qi('矩阵账号', 110), 'qSave(\'eff\')');
  h += tbl(['组编号', 'IP 组名称', '组长', '成员', '矩阵账号', '作品数（本月）', '带货 GMV（本月）', '状态', '操作'], rows);
  return h;
}
/* 19 IP 组详情抽屉（复用目标选择交互展示成员口径） */
function effGroupDetail(i) {
  const g = EFF_GROUPS[i];
  const body = '<div class="kv"><div><div class="k">IP 组 / 组长</div><div class="v">' + g.name + ' · ' + g.lead + '</div></div>' +
    '<div><div class="k">状态 / 矩阵账号</div><div class="v">' + g.st + ' · ' + g.accts + ' 个</div></div></div>' +
    '<div class="dsec">组成员（目标选择 · 复用既有交互）</div>' +
    '<div class="pills" style="flex-wrap:wrap">' + g.members.map(function (m) { return '<label class="pill on" style="cursor:default"><span>' + m + '</span></label>'; }).join('') + '</div>' +
    '<div class="dsec">本月产出</div><div class="kv"><div><div class="k">作品数</div><div class="v">' + g.works + ' 条</div></div>' +
    '<div><div class="k">带货 GMV</div><div class="v">¥' + g.gmv + ' 万</div></div></div>' +
    '<div class="hint">组内成员的兼职/主归属分摊已在 19 人效看板中体现（合并口径）；作品数据联动 18 作品监测。</div>';
  openDrawer('IP 组详情 · ' + g.name, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '560px');
}
/* 19 新建 IP 组（成员选择复用目标 pill 多选交互） */
function effGroupAdd() {
  const body = frow([
    { k: 'gname', label: 'IP 组名称', type: 'text', req: true, ph: '如：营养补给 IP 组' },
    { k: 'glead', label: '组长', type: 'select', req: true, opts: ['苏杳', '赵敏', '孙倩', '李澈', '陈默', '何舟'] }
  ]) +
    '<div class="fld wide"><label>组成员（多选）</label>' +
    '<div class="pills" style="flex-wrap:wrap">' +
    ['苏杳', '赵敏', '孙倩', '李澈', '何舟', '陈默', '林岚', '周晴'].map(function (c) { return '<label class="pill" style="cursor:pointer"><input type="checkbox" value="' + c + '" onchange="pillChk(this)" style="accent-color:var(--blue)"><span>' + c + '</span></label>'; }).join('') +
    '</div></div>';
  openDrawer('新建 IP 组', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="effGroupAddOk()">创建 IP 组</button>', '520px');
}
function effGroupAddOk() {
  if (!formValidate(['gname', 'glead'])) return;
  const no = 'IPG-' + String(EFF_GROUPS.length + 1).padStart(3, '0');
  EFF_GROUPS.push({ g: no, name: $('#F_gname').value, lead: $('#F_glead').value, members: [$('#F_glead').value], accts: 0, works: 0, gmv: 0, st: '筹备中' });
  formOk(no, 'IP 组已创建（19 IP 组与组织人效合并口径），可在 IP 组管理 Tab 中维护成员与矩阵账号', 'renderPage');
}

/* ===================== 20 AIR AI 资源中台（V1.5 专项） ===================== */
/* AIR-002 技能库：SKILL-1~4（来源→审核→版本→授权） */
const SKILLS = [
  { id: 'SKL-0001', name: '商品卖点提炼', cat: '内容生产', v: 'v1.3', st: '已发布', audit: '已通过', owner: '唐宁', grants: 12, calls: 486, desc: '基于商品参数与目标人群生成 3 组卖点文案，输出结构化 JSON（hook/points/cta）。' },
  { id: 'SKL-0002', name: '直播切片脚本生成', cat: '内容生产', v: 'v2.0', st: '已发布', audit: '已通过', owner: '孙倩', grants: 8, calls: 342, desc: '输入场次回放时间轴与高光区间，产出切片标题/封面文案/发布节奏建议。' },
  { id: 'SKL-0003', name: '短视频脚本分镜', cat: '内容生产', v: 'v1.1', st: '已发布', audit: '已通过', owner: '孙倩', grants: 9, calls: 298, desc: '按 SOP 节点提示词生成 15/30/60 秒分镜脚本，与 CONTENT 模块 SOP 联动。' },
  { id: 'SKL-0004', name: '竞品周报解读', cat: '数据分析', v: 'v1.0', st: '审核中', audit: '待复核', owner: '陈默', grants: 0, calls: 0, desc: '聚合 COMP 竞品周数据生成解读纪要，引用竞品库指标口径。' },
  { id: 'SKL-0005', name: '客诉话术助手', cat: '运营支持', v: 'v1.2', st: '已发布', audit: '已通过', owner: '唐宁', grants: 6, calls: 173, desc: '按客诉类型匹配话术库生成回复建议，支持多轮追问。' },
  { id: 'SKL-0006', name: '财务对账差异分析', cat: '财务', v: 'v0.9', st: '草稿', audit: '未提交', owner: '周晴', grants: 0, calls: 0, desc: '对账差异自动归因（充值/退款/手续费），输出差异清单。' }
];
/* AIR-004 专家库：EXPERT-1~3（system_prompt + skills + kbs 组装包） */
const EXPERTS = [
  { id: 'EXP-0001', name: '直播运营专家', scene: '直播复盘 / 开播策划', skills: ['SKL-0002', 'SKL-0001'], kbs: ['KB-0001', 'KB-0002'], v: 'v1.2', st: '已发布', grants: 7, calls: 215, owner: '唐宁', sysp: '你是神鱼体育直播运营专家，擅长抖音/快手直播间复盘与开播策划。回答须引用给定知识库片段并标注来源，严禁编造数据；涉及平台规则以最新知识库为准。' },
  { id: 'EXP-0002', name: '内容创作专家', scene: '短视频选题 / 脚本创作', skills: ['SKL-0003', 'SKL-0001'], kbs: ['KB-0003'], v: 'v2.1', st: '已发布', grants: 9, calls: 331, owner: '孙倩', sysp: '你是神鱼体育内容创作专家。基于品牌调性（专业运动 + 轻快表达）产出选题与分镜脚本，所有卖点必须来自技能输出的结构化结果，不得虚构商品参数。' },
  { id: 'EXP-0003', name: '数据分析专家', scene: '场次数据解读 / 周报解读', skills: ['SKL-0004'], kbs: ['KB-0002', 'KB-0004'], v: 'v1.0', st: '已发布', grants: 4, calls: 96, owner: '陈默', sysp: '你是神鱼体育数据分析专家，口径以 IMS 数据中心字典为准（场次 ID 编码 IMS+日期+平台码+序列）。先给结论再给明细，指标异常须标注环比与阈值。' },
  { id: 'EXP-0004', name: '财务核算专家', scene: '成本归集 / 分成测算', skills: [], kbs: ['KB-0002'], v: 'v0.8', st: '草稿', grants: 0, calls: 0, owner: '周晴', sysp: '你是神鱼体育财务核算专家，熟悉直播场次成本项与主播分成规则引擎。测算须列出成本项拆分与规则版本号。' },
  { id: 'EXP-0005', name: '客服质检专家', scene: '客诉回复 / 话术质检', skills: ['SKL-0005'], kbs: ['KB-0001'], v: 'v1.1', st: '已发布', grants: 5, calls: 128, owner: '唐宁', sysp: '你是神鱼体育客服质检专家。对客服回复按「准确性/合规性/温度」三维打分，命中机密级知识须脱敏输出。' }
];
/* AIR-006 知识库：KNOW-1~4（4 级密级 + RAGFlow 底座） */
const KBS = [
  { id: 'KB-0001', name: '商品知识库', docs: 486, chunks: 12842, secret: '内部', st: '已发布', grants: 18, provider: 'ragflow', owner: '唐宁', upd: '2026-09-18' },
  { id: 'KB-0002', name: '平台规则库', docs: 212, chunks: 6348, secret: '公开', st: '已发布', grants: 22, provider: 'ragflow', owner: '何舟', upd: '2026-09-17' },
  { id: 'KB-0003', name: '内容 SOP 知识库', docs: 96, chunks: 2714, secret: '内部', st: '已发布', grants: 11, provider: 'ragflow', owner: '孙倩', upd: '2026-09-15' },
  { id: 'KB-0004', name: '经营数据知识库', docs: 38, chunks: 1056, secret: '机密', st: '已发布', grants: 3, grantsLimit: '仅 R1/R3/R4 可授权', provider: 'ragflow', owner: '周晴', upd: '2026-09-12' },
  { id: 'KB-0005', name: '主播分成合同库', docs: 42, chunks: 0, secret: '机密', st: '入库审批中', grants: 0, provider: 'ragflow', owner: '周晴', upd: '2026-09-18' },
  { id: 'KB-0006', name: '股权与融资档案', docs: 6, chunks: 98, secret: '绝密', st: '已发布', grants: 1, grantsLimit: '仅 R1 可授权', provider: 'ragflow', owner: 'Donny', upd: '2026-08-30' }
];
/* AIR-008 Key 管理：KEY-1~4（一次性明文 + 动态鉴权 + 生命周期） */
const APIKEYS = [
  { id: 'KEY-0001', user: '何舟', role: 'R4 运营总监', hash: 'air-8f3d•••••••••••••2c9a', st: '启用', grants: 14, calls: 1284, qps: 12, last: '今天 14:32', wl: '未开启', expire: '2027-09-01' },
  { id: 'KEY-0002', user: '赵敏', role: 'R5 直播运营', hash: 'air-b6e7•••••••••••••4d21', st: '启用', grants: 6, calls: 967, qps: 6, last: '今天 11:05', wl: '未开启', expire: '2027-03-01' },
  { id: 'KEY-0003', user: '陈默', role: 'R9 数据分析师', hash: 'air-2a9c•••••••••••••8e54', st: '启用', grants: 5, calls: 412, qps: 4, last: '昨天 19:20', wl: 'IP 白名单 ×3', expire: '2026-12-31' },
  { id: 'KEY-0004', user: '孙倩', role: 'R6 短视频运营', hash: 'air-c4f1•••••••••••••7b08', st: '停用', grants: 4, calls: 236, qps: 0, last: '09-14 10:47', wl: '未开启', expire: '2027-06-30' },
  { id: 'KEY-0005', user: '王野', role: 'R10 外协人员', hash: 'air-e7d2•••••••••••••1f66', st: '已吊销', grants: 0, calls: 41, qps: 0, last: '09-10 16:22', wl: '未开启', expire: '—', reason: '钉钉离职事件联动吊销（BR-023）' }
];
/* AIR-012 调用审计 + RAGFlow 组件健康 */
const AIRLOGS = [
  { t: '今天 14:32', tool: 'experts.assemble', user: '何舟', key: 'KEY-0001', ok: true, ms: 86, auth: '实时鉴权通过' },
  { t: '今天 14:28', tool: 'knowledge.search', user: '何舟', key: 'KEY-0001', ok: true, ms: 1420, auth: '实时鉴权通过' },
  { t: '今天 13:55', tool: 'skills.get', user: '赵敏', key: 'KEY-0002', ok: true, ms: 64, auth: '实时鉴权通过' },
  { t: '今天 13:41', tool: 'knowledge.get', user: '陈默', key: 'KEY-0003', ok: false, ms: 3800, code: '5007', auth: '检索超时' },
  { t: '今天 11:05', tool: 'experts.assemble', user: '赵敏', key: 'KEY-0002', ok: true, ms: 92, auth: '实时鉴权通过' },
  { t: '今天 09:47', tool: 'knowledge.search', user: '孙倩', key: 'KEY-0004', ok: false, ms: 12, code: '401', auth: 'Key 已停用' },
  { t: '昨天 19:20', tool: 'knowledge.search', user: '陈默', key: 'KEY-0003', ok: true, ms: 1180, auth: '命中 IP 白名单' },
  { t: '昨天 15:03', tool: 'experts.assemble', user: '王野', key: 'KEY-0005', ok: false, ms: 8, code: '401', auth: '离职联动吊销' },
  { t: '昨天 10:12', tool: 'skills.list', user: '何舟', key: 'KEY-0001', ok: true, ms: 45, auth: '实时鉴权通过' },
  { t: '09-17 16:40', tool: 'knowledge.get', user: '何舟', key: 'KEY-0001', ok: false, ms: 2100, code: '5007', auth: 'RAGFlow 检索超时' }
];
/* RAGFlow 组件健康卡（D1：P0 自建，Docker Compose：ES/Infinity + Redis + MinIO） */
const RAGFLOW_HEALTH = [
  { c: 'ES/Infinity 检索引擎', st: '健康', detail: 'P95 1.2s · 向量索引 22.8万块' },
  { c: 'Redis 缓存', st: '健康', detail: '命中 87% · 动态鉴权缓存 60s' },
  { c: 'MinIO 对象存储', st: '健康', detail: '原始文档 872 份 · 38.6 GB' },
  { c: 'Embedding（bge-m3）', st: '健康', detail: 'GPU 与 ComfyUI 算力池共用' }
];
/* MCP 网关 6 工具（BR-034：网关不执行模型，experts.assemble 纯组装下发） */
const MCP_TOOLS = [
  { n: 'skills.list', d: '列出本人已授权技能（id/名称/版本/能力说明）' },
  { n: 'skills.get', d: '取技能详情（含提示词模板与输出契约）' },
  { n: 'experts.list', d: '列出本人已授权专家包' },
  { n: 'experts.assemble', d: '组装专家包（system_prompt + skills + kbs 检索片段）下发，不执行' },
  { n: 'knowledge.search', d: '按关键词检索授权知识库（机密级仅返回标题+100字摘要）' },
  { n: 'knowledge.get', d: '取知识片段详情（机密级默认拦截，BR-027）' }
];
function airSecretTag(s) {
  const m = { '公开': 'green', '内部': 'blue', '机密': 'orange', '绝密': 'red' };
  return tag('密级·' + s, m[s]);
}
/* AIR-001 技能新增：提交后进「审核中」（BR-025 强制审核，无直接发布路径） */
function skillAdd() {
  const body = frow([
    { k: 'name', label: '技能名称', type: 'text', req: true, ph: '如：商品卖点提炼' },
    { k: 'cat', label: '技能分类', type: 'select', req: true, opts: ['内容生产', '数据分析', '运营支持', '财务', '人事行政'] },
    { k: 'ver', label: '初始版本', type: 'text', val: 'v1.0', ph: '语义化版本号' },
    { k: 'owner', label: '维护责任人', type: 'select', req: true, opts: ['唐宁', '孙倩', '陈默', '周晴', '何舟'] },
    { k: 'desc', label: '能力说明', type: 'textarea', req: true, ph: '输入输出契约、适用场景、边界约束（选填补充）', wide: true },
    { k: 'prompt', label: '提示词模板', type: 'textarea', req: true, ph: 'Prompt 模板（支持 {变量} 占位符）', wide: true }
  ]);
  openDrawer('新增技能', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="skillAddSubmit()">提交审核</button>', '480px');
}
function skillAddSubmit() {
  if (!formValidate(['name', 'desc', 'prompt'])) return;
  SKILLS.unshift({ id: 'SKL-' + String(SKILLS.length + 1).padStart(4, '0'), name: $('#F_name').value, cat: $('#F_cat').value, v: $('#F_ver').value || 'v1.0', st: '审核中', audit: '待复核', owner: $('#F_owner').value, grants: 0, calls: 0, desc: $('#F_desc').value });
  formOk('SKL-' + String(SKILLS.length + 1).padStart(4, '0'), '技能已提交，进入强制审核流（BR-025）· 审核通过前不可授权', 'renderPage');
}
/* SKILL-3 技能授权抽屉：按人员/角色/部门三种授权类型（AirGrantType） */
function skillGrant(i) {
  const s = SKILLS[i];
  const body = '<div class="kv"><div><div class="k">技能名称</div><div class="v">' + s.name + '（' + s.v + '）</div></div>' +
    '<div><div class="k">当前授权人数</div><div class="v">' + s.grants + ' 人 · 累计调用 ' + s.calls + ' 次</div></div></div>' +
    '<div class="dsec">新增授权</div>' + frow([
      { k: 'gtype', label: '授权类型', type: 'select', opts: ['按人员', '按角色', '按部门'] },
      { k: 'gobj', label: '授权对象', type: 'text', req: true, ph: '人员姓名 / 角色 / 部门名称' },
      { k: 'gexpire', label: '授权有效期', type: 'date', req: true, val: '2027-03-31' }
    ]) +
    '<div class="hint">' + ic('warn', 13) + ' 授权即刻生效，经 MCP 网关实时鉴权（缓存 60s）；离职事件自动收回（BR-023）。</div>';
  openDrawer('技能授权 · ' + s.name, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="skillGrantOk(' + i + ')">确认授权</button>', '520px');
}
function skillGrantOk(i) {
  if (!formValidate(['gobj', 'gexpire'])) return;
  SKILLS[i].grants++;
  closeDrawer();
  toast('授权成功：' + $('#F_gobj').value + ' 可经 MCP 网关调用「' + SKILLS[i].name + '」（实时生效）', 'success');
}
/* SKILL-2 技能审核抽屉：通过→已发布 / 驳回→草稿 */
function skillAudit(i) {
  const s = SKILLS[i];
  const body = '<div class="kv"><div><div class="k">技能名称</div><div class="v">' + s.name + '（' + s.v + '）</div></div>' +
    '<div><div class="k">责任人</div><div class="v">' + s.owner + ' · 当前状态 ' + s.st + '</div></div></div>' +
    '<div class="dsec">能力说明</div><div style="font-size:13px;line-height:1.6">' + s.desc + '</div>' +
    '<div class="dsec">审核意见</div>' + frow([{ k: 'auditnote', label: '意见（驳回时必填）', type: 'textarea', ph: '说明通过与驳回原因', wide: true }]);
  openDrawer('技能审核 · ' + s.name, body,
    '<button class="btn btn-sec" onclick="skillAuditDeny(' + i + ')">驳回</button><button class="btn btn-pri" onclick="skillAuditOk(' + i + ')">审核通过</button>', '560px');
}
function skillAuditOk(i) {
  SKILLS[i].st = '已发布'; SKILLS[i].audit = '已通过';
  closeDrawer(); renderPage();
  toast('审核通过：「' + SKILLS[i].name + '」已发布，可授权分发（BR-025）', 'success');
}
function skillAuditDeny(i) {
  if (!formValidate(['auditnote'])) return;
  SKILLS[i].st = '草稿'; SKILLS[i].audit = '已驳回';
  closeDrawer(); renderPage();
  toast('已驳回：「' + SKILLS[i].name + '」退回草稿，须修改后重新提交审核', 'warn');
}
/* EXPERT-3 专家包组装预览（BR-034：纯组装，执行留客户端） */
function expertDetail(i) {
  const e = EXPERTS[i];
  const skNames = e.skills.map(function (sid) { const s = SKILLS.find(function (x) { return x.id === sid; }); return s ? s.id + ' ' + s.name : sid; });
  const kbNames = e.kbs.map(function (kid) { const k = KBS.find(function (x) { return x.id === kid; }); return k ? k.id + ' ' + k.name + '（' + k.secret + '）' : kid; });
  const body = '<div class="kv"><div><div class="k">适用场景</div><div class="v">' + e.scene + '</div></div>' +
    '<div><div class="k">版本 / 状态</div><div class="v">' + e.v + ' · ' + e.st + ' · 负责人 ' + e.owner + '</div></div></div>' +
    '<div class="dsec">System Prompt</div><div style="font-size:12.5px;line-height:1.7;padding:12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);font-family:ui-monospace,Menlo,Consolas,monospace">' + e.sysp + '</div>' +
    '<div class="dsec">挂载技能（skills）</div><div>' + (skNames.length ? skNames.map(function (n) { return '<span class="chip">' + n + '</span>'; }).join('') : '<span style="font-size:12px;color:var(--text2)">未挂载</span>') + '</div>' +
    '<div class="dsec">挂载知识库（kbs）</div><div>' + (kbNames.length ? kbNames.map(function (n) { return '<span class="chip pp">' + n + '</span>'; }).join('') : '<span style="font-size:12px;color:var(--text2)">未挂载</span>') + '</div>' +
    '<div class="hint">' + ic('warn', 13) + ' experts.assemble 仅下发组装包（prompt + 技能契约 + 知识检索片段），网关不执行模型（BR-034）。</div>';
  openDrawer('专家包组装预览 · ' + e.name, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="expertGrant(' + i + ')">授权管理</button>', '640px');
}
function expertGrant(i) {
  const e = EXPERTS[i];
  const body = '<div class="kv"><div><div class="k">专家包</div><div class="v">' + e.name + '（' + e.v + '）</div></div>' +
    '<div><div class="k">当前授权</div><div class="v">' + e.grants + ' 人 · 累计组装 ' + e.calls + ' 次</div></div></div>' +
    '<div class="dsec">新增授权</div>' + frow([
      { k: 'egobj', label: '授权对象', type: 'text', req: true, ph: '人员姓名 / 角色 / 部门名称' },
      { k: 'egexpire', label: '授权有效期', type: 'date', req: true, val: '2027-03-31' }
    ]) +
    '<div class="hint">授权含包内全部技能与知识库权限；机密级知识库成员自动降级为「仅摘要」。</div>';
  openDrawer('专家包授权 · ' + e.name, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="expertGrantOk(' + i + ')">确认授权</button>', '520px');
}
function expertGrantOk(i) {
  if (!formValidate(['egobj', 'egexpire'])) return;
  EXPERTS[i].grants++;
  closeDrawer();
  toast('授权成功：' + $('#F_egobj').value + ' 可组装「' + EXPERTS[i].name + '」（含包内技能与知识检索权限）', 'success');
}
/* KNOW-2 知识检索示意：机密级仅返回标题+100字摘要（BR-027） */
function kbSearch() {
  const kw = $('#F_kw').value;
  if (!formValidate(['kw'])) return;
  const hit = [
    { kb: 'KB-0002 平台规则库', title: '抖音直播违禁词清单（2026-09 更新）', brief: '…含「国家级」「第一」等绝对化用语共 214 条，虚拟健康类目限…', secret: '公开', full: true },
    { kb: 'KB-0001 商品知识库', title: '缓震跑鞋中底材料对比（EVA/TPU/Pebax）', brief: '…Pebax 回弹率 85% 但成本约为 EVA 的 6 倍，适用高端竞训定位…', secret: '内部', full: true },
    { kb: 'KB-0004 经营数据知识库', title: '8 月直播场次毛利分析', brief: '…8 月 38 场直播毛利率 22.4%，环比 +3.1pct；投流 ROI 低于阈值的场次…（仅返回标题与 100 字摘要，机密级不出库）', secret: '机密', full: false },
    { kb: 'KB-0006 股权与融资档案', title: 'A 轮融资条款清单', brief: '（检索命中但超出您的密级权限，BR-027 拦截 · 仅 R1 可见）', secret: '绝密', full: false }
  ];
  const body = '<div class="dsec">检索结果（关键词：' + kw + '）</div>' +
    hit.map(function (r) {
      return '<div class="mg-i" style="border-radius:8px' + (r.full ? '' : ';opacity:.72') + '"><span style="margin-top:2px;color:' + (r.secret === '绝密' ? 'var(--red)' : r.secret === '机密' ? 'var(--orange)' : 'var(--blue)') + '">' + ic(r.full ? 'doc' : 'warn', 16) + '</span>' +
        '<div style="flex:1;min-width:0"><div class="rowline" style="justify-content:space-between"><div class="mt">' + r.title + '</div>' + airSecretTag(r.secret) + '</div>' +
        '<div class="mc">' + r.brief + '</div><div class="md">' + r.kb + ' · RAGFlow 检索 · ' + (r.full ? '可获取全文' : 'BR-027 拦截') + '</div></div></div>';
    }).join('') +
    '<div class="hint">检索链路：MCP knowledge.search → 网关实时鉴权 → KnowledgeProvider（RAGFlow）→ 密级过滤后返回；绝密级知识不可经连接器检索。</div>';
  openDrawer('知识检索演示 · ' + kw, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '640px');
}
/* KB-0002 入库审批：审批通过后开始 DeepDoc 解析向量化 */
function kbAudit(i) {
  const k = KBS[i];
  const body = '<div class="kv"><div><div class="k">知识库名称</div><div class="v">' + k.name + '</div></div>' +
    '<div><div class="k">密级 / 责任人</div><div class="v">' + k.secret + ' · ' + k.owner + '</div></div></div>' +
    '<div class="dsec">待入库文档</div><div style="font-size:13px">共 ' + k.docs + ' 份文档（PDF/Word/Excel），审批通过后由 RAGFlow DeepDoc 解析并向量化（分块/表格/OCR）。</div>' +
    '<div class="hint">机密级及以上：连接器检索仅返回标题 + 100 字摘要，全文不出库（BR-027）。</div>';
  openDrawer('入库审批 · ' + k.name, body,
    '<button class="btn btn-sec" onclick="kbAuditDeny(' + i + ')">驳回</button><button class="btn btn-pri" onclick="kbAuditOk(' + i + ')">审批通过</button>', '560px');
}
function kbAuditOk(i) {
  KBS[i].st = '解析中'; KBS[i].chunks = '—';
  closeDrawer(); renderPage();
  toast('审批通过：' + KBS[i].name + ' 开始 DeepDoc 解析向量化，完成后自动发布', 'success');
}
function kbAuditDeny(i) {
  KBS[i].st = '草稿';
  closeDrawer(); renderPage();
  toast('已驳回：' + KBS[i].name + ' 退回草稿，请补充文档后重新提交', 'warn');
}
/* KEY-1 Key 生成：抽屉表单 → 一次性明文弹窗 + 客户端配置卡片复制（BR-020） */
function keyGen() {
  const body = frow([
    { k: 'kuser', label: 'Key 归属人员', type: 'select', req: true, opts: ['何舟', '赵敏', '孙倩', '李澈', '苏杳', '陈默', '周晴', '林岚'] },
    { k: 'kexpire', label: '有效期至', type: 'date', req: true, val: '2027-09-01' },
    { k: 'kqps', label: 'QPM 限额', type: 'num', val: 60, unit: '次/分钟', hint: '默认 60 次/分钟/人，超限返回 HTTP 429，BR-029' },
    { k: 'kwl', label: 'IP 白名单（P1 可选）', type: 'select', opts: ['不开启', '开启（逗号分隔 IP）'], hint: '总开关 air.key.ip_whitelist.enabled 默认关闭（D3）' }
  ]) +
    '<div class="cf-warn" style="background:rgba(255,149,0,.08);color:#c46a00">' + ic('warn', 14) + '明文 Key 仅在生成时展示一次，关闭后不可再次查看（服务端只存哈希）。</div>';
  openDrawer('生成 API Key', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="keyGenOk()">生成 Key</button>', '480px');
}
function keyGenOk() {
  if (!formValidate(['kuser', 'kexpire'])) return;
  const user = $('#F_kuser').value;
  const rnd = Array.from({ length: 4 }, function () { return Math.random().toString(16).slice(2, 6); }).join('');
  const plain = 'air-' + rnd + Array.from({ length: 12 }, function () { return Math.floor(Math.random() * 16).toString(16); }).join('');
  const cfg = JSON.stringify({ mcpServers: { 'ims-air': { url: 'https://ims.shenyu.example.com/ims/mcp', auth: 'Bearer ' + plain } } }, null, 2);
  const body = '<div style="padding:26px 8px 10px;text-align:center">' +
    '<div style="width:44px;height:44px;border-radius:50%;background:var(--blue-bg);color:var(--blue);display:flex;align-items:center;justify-content:center;margin:0 auto 12px">' + ic('spark', 22) + '</div>' +
    '<div style="font-size:16px;font-weight:600">Key 已生成 · 仅此一次展示</div>' +
    '<div class="mono" style="margin:14px 0 6px;padding:12px;border:1px dashed var(--line2);border-radius:8px;background:var(--bg);font-size:14px;color:var(--blue);font-weight:600;user-select:all">' + plain + '</div>' +
    '<div style="font-size:12px;color:var(--text2)">归属：' + user + ' · 动态鉴权（在职/授权实时校验，缓存 60s，BR-021）· 钉钉离职自动吊销（BR-023）</div></div>' +
    '<div class="dsec">客户端接入配置（复制即用）</div>' +
    '<pre class="mono" style="margin:0;padding:12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);font-size:11.5px;line-height:1.6;white-space:pre-wrap;user-select:all">' + cfg.replace(/</g, '&lt;') + '</pre>' +
    '<div class="hint">适用于 Claude Desktop / Cursor / Cherry Studio 等支持 MCP 的客户端：连接器内该人员只能看到自己权限内的技能、专家与知识。</div>';
  openDrawer('生成成功 · 请立即保存', body,
    '<button class="btn btn-sec" onclick="airCopy(\'' + plain + '\')">复制 Key</button><button class="btn btn-pri" onclick="airCopy(\'' + cfg.replace(/'/g, "\\'") + '\')">复制客户端配置</button>', '600px');
}
/* KEY-3 生命周期操作：停用/启用/吊销（危险操作二次确认） */
function keyToggle(i) {
  const k = APIKEYS[i];
  if (k.st === '启用') {
    confirmDlg('停用 Key', '确认停用 <b>' + k.user + '</b> 的 Key？停用期间所有 MCP 调用返回 401，恢复后即刻生效。', '确认停用', function () {
      k.st = '停用'; k.qps = 0; renderPage();
      toast('Key 已停用：' + k.hash.slice(0, 12) + '…（' + k.user + '）', 'warn');
    });
  } else if (k.st === '停用') {
    confirmDlg('启用 Key', '确认重新启用 <b>' + k.user + '</b> 的 Key？启用后按当前在职状态与授权实时鉴权。', '确认启用', function () {
      k.st = '启用'; k.qps = 6; renderPage();
      toast('Key 已启用：动态鉴权实时生效（' + k.user + '）', 'success');
    });
  } else {
    toast('该 Key 已吊销，不可恢复。如需接入请新生成 Key（BR-020）', 'warn');
  }
}
function keyRevoke(i) {
  const k = APIKEYS[i];
  confirmDlg('吊销 Key', '确认吊销 <b>' + k.user + '</b> 的 Key？吊销不可恢复，所有调用立即 401。离职联动吊销无需手工操作。', '确认吊销', function () {
    k.st = '已吊销'; k.qps = 0; k.expire = '—'; k.reason = '管理员手工吊销'; renderPage();
    toast('Key 已吊销：' + k.hash.slice(0, 12) + '…· 不可恢复', 'error');
  }, { danger: true, warn: '危险操作：该人员所有依赖此 Key 的外部工具将立即断连。' });
}
/* MCP-002 连接器配置卡片：端点 + 认证说明 + 6 工具 */
function mcpCfg() {
  const body = '<div class="dsec">网关端点</div>' +
    '<div class="mono" style="padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);font-size:12.5px">POST https://ims.shenyu.example.com/ims/mcp<span style="color:var(--text2)">  （Streamable HTTP + SSE 兼容）</span></div>' +
    '<div class="dsec">认证方式</div><div style="font-size:13px;line-height:1.7">请求头携带 <span class="mono" style="color:var(--blue)">Authorization: Bearer air-…</span>。网关实时校验：Key 状态 → 人员在职 → 资源授权（缓存 60s）；QPM 超限返回 <span class="mono">429</span>（默认 60 次/分钟/人），鉴权失败返回 <span class="mono">401</span>。</div>' +
    '<div class="dsec">可分发工具（6 个）</div>' +
    MCP_TOOLS.map(function (t) {
      return '<div class="mg-i" style="border-radius:8px"><span style="color:var(--blue);margin-top:2px">' + ic('spark', 16) + '</span><div style="flex:1;min-width:0"><div class="mt mono" style="font-size:12.5px">' + t.n + '</div><div class="mc" style="font-size:12px">' + t.d + '</div></div></div>';
    }).join('') +
    '<div class="hint">网关不执行模型与技能：experts.assemble 仅下发组装包，执行留在客户端（BR-034）；机密级知识仅标题+摘要（BR-027）。</div>';
  openDrawer('连接器（MCP）配置说明', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="keyGen()">生成新 Key</button>', '600px');
}
/* 复制：优先剪贴板 API，沙箱/降级走选中文本 */
function airCopy(txt) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(txt).then(function () { toast('已复制到剪贴板（' + txt.length + ' 字符）', 'success'); },
      function () { toast('复制失败，请手动选中文本复制', 'warn'); });
  } else toast('已复制到剪贴板（原型示意）', 'success');
}
/* RAGFlow 健康巡检（KB-1 运维） */
function ragflowCheck() {
  toast('RAGFlow 健康巡检完成：4/4 组件健康 · 检索 P95 1.2s · 无慢查询', 'success');
}

/* ===================== 20 AIR 页面（拆分为 5 个独立菜单页） ===================== */
/* AIR 统计卡（各页复用） */
function airStats() {
  const cnt = { s: SKILLS.length, e: EXPERTS.length, k: KBS.length, key: APIKEYS.filter(function (x) { return x.st === '启用'; }).length };
  const calls = SKILLS.reduce(function (s, x) { return s + x.calls; }, 0) + EXPERTS.reduce(function (s, x) { return s + x.calls; }, 0);
  return '<div class="g4">' +
    '<div class="card stat"><span class="l">技能 / 专家 / 知识库</span><div class="n" style="font-size:21px">' + cnt.s + ' / ' + cnt.e + ' / ' + cnt.k + '</div><div class="d">发布中 ' + (SKILLS.filter(function (x) { return x.st === '已发布'; }).length + EXPERTS.filter(function (x) { return x.st === '已发布'; }).length + KBS.filter(function (x) { return x.st === '已发布'; }).length) + ' 项</div></div>' +
    '<div class="card stat"><span class="l">启用中 Key</span><div class="n" style="color:var(--green)">' + cnt.key + '</div><div class="d">MCP 网关动态鉴权</div></div>' +
    '<div class="card stat"><span class="l">累计调用</span><div class="n">' + (calls + APIKEYS.reduce(function (s, x) { return s + x.calls; }, 0)).toLocaleString('zh-CN') + '</div><div class="d">今日 1,284 次 · P95 1.4s</div></div>' +
    '<div class="card stat"><span class="l">RAGFlow 底座</span><div class="n" style="color:var(--green)">健康</div><div class="d">自建 Docker · 22.8万向量块</div></div></div>';
}
/* 技能库页 */
PAGES.airSkill = function () {
  let h = pgHead('airSkill', '<button class="btn btn-pri" onclick="skillAdd()">' + ic('plus', 15) + '新增技能</button>');
  h += airStats();
  h += airSkillTab();
  return h;
};
/* 专家库页 */
PAGES.airExpert = function () {
  let h = pgHead('airExpert', '<button class="btn btn-sec" onclick="exportX(this,\'专家包台账\',EXPERTS.length)">导出</button>');
  h += airStats();
  h += airExpertTab();
  return h;
};
/* 知识库页（左侧知识目录树 + 右侧内容） */
PAGES.airKb = function () {
  let h = pgHead('airKb', '<button class="btn btn-sec" onclick="ragflowCheck()">底座巡检</button>');
  h += '<div style="display:grid;grid-template-columns:228px 1fr;gap:16px;align-items:start">' +
    airKbTree() +
    '<div style="min-width:0">' + airKbTab() + '</div></div>';
  return h;
};
/* 技能库列表（技能库页主体） */
function airSkillTab() {
  let h = catTabs('air2', ['内容生产', '数据分析', '运营支持', '财务'], SKILLS, function (s) { return s.cat; });
  const stc = { '已发布': 'green', '审核中': 'orange', '草稿': 'gray' };
  let rows = '';
  SKILLS.forEach(function (s) {
    const i = SKILLS.indexOf(s);
    rows += '<tr><td class="mono num" style="color:var(--blue);cursor:pointer" onclick="toast(\'技能详情 · ' + s.id + ' · 原型示意\',\'success\')">' + s.id + '</td>' +
      '<td style="font-weight:500">' + s.name + '</td><td>' + s.cat + '</td><td class="num">' + s.v + '</td>' +
      '<td>' + tag(s.st, stc[s.st]) + '</td>' +
      '<td>' + (s.audit === '已通过' ? tag(s.audit, 'green') : s.audit === '待复核' ? tag(s.audit, 'orange') : tag(s.audit, 'gray')) + '</td>' +
      '<td>' + s.owner + '</td><td class="num">' + s.grants + '</td><td class="num">' + s.calls + '</td>' +
      '<td>' + (s.st === '审核中' ? '<button class="btn btn-pri btn-sm" onclick="skillAudit(' + i + ')">审核</button> ' : '') +
      '<span class="btn btn-sec btn-sm" onclick="skillGrant(' + i + ')">授权</span></td></tr>';
  });
  h += qbar(qi('技能名称', 120) + qs(['全部状态', '已发布', '审核中', '草稿'], 90) + qi('责任人', 90), 'qSave(\'airSkill\')');
  h += tbl(['技能编号', '技能名称', '分类', '版本', '状态', '审核', '责任人', '授权人数', '累计调用', '操作'], rows);
  return h;
}
/* 专家库列表（方形头像卡片网格） */
function airExpertTab() {
  const stc = { '已发布': 'green', '草稿': 'gray' };
  const gr = ['linear-gradient(135deg,#0071e3,#5ac8fa)', 'linear-gradient(135deg,#af52d6,#c77dff)', 'linear-gradient(135deg,#34c759,#63e085)', 'linear-gradient(135deg,#ff9f0a,#ffb84d)', 'linear-gradient(135deg,#5e5ce6,#7a7aff)'];
  let h = qbar(qi('专家名称', 120) + qs(['全部状态', '已发布', '草稿'], 90) + qi('责任人', 90), 'qSave(\'airExpert\')');
  const list = qFilter(EXPERTS, function (e) { return [e.id, e.name, e.scene, e.owner]; }, function (e) { return e.st; });
  h += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px">';
  list.forEach(function (e) {
    const i = EXPERTS.indexOf(e);
    const draft = e.st !== '已发布';
    h += '<div class="card hov" onclick="expertDetail(' + i + ')">' +
      '<div class="rowline" style="margin-bottom:12px">' +
      '<span class="av" style="width:46px;height:46px;border-radius:12px;font-size:20px;background:' + gr[i % gr.length] + (draft ? ';filter:grayscale(.35);opacity:.8' : '') + '">' + e.name.slice(0, 1) + '</span>' +
      '<div style="min-width:0;flex:1"><b style="font-size:15px;display:block;line-height:1.3">' + e.name + '</b>' +
      '<span class="mono" style="font-size:11px;color:var(--text2)">' + e.id + ' · ' + e.v + '</span></div>' +
      tag(e.st, stc[e.st]) + '</div>' +
      '<div style="font-size:12px;color:var(--text2);line-height:1.5;margin-bottom:12px;min-height:36px">' + e.scene + '</div>' +
      '<div class="kv" style="grid-template-columns:1fr 1fr 1fr;gap:8px;margin:0 0 12px">' +
      '<div><div class="k">挂载技能</div><div class="v" style="font-size:14px">' + (e.skills.length || '—') + '</div></div>' +
      '<div><div class="k">挂载知识库</div><div class="v" style="font-size:14px">' + (e.kbs.length || '—') + '</div></div>' +
      '<div><div class="k">累计组装</div><div class="v" style="font-size:14px;color:var(--blue)">' + e.calls + '</div></div></div>' +
      '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">' +
      (e.skills.map(function (sid) { const s = SKILLS.find(function (x) { return x.id === sid; }); return '<span class="chip">' + (s ? s.name : sid) + '</span>'; }).join('') || '<span style="font-size:11.5px;color:var(--text2)">未挂载技能</span>') + '</div>' +
      '<div class="rowline" style="justify-content:space-between">' +
      '<span style="font-size:11.5px;color:var(--text2)">' + ic('people', 12) + ' 授权 ' + e.grants + ' 人 · 负责人 ' + e.owner + '</span>' +
      '<span class="rowline" style="gap:6px" onclick="event.stopPropagation()">' +
      '<span class="btn btn-sec btn-sm" onclick="expertDetail(' + i + ')">组装预览</span>' +
      '<span class="btn btn-pri btn-sm" onclick="expertGrant(' + i + ')">授权</span></span></div></div>';
  });
  h += '</div>';
  if (!list.length) h += '<div class="card">' + emptyState('未找到匹配的专家包', '尝试调整查询条件') + '</div>';
  return h;
}
/* Key 管理页 */
PAGES.airKey = function () {
  let h = pgHead('airKey', '<button class="btn btn-sec" onclick="mcpCfg()">连接器配置</button><button class="btn btn-pri" onclick="keyGen()">' + ic('plus', 15) + '生成 Key</button>');
  h += airStats();
  h += airKeyTab();
  return h;
};
PAGES.airCfg = function () {
  const cur = state.tab.airCfg || '模型连接';
  let h = pgHead('airCfg', cur === '模型连接'
    ? '<button class="btn btn-pri" onclick="airModelEdit(-1)">' + ic('plus', 15) + '新增模型</button>'
    : '<button class="btn btn-pri" onclick="airPromptEdit(-1)">' + ic('plus', 15) + '新增提示词</button>');
  h += airStats();
  h += '<div class="tabs">' + ['模型连接', '提示词'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'airCfg\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  if (cur === '提示词') {
    let rows = '';
    AIR_PROMPTS.forEach(function (p, i) {
      rows += '<tr><td>' + p.name + '</td><td>' + p.scene + '</td><td>' + (p.doc || '通用') + '</td><td class="mono">' + p.ver + '</td><td>' + tag(p.st, 'green') + '</td>' +
        '<td><span class="btn-txt btn" onclick="airPromptEdit(' + i + ')">编辑</span></td></tr>';
    });
    h += qbar(qi('模板名', 140) + qs(['全部场景', '内容生成', '短视频文案', 'AI排版语义'])) +
      tbl(['模板', '场景 dict_ai_scene', '文档类型', '版本', '状态', '操作'], rows) +
      '<div class="hint">原 OPS AI 提示词并入；保存 version+1。禁止与模型页维护两套 Key。</div>';
  } else {
    let rows = '';
    AIR_MODELS.forEach(function (m, i) {
      rows += '<tr><td>' + m.name + '</td><td>' + m.vendor + '</td><td class="mono">' + m.model + '</td><td>' + m.use + '</td><td>' + tag(m.conn, m.conn === 'CONNECTED' ? 'green' : 'orange') + '</td>' +
        '<td>' + (m.def ? tag('默认', 'blue') : '—') + '</td>' +
        '<td><span class="btn-txt btn" onclick="airModelEdit(' + i + ')">编辑</span> <span class="btn-txt btn" onclick="toast(\'测试连接 · ' + m.conn + '\',\'success\')">测试</span></td></tr>';
    });
    h += tbl(['名称', '供应商', 'model', '用途', '连接', '默认', '操作'], rows) +
      '<div class="hint">内容生成默认走 jingcai（环境变量，非本页明文 Key）；AI 排版语义须 CONNECTED Chat 模型。OPS 模型表扩展为 AIR 连接器。</div>';
  }
  return h;
};
const AIR_MODELS = [
  { name: 'jingcai.article', vendor: 'Football jingcai', model: 'FOOTBALL_AI_MODEL', use: '内容生成 / 润色', conn: 'CONNECTED', def: true },
  { name: '排版语义 Chat', vendor: 'OpenAI 兼容', model: 'qwen-plus', use: 'AI_TYPESET_SEMANTIC', conn: 'CONNECTED', def: false },
  { name: '备用直连 LLM', vendor: '自建网关', model: 'gpt-4o-mini', use: '降级直连', conn: 'DISABLED', def: false }
];
const AIR_PROMPTS = [
  { name: '竞彩方案正文', scene: '内容生成', doc: '正式方案', ver: 'v3', st: '启用' },
  { name: '短视频口播', scene: '短视频文案', doc: '短视频文案', ver: 'v2', st: '启用' },
  { name: '语义分段排版', scene: 'AI排版语义', doc: '—', ver: 'v1', st: '启用' }
];
function airModelEdit(i) {
  const m = i < 0 ? { name: '', vendor: 'OpenAI 兼容', model: '', use: 'AI_TYPESET_SEMANTIC' } : AIR_MODELS[i];
  openDrawer(i < 0 ? '新增模型连接' : '编辑模型 · ' + m.name, frow([
    { k: 'name', label: '名称', type: 'text', req: true, val: m.name },
    { k: 'vendor', label: '供应商', type: 'select', opts: ['Football jingcai', 'OpenAI 兼容', '自建网关'], val: m.vendor },
    { k: 'model', label: 'model', type: 'text', req: true, val: m.model },
    { k: 'use', label: '用途', type: 'select', opts: ['内容生成 / 润色', 'AI_TYPESET_SEMANTIC', '降级直连'], val: m.use },
    { k: 'key', label: 'API Key', type: 'text', ph: '已加密，留空不更新' }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'name\',\'model\']))return;toast(\'模型已保存（禁止两套 Key）\',\'success\');closeDrawer()">保存</button>', '520px');
}
function airPromptEdit(i) {
  const p = i < 0 ? { name: '', scene: '内容生成', doc: '正式方案', ver: 'v1' } : AIR_PROMPTS[i];
  openDrawer(i < 0 ? '新增提示词' : '编辑提示词 · ' + p.name, frow([
    { k: 'name', label: '模板名称', type: 'text', req: true, val: p.name },
    { k: 'scene', label: '场景', type: 'select', opts: ['内容生成', '短视频文案', '直播脚本', 'AI排版语义'], val: p.scene },
    { k: 'doc', label: '文档类型', type: 'select', opts: ['通用', '短视频文案', '正式方案', '预热前瞻'], val: p.doc },
    { k: 'body', label: '正文（{{变量}}）', type: 'textarea', req: true, ph: '你是神鱼体育运营助手……', wide: true }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'name\']))return;toast(\'提示词已保存，版本 +1\',\'success\');closeDrawer()">保存</button>', '560px');
}
/* 审计监控页 */
PAGES.airLog = function () {
  let h = pgHead('airLog', '<button class="btn btn-sec" onclick="exportX(this,\'MCP 调用日志\',AIRLOGS.length)">导出日志</button>');
  h += airStats();
  h += airLogTab();
  return h;
};
/* 知识目录树（知识库页左侧）：库 → 目录/分类，点选联动右侧表格过滤 */
const KB_TREE = [
  { name: '商品知识库', id: 'KB-0001', secret: '内部', cats: ['跑鞋系列', '健身器材', '运动服饰', '配件耗材'] },
  { name: '平台规则库', id: 'KB-0002', secret: '公开', cats: ['抖音规则', '快手规则', '视频号规则', '通用合规'] },
  { name: '内容 SOP 知识库', id: 'KB-0003', secret: '内部', cats: ['直播 SOP', '短视频 SOP', '复盘模板'] },
  { name: '经营数据知识库', id: 'KB-0004', secret: '机密', cats: ['场次毛利', '投流 ROI', '分成测算'] },
  { name: '主播分成合同库', id: 'KB-0005', secret: '机密', cats: ['合同正文', '结算单'] },
  { name: '股权与融资档案', id: 'KB-0006', secret: '绝密', cats: ['融资条款', '股东会决议'] }
];
function kbTreeGo(id) {
  if (!state.q.airKb) state.q.airKb = {};
  state.q.airKb.k0 = id;
  state.tab.airKbSel = id;
  renderPage();
  toast('已定位知识库：' + id + '（目录树联动过滤）', 'success');
}
function airKbTree() {
  const sel = state.tab.airKbSel || '';
  const sc = { '公开': 'green', '内部': 'blue', '机密': 'orange', '绝密': 'red' };
  let h = '<div class="card" style="padding:12px 10px;position:sticky;top:0"><div class="hd-row" style="margin-bottom:8px;padding:0 4px"><h3 style="font-size:14px">知识目录</h3>' +
    '<span style="font-size:11px;color:var(--text2)">' + KB_TREE.length + ' 库</span></div>';
  h += '<div style="font-size:12px">';
  KB_TREE.forEach(function (t) {
    const open = true;
    h += '<div style="padding:4px 6px;margin:2px 0;border-radius:6px;cursor:pointer' + (sel === t.id ? ';background:var(--blue-bg);color:var(--blue);font-weight:600' : '') + '" onclick="kbTreeGo(\'' + t.id + '\')">' +
      ic('db', 13) + ' <b style="font-size:12.5px">' + t.name + '</b> <span style="float:right">' + tag(t.secret, sc[t.secret]) + '</span></div>';
    t.cats.forEach(function (c) {
      h += '<div style="padding:3px 6px 3px 26px;font-size:11.5px;color:var(--text2);cursor:pointer;border-radius:6px" onmouseover="this.style.color=\'var(--blue)\'" onmouseout="this.style.color=\'var(--text2)\'" onclick="toast(\'目录 · ' + t.name + ' / ' + c + ' · 文档列表（原型示意）\',\'success\')">' + ic('doc', 11) + ' ' + c + '</div>';
    });
  });
  h += '</div><div class="hint" style="margin-top:10px;padding:0 4px">目录结构同步自 RAGFlow 数据集分组；点选库节点联动右侧表格过滤。</div></div>';
  return h;
}
/* 知识库页签（右侧内容：目录树选中联动过滤） */
function airKbTab() {
  const qr = state.q.airKb || {};
  let h = qbar(qi('库编号/名称', 130, qr.k0) + qi('关键词（演示检索）', 150) + qs(['全部密级', '公开', '内部', '机密', '绝密'], 90) + qs(['全部状态', '已发布', '解析中', '入库审批中', '草稿'], 110), 'qSave(\'airKb\')');
  const stc = { '已发布': 'green', '解析中': 'blue', '入库审批中': 'orange', '草稿': 'gray' };
  let rows = '';
  /* 目录树选中（kbTreeGo 写入 qr.k0）优先于 qGrab：qFilter 未命中回存值时回退树选中过滤 */
  let list = qFilter(KBS, function (k) { return [k.id, k.name, k.owner]; }, function (k) { return k.secret + '|' + k.st; });
  if (qr.k0 && list.length === KBS.length) {
    const kw = qr.k0.toLowerCase();
    list = KBS.filter(function (k) { return (k.id + ' ' + k.name).toLowerCase().indexOf(kw) >= 0; });
  }
  list.forEach(function (k) {
    const i = KBS.indexOf(k);
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + k.id + '</td>' +
      '<td style="font-weight:500">' + k.name + '</td>' +
      '<td>' + airSecretTag(k.secret) + (k.grantsLimit ? '<div style="font-size:11px;color:var(--text2);margin-top:3px">' + k.grantsLimit + '</div>' : '') + '</td>' +
      '<td class="num">' + k.docs + '</td>' +
      '<td class="num">' + (typeof k.chunks === 'number' ? k.chunks.toLocaleString('zh-CN') : k.chunks) + '</td>' +
      '<td>' + tag(k.st, stc[k.st]) + '</td>' +
      '<td><span class="chip">RAGFlow</span></td>' +
      '<td>' + k.owner + '</td><td class="num" style="font-size:12px">' + k.upd + '</td><td class="num">' + k.grants + '</td>' +
      '<td>' + (k.st === '入库审批中' ? '<button class="btn btn-pri btn-sm" onclick="kbAudit(' + i + ')">审批</button> ' : '') +
      '<span class="btn btn-sec btn-sm" onclick="kbSearchForm()">检索演示</span></td></tr>';
  });
  if (!list.length) rows = '';
  h += tbl(['库编号', '知识库名称', '密级', '文档数', '向量块', '状态', '底座', '责任人', '更新时间', '授权', '操作'], rows);
  h += '<div class="card" style="margin-top:16px"><div class="hd-row"><h3>RAGFlow 底座健康</h3><span class="btn btn-sec btn-sm" onclick="ragflowCheck()">立即巡检</span></div>' +
    '<div class="g4" style="margin-top:10px">' + RAGFLOW_HEALTH.map(function (r) {
      return '<div class="card stat" style="box-shadow:none;border:1px solid var(--line)"><span class="l">' + r.c + '</span><div class="n" style="color:var(--green);font-size:18px">' + r.st + '</div><div class="d">' + r.detail + '</div></div>';
    }).join('') + '</div>' +
    '<div class="hint">知识底座经 KnowledgeProvider 抽象接入（D1：P0 自建 RAGFlow），底座替换对 MCP 客户端无感；GPU 与 ComfyUI 算力池共用。</div></div>';
  return h;
}
/* Key 管理页签 */
function airKeyTab() {
  let h = '';
  let rows = '';
  APIKEYS.forEach(function (k) {
    const i = APIKEYS.indexOf(k);
    const stc = { '启用': 'green', '停用': 'orange', '已吊销': 'red' };
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + k.id + '</td>' +
      '<td style="font-weight:500">' + k.user + '</td><td style="font-size:12px;color:var(--text2)">' + k.role + '</td>' +
      '<td class="mono" style="color:var(--text2)">' + k.hash + '</td>' +
      '<td>' + tag(k.st, stc[k.st]) + '</td>' +
      '<td class="num">' + k.grants + '</td><td class="num">' + k.calls + '</td><td class="num">' + k.qps + '</td>' +
      '<td>' + (k.wl === '未开启' ? '<span style="font-size:12px;color:var(--text2)">未开启</span>' : '<span class="chip">' + k.wl + '</span>') + '</td>' +
      '<td class="num" style="font-size:12px">' + k.last + '</td><td class="num" style="font-size:12px">' + k.expire + '</td>' +
      '<td>' + (k.st === '已吊销' ? '<span style="font-size:11.5px;color:var(--text2)">' + k.reason + '</span>' :
        '<span class="btn btn-sec btn-sm" onclick="keyToggle(' + i + ')">' + (k.st === '启用' ? '停用' : '启用') + '</span> <span class="btn btn-sec btn-sm" style="color:var(--red)" onclick="keyRevoke(' + i + ')">吊销</span>') +
      ' <span class="btn btn-sec btn-sm" onclick="mcpCfg()">配置</span></td></tr>';
  });
  h += qbar(qi('人员姓名', 110) + qs(['全部状态', '启用', '停用', '已吊销'], 90) + qs(['全部白名单', '未开启', '已开启'], 90), 'qSave(\'airKey\')');
  h += tbl(['Key 编号', '归属人员', '角色', 'Key 哈希（掩码）', '状态', '授权资源', '累计调用', 'QPS 限额', 'IP 白名单', '最近调用', '有效期', '操作'], rows);
  h += '<div class="hint">' + ic('warn', 13) + ' 动态鉴权：每次调用实时校验人员在职状态与资源授权（缓存 60s，BR-021），钉钉离职事件即时吊销（BR-023）——Key-0005 即离职联动吊销示例。明文仅生成时展示一次（BR-020）。</div>';
  return h;
}
/* 审计监控页签 */
function airLogTab() {
  let h = '';
  let rows = '';
  AIRLOGS.forEach(function (l) {
    rows += '<tr><td class="num" style="font-size:12px">' + l.t + '</td>' +
      '<td class="mono" style="font-size:12px;color:var(--blue)">' + l.tool + '</td>' +
      '<td>' + l.user + '</td><td class="mono num" style="font-size:12px">' + l.key + '</td>' +
      '<td>' + (l.ok ? tag('成功', 'green') : tag('失败·' + l.code, 'red')) + '</td>' +
      '<td class="num">' + l.ms + ' ms</td><td style="font-size:12px;color:var(--text2)">' + l.auth + '</td></tr>';
  });
  h += qbar(qi('工具名/人员', 120) + qs(['全部结果', '成功', '失败'], 90) + qi('Key 编号', 100), 'qSave(\'airLog\')');
  h += tbl(['时间', 'MCP 工具', '调用人', 'Key', '结果', '耗时', '鉴权说明'], rows);
  h += '<div class="card" style="margin-top:16px"><div class="hd-row"><h3>用量统计（近 7 天）</h3></div><div class="bars" style="margin-top:12px">' +
    [412, 386, 295, 468, 521, 603, 1284].map(function (v) {
      const max = 1284;
      return '<div class="b" style="height:' + Math.round(v / max * 100) + '%" title="' + v + ' 次调用"></div>';
    }).join('') + '</div>' +
    '<div class="rowline" style="justify-content:space-between;margin-top:8px;font-size:11.5px;color:var(--text2)"><span>09-12</span><span>09-13</span><span>09-14</span><span>09-15</span><span>09-16</span><span>09-17</span><span>今天</span></div>' +
    '<div class="hint">审计日志全量落 ims_mcp_log（含鉴权上下文），失败调用重点跟踪 5007 检索超时与 401 鉴权失败（KEY-0004 停用 / KEY-0005 离职吊销样例）。</div></div>';
  return h;
}
/* 知识检索入口（知识库页 qbar → 检索演示抽屉） */
function kbSearchForm() {
  openDrawer('知识检索演示', frow([{ k: 'kw', label: '检索关键词', type: 'text', req: true, ph: '如：违禁词 / 中底材料 / 毛利率' }]) +
    '<div class="hint">演示 knowledge.search 链路：实时鉴权 → RAGFlow 向量检索 → 密级过滤。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="kbSearch()">检索</button>', '480px');
}
/* 兼容旧入口：PAGES.air 重定向到技能库 */
PAGES.air = function () { return PAGES.airSkill(); };

/* ===================== 报销表单（财务模块演示） ===================== */
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

/* ===================== 完整版并入：运营看板 / 系统 / 主数据 / IP组 / 账号财务 / 采集 / 监测 / 指标 ===================== */
PAGES.home = function () {
  const cards = [
    { l: '账号数', n: '1,286', d: '环比 <span class="pos">+12</span>', icon: 'user', go: 'acct' },
    { l: '今日作品', n: '84', d: '采集延迟已标注', icon: 'film', go: 'mon' },
    { l: '待办任务', n: String(TODOS.length), d: '含工作任务确认', icon: 'doc', go: 'workbench' },
    { l: '采集异常', n: '3', d: 'Cookie 失效可下钻', icon: 'warn', go: 'collect' }
  ].filter(function (c) { return canAccess(c.go) || c.go === 'workbench'; });
  let h = pgHead('home', qs(['全部 IP 组', '电竞一组', '体育二组'], 140) + qs(['近 7 天', '近 30 天'], 110) +
    '<button class="btn btn-pri" onclick="toast(\'仪表盘已刷新（IMS 库，不请求 OPS）\',\'success\')">刷新</button>');
  h += '<div class="g4">';
  cards.forEach(function (c) {
    h += '<div class="card hov stat" onclick="go(\'' + c.go + '\')"><div class="rowline" style="justify-content:space-between"><span class="l">' + c.l + '</span><span style="color:var(--blue)">' + ic(c.icon, 17) + '</span></div>' +
      '<div class="n">' + c.n + '</div><div class="d">' + c.d + '</div></div>';
  });
  h += '</div><div class="g2">';
  h += '<div class="card"><div class="hd-row"><h3>播放 / 互动</h3><span class="csub">按 IP 组权限 BR-305</span></div><div class="bars">' +
    [40, 55, 48, 72, 63, 80, 70].map(function (v) { return '<div class="b" style="height:' + v + '%"></div>'; }).join('') +
    '</div><div class="rowline" style="justify-content:space-between;margin-top:8px;font-size:11.5px;color:var(--text2)"><span>D-6</span><span>今天</span></div></div>';
  h += '<div class="card"><div class="hd-row"><h3>待办聚合</h3><span class="csub">不请求 OPS</span></div>';
  [{ t: '工作任务确认', d: 'CONTENT-104', g: 'contentWork' }, { t: '内容二审', d: 'CONTENT-005', g: 'contentReview' }, { t: '采集失败', d: 'COLLECT', g: 'collect' }, { t: '账号归还', d: 'ACCT-003', g: 'acct' }].forEach(function (x) {
    h += '<div class="mg-i" style="border-radius:8px" onclick="go(\'' + x.g + '\')"><span style="color:var(--blue)">' + ic('right', 16) + '</span><div><div class="mt">' + x.t + '</div><div class="md">' + x.d + '</div></div></div>';
  });
  h += '</div></div>';
  h += '<div class="sec">快捷入口</div><div style="display:grid;grid-template-columns:repeat(6,1fr);gap:9px">';
  [{ n: '登记工作任务', g: 'contentWork', i: 'film' }, { n: 'IP 组', g: 'ipg', i: 'people' }, { n: '账号领用', g: 'acct', i: 'user' }, { n: '采集任务', g: 'collectTask', i: 'search' }, { n: '账号 ROI', g: 'cost', i: 'yuan' }, { n: '指标管理', g: 'bi0Metric', i: 'chart' }].forEach(function (q) {
    if (!canAccess(q.g)) return;
    h += '<div class="card hov" style="padding:13px 8px;text-align:center;box-shadow:none;border:1px solid var(--line)" onclick="go(\'' + q.g + '\')">' +
      '<div style="color:var(--blue);margin-bottom:6px">' + ic(q.i, 19) + '</div><div style="font-size:12px;font-weight:500">' + q.n + '</div></div>';
  });
  h += '</div><div class="hint" style="margin-top:14px">' + ic('warn', 13) + ' 铁律：独立 IMS · Football 仅 HTTP WebAPI · 表只扩展 · 用户/账号主键迁入后不变。</div>';
  return h;
};

const SYS_USERS = [
  { id: '10086', name: '何舟', dept: '运营中心', role: 'ops:director', ding: '已绑定', st: '启用' },
  { id: '10087', name: '赵敏', dept: '直播组', role: 'ops:live', ding: '已绑定', st: '启用' },
  { id: '10088', name: '孙倩', dept: '内容中心', role: 'ops:editor', ding: '未绑定', st: '启用' },
  { id: '10001', name: 'Donny', dept: '信息中心', role: 'sys:admin', ding: '已绑定', st: '启用' }
];
const SYS_ROLES = [
  { code: 'sys:admin', name: '系统管理员', menus: 46, st: '启用' },
  { code: 'ops:director', name: '运营总监', menus: 38, st: '启用' },
  { code: 'ops:live', name: '直播运营', menus: 18, st: '启用' },
  { code: 'content_reviewer', name: '内容审核', menus: 8, st: '启用' }
];
const SYS_PARAMS = [
  { k: 'work.task.confirm.auto-ai-generate', d: '工作任务确认后是否自动 AI（竞彩）', v: 'false' },
  { k: 'content.review.levels', d: '内容审核级数', v: '2' },
  { k: 'content.review.level1.role', d: '一级审核角色', v: 'ip_group_leader' },
  { k: 'content.review.level2.role', d: '二级审核角色', v: 'ops_manager' },
  { k: 'air.key.ip_whitelist.enabled', d: 'AIR Key IP 白名单', v: 'true' },
  { k: 'dingtalk.sso.enabled', d: '钉钉 SSO', v: 'true' }
];
PAGES.sysUser = function () {
  let h = pgHead('sysUser', '<button class="btn btn-sec" onclick="exportX(this,\'用户\', SYS_USERS.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="sysUserEdit(-1)">' + ic('plus', 15) + '新建用户</button>');
  h += qbar(qi('用户名 / 手机', 150) + qs(['全部部门', '运营中心', '直播组', '内容中心', '信息中心']) + qs(['全部状态', '启用', '停用']));
  let rows = '';
  SYS_USERS.forEach(function (u, i) {
    rows += '<tr><td class="mono num">' + u.id + '</td><td style="font-weight:500">' + sens(u.name) + '</td><td>' + u.dept + '</td>' +
      '<td><span class="chip">' + u.role + '</span></td><td>' + tag(u.ding, u.ding === '已绑定' ? 'green' : 'orange') + '</td>' +
      '<td>' + tag(u.st, 'green') + '</td><td><span class="btn-txt btn" onclick="sysUserEdit(' + i + ')">编辑</span></td></tr>';
  });
  h += tbl(['用户 ID（迁入主键，只读）', '姓名', '部门', 'IMS 角色', '钉钉', '状态', '操作'], rows);
  h += '<div class="hint">' + ic('warn', 13) + ' SYS-001：左侧部门树 + GET /system/user/page · 禁止改主键 · 组织同步见 <span class="btn-txt btn" onclick="go(\'authOrg\')">权限管理→组织架构同步</span>。</div>';
  return h;
};
PAGES.sysRole = function () {
  let h = pgHead('sysRole', '<button class="btn btn-pri" onclick="toast(\'新建角色 · POST /system/role\',\'success\')">' + ic('plus', 15) + '新建角色</button>');
  let rows = '';
  SYS_ROLES.forEach(function (r) {
    rows += '<tr><td class="mono">' + r.code + '</td><td>' + r.name + '</td><td class="num">' + r.menus + '</td><td>' + tag(r.st, 'green') + '</td>' +
      '<td><span class="btn-txt btn" onclick="toast(\'PUT /system/role/{id}/menus · 兼容 ops:*\',\'success\')">菜单授权</span></td></tr>';
  });
  h += tbl(['角色编码', '名称', '菜单数', '状态', '操作'], rows);
  h += '<div class="hint">SYS-002 · 行级数据范围在 AUTH-003 岗位模板 dataScope + 角色并集。</div>';
  return h;
};
PAGES.sysMenu = function () {
  let h = pgHead('sysMenu', '<button class="btn btn-pri" onclick="sysMenuEdit(-1)">' + ic('plus', 15) + '新建菜单</button>');
  h += sysMenuTab();
  return h;
};
PAGES.sysDict = function () {
  let h = pgHead('sysDict', '<button class="btn btn-pri" onclick="sysDictTypeAdd()">' + ic('plus', 15) + '新建字典类型</button>');
  h += sysDictTab();
  return h;
};
PAGES.sysParam = function () {
  let h = pgHead('sysParam', '<button class="btn btn-pri" onclick="sysParamEdit(0)">修改参数</button>');
  let rows = '';
  SYS_PARAMS.forEach(function (p, i) {
    rows += '<tr><td class="mono">' + p.k + '</td><td>' + p.d + '</td><td>' + tag(p.v, p.v === 'true' ? 'green' : p.v === 'false' ? 'gray' : 'blue') + '</td>' +
      '<td><span class="btn-txt btn" onclick="sysParamEdit(' + i + ')">修改</span></td></tr>';
  });
  h += tbl(['key（不改名）', '说明', '当前值', '操作'], rows);
  h += '<div class="hint">SYS-005 · 含 jingcai / content.review.* / dingtalk / air.key.ip_whitelist.enabled。</div>';
  return h;
};
PAGES.sysLog = function () {
  let h = pgHead('sysLog', '<button class="btn btn-sec" onclick="exportX(this,\'日志\',2)">导出</button>');
  h += '<div class="tabs">' + ['操作日志', '登录日志'].map(function (t) {
    const cur = state.tab.sysLog || '操作日志';
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'sysLog\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  h += qbar(qi('操作人 / 路径', 160) + qs(['全部', '登录', '业务', '系统']));
  h += tbl(['时间', '用户', '动作', '路径'], '<tr><td class="num">2026-09-28 10:12</td><td>何舟</td><td>保存内容</td><td class="mono">POST /ims/content</td></tr><tr><td class="num">2026-09-28 09:01</td><td>Donny</td><td>登录 SSO</td><td class="mono">POST /ims/auth/sso</td></tr>');
  h += '<div class="hint">SYS-006 · GET /system/operate-log/page · GET /system/login-log/page · 仅 IMS 新操作。</div>';
  return h;
};
PAGES.sysNotify = function () {
  let h = pgHead('sysNotify', '<button class="btn btn-pri" onclick="toast(\'补发站内信 · 事件去重 SYS-007\',\'success\')">补发通知</button>');
  h += qbar(qs(['全部事件', 'TASK_PENDING', 'CONTENT_REVIEW_SUBMIT', 'WORK_HIT'], 180) + qs(['全部渠道', '站内', '钉钉']));
  let nr = '';
  SYS_NOTICES.forEach(function (n) {
    nr += '<tr><td class="mono">' + n.ev + '</td><td>' + n.biz + '</td><td>' + n.to + '</td><td>' + n.ch + '</td><td>' + tag(n.st, n.st === '已送达' ? 'green' : 'orange') + '</td><td class="num">' + n.t + '</td></tr>';
  });
  h += tbl(['事件类型', '业务键', '接收人', '渠道', '状态', '时间'], nr);
  h += '<div class="hint">SYS-007：站内信+钉钉；(tenant_id, event_type, biz_key) 去重，不重复推送。</div>';
  return h;
};
PAGES.sys = PAGES.sysUser;
function navLeafRoute(cid) {
  return CONTENT_ROUTE[cid] || AUTH_ROUTE[cid] || SYS_ROUTE[cid] || DAILY_ROUTE[cid] || REPORT_ROUTE[cid] || TRAIN_ROUTE[cid] || PERF_ROUTE[cid] || '/ims/' + cid;
}
const SYS_MENUS = (function () {
  const rows = [];
  let i = 1;
  GROUPS.forEach(function (g) {
    const pid = 'M' + String(i).padStart(3, '0');
    rows.push({ id: pid, parent: '—', name: g[0], path: '', perm: 'ims:nav:' + g[0], vis: '显示', sort: i * 10, typ: '目录' });
    i++;
    g[1].forEach(function (mid, j) {
      if (isNavSub(mid)) {
        const subPid = 'M' + String(i).padStart(3, '0');
        const pm = MODS[mid.id] || { name: mid.label, code: 'CONTENT' };
        rows.push({ id: subPid, parent: pid, name: mid.label, path: '', perm: 'ims:' + (pm.code || 'nav').toLowerCase() + ':nav', vis: '显示', sort: j + 1, typ: '目录', code: pm.code });
        i++;
        mid.children.forEach(function (cid, k) {
          const m = MODS[cid];
          rows.push({ id: 'M' + String(i).padStart(3, '0'), parent: subPid, name: m.name, path: navLeafRoute(cid), perm: 'ims:' + cid + ':list', vis: '显示', sort: k + 1, typ: '菜单', code: m.code });
          i++;
        });
        return;
      }
      const m = MODS[mid];
      rows.push({ id: 'M' + String(i).padStart(3, '0'), parent: pid, name: m.name, path: '/ims/' + mid, perm: 'ims:' + mid + ':list', vis: '显示', sort: j + 1, typ: '菜单', code: m.code });
      i++;
    });
  });
  return rows;
})();
const SYS_DICTS = [
  { type: 'dict_sop_node_type', name: 'SOP节点类型', n: 3, items: [['内容生成', 'CONTENT_GENERATION'], ['内容发布', 'CONTENT_PUBLISH'], ['普通节点', 'NORMAL']] },
  { type: 'dict_document_type', name: '文档类型', n: 5, items: [['短视频文案', 'SHORT_VIDEO_SCRIPT'], ['新号引流', 'NEW_ACCOUNT_TRAFFIC'], ['赛后复盘', 'POST_MATCH_REVIEW'], ['正式方案', 'OFFICIAL_PLAN'], ['预热前瞻', 'PREHEAT_PREVIEW']] },
  { type: 'dict_marketing_plan_type', name: '营销计划类型', n: 3, items: [['快手付费课程', 'KUAISHOU_PAID_COURSE'], ['公司平台付费', 'COMPANY_PAID'], ['免费公推', 'FREE_PUBLIC']] },
  { type: 'dict_position', name: '岗位', n: 7, items: [['运营', 'OPERATOR'], ['编辑', 'EDITOR'], ['主播', 'ANCHOR'], ['销售', 'SALES'], ['运营组长', 'OPS_LEADER'], ['运营官方号', 'OPS_OFFICIAL'], ['直播运营', 'LIVE_OPERATOR']] },
  { type: 'dict_platform_type', name: '平台类型', n: 7, items: [['微信公众号', 'WECHAT_OFFICIAL'], ['抖音', 'DOUYIN'], ['企业微信', 'WEWORK'], ['视频号', 'WECHAT_VIDEO'], ['快手', 'KUAISHOU'], ['小红书', 'XIAOHONGSHU'], ['全部', 'ALL']] },
  { type: 'dict_content_type', name: '内容类型', n: 3, items: [['文章', 'ARTICLE'], ['短视频', 'SHORT_VIDEO'], ['视频', 'VIDEO']] },
  { type: 'dict_ai_scene', name: 'AI应用场景', n: 4, items: [['内容生成', 'CONTENT_GEN'], ['短视频文案', 'SHORT_VIDEO'], ['直播脚本', 'LIVE_SCRIPT'], ['公众号文章', 'WECHAT_ARTICLE']] }
];
const SYS_NOTICES = [
  { ev: 'TASK_PENDING', biz: 'TK-881', to: '孙倩', ch: '站内+钉钉', st: '已送达', t: '今天 09:12' },
  { ev: 'CONTENT_REVIEW_SUBMIT', biz: '8821', to: '李澈', ch: '站内', st: '已送达', t: '今天 10:40' },
  { ev: 'WORK_HIT', biz: '作品#12', to: '何舟', ch: '钉钉', st: '去重跳过', t: '今天 11:02' }
];
function sysMenuTab() {
  let rows = '';
  SYS_MENUS.forEach(function (m, i) {
    const pad = m.parent === '—' ? '' : '<span class="indent"></span>';
    rows += '<tr><td class="mono">' + m.id + '</td><td>' + pad + (m.parent === '—' ? '<b>' + m.name + '</b>' : m.name) + '</td><td class="mono">' + (m.path || '—') + '</td>' +
      '<td class="mono">' + m.perm + '</td><td>' + tag(m.typ, m.typ === '目录' ? 'blue' : 'gray') + '</td><td>' + tag(m.vis, 'green') + '</td>' +
      '<td><span class="btn-txt btn" onclick="sysMenuEdit(' + i + ')">编辑</span></td></tr>';
  });
  return qbar(qi('菜单名 / 权限码', 160) + qs(['全部类型', '目录', '菜单'])) +
    tbl(['菜单 ID', '名称', '路由', '权限码', '类型', '可见', '操作'], rows) +
    '<div class="hint">SYS-003：IMS 菜单树由原运营菜单迁入；权限码兼容 ops:* 。GET /system/menu/tree</div>';
}
function sysMenuEdit(i) {
  const m = i < 0 ? { name: '', path: '/ims/', perm: 'ims:', typ: '菜单', vis: '显示' } : SYS_MENUS[i];
  openDrawer(i < 0 ? '新建菜单' : '编辑菜单 · ' + m.name, frow([
    { k: 'name', label: '名称', type: 'text', req: true, val: m.name },
    { k: 'path', label: '路由', type: 'text', val: m.path },
    { k: 'perm', label: '权限码', type: 'text', val: m.perm },
    { k: 'typ', label: '类型', type: 'select', opts: ['目录', '菜单', '按钮'], val: m.typ }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'name\']))return;toast(\'菜单已保存（SYS-003）\',\'success\');closeDrawer()">保存</button>', '480px');
}
function sysDictTab() {
  const open = state.tab.sysDict || SYS_DICTS[0].type;
  let left = '<div class="card" style="padding:10px"><div class="hd-row"><h3>字典类型</h3><span class="csub">' + SYS_DICTS.length + '</span></div>';
  SYS_DICTS.forEach(function (d) {
    left += '<div class="mi" style="cursor:pointer;padding:8px;border-radius:8px' + (open === d.type ? ';background:var(--blue-bg);color:var(--blue)' : '') + '" onclick="state.tab.sysDict=\'' + d.type + '\';renderPage()">' +
      '<b style="font-size:12.5px">' + d.name + '</b><div class="mono" style="font-size:11px">' + d.type + ' · ' + d.n + ' 值</div></div>';
  });
  left += '</div>';
  const d = SYS_DICTS.filter(function (x) { return x.type === open; })[0] || SYS_DICTS[0];
  let rows = '';
  d.items.forEach(function (it, i) {
    rows += '<tr><td class="num">' + (i + 1) + '</td><td>' + it[0] + '</td><td class="mono">' + it[1] + '</td><td>' + tag('启用', 'green') + '</td>' +
      '<td><span class="btn-txt btn" onclick="sysDictDataEdit(\'' + d.type + '\',' + i + ')">编辑</span></td></tr>';
  });
  const right = qbar(qi('标签 / 值', 140)) + tbl(['排序', '标签 dictLabel', '值 dictValue', '状态', '操作'], rows) +
    '<div class="hint">SYS-004：dictType 小写+下划线；dictValue 全大写+下划线；停用值不可删。GET /system/dict-type/list · /dict-data/list</div>';
  return '<div style="display:grid;grid-template-columns:280px 1fr;gap:14px">' + left + '<div>' + right + '</div></div>';
}
function sysDictTypeAdd() {
  openDrawer('新建字典类型', frow([
    { k: 'type', label: 'dictType', type: 'text', req: true, ph: 'dict_xxx' },
    { k: 'name', label: '名称', type: 'text', req: true }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'type\',\'name\']))return;toast(\'字典类型已创建\',\'success\');closeDrawer()">保存</button>', '480px');
}
function sysDictDataEdit(type, i) {
  const d = SYS_DICTS.filter(function (x) { return x.type === type; })[0];
  const it = d.items[i];
  openDrawer('编辑字典值 · ' + d.name, frow([
    { k: 'label', label: 'dictLabel', type: 'text', req: true, val: it[0] },
    { k: 'value', label: 'dictValue', type: 'text', req: true, val: it[1], hint: '全大写+下划线' },
    { k: 'sort', label: '排序', type: 'num', val: String(i + 1) }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="toast(\'字典值已保存（停用不可删）\',\'success\');closeDrawer()">保存</button>', '480px');
}
function sysUserEdit(i) {
  const u = i < 0 ? { id: '（提交后由迁入序列生成）', name: '', dept: '运营中心', role: 'ops:live' } : SYS_USERS[i];
  openDrawer(i < 0 ? '新建用户' : '编辑用户',
    '<div class="formrow">' + frow([
      { k: 'id', label: '用户 ID', type: 'text', val: u.id, disabled: true, hint: '主键不可改' },
      { k: 'ding', label: '钉钉 userId（映射）', type: 'text', ph: 'ding_xxx' },
      { k: 'name', label: '姓名', type: 'text', req: true, val: u.name },
      { k: 'dept', label: '部门', type: 'select', opts: ['运营中心', '直播组', '内容中心', '信息中心'], val: u.dept },
      { k: 'role', label: '角色', type: 'select', opts: ['sys:admin', 'ops:director', 'ops:live', 'ops:editor', 'content_reviewer'], val: u.role }
    ]) + '</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'name\']))return;formOk(\'' + (u.id || 'U-new') + '\',\'用户已保存（不回写 Football）\');toast(\'已保存\',\'success\')">保存</button>');
}
function sysParamEdit(i) {
  const p = SYS_PARAMS[i] || SYS_PARAMS[0];
  openDrawer('修改系统参数', frow([
    { k: 'k', label: 'key', type: 'text', val: p.k, disabled: true },
    { k: 'v', label: '值', type: 'select', opts: ['true', 'false', '2', '1'], val: p.v }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="toast(\'参数已更新（key 未改名）\',\'success\');closeDrawer()">保存</button>', '480px');
}

const MASTER_CO = [{ id: 'c01', name: '神鱼互娱', cap: '12 / 20', st: '启用' }, { id: 'c02', name: '神鱼传媒', cap: '4 / 10', st: '启用' }];
const MASTER_PS = [{ id: '9001', name: '苏杳', idn: '320***********1234', agent: '—', st: '在职' }, { id: '9002', name: '赵敏', idn: '310***********5566', agent: '中介A', st: '在职' }];
const MASTER_PH = [{ id: 'p01', model: 'iPhone 15', person: '苏杳', st: '在用' }, { id: 'p02', model: 'Android 采集机', person: '赵敏', st: '在用' }];
const MASTER_SIM = [{ id: 's01', no: '138****5678', person: '苏杳', fee: 128 }, { id: 's02', no: '139****2211', person: '赵敏', fee: 59 }];
PAGES.master = function () {
  const cur = state.tab.master || '实名人';
  const tabs = ['公司', '实名人', '手机', '手机卡', '平台账号', '个人账号'];
  let h = pgHead('master', '<button class="btn btn-sec" onclick="exportX(this,\'主数据\',8)">导出</button><button class="btn btn-pri" onclick="masterAdd()">' + ic('plus', 15) + '新建</button>');
  h += '<div class="tabs">' + tabs.map(function (t) { return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'master\',\'' + t + '\')">' + t + '</div>'; }).join('') + '</div>';
  if (cur === '公司') {
    let rows = '';
    MASTER_CO.forEach(function (r) {
      rows += '<tr><td class="mono">' + r.id + '</td><td style="font-weight:500">' + r.name + '</td><td class="num">' + r.cap + '</td><td>' + tag(r.st, 'green') + '</td><td><span class="btn-txt btn" onclick="toast(\'编辑公司 · 公众号容量\',\'success\')">编辑</span></td></tr>';
    });
    h += tbl(['公司 ID', '名称', '公众号容量', '状态', '操作'], rows);
  } else if (cur === '实名人') {
    h += qbar(qi('姓名', 120) + qs(['全部状态', '在职', '离职']));
    let rows = '';
    MASTER_PS.forEach(function (r) {
      rows += '<tr><td class="mono">' + r.id + '</td><td>' + sens(r.name) + '</td><td class="mono">' + r.idn + '</td><td>' + r.agent + '</td><td>' + tag(r.st, 'green') + '</td>' +
        '<td><span class="btn-txt btn" onclick="toast(\'实名人档案（证件 AES）\',\'success\')">编辑</span></td></tr>';
    });
    h += tbl(['实名人 ID', '姓名', '证件号', '中介人', '状态', '操作'], rows);
  } else if (cur === '手机') {
    let rows = '';
    MASTER_PH.forEach(function (r) {
      rows += '<tr><td class="mono">' + r.id + '</td><td>' + r.model + '</td><td>' + r.person + '</td><td>' + tag(r.st, 'green') + '</td></tr>';
    });
    h += tbl(['设备 ID', '型号', '绑定实名人', '状态'], rows);
  } else if (cur === '手机卡') {
    let rows = '';
    MASTER_SIM.forEach(function (r) {
      rows += '<tr><td class="mono">' + r.id + '</td><td>' + maskPhone(r.no.replace(/\*/g, '1')) + '</td><td>' + r.person + '</td><td class="num">' + fmtMoney(r.fee) + '</td></tr>';
    });
    h += tbl(['卡 ID', '号码', '实名人', '月租'], rows);
  } else if (cur === '平台账号') {
    h += qbar(qi('账号 / 昵称', 140) + qs(['全部平台', '抖音', '快手', '视频号']));
    h += tbl(['账号 ID', '平台', '昵称', 'IP 组', '实名人', '状态', '操作'],
      '<tr><td class="mono">88001</td><td>抖音</td><td style="font-weight:500">神鱼电竞A</td><td>电竞一组</td><td>' + sens('苏杳') + '</td><td>' + tag('在用', 'green') + '</td>' +
      '<td><span class="btn-txt btn" onclick="masterAcctAdd()">编辑</span> <span class="btn-txt btn" onclick="acctApply()">领用</span> <span class="btn-txt btn" onclick="go(\'caDouyin\')">抖音账号</span></td></tr>');
    h += '<div class="hint">与账号管理同一套登记，禁止两套台账。创建必须走公司/实名人/手机/IP 组选择器（1501/1502）。</div>';
  } else {
    h += tbl(['账号 ID', '类型', '绑定', '状态'], '<tr><td class="mono">wx01</td><td>企微</td><td>苏杳</td><td>' + tag('正常', 'green') + '</td></tr>');
  }
  return h;
};
function masterAdd() {
  const cur = state.tab.master || '实名人';
  if (cur === '平台账号') { masterAcctAdd(); return; }
  toast('新建「' + cur + '」抽屉 · 强关联字段仅选择器', 'success');
}
function masterAcctAdd() {
  openDrawer('平台账号（MASTER-005）', frow([
    { k: 'plat', label: '平台', type: 'select', req: true, opts: ['请选择', '抖音', '快手', '视频号', '小红书'] },
    { k: 'nick', label: '昵称', type: 'text', req: true, ph: '账号昵称' },
    { k: 'ipg', label: 'IP 组', type: 'select', req: true, opts: ['请选择 IP 组', '电竞一组', '体育二组'] },
    { k: 'co', label: '公司', type: 'select', req: true, opts: ['请选择公司', '神鱼互娱', '神鱼传媒'] },
    { k: 'ps', label: '实名人', type: 'select', req: true, opts: ['请选择实名人', '苏杳', '赵敏'] },
    { k: 'ph', label: '手机 / 卡', type: 'select', opts: ['请选择', 'iPhone 15 / 138****5678'] }
  ]) + '<div class="hint">禁止手输关联 ID。主键保持迁入前账号 id。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'nick\']))return;formOk(\'88002\',\'账号已创建，可在账号管理领用\');toast(\'已创建\',\'success\')">提交</button>');
}

const IPG_FOREST = [
  {
    id: 'g_sy', name: '神鱼体育', typ: 'BIG', leader: '何舟', level: '', status: '启用', sort: 0, remark: '—',
    created: '2026-06-01 10:00:00', updated: '2026-08-20 14:22:00', mc: 3, ac: 0, anc: 3,
    children: [
      { id: 'g_zw', name: '张武（测试）', typ: 'SMALL', leader: '张武', level: 'C级', status: '启用', sort: 0, remark: '—', created: '2026-08-27 18:31:44', updated: '2026-08-27 18:31:44', mc: 0, ac: 0, anc: 1 },
      { id: 'g_dy', name: '电竞一组', typ: 'SMALL', leader: '苏杳', level: 'A级', status: '启用', sort: 1, remark: '主站电竞垂类', created: '2026-07-02 11:20:00', updated: '2026-09-10 09:15:00', mc: 2, ac: 3, anc: 1 },
      { id: 'g_ty', name: '体育二组', typ: 'SMALL', leader: '赵敏', level: 'B级', status: '启用', sort: 2, remark: '—', created: '2026-07-15 16:00:00', updated: '2026-09-01 08:40:00', mc: 1, ac: 2, anc: 1 }
    ]
  },
  {
    id: 'g_seed', name: 'SEED-运营大组', typ: 'BIG', leader: 'Donny', level: 'S级', status: '启用', sort: 10, remark: '种子数据验收组',
    created: '2026-05-20 09:00:00', updated: '2026-09-28 12:00:00', mc: 3, ac: 4, anc: 2,
    children: [
      { id: 'g_s1', name: 'SEED-小组甲', typ: 'SMALL', leader: '孙倩', level: 'B级', status: '启用', sort: 0, remark: '—', created: '2026-05-21 10:00:00', updated: '2026-09-20 10:00:00', mc: 2, ac: 2, anc: 1 },
      { id: 'g_s2', name: 'SEED-小组乙', typ: 'SMALL', leader: '李澈', level: 'C级', status: '停用', sort: 1, remark: '演示停用态', created: '2026-05-21 10:05:00', updated: '2026-09-18 17:00:00', mc: 1, ac: 2, anc: 1 }
    ]
  }
];
const IPG_MEMBERS = {
  g_zw: [],
  g_dy: [
    { name: '苏杳', pos: '运营组长', rel: '主职', lead: true },
    { name: '赵敏', pos: '直播运营', rel: '主职', lead: false },
    { name: '孙倩', pos: '编辑', rel: '兼职', lead: false }
  ],
  g_ty: [{ name: '赵敏', pos: '运营组长', rel: '主职', lead: true }],
  g_sy: [{ name: '何舟', pos: '运营总监', rel: '主职', lead: true }],
  g_s1: [{ name: '孙倩', pos: '编辑', rel: '主职', lead: true }, { name: '王野', pos: '运营', rel: '主职', lead: false }],
  g_s2: [{ name: '李澈', pos: '运营', rel: '主职', lead: true }]
};
const IPG_ANCHORS = {
  g_zw: [{ id: 'au_zw', name: '张武', typ: '短视频', acct: '88021 张武说球', user: '张武' }],
  g_dy: [{ id: 'au_sy', name: '苏杳', typ: '官方号', acct: '88001 神鱼电竞A', user: '苏杳' }],
  g_ty: [{ id: 'au_zm', name: '赵敏', typ: '直播', acct: '88014 体育号B', user: '赵敏' }],
  g_s1: [{ id: 'au_sq', name: '孙倩', typ: '短视频', acct: '88033 神鱼健身', user: '孙倩' }]
};
const IPG_ACCOUNTS = {
  g_dy: [{ nick: '神鱼电竞A', plat: '抖音', id: '88001' }, { nick: '神鱼电竞B', plat: '快手', id: '88002' }, { nick: '神鱼官方号', plat: '视频号', id: '88003' }],
  g_ty: [{ nick: '体育号B', plat: '快手', id: '88014' }, { nick: '跑步日记', plat: '小红书', id: '88019' }]
};
const IPG_STATS = {
  g_zw: { fans: '1.2w', works: 6, inner: 2, roi: '—', cost: 0, rev: 0 },
  g_dy: { fans: '186.2w', works: 412, inner: 38, roi: '1.46', cost: 42000, rev: 61200 },
  g_ty: { fans: '42.8w', works: 128, inner: 15, roi: '1.32', cost: 18000, rev: 23760 },
  g_sy: { fans: '230.2w', works: 546, inner: 55, roi: '1.44', cost: 60000, rev: 86400 },
  g_s1: { fans: '8.6w', works: 44, inner: 8, roi: '1.18', cost: 9200, rev: 10856 },
  g_s2: { fans: '3.1w', works: 19, inner: 3, roi: '0.92', cost: 5600, rev: 5152 }
};
if (!state.ipgOpen) state.ipgOpen = { g_sy: true, g_seed: false };
function ipgEach(fn) {
  IPG_FOREST.forEach(function (big) {
    fn(big, null);
    (big.children || []).forEach(function (sm) { fn(sm, big); });
  });
}
function ipgFind(id) {
  let found = null;
  ipgEach(function (n) { if (n.id === id) found = n; });
  return found;
}
function ipgParentName(n) {
  if (!n) return '—';
  let p = '—';
  ipgEach(function (node, par) { if (node.id === n.id && par) p = par.name; });
  return p;
}
function ipgTypLabel(typ) { return typ === 'BIG' ? '大组' : '小组'; }
function ipgSelect(id) { state.ipgSel = id; renderPage(); }
function ipgDetailTab(t) { state.tab.ipgDetail = t; renderPage(); }
function ipgToggleExpand(id, ev) {
  if (ev) ev.stopPropagation();
  state.ipgOpen[id] = !state.ipgOpen[id];
  renderPage();
}
function ipgTreeFilter(kw) {
  state.q.ipgTree = kw;
  renderPage();
}
function ipgRenderTree() {
  const kw = (state.q.ipgTree || '').trim().toLowerCase();
  const sel = state.ipgSel || 'g_zw';
  let html = '';
  IPG_FOREST.forEach(function (big) {
    const bigMatch = !kw || big.name.toLowerCase().indexOf(kw) >= 0;
    const childMatch = (big.children || []).some(function (c) { return c.name.toLowerCase().indexOf(kw) >= 0; });
    if (kw && !bigMatch && !childMatch) return;
    const open = kw ? true : !!state.ipgOpen[big.id];
    html += '<div class="ipg-node' + (sel === big.id ? ' on' : '') + '" onclick="ipgSelect(\'' + big.id + '\')">' +
      '<span class="exp' + ((big.children || []).length ? '' : ' ph') + '" onclick="ipgToggleExpand(\'' + big.id + '\',event)">' + ic(open ? 'chev' : 'right', 14) + '</span>' +
      '<span class="nm"><span style="margin-right:4px;color:var(--text2)">' + ic('box', 14) + '</span>' + big.name +
      ' <span class="cnt">(' + big.mc + '/' + big.ac + '/' + big.anc + ')</span>' +
      (big.level ? ' <span class="lv">' + big.level + '</span>' : '') + '</span></div>';
    if (open) {
      (big.children || []).forEach(function (sm) {
        if (kw && sm.name.toLowerCase().indexOf(kw) < 0 && big.name.toLowerCase().indexOf(kw) < 0) return;
        html += '<div class="ipg-node child' + (sel === sm.id ? ' on' : '') + '" onclick="ipgSelect(\'' + sm.id + '\')">' +
          '<span class="exp ph"></span><span class="nm">' + sm.name +
          ' <span class="cnt">(' + sm.mc + '/' + sm.ac + '/' + sm.anc + ')</span>' +
          (sm.level ? ' <span class="lv">' + sm.level + '</span>' : '') + '</span></div>';
      });
    }
  });
  return html || '<div class="empty" style="padding:24px"><div class="es">无匹配组名</div></div>';
}
function ipgInfoRow(lbl, val) {
  return '<tr><td class="lbl">' + lbl + '</td><td>' + val + '</td></tr>';
}
function ipgDetailPane(n) {
  const tab = state.tab.ipgDetail || '基本信息';
  const tabs = ['基本信息', '成员管理', '关联作者', '统计'];
  let pane = '';
  if (tab === '成员管理') {
    const mem = IPG_MEMBERS[n.id] || [];
    let rows = mem.map(function (m, i) {
      return '<tr><td>' + sens(m.name) + (m.lead ? ' ' + tag('组长', 'blue') : '') + '</td><td>' + m.pos + '</td><td>' + tag(m.rel, m.rel === '主职' ? 'blue' : 'gray') + '</td>' +
        '<td><span class="btn-txt btn" onclick="ipgMemberEdit(\'' + n.id + '\',' + i + ')">编辑</span> <span class="btn-txt btn" onclick="ipgMemberRemove(\'' + n.id + '\',' + i + ')">移除</span></td></tr>';
    }).join('');
    if (!rows) rows = '<tr><td colspan="4" style="color:var(--text2);text-align:center;padding:20px">暂无成员 · 点击「添加成员」</td></tr>';
    pane = '<div class="hd-row" style="margin-top:12px"><h3 style="font-size:15px">成员与岗位</h3><button class="btn btn-pri btn-sm" onclick="ipgMemberAdd(\'' + n.id + '\')">' + ic('plus', 14) + '添加成员</button></div>' +
      tbl(['成员', '岗位 dict_position', '主/兼', '操作'], rows) +
      '<div class="hint">PUT /ip-group/{id}/members · userId 须 Football 可存 id（ADR-056）。</div>';
  } else if (tab === '关联作者') {
    const anc = IPG_ANCHORS[n.id] || [];
    let rows = anc.map(function (a, i) {
      return '<tr><td class="mono">' + a.id + '</td><td style="font-weight:500">' + sens(a.name) + '</td><td>' + a.typ + '</td><td>' + a.acct + '</td><td>' + sens(a.user) + '</td>' +
        '<td><span class="btn-txt btn" onclick="ipgAnchorRemove(\'' + n.id + '\',' + i + ')">解除</span></td></tr>';
    }).join('');
    if (!rows) rows = '<tr><td colspan="6" style="color:var(--text2);text-align:center;padding:20px">暂无关联作者</td></tr>';
    pane = '<div class="hd-row" style="margin-top:12px"><h3 style="font-size:15px">关联作者</h3><button class="btn btn-pri btn-sm" onclick="ipgAnchorAdd(\'' + n.id + '\')">' + ic('plus', 14) + '添加作者</button></div>' +
      tbl(['作者 ID', '作者名', '类型', '主推号', '绑定用户', '操作'], rows) +
      '<div class="hint">POST /ip-group/{id}/anchors · 作者下拉（author_user.id），非 UserSelect（ADR-051）。工作任务登记须在此绑定作者。</div>';
  } else if (tab === '统计') {
    const st = IPG_STATS[n.id] || { fans: '—', works: '—', inner: '—', roi: '—', cost: 0, rev: 0 };
    pane = '<div class="g4" style="margin-top:14px">' +
      '<div class="card stat"><span class="l">粉丝</span><div class="n">' + st.fans + '</div></div>' +
      '<div class="card stat"><span class="l">作品</span><div class="n">' + st.works + '</div></div>' +
      '<div class="card stat"><span class="l">内部内容</span><div class="n">' + st.inner + '</div></div>' +
      '<div class="card stat"><span class="l">ROI</span><div class="n">' + st.roi + '</div></div></div>' +
      '<table class="ipg-info-grid"><tbody>' +
      ipgInfoRow('账号数', String(n.ac)) + ipgInfoRow('成员数', String(n.mc)) +
      ipgInfoRow('成本（期间）', fmtMoney(st.cost)) + ipgInfoRow('营收（WebAPI）', fmtMoney(st.rev)) +
      '</tbody></table>' +
      '<div class="rowline" style="margin-top:14px;flex-wrap:wrap;gap:8px">' +
      '<button class="btn btn-sec btn-sm" onclick="toast(\'跳转账号分析（P-M1-003）\',\'success\');">账号分析</button>' +
      '<button class="btn btn-sec btn-sm" onclick="toast(\'跳转作品分析（P-M1-005）\',\'success\');">作品分析</button>' +
      '<button class="btn btn-sec btn-sm" onclick="go(\'cost\');setTab(\'cost\',\'账号 ROI\')">IP 组 ROI</button></div>' +
      '<div class="hint">GET /ip-group/{id}/stats · 大组指标 = 子组求和（BR-M1-004）。</div>';
  } else {
    pane = '<table class="ipg-info-grid"><tbody>' +
      ipgInfoRow('组名', n.name) + ipgInfoRow('组类型', tag(ipgTypLabel(n.typ), n.typ === 'BIG' ? 'blue' : 'cyan')) +
      ipgInfoRow('上级组', ipgParentName(n)) + ipgInfoRow('组长', sens(n.leader || '—')) +
      ipgInfoRow('等级', n.level ? tag(n.level, 'blue') : tag('未分级', 'gray')) + ipgInfoRow('状态', tag(n.status, n.status === '启用' ? 'green' : 'gray')) +
      ipgInfoRow('排序', String(n.sort)) + ipgInfoRow('备注', n.remark || '—') +
      ipgInfoRow('创建时间', n.created) + ipgInfoRow('更新时间', n.updated) +
      '</tbody></table>';
    if (n.typ === 'SMALL' && (IPG_ACCOUNTS[n.id] || []).length) {
      pane += '<div class="dsec">已绑账号（OPS UX 独立 Tab「账号」；原型暂展示摘要）</div><div class="tbl-wrap"><table><thead><tr><th>账号</th><th>平台</th><th>操作</th></tr></thead><tbody>';
      (IPG_ACCOUNTS[n.id] || []).forEach(function (a) {
        pane += '<tr><td>' + a.nick + '</td><td>' + a.plat + '</td><td><span class="btn-txt btn" onclick="ipgAccountBind(\'' + n.id + '\')">调整</span></td></tr>';
      });
      pane += '</tbody></table></div>';
    }
  }
  return '<div class="tabs">' + tabs.map(function (t) {
    return '<div class="tab' + (tab === t ? ' on' : '') + '" onclick="ipgDetailTab(\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>' + pane;
}
PAGES.ipg = function () {
  if (!state.ipgSel) state.ipgSel = 'g_zw';
  if (!state.tab.ipgDetail) state.tab.ipgDetail = '基本信息';
  let h = pgHead('ipg', '<button class="btn btn-sec" onclick="exportX(this,\'IP组树\',6)">导出</button>');
  h += '<div class="ipg-split">';
  h += '<div class="ipg-tree-panel card"><div class="ipg-tree-hd"><span>IP 组结构</span><span class="btn-txt btn" onclick="ipgEdit(null,\'BIG\')">' + ic('plus', 14) + '新建大组</span></div>';
  h += '<div class="ipg-tree-search"><div class="ico">' + ic('search', 15) + '<input placeholder="搜索组名" value="' + (state.q.ipgTree || '') + '" oninput="ipgTreeFilter(this.value)"></div></div>';
  h += '<div class="ipg-tree-body">' + ipgRenderTree() + '</div></div>';
  const n = ipgFind(state.ipgSel);
  h += '<div class="ipg-detail-panel card">';
  if (!n) {
    h += '<div class="ipg-empty-detail">请从左侧选择 IP 组</div>';
  } else {
    const typTag = tag(ipgTypLabel(n.typ), n.typ === 'BIG' ? 'blue' : 'cyan');
    const canChild = n.typ === 'BIG';
    h += '<div class="ipg-detail-hd"><div class="rowline" style="justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">' +
      '<div><div class="rowline" style="gap:8px;flex-wrap:wrap">' + typTag + (n.level ? tag(n.level, 'blue') : '') + '</div>' +
      '<h2>' + n.name + '</h2>' +
      '<div class="ipg-detail-meta"><span>组长：' + sens(n.leader || '—') + '</span><span>上级：' + ipgParentName(n) + '</span><span>创建于：' + n.created + '</span></div></div>' +
      '<div class="acts">' +
      (canChild ? '<button class="btn btn-sec btn-sm" onclick="ipgEdit(\'' + n.id + '\',\'SMALL\')">' + ic('plus', 14) + '新建小组</button>' : '') +
      '<button class="btn btn-sec btn-sm" onclick="ipgEdit(\'' + n.id + '\',\'edit\')">编辑</button>' +
      '<button class="btn btn-sm" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="ipgToggleStatus(\'' + n.id + '\')">' + (n.status === '启用' ? '停用' : '启用') + '</button>' +
      '<button class="btn btn-sm" style="background:var(--red);color:#fff;border-color:var(--red)" onclick="ipgDelete(\'' + n.id + '\')">删除</button>' +
      '</div></div></div>';
    h += '<div class="ipg-detail-body">' + ipgDetailPane(n) + '</div>';
  }
  h += '</div></div>';
  h += '<div class="hint" style="margin-top:12px">' + ic('warn', 13) + ' 交互 SSOT：OPS UX-M1 P-M1-001 · GET /ims/ip-group/tree · 数据范围 accessible-tree（ADR-IMS-003）。</div>';
  return h;
};
function ipgEdit(id, mode) {
  let n = id ? ipgFind(id) : null;
  const isCreate = mode === 'BIG' || mode === 'SMALL';
  const typ = mode === 'BIG' ? 'BIG' : mode === 'SMALL' ? 'SMALL' : (n ? n.typ : 'SMALL');
  const parentOpts = IPG_FOREST.map(function (b) { return b.name; });
  openDrawer(isCreate ? (typ === 'BIG' ? '新建大组' : '新建小组') : '编辑 IP 组 · ' + n.name, frow([
    { k: 'name', label: 'IP 组名称', type: 'text', req: true, val: isCreate ? '' : n.name, ph: '1-50 字符' },
    { k: 'typ', label: '组类型', type: 'pills', opts: ['大组', '小组'], val: typ === 'BIG' ? '大组' : '小组', disabled: !isCreate },
    { k: 'parent', label: '上级 IP 组', type: 'select', opts: parentOpts, val: mode === 'SMALL' && n ? n.name : (n ? ipgParentName(n) : parentOpts[0]), hint: '小组须选大组' },
    { k: 'leader', label: '组长', type: 'select', opts: ['（空）', '何舟', '苏杳', '赵敏', '孙倩', '张武', 'Donny'], val: isCreate ? '（空）' : (n.leader || '（空）') },
    { k: 'level', label: '等级', type: 'select', opts: ['未分级', 'S级', 'A级', 'B级', 'C级'], val: isCreate ? '未分级' : (n.level || '未分级') },
    { k: 'sort', label: '排序', type: 'num', val: isCreate ? '0' : String(n.sort) },
    { k: 'remark', label: '备注', type: 'textarea', val: isCreate ? '' : (n.remark === '—' ? '' : n.remark), wide: true }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="ipgSave(\'' + (id || '') + '\',\'' + mode + '\')">确认</button>', '520px');
}
function ipgSave(id, mode) {
  if (!formValidate(['name'])) return;
  const name = $('#F_name').value.trim();
  if (mode === 'BIG') {
    IPG_FOREST.push({ id: 'g_' + Date.now(), name: name, typ: 'BIG', leader: '—', level: '', status: '启用', sort: 0, remark: '—', created: '2026-09-29 17:30:00', updated: '2026-09-29 17:30:00', mc: 0, ac: 0, anc: 0, children: [] });
    state.ipgOpen[IPG_FOREST[IPG_FOREST.length - 1].id] = true;
  } else if (mode === 'SMALL') {
    const par = ipgFind(id);
    if (par && par.children) par.children.push({ id: 'g_' + Date.now(), name: name, typ: 'SMALL', leader: '—', level: 'C级', status: '启用', sort: par.children.length, remark: '—', created: '2026-09-29 17:30:00', updated: '2026-09-29 17:30:00', mc: 0, ac: 0, anc: 0 });
  } else {
    const n = ipgFind(id);
    if (n) { n.name = name; n.updated = '2026-09-29 17:30:00'; n.leader = $('#F_leader').value === '（空）' ? '—' : $('#F_leader').value; n.level = $('#F_level').value === '未分级' ? '' : $('#F_level').value; n.sort = Number($('#F_sort').value || 0); n.remark = $('#F_remark').value.trim() || '—'; }
  }
  toast('IP 组已保存（POST/PUT /ims/ip-group）', 'success');
  closeDrawer();
  renderPage();
}
function ipgToggleStatus(id) {
  const n = ipgFind(id);
  if (!n) return;
  n.status = n.status === '启用' ? '停用' : '启用';
  n.updated = '2026-09-29 17:30:00';
  toast('状态已更新为「' + n.status + '」', 'success');
  renderPage();
}
function ipgDelete(id) {
  const n = ipgFind(id);
  if (!n) return;
  const hasData = n.mc > 0 || n.ac > 0 || n.anc > 0 || (IPG_MEMBERS[n.id] || []).length || (IPG_ANCHORS[n.id] || []).length;
  if (hasData) { toast('该 IP 组下存在数据，禁止删除（AC-M1-001-3）', 'error'); return; }
  IPG_FOREST.forEach(function (big, bi) {
    if (big.id === id) { IPG_FOREST.splice(bi, 1); return; }
    big.children = (big.children || []).filter(function (c) { return c.id !== id; });
  });
  if (state.ipgSel === id) state.ipgSel = 'g_zw';
  toast('IP 组已删除', 'success');
  renderPage();
}
function ipgMemberAdd(gid) {
  openDrawer('添加成员', frow([
    { k: 'user', label: '用户 UserSelect', type: 'select', req: true, opts: ['请选择', '赵敏', '孙倩', '王野', '李澈'] },
    { k: 'pos', label: '岗位', type: 'select', req: true, opts: ['运营', '编辑', '直播运营', '运营组长', '运营总监'] },
    { k: 'rel', label: '主/兼', type: 'pills', opts: ['主职', '兼职'], val: '主职' }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="ipgMemberSave(\'' + gid + '\',-1)">确定</button>', '480px');
}
function ipgMemberEdit(gid, i) {
  const m = (IPG_MEMBERS[gid] || [])[i];
  openDrawer('编辑成员 · ' + m.name, frow([
    { k: 'pos', label: '岗位', type: 'select', val: m.pos, opts: ['运营', '编辑', '直播运营', '运营组长'] },
    { k: 'rel', label: '主/兼', type: 'pills', opts: ['主职', '兼职'], val: m.rel }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="ipgMemberSave(\'' + gid + '\',' + i + ')">保存</button>', '480px');
}
function ipgMemberSave(gid, i) {
  if (i < 0 && !formValidate(['user', 'pos'])) return;
  if (!IPG_MEMBERS[gid]) IPG_MEMBERS[gid] = [];
  if (i < 0) {
    const u = $('#F_user').value;
    IPG_MEMBERS[gid].push({ name: u, pos: $('#F_pos').value, rel: $('#F_rel').value || '主职', lead: false });
    const n = ipgFind(gid);
    if (n) n.mc = IPG_MEMBERS[gid].length;
  } else {
    const m = IPG_MEMBERS[gid][i];
    m.pos = $('#F_pos').value;
    m.rel = $('#F_rel').value || m.rel;
  }
  toast('成员已保存', 'success');
  closeDrawer();
  renderPage();
}
function ipgMemberRemove(gid, i) {
  (IPG_MEMBERS[gid] || []).splice(i, 1);
  const n = ipgFind(gid);
  if (n) n.mc = (IPG_MEMBERS[gid] || []).length;
  toast('成员已移除', 'success');
  renderPage();
}
function ipgAnchorAdd(gid) {
  openDrawer('添加关联作者', frow([
    { k: 'author', label: '作者（下拉）', type: 'select', req: true, opts: ['请选择作者', '苏杳 · au_sy', '赵敏 · au_zm', '孙倩 · au_sq', '张武 · au_zw'] },
    { k: 'atype', label: '作者类型', type: 'select', opts: ['短视频', '官方号', '直播'] }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="ipgAnchorSave(\'' + gid + '\')">确定</button>', '480px');
}
function ipgAnchorSave(gid) {
  if (!formValidate(['author'])) return;
  const raw = $('#F_author').value;
  const name = raw.split('·')[0].trim();
  if (!IPG_ANCHORS[gid]) IPG_ANCHORS[gid] = [];
  IPG_ANCHORS[gid].push({ id: 'au_new', name: name, typ: $('#F_atype').value, acct: '—', user: name });
  const n = ipgFind(gid);
  if (n) n.anc = IPG_ANCHORS[gid].length;
  toast('关联作者已绑定（POST .../anchors）', 'success');
  closeDrawer();
  renderPage();
}
function ipgAnchorRemove(gid, i) {
  (IPG_ANCHORS[gid] || []).splice(i, 1);
  const n = ipgFind(gid);
  if (n) n.anc = (IPG_ANCHORS[gid] || []).length;
  toast('已解除关联', 'success');
  renderPage();
}
function ipgAccountBind(gid) {
  openDrawer('关联账号 · 仅小组', frow([
    { k: 'acct', label: '平台账号', type: 'select', req: true, opts: ['88001 神鱼电竞A · 抖音', '88014 体育号B · 快手', '88033 神鱼健身 · 小红书'] }
  ]) + '<div class="hint">大组绑账号返回 1203；须账号选择器（1501）。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'acct\']))return;toast(\'账号已关联\',\'success\');closeDrawer();renderPage()">确定</button>', '480px');
}

const COST_ROWS = [
  { no: 'C-2201', acct: '88001 神鱼电竞A', typ: '采购', amt: 12000, per: '2026-09' },
  { no: 'C-2208', acct: '88001 神鱼电竞A', typ: '过程成本', amt: 860, per: '2026-09' },
  { no: 'C-2212', acct: '88014 体育号B', typ: '采购', amt: 5400, per: '2026-08' }
];
PAGES.cost = function () {
  const cur = state.tab.cost || '成本登记';
  let h = pgHead('cost', '<button class="btn btn-sec" onclick="exportX(this,\'账号财务\',COST_ROWS.length)">导出</button><button class="btn btn-pri" onclick="costAdd()">' + ic('plus', 15) + '登记成本</button>');
  h += '<div class="tabs">' + ['成本登记', '账号 ROI'].map(function (t) { return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'cost\',\'' + t + '\')">' + t + '</div>'; }).join('') + '</div>';
  if (cur === '成本登记') {
    h += qbar(qi('账号 / 单号', 140) + qs(['全部类型', '采购', '过程成本']));
    let rows = '';
    COST_ROWS.forEach(function (r) {
      rows += '<tr><td class="mono">' + r.no + '</td><td>' + r.acct + '</td><td>' + tag(r.typ, r.typ === '采购' ? 'blue' : 'orange') + '</td><td class="num">' + fmtMoney(r.amt) + '</td><td class="num">' + r.per + '</td>' +
        '<td><span class="btn-txt btn" onclick="toast(\'成本详情\',\'success\')">详情</span></td></tr>';
    });
    h += tbl(['成本单', '账号', '类型', '金额', '期间', '操作'], rows);
  } else {
    h += '<div class="card" style="margin-bottom:14px;border:1px solid rgba(255,149,0,.35);background:rgba(255,149,0,.08)"><div class="rowline">' + ic('warn', 16) +
      '<div><b>营收口径 BR-302</b><div class="csub">账号 ROI 营收来自 Football 订单 WebAPI 汇总，禁止直连 pay 库。场次利润见「场次财务」，粒度不同须标注。</div></div></div></div>';
    h += tbl(['账号', '成本', '营收（WebAPI）', 'ROI', '粒度'],
      '<tr><td>88001 神鱼电竞A</td><td class="num">' + fmtMoney(12860) + '</td><td class="num">' + fmtMoney(18640) + '</td><td class="pos">1.45</td><td>' + tag('账号', 'blue') + '</td></tr>' +
      '<tr><td>电竞一组（汇总）</td><td class="num">' + fmtMoney(42000) + '</td><td class="num">' + fmtMoney(61200) + '</td><td class="pos">1.46</td><td>' + tag('IP 组', 'cyan') + '</td></tr>');
  }
  return h;
};
function costAdd() {
  openDrawer('登记成本', frow([
    { k: 'acct', label: '账号', type: 'select', req: true, opts: ['请选择账号', '88001 神鱼电竞A', '88014 体育号B'] },
    { k: 'typ', label: '类型', type: 'pills', opts: ['采购', '过程成本'], val: '采购' },
    { k: 'amt', label: '金额', type: 'num', req: true, unit: '¥' },
    { k: 'per', label: '期间', type: 'text', val: '2026-09' }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'amt\']))return;formOk(\'C-2299\',\'成本已登记\');toast(\'已保存\',\'success\')">提交</button>', '480px');
}

const COL_JOBS = [
  { id: 'J-101', name: '抖音统一 nightly', plat: '抖音', typ: '统一任务', obj: '12 个启用成员', cron: '0 2 * * *', last: '2026-09-29 02:00', next: '2026-09-30 02:00', on: true },
  { id: 'J-102', name: '神鱼体育 · 作品', plat: '抖音', typ: '单账号', obj: '88001 神鱼体育', cron: '0 */6 * * *', last: '2026-09-29 08:00', next: '2026-09-29 14:00', on: true },
  { id: 'J-103', name: '外部竞品监测', plat: '抖音', typ: '外部配置', obj: '竞品抖音 A', cron: '0 8 * * *', last: '2026-09-29 08:00', next: '2026-09-30 08:00', on: true }
];
const COL_LOGS = [
  { task: 'J-102', acct: '88001 神鱼体育', plat: '抖音', st: '失败', err: 'Cookie 失效 · 建议打开账号采集 Tab', ts: '2026-09-29 08:02', partial: false },
  { task: 'J-101', acct: '88014 神鱼好物优选', plat: '抖音', st: '失败', err: '未绑定 Collector（oa_collector_account_bind）', ts: '2026-09-29 02:01', partial: false },
  { task: 'J-101', acct: '（批量）', plat: '抖音', st: 'PARTIAL', err: '11/12 成功', ts: '2026-09-29 02:00', partial: true },
  { task: 'J-103', acct: '—', plat: '抖音', st: '成功', err: '—', ts: '2026-09-29 08:00', partial: false }
];
PAGES.collectTask = function () {
  let h = pgHead('collectTask', '<button class="btn btn-sec" onclick="exportX(this,\'采集任务\',COL_JOBS.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="colJobEdit(-1)">' + ic('plus', 15) + '新增任务</button>' +
    '<button class="btn btn-sec btn-sm" onclick="toast(\'企微/奥创内部例外 · /ims/collect/internal\',\'success\')">内部例外</button>');
  h += qbar(qi('任务名称', 140) + qs(['全部平台', '抖音', '快手', '企业微信']) + qs(['全部类型', '单账号', '统一任务', '外部配置']));
  let rows = '';
  COL_JOBS.forEach(function (j, idx) {
    rows += '<tr><td style="font-weight:500">' + j.name + '</td><td>' + j.plat + '</td><td>' + j.typ + '</td><td>' + j.obj + '</td><td class="mono" style="font-size:11px">' + j.cron + '</td>' +
      '<td class="num" style="font-size:11px">' + j.last + '</td><td class="num" style="font-size:11px">' + j.next + '</td><td>' + tag(j.on ? '启用' : '停用', j.on ? 'green' : 'gray') + '</td>' +
      '<td><button class="btn btn-pri btn-sm" onclick="colJobRun(' + idx + ')">立即执行</button> <span class="btn-txt btn" onclick="colJobEdit(' + idx + ')">编辑</span> <span class="btn-txt btn" onclick="go(\'collectLog\')">日志</span></td></tr>';
  });
  h += tbl(['任务名称', '平台', '类型', '绑定对象', 'cron', '上次执行', '下次执行', '状态', '操作'], rows);
  h += '<div class="hint">Channel-A 凭证在 <b>账号详情 · 采集 Tab</b>（ADR-047）；本页只调度。统一任务 collectEnabled（ADR-061）。Channel-D 绑定竞品账号配置 + credential_profile。</div>';
  return h;
};
PAGES.collectLog = function () {
  let h = pgHead('collectLog', '<button class="btn btn-sec" onclick="exportX(this,\'采集日志\',COL_LOGS.length)">导出</button>' +
    '<button class="btn btn-sec" onclick="colFill()">手工补录</button>');
  h += '<div class="g4" style="margin-bottom:12px"><div class="card stat"><span class="l">24h 成功率</span><div class="n pos">94.2%</div></div><div class="card stat"><span class="l">连续失败账号</span><div class="n neg">2</div></div><div class="card stat"><span class="l">待补录</span><div class="n">0</div></div><div class="card stat"><span class="l">预警</span><div class="n" style="color:var(--orange)">1</div></div></div>';
  h += qbar(qi('任务', 100) + qi('账号', 120) + qs(['全部状态', '成功', '失败', 'PARTIAL']));
  let rows = '';
  COL_LOGS.forEach(function (L, idx) {
    const stc = L.st === '成功' ? 'green' : L.st === 'PARTIAL' ? 'orange' : 'red';
    rows += '<tr><td class="mono">' + L.task + '</td><td>' + L.acct + '</td><td>' + L.plat + '</td><td>' + tag(L.st, stc) + '</td><td style="font-size:12px;color:var(--text2)">' + L.err + '</td><td class="num">' + L.ts + '</td>' +
      '<td><span class="btn-txt btn" onclick="colLogDetail(' + idx + ')">详情</span>' +
      (L.st === '失败' ? ' <span class="btn-txt btn" onclick="go(\'acct\');acctDetail(0,\'collect\')">账号采集 Tab</span>' : '') + '</td></tr>';
  });
  h += tbl(['任务', '账号', '平台', '状态', '摘要', '时间', '操作'], rows);
  h += '<div class="hint">连续失败 → ALERT COLLECT_ERROR。排障：日志详情 → 账号采集 Tab → 重新 bind。</div>';
  return h;
};
PAGES.collectExtAccount = function () {
  let h = pgHead('collectExtAccount', '<button class="btn btn-pri" onclick="colCfg(\'extAccount\')">' + ic('plus', 15) + '新增外部账号</button>' +
    '<button class="btn btn-sec" onclick="colCfg(\'credential\')">租户采集凭账号</button>' +
    '<button class="btn btn-sec btn-sm" onclick="colCfg(\'extSource\')">外部 HTTP 数据源</button>');
  h += '<div class="hint" style="margin-bottom:10px">UX-M8 §3.2 · 配置行 <b>不嵌 Cookie</b>（ADR-052）；operator 凭账号单独维护。</div>';
  h += qbar(qi('账号名称', 120) + qs(['全部平台', '抖音', '快手', '小红书']) + qs(['全部状态', '启用', '停用']));
  h += tbl(['ID', '平台', '账号名称', '账号标识', '状态', '更新时间', '操作'],
    '<tr><td class="mono">E-101</td><td>抖音</td><td>竞品抖音 A</td><td class="mono">dy_comp_a</td><td>' + tag('启用', 'green') + '</td><td class="num">2026-09-28</td><td><span class="btn-txt btn" onclick="colCfg(\'extAccount\')">编辑</span> <span class="btn-txt btn" onclick="toast(\'批量导入 CSV\',\'success\')">导入</span></td></tr>' +
    '<tr><td class="mono">E-102</td><td>快手</td><td>竞品快手 B</td><td class="mono">ks_comp_b</td><td>' + tag('启用', 'green') + '</td><td class="num">2026-09-20</td><td><span class="btn-txt btn" onclick="colCfg(\'extAccount\')">编辑</span></td></tr>');
  return h;
};
PAGES.collectExtKeyword = function () {
  let h = pgHead('collectExtKeyword', '<button class="btn btn-pri" onclick="colCfg(\'keyword\')">' + ic('plus', 15) + '新增关键词</button>');
  h += qbar(qi('关键词', 120) + qs(['全部平台', '抖音', '快手']) + qs(['全部状态', '启用', '停用']));
  h += tbl(['ID', '平台', '关键词', '匹配类型', '状态', '操作'],
    '<tr><td class="mono">K-201</td><td>抖音</td><td>电竞赛事</td><td>模糊</td><td>' + tag('启用', 'green') + '</td><td><span class="btn-txt btn" onclick="colCfg(\'keyword\')">编辑</span></td></tr>' +
    '<tr><td class="mono">K-202</td><td>抖音</td><td>跑鞋测评</td><td>精确</td><td>' + tag('启用', 'green') + '</td><td><span class="btn-txt btn" onclick="colCfg(\'keyword\')">编辑</span></td></tr>');
  h += '<div class="hint">独立路由 · 与「竞品账号配置」并列，禁止与外部数据源混在同一 Tab 条。</div>';
  return h;
};
PAGES.collectMetadata = function () {
  let h = pgHead('collectMetadata', '<button class="btn btn-pri" onclick="colMetaAdd()">' + ic('plus', 15) + '映射实体</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'bi0Query\');toast(\'自定义查询消费已映射实体\',\'success\')">去自定义查询</button>');
  h += qbar(qi('表名 / 实体', 160) + qs(['全部', '已映射', '未映射']));
  h += tbl(['实体编码', '物理表', '字段数', '查询控件', '状态', '操作'],
    '<tr><td class="mono">ip_group</td><td class="mono">oa_ip_group</td><td class="num">18</td><td>树选择 / 文本</td><td>' + tag('已映射', 'green') + '</td><td><span class="btn-txt btn" onclick="colMetaAdd()">字段配置</span></td></tr>' +
    '<tr><td class="mono">account</td><td class="mono">oa_platform_account</td><td class="num">24</td><td>账号选择器</td><td>' + tag('已映射', 'green') + '</td><td><span class="btn-txt btn" onclick="colMetaAdd()">字段配置</span></td></tr>' +
    '<tr><td>—</td><td class="mono">oa_collect_raw_tmp</td><td class="num">9</td><td>—</td><td>' + tag('未映射', 'orange') + '</td><td><span class="btn-txt btn" onclick="colMetaAdd()">从物理表导入</span></td></tr>');
  h += '<div class="hint">UX-M8 §4 · 主导航在 <b>数据采集</b>；BI0 自定义查询未映射返回 1261 并链回本页。</div>';
  return h;
};
PAGES.collectThreshold = function () {
  const cur = state.tab.collectThreshold || '作品阈值';
  const tabs = ['预警阈值', '粉丝阈值', '作品阈值', '账号覆盖'];
  let h = pgHead('collectThreshold', '<button class="btn btn-pri" onclick="colThresholdEdit()">' + ic('plus', 15) + '新增规则</button>');
  h += '<div class="tabs">' + tabs.map(function (t) { return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'collectThreshold\',\'' + t + '\')">' + t + '</div>'; }).join('') + '</div>';
  h += tbl(['规则', '类别', '条件', '通知', '状态', '操作'],
    '<tr><td>爆款播放</td><td>' + cur + '</td><td>播放 ≥ 50w</td><td>站内</td><td>' + tag('启用', 'green') + '</td><td><span class="btn-txt btn" onclick="colThresholdEdit()">编辑</span></td></tr>' +
    '<tr><td>低分作品</td><td>' + cur + '</td><td>互动率 &lt; 1%</td><td>站内+钉钉</td><td>' + tag('启用', 'green') + '</td><td><span class="btn-txt btn" onclick="colThresholdEdit()">编辑</span></td></tr>' +
    '<tr><td>高粉账号</td><td>粉丝阈值</td><td>粉丝 ≥ 10w</td><td>站内</td><td>' + tag('启用', 'green') + '</td><td><span class="btn-txt btn" onclick="colThresholdEdit()">编辑</span></td></tr>');
  h += '<div class="hint">GET/PUT /collect/threshold · <b>13 预警中心</b> 与 <b>内部分析 / 竞品分析</b> 引用本配置；账号覆盖优先于全局。</div>';
  return h;
};
PAGES.collect = PAGES.collectTask;

const COMP_WORKS = [
  { title: '夏季跑鞋横评 · 全价位', account: '竞品抖音 A', plat: '抖音', play: 1284000, seg: '爆款', pub: '2026-09-28', complete: '32%' },
  { title: '百万播放示范片', account: 'Keep 官方', plat: '抖音', play: 1560000, seg: '爆款', pub: '2026-09-15', complete: '41%' },
  { title: '新手入门跑姿', account: '竞品快手 B', plat: '快手', play: 62000, seg: '低分', pub: '2026-09-25', complete: '12%' },
  { title: '低完播复盘样例', account: '悦跑圈官方', plat: '抖音', play: 183000, seg: '低分', pub: '2026-09-18', complete: '15%' },
  { title: '赛事花絮 v3', account: '竞品抖音 A', plat: '抖音', play: 421000, seg: '正常', pub: '2026-09-20', complete: '28%' }
];
const COMP_ACCOUNTS = [
  { name: '竞品抖音 A', plat: '抖音', fans: 862000, works: 142, sync: '2026-09-29 08:00', seg: '高粉', growth: '+1.2w/日' },
  { name: 'Keep 官方', plat: '抖音', fans: 5120000, works: 890, sync: '2026-09-29 08:00', seg: '高粉', growth: '+3.8w/日' },
  { name: '竞品快手 B', plat: '快手', fans: 48000, works: 56, sync: '2026-09-28 08:00', seg: '低粉', growth: '连降 7 日' },
  { name: '悦跑圈官方', plat: '抖音', fans: 92000, works: 210, sync: '2026-09-27 08:00', seg: '正常', growth: '+120/日' }
];
function compWorkFilter(tab) {
  tab = tab || state.tab.compWork || '全部';
  if (tab === '爆款') return COMP_WORKS.filter(function (w) { return w.seg === '爆款'; });
  if (tab === '低分') return COMP_WORKS.filter(function (w) { return w.seg === '低分'; });
  return COMP_WORKS.slice();
}
function compAccountFilter(tab) {
  tab = tab || state.tab.compAccount || '全部';
  if (tab === '高粉') return COMP_ACCOUNTS.filter(function (a) { return a.seg === '高粉'; });
  if (tab === '低粉') return COMP_ACCOUNTS.filter(function (a) { return a.seg === '低粉'; });
  return COMP_ACCOUNTS.slice();
}
function fmtPlay(n) {
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w';
  return String(n);
}
PAGES.compWork = function () {
  const tab = state.tab.compWork || '全部';
  const list = compWorkFilter(tab);
  let h = pgHead('compWork', '<button class="btn btn-sec" onclick="exportX(this,\'竞品作品\',' + list.length + ')">导出</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'collectThreshold\')">阈值规则</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'collectExtAccount\')">竞品账号配置</button>');
  h += '<div class="hint" style="margin-bottom:8px">UX-M7 · 爆款=BR-003（≥100w 播放）· 低分=BR-004（完播 &lt;20%）· 阈值只读引用 COLLECT。</div>';
  h += catTabs('compWork', ['爆款', '低分'], COMP_WORKS, function (w) { return w.seg === '正常' ? '—' : w.seg; });
  h += qbar(qs(['全部平台', '抖音', '快手', '小红书'], 100) + qs(['全部 IP 组', '电竞一组', '体育二组'], 110) + qi('日期范围', 130));
  const hits = COMP_WORKS.filter(function (w) { return w.seg === '爆款'; }).length;
  const lows = COMP_WORKS.filter(function (w) { return w.seg === '低分'; }).length;
  h += '<div class="g4" style="margin:12px 0"><div class="card stat"><span class="l">当前 Tab 作品</span><div class="n">' + list.length + '</div></div>' +
    '<div class="card stat"><span class="l">爆款（库内）</span><div class="n" style="color:var(--orange)">' + hits + '</div></div>' +
    '<div class="card stat"><span class="l">低分（库内）</span><div class="n">' + lows + '</div></div>' +
    '<div class="card stat"><span class="l">API segment</span><div class="n" style="font-size:14px">' + (tab === '全部' ? 'ALL · BLOCKED' : tab === '爆款' ? 'HIT' : 'LOW_SCORE') + '</div></div></div>';
  if (tab === '全部' && !list.length) {
    h += '<div class="card" style="padding:24px;text-align:center;color:var(--text2)">Tab「全部」待 OPS <code>external-work</code> 分页 API · 原型用 mock 5 条</div>';
  }
  let rows = '';
  if (!list.length && tab !== '全部') {
    rows = '<tr><td colspan="7" style="text-align:center;padding:28px;color:var(--text2)">当前 Tab 无命中作品 · 可调整阈值或日期</td></tr>';
  } else {
    list.forEach(function (w, idx) {
      const tg = w.seg === '爆款' ? tag('爆款', 'orange') : w.seg === '低分' ? tag('低分', 'gray') : tag('正常', 'green');
      rows += '<tr><td style="font-weight:500">' + w.title + '</td><td>' + w.account + '</td><td>' + w.plat + '</td><td class="num">' + fmtPlay(w.play) + '</td><td class="num">' + w.complete + '</td><td>' + tg + '</td>' +
        '<td><span class="btn-txt btn" onclick="compWorkDetail(' + COMP_WORKS.indexOf(w) + ')">详情</span></td></tr>';
    });
  }
  h += tbl(['作品', '竞品账号', '平台', '播放', '完播率', '标签', '操作'], rows);
  h += '<div class="hint">GET /comp-analysis/work/page?segment=… → 透传 OPS hit/list · low-score/list · 全部 BLOCKED。</div>';
  return h;
};
PAGES.compAccount = function () {
  const tab = state.tab.compAccount || '全部';
  const list = compAccountFilter(tab);
  let h = pgHead('compAccount', '<button class="btn btn-sec" onclick="exportX(this,\'竞品账号\',' + list.length + ')">导出</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'collectThreshold\')">阈值规则</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'collectExtAccount\')">竞品账号配置</button>');
  h += '<div class="hint" style="margin-bottom:8px">≠ 数据采集 · 竞品账号配置（Channel-D 配置行）；本页消费 <code>oa_external_account</code> 快照。</div>';
  h += catTabs('compAccount', ['高粉', '低粉'], COMP_ACCOUNTS, function (a) { return a.seg === '正常' ? '—' : a.seg; });
  h += qbar(qs(['全部平台', '抖音', '快手'], 90) + qs(['全部 IP 组', '电竞一组', '体育二组'], 110) + qi('日期范围', 130));
  let rows = '';
  if (!list.length) {
    rows = '<tr><td colspan="7" style="text-align:center;padding:28px;color:var(--text2)">当前 Tab 无账号 · 检查采集任务或阈值</td></tr>';
  } else {
    list.forEach(function (a) {
      const tg = a.seg === '高粉' ? tag('高粉', 'orange') : a.seg === '低粉' ? tag('低粉', 'gray') : tag('正常', 'green');
      rows += '<tr><td style="font-weight:500">' + a.name + '</td><td>' + a.plat + '</td><td class="num">' + fmtPlay(a.fans) + '</td><td class="num">' + a.works + '</td><td class="num" style="font-size:12px">' + a.growth + '</td><td>' + tg + '</td>' +
        '<td><span class="btn-txt btn" onclick="compAccountDetail(' + COMP_ACCOUNTS.indexOf(a) + ')">详情</span></td></tr>';
    });
  }
  h += tbl(['账号', '平台', '粉丝', '作品数', '增速/趋势', '标签', '操作'], rows);
  h += '<div class="hint">GET /comp-analysis/account/page?segment=ALL|HIGH_FANS|LOW_FANS → external/list · high-follower · low-follower。</div>';
  return h;
};
PAGES.compAnalysis = PAGES.compWork;
function compWorkDetail(i) {
  const w = COMP_WORKS[i];
  if (!w) return;
  openDrawer('竞品作品 · ' + w.title, '<div class="kv"><div><div class="k">账号</div><div class="v">' + w.account + '</div></div><div><div class="k">平台</div><div class="v">' + w.plat + '</div></div>' +
    '<div><div class="k">播放</div><div class="v num">' + fmtPlay(w.play) + '</div></div><div><div class="k">完播率</div><div class="v">' + w.complete + '</div></div></div>' +
    '<div class="hint">对齐 UX-M7 爆款/低分详情抽屉 · 只读摘要。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '480px');
}
function compAccountDetail(i) {
  const a = COMP_ACCOUNTS[i];
  if (!a) return;
  openDrawer('竞品账号 · ' + a.name, '<div class="kv"><div><div class="k">粉丝</div><div class="v num">' + fmtPlay(a.fans) + '</div></div><div><div class="k">作品数</div><div class="v">' + a.works + '</div></div>' +
    '<div><div class="k">最近同步</div><div class="v">' + a.sync + '</div></div><div><div class="k">趋势</div><div class="v">' + a.growth + '</div></div></div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-sec btn-sm" onclick="go(\'collectExtAccount\');closeDrawer()">采集配置</button>', '480px');
}

const INT_WORKS = [
  { title: '晚间集锦 #12', account: '神鱼电竞A', plat: '抖音', play: 1284000, seg: '爆款', pub: '2026-09-28', complete: '38%' },
  { title: '训练周记 · 九月', account: '体育号B', plat: '快手', play: 62000, seg: '低分', pub: '2026-09-26', complete: '11%' },
  { title: '赛事复盘长视频', account: '神鱼电竞A', plat: '抖音', play: 2100000, seg: '爆款', pub: '2026-09-20', complete: '35%' },
  { title: '日常花絮', account: '神鱼好物优选', plat: '抖音', play: 89000, seg: '低分', pub: '2026-09-22', complete: '14%' },
  { title: '直播切片 · 周一', account: '神鱼电竞A', plat: '抖音', play: 356000, seg: '正常', pub: '2026-09-25', complete: '26%' }
];
const INT_ACCOUNTS = [
  { name: '神鱼电竞A', plat: '抖音', ipg: '电竞一组', fans: 1280000, works: 486, seg: '高粉', growth: '+2.1w/日' },
  { name: '神鱼好物优选', plat: '抖音', ipg: '体育二组', fans: 920000, works: 312, seg: '高粉', growth: '+8.4k/日' },
  { name: '体育号B', plat: '快手', ipg: '体育二组', fans: 42000, works: 88, seg: '低粉', growth: '连降 7 日' },
  { name: '神鱼视频号', plat: '视频号', ipg: '电竞一组', fans: 156000, works: 64, seg: '正常', growth: '+320/日' }
];
function intWorkFilter(tab) {
  tab = tab || state.tab.intWork || '全部';
  if (tab === '爆款') return INT_WORKS.filter(function (w) { return w.seg === '爆款'; });
  if (tab === '低分') return INT_WORKS.filter(function (w) { return w.seg === '低分'; });
  return INT_WORKS.slice();
}
function intAccountFilter(tab) {
  tab = tab || state.tab.intAccount || '全部';
  if (tab === '高粉') return INT_ACCOUNTS.filter(function (a) { return a.seg === '高粉'; });
  if (tab === '低粉') return INT_ACCOUNTS.filter(function (a) { return a.seg === '低粉'; });
  return INT_ACCOUNTS.slice();
}
PAGES.intWork = function () {
  const tab = state.tab.intWork || '全部';
  const list = intWorkFilter(tab);
  let h = pgHead('intWork', '<button class="btn btn-sec" onclick="exportX(this,\'内部作品\',' + list.length + ')">导出</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'collectThreshold\')">阈值规则</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'caDouyin\')">平台账号</button>');
  h += '<div class="hint" style="margin-bottom:8px">UX-M1 内部内容 · 爆款=BR-003（≥100w）· 低分=BR-004（完播 &lt;20%）· 阈值只读引用 COLLECT。</div>';
  h += catTabs('intWork', ['爆款', '低分'], INT_WORKS, function (w) { return w.seg === '正常' ? '—' : w.seg; });
  h += qbar(qs(['全部平台', '抖音', '快手', '视频号'], 100) + qs(['全部 IP 组', '电竞一组', '体育二组'], 110) + qi('关键词', 120));
  const hits = INT_WORKS.filter(function (w) { return w.seg === '爆款'; }).length;
  const lows = INT_WORKS.filter(function (w) { return w.seg === '低分'; }).length;
  h += '<div class="g4" style="margin:12px 0"><div class="card stat"><span class="l">当前 Tab 作品</span><div class="n">' + list.length + '</div></div>' +
    '<div class="card stat"><span class="l">爆款（库内）</span><div class="n" style="color:var(--orange)">' + hits + '</div></div>' +
    '<div class="card stat"><span class="l">低分（库内）</span><div class="n">' + lows + '</div></div>' +
    '<div class="card stat"><span class="l">API segment</span><div class="n" style="font-size:14px">' + (tab === '全部' ? 'ALL' : tab === '爆款' ? 'HIT' : 'LOW_SCORE') + (tab === '低分' ? ' · TBD' : '') + '</div></div></div>';
  let rows = '';
  if (!list.length) {
    rows = '<tr><td colspan="7" style="text-align:center;padding:28px;color:var(--text2)">当前 Tab 无命中作品 · 可调整阈值或日期</td></tr>';
  } else {
    list.forEach(function (w) {
      const tg = w.seg === '爆款' ? tag('爆款', 'orange') : w.seg === '低分' ? tag('低分', 'gray') : tag('正常', 'green');
      rows += '<tr><td style="font-weight:500">' + w.title + '</td><td>' + w.account + '</td><td>' + w.plat + '</td><td class="num">' + fmtPlay(w.play) + '</td><td class="num">' + w.complete + '</td><td>' + tg + '</td>' +
        '<td><span class="btn-txt btn" onclick="intWorkDetail(' + INT_WORKS.indexOf(w) + ')">详情</span></td></tr>';
    });
  }
  h += tbl(['作品', '内部账号', '平台', '播放', '完播率', '标签', '操作'], rows);
  h += '<div class="hint">GET /int-analysis/work/page?segment=ALL → internal-content/list · HIT → content-analysis?isHit=true · LOW_SCORE 下游 TBD。</div>';
  return h;
};
PAGES.intAccount = function () {
  const tab = state.tab.intAccount || '全部';
  const list = intAccountFilter(tab);
  let h = pgHead('intAccount', '<button class="btn btn-sec" onclick="exportX(this,\'内部账号\',' + list.length + ')">导出</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'collectThreshold\')">阈值规则</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'caDouyin\')">平台账号</button>');
  h += '<div class="hint" style="margin-bottom:8px">M1 账号分析 + M7 高/低粉监测 · 低粉含 ADR-069 绝对值与 7 日连降。</div>';
  h += catTabs('intAccount', ['高粉', '低粉'], INT_ACCOUNTS, function (a) { return a.seg === '正常' ? '—' : a.seg; });
  h += qbar(qs(['全部平台', '抖音', '快手', '视频号'], 100) + qs(['全部 IP 组', '电竞一组', '体育二组'], 110) + qi('账号名', 120));
  let rows = '';
  if (!list.length) {
    rows = '<tr><td colspan="7" style="text-align:center;padding:28px;color:var(--text2)">当前 Tab 无账号 · 检查采集或阈值</td></tr>';
  } else {
    list.forEach(function (a) {
      const tg = a.seg === '高粉' ? tag('高粉', 'orange') : a.seg === '低粉' ? tag('低粉', 'gray') : tag('正常', 'green');
      rows += '<tr><td style="font-weight:500">' + a.name + '</td><td>' + a.plat + '</td><td>' + a.ipg + '</td><td class="num">' + fmtPlay(a.fans) + '</td><td class="num">' + a.works + '</td><td>' + tg + '</td>' +
        '<td><span class="btn-txt btn" onclick="intAccountDetail(' + INT_ACCOUNTS.indexOf(a) + ')">详情</span> <span class="btn-txt btn" onclick="go(\'intWork\')">作品</span></td></tr>';
    });
  }
  h += tbl(['账号', '平台', 'IP 组', '粉丝', '作品数', '标签', '操作'], rows);
  h += '<div class="hint">GET /int-analysis/account/page?segment=ALL|HIGH_FANS|LOW_FANS → account-analysis · high/low-follower。</div>';
  return h;
};
PAGES.intAnalysis = PAGES.intWork;
function intWorkDetail(i) {
  const w = INT_WORKS[i];
  if (!w) return;
  openDrawer('内部作品 · ' + w.title, '<div class="kv"><div><div class="k">账号</div><div class="v">' + w.account + '</div></div><div><div class="k">平台</div><div class="v">' + w.plat + '</div></div>' +
    '<div><div class="k">播放</div><div class="v num">' + fmtPlay(w.play) + '</div></div><div><div class="k">完播率</div><div class="v">' + w.complete + '</div></div></div>' +
    '<div style="height:80px;background:var(--bg2);border-radius:8px;margin-top:12px;display:flex;align-items:center;justify-content:center;color:var(--text2);font-size:12px">近 7 日趋势 · GET /internal-content/{id}/trend</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '480px');
}
function intAccountDetail(i) {
  const a = INT_ACCOUNTS[i];
  if (!a) return;
  openDrawer('内部账号 · ' + a.name, '<div class="kv"><div><div class="k">IP 组</div><div class="v">' + a.ipg + '</div></div><div><div class="k">粉丝</div><div class="v num">' + fmtPlay(a.fans) + '</div></div>' +
    '<div><div class="k">作品数</div><div class="v">' + a.works + '</div></div><div><div class="k">趋势</div><div class="v">' + a.growth + '</div></div></div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-sec btn-sm" onclick="go(\'intWork\');closeDrawer()">查看作品</button>', '480px');
}
function colJobRun(idx) {
  toast('已触发立即执行：' + COL_JOBS[idx].name + ' · 请查看采集日志', 'success');
  go('collectLog');
}
function colJobEdit(idx) {
  const j = idx < 0 ? { name: '', plat: '抖音', typ: '单账号', cron: '0 2 * * *' } : COL_JOBS[idx];
  openDrawer(idx < 0 ? '新增采集任务' : '编辑采集任务', frow([
    { k: 'name', label: '任务名称', type: 'text', req: true, val: j.name || '' },
    { k: 'plat', label: '平台', type: 'select', opts: ['抖音', '快手', '企业微信'], val: j.plat },
    { k: 'typ', label: '任务类型', type: 'select', opts: ['单账号', '统一任务', '外部配置'] },
    { k: 'acct', label: '账号（单账号）', type: 'select', opts: ['请选择', '88001 神鱼体育', '88014 神鱼好物优选'] },
    { k: 'cron', label: 'cron', type: 'text', val: j.cron || '0 2 * * *' }
  ]) + '<div class="hint">禁止在此填写 Cookie。未 bind 账号执行将失败并在日志提示。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'name\']))return;formOk(\'JOB\',\'任务已保存\');toast(\'已保存\',\'success\')">保存</button>', '520px');
}
function colLogDetail(idx) {
  const L = COL_LOGS[idx];
  openDrawer('采集日志详情 · ' + L.task, '<div class="kv">' +
    '<div><div class="k">状态</div><div class="v">' + tag(L.st, L.st === '成功' ? 'green' : 'orange') + '</div></div>' +
    '<div><div class="k">账号</div><div class="v">' + L.acct + '</div></div></div>' +
    (L.partial ? '<div class="dsec">typeResults</div><div class="hint">作品 11 成功 · 粉丝 1 失败（Cookie）</div>' : '') +
    '<div class="dsec">错误摘要</div><p style="font-size:13px">' + L.err + '</p>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '480px');
}
function colCfg(kind) {
  kind = kind || 'extAccount';
  if (kind === 'credential') {
    openDrawer('租户采集凭账号', frow([
      { k: 'plat', label: '平台', type: 'select', opts: ['抖音', '快手'] },
      { k: 'prof', label: 'Profile', type: 'text', val: 'operator-main' },
      { k: 'cookie', label: 'Cookie/Token', type: 'password', ph: '脱敏录入' },
      { k: 'exp', label: '过期时间', type: 'dt' }
    ]) + '<button class="btn btn-sec btn-sm" style="margin-top:8px" onclick="toast(\'探活成功\',\'success\')">探活</button>',
      '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="formOk(\'CRED\',\'已保存\');toast(\'已保存\',\'success\')">保存</button>', '480px');
    return;
  }
  if (kind === 'internal') {
    openDrawer('内部采集（企微/奥创）', frow([
      { k: 'name', label: '名称', type: 'text', req: true },
      { k: 'typ', label: '类型', type: 'select', opts: ['企业微信应用', '个微奥创'] },
      { k: 'agent', label: 'Agent / Bridge ID', type: 'text' }
    ]), '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="formOk(\'INT\',\'已保存\');toast(\'已保存\',\'success\')">保存</button>', '480px');
    return;
  }
  if (kind === 'keyword') {
    openDrawer('竞品关键字配置', frow([
      { k: 'plat', label: '平台', type: 'select', req: true, opts: ['抖音', '快手'] },
      { k: 'kw', label: '关键词', type: 'text', req: true, val: '电竞赛事' },
      { k: 'match', label: '匹配类型', type: 'select', opts: ['精确', '模糊'] }
    ]), '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'kw\']))return;formOk(\'KW\',\'已保存\');toast(\'已保存\',\'success\')">保存</button>', '480px');
    return;
  }
  if (kind === 'extSource') {
    openDrawer('外部 HTTP 数据源', frow([
      { k: 'name', label: '名称', type: 'text', req: true },
      { k: 'url', label: 'API URL', type: 'text', req: true },
      { k: 'key', label: 'API Key', type: 'password', ph: '脱敏' }
    ]), '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="formOk(\'SRC\',\'已保存\');toast(\'已保存\',\'success\')">保存</button>', '480px');
    return;
  }
  openDrawer('竞品账号配置', frow([
    { k: 'plat', label: '平台', type: 'select', req: true, opts: ['抖音', '快手', '小红书'] },
    { k: 'name', label: '账号名称', type: 'text', req: true, val: '竞品抖音 A' },
    { k: 'ident', label: '账号标识', type: 'text', req: true, val: 'dy_comp_a' }
  ]) + '<div class="hint">禁止在此填写 Cookie；Channel-D 任务引用本配置 + 租户凭账号 profile。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'name\']))return;formOk(\'EXT\',\'已保存\');toast(\'已保存\',\'success\')">保存</button>', '480px');
}
function colMetaAdd() {
  openDrawer('元数据实体', frow([
    { k: 'tbl', label: '物理表', type: 'select', req: true, opts: ['oa_ip_group', 'oa_platform_account', 'oa_collect_raw_tmp'] },
    { k: 'code', label: '实体编码', type: 'text', req: true, val: 'ip_group' },
    { k: 'cond', label: '查询条件类别', type: 'select', opts: ['文本', '字典', '日期', '账号选择器', 'IP 组树'] }
  ]), '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="formOk(\'META\',\'实体已保存\');toast(\'已保存\',\'success\')">保存</button>', '520px');
}
function colThresholdEdit() {
  openDrawer('阈值规则', frow([
    { k: 'name', label: '规则名称', type: 'text', req: true, val: '爆款播放' },
    { k: 'plat', label: '平台', type: 'select', opts: ['抖音', '快手', '全平台'] },
    { k: 'metric', label: '指标', type: 'select', opts: ['播放量', '互动率', '粉丝数'] },
    { k: 'op', label: '比较符', type: 'select', opts: ['≥', '≤'] },
    { k: 'val', label: '阈值', type: 'text', val: '500000' },
    { k: 'notify', label: '通知', type: 'select', opts: ['站内', '站内+钉钉'] }
  ]), '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="formOk(\'TH\',\'规则已保存\');toast(\'已保存\',\'success\')">保存</button>', '520px');
}
function colFill() {
  openDrawer('手工补录', frow([
    { k: 'plat', label: '平台', type: 'select', req: true, opts: ['抖音', '快手', '视频号'] },
    { k: 'acct', label: '账号', type: 'select', req: true, opts: ['请选择账号', '88001 神鱼电竞A'] },
    { k: 'note', label: '补录说明', type: 'textarea', req: true, wide: true }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'note\']))return;formOk(\'FILL-01\',\'补录已提交\');toast(\'已补录\',\'success\')">提交</button>', '480px');
}

PAGES.mon = function () {
  const cur = state.tab.mon || 'IP 主题';
  const tabs = ['IP 主题', '行业'];
  let h = pgHead('mon', '<button class="btn btn-sec" onclick="exportX(this,\'监测\',8)">导出</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'intWork\')">内部作品</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'compWork\')">竞品作品</button>');
  h += '<div class="hint" style="margin-bottom:8px">内部作品/账号 → <b>内部分析</b>；外部竞品 → <b>竞品分析</b>；本页仅 IP 主题/行业（UX-M7）。</div>';
  h += '<div class="tabs">' + tabs.map(function (t) { return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'mon\',\'' + t + '\')">' + t + '</div>'; }).join('') + '</div>';
  h += qbar(qi('主题 / 行业', 150) + qs(['全部平台', '抖音', '快手']) + qs(['全部 IP 组', '电竞一组', '体育二组']));
  if (cur === '行业') {
    h += tbl(['行业', '账号数', '平均粉丝', '操作'],
      '<tr><td>体育</td><td class="num">18</td><td class="num">32.4w</td><td><span class="btn-txt btn" onclick="monThemeDetail(\'体育\')">详情</span></td></tr>' +
      '<tr><td>跑步健身</td><td class="num">12</td><td class="num">28.1w</td><td><span class="btn-txt btn" onclick="monThemeDetail(\'跑步健身\')">详情</span></td></tr>');
  } else {
    h += tbl(['IP 主题', '外部账号数', '作品数', '爆款数', '操作'],
      '<tr><td>跑步健身</td><td class="num">12</td><td class="num">840</td><td class="num">23</td><td><span class="btn-txt btn" onclick="monThemeDetail(\'跑步健身\')">详情</span></td></tr>' +
      '<tr><td>电竞赛事</td><td class="num">8</td><td class="num">520</td><td class="num">15</td><td><span class="btn-txt btn" onclick="monThemeDetail(\'电竞赛事\')">详情</span></td></tr>');
  }
  return h;
};
function monThemeDetail(name) {
  openDrawer('IP 主题 / 行业 · ' + name, '<div class="hint">UX-M7 · GET /monitor/ip-theme/{id} · 只读摘要占位。</div>' +
    '<div class="g3" style="margin-top:12px"><div class="card stat"><span class="l">关联账号</span><div class="n">12</div></div><div class="card stat"><span class="l">作品</span><div class="n">840</div></div><div class="card stat"><span class="l">爆款</span><div class="n">23</div></div></div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-sec btn-sm" onclick="go(\'compAccount\');closeDrawer()">竞品账号</button>', '480px');
}

function bi0PageTab() {
  const m = { bi0Metric: '指标管理', bi0Analysis: '指标分析', bi0Report: '标准报表', bi0Query: '自定义查询', bi0Screen: '大屏配置' };
  return m[state.page] || '指标管理';
}
PAGES.bi0Standard = PAGES.bi0Report;
PAGES.bi0ScreenConfig = PAGES.bi0Screen;
PAGES.bi0Metric = PAGES.bi0Analysis = PAGES.bi0Report = PAGES.bi0Query = PAGES.bi0Screen = function () {
  const cur = bi0PageTab();
  let acts = '';
  if (cur === '自定义查询') {
    acts = '<button class="btn btn-sec btn-sm" onclick="go(\'collectMetadata\')">元数据维护</button>';
  } else if (cur === '标准报表') {
    acts = '<button class="btn btn-sec" onclick="exportX(this,\'报表\',8)">导出</button>';
  } else if (cur === '指标管理') {
    acts = '<button class="btn btn-sec btn-sm" onclick="toast(\'DW mt-result：结果历史查询为 IMS non-goal\',\'info\')">结果查询</button>' +
      '<button class="btn btn-pri" onclick="bi0MetricEdit()">' + ic('plus', 15) + '新建指标</button>';
  } else if (cur === '大屏配置') {
    acts = '<button class="btn btn-sec btn-sm" onclick="bi0ScreenMode(\'config\')">布局编辑</button>' +
      '<button class="btn btn-pri btn-sm" onclick="bi0ScreenMode(\'full\')">进入全屏</button>';
  }
  let h = pgHead(state.page, acts);
  if (cur === '标准报表') {
    h += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">';
    BI0_REPORTS.forEach(function (r) {
      h += '<div class="card hov" onclick="bi0OpenReport(\'' + r.slug + '\')"><div class="rowline" style="justify-content:space-between"><b>' + r.name + '</b>' + ic('chart', 18) + '</div><div class="csub" style="margin-top:8px">' + r.slug + ' · 统一筛选+图+表+导出</div></div>';
    });
    h += '</div>';
  } else if (cur === '自定义查询') {
    h += bi0QueryPage();
  } else if (cur === '指标分析') {
    h += qbar(qs(['请选择指标', '播放量', '账号 ROI', '互动率'], 160) + qs(['IP 组', '电竞一组', '体育二组']));
    h += '<div class="card" style="padding:16px;margin-bottom:12px"><div class="csub">P2 指标分析 · 选指标后出趋势图（UX-M6 P-M6-001 分析视图）</div><div style="height:120px;background:var(--bg2);border-radius:8px;margin-top:12px;display:flex;align-items:center;justify-content:center;color:var(--text2)">ECharts 趋势示意</div></div>';
  } else if (cur === '大屏配置') {
    h += bi0ScreenPage();
  } else if (cur === '指标管理') {
    h += bi0MetricPage();
  } else {
    h += tbl(['指标', '口径', '粒度', '状态'], '<tr><td>—</td><td>—</td><td>—</td><td>—</td></tr>');
  }
  return h;
};
function bi0MetricPage() {
  let h = qbar(qi('名称/编码', 140) + qs(['全部类型', 'SIMPLE', 'COMPOSITE', 'RATIO'], 110) + qs(['全部状态', '启用', '停用'], 90));
  h += '<div class="rowline" style="gap:8px;margin-bottom:12px;flex-wrap:wrap">' +
    '<span class="csub">对标 DW <code>mt-list</code></span></div>';
  h += tbl(['编码', '指标名称', '类型', '粒度', '状态', '操作'],
    '<tr><td class="mono">play_count</td><td style="font-weight:500">播放量</td><td>SIMPLE</td><td>作品 / 日</td><td>' + tag('启用', 'green') + '</td>' +
    '<td><span class="btn-txt btn" onclick="bi0MetricEdit(true)">编辑</span> <span class="btn-txt btn" onclick="bi0MetricPreview()">试算</span> <span class="btn-txt btn" onclick="toast(\'引用检查通过\',\'success\')">删除</span></td></tr>' +
    '<tr><td class="mono">account_roi</td><td style="font-weight:500">账号 ROI</td><td>RATIO</td><td>账号 / 月</td><td>' + tag('启用', 'green') + '</td>' +
    '<td><span class="btn-txt btn" onclick="bi0MetricEdit(true)">编辑</span> <span class="btn-txt btn" onclick="bi0MetricPreview()">试算</span> <span class="btn-txt btn">删除</span></td></tr>' +
    '<tr><td class="mono">interaction_rate</td><td style="font-weight:500">互动率</td><td>COMPOSITE</td><td>作品 / 日</td><td>' + tag('启用', 'green') + '</td>' +
    '<td><span class="btn-txt btn" onclick="bi0MetricEdit(true)">编辑</span> <span class="btn-txt btn" onclick="bi0MetricPreview()">试算</span> <span class="btn-txt btn">删除</span></td></tr>');
  h += '<div class="hint">BTN-PREVIEW → <code>POST /admin-api/ims/bi/metric/preview</code> · 无 DW 分类树/计算调度页（见产品对标文档）。</div>';
  return h;
}
function bi0MetricEdit(edit) {
  openDrawer(edit ? '编辑指标' : '新建指标', frow([
    { k: 'code', label: '指标编码', type: 'text', req: true, val: edit ? 'play_count' : '', ph: '全局唯一，如 play_count' },
    { k: 'name', label: '指标名称', type: 'text', req: true, val: edit ? '播放量' : '' },
    { k: 'mtype', label: '指标类型', type: 'select', req: true, opts: ['SIMPLE', 'COMPOSITE', 'RATIO'] },
    { k: 'builder', label: 'MetricBuilder', type: 'textarea', wide: true, ph: '非 COMPOSITE：可视化 Builder SQL', val: edit ? 'SUM(play_count) FROM oa_content_metric WHERE ...' : '' },
    { k: 'desc', label: '口径说明', type: 'textarea', wide: true, ph: '可选 · 若 OPS 未持久化则 IMS 不落库' }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-sec" onclick="bi0MetricPreview()">试算</button>' +
    '<button class="btn btn-pri" onclick="if(!formValidate([\'code\',\'name\']))return;formOk(\'M-01\',\'指标已保存\');toast(\'已保存\',\'success\');closeDrawer()">保存</button>', '640px');
}
function bi0MetricPreview() {
  openDrawer('指标试算 · play_count', '<div class="code-mock">SELECT ip_group_id, SUM(play_count) AS val\nFROM oa_content_metric\nWHERE stat_date BETWEEN \'2026-09-01\' AND \'2026-09-30\'\nGROUP BY ip_group_id\nLIMIT 200</div>' +
    tbl(['IP 组', '指标值'], '<tr><td>电竞一组</td><td class="num">1,284,600</td></tr><tr><td>体育二组</td><td class="num">892,400</td></tr>') +
    '<div class="hint">对标 DW <code>mt-list</code> 试算弹窗 · 预览 API 见 BI0 契约。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="toast(\'已采用试算结果\',\'success\');closeDrawer()">采用结果</button>', '520px');
}
function bi0QueryConfigOpen() {
  return state.q.bi0ConfigOpen !== false;
}
function bi0QueryToggleConfig() {
  state.q.bi0ConfigOpen = !bi0QueryConfigOpen();
  renderPage();
}
function bi0QueryCondOpen() {
  return state.q.bi0CondOpen !== false;
}
function bi0QueryToggleCond() {
  state.q.bi0CondOpen = !bi0QueryCondOpen();
  renderPage();
}
function bi0QueryResultCondOpen() {
  return state.q.bi0ResultCondOpen !== false;
}
function bi0QueryToggleResultCond() {
  state.q.bi0ResultCondOpen = !bi0QueryResultCondOpen();
  renderPage();
}
function bi0QueryExecute() {
  state.q.bi0Executed = true;
  state.q.bi0ResultTab = state.q.bi0ResultTab || 'list';
  toast('POST /ops/query/preview · 执行完成', 'success');
  renderPage();
}
function bi0QuerySetResultTab(t) {
  state.q.bi0ResultTab = t;
  renderPage();
}
function bi0QueryBuilderMock(compact) {
  const condCls = bi0QueryCondOpen() ? '' : ' collapsed';
  const condBody = bi0QueryCondOpen() ? '' : ' style="display:none"';
  let b = '<div class="bi0-qb-root qb-layout"><div class="qb-form">';
  b += '<div class="qb-row"><label>数据源</label>' + qs(['IP 组（oa_ip_group）', '平台账号（oa_platform_account）'], compact ? 200 : 280) + '</div>';
  b += '<div class="qb-row"><label>展示字段</label><div class="qb-chips"><span class="chip">IP 组名称</span><span class="chip">播放量</span><span class="qb-val-muted">多选 · displayFields</span></div></div>';
  b += '<div class="qb-row"><label>计算方式</label>' + qs(['求和 SUM', '计数 COUNT', '— 明细'], 140) + '</div>';
  b += '<div class="qb-row"><label>计算字段</label>' + qs(['播放量 play_count', '互动量 interaction_count'], 180) + '</div>';
  b += '<div class="qb-row"><label>汇总字段</label><span class="qb-val">IP 组名称 <span class="mono qb-val-muted">ip_group_name</span></span></div>';
  b += '<div class="qb-row"><label>关联表</label>' + qs(['— 无', 'oa_content_metric'], 160) + '</div>';
  b += '<div class="qb-cond-hd"><div class="collapse-h' + condCls + '" onclick="bi0QueryToggleCond()"><span class="caret">▼</span><b>查询条件</b></div></div>';
  b += '<div class="qb-cond-body"' + condBody + '><div class="tbl-wrap"><table><thead><tr><th>字段</th><th>运算符</th><th>值</th><th></th></tr></thead><tbody>' +
    '<tr><td class="mono">stat_date</td><td>BETWEEN</td><td class="num">2026-09-01 ~ 2026-09-30</td><td><span class="btn-txt btn btn-danger-txt" onclick="toast(\'已移除\',\'info\')">删除</span></td></tr></tbody></table></div>' +
    '<button class="btn btn-sec btn-sm qb-cond-add" onclick="toast(\'+ 添加条件\',\'info\')">+ 添加条件</button></div>';
  b += '<div class="dsec">SQL 预览</div><textarea class="code-edit" rows="5" readonly>SELECT g.ip_group_name, SUM(m.play_count) AS total_play\nFROM oa_ip_group g\nINNER JOIN oa_content_metric m ON m.ip_group_id = g.id\nWHERE m.stat_date BETWEEN @d1 AND @d2 AND g.tenant_id = :tenantId\nGROUP BY g.ip_group_name\nORDER BY total_play DESC\nLIMIT 1000</textarea>';
  b += '<div class="hint">仅 SELECT · 租户占位 :tenantId · 对标 <code>QueryBuilder.vue</code> + <code>buildQuerySqlFromConfig</code></div>';
  b += '</div><div class="qb-side"><div class="qb-side-hd">字段列表</div><div class="csub">点击加入展示或条件</div>' +
    ['ip_group_name|IP 组名称', 'play_count|播放量', 'platform_code|平台', 'stat_date|统计日期'].map(function (x) {
      const p = x.split('|');
      return '<div class="fi" onclick="toast(\'已选字段 ' + p[0] + '\',\'success\')">' + p[1] + '<br><span class="mono" style="font-size:10px;color:var(--text2)">' + p[0] + '</span></div>';
    }).join('') + '</div></div>';
  return b;
}
function bi0QueryResultPanel() {
  if (!state.q.bi0Executed) return '';
  const rt = state.q.bi0ResultTab || 'list';
  const rCondCls = bi0QueryResultCondOpen() ? '' : ' collapsed';
  const rCondBody = bi0QueryResultCondOpen() ? '' : ' style="display:none"';
  let h = '<div class="card bi0-result-card">';
  h += '<div class="hd-row bi0-result-hd"><div class="collapse-h' + rCondCls + '" onclick="bi0QueryToggleResultCond()"><span class="caret">▼</span><b>查询条件</b></div>' +
    '<button class="btn btn-sec btn-sm" onclick="exportX(this,\'查询结果\',2)">导出</button></div>';
  h += '<div class="desc-grid bi0-result-cond"' + rCondBody + '>' +
    '<span class="dk">数据源</span><span class="dv">IP 组（oa_ip_group）</span><span class="dk">展示字段</span><span class="dv">IP 组名称、播放量</span>' +
    '<span class="dk">计算方式</span><span class="dv">求和 SUM · play_count</span><span class="dk">汇总字段</span><span class="dv">ip_group_name</span>' +
    '<span class="dk">关联表</span><span class="dv">oa_content_metric</span><span class="dk">查询条件</span><span class="dv">stat_date BETWEEN 2026-09-01 ~ 09-30</span></div>';
  h += '<div class="hd-row"><h3 style="font-size:15px;font-weight:600;margin:0">查询结果</h3><span class="csub">共 2 行</span></div>';
  h += '<div class="tabs bi0-result-tabs"><div class="tab' + (rt === 'list' ? ' on' : '') + '" onclick="bi0QuerySetResultTab(\'list\')">结果列表</div>' +
    '<div class="tab' + (rt === 'chart' ? ' on' : '') + '" onclick="bi0QuerySetResultTab(\'chart\')">图表展示</div></div>';
  if (rt === 'chart') {
    h += '<div class="bi0-chart-bar">' +
      qs(['柱状图', '折线图', '饼图'], 100) + qs(['X 轴 · ip_group_name', 'stat_date'], 160) + qs(['Y 轴 · total_play', 'play_count'], 140) + '</div>' +
      '<div class="bi0-chart-ph">ECharts · 对标 QueryResultPanel 图表 Tab</div>';
  } else {
    h += tbl(['IP 组', '播放量'], '<tr><td style="font-weight:500">电竞一组</td><td class="num">428,600</td></tr><tr><td style="font-weight:500">体育二组</td><td class="num">312,400</td></tr>');
    h += '<div class="pag-mock"><span>共 2 条</span><select><option>10 条/页</option><option selected>20 条/页</option></select><span>‹ 1 ›</span></div>';
  }
  h += '</div>';
  return h;
}
function bi0QueryPage() {
  const sub = state.tab.bi0Query || 'build';
  let h = '<div class="page-bi0-query">';
  h += '<div class="tabs"><div class="tab' + (sub === 'build' ? ' on' : '') + '" onclick="setTab(\'bi0Query\',\'build\')">自定义查询</div>' +
    '<div class="tab' + (sub === 'mine' ? ' on' : '') + '" onclick="setTab(\'bi0Query\',\'mine\')">我的查询</div></div>';
  if (sub === 'mine') {
    h += '<div class="card bi0-mine-card"><div class="bi0-mine-hd"><div class="hd-row"><h3 style="font-size:17px;font-weight:600;margin:0">已保存查询</h3><span class="csub">共 2 条</span></div></div>';
    h += '<div class="bi0-mine-body">';
    h += qbar(qi('名称', 180) + qs(['全部状态', '草稿 DRAFT', '已发布 PUBLISHED'], 130), 'toast(\'GET /ops/query/list\',\'success\')');
    h += tbl(['查询名称', '创建人', '状态', '更新时间', '操作'],
      '<tr><td style="font-weight:500">IP 组周产出</td><td>张 analyst</td><td>' + tag('已发布', 'green') + '</td><td class="num">2026-09-30 09:12</td>' +
      '<td><span class="btn-txt btn" onclick="bi0QueryExecuteSaved()">执行</span> <span class="btn-txt btn" onclick="bi0QueryEditSaved()">编辑</span> <span class="btn-txt btn" onclick="toast(\'已是发布态\',\'info\')">发布</span> <span class="btn-txt btn btn-danger-txt" onclick="toast(\'删除（演示）\',\'info\')">删除</span></td></tr>' +
      '<tr><td style="font-weight:500">账号 ROI 明细</td><td>张 analyst</td><td>' + tag('草稿', 'gray') + '</td><td class="num">2026-09-28 16:40</td>' +
      '<td><span class="btn-txt btn" onclick="bi0QueryExecuteSaved()">执行</span> <span class="btn-txt btn" onclick="bi0QueryEditSaved()">编辑</span> <span class="btn-txt btn" onclick="toast(\'POST publish\',\'success\')">发布</span> <span class="btn-txt btn btn-danger-txt" onclick="toast(\'删除（演示）\',\'info\')">删除</span></td></tr>');
    h += '<div class="pag-mock"><span>共 2 条</span><select><option>10 条/页</option><option selected>20 条/页</option></select><span>‹ 1 ›</span></div></div></div>';
    h += '<div class="hint bi0-foot">对标 OPS <code>CustomQuery.vue</code>「我的查询」Tab · <code>dict_query_status</code> · 分页 <code>Pagination.vue</code>。</div>';
    h += '</div>';
    return h;
  }
  const cfgOpen = bi0QueryConfigOpen();
  const cfgCls = cfgOpen ? '' : ' collapsed';
  const cfgBody = cfgOpen ? '' : ' style="display:none"';
  h += '<div class="card bi0-config-card"><div class="bi0-config-hd">';
  h += '<div class="collapse-h' + cfgCls + '" onclick="bi0QueryToggleConfig()"><span class="caret">▼</span><h3>查询配置</h3></div>';
  h += '<div class="rowline"><button class="btn btn-pri btn-sm" onclick="bi0QueryExecute()">执行查询</button><button class="btn btn-sec btn-sm" onclick="bi0QuerySave()">保存为我的查询</button></div></div>';
  h += '<div class="bi0-config-body"' + cfgBody + '>' + bi0QueryBuilderMock(false) + '</div></div>';
  h += bi0QueryResultPanel();
  h += '<div class="hint bi0-foot">布局 SSOT：OPS <code>football-front/.../CustomQuery.vue</code>（配置卡 + 页 Tab 外 <code>QueryResultPanel</code>）· UX-M6 P-M6-013 · 未映射 → 1261 · <span class="btn-txt btn" onclick="go(\'collectMetadata\')">元数据维护</span></div>';
  h += '</div>';
  return h;
}
function bi0QuerySave() {
  openDrawer('保存为我的查询', frow([
    { k: 'name', label: '查询名称', type: 'text', req: true, val: 'IP 组周产出', ph: '1-50 字符' },
    { k: 'status', label: '状态', type: 'select', opts: ['草稿 DRAFT', '已发布 PUBLISHED'] }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'name\']))return;formOk(\'Q-18\',\'查询已保存\');toast(\'POST /ops/query/create\',\'success\');closeDrawer()">确定</button>', '480px');
}
function bi0QueryEditSaved() {
  openDrawer('编辑查询 · IP 组周产出', bi0QueryBuilderMock(true) +
    '<div class="hint" style="margin-top:12px">对标 OPS 编辑弹窗 960px · 内嵌完整 QueryBuilder。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="toast(\'PUT /ops/query/update\',\'success\');closeDrawer()">保存</button>', '720px');
}
function bi0QueryExecuteSaved() {
  state.q.bi0Executed = true;
  state.q.bi0ResultTab = state.q.bi0ResultTab || 'list';
  openDrawer('执行结果 · IP 组周产出', bi0QueryResultPanel() +
    '<div class="hint">对标 OPS 执行弹窗 90% 宽 · QueryResultPanel。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="exportX(this,\'IP组周产出\',2)">导出</button>', '640px');
}
function bi0ScreenPage() {
  const mode = state.tab.bi0Screen || 'config';
  let h = '<div class="tabs"><div class="tab' + (mode === 'config' ? ' on' : '') + '" onclick="bi0ScreenMode(\'config\')">大屏配置 P5b</div>' +
    '<div class="tab' + (mode === 'full' ? ' on' : '') + '" onclick="bi0ScreenMode(\'full\')">全屏预览 P5</div></div>';
  if (mode === 'full') {
    h += '<div class="screen-dark"><div class="rowline" style="justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px">' +
      '<span style="font-size:13px;font-weight:600">经营驾驶舱 · /ims/bi/screen/:id</span>' +
      qs(['全局', '本 IP 组', '本人'], 100) + qi('日期', 100, '2026-09-30') + '<button class="btn btn-sec btn-sm" style="background:#21262d;color:#e6edf3;border-color:#30363d" onclick="toast(\'自动刷新 60s\',\'info\')">刷新</button></div>';
    h += '<div class="g4"><div class="card stat"><span class="l">在线账号</span><div class="n">86</div></div><div class="card stat"><span class="l">今日 GMV</span><div class="n">' + fmtMoney(128640) + '</div></div><div class="card stat"><span class="l">直播场次</span><div class="n">14</div></div><div class="card stat"><span class="l">采集健康</span><div class="n pos">96%</div></div></div>';
    h += '<div class="g2" style="margin-top:12px"><div class="card"><div class="csub">CHART · BUILTIN</div><div style="height:100px;background:rgba(0,113,227,.15);border-radius:8px;margin-top:8px"></div></div>' +
      '<div class="card"><div class="csub">LIST · 已发布 QUERY</div><div style="font-size:12px;margin-top:8px;line-height:1.8">1. 电竞一组 GMV ¥186,400<br>2. 体育二组 GMV ¥412,800</div></div></div></div>';
    h += '<div class="hint">对标 DW <code>biFullscreen</code> · IMS 为 M6 模板非自由画布。</div>';
    return h;
  }
  h += '<div class="g2"><div class="card"><div class="hd-row"><h3 style="font-size:14px">Widget 配置</h3><select style="height:30px;font-size:12px"><option>默认经营模板</option></select></div>' +
    '<div class="dsec">KPI-1</div>' + qs(['BUILTIN', 'METRIC', 'QUERY'], 120) + qs(['builtin_gmv_today', 'play_count', 'IP 组周产出'], 140) +
    '<div class="dsec">图表-1</div>' + qs(['METRIC', 'QUERY', 'BUILTIN'], 120) + qs(['play_count', '—', 'platform_distribution'], 140) +
    '<div class="rowline" style="margin-top:12px"><button class="btn btn-pri btn-sm" onclick="toast(\'配置已保存\',\'success\')">保存</button><button class="btn btn-sec btn-sm" onclick="bi0ScreenMode(\'full\')">预览大屏</button></div></div>';
  h += '<div class="screen-dark"><div class="csub" style="color:#8b949e;margin-bottom:8px">ScreenPreviewPanel · 参数与全屏一致</div>' +
    '<div class="g4"><div class="card stat"><span class="l">KPI</span><div class="n">86</div></div><div class="card stat"><span class="l">GMV</span><div class="n">' + fmtMoney(128640) + '</div></div><div class="card stat"><span class="l">场次</span><div class="n">14</div></div><div class="card stat"><span class="l">健康度</span><div class="n">96%</div></div></div>' +
    '<div style="height:80px;margin-top:10px;border:1px dashed #30363d;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:11px;color:#8b949e">图表 widget 网格</div></div></div>';
  h += '<div class="hint">DC-003 数据可复用 <code>/admin-api/ims/dc/dashboard/*</code> · seed-analytics 非空门槛。</div>';
  return h;
}
function bi0ScreenMode(m) {
  state.tab.bi0Screen = m;
  renderPage();
}
const BI0_REPORTS = [
  { slug: 'unified-account', name: '全平台账号视图' },
  { slug: 'account-status', name: '账号状态监控' },
  { slug: 'video-output', name: '短视频产出统计' },
  { slug: 'live-duration', name: '直播时长统计' },
  { slug: 'cost-allocation', name: '账号成本分摊' },
  { slug: 'roi', name: 'ROI 分析报表' },
  { slug: 'team-config', name: 'IP 团队人员配置' },
  { slug: 'account-alert', name: '账号异常预警' }
];
function bi0OpenReport(slug) {
  const r = BI0_REPORTS.filter(function (x) { return x.slug === slug; })[0];
  const body = qbar(qs(['IP 组', '电竞一组', '体育二组'], 120) + qs(['平台', '抖音', '快手'], 90) + qi('日期范围', 140)) +
    '<div class="g3" style="margin:14px 0"><div class="card stat"><span class="l">汇总 KPI</span><div class="n">128</div></div><div class="card stat"><span class="l">环比</span><div class="n pos">+6.2%</div></div><div class="card stat"><span class="l">明细行</span><div class="n">42</div></div></div>' +
    '<div style="height:100px;background:var(--bg2);border-radius:8px;margin-bottom:12px;display:flex;align-items:center;justify-content:center;color:var(--text2)">图表区（ECharts）</div>' +
    tbl(['维度', '指标 A', '指标 B', '备注'], '<tr><td>示例行</td><td class="num">12,480</td><td class="num">3.2%</td><td>—</td></tr><tr><td>示例行 2</td><td class="num">8,102</td><td class="num">1.8%</td><td>—</td></tr>') +
    '<div class="hint">slug: ' + slug + ' · 与 OPS UX-M6 八张报表同名同布局。</div>';
  openDrawer(r.name, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-pri" onclick="exportX(this,\'' + r.name + '\',42)">导出 Excel</button>', '720px');
}
function bi0Query() {
  go('bi0Query');
  setTab('bi0Query', 'build');
}

/* ===================== 17c 查询工具 QT-001（走查 #18 · FLAT 隐藏 · 交互 demo） ===================== */
const QT_COLLECT_ENTITIES = [
  { code: 'ip_group', label: 'IP 组', table: 'oa_ip_group', mapped: true },
  { code: 'platform_account', label: '平台账号', table: 'oa_platform_account', mapped: true },
  { code: 'live_session', label: '直播场次', table: 'oa_live_session', mapped: true },
  { code: 'content_metric', label: '内容指标', table: 'oa_content_metric', mapped: true },
  { code: 'collect_raw', label: '采集缓冲', table: 'oa_collect_raw_tmp', mapped: false }
];
const QT_ENTITY_FIELDS = {
  ip_group: ['group_name', 'gmv_sum', 'member_cnt'],
  platform_account: ['account_name', 'platform_code', 'status'],
  live_session: ['session_code', 'gmv', 'duration_min'],
  content_metric: ['play_count', 'stat_date'],
  collect_raw: ['batch_id', 'raw_status']
};
const QT_JOIN_OPTS = ['—', 'INNER', 'LEFT', 'RIGHT'];
const QT_RELATION_PRESETS = [
  'group_id → account.ip_group_id',
  'account_id → session.account_id',
  'session_id → fin.session_id',
  'metric_id → session.id'
];
const QT_DRILL_MOCK = {
  ip_group: [{ dim: '电竞一组', val: 128640 }, { dim: '体育二组', val: 412800 }, { dim: '运动精选', val: 61200 }],
  platform_account: [{ dim: '神鱼体育', val: 428600 }, { dim: '跑步研究所', val: 186400 }, { dim: '电竞直播间', val: 96700 }],
  live_session: [{ dim: 'IMS…0131', val: 412800 }, { dim: 'IMS…0138', val: 186400 }, { dim: 'IMS…0127', val: 96700 }],
  content_metric: [{ dim: '2026-09-30', val: 892400 }, { dim: '2026-09-29', val: 764200 }],
  collect_raw: [{ dim: 'batch-0910', val: 0 }]
};
const QT_TRACE_ENTITY_OPTS = [
  { v: 'PERSON', l: '实名人' }, { v: 'IP_GROUP', l: 'IP 组' }, { v: 'ACCOUNT', l: '平台账号' },
  { v: 'ASSET', l: '资产' }, { v: 'SESSION', l: '直播场次' }, { v: 'COST', l: '场次成本' }, { v: 'PROFIT', l: '净利润' }
];
const QT_TRACE_ALL_RELS = [
  { id: 'r_pa', from: 'PERSON', to: 'ACCOUNT', label: '持有账号' },
  { id: 'r_ga', from: 'IP_GROUP', to: 'ACCOUNT', label: '组内账号' },
  { id: 'r_ab', from: 'ACCOUNT', to: 'ASSET', label: '绑定资产' },
  { id: 'r_as', from: 'ACCOUNT', to: 'SESSION', label: '参与场次' },
  { id: 'r_sc', from: 'SESSION', to: 'COST', label: '归集成本' },
  { id: 'r_cp', from: 'COST', to: 'PROFIT', label: '核算利润' },
  { id: 'r_sp', from: 'SESSION', to: 'PROFIT', label: '直算利润（mock）' }
];
const QT_TRACE_RUN_ROWS = {
  PERSON: [{ key: '苏杳', hint: '华东 · 3 账号', nodeId: 'n_person' }],
  IP_GROUP: [{ key: '神鱼体育 IP 组', hint: '42 场/月', nodeId: 'n_acct1' }],
  ACCOUNT: [
    { key: '神鱼体育', hint: 'ACCT-2026-0001 · 抖音', nodeId: 'n_acct1' },
    { key: '跑步研究所', hint: 'ACCT-2026-0002 · 视频号', nodeId: 'n_acct2' }
  ],
  ASSET: [{ key: 'C920 摄像头', hint: 'AS20260901001', nodeId: 'n_asset1' }],
  SESSION: [
    { key: 'IMS202609100DY0131', hint: 'GMV ¥412,800', nodeId: 'sess_131' },
    { key: 'IMS202609110DY0138', hint: 'GMV ¥186,400', nodeId: 'sess_138' }
  ],
  COST: [{ key: '场次成本 FIN-001', hint: '¥249,180', nodeId: 'n_cost' }],
  PROFIT: [{ key: '净利润 FIN-002', hint: '¥163,620', nodeId: 'n_profit' }]
};
function queryToolTraceEntityLabel(code) {
  const o = QT_TRACE_ENTITY_OPTS.filter(function (x) { return x.v === code; })[0];
  return o ? o.l : code;
}
function queryToolTraceRelsFor(fromE, toE) {
  return QT_TRACE_ALL_RELS.filter(function (r) {
    if (toE) return r.from === fromE && r.to === toE;
    return r.from === fromE;
  });
}
function queryToolTraceNextEntity(steps, i) {
  return steps[i + 1] ? steps[i + 1].entity : '';
}
function queryToolEntityLabel(code) {
  const e = QT_COLLECT_ENTITIES.filter(function (x) { return x.code === code; })[0];
  return e ? e.label : code;
}
function queryToolEnsure() {
  if (!state.queryTool) {
    state.queryTool = {
      configOpen: true,
      condOpen: true,
      resultOpen: true,
      hasResult: false,
      queryCostMs: 0,
      templateName: '默认下钻模板',
      drill: {
        levels: [
          { entity: 'ip_group', joinNext: 'INNER', relation: QT_RELATION_PRESETS[0], fields: { group_name: true, gmv_sum: true, member_cnt: false } },
          { entity: 'platform_account', joinNext: 'INNER', relation: QT_RELATION_PRESETS[1], fields: { account_name: true, platform_code: true, status: false } },
          { entity: 'live_session', joinNext: 'LEFT', relation: QT_RELATION_PRESETS[2], fields: { session_code: true, gmv: true, duration_min: false } }
        ],
        activeLevel: 0
      },
      trace: {
        view: 'split',
        filterType: '',
        sourceIdx: null,
        keyword: '',
        pathSteps: [
          { entity: 'PERSON', relationToNext: 'r_pa' },
          { entity: 'ACCOUNT', relationToNext: 'r_as' },
          { entity: 'SESSION', relationToNext: 'r_sc' },
          { entity: 'COST', relationToNext: 'r_cp' },
          { entity: 'PROFIT', relationToNext: '' }
        ],
        runDepth: 0,
        runFocusIdx: 0
      }
    };
  }
  const qt = state.queryTool;
  if (qt.trace && !qt.trace.pathSteps) {
    qt.trace.pathSteps = [
      { entity: 'PERSON', relationToNext: 'r_pa' },
      { entity: 'ACCOUNT', relationToNext: 'r_as' },
      { entity: 'SESSION', relationToNext: 'r_sc' },
      { entity: 'PROFIT', relationToNext: '' }
    ];
    qt.trace.runDepth = 0;
    qt.trace.runFocusIdx = 0;
    delete qt.trace.path;
    delete qt.trace.depth;
    delete qt.trace.focusNodeId;
  }
  if (!qt.templates) {
    qt.templates = [
      { code: 'QT-TPL-001', name: 'IP 组→场次下钻', mode: 'DRILL', status: 'DRAFT', owner: '张 analyst', updatedAt: '2026-09-28 16:40' },
      { code: 'QT-TPL-002', name: '实名人成本 TRACE', mode: 'TRACE', status: 'DRAFT', owner: '张 analyst', updatedAt: '2026-09-27 11:20' },
      { code: 'QT-TPL-003', name: 'IP 组周产出（标准）', mode: 'DRILL', status: 'PUBLISHED', owner: '张 analyst', updatedAt: '2026-09-30 09:12', menuSeed: false },
      { code: 'QT-TPL-004', name: '财务穿透 · 场次成本', mode: 'TRACE', status: 'PUBLISHED', owner: '王 fin', updatedAt: '2026-09-25 14:22', menuSeed: true }
    ];
  }
  if (qt.editingCode == null) qt.editingCode = '';
  return qt;
}
function queryToolMainTab() {
  const v = state.tab.queryToolView || 'config';
  if (v === 'saved' || v === 'published') return 'records';
  return v;
}
function queryToolSetMainTab(t) {
  if (t === 'saved') {
    queryToolEnsure().listStatusFilter = 'DRAFT';
    t = 'records';
  } else if (t === 'published') {
    queryToolEnsure().listStatusFilter = 'PUBLISHED';
    t = 'records';
  }
  state.tab.queryToolView = t;
  renderPage();
}
function queryToolListStatusFilter() {
  const f = queryToolEnsure().listStatusFilter;
  return f === 'DRAFT' || f === 'PUBLISHED' ? f : '';
}
function queryToolSetListStatusFilter(v) {
  queryToolEnsure().listStatusFilter = v === 'DRAFT' || v === 'PUBLISHED' ? v : '';
  renderPage();
}
function queryToolStatusFilterUiValue() {
  const f = queryToolListStatusFilter();
  if (f === 'DRAFT') return '草稿';
  if (f === 'PUBLISHED') return '已发布';
  return '全部';
}
function queryToolSetListStatusFilterFromUi(label) {
  const map = { '全部': '', '草稿': 'DRAFT', '已发布': 'PUBLISHED' };
  queryToolSetListStatusFilter(map[label] || '');
}
function queryToolEnsureTemplates() {
  return queryToolEnsure().templates;
}
function queryToolTemplateByCode(code) {
  return queryToolEnsureTemplates().filter(function (t) { return t.code === code; })[0];
}
function queryToolModeLabelUi(m) {
  return m === 'TRACE' ? tag('TRACE', 'blue') : tag('DRILL', 'purple');
}
function queryToolLoadTemplate(code, silent) {
  const t = queryToolTemplateByCode(code);
  if (!t) return;
  const qt = queryToolEnsure();
  qt.editingCode = code;
  qt.templateName = t.name;
  state.tab.queryToolMode = t.mode === 'TRACE' ? 'trace' : 'drill';
  if (!silent) {
    state.tab.queryToolView = 'config';
    toast('已加载 · ' + t.name + ' → 查询配置', 'success');
    renderPage();
  }
}
function queryToolSaveDraftClick() {
  const qt = queryToolEnsure();
  openDrawer('保存 QueryTemplate 草稿', frow([
    { k: 'name', label: '模板名称', type: 'text', req: true, val: qt.templateName || '未命名模板', ph: '1-50 字符' },
    { k: 'code', label: 'templateCode', type: 'text', val: qt.editingCode || '（保存后生成）', disabled: true }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="queryToolSaveDraftConfirm()">保存草稿</button>', '480px');
}
function queryToolSaveDraftConfirm() {
  if (!formValidate(['name'])) return;
  const name = $('#F_name').value.trim();
  const qt = queryToolEnsure();
  const mode = queryToolMode() === 'trace' ? 'TRACE' : 'DRILL';
  const now = '2026-09-30 18:05';
  const existing = qt.editingCode ? queryToolTemplateByCode(qt.editingCode) : null;
  if (existing && existing.status === 'PUBLISHED') {
    toast('已发布模板请先在「查询记录」取消发布，或新建草稿', 'warn');
    closeDrawer();
    return;
  }
  if (existing && existing.status === 'DRAFT') {
    existing.name = name;
    existing.mode = mode;
    existing.updatedAt = now;
    toast('PUT template/' + existing.code + ' · 草稿已更新', 'success');
  } else {
    const code = 'QT-TPL-' + String(qt.templates.length + 1).padStart(3, '0');
    qt.templates.push({ code: code, name: name, mode: mode, status: 'DRAFT', owner: '张 analyst', updatedAt: now });
    qt.editingCode = code;
    toast('POST template · 草稿 ' + code, 'success');
  }
  qt.templateName = name;
  closeDrawer();
  renderPage();
}
function queryToolPublish(code) {
  const t = queryToolTemplateByCode(code);
  if (!t || t.status !== 'DRAFT') return;
  t.status = 'PUBLISHED';
  t.updatedAt = '2026-09-30 18:08';
  t.menuSeed = false;
  toast('POST template/' + code + '/publish → PUBLISHED', 'success');
  renderPage();
}
function queryToolUnpublish(code) {
  const t = queryToolTemplateByCode(code);
  if (!t || t.status !== 'PUBLISHED') return;
  const finish = function () {
    t.status = 'DRAFT';
    t.menuSeed = false;
    t.updatedAt = '2026-09-30 18:09';
    toast('POST template/' + code + '/unpublish → DRAFT', 'success');
    renderPage();
  };
  if (t.menuSeed) {
    confirmDlg('取消发布', '模板「' + t.name + '」曾标记 MenuSeed 挂 L3（FR-QT-007 仍 P3 BLOCKED）。取消发布后模板回到草稿，不影响现网菜单。', '取消发布', finish, { warn: '仅更新模板态 mock，非真实 MenuSeed 下线。' });
    return;
  }
  finish();
}
function queryToolDelete(code) {
  const t = queryToolTemplateByCode(code);
  if (!t) return;
  confirmDlg('删除 QueryTemplate', '确认删除「' + t.name + '」（' + code + '）？删除后不可恢复。', '删除', function () {
    const qt = queryToolEnsure();
    qt.templates = qt.templates.filter(function (x) { return x.code !== code; });
    if (qt.editingCode === code) { qt.editingCode = ''; qt.templateName = '未命名模板'; }
    toast('DELETE template/' + code, 'success');
    renderPage();
  }, { danger: true });
}
function queryToolExecuteTemplate(code) {
  queryToolLoadTemplate(code, true);
  state.tab.queryToolView = 'config';
  queryToolExecute();
}
function queryToolEditTemplate(code) {
  const t = queryToolTemplateByCode(code);
  if (!t) return;
  queryToolLoadTemplate(code, true);
  const body = (queryToolMode() === 'drill' ? queryToolDrillConfigHtml() : queryToolTraceConfigHtml()) +
    '<div class="hint" style="margin-top:12px">对标 bi0Query 编辑抽屉 720px · 保存走 PUT template/' + code + '（REST BLOCKED）。</div>';
  openDrawer('编辑 QueryTemplate · ' + t.name, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="toast(\'PUT template/' + code + '\',\'success\');closeDrawer()">保存</button>', '720px');
  renderPage();
}
function queryToolRecordsListHtml() {
  const statusF = queryToolListStatusFilter();
  let list = queryToolEnsureTemplates().slice();
  if (statusF) list = list.filter(function (t) { return t.status === statusF; });
  list.sort(function (a, b) { return (b.updatedAt || '').localeCompare(a.updatedAt || ''); });
  let rows = '';
  list.forEach(function (t) {
    const isPub = t.status === 'PUBLISHED';
    let ops = '<span class="btn-txt btn" onclick="queryToolEditTemplate(\'' + t.code + '\')">编辑</span> ';
    if (isPub) ops += '<span class="btn-txt btn" onclick="queryToolUnpublish(\'' + t.code + '\')">取消发布</span> ';
    else ops += '<span class="btn-txt btn" onclick="queryToolPublish(\'' + t.code + '\')">发布</span> ';
    ops += '<span class="btn-txt btn btn-danger-txt" onclick="queryToolDelete(\'' + t.code + '\')">删除</span> ';
    ops += '<span class="btn-txt btn" onclick="queryToolExecuteTemplate(\'' + t.code + '\')">执行</span>';
    const menuCell = isPub
      ? (t.menuSeed ? tag('已挂 L3', 'orange') + ' <span class="csub">数据分析 · P3 BLOCKED</span>' : tag('未挂菜单', 'gray'))
      : '—';
    const stTag = isPub ? tag('已发布', 'green') : tag('草稿', 'gray');
    rows += '<tr><td style="font-weight:500">' + t.name + '</td><td>' + queryToolModeLabelUi(t.mode) + '</td><td>' + stTag + '</td>' +
      '<td class="num">' + t.updatedAt + '</td><td>' + menuCell + '</td><td>' + ops + '</td></tr>';
  });
  if (!rows) rows = '<tr><td colspan="6" class="csub" style="text-align:center;padding:24px">暂无 QueryTemplate · 调整状态筛选或在「查询配置」保存草稿</td></tr>';
  const totalAll = queryToolEnsureTemplates().length;
  const sf = queryToolStatusFilterUiValue();
  const statusSel = '<select style="width:120px" onchange="queryToolSetListStatusFilterFromUi(this.value)">' +
    ['全部', '草稿', '已发布'].map(function (o) { return '<option' + (o === sf ? ' selected' : '') + '>' + o + '</option>'; }).join('') + '</select>';
  let h = '<div class="card bi0-mine-card"><div class="bi0-mine-hd"><div class="hd-row"><h3 style="font-size:17px;font-weight:600;margin:0">QueryTemplate 查询记录</h3><span class="csub">共 ' + list.length + ' 条 · templates[] ' + totalAll + ' 条</span></div></div>';
  h += '<div class="bi0-mine-body">';
  h += qbar(qi('名称', 180) + statusSel + qs(['全部模式', 'DRILL', 'TRACE'], 110), 'toast(\'GET template/page?status=' + (statusF || 'ALL') + '\',\'success\')');
  h += tbl(['查询名称', '模式', '状态', '更新时间', '菜单路径', '操作'], rows);
  h += '<div class="pag-mock"><span>共 ' + list.length + ' 条</span><select><option>10 条/页</option><option selected>20 条/页</option></select><span>‹ 1 ›</span></div></div></div>';
  h += '<div class="hint bi0-foot">单列表 · status=DRAFT|PUBLISHED 为同一 QueryTemplate 记录态 · qbar 状态筛选（非分 Tab）· FR-QT-008~011 · REST BLOCKED §3.1。</div>';
  return h;
}
function queryToolMode() {
  return state.tab.queryToolMode || 'drill';
}
function queryToolSetMode(m) {
  state.tab.queryToolMode = m;
  renderPage();
}
function queryToolResultTab() {
  return state.tab.queryToolResult || 'list';
}
function queryToolSetResultTab(t) {
  state.tab.queryToolResult = t;
  renderPage();
}
function queryToolToggleConfig() {
  queryToolEnsure().configOpen = !queryToolEnsure().configOpen;
  renderPage();
}
function queryToolToggleCond() {
  queryToolEnsure().condOpen = !queryToolEnsure().condOpen;
  renderPage();
}
function queryToolToggleResult() {
  queryToolEnsure().resultOpen = !queryToolEnsure().resultOpen;
  renderPage();
}
function queryToolSetDrillActive(lv) {
  const qt = queryToolEnsure();
  if (lv < 0 || lv >= qt.drill.levels.length) return;
  qt.drill.activeLevel = lv;
  renderPage();
}
function queryToolDrillDown() {
  const qt = queryToolEnsure();
  if (qt.drill.activeLevel < qt.drill.levels.length - 1) {
    qt.drill.activeLevel += 1;
    qt.queryCostMs = 180 + Math.floor(Math.random() * 220);
    renderPage();
  }
}
function queryToolSetDrillEntity(i, code) {
  const qt = queryToolEnsure();
  if (!qt.drill.levels[i]) return;
  qt.drill.levels[i].entity = code;
  const fs = QT_ENTITY_FIELDS[code] || [];
  const nf = {};
  fs.forEach(function (f, j) { nf[f] = j < 2; });
  qt.drill.levels[i].fields = nf;
  renderPage();
}
function queryToolSetDrillJoin(i, join) {
  const qt = queryToolEnsure();
  if (qt.drill.levels[i]) qt.drill.levels[i].joinNext = join;
  renderPage();
}
function queryToolSetDrillRelation(i, rel) {
  const qt = queryToolEnsure();
  if (qt.drill.levels[i]) qt.drill.levels[i].relation = rel;
  renderPage();
}
function queryToolToggleDrillField(li, field) {
  const lv = queryToolEnsure().drill.levels[li];
  if (!lv) return;
  if (!lv.fields) lv.fields = {};
  lv.fields[field] = !lv.fields[field];
  renderPage();
}
function queryToolAddDrillLevel() {
  const qt = queryToolEnsure();
  if (qt.drill.levels.length >= 5) { toast('DrillTemplate 最多 5 层', 'warn'); return; }
  qt.drill.levels.push({ entity: 'content_metric', joinNext: 'LEFT', relation: QT_RELATION_PRESETS[3], fields: { play_count: true, stat_date: true } });
  renderPage();
}
function queryToolRemoveDrillLevel(i) {
  const qt = queryToolEnsure();
  if (qt.drill.levels.length <= 1) { toast('至少保留 1 层', 'warn'); return; }
  qt.drill.levels.splice(i, 1);
  if (qt.drill.activeLevel >= qt.drill.levels.length) qt.drill.activeLevel = qt.drill.levels.length - 1;
  renderPage();
}
function queryToolTraceFilterType(k) {
  queryToolEnsure().trace.filterType = k;
  renderPage();
}
function queryToolTraceSetKeyword(v) {
  queryToolEnsure().trace.keyword = v;
  renderPage();
}
function queryToolTraceSetView(v) {
  queryToolEnsure().trace.view = v;
  renderPage();
}
function queryToolTraceAddPathStep() {
  const tr = queryToolEnsure().trace;
  if (tr.pathSteps.length >= 6) { toast('穿透路径最多 6 层', 'warn'); return; }
  tr.pathSteps.push({ entity: 'SESSION', relationToNext: '' });
  renderPage();
}
function queryToolTraceRemovePathStep(i) {
  const tr = queryToolEnsure().trace;
  if (tr.pathSteps.length <= 2) { toast('至少保留 2 层（根实体 + 末层）', 'warn'); return; }
  tr.pathSteps.splice(i, 1);
  if (tr.runDepth >= tr.pathSteps.length) tr.runDepth = tr.pathSteps.length - 1;
  renderPage();
}
function queryToolTraceSetPathEntity(i, code) {
  const tr = queryToolEnsure().trace;
  if (!tr.pathSteps[i]) return;
  tr.pathSteps[i].entity = code;
  const nextE = queryToolTraceNextEntity(tr.pathSteps, i);
  const rels = queryToolTraceRelsFor(code, nextE);
  if (rels.length === 1) tr.pathSteps[i].relationToNext = rels[0].id;
  else if (rels.every(function (r) { return r.id !== tr.pathSteps[i].relationToNext; })) tr.pathSteps[i].relationToNext = rels[0] ? rels[0].id : '';
  renderPage();
}
function queryToolTraceSetPathRelation(i, relId) {
  const tr = queryToolEnsure().trace;
  if (tr.pathSteps[i]) tr.pathSteps[i].relationToNext = relId;
  renderPage();
}
function queryToolTracePickSource(i) {
  const tr = queryToolEnsure().trace;
  tr.sourceIdx = i;
  tr.runDepth = 0;
  tr.runFocusIdx = 0;
  queryToolEnsure().hasResult = false;
  queryToolEnsure().queryCostMs = 240 + Math.floor(Math.random() * 160);
  renderPage();
}
function queryToolTracePickRow(idx) {
  queryToolEnsure().trace.runFocusIdx = idx;
  renderPage();
}
function queryToolTraceSetRunDepth(d) {
  const tr = queryToolEnsure().trace;
  if (d < 0 || d >= tr.pathSteps.length) return;
  tr.runDepth = d;
  tr.runFocusIdx = 0;
  queryToolTraceRefreshCost();
  renderPage();
}
function queryToolTraceGoNext() {
  const tr = queryToolEnsure().trace;
  const steps = tr.pathSteps;
  if (tr.runDepth >= steps.length - 1) { toast('已在末层', 'info'); return; }
  const relId = steps[tr.runDepth].relationToNext;
  if (!relId) { toast('请先在配置区为本层选择「关联边」', 'warn'); return; }
  tr.runDepth += 1;
  tr.runFocusIdx = 0;
  queryToolTraceRefreshCost();
  renderPage();
}
function queryToolTraceFocusNodeId(tr) {
  const steps = tr.pathSteps;
  const ent = steps[tr.runDepth] ? steps[tr.runDepth].entity : 'ACCOUNT';
  const rows = QT_TRACE_RUN_ROWS[ent] || [];
  const row = rows[tr.runFocusIdx] || rows[0];
  return row && row.nodeId ? row.nodeId : 'n_acct1';
}
function queryToolTraceRefreshCost() {
  queryToolEnsure().queryCostMs = 220 + Math.floor(Math.random() * 200);
}
function queryToolExecute() {
  const qt = queryToolEnsure();
  const mode = queryToolMode();
  if (mode === 'trace') {
    const tr = qt.trace;
    if (tr.sourceIdx == null) { toast('请先选择穿透源头（GET /dc/trace/entry）', 'warn'); return; }
    if (!tr.pathSteps || tr.pathSteps.length < 2) { toast('请配置至少 2 层穿透路径', 'warn'); return; }
    for (var pi = 0; pi < tr.pathSteps.length - 1; pi++) {
      if (!tr.pathSteps[pi].relationToNext) {
        toast('路径 L' + (pi + 1) + ' 缺少至下一层的关联边', 'warn');
        return;
      }
    }
    tr.runDepth = 0;
    tr.runFocusIdx = 0;
    qt.hasResult = true;
    qt.queryCostMs = 280 + Math.floor(Math.random() * 400);
    toast('TracePlan → POST /dc/trace/query · pathSteps=' + tr.pathSteps.length, 'success');
  } else {
    qt.hasResult = true;
    qt.drill.activeLevel = 0;
    qt.queryCostMs = 420 + Math.floor(Math.random() * 680);
    toast('DrillPlan preview · L1~L' + qt.drill.levels.length + ' 已配置', 'success');
  }
  renderPage();
}
function queryToolDrillConfigHtml() {
  const qt = queryToolEnsure();
  const condCls = qt.condOpen ? '' : ' collapsed';
  const condBody = qt.condOpen ? '' : ' style="display:none"';
  const entOpts = QT_COLLECT_ENTITIES.map(function (e) {
    return { v: e.code, l: e.code + ' · ' + e.label + (e.mapped ? ' · 已映射' : ' · 未映射') };
  });
  let rows = '';
  qt.drill.levels.forEach(function (lv, i) {
    const fields = QT_ENTITY_FIELDS[lv.entity] || [];
    let chips = '';
    fields.forEach(function (f) {
      const on = lv.fields && lv.fields[f];
      chips += '<span class="chip field-chip' + (on ? '' : ' off') + '" onclick="queryToolToggleDrillField(' + i + ',\'' + f + '\')">' + f + '</span>';
    });
    const joinSel = i < qt.drill.levels.length - 1
      ? qsvQ(QT_JOIN_OPTS.map(function (j) { return { v: j, l: j === '—' ? '—' : j + ' JOIN' }; }), 108, lv.joinNext, 'queryToolSetDrillJoin(' + i + ',this.value)')
      : '<span class="qb-val-muted">— 末层</span>';
    rows += '<tr><td><span class="chip' + (i === qt.drill.activeLevel ? ' on' : '') + '" style="cursor:pointer" onclick="queryToolSetDrillActive(' + i + ')">L' + (i + 1) + '</span></td>' +
      '<td>' + qsvQ(entOpts, 200, lv.entity, 'queryToolSetDrillEntity(' + i + ',this.value)') + '</td>' +
      '<td>' + joinSel + '</td>' +
      '<td>' + qsvQ(QT_RELATION_PRESETS.map(function (r) { return { v: r, l: r }; }), 240, lv.relation, 'queryToolSetDrillRelation(' + i + ',this.value)') + '</td>' +
      '<td><div class="qb-chips">' + chips + '</div></td>' +
      '<td><span class="btn-txt btn btn-danger-txt" onclick="queryToolRemoveDrillLevel(' + i + ')">移除</span></td></tr>';
  });
  let h = '<div class="dsec" style="margin-top:0;padding-top:0;border-top:none">DrillTemplate · levels[]</div>';
  h += '<div class="qt-drill-levels tbl-wrap"><table><colgroup><col style="width:52px"><col style="width:24%"><col style="width:112px"><col style="width:28%"><col><col style="width:52px"></colgroup><thead><tr><th>层</th><th>实体（COLLECT）</th><th>Join 至下一层</th><th>关联键</th><th>展示列</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>';
  h += '<div class="rowline" style="margin-top:10px;flex-wrap:wrap;gap:8px"><button class="btn btn-sec btn-sm" onclick="queryToolAddDrillLevel()">+ 添加层级</button>' +
    '<span class="csub">已配置 ' + qt.drill.levels.length + ' / 5 层 · 点击 L 标签切换结果预览层</span></div>';
  h += '<div class="bi0-qb-root qb-layout" style="margin-top:16px"><div class="qb-form">';
  h += '<div class="qb-cond-hd"><div class="collapse-h' + condCls + '" onclick="queryToolToggleCond()"><span class="caret">▼</span><b>根层过滤条件</b></div></div>';
  h += '<div class="qb-cond-body"' + condBody + '><div class="tbl-wrap"><table><thead><tr><th>字段</th><th>运算符</th><th>值</th><th></th></tr></thead><tbody>' +
    '<tr><td class="mono">stat_date</td><td>BETWEEN</td><td class="num">2026-09-01 ~ 2026-09-30</td><td><span class="btn-txt btn btn-danger-txt" onclick="toast(\'已移除条件\',\'info\')">删除</span></td></tr></tbody></table></div>' +
    '<button class="btn btn-sec btn-sm qb-cond-add" onclick="toast(\'+ 添加条件\',\'info\')">+ 添加条件</button></div>';
  h += '<div class="dsec">Join 预览</div><div class="qt-join-arrow">';
  qt.drill.levels.forEach(function (lv, i) {
    if (i) h += '<span class="csub"> ' + (qt.drill.levels[i - 1].joinNext === '—' ? '→' : qt.drill.levels[i - 1].joinNext + ' → ') + ' </span>';
    h += '<span class="chip">' + queryToolEntityLabel(lv.entity) + '</span>';
  });
  h += '</div></div><div class="qb-side"><div class="qb-side-hd">COLLECT 字段池</div><div class="csub">只读 · entity/{code}/fields</div>';
  (QT_ENTITY_FIELDS[qt.drill.levels[0].entity] || []).forEach(function (f) {
    h += '<div class="fi" onclick="toast(\'已加入 L1 展示列 ' + f + '\',\'success\')">' + f + '</div>';
  });
  h += '<div class="hint" style="margin-top:8px">1261 未映射 → <span class="btn-txt btn" onclick="go(\'collectMetadata\')">元数据维护</span></div></div></div>';
  return h;
}
function queryToolTracePathPreview(tr) {
  let chain = '';
  tr.pathSteps.forEach(function (step, i) {
    if (i) chain += ' <span class="csub">—</span> ';
    const rel = step.relationToNext;
    const relObj = rel ? QT_TRACE_ALL_RELS.filter(function (r) { return r.id === rel; })[0] : null;
    chain += '<span class="chip">' + queryToolTraceEntityLabel(step.entity) + '</span>';
    if (relObj && i < tr.pathSteps.length - 1) {
      chain += ' <span class="csub">via ' + relObj.label + ' →</span> ';
    }
  });
  return chain;
}
function queryToolTraceConfigHtml() {
  const qt = queryToolEnsure();
  const tr = qt.trace;
  let h = '<div class="dsec" style="margin-top:0;padding-top:0;border-top:none">TraceTemplate · pathSteps[]（配置穿透链）</div>';
  h += '<div class="qt-trace-path"><div class="tbl-wrap"><table><thead><tr><th>层</th><th>实体 / 表（mock 目录）</th><th>关联边 → 下一层</th><th>下一层</th><th></th></tr></thead><tbody>';
  tr.pathSteps.forEach(function (step, i) {
    const nextE = queryToolTraceNextEntity(tr.pathSteps, i);
    const relOpts = queryToolTraceRelsFor(step.entity, nextE).map(function (r) { return { v: r.id, l: r.label + ' · ' + queryToolTraceEntityLabel(r.to) }; });
    const relCell = i < tr.pathSteps.length - 1
      ? (relOpts.length ? qsvQ(relOpts, 200, step.relationToNext, 'queryToolTraceSetPathRelation(' + i + ',this.value)') : '<span class="qb-val-muted">无可用边 · 调整实体</span>')
      : '<span class="qb-val-muted">— 末层</span>';
    h += '<tr><td><span class="chip">L' + (i + 1) + '</span></td>' +
      '<td>' + qsvQ(QT_TRACE_ENTITY_OPTS, 160, step.entity, 'queryToolTraceSetPathEntity(' + i + ',this.value)') + '</td>' +
      '<td>' + relCell + '</td>' +
      '<td class="csub">' + (nextE ? queryToolTraceEntityLabel(nextE) : '—') + '</td>' +
      '<td><span class="btn-txt btn btn-danger-txt" onclick="queryToolTraceRemovePathStep(' + i + ')">移除</span></td></tr>';
  });
  h += '</tbody></table></div>';
  h += '<div class="rowline" style="margin-top:10px;flex-wrap:wrap;gap:8px"><button class="btn btn-sec btn-sm" onclick="queryToolTraceAddPathStep()">+ 添加穿透层</button>' +
    '<span class="csub">共 ' + tr.pathSteps.length + ' 层 · depth 由 pathSteps 推导（非固定 depth 下拉）</span></div>';
  h += '<div class="qt-trace-chain" style="margin-top:12px"><b>路径预览：</b> ' + queryToolTracePathPreview(tr) + '</div></div>';
  h += '<div class="dsec">② 根层入口 · GET /dc/trace/entry</div>';
  h += '<div class="qb-form"><div class="qb-row"><label>入口类型</label><div class="qb-chips">';
  DC_ENTRY_TYPES.forEach(function (t) {
    const on = tr.filterType === t.k;
    h += '<span class="chip' + (on ? ' on' : '') + '" style="cursor:pointer" onclick="queryToolTraceFilterType(\'' + t.k + '\')">' + t.l + '</span>';
  });
  if (tr.filterType) h += '<span class="chip pp" style="cursor:pointer" onclick="queryToolTraceFilterType(\'\')">全部</span>';
  h += '</div></div>';
  h += '<div class="qb-row"><label>关键词</label>' +
    qi('entryId / 姓名 / 标签', 220, tr.keyword).replace('<input ', '<input id="qtTraceKw" class="qt-qctl" ') +
    '<button class="btn btn-sec btn-sm" onclick="queryToolTraceSetKeyword(document.getElementById(\'qtTraceKw\').value)">筛选</button></div></div>';
  h += '<div class="tbl-wrap"><table><thead><tr><th>类型</th><th>标签</th><th>提示</th><th>操作</th></tr></thead><tbody>';
  DC_SOURCES.forEach(function (s, i) {
    if (tr.filterType && s.entryType !== tr.filterType) return;
    if (tr.keyword && s.entryLabel.indexOf(tr.keyword) < 0 && s.entryId.indexOf(tr.keyword) < 0) return;
    const sel = tr.sourceIdx === i;
    h += '<tr' + (sel ? ' style="background:var(--blue-bg)"' : '') + '><td>' + tag(s.entryType, 'blue') + '</td><td style="font-weight:500">' + s.entryLabel + '</td><td class="csub">' + s.hint + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="queryToolTracePickSource(' + i + ')">' + (sel ? '已选源头' : '设为源头') + '</span></td></tr>';
  });
  h += '</tbody></table></div>';
  if (tr.sourceIdx == null) {
    h += '<div class="qt-result-empty" style="margin-top:14px">配置 pathSteps[] 并选择根层源头后，点击「执行查询」在下方 QueryResultPanel 逐层穿透。</div>';
  } else if (!qt.hasResult) {
    h += '<div class="hint" style="margin-top:12px">已选源头 · ' + DC_SOURCES[tr.sourceIdx].entryLabel + ' · 执行后将从 L1「' + queryToolTraceEntityLabel(tr.pathSteps[0].entity) + '」开始按关联链下钻。</div>';
  } else {
    h += '<div class="hint" style="margin-top:12px">运行态见下方 <b>QueryResultPanel</b> · queryCostMs ' + (qt.queryCostMs || '—') + 'ms</div>';
  }
  h += '<div class="hint">全屏 DC → <span class="btn-txt btn" onclick="go(\'dc\')">穿透查询 L3</span></div>';
  return h;
}
function queryToolTraceRunBody(tr) {
  if (tr.sourceIdx == null) return '';
  const src = DC_SOURCES[tr.sourceIdx];
  const steps = tr.pathSteps;
  const depth = tr.runDepth;
  const curStep = steps[depth];
  const atLast = depth >= steps.length - 1;
  const rows = QT_TRACE_RUN_ROWS[curStep.entity] || [];
  let h = '<div class="qt-trace-run">';
  h += '<div class="qt-level-steps"><span class="csub">路径</span>';
  h += '<span class="chip" style="cursor:pointer" onclick="queryToolTraceSetRunDepth(0)">源头 · ' + src.entryLabel + '</span>';
  steps.forEach(function (step, i) {
    h += '<span class="csub">›</span>';
    if (i > 0) {
      const prevRel = steps[i - 1].relationToNext;
      const ro = prevRel ? QT_TRACE_ALL_RELS.filter(function (r) { return r.id === prevRel; })[0] : null;
      if (ro) h += '<span class="csub" style="font-size:10px">' + ro.label + '</span><span class="csub">›</span>';
    }
    h += '<span class="chip' + (i === depth ? ' on' : '') + '" style="cursor:pointer" onclick="queryToolTraceSetRunDepth(' + i + ')">L' + (i + 1) + ' · ' + queryToolTraceEntityLabel(step.entity) + '</span>';
  });
  h += '</div>';
  h += '<div class="rowline" style="justify-content:space-between;flex-wrap:wrap;margin:8px 0 10px">' +
    '<span class="csub">运行 · 选中行后「下一层」按 pathSteps[' + depth + '].relationToNext 穿透</span>' +
    '<div class="rowline">' +
    '<button class="btn btn-sec btn-sm' + (tr.view === 'split' ? ' btn-pri' : '') + '" onclick="queryToolTraceSetView(\'split\')">分栏</button>' +
    '<button class="btn btn-sec btn-sm' + (tr.view === 'graph' ? ' btn-pri' : '') + '" onclick="queryToolTraceSetView(\'graph\')">关系图</button>' +
    '<button class="btn btn-sec btn-sm' + (tr.view === 'list' ? ' btn-pri' : '') + '" onclick="queryToolTraceSetView(\'list\')">明细表</button></div></div>';
  if (!atLast) {
    let tbody = '';
    rows.forEach(function (r, idx) {
      const sel = tr.runFocusIdx === idx;
      tbody += '<tr' + (sel ? ' style="background:var(--blue-bg);cursor:pointer"' : ' style="cursor:pointer"') + ' onclick="queryToolTracePickRow(' + idx + ')"><td style="font-weight:500">' + r.key + '</td><td class="csub">' + r.hint + '</td><td>' + (sel ? tag('当前焦点', 'blue') : '—') + '</td></tr>';
    });
    h += '<div class="tbl-wrap"><table><thead><tr><th>' + queryToolTraceEntityLabel(curStep.entity) + '</th><th>提示</th><th></th></tr></thead><tbody>' + tbody + '</tbody></table></div>';
    const relObj = QT_TRACE_ALL_RELS.filter(function (r) { return r.id === curStep.relationToNext; })[0];
    h += '<div class="rowline" style="margin:10px 0"><button class="btn btn-pri btn-sm" onclick="queryToolTraceGoNext()">下一层 · ' + (relObj ? relObj.label + ' → ' + queryToolTraceEntityLabel(steps[depth + 1].entity) : '—') + '</button></div>';
  }
  const focusId = queryToolTraceFocusNodeId(tr);
  const splitCls = 'dc-trace-split' + (tr.view === 'graph' ? ' single-graph' : tr.view === 'list' ? ' single-list' : '');
  h += '<div class="' + splitCls + '">';
  if (tr.view !== 'list') {
    h += '<div class="card dc-graph-panel">' + dcTraceGraphSvg(dcTraceGraphPack(focusId), focusId) + '</div>';
  }
  if (tr.view !== 'graph') {
    h += '<div class="card dc-list-panel"><div class="dsec" style="margin:12px 12px 0">DC mock 明细 · focus ' + focusId + '</div><div style="padding:0 12px 12px">' +
      dcTraceListHtml(focusId) + '</div></div>';
  }
  h += '</div></div>';
  return h;
}
function queryToolTraceFinalRows(tr) {
  const last = tr.pathSteps[tr.pathSteps.length - 1];
  const rows = QT_TRACE_RUN_ROWS[last.entity] || QT_TRACE_RUN_ROWS.PROFIT;
  return rows.map(function (r) {
    return '<tr><td style="font-weight:500">' + r.key + '</td><td class="csub">' + r.hint + '</td><td class="num">' + (last.entity === 'PROFIT' ? '163,620' : '—') + '</td></tr>';
  }).join('');
}
function queryToolDrillResultRows(entity) {
  const rows = QT_DRILL_MOCK[entity] || QT_DRILL_MOCK.ip_group;
  return rows.map(function (r) {
    return '<tr><td style="font-weight:500">' + r.dim + '</td><td class="num">' + fmtMoney(r.val) + '</td><td class="csub">' + entity + '</td></tr>';
  }).join('');
}
function queryToolDrillChartHtml(entity) {
  const rows = QT_DRILL_MOCK[entity] || [];
  const max = rows.reduce(function (m, r) { return Math.max(m, r.val); }, 1);
  let bars = '<div class="bi0-chart-ph" style="display:block;padding:12px 16px 8px;height:auto;min-height:160px"><div class="bars qt-drill-chart-bars" style="height:120px">';
  rows.forEach(function (r) {
    const pct = Math.round((r.val / max) * 100);
    bars += '<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:4px"><div class="b" style="height:' + pct + '%;width:100%"></div><span class="csub" style="font-size:10px;text-align:center">' + r.dim + '</span></div>';
  });
  return bars + '</div></div>';
}
function queryToolResultPanel() {
  const qt = queryToolEnsure();
  if (!qt.hasResult) return '';
  const rt = queryToolResultTab();
  const mode = queryToolMode();
  const costCls = qt.queryCostMs > 3000 ? ' style="color:var(--orange);font-weight:600"' : '';
  const rOpen = qt.resultOpen;
  const rCls = rOpen ? '' : ' collapsed';
  const rBody = rOpen ? '' : ' style="display:none"';
  let h = '<div class="card bi0-result-card">';
  h += '<div class="hd-row bi0-result-hd"><div class="collapse-h' + rCls + '" onclick="queryToolToggleResult()"><span class="caret">▼</span><b>查询条件</b></div>' +
    '<span class="hint"' + costCls + '>queryCostMs · ' + (qt.queryCostMs || '—') + 'ms</span></div>';
  if (mode === 'drill') {
    const lv0 = qt.drill.levels[0];
    h += '<div class="desc-grid bi0-result-cond"' + rBody + '>' +
      '<span class="dk">模式</span><span class="dv">DRILL · DrillTemplate</span><span class="dk">层级</span><span class="dv">' + qt.drill.levels.length + ' 层</span>' +
      '<span class="dk">根实体</span><span class="dv">' + queryToolEntityLabel(lv0 ? lv0.entity : 'ip_group') + '</span><span class="dk">当前层</span><span class="dv">L' + (qt.drill.activeLevel + 1) + '</span></div>';
  } else {
    const tr = qt.trace;
    const src = tr.sourceIdx != null ? DC_SOURCES[tr.sourceIdx] : null;
    h += '<div class="desc-grid bi0-result-cond"' + rBody + '>' +
      '<span class="dk">模式</span><span class="dv">TRACE · TraceTemplate</span><span class="dk">pathSteps</span><span class="dv">' + tr.pathSteps.length + ' 层</span>' +
      '<span class="dk">根源头</span><span class="dv">' + (src ? src.entryLabel : '—') + '</span><span class="dk">运行深度</span><span class="dv">L' + (tr.runDepth + 1) + ' / ' + tr.pathSteps.length + '</span></div>';
  }
  h += '<div class="hd-row"><h3 style="font-size:15px;font-weight:600;margin:0">查询结果</h3><span class="csub">' + (mode === 'drill' ? 'DrillPlan mock' : 'TracePlan mock') + '</span></div>';
  h += '<div' + rBody + '>';
  if (mode === 'drill') {
    const lv = qt.drill.activeLevel;
    const cur = qt.drill.levels[lv];
    const ent = cur ? cur.entity : 'ip_group';
    h += '<div class="qt-level-steps"><span class="csub">面包屑</span>';
    qt.drill.levels.forEach(function (l, i) {
      h += '<span class="csub">›</span><span class="chip' + (i === lv ? ' on' : '') + '" onclick="queryToolSetDrillActive(' + i + ')">L' + (i + 1) + ' · ' + queryToolEntityLabel(l.entity) + '</span>';
    });
    h += '</div>';
    if (lv < qt.drill.levels.length - 1) {
      h += '<div class="rowline" style="margin-bottom:10px"><button class="btn btn-sec btn-sm" onclick="queryToolDrillDown()">下钻到 L' + (lv + 2) + ' · ' + queryToolEntityLabel(qt.drill.levels[lv + 1].entity) + '</button></div>';
    }
    h += '<div class="tabs bi0-result-tabs"><div class="tab' + (rt === 'list' ? ' on' : '') + '" onclick="queryToolSetResultTab(\'list\')">结果列表</div>' +
      '<div class="tab' + (rt === 'chart' ? ' on' : '') + '" onclick="queryToolSetResultTab(\'chart\')">图表展示</div></div>';
    if (rt === 'list') {
      h += tbl(['维度', '指标', '实体'], queryToolDrillResultRows(ent));
      h += '<div class="pag-mock"><span>共 ' + (QT_DRILL_MOCK[ent] || []).length + ' 条 · L' + (lv + 1) + '</span></div>';
    } else {
      h += '<div class="bi0-chart-bar">' + qs(['柱状图', '折线图'], 100) + qs(['X · dim', 'stat_date'], 140) + '<span class="csub">' + queryToolEntityLabel(ent) + '</span></div>';
      h += queryToolDrillChartHtml(ent);
    }
  } else if (qt.trace.sourceIdx != null) {
    const tr = qt.trace;
    const atLast = tr.runDepth >= tr.pathSteps.length - 1;
    h += queryToolTraceRunBody(tr);
    if (atLast) {
      h += '<div class="tabs bi0-result-tabs" style="margin-top:14px"><div class="tab' + (rt === 'list' ? ' on' : '') + '" onclick="queryToolSetResultTab(\'list\')">末层结果</div>' +
        '<div class="tab' + (rt === 'chart' ? ' on' : '') + '" onclick="queryToolSetResultTab(\'chart\')">图表展示</div></div>';
      if (rt === 'list') {
        h += tbl(['末层对象', '说明', '指标'], queryToolTraceFinalRows(tr));
        h += '<div class="pag-mock"><span>穿透完成 · pathSteps[' + (tr.pathSteps.length - 1) + ']</span></div>';
      } else {
        h += '<div class="bi0-chart-bar">' + qs(['柱状图', '折线图'], 100) + '</div><div class="bi0-chart-ph">ECharts · 末层 ' + queryToolTraceEntityLabel(tr.pathSteps[tr.pathSteps.length - 1].entity) + '</div>';
      }
    } else {
      h += '<div class="hint" style="margin-top:8px">未到末层 · 选中上表行后点击「下一层」继续穿透</div>';
    }
  }
  h += '</div></div>';
  return h;
}
function queryToolPage() {
  const main = queryToolMainTab();
  let h = '<div class="page-bi0-query page-query-tool">';
  h += '<div class="tabs"><div class="tab' + (main === 'config' ? ' on' : '') + '" onclick="queryToolSetMainTab(\'config\')">查询配置</div>' +
    '<div class="tab' + (main === 'records' ? ' on' : '') + '" onclick="queryToolSetMainTab(\'records\')">查询记录</div></div>';
  if (main === 'records') {
    h += queryToolRecordsListHtml();
    h += '</div>';
    return h;
  }
  const qt = queryToolEnsure();
  const mode = queryToolMode();
  const cfgOpen = qt.configOpen;
  const cfgCls = cfgOpen ? '' : ' collapsed';
  const cfgBody = cfgOpen ? '' : ' style="display:none"';
  h += '<div class="tabs mode-tabs"><div class="tab' + (mode === 'drill' ? ' on' : '') + '" onclick="queryToolSetMode(\'drill\')">分级下钻 DRILL</div>' +
    '<div class="tab' + (mode === 'trace' ? ' on' : '') + '" onclick="queryToolSetMode(\'trace\')">穿透 TRACE</div></div>';
  h += '<div class="card bi0-config-card qt-config-card"><div class="bi0-config-hd">';
  h += '<div class="collapse-h' + cfgCls + '" onclick="queryToolToggleConfig()"><span class="caret">▼</span><h3>查询配置 · ' + (mode === 'drill' ? 'DrillTemplate' : 'TraceTemplate') + '</h3></div>';
  h += '<div class="rowline"><span class="csub">' + (qt.editingCode ? '编辑 ' + qt.editingCode : '新建草稿') + '</span>' +
    '<button class="btn btn-pri btn-sm" onclick="queryToolExecute()">执行查询</button>' +
    '<button class="btn btn-sec btn-sm" onclick="queryToolSaveDraftClick()">保存草稿</button>' +
    '<button class="btn btn-sec btn-sm" onclick="toast(\'MenuSeed · FR-QT-007 P3 BLOCKED\',\'warn\')">发布为菜单</button></div></div>';
  h += '<div class="bi0-config-body"' + cfgBody + '>';
  h += mode === 'drill' ? queryToolDrillConfigHtml() : queryToolTraceConfigHtml();
  h += '</div></div>';
  if (qt.hasResult) h += queryToolResultPanel();
  else {
    h += '<div class="qt-result-empty">' + (mode === 'drill'
      ? '配置 Drill levels[] 与根层条件后点击「执行查询」，QueryResultPanel 展示面包屑、下钻与列表/图表 Tab。'
      : '配置 pathSteps[] 穿透链、选择根层源头后点击「执行查询」，在 QueryResultPanel 逐层选行并「下一层」直至末层。') + '</div>';
  }
  h += '<div class="hint bi0-foot">P0 隐藏 FLAT · 自定义查询 <span class="btn-txt btn" onclick="go(\'bi0Query\')">/ims/bi/query</span> · FR-QT-001~011 · 模板闭环 mock（REST BLOCKED）</div></div>';
  return h;
}
PAGES.queryTool = function () {
  return pgHead('queryTool',
    '<button class="btn btn-sec btn-sm" onclick="go(\'collectMetadata\')">元数据维护</button>' +
    '<button class="btn btn-sec btn-sm" onclick="go(\'dc\')">穿透查询 L3</button>') + queryToolPage();
};
function bi0MetaAdd() {
  openDrawer('元数据实体', frow([
    { k: 'tbl', label: '物理表', type: 'select', req: true, opts: ['oa_ip_group', 'oa_platform_account', 'oa_collect_raw_tmp'] },
    { k: 'code', label: '实体编码', type: 'text', req: true, val: 'ip_group' },
    { k: 'cond', label: '查询条件类别', type: 'select', opts: ['文本', '字典', '日期', '账号选择器', 'IP 组树'] }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'code\']))return;formOk(\'META-01\',\'实体已映射，字段已导入\');toast(\'已保存字段配置\',\'success\')">保存字段配置</button>', '520px');
}

const MKT_PLANS = [
  { no: 'MP-01', name: '九月电竞赛事', sop: '电竞赛事集锦 SOP', st: '进行中' },
  { no: 'MP-02', name: '秋季跑鞋矩阵', sop: '跑鞋测评短视频 SOP', st: '进行中' }
];
const OPS_PLANS = [
  { no: 'PL-220', name: '电竞一组 · W38', sop: '电竞赛事集锦 SOP', st: '执行中' },
  { no: 'PL-218', name: '体育二组 · 知识周', sop: '跑步知识科普 SOP', st: '待开始' }
];
const OPS_TASKS = [
  { no: 'TK-881', plan: 'PL-220', node: '内容生成', owner: '孙倩', gate: '待提交审核', st: '进行中', cid: '8821', wt: 'WT-0917' },
  { no: 'TK-882', plan: 'PL-220', node: '拍摄', owner: '赵敏', gate: '通过', st: '待开始', cid: '', wt: '' }
];
const WT_ROWS = [
  { no: 'WT-0918', ipg: '电竞一组', play: '竞彩', live: '是 20:00', st: '待确认' },
  { no: 'WT-0917', ipg: '体育二组', play: '图文种草', live: '否', st: '已出任务' }
];
const OPS_CONTENTS = [
  { id: '8821', title: '今晚焦点场', play: '竞彩 / 待确定玩法', sync: '—', st: '草稿', taskId: 'TK-881' },
  { id: '8819', title: '秋季跑鞋横评', play: '测评 / —', sync: '成功', st: '待审', taskId: '' }
];
function contentMktTab() {
  let rows = '';
  MKT_PLANS.forEach(function (p) {
    rows += '<tr><td class="mono">' + p.no + '</td><td style="font-weight:500">' + p.name + '</td><td>' + p.sop + '</td><td>' + tag(p.st, 'green') + '</td>' +
      '<td><span class="btn-txt btn" onclick="mktPlanAdd()">编辑</span></td></tr>';
  });
  return qbar(qi('计划名称', 140)) + tbl(['编号', '营销计划', '绑定 SOP', '状态', '操作'], rows);
}
function mktPlanAdd() {
  openDrawer('营销计划', frow([
    { k: 'name', label: '名称', type: 'text', req: true },
    { k: 'sop', label: '绑定 SOP', type: 'select', opts: SOPS.map(function (s) { return s.name; }) }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="if(!formValidate([\'name\']))return;formOk(\'MP-03\',\'营销计划已绑定 SOP（CONTENT-101）\');toast(\'已保存\',\'success\')">保存</button>', '480px');
}
function contentPlanTab() {
  let rows = '';
  OPS_PLANS.forEach(function (p) {
    rows += '<tr><td class="mono">' + p.no + '</td><td>' + p.name + '</td><td>' + p.sop + '</td><td>' + tag(p.st, p.st === '执行中' ? 'blue' : 'gray') + '</td></tr>';
  });
  return qbar(qi('计划', 140) + qs(['全部状态', '执行中', '待开始'])) + tbl(['计划编号', '名称', 'SOP', '状态'], rows);
}
function opsPlanAdd() { toast('新建计划 · 绑定 SOP 与 IP 组（选择器）', 'success'); }
function contentTaskTab(mode) {
  mode = mode || '我的任务';
  let rows = '';
  OPS_TASKS.forEach(function (t, idx) {
    if (mode === '我的任务' && t.owner !== ROLES[state.role].user && state.role !== 'R1') return;
    rows += '<tr><td class="mono">' + t.no + '</td><td>' + t.plan + '</td><td>' + t.node + '</td><td>' + t.owner + '</td>' +
      '<td>' + tag(t.gate, t.gate === '通过' ? 'green' : 'orange') + '</td><td>' + tag(t.st, 'blue') + '</td>' +
      '<td>' + (t.cid ? '<button class="btn btn-pri btn-sm" onclick="taskExec(' + idx + ')">执行</button> <span class="btn-txt btn" onclick="go(\'contentList\');opsContentEdit(' + OPS_CONTENTS.findIndex(function (c) { return c.id === t.cid; }) + ')">内容 ' + t.cid + '</span>' : '—') + '</td></tr>';
  });
  return '<div class="hint" style="margin-bottom:8px">UX P-M2-003：默认「我的任务」· 内容生成节点 → 任务执行页 / 内容抽屉（taskId）</div>' +
    qbar(qi('任务号', 120) + (mode === '全部任务' ? qi('执行人', 90) : '')) + tbl(['任务', '计划', '节点', '负责人', '完成门禁', '状态', '操作'], rows || '<tr><td colspan="7" style="color:var(--text2)">暂无任务</td></tr>') +
    '<div class="hint">完成门禁 ADR-079：内容须审核通过方可完成节点；非内容生成须工作说明。</div>';
}
function taskExec(idx) {
  const t = OPS_TASKS[idx];
  const ci = OPS_CONTENTS.findIndex(function (c) { return c.taskId === t.no || c.id === t.cid; });
  opsContentEdit(ci >= 0 ? ci : -1, t.no);
}
function contentWtTab() {
  const authors = ['孙倩', '赵敏', '王野'];
  const matches = ['英超 · 曼城 vs 利物浦', '西甲 · 巴萨 vs 皇马', '德甲 · 拜仁 vs 多特'];
  let matrix = '<div class="card" style="margin-bottom:14px;padding:12px 14px"><div class="rowline" style="justify-content:space-between;margin-bottom:8px"><b style="font-size:13px">作者 × 赛事矩阵（FR-M2-010）</b><span class="csub">勾选单元格 · 合并执行组 · 确认出任务</span></div><div class="tbl-wrap"><table><thead><tr><th>作者 \\ 赛事</th>';
  matches.forEach(function (m) { matrix += '<th style="white-space:normal;max-width:120px">' + m + '</th>'; });
  matrix += '</tr></thead><tbody>';
  authors.forEach(function (a, ai) {
    matrix += '<tr><td style="font-weight:500">' + a + '</td>';
    matches.forEach(function (m, mi) {
      const on = ai === 0 && mi === 0;
      matrix += '<td><span class="sw' + (on ? ' on' : '') + '" onclick="var was=this.classList.contains(\'on\');this.classList.toggle(\'on\');toast(\'矩阵格已\'+(was?\'取消\':\'选中\'),\'success\')"><i></i></span></td>';
    });
    matrix += '</tr>';
  });
  matrix += '</tbody></table></div></div>';
  let rows = '';
  WT_ROWS.forEach(function (w, i) {
    rows += '<tr><td class="mono">' + w.no + '</td><td>' + w.ipg + '</td><td>' + w.play + '</td><td>' + w.live + '</td>' +
      '<td>' + tag(w.st, w.st === '待确认' ? 'orange' : 'green') + '</td>' +
      '<td>' + (w.st === '待确认' ? '<button class="btn btn-pri btn-sm" onclick="wtConfirm(' + i + ')">确认出任务</button> <span class="btn btn-sec btn-sm" onclick="wtRevoke(' + i + ')">撤回</span>' :
        '<span class="btn-txt btn">详情</span>') + '</td></tr>';
  });
  return matrix + qbar(qi('工作任务', 140) + qs(['全部状态', '待确认', '已出任务'])) + tbl(['编号', 'IP 组', '玩法', '直播', '状态', '操作'], rows) +
    '<div class="hint">确认后出 SOP 任务；参数 work.task.confirm.auto-ai-generate 控制竞彩是否入队 AI。撤回将删除 IMS 内草稿并取消任务（CONTENT-110）。</div>';
}
function wtAdd() {
  openDrawer('登记工作任务', frow([
    { k: 'ipg', label: 'IP 组', type: 'select', req: true, opts: ['请选择', '电竞一组', '体育二组'] },
    { k: 'plan', label: '营销计划', type: 'select', opts: ['请选择', '九月电竞赛事', '秋季跑鞋矩阵'] },
    { k: 'match', label: '赛事（可多选示意）', type: 'text', ph: '从赛程 WebAPI 选择，禁止手输非法 ID' },
    { k: 'live', label: '是否直播', type: 'pills', opts: ['是', '否'], val: '是' },
    { k: 'tm', label: '直播时间', type: 'dt' },
    { k: 'play', label: '玩法', type: 'select', opts: ['竞彩', '图文种草', '测评'] }
  ]),
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="formOk(\'WT-0928\',\'工作任务已登记，待确认出任务\');toast(\'已登记\',\'success\')">提交</button>');
}
function wtConfirm(i) {
  confirmDlg('确认出任务', '将按 SOP 生成任务。竞彩玩法是否自动入队 AI 由系统参数 work.task.confirm.auto-ai-generate 决定（当前 false）。', '确认', function () {
    WT_ROWS[i].st = '已出任务';
    const tk = 'TK-' + (880 + OPS_TASKS.length);
    const cid = String(8820 + OPS_CONTENTS.length + 1);
    OPS_TASKS.unshift({ no: tk, plan: WT_ROWS[i].no, node: '内容生成', owner: '孙倩', gate: '待提交审核', st: '进行中', cid: cid, wt: WT_ROWS[i].no });
    OPS_CONTENTS.unshift({ id: cid, title: WT_ROWS[i].play + ' · ' + WT_ROWS[i].ipg, play: '竞彩 / 待确定玩法', sync: '—', st: '草稿', taskId: tk });
    toast('已出任务 ' + tk + ' · 内容草稿 ' + cid, 'success');
    renderPage();
  });
}
function wtRevoke(i) {
  confirmDlg('撤回工作任务', '将删除 IMS 内自动草稿并取消已生成任务。若已同步 Football 方案，将走 WebAPI 删除/下架（CONTENT-110）。', '撤回', function () {
    toast('已撤回 ' + WT_ROWS[i].no, 'success');
  }, { danger: true, warn: '此操作不可恢复草稿内容' });
}
function contentOpsLibTab() {
  let rows = '';
  OPS_CONTENTS.forEach(function (c, i) {
    rows += '<tr><td class="mono">' + c.id + '</td><td style="font-weight:500">' + c.title + '</td><td>' + c.play + '</td>' +
      '<td>' + tag(c.sync, c.sync === '成功' ? 'green' : c.sync === '补偿中' ? 'orange' : 'red') + '</td><td>' + tag(c.st, c.st === '草稿' ? 'gray' : 'blue') + '</td>' +
      '<td><span class="btn btn-pri btn-sm" onclick="opsContentEdit(' + i + ')">编辑</span> <span class="btn btn-sec btn-sm" style="color:var(--red)" onclick="opsContentDel(' + i + ')">删除</span></td></tr>';
  });
  return qbar(qi('标题 / ID', 150) + qs(['全部状态', '草稿', '待审', '已发布'])) + tbl(['内容 ID', '标题', '玩法 / matchScheme', 'Football 同步', '状态', '操作'], rows) +
    '<div class="hint">保存成功即 200；Football HTTP 失败写 outbox，不回滚 IMS（CONTENT-109）。</div>';
}
function opsContentEdit(i, taskId) {
  const c = i < 0 ? { title: '', play: '竞彩 / 待确定玩法', taskId: taskId || '' } : OPS_CONTENTS[i];
  const banner = c.taskId ? '<div class="hint" style="margin-bottom:10px">工作任务 · 任务 ' + c.taskId + ' · 玩法区对齐 amphipoda（竞足/传足/北单 Tab）</div>' : '';
  const playTabs = '<div class="tabs" style="margin:8px 0"><div class="tab on">竞足</div><div class="tab">传足</div><div class="tab">北单</div><div class="tab">足球</div></div><div class="hint">选赛程 → 确定玩法 → 写入 matchScheme / matchPlays</div>';
  openDrawer(i < 0 ? '新建内容' : '编辑内容 · ' + c.id, banner + frow([
    { k: 'title', label: '标题', type: 'text', req: true, val: c.title },
    { k: 'body', label: '正文（付费/免费）', type: 'textarea', ph: 'RichText 区 · 侧栏版式', wide: true }
  ]) + playTabs + '<div class="rowline" style="gap:8px;margin-top:8px;flex-wrap:wrap">' +
    '<button class="btn btn-sec btn-sm" onclick="toast(\'AI 内容生成（jingcai 参数控制）\',\'success\')">AI 内容</button>' +
    '<button class="btn btn-sec btn-sm" onclick="toast(\'AI 排版 preview/apply\',\'success\')">AI 排版</button>' +
    '<button class="btn btn-sec btn-sm" style="background:rgba(175,82,218,.12);color:var(--purple);border-color:rgba(175,82,218,.35)" onclick="aiVideoScriptDrawer(' + i + ')">' + ic('spark', 14) + 'AI 视频脚本</button>' +
    '<button class="btn btn-sec btn-sm" style="background:rgba(175,82,218,.12);color:var(--purple);border-color:rgba(175,82,218,.35)" onclick="aiVideoGenDrawer(' + i + ')">' + ic('video', 14) + 'AI 视频生成</button></div>' +
    '<div class="hint">短视频 SOP 节点内完成脚本与成片；非独立 ComfyUI 13 Tab 主路径。IR-02：Football 同步仅 HTTP WebAPI。</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-sec" onclick="if(!formValidate([\'title\']))return;toast(\'已保存草稿\',\'success\')">保存</button><button class="btn btn-pri" onclick="opsContentSubmitReview(' + (i < 0 ? -1 : i) + ')">提交审核</button>');
}
function aiVideoScriptDrawer(idx) {
  const body = frow([
    { k: 'm8', label: 'AI 模型（M8 已启用）', type: 'select', req: true, opts: ['Football AI · 默认', 'GPT-4o · 备用'] },
    { k: 'prompt', label: '提示词模板', type: 'select', req: true, opts: ['短视频分镜 · 15/30/60s', '赛事解说口播', '测评钩子开场'] },
    { k: 'ctx', label: '上下文（赛事/玩法/matchScheme）', type: 'textarea', ph: '自动带入内容玩法区已选赛程与方案摘要', wide: true },
    { k: 'dur', label: '目标时长', type: 'pills', opts: ['15s', '30s', '60s'], val: '30s' }
  ]) + '<div class="hint">SOP 节点「视频脚本 / 短视频文案」专用 · 生成结果写入脚本引用区（SHORT_VIDEO）。</div>';
  openDrawer('AI 视频脚本生成', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" style="background:var(--purple)" onclick="toast(\'脚本已写入内容 · 可人工润色后保存\',\'success\');closeDrawer()">生成并写入</button>', '560px');
}
function aiVideoGenDrawer(idx) {
  const body = frow([
    { k: 'script', label: '挂接定稿脚本', type: 'select', req: true, opts: ['使用当前内容脚本区', 'SOP 节点短视频文案 N4'] },
    { k: 'wf', label: '视频生成流程（SOP 内）', type: 'select', req: true, opts: ['标准短视频 · 口播+素材', '赛事集锦 · 自动切片', '数字人混剪（需 GPU 队列）'] },
    { k: 'm8v', label: '视频模型/服务', type: 'select', opts: ['M8 视频服务', 'ComfyUI 队列（旁路）'] },
    { k: 'note', label: '补充要求', type: 'textarea', ph: '画幅 9:16 · 字幕样式 · 品牌露出', wide: true }
  ]) + '<div class="card" style="margin-top:10px;box-shadow:none;border:1px dashed var(--line2);padding:16px;text-align:center;color:var(--text2)">' + ic('video', 22) + '<div style="font-size:12px;margin-top:6px">生成进度 · aiGenerateStatus QUEUED/GENERATING/FAILED（ADR-077）</div></div>';
  openDrawer('AI 视频生成', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" style="background:var(--purple)" onclick="toast(\'已入队生成 · 完成后写入 finalVideoUrl\',\'success\');closeDrawer()">提交生成</button>', '600px');
}
function opsContentSubmitReview(i) {
  if (i < 0) { toast('请先保存内容', 'warn'); return; }
  OPS_CONTENTS[i].st = '待审';
  closeDrawer();
  toast('已提交审核 · 请在「内容审核」处理 ' + OPS_CONTENTS[i].id, 'success');
  go('contentReview');
}
function opsContentDel(i) {
  confirmDlg('删除内容', '草稿将调用 Football WebAPI 删除或下架。失败进入补偿队列，IMS 侧按产品规则标记删除。', '删除', function () {
    toast('已删除 ' + OPS_CONTENTS[i].id + ' · 同步下架已入队', 'success');
  }, { danger: true, warn: 'CONTENT-110' });
}
function contentLayoutTab() {
  return '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">' +
    ['公推模板 A', '公推模板 B', '竞彩版式', '测评版式'].map(function (n) {
      return '<div class="card hov" onclick="toast(\'套用「' + n + '」· AI 语义排版抽屉\',\'success\')"><div style="height:88px;border-radius:8px;background:linear-gradient(135deg,#e8f2fe,#d6e7f8);margin-bottom:10px"></div><b>' + n + '</b><div class="csub">CONTENT-107</div></div>';
    }).join('') + '</div>';
}
function contentKbTab() {
  return qbar(qi('知识标题', 160) + qs(['全部分类', '话术', '合规', '玩法'])) +
    tbl(['标题', '分类', '更新', '操作'], '<tr><td>竞彩话术红线</td><td>合规</td><td class="num">2026-09-20</td><td><span class="btn-txt btn" onclick="toast(\'知识库详情\',\'success\')">查看</span></td></tr>');
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
