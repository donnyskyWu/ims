import { createRequire } from 'module';

const require = createRequire('C:/Users/donny/.workbuddy/binaries/node/workspace/node_modules/');
const { chromium } = require('playwright');

const FILE = 'file:///D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html';

const browser = await chromium.launch({
  executablePath: 'C:/Users/donny/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe',
  args: ['--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
await page.goto(FILE, { waitUntil: 'load' });
await page.waitForTimeout(300);

const R = {};

/* ---- 1. 落地 = 模板列表（管理优先） ---- */
R.land = await page.evaluate(() => {
  go('queryTool');
  const c = document.getElementById('content');
  const t = c.textContent;
  return {
    landed: state.page,
    hasList: !!c.querySelector('.bi0-mine-card'),
    hasAddBtn: Array.from(c.querySelectorAll('button')).some(b => b.textContent.indexOf('新增查询模板') >= 0),
    hasExecOp: t.indexOf('执行') >= 0,
    hasEditOp: t.indexOf('编辑') >= 0,
    hasRowTpl: t.indexOf('IP 组周产出') >= 0,
    noOldTabs: t.indexOf('查询记录') < 0,
  };
});

/* ---- 2. 新增向导 · 第0步：选类型卡片 ---- */
R.wizType = await page.evaluate(() => {
  go('queryTool');
  queryToolOpenWizard();
  const b = document.getElementById('qtWizBody');
  const cards = Array.from(b.querySelectorAll('.qt-type-card')).map(x => x.textContent);
  return {
    drawerOpen: document.getElementById('drawer').classList.contains('on'),
    steps: b.querySelectorAll('.qt-wiz-step').length,
    hasDrillCard: cards.some(s => s.indexOf('分级下钻') >= 0),
    hasTraceCard: cards.some(s => s.indexOf('逐级穿透') >= 0),
    hasFlatHiddenHint: b.textContent.indexOf('FLAT') >= 0,
  };
});

/* ---- 3. 向导 · TRACE 分支：第2步出现 pathSteps 表 ---- */
R.wizTraceCfg = await page.evaluate(() => {
  go('queryTool');
  queryToolOpenWizard();
  queryToolSetWizardMode('TRACE');
  queryToolWizardNext();            // 0 -> 1
  queryToolWizardNext();            // 1 -> 2 (config)
  const b = document.getElementById('qtWizBody');
  const ths = Array.from(b.querySelectorAll('.qt-trace-path th')).map(x => x.textContent.trim());
  return {
    step: queryToolWizard().step,
    tableExists: !!b.querySelector('.qt-trace-path table'),
    ths,
    hasPathStepsTitle: b.textContent.indexOf('pathSteps') >= 0,
    hasDepthDerived: b.textContent.indexOf('depth 由 pathSteps 推导') >= 0,
  };
});

/* ---- 4. 向导 · DRILL 分支：第2步出现 levels 表 + 第3步展示与来源 ---- */
R.wizDrillCfg = await page.evaluate(() => {
  go('queryTool');
  queryToolOpenWizard();
  queryToolSetWizardMode('DRILL');
  queryToolWizardNext();            // 0 -> 1
  queryToolWizardNext();            // 1 -> 2 (config)
  const b = document.getElementById('qtWizBody');
  const drillTable = !!b.querySelector('.qt-drill-levels table');
  const hasAddBtn = Array.from(b.querySelectorAll('button')).some(x => x.textContent.indexOf('添加层级') >= 0);
  queryToolWizardNext();            // 2 -> 3 (展示与来源)
  const t = document.getElementById('qtWizBody').textContent;
  return {
    drillTable,
    hasAddBtn,
    step: queryToolWizard().step,
    step3HasDisplay: t.indexOf('结果展示') >= 0,
  };
});

/* ---- 5. 向导 · TRACE 第3步选源头 + 第4步试跑 ---- */
R.wizTraceRun = await page.evaluate(() => {
  go('queryTool');
  queryToolOpenWizard();
  queryToolSetWizardMode('TRACE');
  queryToolWizardNext();            // ->1
  queryToolWizardNext();            // ->2 config
  queryToolWizardNext();            // ->3 root/entry
  const rootText = document.getElementById('qtWizBody').textContent;
  const hasEntry = rootText.indexOf('/dc/trace/entry') >= 0;
  queryToolTracePickSource(0);
  queryToolWizardNext();            // ->4 preview
  queryToolWizardTryRun();
  const t = document.getElementById('qtWizBody').textContent;
  return {
    step: queryToolWizard().step,
    hasEntry,
    hasResult: queryToolEnsure().hasResult === true,
    hasSyncRunHint: t.indexOf('同步 run') >= 0 || t.indexOf('服务端按 pathSteps') >= 0,
    resultShown: t.indexOf('查询结果') >= 0,
  };
});

/* ---- 6. 行内「执行」进入执行页 + 同步 run 提示 ---- */
R.runView = await page.evaluate(() => {
  closeDrawer();
  go('queryTool');
  queryToolExecuteTemplate('QT-TPL-003');
  const c = document.getElementById('content');
  const t = c.textContent;
  return {
    view: state.tab.queryToolView,
    hasBack: t.indexOf('返回模板列表') >= 0,
    hasResult: t.indexOf('查询结果') >= 0,
    hasSyncRunHint: t.indexOf('同步 run') >= 0,
    hasQueryCost: t.indexOf('queryCostMs') >= 0,
  };
});

/* ---- 7. 已发布模板编辑 = 直接改（不另存草稿） ---- */
R.pubEdit = await page.evaluate(() => {
  closeDrawer();
  go('queryTool');
  const before = queryToolEnsureTemplates().length;
  queryToolOpenWizard('QT-TPL-003');           // PUBLISHED
  queryToolWizardPrev();                       // 2 -> 1 basic
  const t = document.getElementById('qtWizBody').textContent;
  queryToolWizardSaveDraft(true);              // 直接改已发布版本
  const tpl = queryToolTemplateByCode('QT-TPL-003');
  const after = queryToolEnsureTemplates().length;
  return {
    step: queryToolWizard().step,
    hasDirectEdit: t.indexOf('直接改') >= 0,
    sameTemplate: tpl !== null && before === after,
    stillPublished: tpl && tpl.status === 'PUBLISHED',
  };
});

/* ---- 8. 陈旧词扫描 ---- */
R.stale = await page.evaluate(() => {
  closeDrawer();
  go('queryTool');
  const t = document.getElementById('content').textContent;
  return {
    noFixedDepthSelect: t.indexOf('穿透深度') < 0,
  };
});

/* ---- 9. 控件样式统一（.qt-wiz 内 select/input/textarea 与抽屉表单基线一致） ---- */
R.styleUniform = await page.evaluate(() => {
  closeDrawer();
  go('queryTool');
  queryToolOpenWizard();
  queryToolSetWizardMode('TRACE');
  queryToolWizardNext();            // ->1 基本信息（含 fld 输入/多行文本）= 基线
  const cs = el => el ? getComputedStyle(el) : null;
  const b1 = document.getElementById('qtWizBody');
  const eIn = b1.querySelector('.fld input:not([type=radio])');
  const eTa = b1.querySelector('.fld textarea');
  const sIn = cs(eIn), sTa = cs(eTa);
  // 仍在文档中时读取基线字符串（导航后旧节点会 detach，computed 变空）
  const base = {
    h: sIn && sIn.height, r: sIn && sIn.borderRadius, b: sIn && sIn.borderTopColor,
    f: sIn && sIn.fontSize, taMin: sTa && sTa.minHeight,
  };
  queryToolWizardNext();            // ->2 配置载荷（qt-qctl 下拉 + 关键词输入 + 表内 select）
  const b2 = document.getElementById('qtWizBody');
  const eSel = b2.querySelector('select.qt-qctl') || b2.querySelector('.qb-row select');
  const eKw = b2.querySelector('input.qt-qctl') || b2.querySelector('.qb-row input');
  const eAny = b2.querySelector('table select');
  const sSel = cs(eSel), sKw = cs(eKw), sAny = cs(eAny);
  const all = [sSel, sKw, sAny];
  return {
    found: { fldInput: !!eIn, fldTextarea: !!eTa, ctlSel: !!eSel, kwInput: !!eKw, anySel: !!eAny },
    base, applied: { selH: sSel && sSel.height, kwH: sKw && sKw.height, anyH: sAny && sAny.height },
    sameH: all.every(x => x && x.height === base.h) && base.h === '34px',
    sameRadius: all.every(x => x && x.borderRadius === base.r),
    sameBorder: all.every(x => x && x.borderTopColor === base.b),
    sameFont: all.every(x => x && x.fontSize === base.f),
  };
});

/* ---- 10. AIR 知识库开放（v2.6.31：四叶 / 分类 / 系统转入 / 上传三方式） ---- */
R.airKb = await page.evaluate(() => {
  closeDrawer();
  state.role = 'R11';
  renderPage();
  const navTxt = (document.querySelector('.side, #side, nav') || document.getElementById('content')).textContent;
  const aiGroup4 = document.getElementById('content');
  // 直达知识库页
  go('airKb');
  const c = document.getElementById('content');
  const t = c.textContent;
  const hasToolbar = ['新增知识库', '分类管理', '上传资料', '从系统转入'].every(k => t.indexOf(k) >= 0);
  // v2.6.32 文件管理期：工具栏不应含「底座巡检」，页面不应含「检索演示」/「RAGFlow」
  const noRagflow = t.indexOf('底座巡检') < 0 && t.indexOf('检索演示') < 0 && t.indexOf('RAGFlow') < 0;
  // 侧栏四叶（AIR 组）
  const side = document.querySelector('.sidebar, #sidebar, .side');
  const sideHasKb = side ? (side.textContent.indexOf('知识库') >= 0 && side.textContent.indexOf('技能库') >= 0) : null;
  // 分类管理抽屉
  kbCatManage();
  const catDrawer = document.getElementById('dr-body').textContent;
  const catHasTree = catDrawer.indexOf('库内两级树') >= 0 && catDrawer.indexOf('新增分类') >= 0;
  closeDrawer();
  // 上传：三方式切换
  kbUpload();
  const upTabs = document.getElementById('dr-body').textContent;
  const hasFileTab = upTabs.indexOf('文件上传') >= 0;
  kbUpMode('url');
  const hasUrlTab = document.getElementById('dr-body').textContent.indexOf('URL 地址') >= 0;
  kbUpMode('text');
  const hasTextTab = document.getElementById('dr-body').textContent.indexOf('正文') >= 0;
  closeDrawer();
  // 从系统转入：4 步向导
  kbTransfer();
  const w0 = document.getElementById('kbWizBody');
  const steps0 = w0 ? w0.querySelectorAll('.qt-wiz-step').length : 0;
  const hasSrcTrain = document.getElementById('dr-body').textContent.indexOf('培训资料库') >= 0;
  kbTransferSetSource('TRAIN');   // -> step1 勾选
  const hasChk = document.querySelectorAll('#dr-body input[type=checkbox]').length;
  kbTransferToggle(101); kbTransferToggle(102);
  const picked = Object.keys(KB_WIZ.picked).length;
  kbTransferNext();               // -> step2 目标
  const hasTarget = document.getElementById('dr-body').textContent.indexOf('目标知识库') >= 0;
  kbTransferNext();               // -> step3 摘要
  const hasSummary = document.getElementById('dr-body').textContent.indexOf('转入摘要') >= 0;
  closeDrawer();
  // 重定向：airKey 仍应回技能库
  go('airKey');
  const keyRedirect = (document.getElementById('content').textContent.indexOf('技能库') >= 0);
  go('airKb');
  return {
    hasToolbar, noRagflow, sideHasKb, catHasTree,
    hasFileTab, hasUrlTab, hasTextTab,
    steps4: steps0 === 4, hasSrcTrain, hasChk: hasChk >= 3, picked2: picked === 2, hasTarget, hasSummary,
    keyRedirect,
    kbNavIds: (typeof AIR_NAV_IDS !== 'undefined' ? AIR_NAV_IDS.slice() : []),
  };
});

console.log(JSON.stringify(R, null, 2));

const checks = [
  ['land.landed', R.land.landed === 'queryTool'],
  ['land.hasList', R.land.hasList === true],
  ['land.hasAddBtn', R.land.hasAddBtn === true],
  ['land.hasExecOp', R.land.hasExecOp === true],
  ['land.hasRowTpl', R.land.hasRowTpl === true],
  ['land.noOldTabs', R.land.noOldTabs === true],
  ['wizType.drawerOpen', R.wizType.drawerOpen === true],
  ['wizType.steps=6', R.wizType.steps === 6],
  ['wizType.hasDrillCard', R.wizType.hasDrillCard === true],
  ['wizType.hasTraceCard', R.wizType.hasTraceCard === true],
  ['wizType.flatHint', R.wizType.hasFlatHiddenHint === true],
  ['wizTraceCfg.tableExists', R.wizTraceCfg.tableExists === true],
  ['wizTraceCfg.hasPathStepsTitle', R.wizTraceCfg.hasPathStepsTitle === true],
  ['wizTraceCfg.hasDepthDerived', R.wizTraceCfg.hasDepthDerived === true],
  ['wizDrillCfg.drillTable', R.wizDrillCfg.drillTable === true],
  ['wizDrillCfg.hasAddBtn', R.wizDrillCfg.hasAddBtn === true],
  ['wizDrillCfg.step3HasDisplay', R.wizDrillCfg.step3HasDisplay === true],
  ['wizTraceRun.hasEntry', R.wizTraceRun.hasEntry === true],
  ['wizTraceRun.hasResult', R.wizTraceRun.hasResult === true],
  ['wizTraceRun.resultShown', R.wizTraceRun.resultShown === true],
  ['runView.view=run', R.runView.view === 'run'],
  ['runView.hasBack', R.runView.hasBack === true],
  ['runView.hasResult', R.runView.hasResult === true],
  ['runView.hasSyncRunHint', R.runView.hasSyncRunHint === true],
  ['pubEdit.hasDirectEdit', R.pubEdit.hasDirectEdit === true],
  ['pubEdit.sameTemplate', R.pubEdit.sameTemplate === true],
  ['pubEdit.stillPublished', R.pubEdit.stillPublished === true],
  ['stale.noFixedDepthSelect', R.stale.noFixedDepthSelect === true],
  ['style.foundCtl', R.styleUniform.found.ctlSel === true && R.styleUniform.found.kwInput === true],
  ['style.sameH34', R.styleUniform.sameH === true],
  ['style.sameRadius', R.styleUniform.sameRadius === true],
  ['style.sameBorder', R.styleUniform.sameBorder === true],
  ['style.sameFont', R.styleUniform.sameFont === true],
  ['airKb.nav4', R.airKb.kbNavIds.length === 4 && R.airKb.kbNavIds.indexOf('airKb') >= 0],
  ['airKb.toolbar', R.airKb.hasToolbar === true],
  ['airKb.noRagflow', R.airKb.noRagflow === true],
  ['airKb.sideHasKb', R.airKb.sideHasKb === true],
  ['airKb.catDrawer', R.airKb.catHasTree === true],
  ['airKb.upFile', R.airKb.hasFileTab === true],
  ['airKb.upUrl', R.airKb.hasUrlTab === true],
  ['airKb.upText', R.airKb.hasTextTab === true],
  ['airKb.wiz4steps', R.airKb.steps4 === true],
  ['airKb.wizSrc', R.airKb.hasSrcTrain === true],
  ['airKb.wizChk', R.airKb.hasChk === true],
  ['airKb.wizPicked', R.airKb.picked2 === true],
  ['airKb.wizTarget', R.airKb.hasTarget === true],
  ['airKb.wizSummary', R.airKb.hasSummary === true],
  ['airKb.keyRedirect', R.airKb.keyRedirect === true],
];
const bad = checks.filter(c => !c[1]).map(c => c[0]);
console.log('\nchecks:', checks.length, '| failed:', bad.length, bad.length ? '=> ' + bad.join(', ') : '');
console.log('pageErrors:', JSON.stringify(pageErrors));

await browser.close();