import fs from 'fs';
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

/* ---- 1. 改名：标准报表 → 报表中心（四处证据） ---- */
R.rename = await page.evaluate(() => {
  go('bi0Report');
  const c = document.getElementById('content');
  const modName = (MODS.bi0Report || {}).name;
  const sidebarText = document.getElementById('sidebar') ? document.getElementById('sidebar').textContent : '';
  return {
    modName,
    pageTitle: state.page,
    headerText: (c.querySelector('.pg-title, .hd h1, h1') || {}).textContent || '',
    pageHasOldStandard: c.textContent.indexOf('标准报表') >= 0,
    /* 页面标题/菜单名是否仍残留「标准报表」称谓（排除「八张标准报表」这类描述性短语） */
    headerIsReportCenter: (c.querySelector('h1') || {}).textContent === '报表中心',
    sidebarHasOldStandard: /标准报表/.test(sidebarText),
    sidebarHasReportCenter: /报表中心/.test(sidebarText),
    pageTabLabel: bi0PageTab(),
  };
});

/* ---- 2. 合并菜单：侧栏「数据报表」下仅 2 叶 ---- */
R.menuMerge = await page.evaluate(() => {
  /* GROUPS 为 [label, [ids|sub]] 的数组结构，需穿透查找 biReportMgmt 子组 */
  let g = null;
  GROUPS.forEach(function (grp) {
    (grp[1] || []).forEach(function (x) { if (x && x.type === 'sub' && x.id === 'biReportMgmt') g = x; });
  });
  const sb = document.getElementById('sidebar');
  return {
    groupChildren: g ? g.children : null,
    childCount: g ? g.children.length : 0,
    hasBiList: g ? g.children.indexOf('biList') >= 0 : false,
    hasBi0Report: g ? g.children.indexOf('bi0Report') >= 0 : false,
    hasBiDesign: g ? g.children.indexOf('biDesign') >= 0 : false,
    hasBi0Screen: g ? g.children.indexOf('bi0Screen') >= 0 : false,
    hasBiShare: g ? g.children.indexOf('biShare') >= 0 : false,
    sidebarText: sb ? sb.textContent.replace(/\s+/g, ' ').slice(0, 400) : '',
  };
});

/* ---- 3. 大屏退役：bi0Screen 归一化到 biList；新建抽屉含 type pills ---- */
R.screenRetire = await page.evaluate(() => {
  go('bi0Screen');
  const afterScreen = state.page;
  go('bi0ScreenConfig');
  const afterScreenCfg = state.page;
  go('bi0Standard');
  const afterStandard = state.page;
  go('biList');
  return { afterScreen, afterScreenCfg, afterStandard, hasPageBi0Screen: !!PAGES.bi0Screen, navIds: BI_REPORT_NAV_IDS, orphanIds: BI_REPORT_ORPHAN_IDS };
});

/* ---- 新建抽屉：报表/大屏 pills + 提交进设计器 ---- */
R.biAddDrawer = await page.evaluate(() => {
  go('biList');
  biAdd();
  const dr = document.getElementById('dr-body');
  const pills = Array.from(dr.querySelectorAll('.pills .pill')).map(x => x.textContent.trim());
  return {
    drawerOpen: document.getElementById('drawer').classList.contains('on'),
    title: document.getElementById('dr-title').textContent,
    pills,
    pillRadios: dr.querySelectorAll('input[name="P_type"]').length,
    hasTypeReport: pills.some(t => t.indexOf('报表') >= 0),
    hasTypeScreen: pills.some(t => t.indexOf('大屏') >= 0),
  };
});
R.biAddSubmit = await page.evaluate(() => {
  const before = BI_REPORTS.length;
  /* 真实用户路径：点「🖥 大屏」pill + 填名称 */
  const pill = Array.from(document.querySelectorAll('#dr-body input[name="P_type"]')).find(x => x.value.indexOf('大屏') >= 0);
  if (pill) { pill.checked = true; pill.dispatchEvent(new Event('change', { bubbles: true })); }
  const t = document.getElementById('F_name');
  if (t) { t.value = '运营大屏（走查）'; t.dispatchEvent(new Event('input', { bubbles: true })); }
  biAddSubmit();
  const added = BI_REPORTS[BI_REPORTS.length - 1] || {};
  return { before, after: BI_REPORTS.length, addedName: added.name, addedType: added.type, landedPage: state.page };
});

/* ---- 4. 发布去向：biPubDlg 含①发布去向（中心/菜单），切菜单显示菜单配置 ---- */
R.pubDlg = await page.evaluate(() => {
  closeDrawer();
  state.tab.biPubDst = 'center';
  biPubDlg('运营日报', 1);
  const dr = document.getElementById('dr-body');
  const secs = Array.from(dr.querySelectorAll('.dsec, b')).map(x => x.textContent.trim()).filter(Boolean);
  return {
    drawerOpen: document.getElementById('drawer').classList.contains('on'),
    title: document.getElementById('dr-title').textContent,
    hasDstSection: dr.textContent.indexOf('发布去向') >= 0,
    hasCenter: dr.textContent.indexOf('报表中心') >= 0,
    hasMenu: dr.textContent.indexOf('菜单') >= 0,
    hasMenuCfgWhenCenter: dr.textContent.indexOf('菜单配置') >= 0,
    bodyLen: dr.innerHTML.length,
  };
});
R.pubDlgMenu = await page.evaluate(() => {
  biPubSetDst('menu');
  const dr = document.getElementById('dr-body');
  return {
    state: state.tab.biPubDst,
    hasMenuCfg: dr.textContent.indexOf('菜单配置') >= 0,
    hasSysMenu: dr.textContent.indexOf('sys_menu') >= 0 || dr.textContent.indexOf('ims_report_menu') >= 0,
    bodyLen: dr.innerHTML.length,
  };
});
R.pubDlgBackCenter = await page.evaluate(() => {
  biPubSetDst('center');
  const dr = document.getElementById('dr-body');
  return { state: state.tab.biPubDst, hasMenuCfg: dr.textContent.indexOf('菜单配置') >= 0 };
});

/* ---- 5. 全页回归（走真实路由） ---- */
R.renderAll = await page.evaluate(() => {
  closeDrawer();
  const ids = Object.keys(PAGES);
  const bad = [];
  ids.forEach(id => {
    try {
      go(id);
      const c = document.getElementById('content');
      const html = c ? c.innerHTML : '';
      if (typeof html !== 'string' || html.length < 10) bad.push([id, 'empty']);
    } catch (e) { bad.push([id, e.message]); }
  });
  return { total: ids.length, bad };
});

R.pageErrors = pageErrors;
console.log(JSON.stringify(R, null, 2));
await browser.close();