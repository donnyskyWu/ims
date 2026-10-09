import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/dc-filter-edges-242'
const SEED_SESSION = 'IMS20261008DYS0082'

/**
 * #242 · DC 筛选与下钻边角（纯 UI）
 * 日期颠倒/只填一侧、日期范围内无场次、团队不可下钻、画布空态、
 * 性能监控空区间、利润反查筛选空态。
 */
test.describe('dc filter and drill edge copy', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('date edges, empty drill copy, canvas, perf, and profit filters', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/dc/trace')
    await expect(page.getByTestId('dc-trace-graph-empty')).toContainText('选择入口后查询')
    await page.getByTestId('dc-trace-date-from').fill('2026-10-09')
    await page.getByTestId('dc-trace-date-to').fill('2026-10-01')
    await page.getByTestId('dc-trace-submit').click()
    await expect(page.getByTestId('dc-trace-error')).toContainText('开始日期不能晚于结束日期')
    await page.screenshot({ path: `${SHOTS}/01-trace-inverted-range.png`, fullPage: true })

    await page.getByTestId('dc-trace-date-to').fill('')
    await page.getByTestId('dc-trace-submit').click()
    await expect(page.getByTestId('dc-trace-error')).toContainText('请同时填写开始日和结束日')

    await page.goto(`/ims/dc/trace?entryType=SESSION&keyword=${SEED_SESSION}`)
    await expect(page.getByTestId('dc-trace-keyword')).toHaveValue(SEED_SESSION)
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText('场次', { timeout: 15_000 })
    await expect(page.getByTestId('dc-trace-detail-table')).toContainText(SEED_SESSION)
    await page.getByTestId('dc-trace-date-from').fill('2099-03-01')
    await page.getByTestId('dc-trace-date-to').fill('2099-03-02')
    await page.getByTestId('dc-trace-submit').click()
    await expect(page.getByTestId('dc-trace-detail-empty')).toContainText('该日期范围内暂无场次')
    await expect(page.getByTestId('dc-trace-graph-empty')).toContainText('该日期范围内暂无关联场次')
    await page.screenshot({ path: `${SHOTS}/02-trace-range-empty.png`, fullPage: true })

    await page.getByTestId('dc-trace-mode-aggregate').click()
    await expect(page.getByTestId('dc-trace-aggregate-empty')).toContainText('该日期范围内暂无汇总')
    await page.getByTestId('dc-trace-aggregate-by').selectOption('TEAM')
    await expect(page.getByTestId('dc-trace-aggregate-team-hint')).toContainText('团队汇总不可下钻')
    await page.screenshot({ path: `${SHOTS}/03-trace-aggregate-team.png`, fullPage: true })

    await page.goto('/ims/dc/dashboard')
    await expect(page.getByTestId('dc-dash-freshness')).toBeVisible()
    await page.getByTestId('dc-dash-manage').click()
    const drawer = page.getByTestId('dc-dash-drawer')
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('dc-dash-new').click()
    await expect(drawer.getByTestId('dc-dash-canvas-empty')).toContainText('从左侧组件库选择组件加入画布')
    await page.screenshot({ path: `${SHOTS}/04-dashboard-canvas-empty.png`, fullPage: true })
    await drawer.getByTestId('dc-dash-drawer-close').click()

    await page.goto('/ims/dc/trace/perf')
    await expect(page.locator('h1')).toHaveText('穿透性能监控')
    await page.getByTestId('dc-trace-perf-from').fill('2026-10-09')
    await page.getByTestId('dc-trace-perf-to').fill('2026-10-01')
    await page.getByTestId('dc-trace-perf-refresh').click()
    await expect(page.getByTestId('dc-trace-perf-range')).toContainText('开始日期不能晚于结束日期')
    await page.getByTestId('dc-trace-perf-from').fill('2099-01-01')
    await page.getByTestId('dc-trace-perf-to').fill('2099-01-02')
    await page.getByTestId('dc-trace-perf-refresh').click()
    await expect(page.getByTestId('dc-trace-perf-empty')).toContainText('所选日期暂无穿透查询')
    await expect(page.getByTestId('dc-trace-perf-count')).toContainText('0')
    await page.screenshot({ path: `${SHOTS}/05-perf-empty-range.png`, fullPage: true })

    await page.goto('/ims/fin/profit-trace')
    await expect(page.locator('h1')).toHaveText('利润反查', { timeout: 15_000 })
    await page.getByTestId('fin-trace-session').fill('IMS-NO-SUCH-242')
    await page.getByTestId('fin-trace-list-query').click()
    await expect(page.getByTestId('fin-trace-list-empty')).toContainText('当前筛选无已核算利润')
    await page.screenshot({ path: `${SHOTS}/06-profit-filter-empty.png`, fullPage: true })

    await page.getByTestId('fin-trace-tab-aggregate').click()
    await page.getByTestId('fin-trace-aggregate-from').fill('1999-04-01')
    await page.getByTestId('fin-trace-aggregate-to').fill('1999-04-30')
    await page.getByTestId('fin-trace-aggregate-query').click()
    await expect(page.getByTestId('fin-trace-aggregate-empty')).toContainText(
      '该维度暂无已核算利润（当前日期范围内无场次）',
    )

    await page.getByTestId('fin-trace-tab-abnormal').click()
    await page.getByTestId('fin-trace-abnormal-platform').fill('ZZZ-242')
    await page.getByTestId('fin-trace-abnormal-query').click()
    await expect(page.getByTestId('fin-trace-abnormal-empty')).toContainText('当前筛选暂无异常利润')
    await page.screenshot({ path: `${SHOTS}/07-profit-abnormal-filter.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
