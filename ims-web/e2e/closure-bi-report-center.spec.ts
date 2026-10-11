import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * BUG-C038：报表中心 8 张都有 KPI、趋势图和中文明细；筛选含 IP 组、时间维度、重置和导出。
 */
test.describe('bi report center C038', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('kpi trend chinese columns filters and export', async ({ page }) => {
    test.setTimeout(90_000)
    await loginAdmin(page)
    await page.goto('/ims/bi/report')
    await expect(page.locator('h1')).toContainText('报表中心')
    await expect(page.getByTestId('bi-report-ip')).toBeVisible()
    await expect(page.getByTestId('bi-report-grain')).toBeVisible()
    await expect(page.getByTestId('bi-report-reset')).toBeVisible()
    await expect(page.getByTestId('bi-report-export-xlsx')).toBeVisible()
    await expect(page.getByTestId('bi-report-export-pdf')).toBeVisible()

    const titles = [
      '全平台账号视图',
      '账号状态监控',
      '短视频产出统计',
      '直播时长统计',
      '账号成本分摊',
      'ROI 分析报表',
      'IP 团队人员配置',
      '账号异常预警',
    ]
    for (const title of titles) {
      await expect(page.getByText(title, { exact: true })).toBeVisible()
    }

    await expect(page.getByTestId('bi-report-kpi')).toBeVisible()
    await expect(page.getByTestId('bi-report-trend')).toBeVisible()
    await expect(page.getByTestId('bi-report-result')).toContainText('平台')
    await expect(page.getByTestId('bi-report-result')).not.toContainText('metric')

    await page.getByTestId('bi-report-card-account-status').click()
    await expect(page.getByTestId('bi-report-result')).toContainText('状态')
    await expect(page.getByTestId('bi-report-result')).toContainText('健康度')
    await expect(page.getByTestId('bi-report-kpi')).toBeVisible()
    await expect(page.getByTestId('bi-report-trend')).toBeVisible()

    await page.getByTestId('bi-report-grain').selectOption('WEEK')
    await page.getByTestId('bi-report-run').click()
    await expect(page.getByTestId('bi-report-trend')).toBeVisible()

    await page.getByTestId('bi-report-reset').click()
    await expect(page.getByTestId('bi-report-reset-note')).toContainText('已重置统一筛选条')
    await expect(page.getByTestId('bi-report-grain')).toHaveValue('DAY')

    const xlsx = page.waitForEvent('download')
    await page.getByTestId('bi-report-export-xlsx').click()
    expect((await xlsx).suggestedFilename()).toContain('.xls')
    const pdf = page.waitForEvent('download')
    await page.getByTestId('bi-report-export-pdf').click()
    expect((await pdf).suggestedFilename()).toContain('.pdf')
  })
})
