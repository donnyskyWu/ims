import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/dc-drill-tails-193'
const SEED_SESSION = 'IMS20261008DYS0082'

/**
 * #193 · DC 下钻收尾（纯 UI）
 * 空周期、无组件看板、新鲜度状态色；场次 openDetail 打开明细抽屉；反查带上场次号。
 */
test.describe('dc drill tails empty freshness', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty period, blank layout, freshness status, and session drill', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/dc/trace')
    await page.getByTestId('dc-trace-dashboard').click()
    await page.waitForURL(/\/ims\/dc\/dashboard/)

    const freshness = page.getByTestId('dc-dash-freshness')
    await expect(freshness).toBeVisible()
    const syncRows = page.getByTestId('dc-dash-sync-row')
    await expect(syncRows.first()).toBeVisible()
    const statuses = await syncRows.evaluateAll((rows) => rows.map((row) => row.getAttribute('data-status') || ''))
    expect(statuses.length).toBeGreaterThan(0)
    for (const status of statuses) {
      expect(['SUCCESS', 'DELAYED', 'FAILED']).toContain(status)
    }
    const alert = page.getByTestId('dc-dash-fresh-alert')
    if (statuses.includes('FAILED')) {
      await expect(alert).toContainText('同步失败，断点续传中')
      await expect(page.getByTestId('dc-dash-asof')).toHaveAttribute('data-alarm', '1')
    } else if (statuses.includes('DELAYED')) {
      await expect(alert).toContainText('数据新鲜度超过 1 小时')
      await expect(page.getByTestId('dc-dash-asof')).toHaveAttribute('data-alarm', '1')
    } else {
      await expect(alert).toHaveCount(0)
      await expect(page.getByTestId('dc-dash-asof')).toHaveAttribute('data-alarm', '0')
    }
    await expect(page.getByTestId('dc-dash-sync-empty')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/01-freshness.png`, fullPage: true })

    const emptyBoard = page.getByTestId('dc-dash-empty-board')
    if ((await emptyBoard.count()) > 0) {
      await expect(emptyBoard).toContainText('暂无启用看板，请联系管理员配置（R1/R4）')
      await page.screenshot({ path: `${SHOTS}/02-empty-board.png`, fullPage: true })
    }

    await page.getByTestId('dc-dash-period').fill('2098-01')
    await page.getByTestId('dc-dash-refresh').click()
    await expect(page.getByTestId('dc-dash-dim-empty')).toContainText('该周期暂无已核算场次')
    await page.screenshot({ path: `${SHOTS}/03-empty-dimension.png`, fullPage: true })

    await page.getByTestId('dc-dash-manage').click()
    const drawer = page.getByTestId('dc-dash-drawer')
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('dc-dash-new').click()
    await drawer.getByTestId('dc-dash-name').fill('空布局-193')
    const created = page.waitForResponse(
      (res) => res.url().includes('/dc/dashboard') && res.request().method() === 'POST' && res.status() === 200,
    )
    await drawer.getByTestId('dc-dash-save').click()
    const createdBody = await (await created).json()
    expect(createdBody.code).toBe(0)
    expect(createdBody.data.dashboardName).toBe('空布局-193')
    await expect(drawer.getByTestId('dc-dash-save-note')).toContainText('看板已创建')
    await drawer.getByTestId('dc-dash-drawer-close').click()
    await expect(page.getByTestId('dc-dash-empty-board')).toHaveCount(0)
    await expect(page.getByTestId('dc-dash-layout-empty')).toContainText('该看板尚未配置组件')
    await page.screenshot({ path: `${SHOTS}/04-empty-layout.png`, fullPage: true })

    await page.goto(`/ims/dc/trace?entryType=SESSION&keyword=${SEED_SESSION}&openDetail=1`)
    const sessionDrawer = page.getByTestId('dc-trace-session-drawer')
    await expect(sessionDrawer).toBeVisible({ timeout: 15_000 })
    await expect(sessionDrawer).toContainText(SEED_SESSION)
    await expect(page.getByTestId('dc-trace-keyword')).toHaveValue(SEED_SESSION)
    await expect(page.getByTestId('dc-trace-entry-type')).toHaveValue('SESSION')
    await page.screenshot({ path: `${SHOTS}/05-session-drawer.png`, fullPage: true })

    const listed = page.waitForResponse(
      (res) =>
        res.url().includes('/dc/profit-trace/list') &&
        res.url().includes(`sessionCode=${SEED_SESSION}`) &&
        res.request().method() === 'GET',
    )
    await page.goto(`/ims/fin/profit-trace?sessionCode=${SEED_SESSION}`)
    await listed
    await expect(page.getByTestId('fin-trace-session')).toHaveValue(SEED_SESSION)
    await page.screenshot({ path: `${SHOTS}/06-profit-prefill.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
