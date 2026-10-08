import { createRequire } from 'module';
const require = createRequire('C:/Users/donny/.workbuddy/binaries/node/workspace/node_modules/');
const { chromium } = require('playwright');
const FILE = 'file:///D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html';
const OUT = 'D:/self/sy/文档/IMS系统产品/UI原型/_verify/shots/';
const browser = await chromium.launch({
  executablePath: 'C:/Users/donny/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe',
  args: ['--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
await page.goto(FILE, { waitUntil: 'load' });
await page.waitForTimeout(300);

// 1. 基础信息步（表单基线）
await page.evaluate(() => { go('queryTool'); queryToolOpenWizard(); });
await page.waitForTimeout(150);
await page.screenshot({ path: OUT + 'qt-style-1-basic.png' });

// 2. TRACE 配置载荷步（统一后的下拉框/文本框/表内 select）
await page.evaluate(() => { queryToolSetWizardMode('TRACE'); queryToolWizardNext(); queryToolWizardNext(); });
await page.waitForTimeout(150);
await page.screenshot({ path: OUT + 'qt-style-2-trace-cfg.png' });

// 3. DRILL 配置载荷步
await page.evaluate(() => { queryToolSetWizardMode('DRILL'); queryToolWizardPrev(); });
await page.waitForTimeout(150);
await page.evaluate(() => { queryToolWizardNext(); });
await page.waitForTimeout(150);
await page.screenshot({ path: OUT + 'qt-style-3-drill-cfg.png' });

console.log('SHOTS_OK');
await browser.close();