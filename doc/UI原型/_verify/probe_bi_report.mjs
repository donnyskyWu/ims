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
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
await page.goto(FILE, { waitUntil: 'load' });
await page.waitForTimeout(300);

const report = {};

/* ---------- 1. 报表管理列表（biList） ---------- */
report.biList = await page.evaluate(() => {
  go('biList');
  const c = document.getElementById('content');
  return {
    page: state.page,
    treeItems: c.querySelectorAll('.bi-ti').length,
    cards: c.querySelectorAll('.bi-card').length,
    thumbs: c.querySelectorAll('.bi-card .bi-thumb svg').length,
    viewSwitch: c.querySelectorAll('.bi-viewsw button').length,
    len: c.innerHTML.length,
  };
});
/* 切列表视图 */
report.biListListView = await page.evaluate(() => {
  biListSetView('list');
  const c = document.getElementById('content');
  const t = c.querySelector('table');
  return { rows: t ? t.querySelectorAll('tbody tr').length : 0, heads: t ? Array.from(t.querySelectorAll('th')).map(x => x.textContent.trim()) : [] };
});
/* 切分类 */
report.biListCat = await page.evaluate(() => {
  biListSetView('card'); biListSetCat('运营');
  const c = document.getElementById('content');
  return { cards: c.querySelectorAll('.bi-card').length };
});
await page.evaluate(() => biListSetCat('all'));
await page.screenshot({ path: OUT + '/shot-biList.png', fullPage: false });

/* ---------- 2. 报表设计器（biDesign） ---------- */
report.biDesign = await page.evaluate(() => {
  go('biDesign');
  const c = document.getElementById('content');
  return {
    page: state.page,
    compCells: c.querySelectorAll('.comp-cell').length,
    draggable: c.querySelectorAll('.comp-cell[draggable="true"]').length,
    canvas: !!document.getElementById('biCanvas'),
    compsOnCanvas: c.querySelectorAll('.bidsn-cmp').length,
    layerItems: c.querySelectorAll('.layer-item').length,
    propSecs: c.querySelectorAll('.prop-sec').length,
    cols: getComputedStyle(c.querySelector('.bidsn')).gridTemplateColumns,
    len: c.innerHTML.length,
  };
});
await page.screenshot({ path: OUT + '/shot-biDesign-empty.png', fullPage: false });

/* 载入报表 → 自动铺组件 */
report.biDesignSeeded = await page.evaluate(() => {
  biOpenDesigner(1);
  return new Promise(res => setTimeout(() => {
    const c = document.getElementById('content');
    res({
      name: (state.bidsn || {}).name,
      comps: (state.bidsn || {}).comps ? state.bidsn.comps.length : 0,
      compsOnCanvas: c.querySelectorAll('.bidsn-cmp').length,
      layerItems: c.querySelectorAll('.layer-item').length,
      svgInCanvas: c.querySelectorAll('.bidsn-cmp svg').length,
      kpiVals: Array.from(c.querySelectorAll('.bidsn-cmp')).filter(n => n.textContent.indexOf('¥412.8') >= 0).length,
    });
  }, 120));
});
await page.screenshot({ path: OUT + '/shot-biDesign-seeded.png', fullPage: false });

/* 点击添加组件 */
report.biAddComp = await page.evaluate(() => {
  const before = (state.bidsn || {}).comps.length;
  biAddComp('radar', -1, -1);
  const c = document.getElementById('content');
  return { before, after: state.bidsn.comps.length, onCanvas: c.querySelectorAll('.bidsn-cmp').length, layers: c.querySelectorAll('.layer-item').length };
});

/* 选中组件 → 属性面板出现三区
   注意：biSelectComp 经 renderPage() 走 setTimeout(biRenderCanvas,0) 异步重绘，
   必须先把「触发」与「测量」拆成两次 evaluate + 等待，否则测到的是旧 DOM。 */
const selUid = await page.evaluate(() => {
  const uid = state.bidsn.comps[state.bidsn.comps.length - 1].uid;
  biSelectComp(uid);
  return uid;
});
await page.waitForTimeout(120);
report.biSelect = await page.evaluate((uid) => {
  const c = document.getElementById('content');
  return {
    sel: uid,
    selectedOnCanvas: c.querySelectorAll('.bidsn-cmp.sel').length,
    propSecs: Array.from(c.querySelectorAll('.prop-sec .prop-hd')).map(x => x.textContent.replace('▾', '').trim()),
    hasX: !!document.getElementById('bpX'),
    selLayer: c.querySelectorAll('.layer-item.sel').length,
  };
}, selUid);
await page.screenshot({ path: OUT + '/shot-biDesign-selected.png', fullPage: false });

