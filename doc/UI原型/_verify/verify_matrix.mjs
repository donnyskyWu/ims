import { createRequire } from 'module';
const require = createRequire('C:/Users/donny/.workbuddy/binaries/node/workspace/node_modules/');
const { chromium } = require('playwright');
import path from 'path';
import { pathToFileURL } from 'url';

const htmlPath = path.resolve('UI原型/IMS-完整系统-UI原型.html');
const url = pathToFileURL(htmlPath).href;

const exe = 'C:/Users/donny/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe';
const browser = await chromium.launch({ executablePath: exe, args: ['--no-sandbox'] });
const page = await browser.newPage();
const consoleErrs = [], pageErrs = [];
page.on('console', m => { if (m.type() === 'error') consoleErrs.push(m.text()); });
page.on('pageerror', e => pageErrs.push(String(e)));
await page.goto(url, { waitUntil: 'load' });
await page.waitForTimeout(500);

// 切到 任务管理 Tab
const ok = await page.evaluate(() => {
  try { if (window.go) window.go('contentWork'); } catch (e) { return 'go err: ' + e.message; }
  try { if (window.setTab) window.setTab('contentWork', 'matrix'); } catch (e) { return 'setTab err: ' + e.message; }
  try { if (window.renderPage) window.renderPage(); } catch (e) { return 'renderPage err: ' + e.message; }
  return 'ok';
});
await page.waitForTimeout(400);

const result = await page.evaluate(() => {
  const t = document.querySelector('table.wt-matrix');
  if (!t) return { found: false };
  const groupRow = t.querySelector('thead tr.hg');
  const subRow = t.querySelector('thead tr.hs');
  const gths = groupRow ? Array.from(groupRow.querySelectorAll('th')).map(th => ({ txt: th.textContent.trim(), colspan: th.getAttribute('colspan') })) : [];
  const sths = subRow ? Array.from(subRow.querySelectorAll('th')).map(th => th.textContent.trim()) : [];
  const bodyRows = Array.from(t.querySelectorAll('tbody tr'));
  const dateCells = Array.from(t.querySelectorAll('tbody td.date-cell')).map(td => ({ txt: td.textContent.trim(), rowspan: td.getAttribute('rowspan') }));
  const firstRowCells = bodyRows[0] ? Array.from(bodyRows[0].querySelectorAll('td')).map(td => td.textContent.trim()) : [];
  const planBadges = Array.from(t.querySelectorAll('.plan-badge')).map(b => b.textContent.trim());
  const winBadges = Array.from(t.querySelectorAll('.win-badge')).map(b => b.textContent.trim());
  const summary = Array.from(document.querySelectorAll('.wt-matrix-summary .sm')).map(sm => sm.querySelector('.lb').textContent.trim() + '=' + sm.querySelector('.vv').textContent.trim());
  return {
    found: true,
    groupCols: gths,
    subCols: sths,
    bodyRowCount: bodyRows.length,
    dateCells,
    firstRowCells,
    planBadges,
    winBadges,
    summary
  };
});
console.log(JSON.stringify(result, null, 2));
console.log('setTab:', ok);
console.log('consoleErrors:', consoleErrs.length, consoleErrs.slice(0, 5));
console.log('pageErrors:', pageErrs.length, pageErrs.slice(0, 5));
await browser.close();