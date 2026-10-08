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

const report = {};

/* ===== 抽屉路径（我的查询 → 执行）——干净状态，强制 tab=list ===== */
await page.goto(FILE, { waitUntil: 'load' });
await page.waitForTimeout(200);
report.drawer = await page.evaluate(() => {
  go('bi0Query');
  setTab('bi0Query', 'saved');
  state.q.bi0ResultTab = 'list';
  bi0QueryExecuteSaved();
  const dr = document.getElementById('dr-body');
  return {
    drawerOpen: document.getElementById('drawer').classList.contains('on'),
    tabState: state.q.bi0ResultTab,
    activeTab: (dr.querySelector('.bi0-result-tabs .tab.on') || {}).textContent,
    hasChartBar: !!dr.querySelector('.bi0-chart-bar'),
    hasListTable: !!dr.querySelector('.tbl-wrap table'),
  };
});
await page.waitForTimeout(120);
report.drawerClickChart = await page.evaluate(() => {
  const dr = document.getElementById('dr-body');
  const chartTab = Array.from(dr.querySelectorAll('.bi0-result-tabs .tab')).find(t => t.textContent.includes('图表'));
  if (chartTab) chartTab.click();
  return {
    afterStateTab: state.q.bi0ResultTab,
    afterActiveTab: (dr.querySelector('.bi0-result-tabs .tab.on') || {}).textContent,
    afterHasChartBar: !!dr.querySelector('.bi0-chart-bar'),
    afterHasSvg: dr.querySelectorAll('svg').length,
    afterHasPolyline: dr.querySelectorAll('.bi0-chart-stage svg polyline').length,
    afterHasRect: dr.querySelectorAll('.bi0-chart-stage svg rect').length,
    contentBehindChartBar: !!document.querySelector('#content .bi0-chart-bar'),
  };
});
/* 抽屉内切换图表类型：柱 → 折 → 饼 */
report.drawerChartTypes = await page.evaluate(() => {
  const dr = () => document.getElementById('dr-body');
  const out = {};
  bi0QuerySetChart('折线图');
  out.line = { polyline: dr().querySelectorAll('.bi0-chart-stage svg polyline').length, rect: dr().querySelectorAll('.bi0-chart-stage svg rect').length, state: state.q.bi0ChartType };
  bi0QuerySetChart('饼图');
  out.pie = { rect: dr().querySelectorAll('.bi0-chart-stage svg rect').length, circle: dr().querySelectorAll('.bi0-chart-stage svg circle').length, state: state.q.bi0ChartType };
  bi0QuerySetChart('柱状图');
  out.bar = { rect: dr().querySelectorAll('.bi0-chart-stage svg rect').length, state: state.q.bi0ChartType };
  return out;
});

/* ===== 内联路径干净复测 ===== */
await page.goto(FILE, { waitUntil: 'load' });
await page.waitForTimeout(200);
report.inline = await page.evaluate(() => {
  go('bi0Query');
  setTab('bi0Query', 'builder');
  state.q.bi0ResultTab = 'list';
  bi0QueryExecute();
  const c = document.getElementById('content');
  return {
    activeTab: (c.querySelector('.bi0-result-tabs .tab.on') || {}).textContent,
    hasChartBar: !!c.querySelector('.bi0-chart-bar'),
  };
});
await page.waitForTimeout(120);
report.inlineClickChart = await page.evaluate(() => {
  const c = document.getElementById('content');
  const chartTab = Array.from(c.querySelectorAll('.bi0-result-tabs .tab')).find(t => t.textContent.includes('图表'));
  if (chartTab) chartTab.click();
  return {
    afterActiveTab: (c.querySelector('.bi0-result-tabs .tab.on') || {}).textContent,
    afterHasChartBar: !!c.querySelector('.bi0-chart-bar'),
  };
});

report.pageErrors = pageErrors;
console.log(JSON.stringify(report, null, 2));
await browser.close();