/* 删除组件 */
report.biDelComp = await page.evaluate(() => {
  const before = state.bidsn.comps.length;
  biDelComp(state.bidsn.comps[before - 1].uid);
  return { before, after: state.bidsn.comps.length };
});

/* 撤销 */
report.biUndo = await page.evaluate(() => {
  const before = state.bidsn.comps.length;
  biDesignUndo();
  return { before, after: state.bidsn.comps.length };
});

/* 保存并发布 */
report.biSave = await page.evaluate(() => {
  biDesignSave(1);
  const r = BI_REPORTS.filter(x => x.id === 1)[0];
  return { ver: r.ver, st: r.st, comps: r.comps };
});

/* 真实拖拽：模拟 HTML5 DnD */
try {
  await page.evaluate(() => { go('biDesign'); });
  await page.waitForTimeout(150);
  const cell = await page.$('.comp-cell[draggable="true"]');
  const canvas = await page.$('#biCanvas');
  const before = await page.evaluate(() => state.bidsn.comps.length);
  // 用 dispatchEvent 构造 dragstart/drop（Playwright dragTo 对 HTML5 DnD 支持有限）
  await page.evaluate(() => {
    const cell = document.querySelector('.comp-cell[draggable="true"]');
    const cv = document.getElementById('biCanvas');
    const dt = new DataTransfer();
    cell.dispatchEvent(new DragEvent('dragstart', { bubbles: true, dataTransfer: dt }));
    const r = cv.getBoundingClientRect();
    cv.dispatchEvent(new DragEvent('drop', { bubbles: true, dataTransfer: dt, clientX: r.left + 500, clientY: r.top + 400 }));
  });
  await page.waitForTimeout(150);
  report.biRealDrop = await page.evaluate((b) => {
    const c = document.getElementById('content');
    const comps = state.bidsn.comps;
    const last = comps[comps.length - 1] || {};
    return { before: b, after: comps.length, lastType: last.type, lastX: last.x, lastY: last.y, onCanvas: c.querySelectorAll('.bidsn-cmp').length };
  }, before);
} catch (e) { report.biRealDrop = { error: e.message }; }

/* 拖动移动 */
report.biDragMove = await page.evaluate(() => {
  const c0 = state.bidsn.comps[0];
  const x0 = c0.x, y0 = c0.y;
  const node = document.querySelector('.bidsn-cmp[data-uid="' + c0.uid + '"]');
  const r = node.getBoundingClientRect();
  node.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: r.left + 10, clientY: r.top + 10 }));
  document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: r.left + 130, clientY: r.top + 90 }));
  document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
  return { x0, y0, x1: c0.x, y1: c0.y, moved: c0.x !== x0 || c0.y !== y0 };
});

/* 属性面板改坐标（同样拆分触发/测量，等待异步重绘） */
await page.evaluate(() => {
  const uid = state.bidsn.comps[0].uid;
  biSelectComp(uid);
});
await page.waitForTimeout(120);
await page.evaluate(() => {
  biPropSet('x', 60);
  biPropSet('title', 'GMV 合计');
});
await page.waitForTimeout(120);
report.biPropSet = await page.evaluate(() => {
  const uid = state.bidsn.comps[0].uid;
  const c0 = state.bidsn.comps[0];
  const node = document.querySelector('.bidsn-cmp[data-uid="' + uid + '"]');
  return { x: c0.x, title: c0.title, nodeLeft: node ? node.style.left : null, nodeTitle: node ? node.querySelector('.bc-h .t').textContent : null };
});
await page.screenshot({ path: OUT + '/shot-biDesign-final.png', fullPage: false });

/* ---------- 3. 预览页（biPreview） ---------- */
report.biPreview = await page.evaluate(() => {
  biOpenPreview(1);
  return new Promise(res => setTimeout(() => {
    const c = document.getElementById('content');
    return res({
      page: state.page,
      filterBar: !!c.querySelector('.bi-pv-bar'),
      kpis: c.querySelectorAll('.bi-pv-kpi .k').length,
      charts: c.querySelectorAll('.bi-chartbox svg').length,
      detailRows: (c.querySelector('table') || {}).querySelectorAll ? c.querySelector('table').querySelectorAll('tbody tr').length : 0,
      statusText: (c.querySelector('.bi-status') || {}).textContent || '',
    });
  }, 200));
});
await page.screenshot({ path: OUT + '/shot-biPreview.png', fullPage: false });

