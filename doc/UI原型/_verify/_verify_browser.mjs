import fs from 'fs';
import { createRequire } from 'module';

const require = createRequire('C:/Users/donny/.workbuddy/binaries/node/workspace/node_modules/');
const { chromium } = require('playwright');

const FILE = 'file:///D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html';
const OUT = 'D:/self/sy/文档/IMS系统产品/UI原型/_verify/shots';
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({
  executablePath: 'C:/Users/donny/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe',
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const consoleErrors = [];
const pageErrors = [];
page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
page.on('pageerror', e => pageErrors.push(e.message));

await page.goto(FILE, { waitUntil: 'load' });
await page.waitForTimeout(400);

// --- sanity: app booted ---
const bootOk = await page.evaluate(() => typeof PAGES === 'object' && Object.keys(PAGES).length > 50);
console.log('app booted:', bootOk);

// --- navigate every CONTENT page, assert content non-empty ---
const contentIds = await page.evaluate(() => CONTENT_IDS.slice());
const navResults = [];
for (const id of contentIds) {
  const r = await page.evaluate((pid) => {
    try {
      go(pid);
      const c = document.getElementById('content');
      return { id: pid, page: state.page, len: (c ? c.innerHTML : '').length };
    } catch (e) { return { id: pid, error: e.message }; }
  }, id);
  navResults.push(r);
}

// --- open key drawers, screenshot a representative few ---
const drawerCases = [
  ['contentList', "state.opsContentEditIdx=0; opsContentEdit(0, state.opsEditTaskId);", 'drawer-content-edit'],
  ['contentList', "opsQuickTypesetDialog(0);", 'drawer-quick-typeset'],
  ['contentList', "opsAiTypesetDialog(0);", 'drawer-ai-typeset'],
  ['contentReview', "opsReviewView(0);", 'drawer-review'],
  ['contentTask', "taskDetail(0);", 'drawer-task-detail'],
  ['contentWork', "state.tab.contentWork='register'; wtAdd();", 'drawer-wt-add'],
  ['contentPlan', "opsPlanAdd();", 'drawer-plan-add'],
];
const drawerResults = [];
for (const [nav, code, shot] of drawerCases) {
  const r = await page.evaluate(([n, c]) => {
    try {
      go(n);
      const before = console; // noop
      // eslint-disable-next-line no-new-func
      new Function(c)();
      const dr = document.getElementById('drawer');
      return { ok: dr && dr.classList.contains('on'), title: (document.getElementById('dr-title') || {}).textContent || '' };
    } catch (e) { return { error: e.message }; }
  }, [nav, code]);
  drawerResults.push({ shot, ...r });
  if (r.ok) { await page.waitForTimeout(150); await page.screenshot({ path: OUT + '/' + shot + '.png' }); }
  await page.evaluate(() => { try { closeDrawer(); } catch (e) {} });
}

// --- full-page screenshots of key content pages ---
for (const [id, name] of [['contentWork', 'page-worktask'], ['contentTask', 'page-mytask'], ['contentList', 'page-contentlist'], ['contentPlan', 'page-plan'], ['contentReview', 'page-review'], ['contentLayout', 'page-layout']]) {
  await page.evaluate((pid) => go(pid), id);
  await page.waitForTimeout(150);
  await page.screenshot({ path: OUT + '/' + name + '.png' });
}

await browser.close();

console.log('\n--- CONTENT page navigation ---');
navResults.forEach(r => console.log(r.error ? ('  ERR ' + r.id + ' : ' + r.error) : ('  ok  ' + r.id + ' -> state.page=' + r.page + ' contentLen=' + r.len)));
console.log('\n--- drawer smoke ---');
drawerResults.forEach(r => console.log(r.error ? ('  ERR ' + r.shot + ' : ' + r.error) : ('  ok  ' + r.shot + ' on=' + r.ok + ' title=' + r.title)));
console.log('\n--- console errors:', consoleErrors.length, '| page errors:', pageErrors.length);
consoleErrors.slice(0, 20).forEach(e => console.log('  [console] ' + e));
pageErrors.slice(0, 20).forEach(e => console.log('  [pageerror] ' + e));
console.log('\nscreenshots ->', OUT);