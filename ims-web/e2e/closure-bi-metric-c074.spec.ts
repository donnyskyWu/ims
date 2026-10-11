import { expect, test, type Locator } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/** BUG-C074 · 饼图图例里的数值和占比不能叠在一起。 */
test.describe('bi metric analysis C074', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('pie legend keeps value and percent apart', async ({ page }) => {
    test.setTimeout(120_000)
    const code = `C074_${Date.now()}`
    const name = `C074分析${Date.now()}`

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
    await page.getByTestId('bi-analysis-from').fill('2026-09-01')
    await page.getByTestId('bi-analysis-to').fill('2026-09-30')
    await page.getByTestId('bi-analysis-run').click()
    await expect(page.locator('tbody')).toContainText('电竞一组')

    await page.locator('.tab', { hasText: '指标趋势' }).click()
    await page.getByTestId('bi-analysis-chart-type').selectOption('pie')
    const chart = page.getByTestId('bi-analysis-chart')
    const value = chart.locator('text', { hasText: '1,284,600' })
    const percent = chart.locator('text', { hasText: '59.0%' })
    await expect(value).toBeVisible()
    await expect(percent).toBeVisible()
    expect(await separated(value, percent)).toBe(true)
    expect(await separated(chart.locator('text', { hasText: '892,400' }), chart.locator('text', { hasText: '41.0%' }))).toBe(true)
  })
})

async function separated(left: Locator, right: Locator): Promise<boolean> {
  const a = await left.boundingBox()
  const b = await right.boundingBox()
  if (!a || !b) return false
  const apart = a.x + a.width <= b.x + 0.5 || b.x + b.width <= a.x + 0.5
  const sameRow = Math.abs(a.y - b.y) < 8
  return sameRow && apart
}
