import fs from 'fs';
import { createRequire } from 'module';
const require = createRequire('C:/Users/donny/.workbuddy/binaries/node/workspace/node_modules/');
const { chromium } = require('playwright');

const FILE = 'file:///D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html';
const browser = await chromium.launch({ executablePath: 'C:/Users/donny/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const perr = [];
page.on('pageerror', e => perr.push(e.message));
await page.goto(FILE, { waitUntil: 'load' });

const checks = [];
function chk(name, cond, extra) { checks.push({ name, pass: !!cond, extra: extra || '' }); }

// ---- helper: get rendered text of current page / drawer ----
const pageText = () => page.evaluate(() => document.getElementById('content').innerText);
const drawerText = () => page.evaluate(() => (document.getElementById('drawer').classList.contains('on') ? document.getElementById('drawer').innerText : ''));
const drawerTitle = () => page.evaluate(() => document.getElementById('dr-title').textContent);

// ================= 1. 工作任务登记：三 Tab + 发布账号列 =================
await page.evaluate(() => go('contentWork'));
let t = await pageText();
chk('WT 三Tab-任务登记', t.includes('任务登记'));
chk('WT 三Tab-任务执行情况', t.includes('任务执行情况'));
chk('WT 三Tab-任务管理', t.includes('任务管理'));
chk('WT 发布账号列', t.includes('发布账号'));
await page.evaluate(() => { state.tab.contentWork = 'execution'; renderPage(); });
t = await pageText();
chk('WT-execution 节点粒度表(节点名称)', t.includes('节点名称'));

// ================= 1b. 任务管理 Tab：两级合并表头 + 日期 rowspan =================
await page.evaluate(() => { state.tab.contentWork = 'matrix'; renderPage(); });
const mx = await page.evaluate(() => {
  const table = document.querySelector('table.wt-matrix');
  if (!table) return { found: false };
  const hg = table.querySelector('thead tr.hg');
  const hs = table.querySelector('thead tr.hs');
  return {
    found: true,
    group: Array.from(hg.querySelectorAll('th')).map(th => ({ txt: th.textContent.trim(), colspan: th.getAttribute('colspan') })),
    sub: Array.from(hs.querySelectorAll('th')).map(th => th.textContent.trim()),
    bodyRows: table.querySelectorAll('tbody tr').length,
    dateCells: Array.from(table.querySelectorAll('tbody td.date-cell')).map(td => ({ txt: td.textContent.trim(), rowspan: td.getAttribute('rowspan') })),
    plans: Array.from(table.querySelectorAll('.plan-badge')).map(b => b.textContent.trim()),
    wins: Array.from(table.querySelectorAll('.win-badge')).map(b => b.textContent.trim()),
  };
});
chk('MX 矩阵表存在', mx.found);
chk('MX 组表头「赛事信息」colspan=5', mx.found && mx.group[0] && mx.group[0].txt === '赛事信息' && mx.group[0].colspan === '5', JSON.stringify(mx.group && mx.group[0]));
chk('MX 作者列组 colspan=4 + 作者【组-组长】格式', mx.found && mx.group.length === 3 && mx.group.slice(1).every(g => g.colspan === '4' && /【.+-.+】/.test(g.txt)), JSON.stringify(mx.group && mx.group.map(g => g.txt)));
chk('MX 子表头 5 固定列 + 每作者 4 子列', mx.found && mx.sub.slice(0, 5).join(',') === '日期,场次,赛事,比赛名称,比赛时间' && mx.sub.slice(5).join(',') === '营销计划,直播时间,销售平台,红黑,营销计划,直播时间,销售平台,红黑', JSON.stringify(mx.sub));
chk('MX 日期列 rowspan 纵向合并(9/18 跨 2 行)', mx.found && mx.dateCells.length === 2 && mx.dateCells[0].rowspan === '2' && mx.dateCells[1].rowspan === '1', JSON.stringify(mx.dateCells));
chk('MX 营销计划徽章中文化(直播公推/付费销售)', mx.found && mx.plans.includes('直播公推') && mx.plans.includes('付费销售'), JSON.stringify(mx.plans));
chk('MX 红黑徽章中文化(红/黑)', mx.found && mx.wins.includes('红') && mx.wins.includes('黑'), JSON.stringify(mx.wins));

// ================= 2. 我的任务（页内 Tab：我的任务 / 全部任务）=================
await page.evaluate(() => go('contentTask'));
t = await pageText();
chk('我的任务标题', t.includes('我的任务'));
chk('我的任务含执行入口', t.includes('执行') && t.includes('查看详情'));
chk('内容生产含「全部任务」页内 Tab', t.includes('全部任务'));
// v2.6.33：「全部任务」由独立菜单改为页内 Tab（不再 go('contentTaskAll')）
chk('「全部任务」不再是侧栏菜单', (await page.evaluate(() => typeof MODS !== 'undefined' && !MODS.contentTaskAll)));
await page.evaluate(() => { setTab('contentTask', '全部任务'); renderPage(); });
t = await pageText();
chk('全部任务 Tab 含执行人筛选', t.includes('全部执行人') || t.includes('执行人'));
chk('全部任务 Tab 无「执行」入口', !t.includes('>执行<'));

// ================= 4. 内容生产：SOP 审核已移除（v2.6.33）=================
await page.evaluate(() => go('contentSop'));
t = await pageText();
chk('SOP 管理页存在', t.includes('SOP') || t.length > 100);
chk('SOP 管理页无「待审核任务」按钮', !t.includes('待审核任务'));
chk('SOP 管理页无「提交审核」动作', !t.includes('提交审核'));
chk('「SOP审核」不再是侧栏菜单', (await page.evaluate(() => typeof MODS !== 'undefined' && !MODS.contentSopReview)));
chk('SOP 审核页函数已移除', (await page.evaluate(() => typeof PAGES.contentSopReview === 'undefined' && typeof sopReviewDetail === 'undefined')));

// ================= 3. 任务详情抽屉：只读 + 仅返回 =================
await page.evaluate(() => { go('contentTask'); taskDetail(0); });
let dt = await drawerText(); let dtitle = await drawerTitle();
chk('任务详情抽屉标题', dtitle.includes('任务详情'));
chk('任务详情-任务名称字段', dt.includes('任务名称'));
chk('任务详情-节点名称字段', dt.includes('节点名称'));
chk('任务详情-执行人字段', dt.includes('执行人'));
chk('任务详情-只读(仅返回按钮)', (await page.evaluate(() => document.getElementById('dr-foot').innerText)).trim() === '返回', 'foot=' + (await page.evaluate(() => document.getElementById('dr-foot').innerText)));
await page.evaluate(() => closeDrawer());

// ================= 5. 内容编辑弹窗：玩法区 + 工具栏 =================
await page.evaluate(() => { go('contentList'); state.opsContentEditIdx = 0; opsContentEdit(0, state.opsEditTaskId); });
dt = await drawerText();
chk('编辑-玩法Tab竞足', dt.includes('竞足'));
chk('编辑-玩法Tab传足', dt.includes('传足'));
chk('编辑-玩法Tab北单', dt.includes('北单'));
chk('编辑-玩法Tab足球', dt.includes('足球'));
chk('编辑-一键排版', dt.includes('一键排版'));
chk('编辑-AI 排版', dt.includes('AI 排版'));
chk('编辑-选择版式模板', dt.includes('选择版式模板'));
chk('编辑-付费/免费双栏', dt.includes('付费') && dt.includes('免费'));
chk('编辑-IP组只读', dt.includes('任务驱动只读'));

// ================= 6. 玩法区状态机：真实 DOM 点击 U1 / U3 / U6 =================
const clickByText = async (text) => page.evaluate((tx) => {
  const els = Array.from(document.querySelectorAll('#drawer button, #drawer .tab, #drawer .btn'));
  const el = els.find(e => (e.innerText || '').trim() === tx);
  if (el) { el.click(); return true; } return false;
}, text);
const getPlay = () => page.evaluate(() => ({ len: state.opsEditScheme.length, conf: state.opsEditPlayConfirmed, tab: state.opsEditPlayTab }));

await page.evaluate(() => { state.opsEditPlayTab = 1; state.opsEditScheme = [{ scheduleId: 'S1', homeName: 'A', awayName: 'B', matchType: 1 }]; state.opsEditPlayConfirmed = true; rerenderDrawer(); });
let p0 = await getPlay();
chk('玩法区-重绘保留状态(keepState)', p0.len === 1 && p0.conf === true, JSON.stringify(p0)); // keepState fix

await clickByText('竞足');  // 切到竞足（U1 清空）
await page.waitForTimeout(80);
let p1 = await getPlay();
chk('U1 切换Tab清空未确认玩法', p1.len === 0 && p1.conf === false, JSON.stringify(p1));

// 加一场
const added = await page.evaluate(() => { const b = Array.from(document.querySelectorAll('#drawer button')).find(e => (e.innerText || '').includes('曼联 VS 切尔西')); if (b) { b.click(); return true; } return false; });
await page.waitForTimeout(80);
let p2 = await getPlay();
chk('U3 加场写入matchScheme', added && p2.len === 1, 'added=' + added + ' ' + JSON.stringify(p2));

// 确定玩法
const conf = await clickByText('确定玩法');
await page.waitForTimeout(80);
let p3 = await getPlay();
chk('U4/确认玩法 panduan=true', p3.conf === true, JSON.stringify(p3));

// 删除至 0 场（U6）— 行内「删除」为 <span class="btn-txt btn">
const rm = await page.evaluate(() => {
  const b = Array.from(document.querySelectorAll('#drawer .btn, #drawer button')).find(e => (e.innerText || '').trim() === '删除');
  if (b) { b.click(); return true; } return false;
});
await page.waitForTimeout(80);
let p4 = await getPlay();
chk('U6 删至0场回未确认态', rm && p4.len === 0 && p4.conf === false, 'rm=' + rm + ' ' + JSON.stringify(p4));

// ================= 7. AI 排版弹窗 =================
await page.evaluate(() => { opsAiTypesetDialog(0); });
dt = await drawerText();
chk('AI排版-固定AUTO说明', dt.includes('AUTO') || dt.includes('自动'));
chk('AI排版-对比Tab', dt.includes('排版前') || dt.includes('排版后'));

// ================= 8. 审核抽屉 steps =================
await page.evaluate(() => { go('contentReview'); opsReviewView(0); });
dt = await drawerText(); dtitle = await drawerTitle();
chk('审核抽屉标题', dtitle.includes('审核'));
chk('审核-审核流程steps', dt.includes('审核流程') || dt.includes('一级审核') || dt.includes('二级审核'));
chk('审核-意见输入', dt.includes('意见'));
chk('审核-通过/驳回按钮', dt.includes('通过') && dt.includes('驳回'));

// ================= 9. 计划页（已移除营销计划区） =================
await page.evaluate(() => go('contentPlan'));
t = await pageText();
chk('计划页-不再有营销计划区', !t.includes('营销计划'));
chk('计划页-保留计划列表', t.includes('计划列表'));
chk('计划页-新增计划按钮', t.includes('新增计划'));
chk('计划页-无「新增营销计划」按钮', !t.includes('新增营销计划'));

// ================= 10. 任务执行页 nodeType =================
await page.evaluate(() => go('contentTaskExecute'));
t = await pageText();
chk('执行页-节点类型', t.includes('节点类型') || t.includes('内容生成') || t.includes('普通节点'));

// ================= 11. 版式库导入三Tab =================
await page.evaluate(() => { go('contentLayout'); contentLayoutImport(); });
dt = await drawerText();
chk('版式导入三Tab', (dt.includes('URL') || dt.includes('链接')) && (dt.includes('MHTML') || dt.includes('mhtml')) && dt.includes('HTML'));

// ================= 12. BI0 四域 + 报表管理（DW 借鉴修正 2026-10-03） =================
// 12a 指标管理：分类 / 计算频率 列
await page.evaluate(() => go('bi0Metric'));
let bt = await pageText();
chk('BI0-指标管理 表头含「分类」', bt.includes('分类'));
chk('BI0-指标管理 表头含「计算频率」', bt.includes('计算频率'));
chk('BI0-指标管理 含指标分类值', bt.includes('内容表现') || bt.includes('财务效率'));
chk('BI0-指标管理 含频率值', bt.includes('每日') || bt.includes('实时'));
chk('BI0-指标管理 筛选含分类下拉', bt.includes('全部分类'));

// 12b 指标管理抽屉：分类 + 计算频率字段
await page.evaluate(() => bi0MetricEdit(-1));
dt = await drawerText();
chk('BI0-指标抽屉 含「指标分类」', dt.includes('指标分类'));
chk('BI0-指标抽屉 含「计算频率」', dt.includes('计算频率'));
chk('BI0-指标抽屉 单位字段', dt.includes('单位'));
await page.evaluate(() => closeDrawer());

// 12c 报表中心（原「标准报表」· v2.6.27 走查 #21 更名）：统一筛选条 + 逐张差异化
await page.evaluate(() => go('bi0Report'));
bt = await pageText();
chk('BI0-报表中心 统一筛选-时间维度', bt.includes('时间维度'));
chk('BI0-报表中心 统一筛选-日期范围', bt.includes('日期范围'));
chk('BI0-报表中心 导出 PDF', bt.includes('PDF'));
const repProbe = [];
for (const slug of ['unified-account', 'live-duration', 'cost-allocation', 'roi', 'video-output', 'account-status', 'team-config', 'account-alert']) {
  await page.evaluate((s) => bi0OpenReport(s), slug);
  await page.waitForTimeout(40);
  const info = await page.evaluate(() => ({
    body: document.getElementById('dr-body').innerText,
    svg: document.querySelectorAll('#dr-body svg').length,
    rows: document.querySelectorAll('#dr-body tbody tr').length,
  }));
  repProbe.push({ slug, ...info });
  await page.evaluate(() => closeDrawer());
}
chk('BI0-八张报表 均有 SVG 图表', repProbe.every(r => r.svg >= 1), JSON.stringify(repProbe.map(r => r.svg)));
chk('BI0-八张报表 均有明细行', repProbe.every(r => r.rows >= 3), JSON.stringify(repProbe.map(r => r.rows)));
const uniqBodies = new Set(repProbe.map(r => r.body.slice(0, 200)));
chk('BI0-八张报表 内容逐张差异化(非同一模板)', uniqBodies.size === 8, 'uniq=' + uniqBodies.size);
chk('BI0-直播时长报表 含时长口径', repProbe.find(r => r.slug === 'live-duration').body.includes('时长'));
chk('BI0-ROI报表 含 ROI 字样', repProbe.find(r => r.slug === 'roi').body.includes('ROI'));
chk('BI0-成本分摊报表 含成本占比', repProbe.find(r => r.slug === 'cost-allocation').body.includes('成本占比'));

// 12d 自定义查询：分组/排序/限制 + SQL 复制 + 结果图表
await page.evaluate(() => { go('bi0Query'); state.q.bi0Executed = true; state.q.bi0ResultTab = 'chart'; renderPage(); });
bt = await pageText();
chk('BI0-自定义查询 分组 GROUP BY', bt.includes('GROUP BY'));
chk('BI0-自定义查询 排序 ORDER BY', bt.includes('ORDER BY'));
chk('BI0-自定义查询 结果行数 LIMIT', bt.includes('结果行数'));
chk('BI0-自定义查询 复制 SQL 按钮', bt.includes('复制 SQL'));
const qSvg = await page.evaluate(() => document.querySelectorAll('#content svg').length);
chk('BI0-自定义查询 图表 Tab 渲染 SVG', qSvg >= 1, 'svg=' + qSvg);
chk('BI0-自定义查询 结果行含耗时/截断说明', bt.includes('上限 1000 行未截断') || bt.includes('耗时'));

// 12e 指标分析：趋势 Tab 真图表
await page.evaluate(() => { go('bi0Analysis'); bi0AnalysisRun(); state.tab.bi0AnalysisView = 'trend'; renderPage(); });
const anaSvg = await page.evaluate(() => document.querySelectorAll('#content svg').length);
bt = await pageText();
chk('BI0-指标分析 趋势 Tab 渲染 SVG 图表', anaSvg >= 1, 'svg=' + anaSvg);
chk('BI0-指标分析 趋势 Tab 不再为占位块', !bt.includes('当前指标结果中未检测到数值列时，Y 轴/数值字段下拉禁用并展示告警') || anaSvg >= 1);

// 12f 大屏（v2.6.27 走查 #21：大屏归为报表类型 dashboard，「大屏配置」独立页退役 → 归一化到报表管理 biList）
await page.evaluate(() => go('bi0Screen'));
const screenNorm = await page.evaluate(() => state.page);
chk('BI0-大屏 退役：go(bi0Screen) 归一化到报表管理', screenNorm === 'biList');
await page.evaluate(() => go('bi0ScreenConfig'));
const screenCfgNorm = await page.evaluate(() => state.page);
chk('BI0-大屏 退役：go(bi0ScreenConfig) 归一化到报表管理', screenCfgNorm === 'biList');
bt = await pageText();
chk('BI0-报表管理 大屏类型提示', bt.includes('大屏'));
// 全屏大屏（P5）仍保留：暗色全屏页
const fsInfo = await page.evaluate(() => {
  biFullscreen(2);
  const fs = document.querySelector('.fs-page');
  const n = fs ? fs.querySelectorAll('svg').length : 0;
  if (fs) fs.remove();
  return { exists: !!fs, svg: n };
});
chk('BI0-全屏大屏 .fs-page 存在', fsInfo.exists);
chk('BI0-全屏大屏 含 SVG 图表', fsInfo.svg >= 1);

// ================= 12g 报表域 IA 重构（v2.6.27 走查 #21）=================
// ① 改名：报表中心
await page.evaluate(() => go('bi0Report'));
const renameInfo = await page.evaluate(() => ({
  modName: (MODS.bi0Report || {}).name,
  h1: (document.querySelector('#content h1') || {}).textContent,
  tab: bi0PageTab(),
}));
chk('#21-改名 报表中心·MODS', renameInfo.modName === '报表中心');
chk('#21-改名 报表中心·H1', renameInfo.h1 === '报表中心');
chk('#21-改名 报表中心·页Tab', renameInfo.tab === '报表中心');
// ② 合并菜单：数据报表 = 2 叶
const mergeInfo = await page.evaluate(() => {
  let g = null; GROUPS.forEach(function (grp) { (grp[1] || []).forEach(function (x) { if (x && x.type === 'sub' && x.id === 'biReportMgmt') g = x; }); });
  return { children: g ? g.children : [], navIds: BI_REPORT_NAV_IDS };
});
chk('#21-合并 数据报表=2叶', mergeInfo.children.length === 2);
chk('#21-合并 含 biList/bi0Report', mergeInfo.children.indexOf('biList') >= 0 && mergeInfo.children.indexOf('bi0Report') >= 0);
chk('#21-合并 设计器不在侧栏', mergeInfo.children.indexOf('biDesign') < 0);
// ③ 大屏退役 + 报表类型 pills
const addInfo = await page.evaluate(() => {
  go('biList'); biAdd();
  const dr = document.getElementById('dr-body');
  const pills = Array.from(dr.querySelectorAll('.pills .pill')).map(x => x.textContent.trim());
  return { pills: pills, radios: dr.querySelectorAll('input[name="P_type"]').length };
});
chk('#21-新建抽屉 报表类型 pills=2', addInfo.radios === 2);
chk('#21-新建抽屉 含报表/大屏', addInfo.pills.some(x => x.includes('报表')) && addInfo.pills.some(x => x.includes('大屏')));
const addSubmit = await page.evaluate(() => {
  const pill = Array.from(document.querySelectorAll('#dr-body input[name="P_type"]')).find(x => x.value.indexOf('大屏') >= 0);
  if (pill) { pill.checked = true; pill.dispatchEvent(new Event('change', { bubbles: true })); }
  const n = document.getElementById('F_name'); if (n) n.value = '#21断言-大屏';
  const before = BI_REPORTS.length; biAddSubmit();
  const added = BI_REPORTS[BI_REPORTS.length - 1] || {};
  return { grew: BI_REPORTS.length > before, type: added.type, page: state.page };
});
chk('#21-新建大屏 type=DASHBOARD', addSubmit.type === 'dashboard');
chk('#21-新建大屏 落设计器', addSubmit.page === 'biDesign');
// ④ 发布去向二选一
const pubInfo = await page.evaluate(() => {
  state.tab.biPubDst = 'center'; biPubDlg('运营日报', 1);
  const dr = document.getElementById('dr-body');
  const a = { hasDst: dr.textContent.includes('发布去向'), centerNoMenu: !dr.textContent.includes('菜单配置') };
  biPubSetDst('menu');
  const b = { menuCfg: dr.textContent.includes('菜单配置'), sysMenu: dr.textContent.includes('sys_menu') || dr.textContent.includes('ims_report_menu') };
  closeDrawer();
  return { a, b };
});
chk('#21-发布 含①发布去向', pubInfo.a.hasDst);
chk('#21-发布 选中心无菜单配置', pubInfo.a.centerNoMenu);
chk('#21-发布 选菜单出现菜单配置', pubInfo.b.menuCfg && pubInfo.b.sysMenu);
// ⑤ 图表 Tab 双路径 + 柱/折/饼
const chartInfo = await page.evaluate(() => {
  go('bi0Query'); setTab('bi0Query', 'saved'); state.q.bi0ResultTab = 'list'; bi0QueryExecuteSaved();
  const dr = () => document.getElementById('dr-body');
  bi0QuerySetResultTab('chart');
  const drawerChart = !!dr().querySelector('.bi0-chart-bar');
  bi0QuerySetChart('折线图'); const line = dr().querySelectorAll('.bi0-chart-stage svg polyline').length;
  bi0QuerySetChart('饼图'); const pie = dr().querySelectorAll('.bi0-chart-stage svg circle').length;
  bi0QuerySetChart('柱状图'); const bar = dr().querySelectorAll('.bi0-chart-stage svg rect').length;
  closeDrawer();
  go('bi0Query'); setTab('bi0Query', 'builder'); state.q.bi0ResultTab = 'chart'; state.q.bi0ChartType = '柱状图'; bi0QueryExecute();
  const inlineChart = !!document.querySelector('#content .bi0-chart-bar');
  return { drawerChart, line, pie, bar, inlineChart };
});
chk('#21-图表 抽屉(我的查询)图表Tab可开', chartInfo.drawerChart);
chk('#21-图表 折线图 polyline', chartInfo.line === 1);
chk('#21-图表 饼图 circle', chartInfo.pie >= 4);
chk('#21-图表 柱状图 rect', chartInfo.bar === 3);
chk('#21-图表 内联页图表Tab可开', chartInfo.inlineChart);

await browser.close();

// ---- report ----
const fail = checks.filter(c => !c.pass);
console.log('=== 文本/交互断言 ===');
checks.forEach(c => console.log((c.pass ? ' PASS ' : ' FAIL ') + c.name + (c.extra ? '  [' + c.extra + ']' : '')));
console.log('\n合计: ' + checks.length + ' | 通过: ' + (checks.length - fail.length) + ' | 失败: ' + fail.length);
console.log('pageerror: ' + perr.length);
perr.forEach(e => console.log('  ' + e));
process.exit(fail.length ? 1 : 0);