/* ---------- 4. 分享/发布（biShare） ---------- */
report.biShare = await page.evaluate(() => {
  go('biShare');
  return new Promise(res => setTimeout(() => {
    const c = document.getElementById('content');
    res({ page: state.page, tabs: Array.from(c.querySelectorAll('.tab')).map(t => t.textContent.trim()) });
  }, 120));
});
report.biShareLink = await page.evaluate(() => {
  state.tab.biShareTab = 'link'; renderPage();
  const c = document.getElementById('content');
  return { tabs: Array.from(c.querySelectorAll('.tab')).map(t => t.textContent.trim()), tables: c.querySelectorAll('table').length, rows: Array.from(c.querySelectorAll('tbody')).map(t => t.querySelectorAll('tr').length) };
});
report.biSharePub = await page.evaluate(() => {
  state.tab.biShareTab = 'pub'; renderPage();
  const c = document.getElementById('content');
  return { tables: c.querySelectorAll('table').length, rows: (c.querySelector('table') || {}).querySelectorAll ? c.querySelector('table').querySelectorAll('tbody tr').length : 0, heads: Array.from(c.querySelectorAll('th')).map(t => t.textContent.trim()) };
});
await page.screenshot({ path: OUT + '/shot-biShare-pub.png', fullPage: false });

/* 发布配置抽屉 */
report.biPubDlg = await page.evaluate(() => {
  state.tab.biShareTab = 'sub'; renderPage();
  biPubDlg('运营日报', 1);
  const d = document.getElementById('drawer');
  return { on: d.classList.contains('on'), title: document.getElementById('dr-title').textContent, bodyLen: document.getElementById('dr-body').innerHTML.length };
});
report.biSnapshotDlg = await page.evaluate(() => {
  closeDrawer(); biSnapshotDlg();
  return { on: document.getElementById('drawer').classList.contains('on'), title: document.getElementById('dr-title').textContent };
});

/* 大屏全屏 */
report.biFullscreen = await page.evaluate(() => {
  closeDrawer(); biFullscreen(2);
  const fs = document.querySelector('.fs-page');
  return { exists: !!fs, kpis: fs ? fs.querySelectorAll('div[style*="rgba(255,255,255,.05)"]').length : 0, svg: fs ? fs.querySelectorAll('svg').length : 0 };
});
await page.screenshot({ path: OUT + '/shot-biFullscreen.png', fullPage: false });
await page.evaluate(() => { const f = document.querySelector('.fs-page'); if (f) f.remove(); });

/* ---------- 5. 全页回归 ----------
   关键：必须走真实路由 go(id)（内含 *Norm 归一化），不能直接 PAGES[id]()。
   直接调用会绕过归一化，把别名页（bi0Standard→bi0Report、biShare→biList 等）
   当成独立页渲染，导致 pgHead 读 MODS[别名] 为 undefined 而假报错。 */
const renderAll = await page.evaluate(() => {
  const ids = Object.keys(PAGES);
  const bad = [];
  const aliased = [];
  ids.forEach(id => {
    try {
      go(id);                       // 走真实路由 + 归一化
      const real = state.page;      // 归一化后的真实页
      if (real !== id) aliased.push([id, real]);
      const c = document.getElementById('content');
      const html = c ? c.innerHTML : '';
      if (typeof html !== 'string' || html.length < 10) bad.push([id, 'empty']);
    } catch (e) { bad.push([id, e.message]); }
  });
  return { total: ids.length, bad, aliasCount: aliased.length, aliased };
});
report.renderAll = renderAll;

console.log('renderAll: total=' + renderAll.total + ' bad=' + JSON.stringify(renderAll.bad) + ' alias=' + renderAll.aliasCount);

await browser.close();
fs.writeFileSync(OUT + '/probe_bi_report.json', JSON.stringify(report, null, 2), 'utf8');
console.log(JSON.stringify(report, null, 2));
console.log('\npageErrors:', pageErrors.length);
pageErrors.slice(0, 12).forEach(e => console.log('  ' + e));