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

// 1. 知识库页（四叶 + 页头工具条 + 库内两级树）
await page.evaluate(() => { state.role = 'R11'; go('airKb'); });
await page.waitForTimeout(200);
await page.screenshot({ path: OUT + 'air-kb-1-page.png' });

// 2. 分类管理抽屉
await page.evaluate(() => { kbCatManage(); });
await page.waitForTimeout(150);
await page.screenshot({ path: OUT + 'air-kb-2-category.png' });

// 3. 上传资料抽屉（文件/URL/文本）
await page.evaluate(() => { closeDrawer(); kbUpload(); });
await page.waitForTimeout(150);
await page.screenshot({ path: OUT + 'air-kb-3-upload.png' });

// 4. 从系统转入向导（步骤② 勾选条目）
await page.evaluate(() => { closeDrawer(); kbTransfer(); kbTransferSetSource('TRAIN'); });
await page.waitForTimeout(150);
await page.screenshot({ path: OUT + 'air-kb-4-transfer.png' });

console.log('SHOTS_OK');
await browser.close();