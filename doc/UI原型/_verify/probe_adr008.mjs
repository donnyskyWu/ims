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

/* ---- 1. 模块定义：AUTH-003 改名 + SYS-002 描述更新 ---- */
R.mods = await page.evaluate(() => ({
  authPositionName: (MODS.authPosition || {}).name,
  authPositionDesc: (MODS.authPosition || {}).desc,
  authMgmtDesc: (MODS.authMgmt || {}).desc,
  sysRoleDesc: (MODS.sysRole || {}).desc,
}));

/* ---- 2. 岗位-角色供给规则页（AUTH-003）---- */
R.authPosition = await page.evaluate(() => {
  go('authPosition');
  const c = document.getElementById('content');
  const t = c.textContent;
  const ths = Array.from(c.querySelectorAll('th')).map(x => x.textContent.trim());
  return {
    landed: state.page,
    hasNewTitle: t.indexOf('岗位-角色供给规则') >= 0,
    hasAdr: t.indexOf('ADR-IMS-008') >= 0,
    noOldMatrix: t.indexOf('岗位-权限矩阵') < 0,
    hasGrantRoleCol: ths.indexOf('授予角色') >= 0,
    hasRoleSourceCol: ths.indexOf('角色来源') >= 0,
    noPermSummaryCol: ths.indexOf('权限概要') < 0,
    hasFailClosed: t.indexOf('失败关闭') >= 0,
    hasPendingBadge: t.indexOf('待配置') >= 0,
    hasAutoCreate: t.indexOf('自动创建') >= 0,
    statCards: c.querySelectorAll('.card.stat').length,
  };
});

/* ---- 3. 新建供给规则抽屉（授予角色 Select，无权限矩阵）---- */
R.authRuleDrawer = await page.evaluate(() => {
  authRuleAdd();
  const dr = document.getElementById('dr-body');
  const labels = Array.from(dr.querySelectorAll('.flabel, label, b')).map(x => x.textContent.trim()).filter(Boolean);
  const sel = Array.from(dr.querySelectorAll('select')).map(s => Array.from(s.options).map(o => o.value));
  return {
    title: document.getElementById('dr-title').textContent,
    hasPost: labels.some(x => x.indexOf('钉钉岗位') >= 0),
    hasGrantRole: labels.some(x => x.indexOf('授予角色') >= 0),
    noPermCount: labels.every(x => x.indexOf('权限概要') < 0),
    selectCount: sel.length,
    roleOptsHasOpsLive: sel.some(a => a.indexOf('ops:live') >= 0),
  };
});

/* ---- 4. 角色页（SYS-002）吸收权限明细 ---- */
R.sysRole = await page.evaluate(() => {
  closeDrawer();
  go('sysRole');
  const c = document.getElementById('content');
  const t = c.textContent;
  const ths = Array.from(c.querySelectorAll('th')).map(x => x.textContent.trim());
  const rows = c.querySelectorAll('tbody tr').length;
  return {
    landed: state.page,
    hasAdr: t.indexOf('ADR-IMS-008') >= 0,
    hasUniqueCarrier: t.indexOf('权限唯一载体') >= 0,
    hasFpCol: ths.some(x => x.indexOf('功能点 R/W/D') >= 0),
    hasScopeCol: ths.indexOf('数据范围') >= 0,
    hasPostCol: ths.indexOf('钉钉岗位') >= 0,
    hasSourceCol: ths.indexOf('来源') >= 0,
    hasPendingRow: t.indexOf('待配置') >= 0,
    hasAutoCreate: t.indexOf('自动创建') >= 0,
    hasDingSync: t.indexOf('钉钉同步') >= 0,
    rowCount: rows,
    statCards: c.querySelectorAll('.card.stat').length,
    editBtn: t.indexOf('编辑权限') >= 0,
    scopeBtn: t.indexOf('数据范围') >= 0,
    oldHintGone: t.indexOf('AUTH-003 岗位模板 dataScope') < 0,
  };
});

/* ---- 5. 全页回归 ---- */
R.renderAll = await page.evaluate(() => {
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

/* ---- 6. 残留旧词扫描（页面文本）---- */
R.stale = await page.evaluate(() => {
  const hits = [];
  Object.keys(PAGES).forEach(id => {
    try {
      go(id);
      const t = (document.getElementById('content') || {}).textContent || '';
      ['岗位模板', '岗位-权限矩阵'].forEach(w => { if (t.indexOf(w) >= 0) hits.push([id, w]); });
    } catch (e) {}
  });
  return hits;
});

R.pageErrors = pageErrors;
console.log(JSON.stringify(R, null, 2));
await browser.close();