import fs from 'fs';
import { createRequire } from 'module';

const require = createRequire('C:/Users/donny/.workbuddy/binaries/node/workspace/node_modules/');
const { chromium } = require('playwright');

const FILE = 'file:///D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html';
const OUT = 'D:/self/sy/文档/IMS系统产品/UI原型/_verify/probe';
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({
  executablePath: 'C:/Users/donny/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe',
  args: ['--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
await page.goto(FILE, { waitUntil: 'load' });
await page.waitForTimeout(300);

const targets = [
  ['bi0Metric', 'page=bi0Metric'],
  ['bi0Analysis', 'page=bi0Analysis'],
  ['bi0Report', 'page=bi0Report'],
  ['bi0Query', 'page=bi0Query'],
  ['bi0Screen', 'page=bi0Screen'],
  ['biList', 'page=biList'],
];

const report = {};
for (const [id, label] of targets) {
  const info = await page.evaluate((pid) => {
    try {
      go(pid);
      const c = document.getElementById('content');
      const html = c ? c.innerHTML : '';
      const tables = [];
      c.querySelectorAll('table').forEach(t => {
        const heads = [];
        t.querySelectorAll('thead tr').forEach(tr => {
          const cells = [];
          tr.querySelectorAll('th').forEach(th => cells.push({ t: th.textContent.trim(), cs: th.colSpan, rs: th.rowSpan }));
          heads.push(cells);
        });
        const rowCount = t.querySelectorAll('tbody tr').length;
        tables.push({ heads, rowCount });
      });
      const btns = [];
      c.querySelectorAll('button, .btn').forEach(b => { const s = b.textContent.trim(); if (s) btns.push(s); });
      const tabs = [];
      c.querySelectorAll('.tab').forEach(t => tabs.push(t.textContent.trim()));
      const cards = c.querySelectorAll('.card').length;
      const hints = [];
      c.querySelectorAll('.hint').forEach(h => hints.push(h.textContent.trim().slice(0, 160)));
      return { page: state.page, len: html.length, tables, btns: btns.slice(0, 40), tabs, cards, hints: hints.slice(0, 8) };
    } catch (e) { return { error: e.message }; }
  }, id);
  report[label] = info;
}

// 指标管理：打开新增抽屉
try {
  await page.evaluate(() => { go('bi0Metric'); bi0MetricEdit(-1); });
  await page.waitForTimeout(200);
  const drawer = await page.evaluate(() => {
    const d = document.getElementById('drawer');
    return { on: d && d.classList.contains('on'), title: (document.getElementById('dr-title') || {}).textContent, bodyLen: (document.getElementById('dr-body') || {}).innerHTML ? document.getElementById('dr-body').innerHTML.length : 0 };
  });
  report['_drawer_metricNew'] = drawer;
  await page.screenshot({ path: OUT + '/shot-drawer-metric.png', fullPage: false });
} catch (e) { report['_drawer_metricNew'] = { error: e.message }; }

// 自定义查询：执行查询
try {
  await page.evaluate(() => { closeDrawer(); go('bi0Query'); });
  await page.waitForTimeout(100);
  await page.evaluate(() => { bi0QueryExecute(); });
  await page.waitForTimeout(150);
  const q = await page.evaluate(() => {
    const c = document.getElementById('content');
    const tabs = []; c.querySelectorAll('.tab').forEach(t => tabs.push(t.textContent.trim()));
    const charts = c.querySelectorAll('.bi0-chart-ph, .bi0-chart-bar').length;
    return { tabs, charts, len: c.innerHTML.length };
  });
  report['_query_executed'] = q;
  await page.screenshot({ path: OUT + '/shot-query.png', fullPage: false });
} catch (e) { report['_query_executed'] = { error: e.message }; }

// 报表：打开一个 slug
try {
  await page.evaluate(() => { go('bi0Report'); bi0OpenReport('unified-account'); });
  await page.waitForTimeout(200);
  const r = await page.evaluate(() => {
    const d = document.getElementById('drawer');
    return { on: d && d.classList.contains('on'), title: (document.getElementById('dr-title') || {}).textContent };
  });
  report['_report_open'] = r;
  await page.screenshot({ path: OUT + '/shot-report.png', fullPage: false });
} catch (e) { report['_report_open'] = { error: e.message }; }

await browser.close();

fs.writeFileSync(OUT + '/probe.json', JSON.stringify(report, null, 2), 'utf8');
console.log(JSON.stringify(report, null, 2));
console.log('\npageErrors:', pageErrors.length);
pageErrors.slice(0, 10).forEach(e => console.log('  ' + e));