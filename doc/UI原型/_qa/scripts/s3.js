
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
/* ---- TRAIN P1：培训资料库（岗位 → 类别 · TRAIN-001） ---- */
const TRAIN_POS = [
  { code: 'POS_HOST', name: '主播组', cnt: 12 },
  { code: 'POS_LIVE_OPS', name: '直播运营', cnt: 8 },
  { code: 'POS_CONTENT', name: '内容中心', cnt: 15 },
  { code: 'POS_ALL', name: '全员通用', cnt: 6 }
];
const TRAIN_MATS = [
  { no: 'MT20260918-301', title: '开播规范手册 V3.2', tp: 'DOC', ver: 3, pos: ['POS_HOST', 'POS_ALL'], st: '已发布', uploader: '赵敏', upd: '2026-09-18' },
  { no: 'MT20260917-302', title: '直播间违规红线案例集', tp: 'DOC', ver: 2, pos: ['POS_ALL'], st: '已发布', uploader: '林岚', upd: '2026-09-17' },
  { no: 'MT20260916-303', title: '开场话术与留存技巧（视频）', tp: 'VIDEO', ver: 2, pos: ['POS_HOST'], st: '已发布', uploader: '苏杳', upd: '2026-09-16' },
  { no: 'MT20260915-304', title: '平台违规判例 9 月更新', tp: 'LINK', ver: 1, pos: ['POS_LIVE_OPS', 'POS_HOST'], st: '已发布', uploader: '何舟', upd: '2026-09-15' },
  { no: 'MT20260914-305', title: '短视频脚本结构模板', tp: 'DOC', ver: 4, pos: ['POS_CONTENT'], st: '已发布', uploader: '孙倩', upd: '2026-09-14' },
  { no: 'MT20260912-306', title: '报销制度宣导（草稿）', tp: 'DOC', ver: 1, pos: ['POS_ALL'], st: '草稿', uploader: '周晴', upd: '2026-09-12' }
];
function trainMatPosLabel(codes) {
  return (codes || []).map(function (c) {
    const p = TRAIN_POS.find(function (x) { return x.code === c; });
    return p ? p.name : c;
  }).join('、');
}
function trainMaterialPage() {
  const sel = state.tab.trainMatPos || 'POS_HOST';
  let h = pgHead('trainMaterial', '<button class="btn btn-sec" onclick="exportX(this,\'培训资料\',TRAIN_MATS.length)">导出</button>' +
    '<button class="btn btn-pri" onclick="trainMatUpload()">' + ic('plus', 15) + '上传资料</button>');
  h += '<div class="g4"><div class="card stat"><span class="l">本周应更新</span><div class="n">41</div><div class="d">BR-101</div></div>' +
    '<div class="card stat"><span class="l">已更新</span><div class="n" style="color:var(--green)">39</div></div>' +
    '<div class="card stat"><span class="l">周更新率</span><div class="n" style="color:var(--yellow)">95.1%</div><div class="d"><span class="btn-txt btn-sm" onclick="trainMatUnupdated()">未更新清单</span></div></div>' +
    '<div class="card stat"><span class="l">岗位维度</span><div class="n" style="font-size:22px">' + TRAIN_POS.length + '</div><div class="d">AUTH-003 · dict_position</div></div></div>';
  h += '<div class="rowline" style="align-items:flex-start;gap:14px;margin-top:12px">';
  h += '<div style="width:220px;flex:none;border:1px solid var(--line2);border-radius:var(--r-m);padding:8px 0;background:var(--card)">';
  TRAIN_POS.forEach(function (p) {
    h += '<div class="nav-item sub' + (sel === p.code ? ' active' : '') + '" style="margin:0 6px;border-radius:8px" onclick="state.tab.trainMatPos=\'' + p.code + '\';renderPage()">' +
      '<span style="flex:1">' + p.name + '</span><span class="csub">' + p.cnt + '</span></div>';
  });
  h += '</div><div style="flex:1;min-width:0">';
  h += qbar(qi('标题', 130) + qs(['全部类型', 'DOC', 'VIDEO', 'LINK'], 100) + qs(['全部状态', '已发布', '草稿', '已下架'], 100));
  const list = TRAIN_MATS.filter(function (m) { return m.pos.indexOf(sel) >= 0 || sel === 'POS_ALL'; });
  let rows = '';
  list.forEach(function (m) {
    const gi = TRAIN_MATS.indexOf(m);
    const stc = { '已发布': 'green', '草稿': 'gray', '已下架': 'red' };
    rows += '<tr><td class="mono" style="color:var(--blue);cursor:pointer" onclick="trainMatDetail(' + gi + ')">' + m.no + '</td><td style="font-weight:500">' + m.title + '</td>' +
      '<td>' + tag(m.tp, 'cyan') + '</td><td>V' + m.ver + '</td><td style="font-size:12px">' + trainMatPosLabel(m.pos) + '</td>' +
      '<td>' + tag(m.st, stc[m.st]) + '</td><td>' + sens(m.uploader) + '</td><td class="num" style="font-size:12px">' + m.upd + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="trainMatDetail(' + gi + ')">详情</span></td></tr>';
  });
  h += tbl(['资料编号', '标题', '类型', '版本', '关联岗位', '状态', '更新人', '更新时间', '操作'], rows);
  h += '<div class="hint">GET ' + TRAIN_ROUTE.trainMaterial + '/list · positionCode 来自岗位模板 · 学员仅见已发布（TRN-M-R1）。</div></div></div>';
  return h;
}
PAGES.trainMaterial = trainMaterialPage;
function trainMatFind(no) {
  return TRAIN_MATS.find(function (m) { return m.no === no; });
}
function trainPublishedMats() {
  return TRAIN_MATS.filter(function (m) { return m.st === '已发布'; });
}
function trainMatUpload(editNo) {
  const em = editNo ? trainMatFind(editNo) : null;
  state.trainMatEdit = editNo || null;
  openDrawer(em ? '编辑资料（新版本）' : '上传资料', frow([
    { k: 'mtitle', label: '标题', type: 'text', req: true, ph: '≤128 字', val: em ? em.title : '' },
    { k: 'mtype', label: '类型', type: 'select', opts: ['DOC', 'VIDEO', 'LINK'], val: em ? em.tp : 'DOC' },
    { k: 'mpos', label: '关联岗位', type: 'select', req: true, opts: TRAIN_POS.map(function (p) { return p.name + ' (' + p.code + ')'; }), val: em && em.pos[0] ? (function () { const p = TRAIN_POS.find(function (x) { return x.code === em.pos[0]; }); return p ? p.name + ' (' + p.code + ')' : ''; })() : '' }
  ]), '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-sec" onclick="trainMatSave(false)">存草稿</button><button class="btn btn-pri" onclick="trainMatSave(true)">发布</button>', '640px');
}
function trainMatSave(publish) {
  if (!formValidate(['mtitle'])) return;
  const title = $('#F_mtitle').value.trim();
  const tp = $('#F_mtype').value || 'DOC';
  const posRaw = $('#F_mpos').value || '';
  const m = posRaw.match(/\(([A-Z_0-9]+)\)/);
  const posCode = m ? m[1] : 'POS_ALL';
  const today = '2026-09-30';
  if (state.trainMatEdit) {
    const old = trainMatFind(state.trainMatEdit);
    if (old) {
      old.title = title; old.tp = tp; old.pos = [posCode]; old.ver += 1; old.st = publish ? '已发布' : '草稿'; old.upd = today;
      closeDrawer();
      if (state.page === 'trainMaterial') renderPage();
      toast((publish ? '已发布 · PUT /train/material/' : '已存草稿 · ') + old.no, 'success');
      return;
    }
  }
  const no = 'MT20260930-' + String(300 + TRAIN_MATS.length + 1);
  TRAIN_MATS.unshift({ no: no, title: title, tp: tp, ver: 1, pos: [posCode], st: publish ? '已发布' : '草稿', uploader: state.role.user || '当前用户', upd: today });
  closeDrawer();
  if (state.page === 'trainMaterial') renderPage();
  toast((publish ? '已发布 · POST /train/material · 学员可见' : '已存草稿 · POST /train/material'), 'success');
}
function trainMatDetail(i) {
  const m = TRAIN_MATS[i];
  if (m) trainMatDetailByNo(m.no);
}
function trainMatDetailByNo(no) {
  const m = trainMatFind(no);
  if (!m) return;
  const stc = { '已发布': 'green', '草稿': 'gray', '已下架': 'red' };
  openDrawer('资料 · ' + m.title,
    '<div class="kv"><div><div class="k">编号</div><div class="v mono">' + m.no + '</div></div><div><div class="k">状态</div><div class="v">' + tag(m.st, stc[m.st]) + '</div></div><div><div class="k">岗位</div><div class="v">' + trainMatPosLabel(m.pos) + '</div></div><div><div class="k">版本</div><div class="v">V' + m.ver + ' · 旧版留档 TRN-M-R2</div></div></div><div class="hint">预览区：OSS 签名 URL 60s · LINK 外链跳转 · source=AI_DRAFT 仅 QUIZ 审计字段</div>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
    (m.st !== '已下架' ? '<button class="btn btn-sec" onclick="trainMatUpload(\'' + m.no + '\')">编辑（新版本）</button>' : '') +
    (m.st === '已发布' ? '<button class="btn btn-sec" style="color:var(--red)" onclick="trainMatOffline(\'' + m.no + '\')">下架</button>' : ''), '560px');
}
function trainMatOffline(no) {
  const m = trainMatFind(no);
  if (!m) return;
  confirmDlg('确认下架？', '资料「' + m.title + '」下架后学员不可见；关联任务仍保留历史引用。', '下架', function () {
    m.st = '已下架';
    closeDrawer();
    if (state.page === 'trainMaterial') renderPage();
    toast('DELETE /train/material/' + m.no + ' · 已下架', 'success');
  });
}
function trainMatUnupdated() {
  openDrawer('未更新清单（BR-101）', '<table class="tb"><thead><tr><th>编号</th><th>标题</th><th>负责人</th><th>最后更新</th></tr></thead><tbody><tr><td class="mono">MT20260912-306</td><td>报销制度宣导（草稿）</td><td>周晴</td><td>2026-09-12</td></tr></tbody></table>',
    '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button><button class="btn btn-sec btn-sm" onclick="toast(\'清单已复制\',\'success\')">复制清单</button>', '640px');
}
PAGES.trainTask = function () {
  let h = pgHead('trainTask', '<button class="btn btn-sec" onclick="trainAiQuizOpen()">' + ic('spark', 15) + 'AI 生成试卷</button>' +
    '<button class="btn btn-pri" onclick="taskAdd()">' + ic('plus', 15) + '下达学习任务</button>');
  h += trainTaskTab();
  return h;
};
PAGES.trainStat = function () {
  let h = pgHead('trainStat', '<button class="btn btn-sec" onclick="exportX(this,\'培训完成率\',1)">导出逾期清单</button>');
  h += '<div class="g3"><div class="card stat"><span class="l">总完成率</span><div class="n" style="color:var(--green)">92.4%</div><div class="d">BR-102 目标 &gt;90%</div></div>' +
    '<div class="card stat"><span class="l">逾期未完成</span><div class="n" style="color:var(--red)">7</div></div>' +
    '<div class="card stat"><span class="l">统计截至</span><div class="n" style="font-size:18px">2026-09-28</div><div class="d">TRN-S-R1 日汇总</div></div></div>';
  h += '<div class="tabs" style="margin-top:14px">' + ['完成率总览', '部门统计', '逾期督办'].map(function (t, i) {
    return '<div class="tab' + (i === 0 ? ' on' : '') + '" onclick="toast(\'Tab：' + t + ' · GET /train/stat\',\'success\')">' + t + '</div>';
  }).join('') + '</div>';
  h += '<div class="hint" style="margin-top:12px">P3 培训统计看板 · 完整图表见《TRAIN-培训管理-页面规格》P3。</div>';
  return h;
};
PAGES.train = trainMaterialPage;
/* ---- TRAIN P2：学习任务（ConfirmType = DURATION / QUIZ） ---- */
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
    '<span style="font-size:12px;color:var(--text2);line-height:1.6">资料须从 <b style="color:var(--text)">培训资料库</b> 多选关联；QUIZ 可用 <b style="color:var(--text)">AI 生成试卷</b>（TRAIN-004 · ADR-004 BLOCKED）。确认方式：<b>DURATION</b> 学时达标 / <b>QUIZ</b> 自测判分。完成率三色阈值 BR-102。</span></div>';
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
  if (state.page === 'trainTask') renderPage();
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
function trainMatPickHtml(idPrefix, preSel) {
  preSel = preSel || {};
  return trainPublishedMats().map(function (m, i) {
    const posLbl = trainMatPosLabel(m.pos);
    const tpLbl = m.tp === 'DOC' ? '文档' : m.tp === 'VIDEO' ? '视频' : '外链';
    return '<label style="display:flex;align-items:center;gap:9px;padding:7px 2px;border-bottom:1px solid var(--line);font-size:12.5px;cursor:pointer">' +
      '<input type="checkbox" name="' + idPrefix + '" value="' + i + '"' + (preSel[i] ? ' checked' : '') + ' style="accent-color:var(--blue)">' +
      '<span class="mono" style="color:var(--text2);font-size:11px">' + m.no + '</span><span style="flex:1">' + m.title + '</span>' +
      '<span style="color:var(--text2);font-size:11px">' + tpLbl + ' · V' + m.ver + ' · ' + posLbl + '</span></label>';
  }).join('');
}
/* TRAIN-004：AI 生成试卷向导（Mock · ADR-IMS-004 BLOCKED） */
function trainAiQuizOpen(reopenTaskAfter) {
  const preSel = {};
  if (reopenTaskAfter) {
    document.querySelectorAll('#tmats input:checked').forEach(function (inp) {
      preSel[inp.value] = true;
    });
  }
  state.aiQuiz = { step: 1, sel: preSel, reopenTaskAfter: !!reopenTaskAfter, pass: 80, count: 10, diff: '中等' };
  trainAiQuizRender();
}
function trainAiQuizToggleMat(i) {
  if (!state.aiQuiz) return;
  state.aiQuiz.sel[i] = !state.aiQuiz.sel[i];
}
function trainAiQuizRender() {
  const st = state.aiQuiz;
  if (!st) return;
  const steps = ['① 选择资料', '② 生成参数', '③ AI 生成中', '④ 预览采纳'];
  let body = '<div class="wiz-steps">' + steps.map(function (lbl, n) {
    const s = n + 1;
    let cls = 'ws';
    if (st.step === s) cls += ' on';
    else if (st.step > s) cls += ' done';
    return '<div class="' + cls + '">' + lbl + '</div>';
  }).join('') + '</div><div class="hint" style="margin:-6px 0 12px">TRAIN-004 · API <b style="color:var(--orange)">BLOCKED</b>（ADR-IMS-004）· AIR Mock · 无 REST</div>';
  if (st.step === 1) {
    body += '<div class="fld wide"><label>已发布资料（多选）<i class="req">*</i></label><div style="max-height:200px;overflow:auto;border:1px solid var(--line2);border-radius:var(--r-s);padding:4px 10px">' +
      trainPublishedMats().map(function (m, i) {
        return '<label style="display:flex;align-items:center;gap:9px;padding:7px 2px;border-bottom:1px solid var(--line);font-size:12.5px;cursor:pointer">' +
          '<input type="checkbox"' + (st.sel[i] ? ' checked' : '') + ' onchange="trainAiQuizToggleMat(' + i + ')" style="accent-color:var(--blue)">' +
          '<span style="flex:1">' + m.title + '</span><span class="csub">' + m.no + '</span></label>';
      }).join('') + '</div></div>';
  } else if (st.step === 2) {
    body += frow([
      { k: 'aiCount', label: '题量', type: 'select', opts: ['5', '10', '15', '20'], val: String(st.count) },
      { k: 'aiDiff', label: '难度', type: 'pills', opts: ['基础', '中等', '进阶'], val: st.diff },
      { k: 'aiPass', label: '建议及格分', type: 'num', val: st.pass, min: 1, max: 100 }
    ]) + '<div class="hint">题型：单选 + 判断（开放问题 Q2 · 简答不进自动判分）</div>';
  } else if (st.step === 3) {
    body += '<div style="text-align:center;padding:36px 12px"><div class="n" style="font-size:15px;font-weight:600;margin-bottom:8px">' + ic('spark', 22) + ' 正在解析资料并出题…</div>' +
      '<div class="pg" style="width:220px;margin:12px auto;height:6px"><i id="aiQuizBar" style="width:8%;background:var(--blue)"></i></div>' +
      '<div class="csub">Mock：无 POST /train/... · 约 2 秒</div></div>';
  } else {
    const draft = st.draft || [];
    body += '<div class="hint" style="margin-bottom:8px">预览 ' + draft.length + ' 题 · 采纳后写入 QUIZ 编辑器（可再手工改）</div>';
    draft.forEach(function (it, n) {
      body += '<div class="qz-item" style="padding:10px 0;border-bottom:1px solid var(--line)"><b style="font-size:13px">' + (n + 1) + '. ' + it.q + '</b><div class="csub" style="margin-top:4px">答案：' + 'ABCD'[it.ans] + ' · ' + it.opts[it.ans] + '</div></div>';
    });
  }
  let foot = '<button class="btn btn-sec" onclick="closeDrawer()">取消</button>';
  if (st.step === 1) foot += '<button class="btn btn-pri" onclick="trainAiQuizNext1()">下一步</button>';
  else if (st.step === 2) foot += '<button class="btn btn-sec" onclick="state.aiQuiz.step=1;trainAiQuizRender()">上一步</button><button class="btn btn-pri" onclick="trainAiQuizRun()">开始生成</button>';
  else if (st.step === 3) foot += '';
  else foot += '<button class="btn btn-sec" onclick="state.aiQuiz.step=2;trainAiQuizRender()">重新生成</button><button class="btn btn-pri" onclick="trainAiQuizAdopt()">采纳到问卷</button>';
  openDrawer('AI 生成培训试卷 · 步骤 ' + st.step + '/4', body, foot, '720px');
  if (st.step === 3) trainAiQuizSimProgress();
}
function trainAiQuizNext1() {
  const picked = Object.keys(state.aiQuiz.sel).filter(function (k) { return state.aiQuiz.sel[k]; });
  if (!picked.length) { toast('请至少选择 1 份已发布资料', 'warn'); return; }
  state.aiQuiz.step = 2;
  trainAiQuizRender();
}
function trainAiQuizRun() {
  state.aiQuiz.count = Number($('#F_aiCount') ? $('#F_aiCount').value : state.aiQuiz.count) || 10;
  state.aiQuiz.diff = ($('#F_aiDiff') && $('#F_aiDiff').value) ? $('#F_aiDiff').value : state.aiQuiz.diff;
  state.aiQuiz.pass = Number($('#F_aiPass') ? $('#F_aiPass').value : state.aiQuiz.pass) || 80;
  state.aiQuiz.step = 3;
  trainAiQuizRender();
}
function trainAiQuizSimProgress() {
  let w = 8;
  const bar = document.getElementById('aiQuizBar');
  const t = setInterval(function () {
    w += 18;
    if (bar) bar.style.width = Math.min(w, 100) + '%';
    if (w >= 100) {
      clearInterval(t);
      const n = Math.min(20, Math.max(5, state.aiQuiz.count || 10));
      const tpl = [
        { q: '根据所选资料：开播前必须完成的合规检查包括？', opts: ['仅检查网络', '实名、禁词预案、商品资质', '只确认灯光', '无需检查'], ans: 1 },
        { q: '直播间出现用户引导私下交易时，正确做法是？', opts: ['同意并留微信', '忽略', '话术引导回平台并上报', '下播处理'], ans: 2 },
        { q: '「痛点前置」脚本结构的核心顺序是？', opts: ['品牌-参数-价格', '痛点-方案-证明-行动', '随机发挥', '先报价'], ans: 1 },
        { q: '判断：拖拽快进仍计入有效观看学时。（TRN-T-R1）', opts: ['正确', '错误'], ans: 1 }
      ];
      state.aiQuiz.draft = [];
      for (let i = 0; i < n; i++) state.aiQuiz.draft.push(JSON.parse(JSON.stringify(tpl[i % tpl.length])));
      state.aiQuiz.step = 4;
      trainAiQuizRender();
    }
  }, 400);
}
function trainAiQuizApplyPrefill() {
  const draft = state.qzEdPrefill || [];
  const qzRadio = document.querySelector('input[name="P_ct2"][value="自测问卷"]');
  if (qzRadio) { qzRadio.checked = true; ctSel(qzRadio); }
  state.qzEd = draft.map(function (it) { return { q: it.q, opts: it.opts.slice(), ans: it.ans }; });
  if ($('#F_pass') && state.qzEdPassPrefill != null) $('#F_pass').value = state.qzEdPassPrefill;
  renderQuizEd();
}
function trainAiQuizAdopt() {
  const draft = (state.aiQuiz && state.aiQuiz.draft) || [];
  if (!draft.length) { toast('无草稿可采纳', 'warn'); return; }
  state.qzEdPrefill = draft.map(function (it) { return { q: it.q, opts: it.opts.slice(), ans: it.ans }; });
  state.qzEdPassPrefill = state.aiQuiz.pass || 80;
  const inTaskForm = !!document.getElementById('quizEd');
  closeDrawer();
  toast('已采纳 ' + draft.length + ' 题（source=AI_DRAFT · Mock）', 'success');
  if (inTaskForm) {
    trainAiQuizApplyPrefill();
    return;
  }
  taskAdd();
  setTimeout(trainAiQuizApplyPrefill, 80);
}
function taskAdd() {
  const body = '<div style="padding:2px 4px">' +
    frow([
      { k: 'title', label: '任务名称', type: 'text', req: true, ph: '如：新主播开播规范 · 学习任务（≤128 字）' },
      { k: 'scope', label: '指派范围', type: 'pills', req: true, val: '按人', opts: ['按人', '按岗位'] },
      { k: 'deadline', label: '截止时间', type: 'dt', req: true, val: '2026-10-02T18:00', hint: '不得早于当前时间（1102 拦截）' }
    ]) +
    '<div class="fld wide"><label>学习资料（多选，仅已发布资料）<i class="req">*</i></label>' +
    '<div id="tmats" style="max-height:150px;overflow:auto;border:1px solid var(--line2);border-radius:var(--r-s);padding:4px 10px">' +
    trainMatPickHtml('tmats') + '</div><div class="ferr" id="E_mats"></div></div>' +
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
    '<div class="rowline" style="margin-bottom:10px;flex-wrap:wrap;gap:8px"><button type="button" class="btn btn-sec btn-sm" onclick="trainAiQuizOpen(true)">' + ic('spark', 14) + 'AI 生成试卷</button><span class="csub">TRAIN-004 向导 · API BLOCKED · 采纳后填充下方编辑器</span></div>' +
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
    if (state.page === 'trainTask') renderPage();
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
    if (state.page === 'trainTask') renderPage();
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
  if (state.page === 'trainTask') renderPage();
  formOk(no, '培训已创建，进入「报名中」状态并开放报名', '');
  toast('培训创建成功：' + no, 'success');
}

