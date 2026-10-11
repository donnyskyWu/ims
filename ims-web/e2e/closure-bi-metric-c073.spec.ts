import { expect, test } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/** BUG-C073 · 趋势图日期与明细一致，不再画出明细里没有的 09-24~09-29。 */
test.describe('bi metric analysis C073', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('trend chart uses the same dates as the detail rows', async ({ page }) => {
    test.setTimeout(120_000)
    const code = `C073_${Date.now()}`
    const name = `C073分析${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/bi/metric')
    await page.getByRole('button', { name: '新建指标' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '新建指标' })
    await modal.getByTestId('bi-metric-name').fill(name)
    await modal.getByTestId('bi-metric-code').fill(code)
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal).toBeHidden({ timeout: 15_000 })

    await page.goto('/ims/bi/analysis')
    const metricSelect = page.getByTestId('bi-analysis-metrics')
    const metricValue = await metricSelect.locator('option', { hasText: name }).getAttribute('value')
    expect(metricValue).toBeTruthy()
    await metricSelect.selectOption(metricValue!)
    await page.getByTestId('bi-analysis-ip').selectOption('')
    await page.getByTestId('bi-analysis-from').fill('2026-09-01')
    await page.getByTestId('bi-analysis-to').fill('2026-09-30')
    await page.getByTestId('bi-analysis-run').click()

    const table = page.locator('tbody')
    await expect(table).toContainText('2026-09-30')
    await expect(table).toContainText('电竞一组')
    await expect(table).toContainText('体育二组')
    await expect(page.getByTestId('bi-analysis-page')).toContainText('共 2 条')

    await page.locator('.tab', { hasText: '指标趋势' }).click()
    const chart = page.getByTestId('bi-analysis-chart')
    await expect(chart.locator('svg')).toBeVisible()
    await expect(chart).toContainText('09-30')
    await expect(chart).toContainText('电竞一组')
    await expect(chart).toContainText('体育二组')
    for (const day of ['09-24', '09-25', '09-26', '09-27', '09-28', '09-29']) {
      await expect(chart).not.toContainText(day)
    }
  })
})
