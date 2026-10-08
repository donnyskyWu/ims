import fs from 'fs';
import { createRequire } from 'module';

const require = createRequire('C:/Users/donny/.workbuddy/binaries/node/workspace/node_modules/');
const { chromium } = require('playwright');

const FILE = 'file:///D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html';
const OUT = 'D:/self/sy/文档/IMS系统产品/UI原型/_verify/shots';
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({
  executablePath: 'C:/Users/donny/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe',
  args: ['--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
await page.goto(FILE, { waitUntil: 'load' });
await page.waitForTimeout(300);

/* 1. 报表管理 */
await page.evaluate(() => { go('biList'); });
await page.waitForTimeout(200);
await page.screenshot({ path: OUT + '/idx-1-biList.png' });

/* 2. 报表中心 */
await page.evaluate(() => { go('bi0Report'); });
await page.waitForTimeout(200);
await page.screenshot({ path: OUT + '/idx-2-bi0Report.png' });

/* 3. 新建抽屉（报表/大屏 pills） */
await page.evaluate(() => { go('biList'); biAdd(); });
await page.waitForTimeout(200);
await page.screenshot({ path: OUT + '/idx-3-biAdd.png' });
await page.evaluate(() => { closeDrawer(); });

/* 4. 发布配置抽屉（①发布去向） */
await page.evaluate(() => { state.tab.biPubDst = 'menu'; biPubDlg('运营日报', 1); });
await page.waitForTimeout(200);
await page.screenshot({ path: OUT + '/idx-4-biPubDlg.png' });
await page.evaluate(() => { closeDrawer(); });

/* 5. 自定义查询 · 图表展示（内联） */
await page.evaluate(() => { go('bi0Query'); setTab('bi0Query', 'builder'); state.q.bi0ResultTab = 'chart'; state.q.bi0ChartType = '折线图'; bi0QueryExecute(); });
await page.waitForTimeout(200);
await page.screenshot({ path: OUT + '/idx-5-queryChart.png' });

/* 6. 自定义查询 · 执行抽屉 + 图表 Tab */
await page.evaluate(() => { setTab('bi0Query', 'saved'); state.q.bi0ResultTab = 'chart'; state.q.bi0ChartType = '柱状图'; bi0QueryExecuteSaved(); });
await page.waitForTimeout(250);
await page.screenshot({ path: OUT + '/idx-6-queryDrawer.png' });

console.log('shots done. pageErrors=' + pageErrors.length);
pageErrors.forEach(e => console.log('  ' + e));
await browser.close();