/* ===================== 03 MEET 会议 ===================== */
const MEETS = [
  { id: 'MT20260912-03', topic: '秋季大促直播动员会', org: '何舟', time: '今天 16:00', dur: '1.5h', room: '3F-大会议室', ppl: 12, min: '待生成' },
  { id: 'MT20260912-02', topic: '跑鞋新品选品评审', org: '何舟', time: '今天 10:00', dur: '1h', room: '2F-会议室 A', ppl: 8, min: 'AI 转写中' },
  { id: 'MT20260911-05', topic: '周度经营复盘会', org: 'Donny', time: '昨天 19:00', dur: '2h', room: '3F-大会议室', ppl: 15, min: '已生成', minBody: '一、GMV 复盘：本周 GMV ¥412.8 万，环比 +18.6%，抖音贡献 58%。二、问题：退货率升至 6.1%（上周 4.8%），尺码问题占 42%。三、决议事项见右侧清单。', decisions: [{ d: '退货率专项：尺码描述模板本周内修订，责任：孙倩', due: '09-15' }, { d: '斗鱼场次排期增至每周 3 场，责任：赵敏', due: '09-18' }] },
  { id: 'MT20260911-04', topic: '短视频选题周会', org: '孙倩', time: '昨天 14:00', dur: '1h', room: '线上（钉闪会）', ppl: 6, min: '已生成', minBody: '本周选题通过 12 个，重点方向：秋季跑步装备测评（4 条）、马拉松备赛（3 条）、大促预热（5 条）。AI 脚本生成效率提升 30%。', decisions: [{ d: '大促预热 5 条提前至 09-16 发布', due: '09-16' }] },
  { id: 'MT20260910-08', topic: '财务月度结算对齐', org: '周晴', time: '09-10 15:00', dur: '1.5h', room: '2F-会议室 B', ppl: 5, min: '已生成', minBody: '8 月结算全部完成，利润双口径核对无差异。9 月结算时效目标：场次结束后 5 日内完成。', decisions: [{ d: '超 5 日未结算场次自动预警，责任：周晴', due: '09-20' }] },
  { id: 'MT20260910-07', topic: '主播排期协调会', org: '赵敏', time: '09-10 09:30', dur: '0.5h', room: '线上（钉闪会）', ppl: 9, min: '待生成' },
  { id: 'MT20260909-11', topic: '竞品数据月度分析', org: '陈默', time: '09-09 16:00', dur: '1h', room: '3F-培训室', ppl: 7, min: '已生成', minBody: '竞品互动率前三：帕梅拉 5.8%、刘畊宏 6.2%、悦跑圈 5.4%。刘畊宏流量连续 30 天下滑，建议降低监控优先级。', decisions: [] },
  { id: 'MT20260908-02', topic: '资产盘点启动会', org: '林岚', time: '09-08 10:00', dur: '1h', room: '2F-会议室 A', ppl: 10, min: '已归档', minBody: '9 月中旬资产盘点：范围 128 件在册资产，责任人 34 人，盘点周期 5 天。', decisions: [] },
  { id: 'MT20260907-01', topic: '外协合作协议评审', org: 'Donny', time: '09-07 14:00', dur: '1h', room: '2F-会议室 B', ppl: 4, min: '已生成', minBody: '外协协议 V2 条款评审：分成比例由固定 20% 调整为阶梯制，法务需复核终止条款。', decisions: [{ d: '法务复核终止条款后回报', due: '09-12' }] }
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
      '<td><span class="btn btn-sec btn-sm" onclick="meetDetail(\'' + m.id + '\')">查看</span></td></tr>';
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

/* ===================== MEET-004 会议纪要管理 ===================== */
/* 纪要详情抽屉：已生成→内容+决议待办+归档；AI 转写中→进度；待生成→触发 AI 生成 */
function meetDetail(id) {
  const m = MEETS.filter(function (x) { return x.id === id; })[0];
  if (!m) return;
  let body = '<div class="kv">' +
    '<div><div class="k">会议编号</div><div class="v mono">' + m.id + '</div></div>' +
    '<div><div class="k">主题</div><div class="v">' + m.topic + '</div></div>' +
    '<div><div class="k">组织者</div><div class="v">' + sens(m.org) + '</div></div>' +
    '<div><div class="k">时间 / 时长</div><div class="v">' + m.time + ' · ' + m.dur + '</div></div>' +
    '<div><div class="k">会议室</div><div class="v">' + m.room + '</div></div>' +
    '<div><div class="k">参会人数</div><div class="v">' + m.ppl + ' 人</div></div></div>';
  if (m.min === '已生成' || m.min === '已归档') {
    /* 纪要正文 + 决议待办 */
    body += '<div class="dsec">纪要正文' + (m.min === '已归档' ? '（已归档 · 只读）' : '') + '</div>' +
      '<div class="card" style="box-shadow:none;border:1px solid var(--line);padding:12px 14px;font-size:12.5px;line-height:1.7;color:var(--text)">' + (m.minBody || '（纪要内容待补充）') + '</div>';
    const decs = m.decisions || [];
    body += '<div class="dsec">决议事项 → 待办（' + decs.length + ' 项）</div>';
    if (decs.length) {
      body += '<div class="tl">' + decs.map(function (d) {
        return '<div class="tl-i gg"><div class="tt" style="font-size:12.5px">' + d.d + '</div><div class="td">截止 ' + d.due + ' · 已转待办（钉钉待办 + 工作台待办中心）</div></div>';
      }).join('') + '</div>';
    } else {
      body += '<div class="hint">本次会议无决议事项</div>';
    }
    const foot = '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>' +
      (m.min === '已生成' ? '<button class="btn btn-sec" onclick="meetMinEdit(\'' + m.id + '\')">编辑纪要</button>' +
        '<button class="btn btn-pri" onclick="meetMinArchive(\'' + m.id + '\')">归档纪要</button>' : '');
    openDrawer('会议纪要 · ' + m.topic, body, foot, '560px');
  } else if (m.min === 'AI 转写中') {
    /* AI 转写进度 */
    body += '<div class="dsec">AI 纪要生成中</div>' +
      '<div class="card" style="box-shadow:none;border:1px solid var(--line);padding:16px;text-align:center">' +
      '<span class="spin" style="display:inline-block;margin-bottom:8px"></span>' +
      '<div style="font-size:13px;font-weight:600">AI 听记转写中 · 约 3 分钟完成</div>' +
      '<div class="hint" style="margin-top:4px">转写完成后将自动提取决议事项并生成待办推送（MEET-004）</div>' +
      '<div class="rowline" style="justify-content:center;gap:8px;margin-top:10px">' +
      '<span class="btn btn-sec btn-sm" onclick="meetMinDone(\'' + m.id + '\')">模拟转写完成</span></div></div>';
    openDrawer('会议纪要 · ' + m.topic, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '480px');
  } else {
    /* 待生成：触发 AI 生成 */
    body += '<div class="dsec">纪要状态</div>' +
      '<div class="card" style="box-shadow:none;border:1px dashed var(--line2);padding:16px;text-align:center">' +
      '<div style="font-size:13px;font-weight:600;color:var(--orange)">纪要尚未生成</div>' +
      '<div class="hint" style="margin-top:4px">可等待会议结束后 AI 自动生成，或上传录音/手动录入触发即时生成</div>' +
      '<div class="rowline" style="justify-content:center;gap:8px;margin-top:10px">' +
      '<span class="btn btn-pri btn-sm" onclick="meetMinGen(\'' + m.id + '\')">' + ic('bolt', 13) + ' 触发 AI 生成</span>' +
      '<span class="btn btn-sec btn-sm" onclick="meetMinManual(\'' + m.id + '\')">手动录入纪要</span></div></div>';
    openDrawer('会议纪要 · ' + m.topic, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '480px');
  }
}
/* MEET-004：触发 AI 生成（待生成 → AI 转写中 → 模拟完成） */
function meetMinGen(id) {
  const m = MEETS.filter(function (x) { return x.id === id; })[0];
  if (!m) return;
  confirmDlg('触发 AI 纪要生成？', '将调用 AI 听记对会议「' + m.topic + '」进行转写并提取决议事项，约 3 分钟完成。', '开始生成', function () {
    m.min = 'AI 转写中';
    if (state.page === 'meet') renderPage();
    closeDrawer();
    toast('AI 纪要生成已触发：' + m.id + '（约 3 分钟）', 'success');
    hlFirst();
  });
}
/* MEET-004：模拟转写完成（AI 转写中 → 已生成） */
function meetMinDone(id) {
  const m = MEETS.filter(function (x) { return x.id === id; })[0];
  if (!m) return;
  m.min = '已生成';
  m.minBody = '一、AI 转写摘要：会议围绕「' + m.topic + '」展开，参会 ' + m.ppl + ' 人，时长 ' + m.dur + '。二、关键结论：任务分工明确，下周复盘跟进。三、决议事项已自动提取为待办。';
  m.decisions = [{ d: '跟进本次会议结论落实情况，责任：' + m.org, due: '09-25' }];
  if (state.page === 'meet') renderPage();
  closeDrawer();
  meetDetail(id);
  toast('AI 纪要已生成：' + m.id + '（决议 1 项已转待办）', 'success');
}
/* MEET-004：手动录入纪要 */
function meetMinManual(id) {
  const m = MEETS.filter(function (x) { return x.id === id; })[0];
  if (!m) return;
  const body = frow([
    { k: 'minbody', label: '纪要正文', type: 'textarea', req: true, ph: '会议结论、关键数据、分工安排…', wide: true },
    { k: 'mindec', label: '决议事项', type: 'textarea', ph: '每行一条决议（责任人间隔号分隔 + 截止日期）', wide: true }
  ]) + '<div class="hint" style="margin-top:4px">决议事项每行一条，格式：事项描述；责任人；截止日</div>';
  openDrawer('手动录入纪要 · ' + m.topic, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="meetMinManualOk(\'' + m.id + '\')">保存纪要</button>', '560px');
}
function meetMinManualOk(id) {
  const m = MEETS.filter(function (x) { return x.id === id; })[0];
  if (!m) return;
  if (!formValidate(['minbody'])) return;
  m.min = '已生成';
  m.minBody = $('#F_minbody').value.trim();
  const decLines = ($('#F_mindec').value || '').split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
  m.decisions = decLines.map(function (l) {
    const parts = l.split(/[;；]/);
    return { d: (parts[0] || l), due: (parts[2] || '待定').replace(/^截止[：:]?\s*/, '') };
  });
  if (state.page === 'meet') renderPage();
  closeDrawer();
  meetDetail(id);
  toast('纪要已保存：' + m.id + '（决议 ' + m.decisions.length + ' 项已转待办）', 'success');
}
/* MEET-004：编辑纪要正文 */
function meetMinEdit(id) {
  const m = MEETS.filter(function (x) { return x.id === id; })[0];
  if (!m) return;
  const body = frow([
    { k: 'minbody', label: '纪要正文', type: 'textarea', req: true, val: m.minBody || '', wide: true }
  ]);
  openDrawer('编辑纪要 · ' + m.topic, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="meetMinEditOk(\'' + m.id + '\')">保存修改</button>', '560px');
}
function meetMinEditOk(id) {
  const m = MEETS.filter(function (x) { return x.id === id; })[0];
  if (!m) return;
  if (!formValidate(['minbody'])) return;
  m.minBody = $('#F_minbody').value.trim();
  closeDrawer();
  meetDetail(id);
  toast('纪要已更新：' + m.id, 'success');
}
/* MEET-004：归档（已生成 → 已归档，只读） */
function meetMinArchive(id) {
  const m = MEETS.filter(function (x) { return x.id === id; })[0];
  if (!m) return;
  confirmDlg('确认归档纪要？', '纪要「' + m.topic + '」归档后转为只读状态，正文与决议待办不可再编辑（决议待办继续有效）。', '确认归档', function () {
    m.min = '已归档';
    if (state.page === 'meet') renderPage();
    closeDrawer();
    toast('纪要已归档：' + m.id + '（转为只读）', 'success');
    hlFirst();
  });
}

/* ===================== 03 MEET 日报中心（走查 #10 · 与 09 分离） ===================== */
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
function dailyPageView(pageId) {
  return ({ dailyMine: '我的日报', dailyTeam: '团队日报', dailyReview: '待我审阅', dailyStat: '统计' })[pageId] || '我的日报';
}
function renderDailyCenterPage(pageId) {
  const cur = dailyPageView(pageId);
  const pendRvw = REPORTS.filter(function (r) { return r.rvw === '待审阅'; }).length;
  const routeHint = DAILY_ROUTE[pageId] ? '<span class="hint" style="margin-left:8px;font-size:11px">' + DAILY_ROUTE[pageId] + '</span>' : '';
  let h = pgHead(pageId, (cur === '待我审阅' ? '<button class="btn btn-sec" onclick="reportRvwBatch()">批量通过</button>' :
    '<button class="btn btn-pri" onclick="reportWrite()">' + ic('plus', 15) + '填写今日日报</button>') + routeHint);
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
  if (cur === '团队日报') h += '<div class="hint" style="margin-bottom:10px">团队视角（MEET-001/002）：按数据权限展示下属与本部门日报，API GET /admin-api/ims/meet/daily/list。</div>';
  if (cur === '我的日报') h += '<div class="hint" style="margin-bottom:10px">本人日报 · POST /admin-api/ims/meet/daily · 截止默认 22:00（MEE-D-R1）。</div>';
  const stc = { '草稿': 'gray', '已提交': 'blue', '已补交': 'orange', '迟交': 'red' };
  const rvc = { '待审阅': 'orange', '已审阅': 'green', '已退回': 'red', '—': 'gray' };
  let baseList = qFilter(REPORTS, function (r) { return [r.user, r.type, r.date]; }, function (r) { return r.st + '|' + (r.rvw || '—'); });
  if (cur === '我的日报') {
    const me = ROLES[state.role].user;
    baseList = baseList.filter(function (r) { return r.user === me; });
  }
  const list = baseList;
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
}
DAILY_IDS.forEach(function (pid) {
  PAGES[pid] = function () { return renderDailyCenterPage(pid); };
});
/* 09 REPORT 数据上报（独立 L2 · 走查 #10） */
PAGES.reportTpl = function () {
  return pgHead('reportTpl', '<button class="btn btn-sec" onclick="reportTplAdd()">新建模板</button>') +
    '<div class="hint" style="margin-bottom:10px">REPORT-001 · ' + REPORT_ROUTE.reportTpl + ' · /admin-api/ims/report/template</div>' + reportTplTab();
};
PAGES.reportSub = function () {
  const pend = UPLOADS.filter(function (u) { return u.st === '待审核'; }).length;
  return pgHead('reportSub', '<button class="btn btn-pri" onclick="reportSubmitData()">' + ic('plus', 15) + '提交填报单</button>') +
    '<div class="hint" style="margin-bottom:10px">REPORT-002/003 · ' + REPORT_ROUTE.reportSub + (pend ? ' · 待审核 ' + pend + ' 单' : '') + '</div>' + reportUploadListTab();
};
PAGES.reportRate = function () {
  return pgHead('reportRate', '') +
    '<div class="hint" style="margin-bottom:10px">REPORT-004 · BR-106 质量口径 · ' + REPORT_ROUTE.reportRate + '</div>' + reportRateTab();
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
  refreshDailyOrReportPage();
  formOk(no, '日报已提交 · 字段完成度 ' + pct + '%，已进入直属主管审阅队列', '');
  toast('日报提交成功（完成度 ' + pct + '%）· 已推送主管审阅', 'success');
}
/* MEET-002：日报审阅通过（逐级向上汇总） */
function reportApprove(i) {
  const r = REPORTS[i];
  if (!r) return;
  confirmDlg('确认审阅通过？', r.user + ' 的 ' + r.date + ' ' + r.type + '日报（完成度 ' + r.pct + '%）将通过审阅，并逐级向上汇总至部门负责人。', '通过审阅', function () {
    r.rvw = '已审阅';
    refreshDailyOrReportPage();
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
    refreshDailyOrReportPage();
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
    refreshDailyOrReportPage();
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
/** 走查 #10 续：作者 → IP 组账号池级联（mock · 对齐 FR-REPORT-012） */
const REPORT_AUTHOR_OPTS = ['请选择作者', '苏杳 · au_sy', '赵敏 · au_zm', '孙倩 · au_sq', '陈默 · au_cm'];
const REPORT_AUTHOR_ACCOUNTS = {
  '苏杳 · au_sy': ['88001 神鱼电竞A · 抖音', '88002 神鱼短视频 · 抖音'],
  '赵敏 · au_zm': ['88001 神鱼电竞A · 抖音', '88033 神鱼健身 · 小红书'],
  '孙倩 · au_sq': ['88014 体育号B · 快手'],
  '陈默 · au_cm': ['88014 体育号B · 快手', '88033 神鱼健身 · 小红书']
};
function reportAuthorCascade() {
  const authorEl = $('#F_rauthor');
  const acctEl = $('#F_raccount');
  if (!authorEl || !acctEl) return;
  const key = authorEl.value;
  const pool = REPORT_AUTHOR_ACCOUNTS[key];
  const opts = !key || key.indexOf('请选择') === 0 ? ['请先选择作者'] : (pool && pool.length ? ['请选择账号'].concat(pool) : ['（该作者 IP 组暂无绑定账号）']);
  acctEl.innerHTML = opts.map(function (o) { return '<option>' + o + '</option>'; }).join('');
  acctEl.disabled = !pool || !pool.length;
}
function reportCtxFieldsHtml() {
  return '<div class="dsec">归因上下文 · AuthorSelect + AccountSelect（FR-REPORT-011）</div>' + frow([
    { k: 'rauthor', label: '作者 AuthorSelect', type: 'select', req: true, opts: REPORT_AUTHOR_OPTS.slice(), chg: 'reportAuthorCascade()' },
    { k: 'raccount', label: '平台账号 AccountSelect', type: 'select', req: true, opts: ['请先选择作者'], disabled: true }
  ]) + '<div class="hint">选作者后级联账号（GET ip-group/{id}/accounts 示意）；提交写入 authorId + accountId。</div>';
}
function reportCtxValidate() {
  const a = $('#F_rauthor');
  const c = $('#F_raccount');
  if (!a || !c) return true;
  const av = (a.value || '').trim();
  const cv = (c.value || '').trim();
  if (!av || av.indexOf('请选择') === 0) {
    a.classList.add('err');
    toast('请选择作者（AuthorSelect）', 'error');
    return false;
  }
  if (c.disabled || !cv || cv.indexOf('请选择') === 0 || cv.indexOf('请先') === 0) {
    c.classList.add('err');
    toast('请选择平台账号（AccountSelect）', 'error');
    return false;
  }
  a.classList.remove('err');
  c.classList.remove('err');
  return true;
}
const RTPLS = [
  { no: 'RT-003', name: '抖音电商日度经营数据', fields: 12, freq: '每日 18:00 前', owner: '运营中心', on: true, use: 36, flds: [
    { n: '统计日期', ty: '日期', req: true, rule: '不可晚于当日' },
    { n: 'GMV', ty: '金额', req: true, rule: '≥ 0' },
    { n: '订单数', ty: '整数', req: true, rule: '≥ 0' },
    { n: '退款率', ty: '百分比', req: true, rule: '0~100%' },
    { n: '投放消耗', ty: '金额', req: false, rule: '≥ 0' },
    { n: '备注', ty: '文本', req: false, rule: '≤ 200 字' }
  ] },
  { no: 'RT-002', name: '直播场次复盘数据包', fields: 10, freq: '场次结束 2h 内', owner: '直播运营', on: true, use: 28, flds: [
    { n: '场次归属作者', ty: '作者', req: true, rule: 'AuthorSelect · author_user.id' },
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
  { no: 'UP20260918-012', tpl: 'RT-003 抖音日度经营', by: '赵敏', author: '赵敏 · au_zm', acct: '88001 神鱼电竞A · 抖音', ct: '2026-09-18 17:20', rows: 86, st: '待审核' },
  { no: 'UP20260918-011', tpl: 'RT-002 直播复盘', by: '孙倩', author: '孙倩 · au_sq', acct: '88014 体育号B · 快手', ct: '2026-09-18 15:40', rows: 14, st: '待审核' },
  { no: 'UP20260917-010', tpl: 'RT-003 抖音日度经营', by: '赵敏', author: '赵敏 · au_zm', acct: '88001 神鱼电竞A · 抖音', ct: '2026-09-17 17:55', rows: 84, st: '已通过' },
  { no: 'UP20260916-009', tpl: 'RT-003 抖音日度经营', by: '陈默', author: '陈默 · au_cm', acct: '88014 体育号B · 快手', ct: '2026-09-16 19:12', rows: 82, st: '已退回' },
  { no: 'UP20260915-008', tpl: 'RT-001 短视频周度', by: '孙倩', author: '孙倩 · au_sq', acct: '88014 体育号B · 快手', ct: '2026-09-15 11:30', rows: 55, st: '已通过' },
  { no: 'UP20260914-007', tpl: 'RT-004 竞品动向', by: '陈默', author: '陈默 · au_cm', acct: '88033 神鱼健身 · 小红书', ct: '2026-09-14 17:48', rows: 22, st: '已通过' },
  { no: 'UP20260913-006', tpl: 'RT-002 直播复盘', by: '何舟', author: '苏杳 · au_sy', acct: '88002 神鱼短视频 · 抖音', ct: '2026-09-13 22:05', rows: 11, st: '已通过' }
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
    refreshDailyOrReportPage();
    reportTplEdit(i);
    toast('字段已删除：' + f.n + '（剩余 ' + t.flds.length + ' 个字段）', 'success');
  }, { danger: true });
}
/* REPORT：新增字段表单 */
function reportFldAdd(i) {
  const t = RTPLS[i];
  const body = frow([
    { k: 'fn', label: '字段名', type: 'text', req: true, ph: '如：客单价' },
    { k: 'ft', label: '字段类型', type: 'select', req: true, opts: ['文本', '整数', '金额', '百分比', '日期', '枚举', '作者', '平台账号'] },
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
  refreshDailyOrReportPage();
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
    { k: 'ft', label: '字段类型', type: 'select', req: true, opts: ['文本', '整数', '金额', '百分比', '日期', '枚举', '作者', '平台账号'], val: f.ty },
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
  refreshDailyOrReportPage();
  formOk(no, '上报模板已创建并启用，上报人将按模板字段逐项填报', '');
  toast('上报模板创建成功：' + no, 'success');
}
/* REPORT-002：数据提交 + REPORT-003：审核退回 */
function reportSubmitData() {
  const tOpts = RTPLS.filter(function (t) { return t.on; }).map(function (t) { return t.no + ' · ' + t.name; });
  const body = reportCtxFieldsHtml() + frow([
    { k: 'utpl', label: '选择模板', type: 'select', req: true, opts: tOpts.length ? tOpts : ['（暂无启用模板）'] },
    { k: 'udate', label: '数据日期', type: 'date', req: true, val: '2026-09-18' },
    { k: 'ufile', label: '数据附件', type: 'file', ph: '点击上传 CSV / Excel（可选，支持在线填报）', wide: true },
    { k: 'urows', label: '数据行数', type: 'num', unit: '行', val: 86 },
    { k: 'unote', label: '数据说明', type: 'textarea', ph: '口径变化、异常波动说明（选填）', wide: true }
  ]) + '<div class="hint" style="margin-top:4px">提交后进入数据审核流：校验字段完整性与口径 → 通过入仓数据中心 → 不通过将退回并要求补充（REPORT-003）。</div>';
  openDrawer('提交上报数据', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="reportSubmitDataOk()">提交并送审</button>', '560px');
  setTimeout(reportAuthorCascade, 0);
}
function reportSubmitDataOk() {
  if (!reportCtxValidate()) return;
  if (!formValidate(['utpl', 'udate', 'urows'])) return;
  const no = 'UP20260918-' + String(UPLOADS.length + 1).padStart(3, '0');
  UPLOADS.unshift({
    no: no,
    tpl: $('#F_utpl').value.split(' · ')[1] || $('#F_utpl').value,
    by: ROLES[state.role].user,
    author: $('#F_rauthor').value,
    acct: $('#F_raccount').value,
    ct: '2026-09-18 17:30',
    rows: Number($('#F_urows').value || 0),
    st: '待审核'
  });
  refreshDailyOrReportPage();
  formOk(no, '上报数据已提交（待审核），审核通过后将写入数据中心', '');
  toast('数据上报成功：' + no + ' · ' + UPLOADS[0].rows + ' 行', 'success');
}
function reportUploadListTab() {
  const stc = { '待审核': 'orange', '已通过': 'green', '已退回': 'red' };
  let rows = '';
  UPLOADS.forEach(function (u, i) {
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + u.no + '</td><td style="font-weight:500">' + u.tpl + '</td><td>' + sens(u.by) + '</td>' +
      '<td>' + sens((u.author || '—').split('·')[0].trim()) + '</td><td style="font-size:12px">' + (u.acct || '—') + '</td>' +
      '<td class="num" style="font-size:12px;color:var(--text2)">' + u.ct + '</td><td class="num">' + u.rows + ' 行</td>' +
      '<td>' + tag(u.st, stc[u.st]) + '</td>' +
      '<td>' + (u.st === '待审核' ? '<button class="btn btn-pri btn-sm" onclick="reportUplAudit(' + i + ',1)">通过</button> <button class="btn btn-sm" style="color:var(--red);border-color:rgba(255,59,48,.35)" onclick="reportUplAudit(' + i + ',0)">退回</button>' :
        '<span class="btn btn-sec btn-sm" onclick="reportUplDetail(' + i + ')">查看</span>') + '</td></tr>';
  });
  return qbar(qi('上报单号', 130) + qi('提交人', 100) + qs(['全部作者', '苏杳', '赵敏', '孙倩', '陈默'], 90) + qs(['全部账号', '88001', '88014', '88033'], 100) + qs(['全部状态', '待审核', '已通过', '已退回'], 90)) +
    tbl(['上报单号', '模板', '提交人', '作者', '平台账号', '提交时间', '数据量', '状态', '操作'], rows);
}
function reportUplAudit(i, pass) {
  const u = UPLOADS[i];
  if (!u) return;
  if (pass) {
    confirmDlg('确认审核通过？', '上报单 ' + u.no + '（' + u.tpl + ' · ' + u.rows + ' 行）字段校验全部通过，数据将写入数据中心并同步 BI 报表。', '通过入仓', function () {
      u.st = '已通过';
      refreshDailyOrReportPage();
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
      refreshDailyOrReportPage();
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
    '<div><div class="k">提交人</div><div class="v">' + sens(u.by) + '</div></div><div><div class="k">作者 / 账号</div><div class="v">' + sens((u.author || '—').split('·')[0].trim()) + ' · ' + (u.acct || '—') + '</div></div>' +
    '<div><div class="k">提交时间</div><div class="v">' + u.ct + '</div></div>' +
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
  const cur = state.tab.fin || '结算单';
  let h = pgHead('fin', cur === '成本单据' ? '<button class="btn btn-pri" onclick="finCostAdd()">' + ic('plus', 15) + '录入成本单</button>' :
    cur === '分成规则' ? '<button class="btn btn-pri" onclick="finRuleAdd()">' + ic('plus', 15) + '新建分成规则</button>' :
      '<button class="btn btn-sec" onclick="exportX(this,\'核算明细\',FINS.length)">导出</button>' +
      '<button class="btn btn-pri" onclick="finAdd()">' + ic('plus', 15) + '发起结算</button>');
  h += '<div class="tabs">' + ['结算单', '成本单据', '分成规则'].map(function (t) {
    return '<div class="tab' + (cur === t ? ' on' : '') + '" onclick="setTab(\'fin\',\'' + t + '\')">' + t + '</div>';
  }).join('') + '</div>';
  if (cur === '成本单据') return h + finCostTab();
  if (cur === '分成规则') return h + finRuleTab();
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
/* FIN：发起结算表单（多成本项拆分 + 自动算净利润） */
function finAdd() {
  const costRows = FINCOSTS.slice(0, 6).map(function (c, i) {
    return '<tr><td>' + tag(c.type, 'cyan') + '</td><td class="mono num" style="font-size:11.5px">' + c.sid + '</td><td>' + c.note + '</td>' +
      '<td class="num">' + fmtMoney(c.amt) + '</td><td>' + c.st + '</td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="finCostAttach(' + i + ')">计入本单</span></td></tr>';
  }).join('');
  const body = frow([
    { k: 'sid', label: '选择场次', type: 'select', req: true, opts: ['IMS202609120DY0142 · 抖音 · 秋季新品首发', 'IMS202609120DY0141 · 斗鱼 · 晚间健身操', 'IMS202609110DY0138 · 视频号 · 装备开箱'] },
    { k: 'rev', label: '总收入', type: 'num', req: true, unit: '¥', ph: '0.00', pre: 'finCalc()' },
    { k: 'cost', label: '总成本', type: 'num', req: true, unit: '¥', ph: '0.00', pre: 'finCalc()', hint: '可在下方成本项清单中逐项计入自动汇总' },
    { k: 'ratio', label: '分成比例', type: 'num', req: true, unit: '%', val: 30, pre: 'finCalc()' },
    { k: 'note', label: '备注', type: 'textarea', ph: '结算口径、特殊分成约定（选填）', wide: true }
  ]) + '<div class="dsec">成本项拆分（FIN-001 · 待计入 ' + FINCOSTS.filter(function (c) { return c.st === '已审核'; }).length + ' 笔）</div>' +
    '<div class="tbl-wrap"><table><thead><tr><th>成本类型</th><th>关联场次</th><th>说明</th><th>金额</th><th>状态</th><th>操作</th></tr></thead><tbody>' +
    (costRows || '<tr><td colspan="6" style="text-align:center;color:var(--text2)">暂无待计入成本项</td></tr>') +
    '</tbody></table></div>' +
    '<div class="dsec">净利润测算（自动计算）</div>' +
    '<div class="kv" style="background:var(--bg);border-radius:10px;padding:12px 14px">' +
    '<div><div class="k">毛利</div><div class="v num" id="finP">¥0.00</div></div>' +
    '<div><div class="k">主播分成</div><div class="v num" style="color:var(--blue)" id="finS">¥0.00</div></div>' +
    '<div><div class="k">净利润</div><div class="v num pos" style="font-weight:700" id="finN">¥0.00</div></div></div>';
  openDrawer('发起结算', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="finAddSubmit()">提交结算单</button>', '640px');
}
/* FIN-001：成本项计入结算单（自动累加到总成本） */
function finCostAttach(i) {
  const c = FINCOSTS[i];
  if (!c) return;
  if (c.st !== '已审核') { toast('仅已审核成本项可计入', 'warn'); return; }
  const el = $('#F_cost');
  const cur = Number(el.value || 0);
  el.value = (cur + c.amt).toFixed(2);
  finCalc();
  toast('成本项已计入：' + c.type + ' ' + fmtMoney(c.amt) + '（总成本 ' + fmtMoney(cur + c.amt) + '）', 'success');
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

/* ===================== FIN-001 成本单据管理 ===================== */
const FINCOSTS = [
  { no: 'CB20260918-012', type: '投流消耗', sid: 'IMS202609110DY0138', amt: 38000.00, by: '赵敏', note: '巨量千川 · 秋季装备开箱', st: '已审核' },
  { no: 'CB20260918-011', type: '坑位费', sid: 'IMS202609110DY0138', amt: 15000.00, by: '何舟', note: '达人坑位 · 跑鞋专场', st: '已审核' },
  { no: 'CB20260917-010', type: '佣金', sid: 'IMS202609100DY0131', amt: 24600.00, by: '周晴', note: '联盟佣金 6%', st: '已审核' },
  { no: 'CB20260917-009', type: '物流仓储', sid: '—', amt: 8200.00, by: '林岚', note: '发货仓月度分摊', st: '已审核' },
  { no: 'CB20260916-008', type: '设备折旧', sid: '—', amt: 4500.00, by: '林岚', note: '直播设备月折旧', st: '已审核' },
  { no: 'CB20260916-007', type: '样品损耗', sid: 'IMS202609090DY0127', amt: 3200.00, by: '孙倩', note: '测评样品 12 件', st: '待审核' }
];
/* FIN-001：成本单据 Tab */
function finCostTab() {
  const tot = FINCOSTS.filter(function (c) { return c.st === '已审核'; }).reduce(function (s, c) { return s + c.amt; }, 0);
  const pend = FINCOSTS.filter(function (c) { return c.st === '待审核'; }).length;
  const linked = FINCOSTS.filter(function (c) { return c.sid !== '—'; }).length;
  let h = '<div class="g4">' +
    '<div class="card stat"><span class="l">已审核成本</span><div class="n" style="font-size:22px">' + fmtMoney(tot) + '</div><div class="d">FIN-001 成本口径</div></div>' +
    '<div class="card stat"><span class="l">待审核</span><div class="n" style="font-size:22px;color:var(--orange)">' + pend + ' 笔</div><div class="d">财务复核中</div></div>' +
    '<div class="card stat"><span class="l">场次关联率</span><div class="n" style="font-size:22px;color:var(--blue)">' + Math.round(linked / Math.max(FINCOSTS.length, 1) * 100) + '%</div><div class="d">关联场次 ID</div></div>' +
    '<div class="card stat"><span class="l">成本类型</span><div class="n" style="font-size:22px">8 类</div><div class="d">坑位/投流/佣金/物流…</div></div></div>';
  h += '<div class="hint" style="margin-bottom:10px">成本单据独立录入（FIN-001），按成本类型拆分并关联场次 ID；结算时在「发起结算」中逐项计入自动汇总总成本。</div>';
  h += qbar(qi('成本单号', 130) + qi('场次 ID', 150) + qs(['全部类型', '坑位费', '投流消耗', '佣金', '物流仓储', '设备折旧', '样品损耗']) + qs(['全部状态', '已审核', '待审核'], 90));
  const stc = { '已审核': 'green', '待审核': 'orange' };
  let rows = '';
  FINCOSTS.forEach(function (c, i) {
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + c.no + '</td><td>' + tag(c.type, 'cyan') + '</td>' +
      '<td class="mono num" style="font-size:11.5px">' + c.sid + '</td>' +
      '<td class="num" style="font-weight:500">' + fmtMoney(c.amt) + '</td><td>' + sens(c.by) + '</td>' +
      '<td style="font-size:12px;color:var(--text2)">' + c.note + '</td><td>' + tag(c.st, stc[c.st]) + '</td>' +
      '<td>' + (c.st === '待审核' ? '<button class="btn btn-pri btn-sm" onclick="finCostAudit(' + i + ')">审核</button>' : '<span class="btn btn-sec btn-sm" onclick="finCostDetail(' + i + ')">查看</span>') + '</td></tr>';
  });
  h += tbl(['成本单号', '类型', '关联场次', '金额', '录入人', '说明', '状态', '操作'], rows);
  return h;
}
/* FIN-001：录入成本单表单 */
function finCostAdd() {
  const body = frow([
    { k: 'ctype', label: '成本类型', type: 'select', req: true, opts: ['坑位费', '投流消耗', '佣金', '物流仓储', '设备折旧', '样品损耗', '场地租赁', '其他'] },
    { k: 'csid', label: '关联场次', type: 'text', ph: 'IMS 开头场次 ID（非场次分摊类可留空）' },
    { k: 'camt', label: '金额', type: 'num', req: true, unit: '¥', ph: '0.00' },
    { k: 'cby', label: '录入人', type: 'text', val: ROLES[state.role].user, disabled: true },
    { k: 'cnote', label: '费用说明', type: 'textarea', req: true, ph: '投放计划 / 合同编号 / 分摊口径…', wide: true }
  ]) + '<div class="hint" style="margin-top:4px">录入后进入财务审核；审核通过的成本项可在结算单中计入（FIN-001）。</div>';
  openDrawer('录入成本单', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="finCostAddSubmit()">提交成本单</button>', '480px');
}
function finCostAddSubmit() {
  if (!formValidate(['camt', 'cnote'])) return;
  const no = 'CB20260918-' + String(FINCOSTS.length + 1).padStart(3, '0');
  FINCOSTS.unshift({ no: no, type: $('#F_ctype').value, sid: ($('#F_csid').value || '').trim() || '—', amt: Number($('#F_camt').value || 0), by: ROLES[state.role].user, note: $('#F_cnote').value.trim(), st: '待审核' });
  if (state.page === 'fin') renderPage();
  formOk(no, '成本单已提交（待财务审核），审核通过后可在结算中计入', '');
  toast('成本单提交成功：' + no + ' · ' + fmtMoney(FINCOSTS[0].amt), 'success');
}
/* FIN-001：成本审核 */
function finCostAudit(i) {
  const c = FINCOSTS[i];
  if (!c) return;
  confirmDlg('审核通过成本单？', '成本单 ' + c.no + '（' + c.type + ' · ' + fmtMoney(c.amt) + ' · ' + c.note + '）审核通过后进入可计入状态。', '通过审核', function () {
    c.st = '已审核';
    if (state.page === 'fin') renderPage();
    toast('成本单已审核：' + c.no + '（可计入结算）', 'success');
    hlFirst();
  }, { warn: '请核对金额与关联场次一致性（BR-017 账实核对口径）' });
}
/* FIN-001：成本单详情 */
function finCostDetail(i) {
  const c = FINCOSTS[i];
  if (!c) return;
  const body = '<div class="kv">' +
    '<div><div class="k">成本单号</div><div class="v mono">' + c.no + '</div></div>' +
    '<div><div class="k">类型</div><div class="v">' + c.type + '</div></div>' +
    '<div><div class="k">金额</div><div class="v num" style="font-weight:600">' + fmtMoney(c.amt) + '</div></div>' +
    '<div><div class="k">关联场次</div><div class="v mono" style="font-size:12px">' + c.sid + '</div></div>' +
    '<div><div class="k">录入人</div><div class="v">' + sens(c.by) + '</div></div>' +
    '<div><div class="k">状态</div><div class="v">' + c.st + '</div></div></div>' +
    '<div class="dsec">费用说明</div>' +
    '<div class="card" style="box-shadow:none;border:1px solid var(--line);padding:12px;font-size:12.5px">' + c.note + '</div>';
  openDrawer('成本单详情 · ' + c.no, body, '<button class="btn btn-sec" onclick="closeDrawer()">关闭</button>', '480px');
}

/* ===================== FIN-003 分成规则引擎 ===================== */
const FINRULES = [
  { no: 'SR-001', name: '主播固定分成', mode: '固定比例', body: [{ role: '主播', pct: 30 }], on: true, use: 62 },
  { no: 'SR-002', name: '主播阶梯分成（GMV）', mode: '阶梯', body: [{ role: 'GMV < 10 万', pct: 20 }, { role: 'GMV 10~50 万', pct: 30 }, { role: 'GMV > 50 万', pct: 40 }], on: true, use: 28 },
  { no: 'SR-003', name: '团队多方分成（大促）', mode: '多方', body: [{ role: '主播', pct: 25 }, { role: '运营', pct: 10 }, { role: '场控', pct: 5 }], on: true, use: 11 },
  { no: 'SR-004', name: '外协阶梯分成', mode: '阶梯', body: [{ role: '利润 < 2 万', pct: 15 }, { role: '利润 ≥ 2 万', pct: 20 }], on: false, use: 3 }
];
/* FIN-003：分成规则 Tab */
function finRuleTab() {
  let h = '<div class="hint" style="margin-bottom:10px">分成规则引擎（FIN-003）：固定比例 / GMV 阶梯 / 多方分成三类规则；结算时按规则自动分账，多方分成为各角色比例之和须 ≤ 100%。</div>';
  let rows = '';
  const mc = { '固定比例': 'blue', '阶梯': 'purple', '多方': 'orange' };
  FINRULES.forEach(function (r, i) {
    const chain = r.body.map(function (b, j) {
      return '<span style="font-size:11px;padding:2px 8px;border:1px solid var(--line2);border-radius:10px;white-space:nowrap">' + b.role + ' → ' + b.pct + '%</span>' + (j < r.body.length - 1 ? '<span style="color:var(--text2);font-size:10px;margin:0 2px">|</span>' : '');
    }).join('');
    const sum = r.body.reduce(function (s, b) { return s + b.pct; }, 0);
    rows += '<tr><td class="mono num" style="color:var(--blue)">' + r.no + '</td><td style="font-weight:500">' + r.name + '</td>' +
      '<td>' + tag(r.mode, mc[r.mode]) + '</td>' +
      '<td style="max-width:300px"><div class="rowline" style="gap:3px;flex-wrap:wrap">' + chain + '</div></td>' +
      '<td class="num" style="font-weight:600;' + (sum > 100 ? 'color:var(--red)' : '') + '">' + sum + '%</td>' +
      '<td class="num">' + r.use + ' 次</td>' +
      '<td><span class="sw' + (r.on ? ' on' : '') + '" onclick="this.classList.toggle(\'on\');toast(\'规则已' + (r.on ? '停用' : '启用') + '\',\'success\')"><i></i></span></td>' +
      '<td><span class="btn btn-sec btn-sm" onclick="finRuleEdit(' + i + ')">编辑</span></td></tr>';
  });
  h += tbl(['规则编号', '规则名称', '模式', '分成结构', '比例合计', '累计使用', '启停', '操作'], rows);
  return h;
}
/* FIN-003：规则编辑抽屉 */
function finRuleEdit(i) {
  const r = FINRULES[i];
  const itemRows = r.body.map(function (b, j) {
    return '<tr><td><input id="RI_role' + j + '" value="' + b.role + '" style="width:100%"></td>' +
      '<td><input id="RI_pct' + j + '" type="number" value="' + b.pct + '" style="width:70px"></td>' +
      '<td><span class="btn btn-sm" style="color:var(--red);border-color:rgba(255,59,48,.35)" onclick="finRuleItemDel(' + i + ',' + j + ')">删除</span></td></tr>';
  }).join('');
  const body = frow([
    { k: 'rname', label: '规则名称', type: 'text', req: true, val: r.name },
    { k: 'rmode', label: '分成模式', type: 'select', req: true, opts: ['固定比例', '阶梯', '多方'], val: r.mode }
  ]) + '<div class="dsec">分成结构（' + r.mode + ' · 角色区间/角色 → 比例%）</div>' +
    '<div class="tbl-wrap"><table><thead><tr><th>角色 / 阶梯条件</th><th>比例 %</th><th></th></tr></thead><tbody>' + itemRows +
    '<tr><td colspan="3" style="padding:6px"><span class="btn btn-sec btn-sm" style="background:var(--orange);color:#fff;border-color:var(--orange)" onclick="finRuleItemAdd(' + i + ')">' + ic('plus', 13) + '添加分成项</span></td></tr></tbody></table></div>' +
    '<div class="hint" style="margin-top:6px" id="RI_hint">当前合计 ' + r.body.reduce(function (s, b) { return s + b.pct; }, 0) + '%（多方模式须 ≤ 100%，阶梯模式各行独立）</div>';
  openDrawer('编辑分成规则 · ' + r.no, body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="finRuleSave(' + i + ')">保存规则</button>', '560px');
}
/* FIN-003：添加分成项（重渲染编辑抽屉） */
function finRuleItemAdd(i) {
  const r = FINRULES[i];
  finRuleGrab(i);
  r.body.push({ role: '新角色', pct: 10 });
  finRuleEdit(i);
  toast('已添加分成项（当前 ' + r.body.length + ' 项）', 'success');
}
/* FIN-003：删除分成项 */
function finRuleItemDel(i, j) {
  const r = FINRULES[i];
  if (r.body.length <= 1) { toast('至少保留一个分成项', 'warn'); return; }
  finRuleGrab(i);
  r.body.splice(j, 1);
  finRuleEdit(i);
  toast('分成项已删除（剩余 ' + r.body.length + ' 项）', 'success');
}
/* FIN-003：从当前抽屉输入抓取到数据（编辑/增删前暂存） */
function finRuleGrab(i) {
  const r = FINRULES[i];
  r.body.forEach(function (b, j) {
    const roleEl = $('#RI_role' + j), pctEl = $('#RI_pct' + j);
    if (roleEl) b.role = roleEl.value.trim() || b.role;
    if (pctEl) b.pct = Number(pctEl.value || 0);
  });
  const nameEl = $('#F_rname');
  if (nameEl) r.name = nameEl.value.trim() || r.name;
  const modeEl = $('#F_rmode');
  if (modeEl) r.mode = modeEl.value;
}
/* FIN-003：保存规则（多方模式校验合计 ≤100%） */
function finRuleSave(i) {
  const r = FINRULES[i];
  finRuleGrab(i);
  if (!formValidate(['rname', 'rmode'])) return;
  const sum = r.body.reduce(function (s, b) { return s + b.pct; }, 0);
  if (r.mode === '多方' && sum > 100) {
    toast('多方分成比例合计 ' + sum + '% 超 100%，无法保存（FIN-003）', 'error');
    return;
  }
  if (r.body.some(function (b) { return b.pct < 0 || b.pct > 100; })) {
    toast('分成比例须在 0~100% 之间', 'error');
    return;
  }
  if (state.page === 'fin') renderPage();
  closeDrawer();
  toast('分成规则已保存：' + r.no + ' · ' + r.name + '（' + r.mode + ' · 合计 ' + sum + '%）', 'success');
}
/* FIN-003：新建规则 */
function finRuleAdd() {
  const body = frow([
    { k: 'nrname', label: '规则名称', type: 'text', req: true, ph: '如：新人主播保底分成' },
    { k: 'nrmode', label: '分成模式', type: 'select', req: true, opts: ['固定比例', '阶梯', '多方'] },
    { k: 'nrbody', label: '分成结构', type: 'textarea', req: true, ph: '每行一条：角色/阶梯条件，比例%\n如：\nGMV < 10 万，20%\nGMV ≥ 10 万，30%', wide: true }
  ]) + '<div class="hint" style="margin-top:4px">多方模式各行比例之和须 ≤ 100%；阶梯模式按条件区间从上到下匹配。</div>';
  openDrawer('新建分成规则', body,
    '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="finRuleAddSubmit()">创建规则</button>', '480px');
}
function finRuleAddSubmit() {
  if (!formValidate(['nrname', 'nrbody'])) return;
  const lines = $('#F_nrbody').value.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
  const body = lines.map(function (l) {
    const parts = l.split(/[,，]/);
    return { role: (parts[0] || '角色').trim(), pct: Number((parts[1] || '0').replace('%', '').trim()) || 0 };
  });
  const mode = $('#F_nrmode').value;
  const sum = body.reduce(function (s, b) { return s + b.pct; }, 0);
  if (mode === '多方' && sum > 100) { toast('多方分成合计 ' + sum + '% 超 100%', 'error'); return; }
  const no = 'SR-' + String(FINRULES.length + 1).padStart(3, '0');
  FINRULES.unshift({ no: no, name: $('#F_nrname').value.trim(), mode: mode, body: body, on: true, use: 0 });
  if (state.page === 'fin') renderPage();
  formOk(no, '分成规则已创建并启用（' + body.length + ' 项 · 合计 ' + sum + '%）', '');
  toast('分成规则创建成功：' + no, 'success');
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
const PERF_PLANS = [
  { name: '主播/达人考核方案（直播）', cycle: '季度', target: 36, on: true, d: '开播场次 · GMV · 观看时长 · 粉丝增长', tplId: 1 },
  { name: '直播运营考核方案', cycle: '季度', target: 18, on: true, d: '场次风控通过率 · 直播 GMV · 复盘质量', tplId: 2 },
  { name: '短视频运营考核方案', cycle: '月度', target: 24, on: true, d: '作品数量 · 播放/互动率 · SOP 合规', tplId: 3 },
  { name: '行政/财务考核方案', cycle: '半年度', target: 14, on: false, d: '流程时效 · 差错率 · 满意度', tplId: 4 }
];
const PERF_CYCLES = [
  { id: 'PR202609-018', plan: '主播/达人考核方案（直播）', period: '2026 Q3', target: '赵敏', dept: '运营中心', evaluator: '何舟', st: 'calculated', total: 86,
    items: [{ n: '开播场次', w: 30, val: 42, score: 82, adj: 0 }, { n: '直播 GMV', w: 40, val: 1280000, score: 88, adj: 0 }, { n: '复盘质量', w: 30, val: 4.2, score: 85, adj: 0 }] },
  { id: 'PR202609-017', plan: '短视频运营考核方案', period: '2026-09', target: '孙倩', dept: '内容中心', evaluator: '何舟', st: 'calculating', total: null, items: [] },
  { id: 'PR202609-016', plan: '直播运营考核方案', period: '2026 Q3', target: '苏杳', dept: '主播组', evaluator: '何舟', st: 'draft', total: null, items: [] }
];
function perfStLabel(st) {
  return { draft: '草稿', calculating: '计算中', calculated: '待确认', confirmed: '已确认' }[st] || st;
}
function perfStTag(st) {
  const m = { draft: 'gray', calculating: 'blue', calculated: 'orange', confirmed: 'green' };
  return tag(perfStLabel(st), m[st] || 'gray');
}
function perfResultTableHtml() {
  let h = qbar(qi('被考核人', 110) + qs(['全部部门', '主播组', '运营中心', '内容中心', '数据中心', '行政部', '财务部', '外协']) + qs(['全部周期', '2026 Q3', '2026 Q2']));
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
}
PAGES.perfScheme = function () {
  let h = pgHead('perfScheme', '<button class="btn btn-pri" onclick="perfAdd()">' + ic('plus', 15) + '新建方案</button>');
  h += '<div class="card" style="margin-bottom:14px;padding:12px 16px;font-size:12.5px;color:var(--text2);line-height:1.6">' + ic('help', 15) +
    ' 主路径：<b style="color:var(--text)">考核方案</b> → <b style="color:var(--text)">执行考核</b> → <b style="color:var(--text)">考核结果</b>（对齐 OPS M3 · POST /ops/perf/record/create）</div>';
  h += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:14px">';
  PERF_PLANS.forEach(function (p, pi) {
    h += '<div class="card hov"><div class="rowline" style="justify-content:space-between;margin-bottom:8px">' +
      '<span style="color:var(--blue)">' + ic('chart', 19) + '</span><span class="sw' + (p.on ? ' on' : '') + '" onclick="event.stopPropagation();PERF_PLANS[' + pi + '].on=!PERF_PLANS[' + pi + '].on;renderPage();toast(\'方案已' + (p.on ? '停用' : '启用') + '\',\'success\')"><i></i></span></div>' +
      '<h3 style="font-size:15px">' + p.name + '</h3><div class="csub">' + p.d + '</div>' +
      '<div class="rowline" style="margin-top:12px;flex-wrap:wrap;gap:8px">' + tag(p.cycle, 'blue') + '<span class="csub">' + p.target + ' 名被考核人</span><span class="chip">' + (p.on ? '生效中' : '已停用') + '</span></div>' +
      '<div class="rowline" style="margin-top:12px;gap:8px">' +
      '<button class="btn btn-sec btn-sm" onclick="event.stopPropagation();perfSchemeEdit(' + pi + ')">编辑指标</button>' +
      (p.on ? '<button class="btn btn-pri btn-sm" onclick="event.stopPropagation();perfLaunchCycle(' + pi + ')">' + ic('plus', 13) + '发起考核</button>' :
        '<button class="btn btn-sm" style="opacity:.45" disabled>需启用后发起</button>') +
      '</div></div>';
  });
  h += '</div>';
  return h;
};
PAGES.perfExec = function () {
  let h = pgHead('perfExec', '<button class="btn btn-pri" onclick="perfExecCreate()">' + ic('plus', 15) + '创建考核</button>');
  h += qbar(qi('被考核人', 110) + qs(['全部状态', '草稿', '计算中', '待确认', '已确认'], 100), 'qSave(\'perfExec\')');
  h += '<div class="card" style="margin-bottom:12px;padding:10px 14px;font-size:12px;color:var(--text2)">活动考核周期 · 对接 <span class="mono">GET /ops/perf/record/list</span> · 状态 SSOT：OPS 四态（IMS calc 批量核准见契约 §3 <b>BLOCKED</b>）</div>';
  let rows = '';
  PERF_CYCLES.forEach(function (c, i) {
    const tot = c.total != null ? c.total + ' 分' : '—';
    rows += '<tr><td class="mono num" style="color:var(--blue);font-size:11px">' + c.id + '</td><td style="font-weight:500">' + sens(c.target) + '</td><td>' + c.dept + '</td>' +
      '<td class="num" style="font-size:12px">' + c.period + '</td><td style="font-size:12px;color:var(--text2)">' + c.plan + '</td><td class="num">' + tot + '</td><td>' + perfStTag(c.st) + '</td><td>' + c.evaluator + '</td><td>' +
      (c.st === 'draft' ? '<button class="btn btn-pri btn-sm" onclick="perfExecCalculate(' + i + ')">自动算分</button><button class="btn btn-sec btn-sm" onclick="perfExecScore(' + i + ')">编辑</button>' :
        c.st === 'calculating' ? '<span class="csub">算分中…</span>' :
          c.st === 'calculated' ? '<button class="btn btn-pri btn-sm" onclick="perfExecScore(' + i + ')">评分/调整</button><button class="btn btn-sec btn-sm" onclick="perfExecConfirm(' + i + ')">确认结果</button>' :
            '<button class="btn btn-sec btn-sm" onclick="perfGoResult(\'' + c.period + '\')">查看考核结果</button>') + '</td></tr>';
  });
  h += tbl(['单号', '被考核人', '部门', '考核周期', '考核方案', '总分', '状态', '考核人', '操作'], rows);
  if (state.perfPendingPlan) {
    setTimeout(function () { perfExecCreate(state.perfPendingPlan); state.perfPendingPlan = null; }, 80);
  }
  return h;
};
PAGES.perfResult = function () {
  let h = pgHead('perfResult', '<button class="btn btn-sec" onclick="exportX(this,\'考核结果\',PERFS.length)">导出</button>');
  h += '<div class="hint" style="margin-bottom:10px;font-size:12px">仅展示 <b>已确认</b> 考核（OPS confirm · IMS PUBLISHED 映射 BLOCKED）</div>';
  h += perfResultTableHtml();
  return h;
};
PAGES.perfExam = function () {
  let h = pgHead('perfExam', '<button class="btn btn-pri" onclick="examPaperAdd()">' + ic('plus', 15) + '创建试卷</button>');
  return h + perfExamTab();
};
PAGES.perf = PAGES.perfScheme;
function perfSchemeEdit(pi) {
  const p = PERF_PLANS[pi];
  openDrawer('编辑考核方案 · ' + p.name, frow([
    { k: 'ename', label: '方案名称', type: 'text', req: true, val: p.name },
    { k: 'eweight', label: '指标权重说明', type: 'textarea', val: p.d, wide: true }
  ]), '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="perfSchemeEditSave(' + pi + ')">保存</button>', '480px');
}
function perfSchemeEditSave(pi) {
  if (!formValidate(['ename'])) return;
  PERF_PLANS[pi].name = $('#F_ename').value.trim();
  PERF_PLANS[pi].d = $('#F_eweight').value.trim();
  closeDrawer();
  renderPage();
  toast('方案已保存：' + PERF_PLANS[pi].name, 'success');
}
function perfLaunchCycle(pi) {
  const p = PERF_PLANS[pi];
  if (!p.on) { toast('请先启用考核方案', 'warn'); return; }
  state.perfPendingPlan = p.name;
  go('perfExec');
}
function perfExecCreate(prefPlan) {
  const body = frow([
    { k: 'etarget', label: '被考核人', type: 'select', req: true, opts: ['苏杳', '赵敏', '孙倩', '李澈', '王野'] },
    { k: 'eplan', label: '考核方案', type: 'select', req: true, val: prefPlan || PERF_PLANS[0].name, opts: PERF_PLANS.filter(function (x) { return x.on; }).map(function (x) { return x.name; }) },
    { k: 'eperiod', label: '考核周期', type: 'select', req: true, opts: ['2026 Q3', '2026-09', '2026 Q2'] },
    { k: 'estart', label: '周期开始', type: 'date', val: '2026-07-01' },
    { k: 'eend', label: '周期结束', type: 'date', val: '2026-09-30' }
  ]) + '<div class="hint" style="margin-top:6px">创建后调用 <span class="mono">POST /ops/perf/record/create</span>；同周期同员工不可重复（BR-031）</div>';
  openDrawer('创建考核', body, '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="perfExecCreateSubmit()">创建并进入草稿</button>', '520px');
}
function perfExecCreateSubmit() {
  if (!formValidate(['etarget', 'eplan', 'eperiod'])) return;
  const dup = PERF_CYCLES.some(function (c) { return c.target === $('#F_etarget').value && c.period === $('#F_eperiod').value && c.st !== 'confirmed'; });
  if (dup) { toast('该周期已有进行中的考核记录（BR-031）', 'error'); return; }
  const id = 'PR202609-' + String(100 + PERF_CYCLES.length).slice(-3);
  PERF_CYCLES.unshift({ id: id, plan: $('#F_eplan').value, period: $('#F_eperiod').value, target: $('#F_etarget').value, dept: '运营中心', evaluator: '何舟', st: 'draft', total: null, items: [] });
  closeDrawer();
  renderPage();
  toast('考核已创建：' + id + '（草稿）· 可点击「自动算分」', 'success');
}
function perfExecCalculate(i) {
  const c = PERF_CYCLES[i];
  c.st = 'calculating';
  renderPage();
  setTimeout(function () {
    c.st = 'calculated';
    c.items = [{ n: '指标 A', w: 40, val: 88, score: 85, adj: 0 }, { n: '指标 B', w: 35, val: 72, score: 78, adj: 0 }, { n: '指标 C', w: 25, val: 90, score: 92, adj: 0 }];
    c.total = Math.round(c.items.reduce(function (s, it) { return s + it.score * it.w / 100; }, 0));
    renderPage();
    toast('自动算分完成（POST /ops/perf/record/calculate）· 综合 ' + c.total + ' 分', 'success');
  }, 900);
}
function perfExecScore(i) {
  const c = PERF_CYCLES[i];
  if (!c.items.length && c.st === 'draft') { toast('请先执行自动算分', 'warn'); return; }
  let rows = '';
  c.items.forEach(function (it, j) {
    const fin = it.score + (it.adj || 0);
    rows += '<tr><td>' + it.n + '</td><td class="num">' + it.w + '%</td><td class="num">' + it.val + '</td><td class="num">' + it.score + '</td>' +
      '<td><input type="number" id="adj_' + i + '_' + j + '" value="' + (it.adj || 0) + '" style="width:64px;padding:4px 6px;border:1px solid var(--line2);border-radius:6px" onchange="perfExecAdjPreview(' + i + ',' + j + ')"></td>' +
      '<td class="num" id="fin_' + i + '_' + j + '">' + fin + '</td></tr>';
  });
  const body = '<div class="card" style="padding:12px;margin-bottom:12px;font-size:12.5px"><b>' + c.target + '</b> · ' + c.plan + ' · ' + c.period + '<br><span class="csub">考核人 ' + c.evaluator + ' · ' + perfStLabel(c.st) + '</span></div>' +
    tbl(['指标', '权重', '原始值', '自动得分', '人工调整(±20%)', '最终得分'], rows) +
    '<div class="hint" style="margin-top:8px">保存调整 → <span class="mono">PUT /ops/perf/record/adjust</span></div>';
  openDrawer('评分与调整 · ' + c.id, body, '<button class="btn btn-sec" onclick="closeDrawer()">取消</button><button class="btn btn-pri" onclick="perfExecScoreSave(' + i + ')">保存调整</button>', '640px');
}
function perfExecAdjPreview(i, j) {
  const c = PERF_CYCLES[i], it = c.items[j];
  const v = Number($('#adj_' + i + '_' + j).value) || 0;
  const max = Math.round(it.score * 0.2);
  if (Math.abs(v) > max) { toast('调整幅度不能超过 ±20%（基础分 ' + it.score + '）', 'error'); return; }
  it.adj = v;
  const el = $('#fin_' + i + '_' + j);
  if (el) el.textContent = it.score + v;
}
function perfExecScoreSave(i) {
  const c = PERF_CYCLES[i];
  c.items.forEach(function (it, j) {
    const inp = $('#adj_' + i + '_' + j);
    if (inp) it.adj = Number(inp.value) || 0;
    const max = Math.round(it.score * 0.2);
    if (Math.abs(it.adj) > max) { toast('指标「' + it.n + '」调整超 ±20%', 'error'); return; }
  });
  c.total = Math.round(c.items.reduce(function (s, it) { return s + (it.score + (it.adj || 0)) * it.w / 100; }, 0));
  c.st = 'calculated';
  closeDrawer();
  renderPage();
  toast('调整已保存 · 综合得分 ' + c.total + ' 分', 'success');
}
function perfExecConfirm(i) {
  const c = PERF_CYCLES[i];
  confirmDlg('确认考核结果？', c.target + ' · ' + c.period + ' · 综合得分 <b>' + c.total + '</b> 分。确认后锁定记录（POST /ops/perf/record/confirm），员工可在考核结果中查看。', '确认结果', function () {
    c.st = 'confirmed';
    const exists = PERFS.some(function (p) { return p.name === c.target && p.period === c.period; });
    if (!exists) {
      const g = c.total >= 95 ? 'S' : c.total >= 85 ? 'A' : c.total >= 75 ? 'B' : c.total >= 60 ? 'C' : 'D';
      PERFS.push({ name: c.target, dept: c.dept, period: c.period, kpi: c.total, adj: '0', score: c.total, g: g });
    }
    renderPage();
    toast('考核已确认 · 可前往「考核结果」查看排名', 'success');
  });
}
function perfGoResult(period) {
  state.tab.perfResultFilter = period;
  go('perfResult');
}
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
function alertPageMode() {
  if (state.page === 'alertRule') return '预警规则';
  if (state.page === 'alertLive') {
    const sub = state.tab.alertLive || 'live';
    if (sub === 'history') return '处理记录';
    if (sub === 'dedup') return '去重合并';
    return '实时预警';
  }
  return '实时预警';
}
function alertLiveTabsHtml() {
  const sub = state.tab.alertLive || 'live';
  return '<div class="tabs"><div class="tab' + (sub === 'live' ? ' on' : '') + '" onclick="state.tab.alertLive=\'live\';renderPage()">实时预警</div>' +
    '<div class="tab' + (sub === 'history' ? ' on' : '') + '" onclick="state.tab.alertLive=\'history\';renderPage()">处置记录</div>' +
    '<div class="tab' + (sub === 'dedup' ? ' on' : '') + '" onclick="state.tab.alertLive=\'dedup\';renderPage()">去重合并</div></div>';
}
PAGES.alertRule = PAGES.alertLive = PAGES.alertHistory = PAGES.alertDedup = function () {
  const cur = alertPageMode();
  let h = pgHead(state.page, cur === '预警规则' ? '<button class="btn btn-pri" onclick="alertRuleAdd()">' + ic('plus', 15) + '新建规则</button>' : '');
  if (state.page === 'alertLive') h += alertLiveTabsHtml();
  if (cur !== '预警规则') {
    const cnt = { 红: 0, 橙: 0, 黄: 0 };
    ALERTS.forEach(function (a) { cnt[a.lv]++; });
    h += '<div class="g3"><div class="card stat" style="border-left:3px solid var(--red)"><span class="l">红色预警（高危）</span><div class="n neg">' + cnt['红'] + '</div><div class="d">需立即处理</div></div>' +
      '<div class="card stat" style="border-left:3px solid var(--orange)"><span class="l">橙色预警（重要）</span><div class="n" style="color:var(--orange)">' + cnt['橙'] + '</div><div class="d">24h 内处理</div></div>' +
      '<div class="card stat" style="border-left:3px solid var(--yellow)"><span class="l">黄色预警（提示）</span><div class="n" style="color:#a07d00">' + cnt['黄'] + '</div><div class="d">纳入周报跟踪</div></div></div>';
    h += '<div class="hint" style="margin-bottom:8px">走查 #17：阈值配置在 <span class="btn-txt btn" onclick="go(\'collectThreshold\')">数据采集 → 阈值规则</span>；本页仅规则实例与处置。</div>';
  }
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
    if (ALERT_IDS.indexOf(state.page) >= 0) renderPage();
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
